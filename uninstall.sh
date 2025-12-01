#!/bin/bash

#############################################################################
# ProxMox Ranger Hot-Swap Manager - Uninstallation Script
#
# This script removes ProxMox Ranger from your Proxmox VE system
#
# Usage: bash uninstall.sh
#############################################################################

set -e  # Exit on any error

# Installation paths
INSTALL_DIR="/opt/proxmox-ranger"
SERVICE_NAME="proxmox-ranger.service"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root"
        exit 1
    fi
}

# Confirm uninstallation
confirm_uninstall() {
    echo ""
    echo "=========================================================================="
    echo "  ProxMox Ranger - Uninstallation"
    echo "=========================================================================="
    echo ""
    print_warning "This will remove ProxMox Ranger from your system"
    echo ""
    echo "The following will be removed:"
    echo "  - Service: $SERVICE_NAME"
    echo "  - Installation directory: $INSTALL_DIR"
    echo "  - Symlinks: /usr/local/bin/pmranger, /usr/local/bin/pmranger-cli"
    echo ""
    echo "The following will NOT be removed (optional removal at end):"
    echo "  - Samba configuration"
    echo "  - Log files in /var/log/"
    echo "  - Mounted devices and shares"
    echo ""
    read -p "Continue with uninstallation? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Uninstallation cancelled"
        exit 0
    fi
}

# Stop and disable service
stop_service() {
    print_info "Stopping and disabling service..."

    if systemctl is-active --quiet $SERVICE_NAME; then
        systemctl stop $SERVICE_NAME
        print_success "Service stopped"
    else
        print_info "Service not running"
    fi

    if systemctl is-enabled --quiet $SERVICE_NAME 2>/dev/null; then
        systemctl disable $SERVICE_NAME
        print_success "Service disabled"
    fi
}

# Remove service file
remove_service() {
    print_info "Removing systemd service..."

    if [ -f "/etc/systemd/system/$SERVICE_NAME" ]; then
        rm "/etc/systemd/system/$SERVICE_NAME"
        systemctl daemon-reload
        print_success "Service file removed"
    else
        print_info "Service file not found"
    fi
}

# Remove symlinks
remove_symlinks() {
    print_info "Removing symlinks..."

    if [ -L "/usr/local/bin/pmranger" ]; then
        rm "/usr/local/bin/pmranger"
        print_success "Removed /usr/local/bin/pmranger"
    fi

    if [ -L "/usr/local/bin/pmranger-cli" ]; then
        rm "/usr/local/bin/pmranger-cli"
        print_success "Removed /usr/local/bin/pmranger-cli"
    fi
}

# Remove installation directory
remove_install_dir() {
    print_info "Removing installation directory..."

    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
        print_success "Removed $INSTALL_DIR"
    else
        print_info "Installation directory not found"
    fi
}

# Optional: Remove Samba configuration
remove_samba_config() {
    echo ""
    read -p "Remove Samba usershare configuration? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Removing Samba configuration..."

        # Remove usershare configuration from smb.conf
        if grep -q "# ProxMox Ranger Usershare Configuration" /etc/samba/smb.conf; then
            sed -i '/# ProxMox Ranger Usershare Configuration/,/usershare owner only/d' /etc/samba/smb.conf
            systemctl restart smbd
            print_success "Samba configuration removed"
        else
            print_info "Samba configuration not found"
        fi

        # Remove usershares directory (this will delete all shares!)
        read -p "Remove all usershares directory (DELETES ALL SHARES!)? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [ -d "/var/lib/samba/usershares" ]; then
                rm -rf /var/lib/samba/usershares
                print_success "Usershares directory removed"
            fi
        fi
    fi
}

# Optional: Remove log files
remove_logs() {
    echo ""
    read -p "Remove log files? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Removing log files..."

        if [ -f "/var/log/proxmox-ranger.log" ]; then
            rm "/var/log/proxmox-ranger.log"
            print_success "Removed /var/log/proxmox-ranger.log"
        fi

        if [ -f "/var/log/hotswap-manager.log" ]; then
            rm "/var/log/hotswap-manager.log"
            print_success "Removed /var/log/hotswap-manager.log"
        fi

        # Remove old log files if they exist
        if [ -f "/var/log/hotswap-webui.log" ]; then
            rm "/var/log/hotswap-webui.log"
            print_success "Removed /var/log/hotswap-webui.log"
        fi
    fi
}

# Print completion message
print_completion() {
    echo ""
    echo "=========================================================================="
    print_success "ProxMox Ranger has been uninstalled"
    echo "=========================================================================="
    echo ""
    print_info "Mounted devices and active shares have NOT been unmounted"
    print_info "Use 'pmranger-cli' commands before uninstalling if you need to clean up shares"
    echo ""
    echo "To reinstall, run:"
    echo "  curl -fsSL https://raw.githubusercontent.com/peterjohannmedina/ProxMoxRanger/main/install.sh | bash"
    echo "=========================================================================="
}

# Main uninstallation flow
main() {
    check_root
    confirm_uninstall

    print_info "Starting uninstallation..."
    echo ""

    stop_service
    remove_service
    remove_symlinks
    remove_install_dir

    # Optional removals
    remove_samba_config
    remove_logs

    print_completion
}

# Run main function
main "$@"
