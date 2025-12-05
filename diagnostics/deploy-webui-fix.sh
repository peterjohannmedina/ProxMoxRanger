#!/bin/bash

# Deploy WebUI Fix to ProxMox Server
# This script uploads the fixed pmranger.py and restarts the service

SERVER="${1:-192.168.1.233}"
USER="${2:-root}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}ProxMox Ranger - Deploy WebUI Fix${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""
echo -e "${YELLOW}Server: $SERVER${NC}"
echo -e "${YELLOW}User: $USER${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBUI_SCRIPT="$SCRIPT_DIR/pmranger.py"

# Check if pmranger.py exists
if [ ! -f "$WEBUI_SCRIPT" ]; then
    echo -e "${RED}ERROR: pmranger.py not found at: $WEBUI_SCRIPT${NC}"
    exit 1
fi

echo -e "${GREEN}[1/5] Backing up current pmranger.py on server...${NC}"
ssh "${USER}@${SERVER}" "cp /usr/local/bin/pmranger/scripts/pmranger.py /usr/local/bin/pmranger/scripts/pmranger.py.backup-\$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo 'No existing file to backup'"

echo -e "${GREEN}[2/5] Uploading fixed pmranger.py to server...${NC}"
if ! scp "$WEBUI_SCRIPT" "${USER}@${SERVER}:/tmp/pmranger.py.new"; then
    echo -e "${RED}ERROR: Failed to upload pmranger.py to server${NC}"
    echo -e "${YELLOW}Make sure you can SSH to the server: ssh $USER@$SERVER${NC}"
    exit 1
fi

echo -e "${GREEN}[3/5] Installing new pmranger.py...${NC}"
ssh "${USER}@${SERVER}" "cp /tmp/pmranger.py.new /usr/local/bin/pmranger/scripts/pmranger.py && chmod +x /usr/local/bin/pmranger/scripts/pmranger.py"

echo -e "${GREEN}[4/5] Restarting hotswap-pmranger service...${NC}"
ssh "${USER}@${SERVER}" "systemctl restart hotswap-pmranger"

sleep 2

echo -e "${GREEN}[5/5] Checking service status...${NC}"
echo ""
ssh "${USER}@${SERVER}" "systemctl status hotswap-pmranger --no-pager -l" || true

echo ""
echo -e "${CYAN}================================================${NC}"
echo -e "${GREEN}Deployment complete!${NC}"
echo ""
echo -e "${YELLOW}Web UI should now be available at:${NC}"
echo -e "  http://${SERVER}:8010/shares"
echo ""
echo -e "${CYAN}To view live logs:${NC}"
echo "  ssh ${USER}@${SERVER} 'journalctl -u hotswap-pmranger -f'"
echo ""
echo -e "${CYAN}To rollback if needed:${NC}"
echo "  ssh ${USER}@${SERVER}"
echo "  cd /usr/local/bin/pmranger/scripts"
echo "  cp pmranger.py.backup-YYYYMMDD_HHMMSS pmranger.py"
echo "  systemctl restart hotswap-pmranger"
echo ""
