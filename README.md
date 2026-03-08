# myTTS 🚀

Self-hosted text-to-speech with client/server architecture for GPU offloading.

## 🎯 MVP Status: v1.0.0 - Production Ready

**Current Version**: `v1.0.0-mvp` - Feature-complete, production-ready TTS server with GPU acceleration.

### ✨ MVP Features
- **🚀 GPU-Accelerated**: NVIDIA GPU support (GTX 980/1050 Ti+)
- **🎵 High-Quality Audio**: VITS model with drift elimination
- **⚡ Real-Time Performance**: 10-20x faster than real-time (RTF 0.05-0.26)
- **🛡️ Production Ready**: Stable memory management, error handling, monitoring
- **🔧 Advanced Processing**: Text splitting, audio normalization, fade effects
- **📊 Health Monitoring**: Resource tracking, cleanup endpoints, detailed logging

## 🚀 Quick Start (MVP)

### Step 1: Server (Linux with NVIDIA GPU)

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install myTTS
pip install -e .

# 3. Install GPU-compatible dependencies (MVP optimized)
pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.2+cu118 --extra-index-url https://download.pytorch.org/whl/cu118
pip install TTS==0.13.2

# 4. Start the TTS server (GPU auto-detected)
mytts serve --host 0.0.0.0 --port 8000

# 5. Verify it's working
curl http://localhost:8000/health
```

### Step 2: Client (Your Mac)

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install
pip install -e .

# 3. Read a file (replace IP with your server's IP)
mytts read paper.txt --server --server-url http://192.168.1.100:8000

# 4. Chat with Ollama + TTS
mytts ollama --tts-url http://192.168.1.100:8000 --ollama-url http://192.168.1.100:11434
```

---

## 🚀 Server Setup (GPU Machine) - MVP

### System Requirements
- **GPU**: NVIDIA GTX 980 or newer (4GB+ VRAM recommended)
- **OS**: Linux (Ubuntu 20.04+)
- **RAM**: 8GB+ (16GB recommended)
- **Python**: 3.10+

### Installation (MVP Optimized)

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install myTTS
pip install -e .

# 3. Install GPU-compatible dependencies (MVP version)
pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.2+cu118 --extra-index-url https://download.pytorch.org/whl/cu118
pip install TTS==0.13.2

# 4. Verify GPU support
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### Run Server (Production Ready)

```bash
# Start server with GPU auto-detection
mytts serve --host 0.0.0.0 --port 8000

# Background deployment with logging
python -m mytts.cli serve --host 0.0.0.0 --port 8000 > server.log 2>&1 &

# Force CPU mode (if needed)
mytts serve --host 0.0.0.0 --port 8000 --cpu
```

### Server Features (MVP)

✅ **GPU Acceleration**: NVIDIA GPU support with automatic fallback  
✅ **Drift Elimination**: Intelligent text splitting and audio processing  
✅ **Real-Time Performance**: 10-20x faster than real-time (RTF 0.05-0.26)  
✅ **Health Monitoring**: `/health` endpoint with resource tracking  
✅ **Resource Management**: `/cleanup` endpoint for memory management  
✅ **Production Ready**: Stable under extended load testing  

### API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Generate speech
curl -X POST -H "Content-Type: application/json" \
  -d '{"text":"Hello world!","voice":"en_US-lessac-medium"}' \
  http://localhost:8000/tts --output speech.wav

# Clean up resources
curl -X POST http://localhost:8000/cleanup
```

### Performance Monitoring

```bash
# Check server status
curl http://localhost:8000/health | jq '.'

# Monitor GPU usage
nvidia-smi

# View logs
tail -f server.log
```

📖 **Detailed Documentation**: See [docs/SERVER_MVP.md](docs/SERVER_MVP.md) for comprehensive technical documentation.

---

## Client Setup (Your Mac)

### Install

```bash
python3 -m venv venv
source venv/bin/activate

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
