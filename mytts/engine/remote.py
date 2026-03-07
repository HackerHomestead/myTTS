from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

import numpy as np
import requests
import io
import wave


class BaseEngine(ABC):
    @abstractmethod
    def speak(
        self,
        text: str,
        output: Optional[Union[str, Path]] = None,
        streaming: bool = False,
    ):
        pass

    @abstractmethod
    def stream(self, text: str):
        pass


class RemoteEngine(BaseEngine):
    def __init__(self, server_url: str, voice: str, mode=None):
        self.server_url = server_url.rstrip("/")
        self.voice = voice
        self.mode = mode

    def speak(
        self,
        text: str,
        output: Optional[Union[str, Path]] = None,
        streaming: bool = False,
    ):
        response = requests.post(
            f"{self.server_url}/tts",
            json={"text": text, "voice": self.voice},
            stream=bool(output),
        )
        response.raise_for_status()

        if output:
            with open(output, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        else:
            import sounddevice as sd
            wav_data = io.BytesIO(response.content)
            with wave.open(wav_data, 'rb') as wf:
                audio = wf.readframes(wf.getnframes())
                audio = np.frombuffer(audio, dtype=np.int16)
                audio = audio.astype(np.float32) / 32768.0
                sd.play(audio, samplerate=wf.getframerate())
                sd.wait()

    def stream(self, text: str):
        self.speak(text, streaming=True)
