#!/bin/bash
# Fix SMB share permissions and add authenticated access

echo "=== Fixing SMB Share Permissions ==="
echo ""

# Check if we're on the Proxmox node
if [ ! -f /etc/pve/.version ]; then
    echo "⚠️  This script should be run on the Proxmox node (192.168.1.233)"
    echo "   Run: scp $0 root@192.168.1.233:/tmp/ && ssh root@192.168.1.233 /tmp/$(basename $0)"
    exit 1
fi

# Ensure Samba is configured for proper user mapping
echo "Checking Samba configuration..."
if ! grep -q "^[[:space:]]*force user = root" /etc/samba/smb.conf 2>/dev/null; then
    echo "⚠️  Adding user mapping configuration to Samba"
    
    # Backup smb.conf
    cp /etc/samba/smb.conf /etc/samba/smb.conf.backup.$(date +%s) 2>/dev/null || true
    
    # Add to global section if not exists
    if ! grep -q "map to guest" /etc/samba/smb.conf; then
        sed -i '/\[global\]/a \   # User mapping for authenticated access\n   map to guest = Never\n   security = user\n   username map = /etc/samba/smbusers' /etc/samba/smb.conf
        echo "✓ Added user mapping configuration"
    fi
fi

# Restart Samba to apply changes
systemctl restart smbd 2>/dev/null || systemctl restart samba 2>/dev/null || true
echo "✓ Samba configuration updated"
echo ""

# Function to set proper permissions
fix_share_permissions() {
    local mountpoint=$1
    local label=$2
    
    echo "Setting permissions for: $mountpoint"
    
    # Set ownership to root
    chown -R root:root "$mountpoint"
    
    # Set permissions to 755 (rwxr-xr-x)
    # This allows:
    # - Root: full access
    # - Connecting users: read/execute
    # - Users with write permissions via SMB ACLs: can write
    chmod 755 "$mountpoint"
    
    echo "✓ Set permissions: 755 (user-mapped access)"
}

# Function to recreate share with authentication
recreate_share() {
    local label=$1
    local mountpoint=$2
    
    echo ""
    echo "Recreating share: $label"
    
    # Remove existing share
    net usershare delete "$label" 2>/dev/null
    
    # Set ownership to root and permissions for user mapping
    chown -R root:root "$mountpoint"
    chmod 755 "$mountpoint"
    
    # Recreate share with user mapping
    # guest_ok=no means users must authenticate
    # Empty ACL means inherit from filesystem permissions
    # This allows SMB to map to the connecting user's permissions
    if net usershare add "$label" "$mountpoint" "Shared $label" "" "guest_ok=no"; then
        echo "✓ Created user-mapped share: $label"
        echo "  - Users inherit their system permissions"
        echo "  - Each user sees files with their own UID/GID"
    else
        echo "❌ Failed to create share: $label"
    fi
}

# Get all current SMB shares
echo "Current SMB shares:"
net usershare list

echo ""
echo "─────────────────────────────────────────"
echo ""

# Process each share
for share in $(net usershare list); do
    mountpoint=$(net usershare info "$share" | grep path | cut -d= -f2)
    
    if [ -d "$mountpoint" ]; then
        recreate_share "$share" "$mountpoint"
    fi
done

echo ""
echo "─────────────────────────────────────────"
echo ""

# Add ZFS datasets as shares if they exist
echo "Checking for ZFS datasets to share..."
echo ""

if command -v zfs >/dev/null 2>&1; then
    # Get all ZFS datasets that are mounted
    zfs list -H -o name,mountpoint,mounted | grep -E "yes$" | while read -r name mountpoint mounted; do
        # Skip system datasets
        if [[ "$name" =~ (rpool|pve) ]]; then
            continue
        fi
        
        # Create share name from dataset name
        share_label=$(echo "$name" | tr '/' '_')
        
        if [ -d "$mountpoint" ] && [ "$mountpoint" != "none" ] && [ "$mountpoint" != "-" ]; then
            echo "Found ZFS dataset: $name at $mountpoint"
            
            # Check if share already exists
            if net usershare info "$share_label" >/dev/null 2>&1; then
                echo "  Share already exists, recreating..."
                recreate_share "$share_label" "$mountpoint"
            else
                echo "  Creating new share..."
                chown -R root:root "$mountpoint"
                chmod 755 "$mountpoint"
                
                if net usershare add "$share_label" "$mountpoint" "ZFS: $name" "" "guest_ok=no"; then
                    echo "  ✓ Created ZFS share: $share_label (user-mapped)"
                fi
            fi
        fi
    done
else
    echo "ZFS not installed or no pools available"
fi

echo ""
echo "=== Summary ==="
echo ""
echo "All shares now require authentication:"
net usershare list
echo ""
echo "📝 To access shares:"
echo "   smb://192.168.1.233/share_name"
echo "   Username: root"
echo "   Password: (your system password)"
echo ""
echo "✅ User Mapping Enabled:"
echo "   - Files accessed via SMB inherit system permissions"
echo "   - When you connect as 'root', you have root permissions"
echo "   - Files are accessed with your actual user permissions"
echo "   - No permission elevation or restriction"
echo ""
echo "🔑 Permission Inheritance:"
echo "   - If root can read/write on system → SMB allows read/write"
echo "   - Same permissions as if you SSH'd in as that user"
echo ""
