#!/bin/bash

#############################################################################
# ProxMox Ranger Hot-Swap Manager - Installation Script
#
# This script automates the installation of ProxMox Ranger on Proxmox VE
#
# Usage: bash install.sh
#        curl -fsSL https://raw.githubusercontent.com/peterjohannmedina/ProxMoxRanger/main/install.sh | bash
#############################################################################

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Check if running on Proxmox
check_proxmox() {
    if [ ! -f /etc/pve/.version ]; then
        print_warning "This doesn't appear to be a Proxmox VE system"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        local pve_version=$(cat /etc/pve/.version)
        print_info "Detected Proxmox VE version: $pve_version"
    fi
}

# Install system dependencies
install_dependencies() {
    print_info "Installing system dependencies..."

    apt update
    apt install -y python3 python3-pip samba samba-common-bin

    print_success "System dependencies installed"
}

# Install Python dependencies
install_python_deps() {
    print_info "Installing Python dependencies..."

    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        pip3 install -r "$SCRIPT_DIR/requirements.txt"
    else
        pip3 install Flask>=2.3.0
    fi

    print_success "Python dependencies installed"
}

# Copy scripts to system locations
install_scripts() {
    print_info "Installing scripts..."

    # Create directory if needed
    mkdir -p /usr/local/bin/pmranger

    # Copy webui.py
    if [ -f "$SCRIPT_DIR/scripts/webui.py" ]; then
        cp "$SCRIPT_DIR/scripts/webui.py" /usr/local/bin/webui.py
        chmod +x /usr/local/bin/webui.py
        print_success "Installed webui.py"
    else
        print_error "webui.py not found in $SCRIPT_DIR/scripts/"
        exit 1
    fi

    # Copy hotswap-manager.sh
    if [ -f "$SCRIPT_DIR/scripts/hotswap-manager.sh" ]; then
        cp "$SCRIPT_DIR/scripts/hotswap-manager.sh" /usr/local/bin/hotswap-manager.sh
        chmod +x /usr/local/bin/hotswap-manager.sh
        print_success "Installed hotswap-manager.sh"
    else
        print_error "hotswap-manager.sh not found in $SCRIPT_DIR/scripts/"
        exit 1
    fi

    # Copy assets folder (RangerMark.png logo)
    if [ -d "$SCRIPT_DIR/assets" ]; then
        mkdir -p /usr/local/bin/pmranger/assets
        cp -r "$SCRIPT_DIR/assets/"* /usr/local/bin/pmranger/assets/
        print_success "Installed assets folder"
    else
        print_warning "Assets folder not found in $SCRIPT_DIR/assets/"
    fi
}

# Configure Samba
configure_samba() {
    print_info "Configuring Samba for usershares..."

    # Create usershares directory
    mkdir -p /var/lib/samba/usershares

    # Create smbusers group if it doesn't exist
    if ! getent group smbusers > /dev/null 2>&1; then
        groupadd -r smbusers
        print_info "Created smbusers group"
    fi

    # Set permissions
    chgrp smbusers /var/lib/samba/usershares
    chmod 1770 /var/lib/samba/usershares

    # Check if usershare config exists in smb.conf
    if ! grep -q "usershare path" /etc/samba/smb.conf; then
        print_info "Adding usershare configuration to smb.conf..."

        # Backup original config
        cp /etc/samba/smb.conf /etc/samba/smb.conf.backup.$(date +%Y%m%d_%H%M%S)

        # Add usershare configuration
        cat >> /etc/samba/smb.conf << 'EOF'

# ProxMox Ranger Usershare Configuration
usershare path = /var/lib/samba/usershares
usershare max shares = 100
usershare allow guests = yes
usershare owner only = no
EOF

        # Restart Samba
        systemctl restart smbd
        print_success "Samba configured and restarted"
    else
        print_info "Samba usershare already configured"
    fi
}

# Create systemd service
create_service() {
    print_info "Creating systemd service..."

    cat > /etc/systemd/system/hotswap-webui.service << 'EOF'
[Unit]
Description=ProxMox Ranger Hot-Swap Web UI
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/usr/local/bin
ExecStart=/usr/bin/python3 /usr/local/bin/webui.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    print_success "Systemd service created"
}

# Enable and start service
start_service() {
    print_info "Enabling and starting service..."

    systemctl daemon-reload
    systemctl enable hotswap-webui.service
    systemctl start hotswap-webui.service

    # Wait a moment for service to start
    sleep 2

    # Check if service is running
    if systemctl is-active --quiet hotswap-webui.service; then
        print_success "Service started successfully"
    else
        print_error "Service failed to start. Check logs with: journalctl -u hotswap-webui.service -n 50"
        exit 1
    fi
}

# Get server IP address
get_server_ip() {
    # Try to get the primary IP address
    local ip=$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+')

    if [ -z "$ip" ]; then
        # Fallback to hostname -I
        ip=$(hostname -I | awk '{print $1}')
    fi

    echo "$ip"
}

# Print completion message
print_completion() {
    local server_ip=$(get_server_ip)

    echo ""
    echo "=========================================================================="
    print_success "ProxMox Ranger Hot-Swap Manager installed successfully!"
    echo "=========================================================================="
    echo ""
    echo "Access the web interface at:"
    echo -e "  ${GREEN}http://$server_ip:8007${NC}"
    echo ""
    echo "Service management:"
    echo "  Status:  systemctl status hotswap-webui.service"
    echo "  Stop:    systemctl stop hotswap-webui.service"
    echo "  Start:   systemctl start hotswap-webui.service"
    echo "  Restart: systemctl restart hotswap-webui.service"
    echo ""
    echo "Logs:"
    echo "  Service: journalctl -u hotswap-webui.service -f"
    echo "  App:     tail -f /var/log/hotswap-webui.log"
    echo ""
    echo "Configuration file: /usr/local/bin/webui.py"
    echo ""
    print_warning "Default installation uses HTTP (not HTTPS)"
    print_warning "IP whitelisting is enabled - see INSTALL.md for configuration"
    echo ""
    echo "For detailed documentation, see:"
    echo "  https://github.com/peterjohannmedina/ProxMoxRanger"
    echo "=========================================================================="
}

# Main installation flow
main() {
    echo ""
    echo "=========================================================================="
    echo "  ProxMox Ranger Hot-Swap Manager - Installation"
    echo "=========================================================================="
    echo ""

    check_root
    check_proxmox

    print_info "Starting installation..."
    echo ""

    install_dependencies
    install_python_deps
    install_scripts
    configure_samba
    create_service
    start_service

    print_completion
}

# Run main function
main "$@"
