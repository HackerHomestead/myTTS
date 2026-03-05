from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

import numpy as np
import sounddevice as sd
from TTS.api import TTS


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


class CoquiEngine(BaseEngine):
    def __init__(self, voice: Optional[str] = None, mode=None):
        self.tts = TTS("tts_models/multilingual/multilingual-vits", gpu=True)
        self.voice = voice or "en_US-lessac-medium"
        self.mode = mode

    def speak(
        self,
        text: str,
        output: Optional[Union[str, Path]] = None,
        streaming: bool = False,
    ):
        audio = self.tts.tts(text, voice=self.voice)
        
        if output:
            import scipy.io.wavfile as wav
            wav.write(output, 24000, audio)
            return None
        
        sd.play(audio, samplerate=24000)
        sd.wait()
        return audio

    def stream(self, text: str):
        return self.speak(text)
