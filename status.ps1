. (Join-Path $PSScriptRoot 'common.ps1')
Assert-Docker
Write-Host 'SYSTEM'
Invoke-Docker ($systemCompose + @('ps', '-a'))
Write-Host 'CHATBOT'
Invoke-Docker ($chatbotCompose + @('--profile', 'tunnel', 'ps', '-a'))
Write-Host 'GATEWAY'
Invoke-Docker ($gatewayCompose + @('--profile', 'tunnel', 'ps', '-a'))
