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

# Installation paths
INSTALL_DIR="/opt/proxmox-ranger"
BIN_DIR="$INSTALL_DIR/bin"
LIB_DIR="$INSTALL_DIR/lib"
ASSETS_DIR="$LIB_DIR/assets"
VENV_DIR="$INSTALL_DIR/venv"

# Service configuration
SERVICE_NAME="proxmox-ranger.service"
WEB_PORT=8010  # Default port (changed from 8008 to avoid conflicts with ProxMenux)

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

        # Check if running in interactive mode
        if [ ! -t 0 ]; then
            print_warning "Non-interactive mode - skipping confirmation"
            print_info "Continuing installation on non-Proxmox system..."
        else
            # Interactive mode with timeout
            if read -t 20 -p "Continue anyway? (y/N): " -n 1 -r; then
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    exit 1
                fi
            else
                echo
                print_warning "No response received - aborting installation"
                exit 1
            fi
        fi
    else
        local pve_version=$(cat /etc/pve/.version)
        print_info "Detected Proxmox VE version: $pve_version"
    fi
}

# Prompt for port selection
prompt_port_selection() {
    echo ""
    print_info "Port Configuration"
    echo "  Default port: $WEB_PORT"
    echo "  Note: Port 8008 is used by ProxMenux and other services"
    echo ""

    # Check if running in interactive mode (stdin is a terminal AND stdout is a terminal)
    if [ ! -t 0 ] || [ ! -t 1 ]; then
        print_warning "Non-interactive mode detected (piped installation)"
        print_info "Using default port: $WEB_PORT"
        echo ""
        return
    fi

    # Check if running from curl pipe by testing if we can read
    if ! exec 0</dev/tty 2>/dev/null; then
        print_warning "Cannot access terminal for input"
        print_info "Using default port: $WEB_PORT"
        echo ""
        return
    fi

    # Interactive mode with 20-second countdown
    print_info "You have 20 seconds to respond..."
    echo -n "Use default port $WEB_PORT? (Y/n): "

    # Read with timeout and error handling
    if read -t 20 -n 1 -r REPLY 2>/dev/null; then
        echo

        if [[ $REPLY =~ ^[Nn]$ ]]; then
            while true; do
                echo -n "Enter custom port (1024-65535): "
                if read -r CUSTOM_PORT 2>/dev/null; then
                    if [[ "$CUSTOM_PORT" =~ ^[0-9]+$ ]] && [ "$CUSTOM_PORT" -ge 1024 ] && [ "$CUSTOM_PORT" -le 65535 ]; then
                        WEB_PORT=$CUSTOM_PORT
                        print_success "Using custom port: $WEB_PORT"
                        break
                    else
                        print_error "Invalid port. Please enter a number between 1024 and 65535"
                    fi
                else
                    print_warning "Read failed - using default port: $WEB_PORT"
                    break
                fi
            done
        else
            print_info "Using default port: $WEB_PORT"
        fi
    else
        # Timeout or read failed - use default
        echo
        print_warning "No response received - using default port: $WEB_PORT"
    fi
    echo ""
}

# Check if port is available
check_port() {
    print_info "Checking if port $WEB_PORT is available..."

    if ss -tlnp 2>/dev/null | grep -q ":$WEB_PORT " || netstat -tlnp 2>/dev/null | grep -q ":$WEB_PORT "; then
        print_warning "Port $WEB_PORT is already in use"
        print_warning "Please free the port or change PORT in $BIN_DIR/webui after installation"

        # Check if running in interactive mode
        if [ ! -t 0 ]; then
            print_warning "Non-interactive mode - continuing with port $WEB_PORT"
            print_info "You may need to manually change the port in $BIN_DIR/webui"
        else
            # Interactive mode with timeout
            if read -t 20 -p "Continue anyway? (y/N): " -n 1 -r; then
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    exit 1
                fi
            else
                echo
                print_warning "No response received - aborting installation"
                exit 1
            fi
        fi
    else
        print_success "Port $WEB_PORT is available"
    fi
}

# Install system dependencies
install_dependencies() {
    print_info "Installing system dependencies..."

    apt update
    apt install -y python3 python3-pip python3-venv samba samba-common-bin

    print_success "System dependencies installed"
}

