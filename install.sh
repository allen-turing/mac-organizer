#!/bin/bash

# Mac Organizer - Installation Script

set -e

# Get the absolute path of the current directory
PROJECT_DIR="$(pwd)"
VENV_DIR="$PROJECT_DIR/venv"
SRC_DIR="$PROJECT_DIR/src"
PLIST_NAME="com.user.macorganizer.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"
LOG_DIR="$HOME/Library/Logs"

echo "Installing Mac Organizer..."
echo "Project Directory: $PROJECT_DIR"

# 1. Check/Create Virtual Environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists."
fi

# 2. Install Dependencies
echo "Installing dependencies..."
"$VENV_DIR/bin/pip" install -r requirements.txt

# 3. Create Launch Agent Plist dynamically
echo "Configuring background service..."

cat <<EOF > "$PLIST_NAME"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.macorganizer</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/python</string>
        <string>$SRC_DIR/organizer.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/mac-organizer.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/mac-organizer.err</string>
</dict>
</plist>
EOF

# 4. Install Plist
cp "$PLIST_NAME" "$PLIST_DEST"
rm "$PLIST_NAME" # Remove the temporary local file

# 5. Load Service
# Unload first if exists to force update
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"

echo "-----------------------------------"
echo "✅ Installation Complete!"
echo "The service is running in the background."
echo "Logs: $LOG_DIR/mac-organizer.log"
echo "To uninstall, run: ./uninstall.sh"
