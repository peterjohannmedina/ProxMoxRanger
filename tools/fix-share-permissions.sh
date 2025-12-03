#!/bin/bash
# Fix SMB share permissions for mounted devices
# This script fixes permission issues that prevent writing to SMB shares

MOUNT_POINT="$1"
SHARE_NAME="$2"

if [ -z "$MOUNT_POINT" ] || [ -z "$SHARE_NAME" ]; then
    echo "Usage: $0 <mount_point> <share_name>"
    echo "Example: $0 /media/usb_ded16b93 usb_ded16b93"
    exit 1
fi

if [ ! -d "$MOUNT_POINT" ]; then
    echo "Error: Mount point $MOUNT_POINT does not exist"
    exit 1
fi

echo "=== Fixing permissions for $MOUNT_POINT ==="

# 1. Change ownership to allow writing
echo "1. Setting directory permissions..."
chmod 2775 "$MOUNT_POINT"
chown root:smbusers "$MOUNT_POINT"

# 2. Remove existing share if it exists
echo "2. Removing existing share..."
net usershare delete "$SHARE_NAME" 2>/dev/null || true

# 3. Create new share with proper permissions
echo "3. Creating SMB share with write permissions..."
# The ACL format is: Everyone:F (Full control)
# F = Full Control (read, write, delete)
# Filesystem permissions still apply as a secondary layer
net usershare add "$SHARE_NAME" "$MOUNT_POINT" "USB Device Share" "Everyone:F" "guest_ok=n"

echo ""
echo "=== Share Configuration ==="
net usershare info "$SHARE_NAME"

echo ""
echo "=== Directory Permissions ==="
ls -ld "$MOUNT_POINT"

echo ""
echo "✅ Permissions fixed!"
echo "The share should now allow reading and writing files."
