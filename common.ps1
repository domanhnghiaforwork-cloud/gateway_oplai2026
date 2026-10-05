$ErrorActionPreference = 'Stop'
$workspacePath = Split-Path -Parent $PSScriptRoot
$systemPath = Join-Path $workspacePath 'system_olpai2026'
$chatbotPath = Join-Path $workspacePath 'chatbot_oplai2026/chat_bot_allforn'
$gatewayEnvPath = Join-Path $PSScriptRoot '.env'

function Read-EnvFile([string]$Path) {
    $values = @{}
    if (Test-Path -LiteralPath $Path) {
        foreach ($line in Get-Content -LiteralPath $Path) {
            if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$') {
                $values[$matches[1]] = $matches[2].Trim().Trim('"').Trim("'")
            }
        }
    }
    return $values
}

function Invoke-Docker([string[]]$DockerArgs) {
    & docker @DockerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Docker failed (exit $LASTEXITCODE). Check the output above."
    }
}

function Initialize-Sso {
    $settings = Read-EnvFile $gatewayEnvPath
    if (-not $settings['CHATBOT_SSO_SECRET']) {
        $bytes = New-Object byte[] 48
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
        $secret = [Convert]::ToBase64String($bytes)
        Add-Content -LiteralPath $gatewayEnvPath -Value "`nCHATBOT_SSO_SECRET=$secret" -Encoding UTF8
        $settings['CHATBOT_SSO_SECRET'] = $secret
        Write-Host 'Initialized the private SSO key in gateway .env.'
    }
    if ($settings['CHATBOT_SSO_SECRET'].Length -lt 64) {
        throw 'CHATBOT_SSO_SECRET must contain at least 64 characters.'
    }
    $env:CHATBOT_SSO_SECRET = $settings['CHATBOT_SSO_SECRET']
}

$currentGatewaySettings = Read-EnvFile $gatewayEnvPath
if ($currentGatewaySettings['CHATBOT_SSO_SECRET']) {
    $env:CHATBOT_SSO_SECRET = $currentGatewaySettings['CHATBOT_SSO_SECRET']
}

function Assert-Docker {
    & docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker is unavailable. Start Docker Desktop and try again.'
    }
}

$systemCompose = @(
    'compose', '--project-directory', $systemPath, '-p', 'system_olpai2026',
    '-f', (Join-Path $systemPath 'docker-compose.yml'),
    '-f', (Join-Path $PSScriptRoot 'system.override.yaml')
)
$chatbotCompose = @(
    'compose', '--project-directory', $chatbotPath,
    '--env-file', (Join-Path $chatbotPath '.env'),
    '-f', (Join-Path $chatbotPath 'compose.yaml'),
    '-f', (Join-Path $PSScriptRoot 'chatbot.override.yaml')
)
$gatewayCompose = @(
    'compose', '--project-directory', $PSScriptRoot,
    '--env-file', $gatewayEnvPath,
    '-f', (Join-Path $PSScriptRoot 'compose.yaml')
)
