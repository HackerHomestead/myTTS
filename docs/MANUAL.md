# myTTS User Manual

A comprehensive guide to using myTTS - from beginner to advanced.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Basic Usage](#basic-usage)
4. [Client/Server Setup](#clientserver-setup)
5. [Voice Selection](#voice-selection)
6. [Advanced Features](#advanced-features)
7. [Integration Examples](#integration-examples)
8. [Troubleshooting](#troubleshooting)
9. [API Reference](#api-reference)

---

## Introduction

### What is myTTS?

myTTS is a self-hosted text-to-speech system that lets you convert text into natural-sounding speech. It supports:

- **Multiple voices** - 7 different English voices with various qualities
- **GPU acceleration** - Fast synthesis on NVIDIA GPUs
- **Client/server architecture** - Offload processing to a remote server
- **Progressive playback** - Start playing while still generating
- **Local mode** - Works entirely offline

### Who is this for?

- **Developers** building voice-enabled applications
- **Content creators** needing text-to-speech for videos
- **Accessibility projects** requiring speech synthesis
- **AI enthusiasts** integrating TTS with LLMs like Ollama

---

## Getting Started

### Step 1: Installation

Choose your installation path:

#### Option A: Quick Install (Local Mode)

For simple, local text-to-speech:

```bash
# Clone the repository
git clone https://github.com/yourname/myTTS.git
cd myTTS

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install myTTS
pip install -e .

# Install Piper (recommended engine)
pip install piper-onnx

# Download a voice
mkdir -p ~/.local/share/piper/voices
cd ~/.local/share/piper/voices
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

#### Option B: Client/Server Setup

For GPU-accelerated synthesis with a remote server:

**On the server (Linux with NVIDIA GPU):**

```bash
# Install system dependencies
sudo apt update
sudo apt install python3.10-venv python3.10-dev

# Clone and setup
git clone https://github.com/yourname/myTTS.git
cd myTTS
python3 -m venv venv
source venv/bin/activate

# Install myTTS
pip install -e .

# Install GPU dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install piper-onnx onnxruntime-gpu

# Download voices
./scripts/download_voices.sh

# Start the server
mytts serve --host 0.0.0.0 --port 8000
```

**On your client (Mac/Windows/Linux):**

```bash
# Clone and setup
git clone https://github.com/yourname/myTTS.git
cd myTTS
python3 -m venv venv
source venv/bin/activate

# Install myTTS
pip install -e .

# Set server URL
export TTS_SERVER_URL=http://YOUR_SERVER_IP:8000
```

### Step 2: Verify Installation

Test that everything works:

```bash
# Local mode test
mytts speak "Hello, this is a test."

# Server mode test (if using client/server)
mytts speak "Hello from the server." --server
```

---

## Basic Usage

### Speaking Text Directly

The simplest way to use myTTS:

```bash
# Speak a phrase
mytts speak "Welcome to myTTS!"

# Use a specific voice
mytts speak "Hello there!" --voice en_US-amy-medium

# Use server mode
mytts speak "Processing on GPU." --server
```

### Reading Files

Convert text files to speech:

```bash
# Read a text file
mytts read document.txt

# Read and save to audio file
mytts read article.txt -o output.wav

# Read from server
mytts read paper.txt --server
```

### Interactive Chat Mode

Type and have it spoken immediately:

```bash
# Start chat mode
mytts chat

# With server
mytts chat --server

# With specific voice
mytts chat --voice en_US-ryan-medium --server
```

**Example session:**
```
$ mytts chat --server
Chat mode - type text to speak (Ctrl+C to exit)
> Hello, how are you today?
[Speaking...]
> I'm doing great, thanks for asking!
[Speaking...]
> ^C
```

---

## Client/Server Setup

### Why Use Client/Server?

| Feature | Local Mode | Server Mode |
|---------|-----------|-------------|
| GPU acceleration | No | Yes |
| Voice variety | Limited | Full |
| Network required | No | Yes |
| Processing load | On your machine | On server |
| Multiple clients | N/A | Yes |

### Server Configuration

#### Basic Server

```bash
# Start on default port (8000)
mytts serve

# Custom host and port
mytts serve --host 0.0.0.0 --port 9000

# CPU-only mode (no GPU)
mytts serve --cpu
```

#### Background Server

Run the server in the background:

```bash
# Start in background
nohup mytts serve --host 0.0.0.0 --port 8000 > server.log 2>&1 &
echo $! > server.pid

# Check if running
curl http://localhost:8000/health

# Stop the server
kill $(cat server.pid)
```

#### Using the Management Scripts

```bash
# Start server
./start_server.sh

# Check status
./status_server.sh

# Stop server
./stop_server.sh
```

### Client Configuration

#### Environment Variables

Set once, use everywhere:

```bash
# Add to ~/.bashrc or ~/.zshrc
export TTS_SERVER_URL=http://192.168.1.100:8000

# Now you can use --server without --server-url
mytts speak "Hello" --server
mytts read document.txt --server
```

#### Per-Command Configuration

```bash
# Specify server URL each time
mytts speak "Hello" --server --server-url http://192.168.1.100:8000
```

### Health Monitoring

Check server status:

```bash
# Basic health check
curl http://SERVER_IP:8000/health

# Pretty-printed
curl http://SERVER_IP:8000/health | jq '.'

# Check specific info
curl http://SERVER_IP:8000/health | jq '.gpu'
curl http://SERVER_IP:8000/health | jq '.memory'
```

**Health response:**
```json
{
  "status": "ok",
  "engines": ["piper:en_US-lessac-medium:None"],
  "memory": {
    "total": 33501102080,
    "available": 16000000000,
    "percent": 52.2
  },
  "gpu": {
    "available": true,
    "device_count": 1,
    "memory_allocated": 243990528
  }
}
```

---

## Voice Selection

### Available Voices

myTTS includes 7 English voices:

| Voice | Gender | Best For |
|-------|--------|----------|
| **lessac** | Neutral | General purpose, default choice |
| **amy** | Female | Friendly, conversational |
| **norman** | Male | Professional, narration |
| **john** | Male | Clear, instructional |
| **danny** | Male | Casual, informal |
| **kathleen** | Female | Warm, storytelling |
| **ryan** | Male | Versatile, balanced |

### Quality Levels

Each voice has quality variants:

| Quality | Speed | Audio Quality | Use Case |
|---------|-------|---------------|----------|
| **medium** | Fast | Good | Default, most uses |
| **high** | Slower | Excellent | Professional content |
| **low** | Fastest | Acceptable | Quick previews |

### Choosing a Voice

```bash
# List available voices
curl http://SERVER_IP:8000/voices

# Use a specific voice
mytts speak "Hello!" --voice en_US-amy-medium --server

# Test different voices
for voice in lessac amy norman john ryan; do
  echo "Testing $voice..."
  mytts speak "This is the $voice voice." --voice en_US-$voice-medium --server
done
```

### Voice Comparison Script

Create a script to compare voices:

```bash
#!/bin/bash
# compare_voices.sh

VOICES="lessac amy norman john ryan"
TEXT="The quick brown fox jumps over the lazy dog."

for voice in $VOICES; do
  echo "Playing $voice..."
  mytts speak "$TEXT" --voice en_US-$voice-medium --server
  sleep 1
done
```

---

## Advanced Features

### Progressive TTS

Progressive TTS splits text into sentences and generates them in parallel while playing:

```bash
# Use progressive mode (default with --server)
mytts read long_document.txt --server

# Configure workers and buffer
mytts read document.txt --server --workers 4 --buffer-size 2
```

**How it works:**
1. Text is split into sentences
2. Multiple workers generate audio in parallel
3. Playback starts before all generation completes
4. Next sentences are pre-generated while current one plays

### Python API

#### Basic Usage

```python
from mytts import TTSEngine, TTSBackend

# Create engine
engine = TTSEngine(
    backend=TTSBackend.SERVER,
    server_url="http://192.168.1.100:8000",
    voice="en_US-lessac-medium"
)

# Speak text
engine.speak("Hello from Python!")

# Read file
engine.speak(file_path="document.txt")

# Save to file
engine.speak("Save this to audio", output="output.wav")
```

#### Progressive TTS Client

```python
from mytts import TTSEngine, TTSBackend
from mytts.client import ProgressiveTTSClient

# Create engine
engine = TTSEngine(
    backend=TTSBackend.SERVER,
    server_url="http://192.168.1.100:8000"
)

# Create progressive client
client = ProgressiveTTSClient(
    engine,
    num_workers=4,    # Parallel generation threads
    buffer_size=2    # Sentences to pre-generate
)

# Speak with look-ahead processing
stats = client.speak("This is a long text. It has multiple sentences. Each is processed in parallel.")

print(f"Generated {stats['chunks_generated']} chunks")
print(f"Generation time: {stats['total_generation_time']:.2f}s")
print(f"Playback time: {stats['total_playback_time']:.2f}s")

# Clean up
client.close()
```

#### Streaming TTS

For real-time applications (like LLM output):

```python
from mytts.client import StreamingTTSClient
from mytts import TTSEngine, TTSBackend

engine = TTSEngine(backend=TTSBackend.SERVER, server_url="http://192.168.1.100:8000")
client = StreamingTTSClient(engine, num_workers=4, lookahead=2)

# Start playback thread
client.play()

# Feed text as it arrives
client.feed("First sentence.")
client.feed("Second sentence.")
client.feed("Third sentence.")

# Stop when done
client.stop()
client.close()
```

### Integration with Ollama

Chat with an LLM and hear responses:

```bash
# Start Ollama chat with TTS
mytts ollama --model llama3.2 --tts-url http://SERVER_IP:8000

# With custom Ollama URL
mytts ollama --model llama3.2 \
  --tts-url http://SERVER_IP:8000 \
  --ollama-url http://OLLAMA_IP:11434
```

**Example session:**
```
$ mytts ollama --model llama3.2
Chatting with llama3.2. Responses will be spoken.
Type your message (or 'quit' to exit):
You: What is machine learning?
AI: [Speaking] Machine learning is a branch of artificial intelligence...
You: Tell me more
AI: [Speaking] It involves training algorithms on data...
You: quit
Goodbye!
```

---

## Integration Examples

### Example 1: Reading News Articles

```bash
#!/bin/bash
# read_news.sh

# Download article as text
curl -s "https://example.com/article.txt" > article.txt

# Read it aloud
mytts read article.txt --server --voice en_US-norman-medium

# Or save for later
mytts read article.txt -o news_podcast.wav --server
```

### Example 2: Document to Audiobook

```python
# audiobook.py
import sys
from mytts import TTSEngine, TTSBackend

def text_to_audiobook(input_file, output_file, voice="en_US-lessac-medium"):
    engine = TTSEngine(
        backend=TTSBackend.SERVER,
        server_url="http://192.168.1.100:8000",
        voice=voice
    )
    
    engine.speak(file_path=input_file, output=output_file)
    print(f"Created audiobook: {output_file}")

if __name__ == "__main__":
    text_to_audiobook(sys.argv[1], sys.argv[2])
```

**Usage:**
```bash
python audiobook.py my_book.txt my_book.wav
```

### Example 3: Voice Assistant

```python
# assistant.py
from mytts import TTSEngine, TTSBackend
import requests

def voice_assistant(query):
    # Get response from LLM
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3.2", "prompt": query, "stream": False}
    )
    
    answer = response.json()["response"]
    
    # Speak the response
    engine = TTSEngine(
        backend=TTSBackend.SERVER,
        server_url="http://192.168.1.100:8000"
    )
    engine.speak(answer)

if __name__ == "__main__":
    while True:
        query = input("Ask: ")
        if query.lower() in ["quit", "exit"]:
            break
        voice_assistant(query)
```

### Example 4: Batch Processing

```python
# batch_tts.py
from mytts import TTSEngine, TTSBackend
from pathlib import Path

def batch_convert(input_dir, output_dir, voice="en_US-lessac-medium"):
    engine = TTSEngine(
        backend=TTSBackend.SERVER,
        server_url="http://192.168.1.100:8000",
        voice=voice
    )
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    for text_file in input_path.glob("*.txt"):
        output_file = output_path / f"{text_file.stem}.wav"
        print(f"Converting {text_file.name}...")
        engine.speak(file_path=str(text_file), output=str(output_file))
    
    print(f"Converted {len(list(input_path.glob('*.txt')))} files")

batch_convert("documents/", "audio/")
```

### Example 5: Web API Wrapper

```python
# web_api.py
from fastapi import FastAPI
from pydantic import BaseModel
from mytts import TTSEngine, TTSBackend
import tempfile

app = FastAPI()
engine = TTSEngine(
    backend=TTSBackend.SERVER,
    server_url="http://192.168.1.100:8000"
)

class TTSRequest(BaseModel):
    text: str
    voice: str = "en_US-lessac-medium"

@app.post("/speak")
async def speak(req: TTSRequest):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        engine.speak(req.text, output=f.name)
        return {"audio_file": f.name}

# Run with: uvicorn web_api:app --reload
```

---

## Troubleshooting

### Common Issues

#### Server Not Responding

**Symptom:** Connection refused or timeout

**Solutions:**
```bash
# Check if server is running
curl http://SERVER_IP:8000/health

# Check firewall
sudo ufw allow 8000

# Check server is bound to 0.0.0.0
netstat -tlnp | grep 8000

# Check logs
tail -f server.log
```

#### Voice Not Found

**Symptom:** `RuntimeError: Voice model not found`

**Solutions:**
```bash
# Check installed voices
ls ~/.local/share/piper/voices/

# Download missing voice
cd ~/.local/share/piper/voices
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

#### GPU Not Detected

**Symptom:** Server runs in CPU mode

**Solutions:**
```bash
# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Install CUDA-enabled PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Check NVIDIA driver
nvidia-smi
```

#### Audio Not Playing

**Symptom:** No sound output

**Solutions:**
```bash
# Check audio device
python -c "import sounddevice; print(sounddevice.query_devices())"

# Set default device (macOS)
# System Preferences > Sound > Output

# Test with different player
mytts speak "Test" -o test.wav
afplay test.wav  # macOS
aplay test.wav   # Linux
```

#### Memory Issues

**Symptom:** Server becomes slow or crashes

**Solutions:**
```bash
# Clear engine cache
curl -X POST http://SERVER_IP:8000/cleanup

# Restart server
./stop_server.sh && ./start_server.sh

# Monitor GPU memory
nvidia-smi -l 1
```

### Debug Mode

Enable verbose logging:

```bash
# Server with debug output
mytts serve --host 0.0.0.0 --port 8000 2>&1 | tee server.log

# Check logs
tail -f server.log
```

### Getting Help

1. Check this manual
2. Check the [README](../README.md)
3. Check [SERVER_MVP.md](./SERVER_MVP.md) for server details
4. Open an issue on GitHub

---

## API Reference

### CLI Commands

| Command | Description |
|---------|-------------|
| `mytts speak <text>` | Speak text directly |
| `mytts read <file>` | Read text file aloud |
| `mytts chat` | Interactive chat mode |
| `mytts serve` | Start TTS server |
| `mytts ollama` | Chat with Ollama + TTS |

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--server` | Use remote TTS server | False |
| `--server-url URL` | Server URL | `http://localhost:8000` |
| `--engine ENGINE` | TTS engine (piper/coqui) | piper |
| `--voice VOICE` | Voice model | en_US-lessac-medium |
| `--workers N` | Worker threads | 4 |
| `--buffer-size N` | Pre-generate buffer | 2 |
| `--host HOST` | Server host | 0.0.0.0 |
| `--port PORT` | Server port | 8000 |
| `--cpu` | Force CPU mode | False |

### Server Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tts` | POST | Generate speech |
| `/health` | GET | Server health status |
| `/voices` | GET | List available voices |
| `/cleanup` | POST | Clear engine cache |

### Python Classes

#### TTSEngine

```python
from mytts import TTSEngine, TTSBackend, TTSMode

engine = TTSEngine(
    mode=TTSMode.READING,           # or CONVERSATIONAL
    backend=TTSBackend.SERVER,      # or LOCAL
    engine="piper",                 # or "coqui"
    voice="en_US-lessac-medium",
    server_url="http://localhost:8000"
)

engine.speak(text="Hello!")
engine.speak(file_path="document.txt")
engine.speak(text="Hello", output="output.wav")
```

#### ProgressiveTTSClient

```python
from mytts.client import ProgressiveTTSClient

client = ProgressiveTTSClient(
    engine,
    num_workers=4,
    buffer_size=2
)

stats = client.speak("Long text with multiple sentences.")
client.close()
```

#### StreamingTTSClient

```python
from mytts.client import StreamingTTSClient

client = StreamingTTSClient(engine, num_workers=4, lookahead=2)
client.play()
client.feed("Sentence 1.")
client.feed("Sentence 2.")
client.stop()
client.close()
```

---

## Next Steps

1. **Try the examples** - Pick an integration example and run it
2. **Experiment with voices** - Find the voice that fits your use case
3. **Build something** - Create your own TTS-powered application
4. **Contribute** - Share your improvements with the community

Happy building!
