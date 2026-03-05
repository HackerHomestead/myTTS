# myTTS

Self-hosted text-to-speech toolchain with client/server architecture.

**Use cases:**
- Reading long-form text (white papers, articles)
- Conversational LLM interaction with Ollama

## Architecture

```
┌─────────────────┐          ┌─────────────────┐
│   Your Mac      │          │  GPU Server     │
│   (Client)      │─────────>│  (TTS Server)  │
│                 │  network  │                 │
│ mytts cli/ollama│          │  Coqui TTS     │
└─────────────────┘          │  Piper         │
                              └─────────────────┘
```

## Installation

### Client (macOS)

```bash
# Clone and install
pip install -e .
```

### Server (Linux with GPU)

```bash
# Install Piper (low-latency TTS)
# Option 1: Download binary
curl -sL https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz | tar xz
sudo cp piper /usr/local/bin/

# Option 2: Use piper-onnx Python package (recommended, works on more platforms)
pip install piper-onnx

# Download English voice model
mkdir -p ~/.local/share/piper/voices
curl -sL -o ~/.local/share/piper/voices/en_US-lessac-medium.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
curl -sL -o ~/.local/share/piper/voices/en_US-lessac-medium.onnx.json \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# Install myTTS server
pip install -e .
```

## Usage

### On GPU Server

```bash
# Start TTS server (listens on all interfaces)
mytts serve --host 0.0.0.0 --port 8000
```

### On Your Mac (Client)

```bash
# Read a file using remote TTS server
mytts read paper.txt --server --server-url http://192.168.1.100:8000

# Or save to file
mytts read paper.txt -o output.wav --server --server-url http://192.168.1.100:8000

# Chat with Ollama + TTS (both running on server)
mytts ollama --model llama3.2 --ollama-url http://192.168.1.100:11434 --tts-url http://192.168.1.100:8000

# Or with environment variables
export TTS_SERVER_URL=http://192.168.1.100:8000
export OLLAMA_URL=http://192.168.1.100:11434
mytts ollama --model llama3.2
```

### Python API

```python
from mytts import TTSEngine, TTSMode, TTSBackend

# Use remote TTS server
engine = TTSEngine(
    mode=TTSMode.CONVERSATIONAL,
    backend=TTSBackend.SERVER,
    server_url="http://192.168.1.100:8000"
)
engine.speak("Hello from Ollama!")

# Or use OllamaChat for LLM interaction
from mytts.ollama import OllamaChat

chat = OllamaChat(
    model="llama3.2",
    ollama_url="http://192.168.1.100:11434",
    tts_url="http://192.168.1.100:8000"
)
chat.interactive()
```

## Commands

| Command | Description |
|---------|-------------|
| `mytts read <file>` | Read text file aloud |
| `mytts speak <text>` | Speak text directly |
| `mytts chat` | Interactive TTS chat |
| `mytts serve` | Start TTS server |
| `mytts ollama` | Chat with Ollama + TTS |

## Available Voices

Piper voices (download from HuggingFace):
- https://huggingface.co/rhasspy/piper-voices/tree/main/en
