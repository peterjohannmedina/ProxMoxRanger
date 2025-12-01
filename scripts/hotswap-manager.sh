#!/bin/bash

# Hot-Swap Manager Script for Proxmox Nodes
# Usage: ./hotswap-manager.sh [setup|list|mount|unmount|format|cleanup|webui] [args...]

ACTION=$1
PARAM=$2

LOGFILE="/var/log/hotswap-manager.log"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*" >> "$LOGFILE"
}

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "✗ This script must be run as root"
        log "ERROR: Script not run as root"
        exit 1
    fi
}

# Function to set up automatic mounting and SMB sharing
setup_auto() {
    log "Starting setup_auto"
    echo "=== Setting up automatic mounting and SMB sharing for hot-swap devices ==="

    # Install required packages
    echo "Installing required packages (samba, python3-flask)..."
    apt-get update -y
    apt-get install -y samba python3-flask || { echo "✗ Failed to install packages"; log "ERROR: Failed to install packages"; exit 1; }

    # Configure Samba for usershares
    echo "Configuring Samba for dynamic usershares..."
    cp /etc/samba/smb.conf /etc/samba/smb.conf.autoshare.bak 2>/dev/null || true

    # Add usershare settings to [global] section if not present
    if ! grep -q "usershare allow guests" /etc/samba/smb.conf; then
        sed -i '/^\[global\]/a \
    usershare allow guests = yes\
    usershare max shares = 100\
    usershare owner only = no\
    usershare path = /var/lib/samba/usershares' /etc/samba/smb.conf
    fi

    # Create usershares directory
    mkdir -p /var/lib/samba/usershares
    chown root:sambashare /var/lib/samba/usershares 2>/dev/null || true
    chmod 1770 /var/lib/samba/usershares

    # Create the auto-share script
    echo "Creating auto-share script..."
    cat > /usr/local/bin/auto-share.sh <<'EOF'
#!/bin/bash

ACTION=$1
DEVNAME="/dev/$2"

if [ "$ACTION" = "add" ]; then
    # Get label or UUID for share name
    LABEL=$(blkid -s LABEL -o value "$DEVNAME" 2>/dev/null)
    if [ -z "$LABEL" ]; then
        UUID=$(blkid -s UUID -o value "$DEVNAME" 2>/dev/null)
        if [ -n "$UUID" ]; then
            LABEL="usb_${UUID:0:8}"
        else
            LABEL="usb_$(basename "$DEVNAME")"
        fi
    fi

    MOUNTPOINT="/media/$LABEL"
    mkdir -p "$MOUNTPOINT"

    # Mount the device
    if mount "$DEVNAME" "$MOUNTPOINT"; then
        echo "Mounted $DEVNAME to $MOUNTPOINT"

        # Add SMB share
        if net usershare add "$LABEL" "$MOUNTPOINT" "Auto-shared $LABEL" "" "guest_ok=yes,writeable=yes"; then
            echo "Added SMB share: $LABEL -> $MOUNTPOINT"
        else
            echo "Failed to add SMB share for $LABEL"
        fi
    else
        echo "Failed to mount $DEVNAME"
        rmdir "$MOUNTPOINT"
    fi

elif [ "$ACTION" = "remove" ]; then
    # Find mountpoint
    MOUNTPOINT=$(mount | grep "^$DEVNAME" | awk '{print $3}')
    if [ -n "$MOUNTPOINT" ]; then
        LABEL=$(basename "$MOUNTPOINT")

        # Remove share
        net usershare delete "$LABEL" 2>/dev/null || true

        # Unmount
        umount "$MOUNTPOINT"
        rmdir "$MOUNTPOINT" 2>/dev/null || true
        echo "Unmounted and removed share for $DEVNAME"
    fi
fi
EOF
    chmod +x /usr/local/bin/auto-share.sh

    # Create the web UI script
    echo "Creating web UI script..."
    cat > /usr/local/bin/webui.py <<'EOF'
#!/usr/bin/env python3

import subprocess
import json
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hot-Swap Manager - {{ hostname }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .button { background-color: #4CAF50; color: white; padding: 5px 10px; border: none; cursor: pointer; }
        .button.danger { background-color: #f44336; }
        .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .success { background-color: #d4edda; color: #155724; }
        .error { background-color: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <h1>Hot-Swap Manager on {{ hostname }}</h1>
    {% if message %}
        <div class="message {{ 'success' if success else 'error' }}">{{ message }}</div>
    {% endif %}
    
    <h2>Available Block Devices</h2>
    <table>
        <tr><th>Device</th><th>Size</th><th>FSType</th><th>Label</th><th>Mountpoint</th><th>Actions</th></tr>
        {% for dev in devices %}
        <tr>
            <td>{{ dev.name }}</td>
            <td>{{ dev.size }}</td>
            <td>{{ dev.fstype or '-' }}</td>
            <td>{{ dev.label or '-' }}</td>
            <td>{{ dev.mountpoint or '-' }}</td>
            <td>
                {% if not dev.mountpoint %}
                <form method="post" style="display:inline;">
                    <input type="hidden" name="action" value="mount">
                    <input type="hidden" name="device" value="{{ dev.name }}">
                    <button type="submit" class="button">Mount</button>
                </form>
                {% else %}
                <form method="post" style="display:inline;">
                    <input type="hidden" name="action" value="unmount">
                    <input type="hidden" name="device" value="{{ dev.name }}">
                    <button type="submit" class="button danger">Unmount</button>
                </form>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>
    
    <h2>Mounted Filesystems</h2>
    <table>
        <tr><th>Device</th><th>Mountpoint</th><th>FSType</th></tr>
        {% for fs in mounts %}
        <tr><td>{{ fs.device }}</td><td>{{ fs.mountpoint }}</td><td>{{ fs.fstype }}</td></tr>
        {% endfor %}
    </table>
    
    <h2>Active SMB Shares</h2>
    <table>
        <tr><th>Share Name</th><th>Path</th><th>Comment</th></tr>
        {% for share in shares %}
        <tr><td>{{ share.name }}</td><td>{{ share.path }}</td><td>{{ share.comment }}</td></tr>
        {% endfor %}
    </table>
</body>
</html>
'''

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)

def get_devices():
    success, output = run_cmd("lsblk -J -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT")
    if success:
        data = json.loads(output)
        devices = []
        for dev in data.get('blockdevices', []):
            if dev['name'].startswith(('sd', 'nvme', 'vd')):
                devices.append({
                    'name': f"/dev/{dev['name']}",
                    'size': dev.get('size', '-'),
                    'fstype': dev.get('fstype'),
                    'label': dev.get('label'),
                    'mountpoint': dev.get('mountpoint')
                })
        return devices
    return []

def get_mounts():
    success, output = run_cmd("mount | grep -E '/dev/sd|/dev/nvme|/dev/vd'")
    mounts = []
    if success:
        for line in output.split('\n'):
            if line:
                parts = line.split()
                if len(parts) >= 3:
                    mounts.append({
                        'device': parts[0],
                        'mountpoint': parts[2],
                        'fstype': parts[4] if len(parts) > 4 else '-'
                    })
    return mounts

def get_shares():
    success, output = run_cmd("net usershare list -l")
    shares = []
    if success:
        for line in output.split('\n'):
            if line and '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 3:
                    shares.append({
                        'name': parts[0],
                        'path': parts[1],
                        'comment': parts[2]
                    })
    return shares

def mount_device(device):
    # Get label
    success, label = run_cmd(f"blkid -s LABEL -o value {device}")
    if not success or not label:
        success, uuid = run_cmd(f"blkid -s UUID -o value {device}")
        if success and uuid:
            label = f"usb_{uuid[:8]}"
        else:
            label = f"usb_{device.split('/')[-1]}"
    
    mountpoint = f"/media/{label}"
    run_cmd(f"mkdir -p {mountpoint}")
    
    success, _ = run_cmd(f"mount {device} {mountpoint}")
    if success:
        run_cmd(f"net usershare add {label} {mountpoint} 'Shared {label}' '' 'guest_ok=yes,writeable=yes'")
        return True, f"Mounted {device} to {mountpoint} and shared as {label}"
    else:
        run_cmd(f"rmdir {mountpoint}")
        return False, f"Failed to mount {device}"

def unmount_device(device):
    success, mountpoint = run_cmd(f"mount | grep '^{device}' | awk '{{print $3}}'")
    if success and mountpoint:
        label = mountpoint.split('/')[-1]
        run_cmd(f"net usershare delete {label}")
        run_cmd(f"umount {mountpoint}")
        run_cmd(f"rmdir {mountpoint}")
        return True, f"Unmounted and removed share for {device}"
    return False, f"Device {device} is not mounted"

@app.route('/shares', methods=['GET', 'POST'])
def shares():
    message = None
    success = False
    
    if request.method == 'POST':
        action = request.form.get('action')
        device = request.form.get('device')
        
        if action == 'mount':
            success, message = mount_device(device)
        elif action == 'unmount':
            success, message = unmount_device(device)
    
    devices = get_devices()
    mounts = get_mounts()
    shares = get_shares()
    
    success_hn, hostname = run_cmd("hostname")
    hostname = hostname if success_hn else "Unknown"
    
    return render_template_string(HTML_TEMPLATE, 
                                devices=devices, 
                                mounts=mounts, 
                                shares=shares, 
                                hostname=hostname,
                                message=message,
                                success=success)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8007, debug=False)
EOF
    chmod +x /usr/local/bin/webui.py

    # Create systemd service for web UI
    echo "Creating systemd service for web UI..."
    cat > /etc/systemd/system/hotswap-webui.service <<EOF
[Unit]
Description=Hot-Swap Manager Web UI
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/webui.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable hotswap-webui
    systemctl start hotswap-webui || echo "Warning: Failed to start web UI service"

    echo "✓ Web UI service created and started"

    # Create udev rule
    echo "Creating udev rule for hot-swap devices..."
    cat > /etc/udev/rules.d/99-auto-share.rules <<'EOF'
ACTION=="add", SUBSYSTEM=="block", KERNEL=="sd*", RUN+="/usr/local/bin/auto-share.sh add %k"
ACTION=="remove", SUBSYSTEM=="block", KERNEL=="sd*", RUN+="/usr/local/bin/auto-share.sh remove %k"
EOF

    # Reload udev rules
    udevadm control --reload-rules
    udevadm trigger

    # Restart Samba
    systemctl restart smbd || { echo "✗ Failed to restart Samba"; log "ERROR: Failed to restart Samba"; exit 1; }

    echo "✓ Auto-mounting and sharing setup completed"
    log "Setup completed successfully"
    echo
}

# Function to list block devices and mounted filesystems
list_devices() {
    echo "=== Available Block Devices ==="
    lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT | grep -E "^sd|^nvme|^vd"
    echo
    echo "=== Mounted Filesystems ==="
    mount | grep -E "/dev/sd|/dev/nvme|/dev/vd" | awk '{print $1, $3, $5}'
    echo
    echo "=== Active SMB Shares ==="
    net usershare list 2>/dev/null || echo "No usershares found"
    echo
}

# Function to manually mount a device
mount_device() {
    local device="$1"
    log "Mounting device: $device"
    if [ -z "$device" ]; then
        echo "Usage: $0 mount <device> (e.g., /dev/sdb1)"
        exit 1
    fi

    # Get label or UUID
    LABEL=$(blkid -s LABEL -o value "$device" 2>/dev/null)
    if [ -z "$LABEL" ]; then
        UUID=$(blkid -s UUID -o value "$device" 2>/dev/null)
        if [ -n "$UUID" ]; then
            LABEL="usb_${UUID:0:8}"
        else
            LABEL="usb_$(basename "$device")"
        fi
    fi

    MOUNTPOINT="/media/$LABEL"
    mkdir -p "$MOUNTPOINT"

    if mount "$device" "$MOUNTPOINT"; then
        echo "✓ Mounted $device to $MOUNTPOINT"
        log "Mounted $device to $MOUNTPOINT"
        # Add share
        net usershare add "$LABEL" "$MOUNTPOINT" "Manually shared $LABEL" "" "guest_ok=yes,writeable=yes" && echo "✓ Added SMB share: $LABEL"
        log "Added SMB share: $LABEL"
    else
        echo "✗ Failed to mount $device"
        log "ERROR: Failed to mount $device"
        rmdir "$MOUNTPOINT"
    fi
}

# Function to manually unmount a device
unmount_device() {
    local device=$1
    if [ -z "$device" ]; then
        echo "Usage: $0 unmount <device> (e.g., /dev/sdb1)"
        exit 1
    fi

    MOUNTPOINT=$(mount | grep "^$device" | awk '{print $3}')
    if [ -n "$MOUNTPOINT" ]; then
        LABEL=$(basename "$MOUNTPOINT")
        net usershare delete "$LABEL" 2>/dev/null || true
        umount "$MOUNTPOINT" && rmdir "$MOUNTPOINT" 2>/dev/null && echo "✓ Unmounted and removed share for $device"
    else
        echo "Device $device is not mounted"
    fi
}

# Function to clean up orphaned mounts and shares
cleanup() {
    echo "=== Cleaning up orphaned mounts and shares ==="
    # Find mounts in /media that are not in use
    for mp in /media/*; do
        if [ -d "$mp" ] && ! mountpoint -q "$mp"; then
            rmdir "$mp" 2>/dev/null && echo "Removed empty mountpoint $mp"
        fi
    done
    echo "✓ Cleanup completed"
}

# Function to format a device
format_device() {
    local device="$1"
    local fstype="$2"
    log "Formatting device: $device as $fstype"

    echo "=== Formatting $device as $fstype ==="
    echo "WARNING: This will destroy all data on $device!"
    read -p "Are you sure? Type 'yes' to continue: " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborted."
        log "Format aborted by user"
        exit 1
    fi

    case "$fstype" in
        "ext4")
            apt-get install -y e2fsprogs
            mkfs.ext4 -F "$device"
            ;;
        "ntfs")
            apt-get install -y ntfs-3g
            mkfs.ntfs -f "$device"
            ;;
        "exfat")
            apt-get install -y exfatprogs
            mkfs.exfat "$device"
            ;;
        "fat32")
            apt-get install -y dosfstools
            mkfs.vfat -F 32 "$device"
            ;;
        *)
            echo "Unsupported filesystem: $fstype"
            echo "Supported: ext4, ntfs, exfat, fat32"
            log "ERROR: Unsupported filesystem: $fstype"
            exit 1
            ;;
    esac

    if [ $? -eq 0 ]; then
        echo "✓ Successfully formatted $device as $fstype"
        log "Successfully formatted $device as $fstype"
    else
        echo "✗ Failed to format $device"
        log "ERROR: Failed to format $device"
        exit 1
    fi
}

# Function to start the web UI
start_webui() {
    echo "Starting web UI on port 8007..."
    if [ -f "/usr/local/bin/webui.py" ]; then
        python3 /usr/local/bin/webui.py &
        echo "✓ Web UI started. Access at http://$(hostname -I | awk '{print $1}'):8007/shares"
    else
        echo "✗ Web UI script not found. Run setup first."
    fi
}

# Main execution
case $ACTION in
    "setup")
        check_root
        setup_auto
        ;;
    "list")
        list_devices
        ;;
    "mount")
        check_root
        mount_device "$PARAM"
        ;;
    "unmount")
        check_root
        unmount_device "$PARAM"
        ;;
    "format")
        # Expect format <device> <fstype>
        DEVICE="$PARAM"
        FSTYPE="$3"
        if [ -z "$DEVICE" ] || [ -z "$FSTYPE" ]; then
            echo "Usage: $0 format <device> <fstype>"
            echo "Supported filesystems: ext4, ntfs, exfat, fat32"
            echo "WARNING: This will destroy all data on the device!"
            exit 1
        fi
        check_root
        format_device "$DEVICE" "$FSTYPE"
        ;;
    "webui")
        start_webui
        ;;
    *)
        echo "Invalid action: $ACTION"
        echo "Use: setup, list, mount, unmount, format, cleanup, or webui"
        exit 1
        ;;
esac
