param(
    [switch]$Build,
    [switch]$LocalOnly
)
. (Join-Path $PSScriptRoot 'common.ps1')

Assert-Docker
foreach ($requiredPath in @((Join-Path $chatbotPath '.env'), (Join-Path $chatbotPath 'backend/.env'))) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Missing $requiredPath. Configure the chatbot environment first."
    }
}
if (-not (Test-Path -LiteralPath $gatewayEnvPath)) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot '.env.example') -Destination $gatewayEnvPath
    Write-Host 'Created gateway/.env. Fill in NGROK_DOMAIN and NGROK_AUTHTOKEN for public access.'
}
$gatewaySettings = Read-EnvFile $gatewayEnvPath
if (-not $LocalOnly) {
    if (-not $gatewaySettings['NGROK_AUTHTOKEN'] -or $gatewaySettings['NGROK_AUTHTOKEN'] -match '^replace_') {
        throw 'Set NGROK_AUTHTOKEN in gateway/.env, or use -LocalOnly.'
    }
    if ($gatewaySettings['NGROK_DOMAIN'] -notmatch '^[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}$') {
        throw 'Set NGROK_DOMAIN in gateway/.env to the hostname only (no https:// or slash).'
    }
}

# Validate all Compose files before changing running services.
Invoke-Docker ($systemCompose + @('config', '--quiet'))
Invoke-Docker ($chatbotCompose + @('config', '--quiet'))
Invoke-Docker ($gatewayCompose + @('--profile', 'tunnel', 'config', '--quiet'))

$existingNetwork = & docker network ls --filter 'name=^oplai_gateway$' --format '{{.Name}}'
if ($LASTEXITCODE -ne 0) { throw 'Unable to list Docker networks.' }
if (-not $existingNetwork) {
    Invoke-Docker @('network', 'create', 'oplai_gateway')
}

# The original chatbot tunnel must release its domain and inspector port.
Invoke-Docker ($chatbotCompose + @('--profile', 'tunnel', 'stop', 'ngrok'))
if ($LocalOnly) {
    Invoke-Docker ($gatewayCompose + @('--profile', 'tunnel', 'stop', 'ngrok'))
}

$upArgs = @('up', '-d')
if ($Build) { $upArgs += '--build' }
Write-Host 'Starting system (web: localhost:3001)...'
Invoke-Docker ($systemCompose + $upArgs)
Write-Host 'Starting chatbot (web: localhost:3000/chatbot)...'
Invoke-Docker ($chatbotCompose + $upArgs)
Write-Host 'Starting shared gateway...'
Invoke-Docker ($gatewayCompose + @('up', '-d', '--wait', '--wait-timeout', '90', 'nginx'))

$gatewayPort = $gatewaySettings['GATEWAY_PORT']
if (-not $gatewayPort) { $gatewayPort = '8080' }
function Wait-Http([string]$Url) {
    $deadline = (Get-Date).AddMinutes(3)
    do {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
            if ($response.StatusCode -eq 200) { return }
        } catch { }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "Not ready: $Url. Run status.ps1 and check the container logs."
}
Wait-Http "http://localhost:$gatewayPort/api/auth/me"
Wait-Http "http://localhost:$gatewayPort/chatbot/api/health/ready"
Write-Host "Local system:  http://localhost:$gatewayPort/"
Write-Host "Local chatbot: http://localhost:$gatewayPort/chatbot"

if (-not $LocalOnly) {
    Invoke-Docker ($gatewayCompose + @('--profile', 'tunnel', 'up', '-d', 'ngrok'))
    $inspectorPort = $gatewaySettings['NGROK_INSPECTOR_PORT']
    if (-not $inspectorPort) { $inspectorPort = '4040' }
    $tunnelReady = $false
    $expectedUrl = "https://$($gatewaySettings['NGROK_DOMAIN'])"
    $tunnelDeadline = (Get-Date).AddSeconds(45)
    do {
        try {
            $tunnels = Invoke-RestMethod -Uri "http://localhost:$inspectorPort/api/tunnels" -TimeoutSec 5
            if (@($tunnels.tunnels | Where-Object { $_.public_url -eq $expectedUrl }).Count -gt 0) {
                $tunnelReady = $true
                break
            }
        } catch { }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $tunnelDeadline)
    if (-not $tunnelReady) {
        throw 'The local apps are ready, but ngrok did not open the domain. Run: docker compose --profile tunnel logs --tail 50 ngrok (in gateway).'
    }
    Write-Host "Public system:  $expectedUrl/"
    Write-Host "Public chatbot: $expectedUrl/chatbot"
    Write-Host "Inspector:      http://localhost:$inspectorPort"
}
