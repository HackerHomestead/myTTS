#!/bin/bash
# Download Piper voice models

VOICE_DIR="${VOICE_DIR:-$HOME/.local/share/piper/voices}"
mkdir -p "$VOICE_DIR"
cd "$VOICE_DIR"

BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US"

# Available voices and their quality levels
declare -A VOICES
VOICES["lessac"]="medium high low"
VOICES["amy"]="medium low"
VOICES["norman"]="medium"
VOICES["john"]="medium"
VOICES["danny"]="low"
VOICES["kathleen"]="low"
VOICES["ryan"]="medium high low"

downloaded=0
skipped=0
failed=0

for voice in "${!VOICES[@]}"; do
    for quality in ${VOICES[$voice]}; do
        name="en_US-${voice}-${quality}"
        onnx_file="${name}.onnx"
        json_file="${name}.onnx.json"
        
        if [ -f "$onnx_file" ] && [ -s "$onnx_file" ]; then
            echo "✓ $name already exists"
            ((skipped++))
            continue
        fi
        
        echo "Downloading $name..."
        
        # Download ONNX model
        if wget -q "${BASE_URL}/${voice}/${quality}/${onnx_file}" -O "${onnx_file}" 2>/dev/null; then
            # Download config JSON
            if wget -q "${BASE_URL}/${voice}/${quality}/${json_file}" -O "${json_file}" 2>/dev/null; then
                if [ -s "$onnx_file" ]; then
                    echo "✓ Downloaded $name"
                    ((downloaded++))
                else
                    echo "✗ Empty file for $name"
                    rm -f "$onnx_file" "$json_file"
                    ((failed++))
                fi
            else
                echo "✗ Failed to download config for $name"
                rm -f "$onnx_file" "$json_file"
                ((failed++))
            fi
        else
            echo "✗ Failed to download $name"
            rm -f "$onnx_file" "$json_file"
            ((failed++))
        fi
    done
done

echo ""
echo "================================"
echo "Download Summary"
echo "================================"
echo "Downloaded: $downloaded"
echo "Skipped:    $skipped"
echo "Failed:     $failed"
echo ""
echo "Total voices installed: $(ls -1 *.onnx 2>/dev/null | wc -l)"
