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

# Export host ports so all three Compose projects use the same gateway settings.
# Process environment overrides .env, following Docker Compose precedence.
$hostPortDefaults = [ordered]@{
    GATEWAY_PORT = '8080'
    SYSTEM_FRONTEND_PORT = '3001'
    CHATBOT_FRONTEND_PORT = '3000'
    SYSTEM_BACKEND_PORT = '8000'
    NGROK_INSPECTOR_PORT = '4040'
}
foreach ($portName in $hostPortDefaults.Keys) {
    $portValue = [Environment]::GetEnvironmentVariable($portName, 'Process')
    if (-not $portValue) { $portValue = $currentGatewaySettings[$portName] }
    if (-not $portValue) { $portValue = $hostPortDefaults[$portName] }
    $portNumber = 0
    if ($portValue -notmatch '^[0-9]+$' -or -not [int]::TryParse($portValue, [ref]$portNumber) -or $portNumber -lt 1 -or $portNumber -gt 65535) {
        throw "Invalid ${portName}: use a port between 1 and 65535."
    }
    [Environment]::SetEnvironmentVariable($portName, [string]$portNumber, 'Process')
}

function Assert-UniqueHostPorts([switch]$LocalOnly) {
    $usedPorts = @{}
    foreach ($portName in $hostPortDefaults.Keys) {
        if ($LocalOnly -and $portName -eq 'NGROK_INSPECTOR_PORT') { continue }
        $portValue = [Environment]::GetEnvironmentVariable($portName, 'Process')
        if ($usedPorts.ContainsKey($portValue)) {
            throw "Host port $portValue is shared by $($usedPorts[$portValue]) and $portName. Choose different host ports."
        }
        $usedPorts[$portValue] = $portName
    }
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
