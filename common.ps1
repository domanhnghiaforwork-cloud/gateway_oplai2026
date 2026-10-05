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
