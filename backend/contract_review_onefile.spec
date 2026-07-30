# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — single-file build for macOS."""

import sys
from pathlib import Path

block_cipher = None
spec_dir = Path(SPECPATH)
project_root = spec_dir.parent

a = Analysis(
    [str(spec_dir / 'run.py')],
    pathex=[str(spec_dir)],
    binaries=[],
    datas=[
        (str(project_root / 'frontend' / 'dist'), 'frontend/dist'),
        (str(spec_dir / 'alembic'), 'alembic'),
        (str(spec_dir / 'alembic.ini'), '.'),
    ],
    hiddenimports=[
        'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
        'uvicorn.protocols', 'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan',
        'uvicorn.lifespan.on', 'sqlalchemy.dialects.sqlite',
        'app.api.routes.ai', 'app.api.routes.audit', 'app.api.routes.cases',
        'app.api.routes.exports', 'app.api.routes.files',
        'app.api.routes.issues', 'app.api.routes.review_runs',
        'app.api.routes.settings', 'app.api.routes.tasks',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'PIL.test'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='contract-review',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=True,
    icon=None,
)
