# ProxMox Ranger - Remote Diagnostic Runner
# This script uploads and runs the mount diagnostic tool on the remote server

param(
    [string]$Server = "192.168.1.233",
    [string]$User = "root"
)

$ErrorActionPreference = "Stop"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "ProxMox Ranger - Remote Mount Diagnostic" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server: $Server" -ForegroundColor Yellow
Write-Host "User: $User" -ForegroundColor Yellow
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DiagnosticScript = Join-Path $ScriptDir "diagnose-mount-issues.sh"

# Check if diagnostic script exists
if (-not (Test-Path $DiagnosticScript)) {
    Write-Host "ERROR: Diagnostic script not found at: $DiagnosticScript" -ForegroundColor Red
    exit 1
}

Write-Host "[1/3] Uploading diagnostic script to server..." -ForegroundColor Green

# Upload the script to the server
scp "$DiagnosticScript" "${User}@${Server}:/tmp/diagnose-mount-issues.sh"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to upload script to server" -ForegroundColor Red
    Write-Host "Make sure you can SSH to the server: ssh $User@$Server" -ForegroundColor Yellow
    exit 1
}

Write-Host "[2/3] Making script executable..." -ForegroundColor Green
ssh "${User}@${Server}" "chmod +x /tmp/diagnose-mount-issues.sh"

Write-Host "[3/3] Running diagnostic (this may take a minute)..." -ForegroundColor Green
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Run the diagnostic script
ssh "${User}@${Server}" "bash /tmp/diagnose-mount-issues.sh"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Diagnostic complete!" -ForegroundColor Green
Write-Host ""
Write-Host "The full log has been saved on the server at:" -ForegroundColor Yellow
ssh "${User}@${Server}" "ls -t /tmp/mount-diagnostic-*.log | head -1"
Write-Host ""
Write-Host "To download the log file:" -ForegroundColor Cyan
$LogFile = ssh "${User}@${Server}" "ls -t /tmp/mount-diagnostic-*.log | head -1" | Out-String
$LogFile = $LogFile.Trim()
if ($LogFile) {
    Write-Host "  scp ${User}@${Server}:${LogFile} ." -ForegroundColor White
}
Write-Host ""
