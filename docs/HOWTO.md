# Development and Testing Workflow Guide

## Overview

This guide documents the complete workflow for developing, testing, and deploying changes to the myTTS system. It covers both local development and remote server synchronization.

## System Architecture

```
┌─────────────────────┐         ┌──────────────────────┐
│  Local Machine       │         │  Remote Server       │
│  (macOS/Linux)       │         │  (192.168.88.164)    │
│                     │         │                      │
│  - Development      │         │  - TTS Server        │
│  - Testing         │  push/  │  - GPU Acceleration  │
│  - Git Repository   │◄───────►│  - Git Repository    │
│                     │  pull   │  - Voice Models     │
└─────────────────────┘         └──────────────────────┘
```

## Prerequisites

### Local Machine
- Python 3.10+
- Git
- pytest, pytest-cov
- Access to remote server via SSH

### Remote Server
- Python 3.10+
- GPU with CUDA support (optional)
- TTS models installed
- Server running on port 8000

## Quick Reference

### Server Management
```bash
# Check server status
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./status_server.sh"

# Start server
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./start_server.sh"

# Stop server
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./stop_server.sh"

# Restart server
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./stop_server.sh && sleep 2 && ./start_server.sh"

# Check server logs
ssh bradya@192.168.88.164 "tail -50 /ironwolf4TB/data01/projects/myTTS/server.log"
```

### Testing
```bash
# Run unit tests
pytest tests/test_client.py -v

# Run comprehensive tests
python test_comprehensive.py

# Run server durability tests
python test_server_durability.py

# Run all tests with coverage
pytest tests/ --cov=mytts --cov-report=term-missing
```

### Git Workflow
```bash
# Check status
git status

# Commit changes
git add <files>
git commit -m "message"

# Push to remote
git push origin main

# Pull on server
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && git pull origin main"
```

## Detailed Workflows

### Workflow 1: Making Code Changes

#### Step 1: Make Changes Locally
```bash
# Edit files
vim mytts/client.py

# Run tests to verify changes
pytest tests/test_client.py -v
```

#### Step 2: Commit Changes
```bash
# Check what changed
git diff

# Stage changes
git add mytts/client.py

# Commit with descriptive message
git commit -m "fix: Description of what was changed and why"
```

#### Step 3: Push to Remote Repository
```bash
git push origin main
```

#### Step 4: Update Server
```bash
# Fetch latest changes
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && git fetch origin"

# Check what will be updated
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && git log --oneline origin/main -3"

# Pull changes
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && git pull origin main"
```

#### Step 5: Restart Server (if needed)
```bash
# Only needed if server code changed
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./stop_server.sh && sleep 2 && ./start_server.sh"
```

#### Step 6: Verify Deployment
```bash
# Check server health
curl http://192.168.88.164:8000/health

# Run comprehensive tests
python test_comprehensive.py
```

### Workflow 2: Testing Changes

#### Unit Tests (Fast, No Server Required)
```bash
# Run specific test file
pytest tests/test_client.py -v

# Run specific test
pytest tests/test_client.py::TestProgressiveTTSClient::test_increase_speed -v

# Run with coverage
pytest tests/test_client.py --cov=mytts.client --cov-report=term-missing
```

#### Integration Tests (Requires Server)
```bash
# Ensure server is running
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./status_server.sh"

# Run comprehensive tests
python test_comprehensive.py

# Run durability tests
python test_server_durability.py
```

#### TUI Testing (Manual)
```bash
# Start TUI with test file
python -m mytts.cli read --tui --server-url http://192.168.88.164:8000 docs/nihms-1506969.txt

# Test controls:
# - Arrow keys: Navigate chunks
# - Enter: Jump to selected chunk
# - Space: Pause/Resume
# - +/-: Adjust speed
# - v: Cycle voices
# - q: Quit
```

### Workflow 3: Server Management

#### Starting the Server
```bash
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./start_server.sh"
```

Expected output:
```
Starting TTS server...
  Host: 0.0.0.0
  Port: 8000
  CPU Mode: false
  Log: /ironwolf4TB/data01/projects/myTTS/server.log
Server started (PID: 12345)
```

#### Checking Server Status
```bash
# Method 1: Using status script
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./status_server.sh"

# Method 2: Check process
ssh bradya@192.168.88.164 "ps aux | grep 'uvicorn mytts.server' | grep -v grep"

# Method 3: Health endpoint
curl http://192.168.88.164:8000/health
```

#### Stopping the Server
```bash
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./stop_server.sh"
```

#### Viewing Server Logs
```bash
# Last 50 lines
ssh bradya@192.168.88.164 "tail -50 /ironwolf4TB/data01/projects/myTTS/server.log"

# Follow logs in real-time
ssh bradya@192.168.88.164 "tail -f /ironwolf4TB/data01/projects/myTTS/server.log"

# Search for errors
ssh bradya@192.168.88.164 "grep ERROR /ironwolf4TB/data01/projects/myTTS/server.log | tail -20"
```

