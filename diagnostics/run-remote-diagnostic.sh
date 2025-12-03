#!/bin/bash

# ProxMox Ranger - Remote Diagnostic Runner
# This script uploads and runs the mount diagnostic tool on the remote server

SERVER="${1:-192.168.1.233}"
USER="${2:-root}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}ProxMox Ranger - Remote Mount Diagnostic${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""
echo -e "${YELLOW}Server: $SERVER${NC}"
echo -e "${YELLOW}User: $USER${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIAGNOSTIC_SCRIPT="$SCRIPT_DIR/diagnose-mount-issues.sh"

# Check if diagnostic script exists
if [ ! -f "$DIAGNOSTIC_SCRIPT" ]; then
    echo -e "${RED}ERROR: Diagnostic script not found at: $DIAGNOSTIC_SCRIPT${NC}"
    exit 1
fi

echo -e "${GREEN}[1/3] Uploading diagnostic script to server...${NC}"

# Upload the script to the server
if ! scp "$DIAGNOSTIC_SCRIPT" "${USER}@${SERVER}:/tmp/diagnose-mount-issues.sh"; then
    echo -e "${RED}ERROR: Failed to upload script to server${NC}"
    echo -e "${YELLOW}Make sure you can SSH to the server: ssh $USER@$SERVER${NC}"
    exit 1
fi

echo -e "${GREEN}[2/3] Making script executable...${NC}"
ssh "${USER}@${SERVER}" "chmod +x /tmp/diagnose-mount-issues.sh"

echo -e "${GREEN}[3/3] Running diagnostic (this may take a minute)...${NC}"
echo ""
echo -e "${CYAN}================================================${NC}"
echo ""

# Run the diagnostic script
ssh "${USER}@${SERVER}" "bash /tmp/diagnose-mount-issues.sh"

echo ""
echo -e "${CYAN}================================================${NC}"
echo -e "${GREEN}Diagnostic complete!${NC}"
echo ""
echo -e "${YELLOW}The full log has been saved on the server at:${NC}"
LOGFILE=$(ssh "${USER}@${SERVER}" "ls -t /tmp/mount-diagnostic-*.log 2>/dev/null | head -1")
echo "$LOGFILE"
echo ""
if [ -n "$LOGFILE" ]; then
    echo -e "${CYAN}To download the log file:${NC}"
    echo "  scp ${USER}@${SERVER}:${LOGFILE} ."
    echo ""
fi
