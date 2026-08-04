# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Contract Review Workbench.

Build on Windows:
  pyinstaller backend/contract_review.spec

The resulting dist/contract-review/ folder is a portable distribution.
"""

from pathlib import Path
from importlib.util import find_spec
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs, copy_metadata

block_cipher = None
spec_dir = Path(SPECPATH)
project_root = spec_dir.parent

ocr_datas = []
ocr_binaries = []
ocr_hiddenimports = []
bundled_model_cache = os.environ.get("CONTRACT_REVIEW_OCR_MODELS")
if bundled_model_cache and Path(bundled_model_cache).is_dir():
    ocr_datas.append((bundled_model_cache, "ocr-models"))

for package in [
    'rapidocr',
    'rapidocr_onnxruntime',
    'onnxruntime',
    'paddle',
    'paddleocr',
    'paddlex',
    # PaddleX resolves these OCR-core packages dynamically at runtime.
    'imagesize',
    'cv2',
    'pyclipper',
    'pypdfium2',
    'bidi',
    'shapely',
]:
    if find_spec(package) is None:
        continue
    if sys.platform == 'darwin' and package == 'onnxruntime':
        # The full ONNX Runtime package exposes hundreds of optional tooling modules.
        # macOS only needs the inference extension and its dynamic libraries.
        package_datas = collect_data_files(package, include_py_files=False)
        package_binaries = collect_dynamic_libs(package)
        package_hiddenimports = [
            'onnxruntime',
            'onnxruntime.capi._pybind_state',
            'onnxruntime.capi.onnxruntime_pybind11_state',
        ]
    elif sys.platform == 'darwin' and package == 'rapidocr':
        # RapidOCR selects the ONNX Runtime engine dynamically. Keep its models and
        # the actual OCR path while excluding optional Paddle/TensorRT/PyTorch code.
        package_datas = collect_data_files(package, include_py_files=False)
        package_binaries = collect_dynamic_libs(package)
        package_hiddenimports = [
            'rapidocr',
            'rapidocr.main',
            'rapidocr.cal_rec_boxes.main',
            'rapidocr.ch_ppocr_cls.main',
            'rapidocr.ch_ppocr_det.main',
            'rapidocr.ch_ppocr_rec.main',
            'rapidocr.inference_engine.base',
            'rapidocr.inference_engine.onnxruntime',
            'rapidocr.inference_engine.onnxruntime.main',
            'rapidocr.inference_engine.onnxruntime.provider_config',
        ]
    else:
        package_datas, package_binaries, package_hiddenimports = collect_all(package)
    ocr_datas += package_datas
    ocr_binaries += package_binaries
    ocr_hiddenimports += package_hiddenimports

# PaddleX checks extras with importlib.metadata. Preserve the package metadata
# alongside its dynamically loaded OCR-core dependencies in the frozen app.
for distribution in [
    'paddlex',
    'imagesize',
    'opencv-contrib-python',
    'pyclipper',
    'pypdfium2',
    'python-bidi',
    'shapely',
]:
    ocr_datas += copy_metadata(distribution)

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
