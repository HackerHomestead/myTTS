#!/bin/bash
# Check TTS server status

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.tts_server.pid"
LOG_FILE="$SCRIPT_DIR/server.log"

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo "Server status: STOPPED (no PID file)"
    exit 1
fi

PID=$(cat "$PID_FILE")

# Check if process is running
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "Server status: STOPPED (process not found)"
    rm -f "$PID_FILE"
    exit 1
fi

# Get process info
echo "Server status: RUNNING"
echo "  PID: $PID"
echo "  Started: $(ps -p "$PID" -o lstart= | xargs)"
echo "  Memory: $(ps -p "$PID" -o rss= | awk '{printf "%.1f MB", $1/1024}')"
echo "  CPU: $(ps -p "$PID" -o %cpu= | xargs)%"
echo "  Log: $LOG_FILE"

# Check if log file exists
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
    echo "  Log size: $LOG_SIZE"
    echo ""
    echo "Last 5 log lines:"
    tail -5 "$LOG_FILE" | sed 's/^/    /'
fi

# Test server health
echo ""
echo "Testing server health..."
if curl -s "http://localhost:8000/health" > /dev/null 2>&1; then
    echo "  Health check: OK"
else
    echo "  Health check: FAILED (server may be starting up)"
fi