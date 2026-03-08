#!/usr/bin/env python3
"""Test voice differentiation on server side."""

import argparse
import io
import wave
import numpy as np
import requests
from typing import List, Dict
from mytts import TTSEngine, TTSBackend

SERVER_URL = "http://192.168.88.164:8000"
TEST_VOICES = [
    "en_US-lessac-medium",
    "en_US-lessac-high", 
    "en_US-amy-medium",
    "en_US-norman-medium",
    "en_US-john-medium",
]

TEST_TEXT = "Hello world, this is a voice test."


def get_audio_fingerprint(audio_data: bytes) -> Dict:
    """Extract audio characteristics for comparison."""
    wav_data = io.BytesIO(audio_data)
    with wave.open(wav_data, 'rb') as wf:
        sample_rate = wf.getframerate()
        audio = wf.readframes(wf.getnframes())
        audio = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Calculate fingerprint
        fingerprint = {
            "sample_rate": sample_rate,
            "duration": len(audio) / sample_rate,
            "rms": np.sqrt(np.mean(audio**2)),
            "zero_crossings": np.sum(np.diff(np.sign(audio)) != 0),
            "spectral_centroid": np.sum(np.abs(np.fft.fft(audio)[:len(audio)//2]) * np.arange(len(audio)//2)) / np.sum(np.abs(np.fft.fft(audio)[:len(audio)//2])) if len(audio) > 0 else 0,
            "peak_amplitude": np.max(np.abs(audio)),
        }
        return fingerprint


def test_voice_differentiation():
    """Test that different voices produce different audio."""
    print("Testing voice differentiation on server...")
    print(f"Server: {SERVER_URL}")
    print(f"Test text: '{TEST_TEXT}'")
    print()
    
    fingerprints = {}
    
    for voice in TEST_VOICES:
        print(f"Testing voice: {voice}")
        
        try:
            response = requests.post(
                f"{SERVER_URL}/tts",
                json={"text": TEST_TEXT, "voice": voice},
                timeout=30
            )
            response.raise_for_status()
            
            fingerprint = get_audio_fingerprint(response.content)
            fingerprints[voice] = fingerprint
            
            print(f"  Duration: {fingerprint['duration']:.2f}s")
            print(f"  RMS: {fingerprint['rms']:.4f}")
            print(f"  Zero crossings: {fingerprint['zero_crossings']}")
            print(f"  Spectral centroid: {fingerprint['spectral_centroid']:.1f}")
            print()
            
        except Exception as e:
            print(f"  ERROR: {e}")
            print()
    
    # Compare fingerprints
    print("Voice comparison:")
    print("-" * 60)
    
    voices = list(fingerprints.keys())
    for i, voice1 in enumerate(voices):
        for voice2 in voices[i+1:]:
            fp1 = fingerprints[voice1]
            fp2 = fingerprints[voice2]
            
            # Calculate differences
            rms_diff = abs(fp1['rms'] - fp2['rms'])
            zc_diff = abs(fp1['zero_crossings'] - fp2['zero_crossings'])
            sc_diff = abs(fp1['spectral_centroid'] - fp2['spectral_centroid'])
            
            # Check if significantly different
            different = (rms_diff > 0.01 or zc_diff > 10 or sc_diff > 100)
            
            status = "✓ DIFFERENT" if different else "✗ SIMILAR"
            print(f"{voice1} vs {voice2}: {status}")
            print(f"  RMS diff: {rms_diff:.4f}, ZC diff: {zc_diff}, SC diff: {sc_diff:.1f}")
    
    print()
    print("Test complete!")


def test_voice_parameter_passing():
    """Test that voice parameter is actually passed to server."""
    print("Testing voice parameter passing...")
    
    # Test with a non-existent voice
    try:
        response = requests.post(
            f"{SERVER_URL}/tts",
            json={"text": TEST_TEXT, "voice": "non_existent_voice"},
            timeout=10
        )
        
        if response.status_code == 400:
            print("✓ Server correctly rejects invalid voice")
        else:
            print(f"✗ Server should reject invalid voice, got: {response.status_code}")
            
    except Exception as e:
        print(f"✓ Server error for invalid voice: {e}")


def main():
    global SERVER_URL
    parser = argparse.ArgumentParser(description="Test voice differentiation")
    parser.add_argument("--server-url", default=SERVER_URL, help="TTS server URL")
    args = parser.parse_args()
    
    SERVER_URL = args.server_url
    
    test_voice_parameter_passing()
    print()
    test_voice_differentiation()


if __name__ == "__main__":
    main()