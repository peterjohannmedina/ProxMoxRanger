#!/bin/bash
# Configure Firefox to use xdg-open for SFTP and SMB protocol handlers

echo "=== Configuring Firefox Protocol Handlers ==="
echo ""

# Find Firefox profile directory
FIREFOX_PROFILE=$(find ~/.mozilla/firefox -maxdepth 1 -name "*.default*" -type d 2>/dev/null | head -1)

if [ -z "$FIREFOX_PROFILE" ]; then
    echo "❌ Firefox profile not found. Please run Firefox at least once."
    echo ""
    echo "Alternative: Configure manually when Firefox prompts:"
    echo "   1. Click any SFTP/SMB link"
    echo "   2. Select 'Choose other application...'"
    echo "   3. Type: /usr/bin/xdg-open"
    echo "   4. Check 'Remember my choice'"
    echo "   5. Click 'Open link'"
    exit 1
fi

echo "✓ Found Firefox profile: $FIREFOX_PROFILE"

# Create handlers.json if it doesn't exist
HANDLERS_FILE="$FIREFOX_PROFILE/handlers.json"

# Backup existing handlers
if [ -f "$HANDLERS_FILE" ]; then
    BACKUP_FILE="$HANDLERS_FILE.backup.$(date +%s)"
    cp "$HANDLERS_FILE" "$BACKUP_FILE"
    echo "✓ Backed up existing handlers to: $(basename $BACKUP_FILE)"
fi

# Create new handlers configuration
cat > "$HANDLERS_FILE" << 'EOF'
{
  "defaultHandlersVersion": {
    "en-US": 4
  },
  "mimeTypes": {},
  "schemes": {
    "sftp": {
      "action": 2,
      "handlers": [
        {
          "name": "xdg-open",
          "path": "/usr/bin/xdg-open"
        }
      ]
    },
    "smb": {
      "action": 2,
      "handlers": [
        {
          "name": "xdg-open",
          "path": "/usr/bin/xdg-open"
        }
      ]
    },
    "ssh": {
      "action": 2,
      "handlers": [
        {
          "name": "xdg-open",
          "path": "/usr/bin/xdg-open"
        }
      ]
    }
  }
}
EOF

echo "✓ Firefox handlers configured successfully!"
echo ""
echo "📋 Configured protocols:"
echo "   • sftp:// → xdg-open → Nautilus"
echo "   • smb://  → xdg-open → Nautilus"
echo "   • ssh://  → xdg-open → Nautilus"
echo ""
echo "⚠️  IMPORTANT: Close and restart Firefox completely for changes to take effect"
echo ""
echo "🧪 Test it:"
echo "   1. Close ALL Firefox windows"
echo "   2. Reopen Firefox"
echo "   3. Go to: http://192.168.1.233:8007/shares"
echo "   4. Click any 🔐 or 🌐 link"
echo "   5. Link should open directly in Nautilus without prompts!"
echo ""
