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
    def __init__(self, voice: Optional[str] = None, mode=None, model: str = None, gpu: bool = False):
        import torch
        self.voice = voice or "en_US-lessac-medium"
        self.mode = mode
        
        model = model or "tts_models/en/ljspeech/tacotron2-DDC"
        # Force CPU-only mode
        gpu = False
        
        # Disable NNPACK to avoid hardware compatibility issues
        try:
            torch.backends.nnpack.flags(enabled=False)
        except Exception:
            pass
        
        self.tts = TTS(model, gpu=gpu)

    def speak(
        self,
        text: str,
        output: Optional[Union[str, Path]] = None,
        streaming: bool = False,
    ):
        audio = self.tts.tts(text)
        
        if output:
            import scipy.io.wavfile as wav
            wav.write(output, 22050, audio)
            return None
        
        return audio

    def stream(self, text: str):
        return self.speak(text)
