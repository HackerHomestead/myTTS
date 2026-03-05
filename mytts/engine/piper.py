from abc import abstractmethod
from pathlib import Path
from typing import Optional, Union

import numpy as np
import sounddevice as sd
import subprocess
import json
import os


class PiperEngine(BaseEngine):
    def __init__(self, voice: Optional[str] = None, mode=None):
        self.voice = voice or "en_US-lessac-medium"
        self.mode = mode
        self._check_piper()

    def _check_piper(self):
        result = subprocess.run(
            ["which", "piper"],
            capture_output=True,
            text=True,
        )
        if not result.stdout.strip():
            raise RuntimeError(
                "Piper not found. Install from: https://github.com/rhasspy/piper"
            )

    def speak(
        self,
        text: str,
        output: Optional[Union[str, Path]] = None,
        streaming: bool = False,
    ):
        cmd = [
            "piper",
            "--model", self._get_model(),
            "--output-file", str(output) if output else "-",
        ]
        
        result = subprocess.run(
            cmd,
            input=text,
            capture_output=True,
            text=False,
        )

        if not output:
            import io
            import wave
            wav_data = io.BytesIO(result.stdout)
            with wave.open(wav_data, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16)
                audio = audio.astype(np.float32) / 32768.0
                sd.play(audio, samplerate=wf.getframerate())
                sd.wait()

    def stream(self, text: str):
        self.speak(text, streaming=True)

    def _get_model(self):
        return f"{self.voice}.onnx"
