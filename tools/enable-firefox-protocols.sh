#!/bin/bash
# Enable Firefox to use external protocol handlers for SMB and SFTP

echo "=== Configuring Firefox to Use External Protocol Handlers ==="
echo ""

# Find Firefox profile (check both snap and native locations)
FIREFOX_PROFILE=$(find ~/snap/firefox/common/.mozilla/firefox -maxdepth 1 -name "*.default*" -type d 2>/dev/null | head -1)

if [ -z "$FIREFOX_PROFILE" ]; then
    FIREFOX_PROFILE=$(find ~/.mozilla/firefox -maxdepth 1 -name "*.default*" -type d 2>/dev/null | head -1)
fi

if [ -z "$FIREFOX_PROFILE" ]; then
    echo "❌ Firefox profile not found. Please run Firefox at least once."
    echo ""
    echo "Manual steps:"
    echo "1. Open Firefox"
    echo "2. Type in address bar: about:config"
    echo "3. Click 'Accept the Risk and Continue'"
    echo "4. Search for: network.protocol-handler.external.smb"
    echo "5. Click + to add Boolean = true"
    echo "6. Do same for: network.protocol-handler.external.sftp"
    exit 1
fi

echo "✓ Found Firefox profile: $(basename $FIREFOX_PROFILE)"

# Check for prefs.js
PREFS_FILE="$FIREFOX_PROFILE/prefs.js"

if [ ! -f "$PREFS_FILE" ]; then
    echo "⚠️  Firefox hasn't been fully initialized yet"
    echo "   Please open Firefox once, then run this script again"
    exit 1
fi

# Backup prefs.js
BACKUP_FILE="$PREFS_FILE.backup.$(date +%s)"
cp "$PREFS_FILE" "$BACKUP_FILE"
echo "✓ Backed up prefs.js to: $(basename $BACKUP_FILE)"

# Add protocol handler preferences
echo ""
echo "Adding Firefox preferences..."

# Close Firefox if running (required for prefs.js changes)
if pgrep -x firefox > /dev/null; then
    echo "⚠️  Firefox is currently running"
    echo "   Please close ALL Firefox windows and run this script again"
    exit 1
fi

# Add protocol handlers to prefs.js
cat >> "$PREFS_FILE" << 'EOF'

// Enable external protocol handlers for SMB and SFTP
user_pref("network.protocol-handler.external.smb", true);
user_pref("network.protocol-handler.external.sftp", true);
user_pref("network.protocol-handler.external.ssh", true);
user_pref("network.protocol-handler.expose-all", false);
EOF

echo "✓ Added protocol handler preferences"
echo ""
echo "📋 Configuration complete!"
echo "   • SMB links will prompt for external handler"
echo "   • SFTP links will prompt for external handler"
echo "   • SSH links will prompt for external handler"
echo ""
echo "🎯 Next steps:"
echo "   1. Open Firefox"
echo "   2. Go to: http://192.168.1.233:8007/shares"
echo "   3. Click any SMB or SFTP link"
echo "   4. When prompted, type: /usr/bin/xdg-open"
echo "   5. Check: 'Remember my choice'"
echo "   6. Future clicks will open automatically!"
echo ""
