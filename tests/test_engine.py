import pytest


def test_base_engine_import():
    """Test that BaseEngine can be imported from mytts.engine"""
    from mytts.engine import BaseEngine
    assert BaseEngine is not None


def test_coqui_engine_import():
    """Test that CoquiEngine can be imported"""
    from mytts.engine.coqui import CoquiEngine, BaseEngine
    assert CoquiEngine is not None
    assert BaseEngine is not None
    assert issubclass(CoquiEngine, BaseEngine)


def test_piper_engine_import():
    """Test that PiperEngine can be imported"""
    from mytts.engine.piper import PiperEngine
    assert PiperEngine is not None


def test_remote_engine_import():
    """Test that RemoteEngine can be imported"""
    from mytts.engine.remote import RemoteEngine
    assert RemoteEngine is not None
