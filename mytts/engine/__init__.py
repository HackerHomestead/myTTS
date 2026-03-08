# Lazy imports to avoid loading server-only dependencies on client
from mytts.engine.coqui import BaseEngine


def get_coqui():
    from mytts.engine.coqui import CoquiEngine
    return CoquiEngine, BaseEngine


def get_piper():
    from mytts.engine.piper import PiperEngine
    return PiperEngine, BaseEngine


def get_remote():
    from mytts.engine.remote import RemoteEngine
    return RemoteEngine, BaseEngine
