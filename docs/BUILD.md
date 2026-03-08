# Building myTTS Binaries

This guide explains how to compile myTTS into standalone executables.

## Overview

myTTS can be built as two separate binaries:

| Binary | Size | Purpose | Components |
|--------|------|---------|------------|
| **mytts-client** | ~200-300MB | End-user CLI | Piper, ONNX Runtime, sounddevice |
| **mytts-server** | ~2.5GB | GPU server | PyTorch, Coqui TTS, FastAPI, Piper |

## Supported Platforms

| Platform | Architecture | Binary |
|----------|-------------|--------|
| macOS | ARM64 (M1/M2/M3/M4) | Client only |
| Linux | x86_64 | Client + Server |
| Raspberry Pi | ARM64/ARMv7 | Client only |

---

## Prerequisites

### All Platforms

- Python 3.10+
- Git
- C compiler (gcc/clang)

### macOS

```bash
# Install Xcode command line tools
xcode-select --install

# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Linux

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv \
    build-essential portaudio19-dev

# Fedora/RHEL
sudo dnf install -y python3 python3-pip python3-venv \
    gcc-c++ portaudio-devel
```

### Raspberry Pi

```bash
# Raspberry Pi OS (64-bit recommended)
sudo apt update
sudo apt install -y python3 python3-pip python3-venv \
    build-essential portaudio19-dev

# Increase swap for build (optional but recommended)
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

---

## Building for macOS (M1/M2/M3/M4)

### Quick Build

```bash
# Clone repository
git clone https://github.com/yourname/myTTS.git
cd myTTS

# Build client
./build/build-macos.sh
```

### Manual Build

```bash
# Create build environment
python3 -m venv build-venv
source build-venv/bin/activate

# Install dependencies
pip install -e .
pip install piper-onnx onnxruntime-silicon sounddevice requests
pip install pyinstaller

# Build
cd build
pyinstaller --clean --noconfirm client.spec

# Output: dist/macos-arm64/mytts-client/
```

### Install the Binary

```bash
# Extract archive
cd dist/macos-arm64
tar -xzf mytts-client-*-macos-arm64.tar.gz

# Install to /usr/local/bin
sudo mv mytts-client/mytts /usr/local/bin/

# Or add to PATH
export PATH="$PWD/mytts-client:$PATH"
```

---

## Building for Linux x86_64

### Build Client

```bash
# Clone repository
git clone https://github.com/yourname/myTTS.git
cd myTTS

# Build client
./build/build-linux.sh client
```

### Build Server

```bash
# Build server (requires NVIDIA GPU for full functionality)
./build/build-linux.sh server
```

### Manual Build

```bash
# Create build environment
python3 -m venv build-venv
source build-venv/bin/activate

# Install dependencies
pip install -e .

# For client:
pip install piper-onnx onnxruntime sounddevice requests pyinstaller

# For server:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install TTS==0.13.2 piper-onnx onnxruntime-gpu
pip install fastapi uvicorn sounddevice scipy psutil requests pyinstaller

# Build
cd build
pyinstaller --clean --noconfirm client.spec  # or server.spec
```

### Install the Binary

```bash
# Client
cd dist/linux-x86_64
tar -xzf mytts-client-*-linux-x86_64.tar.gz
sudo mv mytts-client/mytts /usr/local/bin/

# Server
tar -xzf mytts-server-*-linux-x86_64.tar.gz
sudo mv mytts-server/mytts-server /usr/local/bin/
```

---

## Building for Raspberry Pi

### Supported Models

| Model | Architecture | Status |
|-------|-------------|--------|
| Raspberry Pi 4 | ARM64 | ✅ Supported |
| Raspberry Pi 5 | ARM64 | ✅ Supported |
| Raspberry Pi 3 | ARM64 | ✅ Supported |
| Raspberry Pi Zero 2 | ARM64 | ✅ Supported |
| Raspberry Pi 3/Zero | ARMv7 | ⚠️ May work, not tested |

### Quick Build

```bash
# On Raspberry Pi
git clone https://github.com/yourname/myTTS.git
cd myTTS

# Build (takes 30-60 minutes on Pi 4)
./build/build-raspberry-pi.sh
```

### Manual Build

```bash
# Create build environment
python3 -m venv build-venv
source build-venv/bin/activate

# Install dependencies
pip install --upgrade pip wheel setuptools
pip install -e .
pip install piper-onnx onnxruntime sounddevice requests
pip install pyinstaller

# Build
cd build
pyinstaller --clean --noconfirm client.spec

# Output: dist/raspberry-pi-*/mytts-client/
```

### Raspberry Pi Notes

**Performance:**
- ONNX inference is slower on Pi (CPU only)
- Use `--server` mode to offload to GPU server
- Consider using `low` quality voices for faster generation

**Memory:**
- Build process requires ~2GB RAM
- Increase swap if build fails
- Close other applications during build

**Audio:**
- Configure audio output: `raspi-config` > System Options > Audio
- Test audio: `speaker-test -t wav -c 2`

---

## Cross-Compilation

### Using Docker for Linux Builds

Build Linux binaries on macOS:

```bash
# Create Dockerfile
cat > Dockerfile.build << 'EOF'
FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY . .

RUN pip install --upgrade pip wheel setuptools
RUN pip install -e .
RUN pip install piper-onnx onnxruntime sounddevice requests pyinstaller

