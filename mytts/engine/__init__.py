# Lazy imports to avoid loading server-only dependencies on client
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union


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


def get_coqui():
    from mytts.engine.coqui import CoquiEngine
    return CoquiEngine, BaseEngine


def get_piper():
    from mytts.engine.piper import PiperEngine
    return PiperEngine, BaseEngine


def get_remote():
    from mytts.engine.remote import RemoteEngine
    return RemoteEngine, BaseEngine
