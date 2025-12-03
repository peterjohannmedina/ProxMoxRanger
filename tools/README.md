# ProxMox Ranger - Maintenance Tools

Collection of maintenance and configuration tools for fixing common issues with SMB shares, permissions, and system configuration.

## SMB Permission Fixes

### fix-smb-permissions.sh
Comprehensive SMB permission fix for shares. Resets all permissions to allow multi-user write access.

**What it does:**
- Resets share directory permissions (2775)
- Sets proper group ownership (smbusers)
- Configures setgid bit for new files
- Applies permissions recursively

**Usage:**
```bash
ssh root@192.168.1.233
cd /path/to/tools
bash fix-smb-permissions.sh
```

### fix-smb-quick.sh
Quick SMB permission reset for emergency fixes.

**Features:**
- Fast permission reset
- Minimal checks
- Good for quick fixes

**Usage:**
```bash
ssh root@192.168.1.233
bash tools/fix-smb-quick.sh
```

### fix-share-permissions.sh
Fix permissions on a specific share.

**Usage:**
```bash
ssh root@192.168.1.233
bash tools/fix-share-permissions.sh /path/to/share
```

### fix-share-write-permissions.sh
Enable write access on shares for all authenticated users.

**What it fixes:**
- Write permissions for smbusers group
- Directory permissions (775)
- File permissions (664)
- Group ownership

**Usage:**
```bash
ssh root@192.168.1.233
bash tools/fix-share-write-permissions.sh /media/share-name
```

### fix-medinas-multiuser-share.sh
Fix multi-user share permissions specifically for the medinas ZFS pool.

**Specific to:**
- medinas ZFS pool
- Multi-user write access
- Group-based permissions

**Usage:**
```bash
ssh root@192.168.1.233
bash tools/fix-medinas-multiuser-share.sh
```

## Configuration Tools

### configure-zfs-smb-share.sh
Configure SMB sharing for ZFS pools with proper permissions and ACLs.

**Features:**
- Sets up SMB share for ZFS dataset
- Configures proper ACLs
- Handles ZFS-specific permissions
- Creates usershare configuration

**Usage:**
```bash
ssh root@192.168.1.233
bash tools/configure-zfs-smb-share.sh <pool-name> <dataset-name>
```

**Example:**
```bash
bash tools/configure-zfs-smb-share.sh mypool data
```

### configure-firefox-handlers.sh
Configure Firefox to handle smb:// and ssh:// protocol links.

**What it does:**
- Registers SMB protocol handler
- Registers SSH protocol handler
- Creates desktop entries
- Updates Firefox preferences

**Usage:**
```bash
# On local desktop machine (not server)
bash tools/configure-firefox-handlers.sh
```

**After running:**
- Clicking `smb://server/share` opens file manager
- Clicking `ssh://user@server` opens terminal

### enable-firefox-protocols.sh
Enable protocol handlers in Firefox configuration.

**Features:**
- Updates Firefox prefs.js
- Enables external protocol handlers
- No manual Firefox configuration needed

**Usage:**
```bash
bash tools/enable-firefox-protocols.sh
```

## Common Scenarios

### Scenario 1: Cannot write to mounted share

**Problem:** Files are read-only even though you're authenticated

**Solution:**
```bash
ssh root@192.168.1.233

# Find the share mountpoint
mount | grep /media

# Fix permissions
bash tools/fix-share-write-permissions.sh /media/usb_abc123

# Or fix all shares
bash tools/fix-smb-permissions.sh
```

### Scenario 2: ZFS pool not accessible via SMB

**Problem:** ZFS pool is mounted but not shared

**Solution:**
```bash
ssh root@192.168.1.233
bash tools/configure-zfs-smb-share.sh mypool
```

### Scenario 3: Multiple users need write access

**Problem:** Only one user can write to share

**Solution:**
```bash
ssh root@192.168.1.233

# Fix permissions for multi-user access
bash tools/fix-smb-permissions.sh

# Ensure users are in smbusers group
usermod -aG smbusers username

# Add SMB password
smbpasswd -a username
```

### Scenario 4: Firefox not opening SMB links

**Problem:** Clicking SMB links does nothing

**Solution:**
```bash
# On local desktop machine
bash tools/configure-firefox-handlers.sh
bash tools/enable-firefox-protocols.sh

# Restart Firefox
```

## Tool Details

### Permission Structure

Most tools use this permission structure:
- **Directories:** `2775` (drwxrwsr-x)
  - `2xxx` = setgid bit (new files inherit group)
  - `7xx` = owner (root) has rwx
  - `7x` = group (smbusers) has rwx
  - `5` = others have r-x

- **Files:** `664` (rw-rw-r--)
  - Owner and group can read/write
  - Others can read only

- **Group:** `smbusers`
  - All authenticated SMB users should be in this group

### Verification

After running permission fixes, verify:

```bash
# Check directory permissions
ls -ld /media/share-name

# Should show: drwxrwsr-x root smbusers

# Check group membership
getent group smbusers

# Check SMB share exists
net usershare list

# Test write access
su - username
cd /media/share-name
touch test-file
rm test-file
```

## Best Practices

1. **Backup before running:** Some scripts modify system configuration
2. **Run as root:** Most scripts require root privileges
3. **Test after changes:** Verify shares are accessible
4. **Document changes:** Keep notes on what was fixed
5. **Use specific tools:** Don't use fix-all scripts for specific problems

## Troubleshooting

### Tool fails with "Permission denied"
```bash
# Ensure running as root
sudo bash tools/script-name.sh
```

### Changes don't take effect
```bash
# Restart Samba service
systemctl restart smbd

# Clear client cache
# On Windows: net use * /delete
# On Linux: umount //server/share && mount //server/share
```

### Lost changes after reboot
Some permission fixes may need to be made permanent:
```bash
# For ZFS pools, add to /etc/rc.local
# For mounts, add to /etc/fstab
```

## Quick Reference

| Issue | Tool | Command |
|-------|------|---------|
| Can't write to share | fix-share-write-permissions.sh | `bash tools/fix-share-write-permissions.sh /media/share` |
| All shares broken | fix-smb-permissions.sh | `bash tools/fix-smb-permissions.sh` |
| ZFS not shared | configure-zfs-smb-share.sh | `bash tools/configure-zfs-smb-share.sh poolname` |
| Firefox SMB links | configure-firefox-handlers.sh | `bash tools/configure-firefox-handlers.sh` |
| Quick permission reset | fix-smb-quick.sh | `bash tools/fix-smb-quick.sh` |

## Getting Help

If tools don't solve your issue:

1. Check logs: `tail /var/log/samba/log.smbd`
2. Verify Samba is running: `systemctl status smbd`
3. Test manually: `smbclient //localhost/sharename -U username`
4. See [Mount Troubleshooting Guide](../docs/MOUNT_TROUBLESHOOTING.md)

## Contributing

When creating new maintenance tools:
- Add clear documentation
- Include usage examples
- Test on fresh install
- Update this README
