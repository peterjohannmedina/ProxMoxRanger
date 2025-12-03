#!/bin/bash

#================================================================
# ProxMox Ranger - Mount Diagnostic & Troubleshooting Tool
#================================================================
# This script diagnoses why block devices are failing to mount
# and provides actionable recommendations
#================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

LOGFILE="/tmp/mount-diagnostic-$(date +%Y%m%d_%H%M%S).log"

# Redirect all output to both terminal and log file
exec > >(tee -a "$LOGFILE")
exec 2>&1

echo -e "${BOLD}================================================================"
echo -e "ProxMox Ranger - Mount Diagnostic Tool"
echo -e "================================================================${NC}"
echo -e "Started: $(date)"
echo -e "Logfile: $LOGFILE"
echo ""

#================================================================
# Helper Functions
#================================================================

print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}========================================${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

#================================================================
# 1. System Information
#================================================================

print_header "1. System Information"

echo "Hostname: $(hostname)"
echo "Kernel: $(uname -r)"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "Current User: $(whoami)"
echo "Root Access: $([[ $EUID -eq 0 ]] && echo 'YES' || echo 'NO (some checks will be limited)')"

#================================================================
# 2. Block Device Inventory
#================================================================

print_header "2. Block Device Inventory"

echo "All block devices:"
lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,UUID,MOUNTPOINT

echo ""
echo "Hot-swap candidates (sd*, nvme*, vd*):"
lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,UUID,MOUNTPOINT | grep -E "^sd|^nvme|^vd" || echo "None found"

#================================================================
# 3. Detailed Device Analysis
#================================================================

print_header "3. Detailed Device Analysis"

# Get all potential hot-swap devices
DEVICES=$(lsblk -ndo NAME | grep -E "^sd|^nvme|^vd")

if [ -z "$DEVICES" ]; then
    print_warning "No hot-swap devices found (sd*, nvme*, vd*)"
else
    for dev in $DEVICES; do
        DEVPATH="/dev/$dev"
        echo ""
        echo -e "${BOLD}Device: $DEVPATH${NC}"
        echo "----------------------------------------"

        # Check if device exists
        if [ ! -e "$DEVPATH" ]; then
            print_error "Device does not exist"
            continue
        fi

        # Check if device is readable
        if [ ! -r "$DEVPATH" ]; then
            print_error "Device is not readable (permission issue)"
            continue
        fi

        # Get detailed device information
        echo "Device info:"
        blkid "$DEVPATH" 2>/dev/null || echo "  No filesystem signature detected"

        # Get filesystem type
        FSTYPE=$(blkid -s TYPE -o value "$DEVPATH" 2>/dev/null)
        if [ -n "$FSTYPE" ]; then
            print_success "Filesystem type: $FSTYPE"

            # Check if filesystem driver is available
            case "$FSTYPE" in
                ext2|ext3|ext4)
                    if lsmod | grep -q "^ext4"; then
                        print_success "ext4 kernel module loaded"
                    else
                        print_error "ext4 kernel module NOT loaded"
                    fi
                    ;;
                ntfs)
                    if command -v ntfs-3g &>/dev/null; then
                        print_success "ntfs-3g is installed"
                    else
                        print_error "ntfs-3g is NOT installed (required for NTFS)"
                    fi
                    ;;
                vfat|exfat)
                    if lsmod | grep -q "vfat\|exfat"; then
                        print_success "FAT/exFAT kernel modules available"
                    else
                        print_warning "FAT/exFAT kernel modules may not be loaded"
                    fi
                    ;;
                xfs)
                    if lsmod | grep -q "xfs"; then
                        print_success "XFS kernel module loaded"
                    else
                        print_error "XFS kernel module NOT loaded"
                    fi
                    ;;
                *)
                    print_warning "Filesystem type '$FSTYPE' - verify driver availability"
                    ;;
            esac
        else
            print_error "No filesystem detected (device may need formatting)"
        fi

        # Check if currently mounted
        MOUNTPOINT=$(lsblk -no MOUNTPOINT "$DEVPATH" 2>/dev/null)
        if [ -n "$MOUNTPOINT" ]; then
            print_success "Already mounted at: $MOUNTPOINT"
        else
            print_info "Not currently mounted"

            # Attempt test mount if we have root and filesystem type
            if [[ $EUID -eq 0 ]] && [ -n "$FSTYPE" ]; then
                echo "  Attempting test mount..."
                TEST_MOUNT="/tmp/mount-test-$$"
                mkdir -p "$TEST_MOUNT"

                # Try mounting with verbose output
                if mount -v "$DEVPATH" "$TEST_MOUNT" 2>&1; then
                    print_success "Test mount SUCCEEDED"
                    # Check if writable
                    if touch "$TEST_MOUNT/test-write-$$" 2>/dev/null; then
                        print_success "Mount is WRITABLE"
                        rm -f "$TEST_MOUNT/test-write-$$"
                    else
                        print_error "Mount is READ-ONLY or permission denied"
                        echo "  Mount options: $(mount | grep "$TEST_MOUNT" | cut -d'(' -f2 | cut -d')' -f1)"
                    fi
                    umount "$TEST_MOUNT"
                    rmdir "$TEST_MOUNT"
                else
                    print_error "Test mount FAILED"
                    echo "  Error details:"
                    mount -v "$DEVPATH" "$TEST_MOUNT" 2>&1 | sed 's/^/    /'
                    rmdir "$TEST_MOUNT" 2>/dev/null
                fi
            fi
        fi

        # Check device errors in dmesg
        echo "  Recent kernel messages for $dev:"
        dmesg | grep -i "$dev" | tail -5 | sed 's/^/    /' || echo "    No recent messages"
    done
