# Deploy WebUI Fix to ProxMox Server
# This script uploads the fixed pmranger.py and restarts the service

param(
    [string]$Server = "192.168.1.233",
    [string]$User = "root"
)

$ErrorActionPreference = "Continue"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "ProxMox Ranger - Deploy WebUI Fix" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server: $Server" -ForegroundColor Yellow
Write-Host "User: $User" -ForegroundColor Yellow
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WebUIScript = Join-Path $ScriptDir "pmranger.py"

# Check if pmranger.py exists
if (-not (Test-Path $WebUIScript)) {
    Write-Host "ERROR: pmranger.py not found at: $WebUIScript" -ForegroundColor Red
    exit 1
}

Write-Host "[1/5] Backing up current pmranger.py on server..." -ForegroundColor Green
$BackupDate = Get-Date -Format "yyyyMMdd_HHmmss"
ssh "${User}@${Server}" "cp /usr/local/bin/pmranger/scripts/pmranger.py /usr/local/bin/pmranger/scripts/pmranger.py.backup-$BackupDate 2>/dev/null || echo 'No existing file to backup'"

Write-Host "[2/5] Uploading fixed pmranger.py to server..." -ForegroundColor Green
scp "$WebUIScript" "${User}@${Server}:/tmp/pmranger.py.new"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to upload pmranger.py to server" -ForegroundColor Red
    Write-Host "Make sure you can SSH to the server: ssh $User@$Server" -ForegroundColor Yellow
    exit 1
}

Write-Host "[3/5] Installing new pmranger.py..." -ForegroundColor Green
ssh "${User}@${Server}" "cp /tmp/pmranger.py.new /usr/local/bin/pmranger/scripts/pmranger.py && chmod +x /usr/local/bin/pmranger/scripts/pmranger.py"

Write-Host "[4/5] Restarting hotswap-pmranger service..." -ForegroundColor Green
ssh "${User}@${Server}" "systemctl restart hotswap-pmranger"

Start-Sleep -Seconds 2

Write-Host "[5/5] Checking service status..." -ForegroundColor Green
Write-Host ""
ssh "${User}@${Server}" "systemctl status hotswap-pmranger --no-pager -l"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Web UI should now be available at:" -ForegroundColor Yellow
Write-Host "  http://${Server}:8010/shares" -ForegroundColor White
Write-Host ""
Write-Host "To view live logs:" -ForegroundColor Cyan
Write-Host "  ssh ${User}@${Server} 'journalctl -u hotswap-pmranger -f'" -ForegroundColor White
Write-Host ""
Write-Host "To rollback if needed:" -ForegroundColor Cyan
Write-Host "  ssh ${User}@${Server}" -ForegroundColor White
Write-Host "  cd /usr/local/bin/pmranger/scripts" -ForegroundColor White
Write-Host "  cp pmranger.py.backup-$BackupDate pmranger.py" -ForegroundColor White
Write-Host "  systemctl restart hotswap-pmranger" -ForegroundColor White
Write-Host ""
