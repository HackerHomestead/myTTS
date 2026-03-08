import os
import sys
import queue
import threading
import time
import io
import wave
import re
import numpy as np
import sounddevice as sd
import requests
from typing import Optional, List

DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_TTS_URL = os.environ.get("TTS_SERVER_URL", "http://localhost:8000")

SENTENCE_ENDINGS = re.compile(r'[.!?]+[\s]+')


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


def split_into_sentences(text: str) -> List[str]:
    sentences = SENTENCE_ENDINGS.split(text.strip())
    result = []
    for s in sentences:
        s = " ".join(s.split())
        if s:
            if s[-1] not in '.!?':
                s = s + "."
            result.append(s)
    return result


def apply_fade(audio: np.ndarray, sample_rate: int, fade_ms: int = 10) -> np.ndarray:
    fade_samples = int(sample_rate * fade_ms / 1000)
    if len(audio) < fade_samples * 2:
        return audio
    
    faded = audio.copy()
    fade_in = np.linspace(0.0, 1.0, fade_samples)
    fade_out = np.linspace(1.0, 0.0, fade_samples)
    faded[:fade_samples] *= fade_in
    faded[-fade_samples:] *= fade_out
    return faded


def format_time(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


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
        sentences = split_into_sentences(text)
        if not sentences:
            return 0
        
        total_duration = 0
        
        for i, sentence in enumerate(sentences):
            response = requests.post(
                f"{self.tts_url}/tts",
                json={"text": sentence, "voice": self.voice},
            )
            response.raise_for_status()
            
            wav_data = io.BytesIO(response.content)
            with wave.open(wav_data, 'rb') as wf:
                frame_rate = wf.getframerate()
                num_frames = wf.getnframes()
                actual_duration = num_frames / frame_rate
                
                self.duration_estimator.update(sentence, actual_duration)
                
                print(f"\r{format_time(int(actual_duration))} (chunk {i+1}/{len(sentences)})", end="", flush=True)
                
                audio = wf.readframes(num_frames)
                audio = np.frombuffer(audio, dtype=np.int16)
                audio = audio.astype(np.float32) / 32768.0
                
                faded_audio = apply_fade(audio, frame_rate)
                
                sd.play(faded_audio, samplerate=frame_rate)
                sd.wait()
                
                total_duration += actual_duration
        
        print()
        return total_duration

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
