#!/bin/bash
# Build myTTS client for Raspberry Pi (ARM64)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/dist"
VERSION=$(grep -m1 version "$PROJECT_DIR/pyproject.toml" 2>/dev/null | cut -d'"' -f2 || echo "1.0.0")

echo "========================================"
echo "myTTS Build Script for Raspberry Pi"
echo "========================================"
echo "Version: $VERSION"
echo "Project: $PROJECT_DIR"
echo "Build:   $BUILD_DIR"
echo ""

# Check architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

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

# Install dependencies
install_deps() {
    echo ">>> Installing dependencies..."
    
    # Install myTTS
    pip install -e "$PROJECT_DIR"
    
    # Install ONNX runtime for ARM
    # Note: Use onnxruntime (CPU) for Pi, not onnxruntime-gpu
    pip install piper-onnx onnxruntime sounddevice requests
    
    # Build tools
    pip install pyinstaller
}

# Build client binary
build_client() {
    echo ""
    echo ">>> Building mytts-client for Raspberry Pi..."
    echo ""
    
    cd "$SCRIPT_DIR"
    
    pyinstaller \
        --clean \
        --noconfirm \
        --distpath "$BUILD_DIR/raspberry-pi-$ARCH" \
        --workpath "$PROJECT_DIR/build/client-build-pi" \
        client.spec
    
    # Create archive
    cd "$BUILD_DIR/raspberry-pi-$ARCH"
    tar -czf "mytts-client-$VERSION-raspberry-pi-$ARCH.tar.gz" mytts-client/
    
    echo ""
    echo "✓ Client built: $BUILD_DIR/raspberry-pi-$ARCH/mytts-client/"
    echo "✓ Archive:      $BUILD_DIR/raspberry-pi-$ARCH/mytts-client-$VERSION-raspberry-pi-$ARCH.tar.gz"
}

# Test the binary
test_binary() {
    echo ""
    echo ">>> Testing binary..."
    
    CLIENT="$BUILD_DIR/raspberry-pi-$ARCH/mytts-client/mytts"
    
    if [ -x "$CLIENT" ]; then
        "$CLIENT" --help
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
    install_deps
    build_client
    test_binary
    
    echo ""
    echo "========================================"
    echo "Build Complete!"
    echo "========================================"
    echo ""
    echo "Output:"
    echo "  $BUILD_DIR/raspberry-pi-$ARCH/mytts-client/"
    echo "  $BUILD_DIR/raspberry-pi-$ARCH/mytts-client-$VERSION-raspberry-pi-$ARCH.tar.gz"
    echo ""
    echo "To install:"
    echo "  tar -xzf mytts-client-$VERSION-raspberry-pi-$ARCH.tar.gz"
    echo "  sudo mv mytts-client/mytts /usr/local/bin/"
    echo ""
    echo "Note: This is a CLIENT binary only."
    echo "For GPU-accelerated TTS, connect to a remote server."
    echo ""
}

main "$@"
