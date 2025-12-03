#!/bin/bash
set -euo pipefail

# Fix medinas share to allow multiple SMB users (group smbusers) and set ACLs
DATASET=/mypool/medinas
SHARE=medinas
PRIMARY_USER=proxuser
OTHER_USER=peter
PRIMARY_PASS=proxpass
OTHER_PASS=4677

# Ensure users exist and are in smbusers group
id ${PRIMARY_USER} >/dev/null 2>&1 || useradd -m -s /bin/bash ${PRIMARY_USER}
id ${OTHER_USER} >/dev/null 2>&1 || useradd -m -s /bin/bash ${OTHER_USER}
getent group smbusers >/dev/null 2>&1 || groupadd smbusers
usermod -aG smbusers ${PRIMARY_USER} || true
usermod -aG smbusers ${OTHER_USER} || true

# Set Samba passwords
echo -e "${PRIMARY_PASS}\n${PRIMARY_PASS}" | smbpasswd -s -a ${PRIMARY_USER} || true
smbpasswd -e ${PRIMARY_USER} || true
echo -e "${OTHER_PASS}\n${OTHER_PASS}" | smbpasswd -s -a ${OTHER_USER} || true
smbpasswd -e ${OTHER_USER} || true

# Set filesystem ownership and ACLs
echo "Setting filesystem ACLs and permissions..."
chown -R ${PRIMARY_USER}:smbusers ${DATASET}
chmod -R 2775 ${DATASET}
setfacl -R -m u:${OTHER_USER}:rwx ${DATASET}
setfacl -d -m u:${OTHER_USER}:rwx ${DATASET}
setfacl -R -m g:smbusers:rwx ${DATASET}
setfacl -d -m g:smbusers:rwx ${DATASET}

# Update smb.conf for the share: ensure valid users = @smbusers and remove force user
SMBCONF=/etc/samba/smb.conf
cp ${SMBCONF} ${SMBCONF}.bak-$(date +%F-%T)

awk 'BEGIN{in=0}
/\[medinas\]/{print; in=1; next}
/\[/{ if(in==1){in=0} print; next}
{ if(in==1) {
    if($0 ~ /^[[:space:]]*valid users[[:space:]]*=/) { print "    valid users = @smbusers"; next }
    if($0 ~ /^[[:space:]]*force user[[:space:]]*=/) { next }
  }
  print
}' ${SMBCONF} > ${SMBCONF}.tmp && mv ${SMBCONF}.tmp ${SMBCONF}

# Ensure force group = smbusers present in medinas section
awk 'BEGIN{in=0; found=0}
/\[medinas\]/{print; in=1; next}
/\[/{ if(in==1 && found==0){ print "    force group = smbusers"; found=1; in=0 } print; next}
{ if(in==1){ print } else print }' ${SMBCONF} > ${SMBCONF}.tmp2 && mv ${SMBCONF}.tmp2 ${SMBCONF} || true

# Restart Samba
systemctl restart smbd nmbd || systemctl restart smbd || true

# Clean up any usershare duplications and recreate usershare for medinas with explicit ACLs
net usershare delete ${SHARE} 2>/dev/null || true
# Use host's NetBIOS name if available
HOSTNAME_UPPER=$(hostname | tr '[:lower:]' '[:upper:]')
net usershare add ${SHARE} ${DATASET} "ZFS medinas" "${HOSTNAME_UPPER}\\${OTHER_USER}:F,${HOSTNAME_UPPER}\\${PRIMARY_USER}:F" guest_ok=n || true

# Verification
echo "Share medians info:"
net usershare info ${SHARE} || true

# Test using smbclient if available
if command -v smbclient >/dev/null 2>&1; then
  echo "Testing write as ${OTHER_USER}..."
  echo 'test content' | smbclient //localhost/${SHARE} -U ${OTHER_USER}%${OTHER_PASS} -c "put - test-peter-write.txt" || true
  echo "Listing files..."
  smbclient //localhost/${SHARE} -U ${OTHER_USER}%${OTHER_PASS} -c "ls" || true
fi

echo "Finished"
