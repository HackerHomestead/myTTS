# TTS Server Management Scripts

Quick scripts to manage the TTS server.

## Usage

### Start Server
```bash
./start_server.sh
```

Options (environment variables):
- `TTS_HOST` - Server host (default: 0.0.0.0)
- `TTS_PORT` - Server port (default: 8000)
- `TTS_CPU` - Force CPU mode (default: false)

Examples:
```bash
# Start with defaults
./start_server.sh

# Start on different port
TTS_PORT=9000 ./start_server.sh

# Start in CPU mode
TTS_CPU=true ./start_server.sh
```

### Stop Server
```bash
./stop_server.sh
```

Gracefully stops the server. Will force kill if needed.

### Check Status
```bash
./status_server.sh
```

Shows:
- Server status (running/stopped)
- PID and process info
- Memory and CPU usage
- Recent log entries
- Health check

## Logs

Server logs are written to `server.log`:
```bash
# View logs
tail -f server.log

# View last 100 lines
tail -100 server.log
```

## PID File

The server PID is stored in `.tts_server.pid`. This file is automatically managed by the scripts.