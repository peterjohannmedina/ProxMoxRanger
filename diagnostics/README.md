# ProxMox Ranger - Diagnostic Tools

## Overview
Tools to diagnose and troubleshoot mount and sharing issues on your ProxMox Ranger installation.

## Quick Start

### Run Diagnostic from Windows
```powershell
cd diagnostics
.\run-remote-diagnostic.ps1
```

### Run Diagnostic from Linux/Mac
```bash
cd diagnostics
bash run-remote-diagnostic.sh
```

## Tools

### diagnose-mount-issues.sh
Comprehensive diagnostic script that checks all aspects of your hot-swap mount system.

**What it checks:**
- System information (kernel, OS, permissions)
- Block devices and partitions inventory
- Detailed device analysis (filesystems, mount tests)
- Required packages and dependencies
- Filesystem kernel modules
- SMB/Samba configuration
- Mount point directories
- System logs for errors
- Web UI service status
- Provides actionable recommendations

**Usage:**
```bash
# Run locally on server
ssh root@192.168.1.233
bash /path/to/diagnose-mount-issues.sh

# Run remotely from Windows
cd diagnostics
.\run-remote-diagnostic.ps1 192.168.1.233 root

# Run remotely from Linux/Mac
cd diagnostics
bash run-remote-diagnostic.sh 192.168.1.233 root
```

**Output:**
- Terminal output with color-coded results
- Log file saved to `/tmp/mount-diagnostic-YYYYMMDD_HHMMSS.log`

### run-remote-diagnostic.sh / .ps1
Helper scripts to run the diagnostic tool on a remote server.

**Features:**
- Uploads diagnostic script to server
- Executes diagnostic remotely
- Displays results in real-time
- Saves log file on server

**Parameters:**
- `$1` (arg 1): Server IP address (default: 192.168.1.233)
- `$2` (arg 2): SSH user (default: root)

### deploy-webui-fix.sh / .ps1
Deploy updated webui.py to the server and restart the service.

**What it does:**
1. Backs up current webui.py on server
2. Uploads fixed webui.py
3. Installs to correct location
4. Restarts web UI service
5. Verifies service status

**Usage:**
```bash
# From Windows
cd diagnostics
.\deploy-webui-fix.ps1 192.168.1.233 root

# From Linux/Mac
cd diagnostics
bash deploy-webui-fix.sh 192.168.1.233 root
```

**Rollback:**
```bash
ssh root@192.168.1.233
cd /opt/proxmox-ranger/bin
ls -la webui.backup-*  # Find backup
cp webui.backup-YYYYMMDD_HHMMSS webui  # Restore
systemctl restart proxmox-ranger  # or kill/restart manually
```

## Common Issues Detected

### 1. Missing Filesystem Drivers
**Symptom:** Device shows but won't mount
**Fix:** `apt-get install ntfs-3g e2fsprogs exfatprogs dosfstools`

### 2. Device Has No Filesystem
**Symptom:** No filesystem type shown
**Fix:** Format the device using the web UI or `mkfs.ext4 /dev/sdX1`

### 3. Corrupted Share Files
**Symptom:** Shares not displaying in web UI
**Fix:** `net usershare delete <sharename>`

### 4. Permission Issues
**Symptom:** Mount succeeds but not writable
**Fix:** `chmod 755 /media && chown root:root /media`

### 5. Web UI Service Not Running
**Symptom:** Cannot access http://192.168.1.233:8010
**Fix:** `systemctl restart proxmox-ranger`

## Troubleshooting Guides

For detailed troubleshooting steps, see:
- [Mount Troubleshooting Guide](../docs/MOUNT_TROUBLESHOOTING.md)
- [Fix Summary](../docs/FIX_SUMMARY.md)

## Examples

### Example 1: Diagnose why device won't mount
```bash
cd diagnostics
bash run-remote-diagnostic.sh

# Review output, look for:
# - Missing filesystem drivers
# - No filesystem detected
# - Permission issues
```

### Example 2: Deploy webui fix after making changes
```bash
# Edit webui.py locally
cd diagnostics
bash deploy-webui-fix.sh

# Web UI automatically restarts with changes
```

### Example 3: Download diagnostic log for analysis
```bash
# After running diagnostic
scp root@192.168.1.233:/tmp/mount-diagnostic-*.log ./

# Review locally
cat mount-diagnostic-*.log
```

## Getting Help

If diagnostics don't solve your issue:

1. Run the diagnostic and save output
2. Check web UI logs: `journalctl -u proxmox-ranger -n 100`
3. Try manual mount: `mount -v /dev/sdX1 /tmp/test`
4. Report issue with diagnostic output

## Advanced Usage

### Run specific diagnostic checks

```bash
ssh root@192.168.1.233

# Check just block devices
lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINT

# Check just SMB shares
net usershare list
net usershare info <sharename>

# Check web UI service
systemctl status proxmox-ranger
journalctl -u proxmox-ranger -f
```

### Clean up corrupted shares

```bash
ssh root@192.168.1.233

# List all shares (including corrupted)
net usershare list

# Delete corrupted share
net usershare delete <sharename>

# Verify
net usershare list
```

## Tips

- Run diagnostics **before** making changes to establish baseline
- Save diagnostic logs for comparison
- Use `--help` flag on scripts for more options
- Check logs in `/var/log/proxmox-ranger.log` for details