RUN cd build && pyinstaller --clean --noconfirm client.spec

CMD ["sh", "-c", "cd dist/linux-x86_64 && tar -czf /output/mytts-client.tar.gz mytts-client"]
EOF

# Build
docker build -f Dockerfile.build -t mytts-builder .
docker run -v $(pwd)/output:/output mytts-builder
```

### Using GitHub Actions

Create `.github/workflows/build.yml`:

```yaml
name: Build Binaries

on:
  push:
    tags:
      - 'v*'

jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Build
        run: |
          pip install -e .
          pip install piper-onnx onnxruntime-silicon sounddevice requests pyinstaller
          cd build && pyinstaller --clean --noconfirm client.spec
      - uses: actions/upload-artifact@v4
        with:
          name: mytts-client-macos
          path: dist/macos-arm64/mytts-client/

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install system deps
        run: sudo apt-get install -y portaudio19-dev
      - name: Build
        run: |
          pip install -e .
          pip install piper-onnx onnxruntime sounddevice requests pyinstaller
          cd build && pyinstaller --clean --noconfirm client.spec
      - uses: actions/upload-artifact@v4
        with:
          name: mytts-client-linux
          path: dist/linux-x86_64/mytts-client/
```

---

## Binary Structure

### Client Binary

```
mytts-client/
├── mytts              # Main executable
├── _internal/         # Python runtime and libraries
│   ├── python3xx.so
│   ├── piper_onnx/
│   ├── onnxruntime/
│   ├── sounddevice/
│   └── ...
└── ...
```

### Server Binary

```
mytts-server/
├── mytts-server       # Main executable
├── _internal/
│   ├── python3xx.so
│   ├── torch/
│   ├── TTS/
│   ├── piper_onnx/
│   ├── fastapi/
│   └── ...
└── ...
```

---

## Distribution

### Creating Release Archives

```bash
# macOS
cd dist/macos-arm64
tar -czf mytts-client-1.0.0-macos-arm64.tar.gz mytts-client/

# Linux
cd dist/linux-x86_64
tar -czf mytts-client-1.0.0-linux-x86_64.tar.gz mytts-client/
tar -czf mytts-server-1.0.0-linux-x86_64.tar.gz mytts-server/

# Raspberry Pi
cd dist/raspberry-pi-aarch64
tar -czf mytts-client-1.0.0-raspberry-pi-arm64.tar.gz mytts-client/
```

### Creating Installers

**macOS DMG:**

```bash
# Install create-dmg
brew install create-dmg

# Create DMG
create-dmg \
  --volname "myTTS Client" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --app-drop-link 400 200 \
  mytts-client-1.0.0.dmg \
  dist/macos-arm64/mytts-client/
```

**Linux DEB:**

```bash
# Create package structure
mkdir -p mytts-client_1.0.0_amd64/{DEBIAN,usr/local/bin,usr/share/doc/mytts}

# Copy binary
cp -r dist/linux-x86_64/mytts-client/* mytts-client_1.0.0_amd64/usr/local/bin/

# Create control file
cat > mytts-client_1.0.0_amd64/DEBIAN/control << EOF
Package: mytts-client
Version: 1.0.0
Architecture: amd64
Maintainer: Your Name <you@example.com>
Description: myTTS Client - Text-to-speech client
 Self-hosted text-to-speech client for connecting to myTTS servers.
EOF

# Build package
dpkg-deb --build mytts-client_1.0.0_amd64
```

---

## Troubleshooting

### Build Fails

**"No module named 'xxx'"**

Add hidden imports to the spec file:

```python
hidden_imports = [
    'missing_module',
    ...
]
```

**"PyInstaller: command not found"**

```bash
pip install pyinstaller
# or use full path
python -m PyInstaller client.spec
```

**"Permission denied"**

```bash
chmod +x build/*.sh
```

### Binary Fails to Run

**"Library not loaded"**

On macOS, the binary may need to be signed:

```bash
codesign --force --deep --sign - dist/macos-arm64/mytts-client/mytts
```

**"No such file or directory"**

Check that all dependencies are included:

```bash
# List included modules
pyinstaller --log-level DEBUG client.spec 2>&1 | grep "Analyzing"
```

### Performance Issues

**Slow startup**

This is normal - PyInstaller extracts files to a temp directory. For faster startup, use the directory-based distribution instead of single-file.

**Large binary size**

Exclude unnecessary modules in the spec file:

```python
excludes=[
    'matplotlib',
    'PIL',
    'pandas',
    ...
]
```

---

## Advanced Options

### Single-File Binary

Modify the spec file to create a single executable:

```python
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,     # Include binaries
    a.datas,        # Include data
    [],
    name='mytts',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
```

**Note:** Single-file binaries are larger and slower to start.

### UPX Compression

Enable UPX compression to reduce binary size:

```bash
# Install UPX
# macOS:
brew install upx

# Linux:
sudo apt install upx

# Build with compression
pyinstaller --upx-dir=/usr/bin client.spec
```

### Custom Icon (macOS)

```python
exe = EXE(
    ...
    icon='../assets/icon.icns',
    ...
)
```

---

## Next Steps

1. Build the binary for your platform
2. Test with `./mytts --help`
3. Distribute to users
4. Consider creating installers for easier deployment

For questions or issues, see [MANUAL.md](../docs/MANUAL.md) or open a GitHub issue.
