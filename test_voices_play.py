#!/usr/bin/env python3
"""Test voice differentiation by playing audio for each voice."""

import argparse
import io
import wave
import time
import numpy as np
import sounddevice as sd
import requests

SERVER_URL = "http://192.168.88.164:8000"
TEST_VOICES = [
    "en_US-lessac-medium",
    "en_US-lessac-high", 
    "en_US-amy-medium",
    "en_US-norman-medium",
    "en_US-john-medium",
]

TEST_TEXT = "Hello, this is a voice test. Each voice should sound different."


def play_voice(voice: str, text: str, server_url: str):
    """Generate and play audio for a specific voice."""
    print(f"Playing voice: {voice}")
    
    try:
        response = requests.post(
            f"{server_url}/tts",
            json={"text": text, "voice": voice, "engine": "piper"},
            timeout=30
        )
        response.raise_for_status()
        
        # Parse WAV data
        wav_data = io.BytesIO(response.content)
        with wave.open(wav_data, 'rb') as wf:
            sample_rate = wf.getframerate()
            audio = wf.readframes(wf.getnframes())
            audio = np.frombuffer(audio, dtype=np.int16)
            audio = audio.astype(np.float32) / 32768.0
        
        # Play audio
        print(f"  Duration: {len(audio)/sample_rate:.2f}s")
        print("  Playing...")
        sd.play(audio, samplerate=sample_rate)
        sd.wait()
        print("  Done.")
        
    except Exception as e:
        print(f"  ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(description="Test voices by playing audio")
    parser.add_argument("--server-url", default=SERVER_URL, help="TTS server URL")
    parser.add_argument("--text", default=TEST_TEXT, help="Text to speak")
    parser.add_argument("--voices", nargs="+", default=TEST_VOICES, help="Voices to test")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between voices (seconds)")
    args = parser.parse_args()
    
    print(f"Server: {args.server_url}")
    print(f"Text: {args.text}")
    print(f"Testing {len(args.voices)} voices...")
    print()
    
    for i, voice in enumerate(args.voices, 1):
        print(f"[{i}/{len(args.voices)}] ", end="")
        play_voice(voice, args.text, args.server_url)
        
        if i < len(args.voices):
            print(f"  Waiting {args.delay}s before next voice...")
            time.sleep(args.delay)
        
        print()
    
    print("All voices tested!")


if __name__ == "__main__":
    main()