### Workflow 4: Debugging Issues

#### Server 500 Errors
```bash
# 1. Check server logs
ssh bradya@192.168.88.164 "tail -100 /ironwolf4TB/data01/projects/myTTS/server.log"

# 2. Look for specific error
ssh bradya@192.168.88.164 "grep -A 10 'RuntimeError' /ironwolf4TB/data01/projects/myTTS/server.log"

# 3. Restart server
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./stop_server.sh && sleep 2 && ./start_server.sh"

# 4. Test with simple request
curl -X POST http://192.168.88.164:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Test sentence.", "voice": "en_US-lessac-medium"}' \
  -o /tmp/test.wav
```

#### Audio Issues (Popping/Clicking)
```bash
# 1. Check audio configuration
python -c "
from mytts.client import ProgressiveTTSClient
from mytts import TTSEngine, TTSMode, TTSBackend
from unittest.mock import Mock

engine = Mock()
client = ProgressiveTTSClient(engine)
print(client.get_audio_config())
"

# 2. Verify buffer settings
# - audio_buffer_size should be 4096
# - audio_latency should be 'high'

# 3. Check if issue persists
# - Test with different buffer sizes
# - Test with different latency settings
```

#### TUI Display Issues
```bash
# 1. Check terminal size
# - TUI should adapt to terminal size
# - Try resizing terminal window

# 2. Check for error logs
cat tui_errors.log

# 3. Test with simple file
echo "Test sentence one. Test sentence two." > /tmp/test.txt
python -m mytts.cli read --tui --server-url http://192.168.88.164:8000 /tmp/test.txt
```

#### PortAudio Errors
```bash
# Error: "PaMacCore (AUHAL) Error on line 2796: err='-50'"

# This is caused by:
# 1. Calling sd.stop() when not playing
# 2. Rapid start/stop of audio playback

# Solution: Use action queue (already implemented)
# - Actions are queued and processed sequentially
# - 150ms delay between stop and start
```

### Workflow 5: Complete Deployment Cycle

#### Full Deployment from Scratch
```bash
# 1. Make changes locally
vim mytts/client.py

# 2. Run unit tests
pytest tests/test_client.py -v

# 3. Commit changes
git add mytts/client.py
git commit -m "fix: Description of changes"

# 4. Push to remote
git push origin main

# 5. Update server code
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && git pull origin main"

# 6. Restart server
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./stop_server.sh && sleep 2 && ./start_server.sh"

# 7. Wait for server to start
sleep 5

# 8. Verify server health
curl http://192.168.88.164:8000/health

# 9. Run integration tests
python test_comprehensive.py

# 10. Run durability tests
python test_server_durability.py

# 11. Manual TUI test
python -m mytts.cli read --tui --server-url http://192.168.88.164:8000 docs/nihms-1506969.txt
```

## Test-Driven Development (TDD) Workflow

### Red-Green-Refactor Cycle

#### Step 1: Write Failing Test (Red)
```bash
# Create test file
cat > tests/test_new_feature.py << 'EOF'
def test_new_feature():
    """Test new feature."""
    client = ProgressiveTTSClient(mock_engine)
    # This should fail because feature doesn't exist yet
    assert client.new_feature() == expected_result
EOF

# Run test - should FAIL
pytest tests/test_new_feature.py -v
```

#### Step 2: Implement Feature (Green)
```bash
# Edit code to make test pass
vim mytts/client.py

# Run test - should PASS
pytest tests/test_new_feature.py -v
```

#### Step 3: Refactor (Optional)
```bash
# Improve code without changing behavior
vim mytts/client.py

# Run test - should still PASS
pytest tests/test_new_feature.py -v
```

#### Step 4: Commit
```bash
git add tests/test_new_feature.py mytts/client.py
git commit -m "feat: Add new feature with tests"
```

## Common Patterns

### Pattern 1: Fixing a Bug
```bash
# 1. Write test that reproduces bug
pytest tests/test_client.py::test_bug_case -v  # FAILS

# 2. Fix the bug
vim mytts/client.py

# 3. Verify test passes
pytest tests/test_client.py::test_bug_case -v  # PASSES

# 4. Run all tests
pytest tests/test_client.py -v

# 5. Commit
git add mytts/client.py tests/test_client.py
git commit -m "fix: Description of bug fix"
```

### Pattern 2: Adding a Feature
```bash
# 1. Write test for new feature
pytest tests/test_client.py::test_new_feature -v  # FAILS

# 2. Implement feature
vim mytts/client.py

# 3. Verify test passes
pytest tests/test_client.py::test_new_feature -v  # PASSES

# 4. Run all tests
pytest tests/test_client.py -v

# 5. Commit
git add mytts/client.py tests/test_client.py
git commit -m "feat: Add new feature"
```

