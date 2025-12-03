#!/bin/bash
# Quick fix for SMB "Oops something went wrong" error

echo "=== Fixing SMB Share Access ==="
echo ""

if [ ! -f /etc/pve/.version ]; then
    echo "Run this on Proxmox node"
    exit 1
fi

# Step 1: Set SMB password for root
echo "Step 1: Setting SMB password for root user"
echo "----------------------------------------"
echo ""

# Check if root SMB user exists
if ! pdbedit -L | grep -q "^root:"; then
    echo "⚠️  Root user doesn't have SMB password!"
    echo ""
    echo "Setting SMB password for root..."
    echo "Please enter a password (can be same as system password):"
    smbpasswd -a root
    
    if [ $? -eq 0 ]; then
        echo "✓ SMB password set for root"
    else
        echo "❌ Failed to set SMB password"
        exit 1
    fi
else
    echo "✓ Root already has SMB password"
fi

echo ""
echo "Step 2: Fixing share permissions"
echo "----------------------------------------"
echo ""

# Fix all user shares
for share in $(net usershare list); do
    echo "Fixing share: $share"
    
    # Get share info
    path=$(net usershare info "$share" | grep "^path=" | cut -d= -f2)
    comment=$(net usershare info "$share" | grep "^comment=" | cut -d= -f2)
    
    if [ -z "$path" ]; then
        echo "  ⚠️  Could not get path for $share"
        continue
    fi
    
    if [ ! -d "$path" ]; then
        echo "  ⚠️  Path doesn't exist: $path"
        continue
    fi
    
    # Delete and recreate with proper settings
    net usershare delete "$share" 2>/dev/null
    
    # Set filesystem permissions
    chmod 755 "$path"
    chown root:root "$path"
    
    # Recreate share with NO ACL (inherits filesystem permissions)
    # Empty string for ACL means: use filesystem permissions
    if net usershare add "$share" "$path" "$comment" "" "guest_ok=no"; then
        echo "  ✓ Fixed: $share"
    else
        echo "  ❌ Failed: $share"
    fi
done

echo ""
echo "Step 3: Restarting Samba"
echo "----------------------------------------"
systemctl restart smbd
echo "✓ Samba restarted"

echo ""
echo "=== Summary ==="
echo ""
echo "✅ All shares updated with:"
echo "   - Authentication required (guest_ok=no)"
echo "   - User permission mapping (no fixed ACL)"
echo "   - Filesystem permissions: 755"
echo ""
echo "Current shares:"
net usershare list
echo ""
echo "📝 To access:"
echo "   smb://pver430/usb_ded16b93"
echo "   Username: root"
echo "   Password: (the SMB password you just set)"
echo ""
echo "✅ Fix complete!"
echo ""
