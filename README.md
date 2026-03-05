# myTTS

Self-hosted text-to-speech with client/server architecture for GPU offloading.

## Quick Start

### Step 1: Server (Linux with GPU)

```bash
# 1. Install dependencies
pip install -e .
pip install piper-onnx

# 2. Download a voice model
mkdir -p ~/.local/share/piper/voices
curl -sL -o ~/.local/share/piper/voices/en_US-lessac-medium.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
curl -sL -o ~/.local/share/piper/voices/en_US-lessac-medium.onnx.json \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# 3. Start the TTS server
mytts serve --host 0.0.0.0 --port 8000
```

### Step 2: Client (Your Mac)

```bash
# Install
pip install -e .

# Read a file (replace IP with your server's IP)
mytts read paper.txt --server --server-url http://192.168.1.100:8000

# Chat with Ollama + TTS (Ollama must also be running on server)
mytts ollama --tts-url http://192.168.1.100:8000 --ollama-url http://192.168.1.100:11434
```

---

## Server Setup (GPU Machine)

### Install

```bash
pip install -e .
```

### Voice Models

Download from https://huggingface.co/rhasspy/piper-voices/tree/main/en

Quick download (English medium quality):
```bash
mkdir -p ~/.local/share/piper/voices

curl -sL -o ~/.local/share/piper/voices/en_US-lessac-medium.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx

curl -sL -o ~/.local/share/piper/voices/en_US-lessac-medium.onnx.json \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

### Run Server

```bash
# Starts on port 8000, listens on all interfaces
mytts serve --host 0.0.0.0 --port 8000

# Or with custom voice
mytts serve --host 0.0.0.0 --port 8000 --voice en_US-lessac-medium
```

---

## Client Setup (Your Mac)

### Install

```bash
pip install -e .
```

### Usage

```bash
# Read a file aloud
mytts read document.txt --server --server-url http://SERVER_IP:8000

# Save to file
mytts read document.txt -o audio.wav --server --server-url http://SERVER_IP:8000

# Speak text directly
mytts speak "Hello world" --server --server-url http://SERVER_IP:8000

# Chat with Ollama (requires Ollama running on server at port 11434)
mytts ollama --model llama3.2 \
  --tts-url http://SERVER_IP:8000 \
  --ollama-url http://SERVER_IP:11434
```

### Environment Variables

```bash
# Set once, then omit --server-url flags
export TTS_SERVER_URL=http://192.168.1.100:8000
export OLLAMA_URL=http://192.168.1.100:11434

mytts read document.txt --server
mytts ollama --model llama3.2
```

---

## Python API

```python
from mytts import TTSEngine, TTSMode, TTSBackend

# Remote TTS server
engine = TTSEngine(
    backend=TTSBackend.SERVER,
    server_url="http://192.168.1.100:8000"
)
engine.speak("Hello!")

# With Ollama
from mytts.ollama import OllamaChat
chat = OllamaChat(
    model="llama3.2",
    ollama_url="http://192.168.1.100:11434",
    tts_url="http://192.168.1.100:8000"
)
chat.interactive()
```

---

## Commands

| Command | Description |
|---------|-------------|
| `mytts read <file>` | Read text file (use `--server` for remote) |
| `mytts speak <text>` | Speak text directly |
| `mytts serve` | Start TTS server (run on GPU machine) |
| `mytts ollama` | Chat with Ollama + speak responses |

## Finding Your Server IP

On the server, run:
```bash
hostname -I | awk '{print $1}'
```