### Pattern 3: Server-Side Changes
```bash
# 1. Make changes to server code
vim mytts/server.py

# 2. Commit and push
git add mytts/server.py
git commit -m "fix: Server-side fix"
git push origin main

# 3. Update server
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && git pull origin main"

# 4. Restart server
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./stop_server.sh && sleep 2 && ./start_server.sh"

# 5. Test server
python test_server_durability.py
```

## Troubleshooting Guide

### Issue: Tests Fail After Pulling from Server
**Symptom:** Tests pass locally but fail after pulling to server.

**Solution:**
```bash
# 1. Check if server code is in sync
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && git log --oneline -3"
git log --oneline -3

# 2. If out of sync, fetch and pull
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && git fetch origin && git pull origin main"

# 3. Restart server
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./stop_server.sh && sleep 2 && ./start_server.sh"
```

### Issue: Server Won't Start
**Symptom:** Server fails to start or exits immediately.

**Solution:**
```bash
# 1. Check logs
ssh bradya@192.168.88.164 "tail -100 /ironwolf4TB/data01/projects/myTTS/server.log"

# 2. Check if port is in use
ssh bradya@192.168.88.164 "lsof -i :8000"

# 3. Kill any existing process
ssh bradya@192.168.88.164 "pkill -f 'uvicorn mytts.server'"

# 4. Try starting again
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./start_server.sh"
```

### Issue: GPU Not Being Used
**Symptom:** Server running in CPU mode despite GPU being available.

**Solution:**
```bash
# 1. Check GPU status
ssh bradya@192.168.88.164 "nvidia-smi"

# 2. Check server health endpoint
curl http://192.168.88.164:8000/health | python -m json.tool | grep -A 5 gpu

# 3. Restart server
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./stop_server.sh && sleep 2 && ./start_server.sh"
```

### Issue: Audio Quality Problems
**Symptom:** Audio has pops, clicks, or distortion.

**Solution:**
```bash
# 1. Check audio configuration
python -c "
from mytts.client import ProgressiveTTSClient
from unittest.mock import Mock
client = ProgressiveTTSClient(Mock())
print(client.get_audio_config())
"

# 2. Verify settings
# - buffer_size: 4096
# - latency: 'high'

# 3. If settings are wrong, update client initialization
vim mytts/tui.py  # or wherever client is created
```

## Best Practices

### Git Commit Messages
```bash
# Good commit messages:
git commit -m "fix: Prevent PortAudio errors by tracking playback state"
git commit -m "feat: Add voice cycling to TUI with 'v' key"
git commit -m "test: Add unit tests for audio fade functionality"
git commit -m "docs: Update HOWTO with server management section"

# Bad commit messages:
git commit -m "fixed stuff"
git commit -m "updates"
git commit -m "WIP"
```

### Testing Before Committing
```bash
# Always run tests before committing:
pytest tests/test_client.py -v
python test_comprehensive.py

# If tests fail, fix before committing
```

### Server Synchronization
```bash
# Always verify both sides are in sync:
# Local:
git log --oneline -3

# Server:
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && git log --oneline -3"

# Should show same commits
```

### Restarting Server After Changes
```bash
# Server restart is needed when:
# - mytts/server.py changed
# - mytts/engine/*.py changed
# - Any server-side code changed

# Server restart is NOT needed when:
# - mytts/client.py changed (client-side only)
# - mytts/tui.py changed (client-side only)
# - mytts/cli.py changed (client-side only)
# - Tests changed
```

## Quick Command Reference

### Local Development
```bash
# Run tests
pytest tests/test_client.py -v
python test_comprehensive.py
python test_server_durability.py

# Check coverage
pytest --cov=mytts --cov-report=html
open htmlcov/index.html

# Format code (if using black)
black mytts/
```

### Git Operations
```bash
# Status
git status

# Diff
git diff
git diff mytts/client.py

# Commit
git add <files>
git commit -m "message"

# Push
git push origin main

# Pull
git pull origin main
```

### Server Operations
```bash
# SSH to server
ssh bradya@192.168.88.164

# Check server
ssh bradya@192.168.88.164 "ps aux | grep uvicorn"

# View logs
ssh bradya@192.168.88.164 "tail -f /ironwolf4TB/data01/projects/myTTS/server.log"

# Restart server
ssh bradya@192.168.88.164 "cd /ironwolf4TB/data01/projects/myTTS && ./stop_server.sh && sleep 2 && ./start_server.sh"
```

### Health Checks
```bash
# Server health
curl http://192.168.88.164:8000/health

# Server voices
curl http://192.168.88.164:8000/voices

# Test TTS
curl -X POST http://192.168.88.164:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Test", "voice": "en_US-lessac-medium"}' \
  -o /tmp/test.wav
```

## Summary

The key workflow is:
1. **Make changes locally**
2. **Test locally** (unit tests)
3. **Commit and push**
4. **Update server** (git pull)
5. **Restart server** (if needed)
6. **Test integration** (comprehensive tests)
7. **Verify deployment** (health checks, manual testing)

Always ensure both local and server are synchronized before testing integration features.
