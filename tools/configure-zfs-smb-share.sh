#!/bin/bash
# configure-zfs-smb-share.sh
# Usage: configure-zfs-smb-share.sh <dataset_path> <share_name> <smb_user> <smb_password>

DATASET_PATH="$1"
SHARE_NAME="$2"
SMB_USER="$3"
SMB_PASS="$4"

if [ -z "$DATASET_PATH" ] || [ -z "$SHARE_NAME" ] || [ -z "$SMB_USER" ] || [ -z "$SMB_PASS" ]; then
    echo "Usage: $0 <dataset_path> <share_name> <smb_user> <smb_password>"
    exit 1
fi

if [ ! -d "$DATASET_PATH" ]; then
    echo "Error: dataset path $DATASET_PATH does not exist"
    exit 1
fi

# 1) Create unix user if it doesn't exist
if id "$SMB_USER" >/dev/null 2>&1; then
    echo "User $SMB_USER already exists"
else
    echo "Creating local user $SMB_USER..."
    useradd -m -s /bin/bash "$SMB_USER"
fi

# 2) Ensure group exists and add user
if ! getent group smbusers >/dev/null 2>&1; then
    groupadd smbusers
fi
usermod -aG smbusers "$SMB_USER"

# 3) Set ownership and permissions
echo "Setting ownership and ACLs for $DATASET_PATH..."
chown -R "$SMB_USER":smbusers "$DATASET_PATH"
chmod -R 2775 "$DATASET_PATH"  # Set group sticky to inherit group
setfacl -R -m g:smbusers:rwx "$DATASET_PATH"
setfacl -d -m g:smbusers:rwx "$DATASET_PATH"

# 4) Add Samba user
echo -e "$SMB_PASS\n$SMB_PASS" | smbpasswd -s -a "$SMB_USER"
smbpasswd -e "$SMB_USER"

# 5) Backup smb.conf
SMBCONF=/etc/samba/smb.conf
cp "$SMBCONF" "$SMBCONF.bak-$(date +%F-%T)"

# 6) Remove existing share block if present
awk -v share="\[${SHARE_NAME}\]" 'BEGIN{del=0} /^\[/ { if(del==1 && $0 ~ /^\[/) {del=0} } { if($0 ~ share) {del=1; next} } { if(!del) print $0 }' "$SMBCONF" > "$SMBCONF.tmp"
mv "$SMBCONF.tmp" "$SMBCONF"

# 7) Append new share configuration
cat >> "$SMBCONF" << EOF

[${SHARE_NAME}]
    comment = ZFS dataset ${SHARE_NAME}
    path = ${DATASET_PATH}
    browseable = yes
    read only = no
    guest ok = no
    valid users = ${SMB_USER}
    force user = ${SMB_USER}
    force group = smbusers
    create mask = 0664
    directory mask = 2775
    force create mode = 0
    force directory mode = 2775
EOF

# 8) Restart Samba
echo "Restarting Samba..."
systemctl restart smbd nmbd || systemctl restart smbd || true

# 9) Confirm
echo "New Samba share configuration for ${SHARE_NAME}:"

smbclient -L localhost -U ${SMB_USER}%${SMB_PASS} 2>/dev/null | sed -n '1,200p'

# End

echo "Configuration complete. Verify the share as user: smbclient //localhost/${SHARE_NAME} -U ${SMB_USER} -W WORKGROUP"
