import os
import sys
import queue
import threading
import time
import io
import wave
import numpy as np
import sounddevice as sd
import requests
from typing import Optional, List

DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_TTS_URL = os.environ.get("TTS_SERVER_URL", "http://localhost:8000")


class DynamicEstimator:
    def __init__(self, initial_words_per_second: float = 2.5):
        self.words_per_second = initial_words_per_second
        self.max_samples = 10

    def estimate_duration(self, text: str) -> int:
        word_count = len(text.split())
        seconds = word_count / self.words_per_second
        return max(1, int(seconds))

    def update(self, text: str, actual_seconds: float):
        word_count = len(text.split())
        actual_wps = word_count / max(actual_seconds, 0.01)
        
        alpha = 0.3
        self.words_per_second = (alpha * actual_wps) + ((1 - alpha) * self.words_per_second)


def format_time(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def countdown_timer(duration: int, stop_event: threading.Event):
    remaining = duration
    while remaining > 0 and not stop_event.is_set():
        print(f"\r{format_time(remaining)}", end="", flush=True)
        time.sleep(1)
        remaining -= 1
    if not stop_event.is_set():
        print(f"\r{format_time(0)}", end="", flush=True)


class OllamaChat:
    def __init__(
        self,
        model: str = "llama3.2",
        ollama_url: str = DEFAULT_OLLAMA_URL,
        tts_url: str = DEFAULT_TTS_URL,
        voice: str = "en_US-lessac-medium",
        initial_wps: float = 2.5,
    ):
        self.model = model
        self.ollama_url = ollama_url.rstrip("/")
        self.tts_url = tts_url.rstrip("/")
        self.voice = voice
        self.audio_queue = queue.Queue()
        self._stream_audio = True
        self.duration_estimator = DynamicEstimator(initial_wps)

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
        estimated_seconds = self.duration_estimator.estimate_duration(text)
        current_wps = self.duration_estimator.words_per_second
        
        stop_event = threading.Event()
        timer_thread = threading.Thread(
            target=countdown_timer,
            args=(estimated_seconds, stop_event)
        )
        timer_thread.start()
        
        response = requests.post(
            f"{self.tts_url}/tts",
            json={"text": text, "voice": self.voice},
        )
        response.raise_for_status()
        
        wav_data = io.BytesIO(response.content)
        with wave.open(wav_data, 'rb') as wf:
            frame_rate = wf.getframerate()
            num_frames = wf.getnframes()
            actual_duration = num_frames / frame_rate
            
            self.duration_estimator.update(text, actual_duration)
            
            stop_event.set()
            timer_thread.join()
            print(f"\r{format_time(int(actual_duration))} (actual)", end="", flush=True)
            
            audio = wf.readframes(num_frames)
            audio = np.frombuffer(audio, dtype=np.int16)
            audio = audio.astype(np.float32) / 32768.0
            
            remaining = int(actual_duration)
            stop_event2 = threading.Event()
            timer_thread2 = threading.Thread(
                target=countdown_timer,
                args=(remaining, stop_event2)
            )
            timer_thread2.start()
            
            sd.play(audio, samplerate=frame_rate)
            sd.wait()
            
            stop_event2.set()
            timer_thread2.join()
        
        print()
        return actual_duration

    def interactive(self):
        print(f"Chat with {self.model} (Ctrl+C to exit)")
        print(f"TTS: {self.tts_url}")
        print(f"Initial WPS estimate: {self.duration_estimator.words_per_second:.1f} words/sec (adaptive)")
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


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ollama + TTS Chat")
    parser.add_argument("--model", default="llama3.2", help="Ollama model")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--tts-url", default=DEFAULT_TTS_URL)
    parser.add_argument("--voice", default="en_US-lessac-medium")
    parser.add_argument("--initial-wps", type=float, default=2.5, help="Initial words per second estimate")
    
    args = parser.parse_args()
    
    chat = OllamaChat(
        model=args.model,
        ollama_url=args.ollama_url,
        tts_url=args.tts_url,
        voice=args.voice,
        initial_wps=args.initial_wps,
    )
    chat.interactive()
