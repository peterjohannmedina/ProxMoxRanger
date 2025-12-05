#!/bin/bash

#############################################################################
# ProxMox Ranger - Upgrade Script
#
# This script upgrades an existing ProxMox Ranger installation to the latest version
#
# Usage: bash upgrade.sh
#        curl -fsSL https://raw.githubusercontent.com/peterjohannmedina/ProxMoxRanger/main/upgrade.sh | bash
#############################################################################

set -e

# Installation paths (must match install.sh)
INSTALL_DIR="/opt/proxmox-ranger"
BIN_DIR="$INSTALL_DIR/bin"
LIB_DIR="$INSTALL_DIR/lib"
ASSETS_DIR="$LIB_DIR/assets"

# Repository
REPO_URL="https://raw.githubusercontent.com/peterjohannmedina/ProxMoxRanger/main"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root"
        exit 1
    fi
}

# Check if ProxMox Ranger is installed
check_installed() {
    if [ ! -d "$INSTALL_DIR" ]; then
        print_error "ProxMox Ranger is not installed at $INSTALL_DIR"
        print_info "Run the full installer instead:"
        print_info "  curl -fsSL ${REPO_URL}/install.sh | bash"
        exit 1
    fi
}

# Get current version
get_current_version() {
    if [ -f "$BIN_DIR/pmranger" ]; then
        grep "version" "$BIN_DIR/pmranger" | grep -o "'[0-9]\.[0-9]\.[0-9]'" | tr -d "'" | head -1 || echo "unknown"
    else
        echo "unknown"
    fi
}

# Backup current installation
backup_current() {
    BACKUP_DIR="$INSTALL_DIR/backup_$(date +%Y%m%d_%H%M%S)"
    print_info "Creating backup at $BACKUP_DIR..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup main script
    if [ -f "$BIN_DIR/pmranger" ]; then
        cp "$BIN_DIR/pmranger" "$BACKUP_DIR/"
    fi
    
    # Backup hotswap-manager
    if [ -f "$BIN_DIR/hotswap-manager" ]; then
        cp "$BIN_DIR/hotswap-manager" "$BACKUP_DIR/"
    fi
    
    print_success "Backup created"
}

# Download and update files
update_files() {
    print_info "Downloading latest version..."
    
    # Update main script
    if curl -fsSL "$REPO_URL/scripts/pmranger.py" -o "$BIN_DIR/pmranger.new"; then
        mv "$BIN_DIR/pmranger.new" "$BIN_DIR/pmranger"
        chmod +x "$BIN_DIR/pmranger"
        print_success "Updated pmranger"
    else
        print_error "Failed to download pmranger.py"
        exit 1
    fi
    
    # Update hotswap-manager
    if curl -fsSL "$REPO_URL/scripts/hotswap-manager.sh" -o "$BIN_DIR/hotswap-manager.new"; then
        mv "$BIN_DIR/hotswap-manager.new" "$BIN_DIR/hotswap-manager"
        chmod +x "$BIN_DIR/hotswap-manager"
        print_success "Updated hotswap-manager"
    else
        print_warning "Failed to download hotswap-manager.sh (may not have changed)"
    fi
    
    # Update assets
    print_info "Updating assets..."
    mkdir -p "$ASSETS_DIR"
    
    for asset in RangerMark.png github-logo-white.png github-mark-white.png; do
        if curl -fsSL "$REPO_URL/assets/$asset" -o "$ASSETS_DIR/$asset.new" 2>/dev/null; then
            mv "$ASSETS_DIR/$asset.new" "$ASSETS_DIR/$asset"
        fi
    done
    print_success "Assets updated"
}

# Restart service
restart_service() {
    print_info "Restarting ProxMox Ranger service..."
    
    if systemctl is-active --quiet proxmox-ranger; then
        systemctl restart proxmox-ranger
        print_success "Service restarted"
    else
        systemctl start proxmox-ranger
        print_success "Service started"
    fi
}

# Get new version
get_new_version() {
    grep "version" "$BIN_DIR/pmranger" | grep -o "'[0-9]\.[0-9]\.[0-9]'" | tr -d "'" | head -1 || echo "unknown"
}

# Main upgrade process
main() {
    echo ""
    echo "=========================================================================="
    echo "  ProxMox Ranger - Upgrade"
    echo "=========================================================================="
    echo ""
    
    check_root
    check_installed
    
    CURRENT_VERSION=$(get_current_version)
    print_info "Current version: $CURRENT_VERSION"
    
    backup_current
    update_files
    restart_service
    
    NEW_VERSION=$(get_new_version)
    
    echo ""
    echo "=========================================================================="
    echo -e "  ${GREEN}Upgrade Complete!${NC}"
    echo "=========================================================================="
    echo ""
    echo "  Previous version: $CURRENT_VERSION"
    echo "  New version:      $NEW_VERSION"
    echo ""
    echo "  Service status: $(systemctl is-active proxmox-ranger)"
    echo ""
    echo "  Access the web UI at: http://$(hostname -I | awk '{print $1}'):8010"
    echo ""
    echo "=========================================================================="
}

main "$@"
