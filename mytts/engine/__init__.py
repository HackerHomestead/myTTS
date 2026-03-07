# Lazy imports to avoid loading server-only dependencies on client

def get_coqui():
    from mytts.engine.coqui import CoquiEngine, BaseEngine
    return CoquiEngine, BaseEngine

def get_piper():
    from mytts.engine.piper import PiperEngine
    return PiperEngine

def get_remote():
    from mytts.engine.remote import RemoteEngine
    return RemoteEngine
