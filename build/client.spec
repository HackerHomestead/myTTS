# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for myTTS client binary.
Builds a lightweight client for end users (no server components).
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all mytts modules
hidden_imports = [
    'mytts',
    'mytts.cli',
    'mytts.client',
    'mytts.engine',
    'mytts.engine.piper',
    'mytts.engine.remote',
    'mytts.ollama',
    'requests',
    'urllib3',
    'charset_normalizer',
    'idna',
    'certifi',
    'sounddevice',
    'numpy',
    'numpy.core',
    'numpy.core._methods',
    'numpy.core._dtype_ctypes',
    'piper_onnx',
    'onnxruntime',
    'phonemizer',
    'espeakng_loader',
]

# Platform-specific imports
if sys.platform == 'darwin':
    hidden_imports.extend(['_sounddevice_data', 'portaudio'])
elif sys.platform == 'linux':
    hidden_imports.extend(['_sounddevice_data', 'portaudio'])

a = Analysis(
    ['../mytts/cli.py'],
    pathex=['..'],
    binaries=[],
    datas=[
        ('../mytts', 'mytts'),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch',
        'torchvision',
        'torchaudio',
        'TTS',
        'coqui_tts',
        'fastapi',
        'uvicorn',
        'starlette',
        'pydantic',
        'matplotlib',
        'PIL',
        'scipy',
        'pandas',
        'jupyter',
        'IPython',
        'notebook',
        'pytest',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='mytts',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='mytts-client',
)
