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
apt install -y python3-pip samba
pip3 install -r requirements.txt
```

### Step 2: Copy Scripts

```bash
# Create installation directory
mkdir -p /usr/local/bin/pmranger

# Copy webui script
cp scripts/webui.py /usr/local/bin/webui.py
chmod +x /usr/local/bin/webui.py

# Copy hotswap manager script
cp scripts/hotswap-manager.sh /usr/local/bin/hotswap-manager.sh
chmod +x /usr/local/bin/hotswap-manager.sh
```

### Step 3: Create Systemd Service

Create the service file at `/etc/systemd/system/hotswap-webui.service`:

```ini
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

[Install]
WantedBy=multi-user.target
```

### Step 4: Enable and Start Service

```bash
systemctl daemon-reload
systemctl enable hotswap-webui.service
systemctl start hotswap-webui.service
```

### Step 5: Verify Installation

Check service status:
```bash
systemctl status hotswap-webui.service
```

The web interface should now be accessible at:
```
http://YOUR_PROXMOX_IP:8007
```

## Configuration

### IP Whitelist

By default, the web UI is accessible from:
- Localhost (127.0.0.1, ::1)
- Private network ranges (192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12)

To modify allowed IPs, edit `/usr/local/bin/webui.py` and update the `ALLOWED_IPS` list around line 19:

```python
ALLOWED_IPS = [
    '127.0.0.1',
    '192.168.0.0/24',  # Your custom network (adjust as needed)
]
```

After making changes, restart the service:
```bash
systemctl restart hotswap-webui.service
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

Navigate to `http://YOUR_PROXMOX_IP:8007` in your web browser.

### Managing Devices

1. **View Devices**: The main page displays all block devices with their mount status
2. **Mount Device**: Click "Mount" next to an unmounted device
3. **Unmount Device**: Click "Unmount" next to a mounted device
4. **Create Share**: Click "Share" to create a Samba share for a mounted device

### Logs

View service logs:
```bash
journalctl -u hotswap-webui.service -f
```

Application logs:
```bash
tail -f /var/log/hotswap-webui.log
```

## Troubleshooting

### Service Won't Start

Check logs:
```bash
journalctl -u hotswap-webui.service -n 50
```

Verify Python dependencies:
```bash
pip3 list | grep -i flask
```

### Can't Access Web UI

1. Check firewall:
```bash
iptables -L -n | grep 8007
```

2. Verify service is listening:
```bash
netstat -tulpn | grep 8007
```

3. Check IP whitelist in webui.py

### Mount/Unmount Failures

Check hotswap-manager.sh permissions:
```bash
ls -l /usr/local/bin/hotswap-manager.sh
```

View detailed error logs:
```bash
tail -f /var/log/hotswap-webui.log
```

## Uninstallation

```bash
# Stop and disable service
systemctl stop hotswap-webui.service
systemctl disable hotswap-webui.service

# Remove files
rm /etc/systemd/system/hotswap-webui.service
rm /usr/local/bin/webui.py
rm /usr/local/bin/hotswap-manager.sh
rm -rf /usr/local/bin/pmranger

# Reload systemd
systemctl daemon-reload
```

## Security Considerations

- The web UI runs on port 8007 by default (non-HTTPS)
- IP whitelisting is enforced by default
- Running as root provides full system access
- Consider using a reverse proxy (nginx/apache) with SSL for production
- Restrict access to trusted networks only

## Support

For issues, feature requests, or contributions, please visit:
https://github.com/peterjohannmedina/ProxMoxRanger
