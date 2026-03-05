import os
import sys
import queue
import threading
import sounddevice as sd
import requests
from typing import Optional

DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_TTS_URL = os.environ.get("TTS_SERVER_URL", "http://localhost:8000")


class OllamaChat:
    def __init__(
        self,
        model: str = "llama3.2",
        ollama_url: str = DEFAULT_OLLAMA_URL,
        tts_url: str = DEFAULT_TTS_URL,
        voice: str = "en_US-lessac-medium",
    ):
        self.model = model
        self.ollama_url = ollama_url.rstrip("/")
        self.tts_url = tts_url.rstrip("/")
        self.voice = voice
        self.audio_queue = queue.Queue()
        self._stream_audio = True

    def chat(self, prompt: str, speak: bool = True):
        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": True,
            },
            stream=True,
        )
        response.raise_for_status()
        
        full_response = ""
        
        for line in response.iter_lines():
            if line:
                data = line.decode("utf-8")
                if '"response"' in data:
                    import json
                    try:
                        chunk = json.loads(data)
                        text = chunk.get("response", "")
                        full_response += text
                        print(text, end="", flush=True)
                    except:
                        pass
        
        print()
        
        if speak:
            self.speak(full_response)
        
        return full_response

    def speak(self, text: str):
        response = requests.post(
            f"{self.tts_url}/tts",
            json={"text": text, "voice": self.voice},
        )
        response.raise_for_status()
        
        import io
        import wave
        wav_data = io.BytesIO(response.content)
        with wave.open(wav_data, 'rb') as wf:
            audio = wf.readframes(wf.getnframes())
            audio = np.frombuffer(audio, dtype=np.int16)
            audio = audio.astype(np.float32) / 32768.0
            sd.play(audio, samplerate=wf.getframerate())
            sd.wait()

    def interactive(self):
        print(f"Chat with {self.model} (Ctrl+C to exit)")
        print(f"TTS: {self.tts_url}")
        print()
        
        while True:
            try:
                prompt = input("> ")
                if prompt.strip():
                    self.chat(prompt)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")


import numpy as np


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ollama + TTS Chat")
    parser.add_argument("--model", default="llama3.2", help="Ollama model")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--tts-url", default=DEFAULT_TTS_URL)
    parser.add_argument("--voice", default="en_US-lessac-medium")
    
    args = parser.parse_args()
    
    chat = OllamaChat(
        model=args.model,
        ollama_url=args.ollama_url,
        tts_url=args.tts_url,
        voice=args.voice,
    )
    chat.interactive()
