#!/bin/bash

# Mac Organizer - Reload Script
# Run this after changing code in src/ or changing config.json

PLIST_DEST="$HOME/Library/LaunchAgents/com.user.macorganizer.plist"

echo "Reloading Mac Organizer Service..."

# Unload the service (stops the running instance)
launchctl unload "$PLIST_DEST" 2>/dev/null

# Load the service (starts the new instance with updated code/config)
launchctl load "$PLIST_DEST"

echo "✅ Service Reloaded! Changes are now active."