# Create directory structure
create_directories() {
    print_info "Creating directory structure..."

    mkdir -p "$BIN_DIR"
    mkdir -p "$LIB_DIR"
    mkdir -p "$ASSETS_DIR"

    print_success "Directory structure created"
}

# Create virtual environment and install Python dependencies
setup_venv() {
    print_info "Creating Python virtual environment..."

    python3 -m venv "$VENV_DIR"

    print_success "Virtual environment created"

    print_info "Installing Python dependencies..."

    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        "$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
    else
        "$VENV_DIR/bin/pip" install Flask>=2.3.0
    fi

    print_success "Python dependencies installed in venv"
}

# Install scripts
install_scripts() {
    print_info "Installing scripts..."

    # Copy webui.py and rename without extension
    if [ -f "$SCRIPT_DIR/scripts/webui.py" ]; then
        cp "$SCRIPT_DIR/scripts/webui.py" "$BIN_DIR/webui"
        chmod +x "$BIN_DIR/webui"
        print_success "Installed webui"
    else
        print_error "webui.py not found in $SCRIPT_DIR/scripts/"
        exit 1
    fi

    # Copy hotswap-manager.sh and rename without extension
    if [ -f "$SCRIPT_DIR/scripts/hotswap-manager.sh" ]; then
        cp "$SCRIPT_DIR/scripts/hotswap-manager.sh" "$BIN_DIR/hotswap-manager"
        chmod +x "$BIN_DIR/hotswap-manager"
        print_success "Installed hotswap-manager"
    else
        print_error "hotswap-manager.sh not found in $SCRIPT_DIR/scripts/"
        exit 1
    fi

    # Copy assets folder
    if [ -d "$SCRIPT_DIR/assets" ]; then
        cp -r "$SCRIPT_DIR/assets/"* "$ASSETS_DIR/"
        print_success "Installed assets"
    else
        print_warning "Assets folder not found in $SCRIPT_DIR/assets/"
    fi
}

# Create symlinks for convenience
create_symlinks() {
    print_info "Creating convenience symlinks..."

    # Create symlink for web UI
    if [ -L /usr/local/bin/pmranger ]; then
        rm /usr/local/bin/pmranger
    fi
    ln -s "$BIN_DIR/webui" /usr/local/bin/pmranger

    # Create symlink for CLI manager
    if [ -L /usr/local/bin/pmranger-cli ]; then
        rm /usr/local/bin/pmranger-cli
    fi
    ln -s "$BIN_DIR/hotswap-manager" /usr/local/bin/pmranger-cli

    print_success "Symlinks created: pmranger, pmranger-cli"
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

    cat > /etc/systemd/system/$SERVICE_NAME << EOF
[Unit]
Description=ProxMox Ranger - Hot-Swap Storage Manager
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python3 $BIN_DIR/webui
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
    systemctl enable --now $SERVICE_NAME

    # Wait a moment for service to start
    sleep 2

    # Check if service is running
    if systemctl is-active --quiet $SERVICE_NAME; then
        print_success "Service started successfully"
    else
        print_error "Service failed to start. Check logs with: journalctl -u $SERVICE_NAME -n 50"
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
    echo -e "  ${GREEN}http://$server_ip:$WEB_PORT${NC}"
    echo ""
    echo "Installation directory: $INSTALL_DIR"
    echo ""
    echo "Service management:"
    echo "  Status:  systemctl status $SERVICE_NAME"
    echo "  Stop:    systemctl stop $SERVICE_NAME"
    echo "  Start:   systemctl start $SERVICE_NAME"
    echo "  Restart: systemctl restart $SERVICE_NAME"
    echo ""
    echo "Logs:"
    echo "  Service: journalctl -u $SERVICE_NAME -f"
    echo "  App:     tail -f /var/log/proxmox-ranger.log"
    echo ""
    echo "Command shortcuts:"
    echo "  Web UI:  pmranger"
    echo "  CLI:     pmranger-cli"
    echo ""
    echo "Configuration: $BIN_DIR/webui"
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
    prompt_port_selection
    check_port

    print_info "Starting installation..."
    echo ""

    install_dependencies
    create_directories
    setup_venv
    install_scripts
    create_symlinks
    configure_samba
    create_service
    start_service

    print_completion
}

# Run main function
main "$@"
