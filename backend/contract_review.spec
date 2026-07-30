# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Contract Review Workbench.

Build on Windows:
  pyinstaller backend/contract_review.spec

The resulting dist/contract-review/ folder is a portable distribution.
"""

from pathlib import Path
from importlib.util import find_spec

from PyInstaller.utils.hooks import collect_all

block_cipher = None
spec_dir = Path(SPECPATH)
project_root = spec_dir.parent

ocr_datas = []
ocr_binaries = []
ocr_hiddenimports = []

for package in [
    'rapidocr',
    'rapidocr_onnxruntime',
    'onnxruntime',
    'paddle',
    'paddleocr',
]:
    if find_spec(package) is None:
        continue
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    ocr_datas += package_datas
    ocr_binaries += package_binaries
    ocr_hiddenimports += package_hiddenimports

a = Analysis(
    [str(spec_dir / 'run.py')],
    pathex=[str(spec_dir)],
    binaries=ocr_binaries,
    datas=[
        (str(project_root / 'frontend' / 'dist'), 'frontend/dist'),
        (str(spec_dir / 'alembic'), 'alembic'),
        (str(spec_dir / 'alembic.ini'), '.'),
    ] + ocr_datas,
    hiddenimports=[
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
        'sqlalchemy.dialects.sqlite',
        'app.api.routes.ai',
        'app.api.routes.audit',
        'app.api.routes.cases',
        'app.api.routes.exports',
        'app.api.routes.files',
        'app.api.routes.issues',
        'app.api.routes.review_runs',
        'app.api.routes.settings',
        'app.api.routes.tasks',
    ] + ocr_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'PIL.test'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='contract-review',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='contract-review',
)