fi

#================================================================
# 4. Required Packages Check
#================================================================

print_header "4. Required Packages & Dependencies"

REQUIRED_PACKAGES=(
    "mount:mount"
    "umount:mount"
    "blkid:util-linux"
    "lsblk:util-linux"
    "ntfs-3g:ntfs-3g"
    "mkfs.ext4:e2fsprogs"
    "mkfs.ntfs:ntfs-3g"
    "mkfs.exfat:exfatprogs"
    "mkfs.vfat:dosfstools"
)

for entry in "${REQUIRED_PACKAGES[@]}"; do
    cmd="${entry%%:*}"
    pkg="${entry##*:}"
    if command -v "$cmd" &>/dev/null; then
        print_success "$cmd is available (package: $pkg)"
    else
        print_error "$cmd is MISSING (install: apt-get install $pkg)"
    fi
done

#================================================================
# 5. Filesystem Kernel Modules
#================================================================

print_header "5. Filesystem Kernel Modules"

MODULES=("ext4" "vfat" "exfat" "ntfs" "xfs" "btrfs")

for mod in "${MODULES[@]}"; do
    if lsmod | grep -q "^$mod"; then
        print_success "$mod module is loaded"
    else
        print_warning "$mod module is NOT loaded (may load automatically on mount)"
    fi
done

#================================================================
# 6. SMB/Samba Configuration
#================================================================

print_header "6. SMB/Samba Configuration"

if systemctl is-active --quiet smbd || systemctl is-active --quiet samba; then
    print_success "Samba service is running"
else
    print_error "Samba service is NOT running"
fi

if [ -d "/var/lib/samba/usershares" ]; then
    print_success "Usershares directory exists"
    echo "  Permissions: $(ls -ld /var/lib/samba/usershares | awk '{print $1, $3":"$4}')"
else
    print_error "Usershares directory does NOT exist"
fi

echo "Current usershares:"
if command -v net &>/dev/null; then
    net usershare list 2>/dev/null || print_warning "No usershares configured"
else
    print_error "'net' command not found (install samba-common-bin)"
fi

#================================================================
# 7. /media Directory Check
#================================================================

print_header "7. Mount Point Directory Check"

