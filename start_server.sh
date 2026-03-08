#!/bin/bash
# Start TTS server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.tts_server.pid"
LOG_FILE="$SCRIPT_DIR/server.log"

# Default settings
HOST="${TTS_HOST:-0.0.0.0}"
PORT="${TTS_PORT:-8000}"
CPU_MODE="${TTS_CPU:-false}"

# Check if server is already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Server already running (PID: $PID)"
        exit 1
    else
        echo "Removing stale PID file"
        rm -f "$PID_FILE"
    fi
fi

echo "Starting TTS server..."
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  CPU Mode: $CPU_MODE"
echo "  Log: $LOG_FILE"

# Activate virtual environment if it exists
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Start server
if [ "$CPU_MODE" = "true" ]; then
    python3 -m mytts.cli serve --host "$HOST" --port "$PORT" --cpu > "$LOG_FILE" 2>&1 &
else
    python3 -m mytts.cli serve --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &
fi

SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"

echo "Server started (PID: $SERVER_PID)"
echo "Check logs: tail -f $LOG_FILE"
echo "Test server: curl http://localhost:$PORT/health"