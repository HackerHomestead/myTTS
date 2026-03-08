# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for myTTS server binary.
Builds a full server with GPU support (includes PyTorch, Coqui, etc.).
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all modules
hidden_imports = [
    'mytts',
    'mytts.cli',
    'mytts.server',
    'mytts.engine',
    'mytts.engine.coqui',
    'mytts.engine.piper',
    'mytts.engine.remote',
    'fastapi',
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'starlette',
    'starlette.responses',
    'starlette.routing',
    'starlette.middleware',
    'starlette.requests',
    'starlette.exceptions',
    'pydantic',
    'pydantic.fields',
    'pydantic.main',
    'pydantic.types',
    'pydantic.validators',
    'requests',
    'urllib3',
    'numpy',
    'numpy.core',
    'numpy.core._methods',
    'numpy.core._dtype_ctypes',
    'torch',
    'torch.cuda',
    'torch.nn',
    'torch.optim',
    'TTS',
    'TTS.api',
    'TTS.tts',
    'TTS.tts.models',
    'TTS.vocoder',
    'piper_onnx',
    'onnxruntime',
    'phonemizer',
    'espeakng_loader',
    'sounddevice',
    'scipy',
    'scipy.io',
    'scipy.io.wavfile',
    'psutil',
]

# Platform-specific
if sys.platform == 'linux':
    hidden_imports.extend([
        'torch._C',
        'torch._torch_docs',
        'torch._tensor_docs',
        'torch._C._VariableFunctions',
    ])

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
        'matplotlib',
        'PIL',
        'pandas',
        'jupyter',
        'IPython',
        'notebook',
        'pytest',
        'tkinter',
        'unittest',
        'email',
        'html',
        'xml',
        'xmlrpc',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='mytts-server',
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
    name='mytts-server',
)
