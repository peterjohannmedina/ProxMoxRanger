# Deploy WebUI Fix to ProxMox Server
# This script uploads the fixed webui.py and restarts the service

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
$WebUIScript = Join-Path $ScriptDir "webui.py"

# Check if webui.py exists
if (-not (Test-Path $WebUIScript)) {
    Write-Host "ERROR: webui.py not found at: $WebUIScript" -ForegroundColor Red
    exit 1
}

Write-Host "[1/5] Backing up current webui.py on server..." -ForegroundColor Green
$BackupDate = Get-Date -Format "yyyyMMdd_HHmmss"
ssh "${User}@${Server}" "cp /usr/local/bin/pmranger/scripts/webui.py /usr/local/bin/pmranger/scripts/webui.py.backup-$BackupDate 2>/dev/null || echo 'No existing file to backup'"

Write-Host "[2/5] Uploading fixed webui.py to server..." -ForegroundColor Green
scp "$WebUIScript" "${User}@${Server}:/tmp/webui.py.new"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to upload webui.py to server" -ForegroundColor Red
    Write-Host "Make sure you can SSH to the server: ssh $User@$Server" -ForegroundColor Yellow
    exit 1
}

Write-Host "[3/5] Installing new webui.py..." -ForegroundColor Green
ssh "${User}@${Server}" "cp /tmp/webui.py.new /usr/local/bin/pmranger/scripts/webui.py && chmod +x /usr/local/bin/pmranger/scripts/webui.py"

Write-Host "[4/5] Restarting hotswap-webui service..." -ForegroundColor Green
ssh "${User}@${Server}" "systemctl restart hotswap-webui"

Start-Sleep -Seconds 2

Write-Host "[5/5] Checking service status..." -ForegroundColor Green
Write-Host ""
ssh "${User}@${Server}" "systemctl status hotswap-webui --no-pager -l"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Web UI should now be available at:" -ForegroundColor Yellow
Write-Host "  http://${Server}:8010/shares" -ForegroundColor White
Write-Host ""
Write-Host "To view live logs:" -ForegroundColor Cyan
Write-Host "  ssh ${User}@${Server} 'journalctl -u hotswap-webui -f'" -ForegroundColor White
Write-Host ""
Write-Host "To rollback if needed:" -ForegroundColor Cyan
Write-Host "  ssh ${User}@${Server}" -ForegroundColor White
Write-Host "  cd /usr/local/bin/pmranger/scripts" -ForegroundColor White
Write-Host "  cp webui.py.backup-$BackupDate webui.py" -ForegroundColor White
Write-Host "  systemctl restart hotswap-webui" -ForegroundColor White
Write-Host ""
