import os
from enum import Enum
from pathlib import Path
from typing import Optional, Union


class TTSMode(Enum):
    READING = "reading"
    CONVERSATIONAL = "conversational"


class TTSBackend(Enum):
    LOCAL = "local"
    SERVER = "server"


class TTSEngine:
    def __init__(
        self,
        mode: TTSMode = TTSMode.READING,
        backend: TTSBackend = TTSBackend.LOCAL,
        engine: str = "coqui",
        voice: Optional[str] = None,
        server_url: Optional[str] = None,
    ):
        self.mode = mode
        self.backend = backend
        self.engine_name = engine
        self.server_url = server_url or os.environ.get("TTS_SERVER_URL", "http://localhost:8000")
        self.voice = voice or "en_US-lessac-medium"

        if backend == TTSBackend.LOCAL:
            if engine == "coqui":
                from mytts.engine.coqui import CoquiEngine
                self._engine = CoquiEngine(voice=self.voice, mode=mode)
            elif engine == "piper":
                from mytts.engine.piper import PiperEngine
                self._engine = PiperEngine(voice=self.voice, mode=mode)
            else:
                raise ValueError(f"Unknown engine: {engine}")
        else:
            from mytts.engine.remote import RemoteEngine
            self._engine = RemoteEngine(
                server_url=self.server_url,
                voice=self.voice,
                mode=mode,
            )

    def speak(
        self,
        text: Optional[str] = None,
        file_path: Optional[Union[str, Path]] = None,
        output: Optional[Union[str, Path]] = None,
        streaming: bool = False,
    ):
        if text is None and file_path is None:
            raise ValueError("Must provide either text or file_path")
        
        if file_path:
            text = Path(file_path).read_text()
        
        return self._engine.speak(text, output=output, streaming=streaming)

    def stream(self, text: str):
        return self._engine.stream(text)
