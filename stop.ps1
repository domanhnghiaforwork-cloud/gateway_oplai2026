. (Join-Path $PSScriptRoot 'common.ps1')
Assert-Docker
Invoke-Docker ($gatewayCompose + @('--profile', 'tunnel', 'stop'))
Invoke-Docker ($chatbotCompose + @('--profile', 'tunnel', 'stop'))
Invoke-Docker ($systemCompose + @('stop'))
Write-Host 'Stopped both projects and the gateway. Containers and data volumes are retained.'
