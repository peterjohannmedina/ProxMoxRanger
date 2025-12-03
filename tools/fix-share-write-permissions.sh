#!/bin/bash
# Fix SMB share permissions to allow peter (and other smbusers) to write

echo "=== Fixing SMB Share Permissions for Write Access ==="
echo ""

# Function to fix permissions on a share path
fix_share_perms() {
    local path=$1
    local sharename=$2

    echo "Fixing permissions for: $path"

    # Check if path exists
    if [ ! -d "$path" ]; then
        echo "  ⚠️  Path does not exist: $path"
        return 1
    fi

    # Change group to smbusers
    chgrp -R smbusers "$path"

    # Set permissions: 2775 (rwxrwsr-x)
    # - 2xxx = setgid bit (new files inherit group)
    # - x7xx = owner (root) has rwx
    # - x7x = group (smbusers) has rwx
    # - xx5 = others have rx
    chmod 2775 "$path"

    # Set ACL for files created inside (if path has content)
    find "$path" -type d -exec chmod 2775 {} \; 2>/dev/null
    find "$path" -type f -exec chmod 664 {} \; 2>/dev/null
    find "$path" -exec chgrp smbusers {} \; 2>/dev/null

    echo "  ✓ Permissions set to 2775 (rwxrwsr-x), group: smbusers"

    # Update share ACL if share exists
    if net usershare info "$sharename" >/dev/null 2>&1; then
        # Get current share info
        local share_path=$(net usershare info "$sharename" | grep "^path=" | cut -d= -f2)
        local share_comment=$(net usershare info "$sharename" | grep "^comment=" | cut -d= -f2)

        # Recreate share with full access ACL
        net usershare delete "$sharename" 2>/dev/null
        net usershare add "$sharename" "$share_path" "$share_comment" "" "guest_ok=no"

        # Set ACL to allow full access for authenticated users
        # Since guest_ok=no, only authenticated users can access
        net usershare setacl "$sharename" Everyone:F

        echo "  ✓ Share ACL updated: Everyone:F (authenticated users only)"
    fi

    echo ""
}

# Fix all current shares
echo "Step 1: Fixing existing share directories"
echo "─────────────────────────────────────────"
echo ""

# Fix ZFS pools
if [ -d "/mypool" ]; then
    fix_share_perms "/mypool" "mypool"
fi

if [ -d "/mypool/medinas" ]; then
    fix_share_perms "/mypool/medinas" "medinas"
fi

# Fix USB shares
for usbdir in /media/usb_*; do
    if [ -d "$usbdir" ]; then
        share_label=$(basename "$usbdir")
        fix_share_perms "$usbdir" "$share_label"
    fi
done

echo "Step 2: Verifying smbusers group membership"
echo "─────────────────────────────────────────"
echo ""

# Check if peter is in smbusers group
if id peter | grep -q smbusers; then
    echo "✓ User 'peter' is in smbusers group"
else
    echo "⚠️  Adding user 'peter' to smbusers group"
    usermod -a -G smbusers peter
    echo "✓ User 'peter' added to smbusers group"
fi

echo ""
echo "Step 3: Current share status"
echo "─────────────────────────────────────────"
echo ""

# List all shares with their ACLs
for share in $(net usershare list); do
    echo "Share: $share"
    net usershare info "$share"
    echo ""
done

echo "Step 4: Verification"
echo "─────────────────────────────────────────"
echo ""

# Show permissions
echo "Directory permissions:"
ls -ld /mypool /mypool/medinas /media/usb_* 2>/dev/null

echo ""
echo "=== Fix Complete ==="
echo ""
echo "📝 Summary:"
echo "  - All shares now have group ownership: smbusers"
echo "  - Permissions: 2775 (rwxrwsr-x)"
echo "  - Share ACL: Everyone:F (requires authentication)"
echo ""
echo "✅ User 'peter' should now be able to:"
echo "  - Browse all shares"
echo "  - Create files and folders"
echo "  - Transfer files between shares"
echo "  - Delete files they own"
echo ""
echo "⚠️  Note: If peter is currently logged in via SMB,"
echo "    they may need to disconnect and reconnect for"
echo "    group membership changes to take effect."
echo ""
