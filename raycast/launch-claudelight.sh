#!/bin/bash

# Raycast Script Command — https://github.com/raycast/script-commands
#
# @raycast.schemaVersion 1
# @raycast.title Launch Claudelight
# @raycast.mode silent
#
# Optional parameters:
# @raycast.packageName Claudelight
# @raycast.icon 🚦
# @raycast.description Start the Claudelight menu bar traffic light (no-op if already running)
# @raycast.author shay

PYTHON="/opt/homebrew/bin/python3"
APP="/Users/shay/Documents/Claude/Projects/Claudelight/app.py"

if pgrep -f "$APP" >/dev/null 2>&1; then
  echo "Claudelight already running"
  exit 0
fi

nohup "$PYTHON" "$APP" >/dev/null 2>&1 &
disown

echo "Claudelight launched"
