# Run after start.ps1. This never writes password hashes to the terminal or host.
. (Join-Path $PSScriptRoot 'common.ps1')
Assert-Docker

$accounts = & docker exec chatbot-v42-backend-1 python -m app.export_system_users
if ($LASTEXITCODE -ne 0) { throw 'Unable to read chatbot accounts. Start both apps first.' }
$oldOutputEncoding = $OutputEncoding
try {
    $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $result = $accounts | & docker exec -i olp_ai_kma_backend python -m app.import_chatbot_users
    if ($LASTEXITCODE -ne 0) { throw 'Account import failed. Existing accounts were preserved.' }
} finally {
    $OutputEncoding = $oldOutputEncoding
    $accounts = $null
}
$report = $result | ConvertFrom-Json
Write-Host "Created: $(@($report.created).Count); preserved existing: $(@($report.skipped_existing).Count)."
Write-Host "System database backup: $($report.backup) (inside backend data volume)."
if (@($report.created).Count) {
    $report.created | Format-Table email, username, role
}
