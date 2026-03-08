#!/bin/bash
# Stop TTS server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.tts_server.pid"

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo "No PID file found. Server may not be running."
    exit 1
fi

PID=$(cat "$PID_FILE")

# Check if process is running
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "Server process not found (PID: $PID)"
    rm -f "$PID_FILE"
    exit 1
fi

echo "Stopping TTS server (PID: $PID)..."

# Try graceful shutdown first
kill "$PID" 2>/dev/null

# Wait for process to stop
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "Server stopped gracefully"
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# Force kill if still running
echo "Server didn't stop gracefully, forcing shutdown..."
kill -9 "$PID" 2>/dev/null
sleep 1

if ps -p "$PID" > /dev/null 2>&1; then
    echo "Failed to stop server"
    exit 1
else
    echo "Server stopped (forced)"
    rm -f "$PID_FILE"
    exit 0
fi