if [ -d "/media" ]; then
    print_success "/media directory exists"
    echo "  Permissions: $(ls -ld /media | awk '{print $1, $3":"$4}')"

    # Check for orphaned mount points
    echo "  Existing mount points in /media:"
    ls -la /media/ 2>/dev/null | grep -v "^total\|^\.$\|^\.\.$" | sed 's/^/    /' || echo "    (empty)"

    # Check for stuck mounts
    echo "  Checking for stuck mounts:"
    for mp in /media/*; do
        if [ -d "$mp" ]; then
            if mountpoint -q "$mp"; then
                print_info "$(basename $mp) is mounted"
            else
                if [ "$(ls -A $mp)" ]; then
                    print_warning "$(basename $mp) is NOT a mountpoint but contains files"
                else
                    print_info "$(basename $mp) is empty and not mounted (can be removed)"
                fi
            fi
        fi
    done
else
    print_error "/media directory does NOT exist"
fi

#================================================================
# 8. System Logs Analysis
#================================================================

print_header "8. Recent Mount/Block Device Errors in Logs"

echo "Checking system logs for mount errors (last 50 lines):"
echo ""

if command -v journalctl &>/dev/null; then
    echo "--- Journal errors (mount/block related) ---"
    journalctl -n 50 --no-pager | grep -iE "mount|block|sd[a-z]|nvme|error" | tail -20 || echo "No relevant errors found"
else
    echo "--- Syslog errors (mount/block related) ---"
    tail -100 /var/log/syslog 2>/dev/null | grep -iE "mount|block|sd[a-z]|nvme|error" | tail -20 || echo "No relevant errors found"
fi

#================================================================
# 9. Web UI Service Status
#================================================================

print_header "9. Hot-Swap Web UI Service Status"

if systemctl list-unit-files | grep -q "hotswap-webui"; then
    print_success "hotswap-webui service exists"
    echo "  Status: $(systemctl is-active hotswap-webui)"
    echo "  Enabled: $(systemctl is-enabled hotswap-webui 2>/dev/null || echo 'no')"

    if systemctl is-active --quiet hotswap-webui; then
        print_success "Service is running"
    else
        print_error "Service is NOT running"
        echo "  Recent logs:"
        journalctl -u hotswap-webui -n 20 --no-pager 2>/dev/null || echo "  (no logs available)"
    fi
else
    print_warning "hotswap-webui service not installed"
fi

#================================================================
# 10. Recommendations
#================================================================

print_header "10. Diagnostic Summary & Recommendations"

echo ""
echo -e "${BOLD}ISSUES DETECTED:${NC}"
echo ""

ISSUES_FOUND=0

# Check for missing packages
for entry in "${REQUIRED_PACKAGES[@]}"; do
    cmd="${entry%%:*}"
    pkg="${entry##*:}"
    if ! command -v "$cmd" &>/dev/null; then
        ((ISSUES_FOUND++))
        print_error "Missing: $cmd (package: $pkg)"
        echo "    Fix: apt-get install $pkg"
    fi
done

# Check for samba service
if ! systemctl is-active --quiet smbd && ! systemctl is-active --quiet samba; then
    ((ISSUES_FOUND++))
    print_error "Samba service not running"
    echo "    Fix: systemctl start smbd && systemctl enable smbd"
fi

# Check for devices with no filesystem
DEVICES=$(lsblk -ndo NAME | grep -E "^sd|^nvme|^vd")
for dev in $DEVICES; do
    DEVPATH="/dev/$dev"
    if [ -e "$DEVPATH" ]; then
        FSTYPE=$(blkid -s TYPE -o value "$DEVPATH" 2>/dev/null)
        if [ -z "$FSTYPE" ]; then
            ((ISSUES_FOUND++))
            print_warning "$DEVPATH has no recognizable filesystem"
            echo "    Fix: Format the device using the web UI or:"
            echo "         mkfs.ext4 $DEVPATH  (for Linux)"
            echo "         mkfs.ntfs $DEVPATH  (for Windows compatibility)"
        fi
    fi
done

# Check for permission issues
if [ ! -w "/media" ] 2>/dev/null; then
    ((ISSUES_FOUND++))
    print_error "/media directory is not writable"
    echo "    Fix: chmod 755 /media"
fi

if [ $ISSUES_FOUND -eq 0 ]; then
    echo ""
    print_success "No critical issues detected!"
    echo ""
    echo "If devices are still failing to mount, check:"
    echo "  1. Device is properly connected and recognized by system"
    echo "  2. Device has a valid filesystem (not corrupted)"
    echo "  3. Web UI logs: journalctl -u hotswap-webui -f"
    echo "  4. Manual mount test: mount /dev/sdX /tmp/test"
else
    echo ""
    print_warning "Found $ISSUES_FOUND issue(s) - see recommendations above"
fi

#================================================================
# 11. Quick Fix Commands
#================================================================

print_header "11. Quick Fix Commands"

echo ""
echo "To install all required packages:"
echo "  apt-get update && apt-get install -y util-linux ntfs-3g e2fsprogs exfatprogs dosfstools samba"
echo ""
echo "To restart services:"
echo "  systemctl restart smbd"
echo "  systemctl restart hotswap-webui"
echo ""
echo "To manually test mount a device:"
echo "  mkdir -p /tmp/mount-test"
echo "  mount /dev/sdX1 /tmp/mount-test"
echo "  ls -la /tmp/mount-test"
echo "  umount /tmp/mount-test"
echo ""
echo "To view web UI logs in real-time:"
echo "  journalctl -u hotswap-webui -f"
echo ""

#================================================================
# Completion
#================================================================

echo ""
echo -e "${BOLD}================================================================"
echo -e "Diagnostic Complete"
echo -e "================================================================${NC}"
echo "Full log saved to: $LOGFILE"
echo ""
echo "To run this diagnostic again:"
echo "  bash $0"
echo ""
