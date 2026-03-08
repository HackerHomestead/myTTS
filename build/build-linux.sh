#!/bin/bash
# Build myTTS binaries for Linux x86_64

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/dist"
VERSION=$(grep -m1 version "$PROJECT_DIR/pyproject.toml" 2>/dev/null | cut -d'"' -f2 || echo "1.0.0")
BUILD_TYPE="${1:-client}"  # client or server

echo "========================================"
echo "myTTS Build Script for Linux x86_64"
echo "========================================"
echo "Version:    $VERSION"
echo "Build Type: $BUILD_TYPE"
echo "Project:    $PROJECT_DIR"
echo "Build:      $BUILD_DIR"
echo ""

# Check architecture
ARCH=$(uname -m)
if [ "$ARCH" != "x86_64" ]; then
    echo "WARNING: Running on $ARCH, targeting x86_64"
fi

# Setup virtual environment
setup_venv() {
    echo ">>> Setting up build environment..."
    
    if [ -d "$PROJECT_DIR/build-venv" ]; then
        source "$PROJECT_DIR/build-venv/bin/activate"
    else
        python3 -m venv "$PROJECT_DIR/build-venv"
        source "$PROJECT_DIR/build-venv/bin/activate"
        pip install --upgrade pip wheel setuptools
    fi
}

# Install client dependencies
install_client_deps() {
    echo ">>> Installing client dependencies..."
    
    pip install -e "$PROJECT_DIR"
    pip install piper-onnx onnxruntime sounddevice requests
    pip install pyinstaller
}

# Install server dependencies
install_server_deps() {
    echo ">>> Installing server dependencies..."
    
    pip install -e "$PROJECT_DIR"
    
    # PyTorch with CUDA support
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    
    # TTS engines
    pip install TTS==0.13.2
    pip install piper-onnx onnxruntime-gpu
    
    # Server dependencies
    pip install fastapi uvicorn sounddevice scipy psutil requests
    pip install pyinstaller
}

# Build client binary
build_client() {
    echo ""
    echo ">>> Building mytts-client..."
    echo ""
    
    cd "$SCRIPT_DIR"
    
    pyinstaller \
        --clean \
        --noconfirm \
        --distpath "$BUILD_DIR/linux-x86_64" \
        --workpath "$PROJECT_DIR/build/client-build" \
        client.spec
    
    # Create archive
    cd "$BUILD_DIR/linux-x86_64"
    tar -czf "mytts-client-$VERSION-linux-x86_64.tar.gz" mytts-client/
    
    echo ""
    echo "✓ Client built: $BUILD_DIR/linux-x86_64/mytts-client/"
    echo "✓ Archive:      $BUILD_DIR/linux-x86_64/mytts-client-$VERSION-linux-x86_64.tar.gz"
}

# Build server binary
build_server() {
    echo ""
    echo ">>> Building mytts-server..."
    echo ""
    
    cd "$SCRIPT_DIR"
    
    pyinstaller \
        --clean \
        --noconfirm \
        --distpath "$BUILD_DIR/linux-x86_64" \
        --workpath "$PROJECT_DIR/build/server-build" \
        server.spec
    
    # Create archive
    cd "$BUILD_DIR/linux-x86_64"
    tar -czf "mytts-server-$VERSION-linux-x86_64.tar.gz" mytts-server/
    
    echo ""
    echo "✓ Server built: $BUILD_DIR/linux-x86_64/mytts-server/"
    echo "✓ Archive:       $BUILD_DIR/linux-x86_64/mytts-server-$VERSION-linux-x86_64.tar.gz"
}

# Test the binary
test_binary() {
    echo ""
    echo ">>> Testing binary..."
    
    if [ "$BUILD_TYPE" = "server" ]; then
        BINARY="$BUILD_DIR/linux-x86_64/mytts-server/mytts-server"
    else
        BINARY="$BUILD_DIR/linux-x86_64/mytts-client/mytts"
    fi
    
    if [ -x "$BINARY" ]; then
        "$BINARY" --help
        echo ""
        echo "✓ Binary test passed"
    else
        echo "✗ Binary not found or not executable"
        exit 1
    fi
}

# Main
main() {
    mkdir -p "$BUILD_DIR"
    
    setup_venv
    
    if [ "$BUILD_TYPE" = "server" ]; then
        install_server_deps
        build_server
    else
        install_client_deps
        build_client
    fi
    
    test_binary
    
    echo ""
    echo "========================================"
    echo "Build Complete!"
    echo "========================================"
    echo ""
    echo "Output:"
    if [ "$BUILD_TYPE" = "server" ]; then
        echo "  $BUILD_DIR/linux-x86_64/mytts-server/"
        echo "  $BUILD_DIR/linux-x86_64/mytts-server-$VERSION-linux-x86_64.tar.gz"
    else
        echo "  $BUILD_DIR/linux-x86_64/mytts-client/"
        echo "  $BUILD_DIR/linux-x86_64/mytts-client-$VERSION-linux-x86_64.tar.gz"
    fi
    echo ""
    echo "To install:"
    if [ "$BUILD_TYPE" = "server" ]; then
        echo "  tar -xzf mytts-server-$VERSION-linux-x86_64.tar.gz"
        echo "  sudo mv mytts-server/mytts-server /usr/local/bin/"
    else
        echo "  tar -xzf mytts-client-$VERSION-linux-x86_64.tar.gz"
        echo "  sudo mv mytts-client/mytts /usr/local/bin/"
    fi
    echo ""
}

main "$@"
