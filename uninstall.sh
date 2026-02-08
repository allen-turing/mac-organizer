#!/bin/bash

# Mac Organizer - Uninstallation Script

PLIST_NAME="com.user.macorganizer.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "Uninstalling Mac Organizer..."

# 1. Unload and Remove Service
if [ -f "$PLIST_DEST" ]; then
    echo "Stopping background service..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    rm "$PLIST_DEST"
    echo "Service removed."
else
    echo "Service not found."
fi

# 2. Optional: Remove Virtual Environment
# read -p "Do you want to delete the virtual environment (venv)? [y/N] " response
# if [[ "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]; then
#    rm -rf venv
#    echo "Virtual environment removed."
# fi

echo "-----------------------------------"
echo "✅ Uninstallation Complete!"
