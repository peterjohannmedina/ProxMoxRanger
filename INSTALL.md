# ProxMox Ranger Hot-Swap Manager - Installation Guide

## Overview
ProxMox Ranger Hot-Swap Manager is a web-based management interface for handling hot-swappable storage devices in Proxmox VE environments. It provides an intuitive interface for mounting/unmounting devices, managing Samba shares, and monitoring storage usage.

## Prerequisites

- Proxmox VE 7.0 or higher
- Python 3.7 or higher (included in Proxmox VE by default)
- Root or sudo access to the Proxmox node
- Network access to the Proxmox management interface

## Quick Installation

Run the following one-liner to install ProxMox Ranger:

```bash
curl -fsSL https://raw.githubusercontent.com/peterjohannmedina/ProxMoxRanger/main/install.sh | bash
```

Or for manual installation, follow the steps below.

## Manual Installation

### Step 1: Install Dependencies

```bash
apt update
apt install -y python3 python3-pip python3-venv samba samba-common-bin
```

### Step 2: Create Directory Structure and Virtual Environment

```bash
# Create installation directory structure
mkdir -p /opt/proxmox-ranger/bin
mkdir -p /opt/proxmox-ranger/lib/assets

# Create Python virtual environment
python3 -m venv /opt/proxmox-ranger/venv

# Install Python dependencies in venv
/opt/proxmox-ranger/venv/bin/pip install -r requirements.txt
```

### Step 3: Copy Scripts and Assets

```bash
# Copy webui script (without extension)
cp scripts/webui.py /opt/proxmox-ranger/bin/webui
chmod +x /opt/proxmox-ranger/bin/webui

# Copy hotswap manager script (without extension)
cp scripts/hotswap-manager.sh /opt/proxmox-ranger/bin/hotswap-manager
chmod +x /opt/proxmox-ranger/bin/hotswap-manager

# Copy assets
cp -r assets/* /opt/proxmox-ranger/lib/assets/

# Create convenience symlinks
ln -s /opt/proxmox-ranger/bin/webui /usr/local/bin/pmranger
ln -s /opt/proxmox-ranger/bin/hotswap-manager /usr/local/bin/pmranger-cli
```

### Step 4: Create Systemd Service

Create the service file at `/etc/systemd/system/proxmox-ranger.service`:

```ini
[Unit]
Description=ProxMox Ranger - Hot-Swap Storage Manager
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/proxmox-ranger
ExecStart=/opt/proxmox-ranger/venv/bin/python3 /opt/proxmox-ranger/bin/webui
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Step 5: Enable and Start Service

```bash
systemctl daemon-reload
systemctl enable --now proxmox-ranger.service
```

### Step 6: Verify Installation

Check service status:
```bash
systemctl status proxmox-ranger.service
```

The web interface should now be accessible at:
```
http://YOUR_PROXMOX_IP:8008
```

## Configuration

### IP Whitelist

By default, the web UI is accessible from:
- Localhost (127.0.0.1, ::1)
- Private network ranges (192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12)

To modify allowed IPs, edit `/opt/proxmox-ranger/bin/webui` and update the `ALLOWED_IPS` list around line 19:

```python
ALLOWED_IPS = [
    '127.0.0.1',
    '192.168.0.0/24',  # Your custom network (adjust as needed)
]
```

After making changes, restart the service:
```bash
systemctl restart proxmox-ranger.service
```

### Samba Configuration

Ensure Samba is configured for user share management:

```bash
# Enable usershares
mkdir -p /var/lib/samba/usershares
groupadd -r smbusers
chgrp smbusers /var/lib/samba/usershares
chmod 1770 /var/lib/samba/usershares
```

Add to `/etc/samba/smb.conf` under `[global]`:
```ini
usershare path = /var/lib/samba/usershares
usershare max shares = 100
usershare allow guests = yes
usershare owner only = no
```

Restart Samba:
```bash
systemctl restart smbd
```

## Usage

### Accessing the Web UI

Navigate to `http://YOUR_PROXMOX_IP:8008` in your web browser.

### Managing Devices

1. **View Devices**: The main page displays all block devices with their mount status
2. **Mount Device**: Click "Mount" next to an unmounted device
3. **Unmount Device**: Click "Unmount" next to a mounted device
4. **Create Share**: Click "Share" to create a Samba share for a mounted device

### Logs

View service logs:
```bash
journalctl -u proxmox-ranger.service -f
```

Application logs:
```bash
tail -f /var/log/proxmox-ranger.log
```

## Troubleshooting

### Service Won't Start

Check logs:
```bash
journalctl -u proxmox-ranger.service -n 50
```

Verify Python dependencies:
```bash
pip3 list | grep -i flask
```

### Can't Access Web UI

1. Check firewall:
```bash
iptables -L -n | grep 8008
```

2. Verify service is listening:
```bash
netstat -tulpn | grep 8008
```

3. Check IP whitelist in `/opt/proxmox-ranger/bin/webui`

### Mount/Unmount Failures

Check hotswap-manager permissions:
```bash
ls -l /opt/proxmox-ranger/bin/hotswap-manager
```

View detailed error logs:
```bash
tail -f /var/log/proxmox-ranger.log
```

## Uninstallation

To cleanly uninstall ProxMox Ranger, use the uninstall script:

```bash
bash uninstall.sh
```

Or manually:

```bash
# Stop and disable service
systemctl stop proxmox-ranger.service
systemctl disable proxmox-ranger.service

# Remove files
rm /etc/systemd/system/proxmox-ranger.service
rm -rf /opt/proxmox-ranger

# Remove symlinks
rm /usr/local/bin/pmranger
rm /usr/local/bin/pmranger-cli

# Reload systemd
systemctl daemon-reload
```

## Security Considerations

- The web UI runs on port 8008 by default (non-HTTPS)
- IP whitelisting is enforced by default
- Running as root provides full system access
- Consider using a reverse proxy (nginx/apache) with SSL for production
- Restrict access to trusted networks only

## Support

For issues, feature requests, or contributions, please visit:
https://github.com/peterjohannmedina/ProxMoxRanger
