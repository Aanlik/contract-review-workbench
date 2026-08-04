"""Entry point for the packaged Contract Review Workbench.

When frozen by PyInstaller the working directory is set to the executable's
folder so that data/, exports/ etc. live next to the binary.
"""

import os
import sys
import threading
import time
import webbrowser

if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

from app.main import app  # noqa: E402


def _open_browser():
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:8000")


def _run_ocr_smoke_test(image_path: str, engine: str = "paddle") -> None:
    from pathlib import Path

    from app.services.document_parser import PaddleOcrProvider, RapidOcrProvider

    provider = PaddleOcrProvider() if engine == "paddle" else RapidOcrProvider()
    blocks = provider.recognize_page(Path(image_path))
    if not blocks:
        raise RuntimeError("OCR smoke test returned no text blocks")
    print(f"OCR smoke test OK: {len(blocks)} blocks")


if __name__ == "__main__":
    import uvicorn

    smoke_engine = "paddle" if "--smoke-ocr" in sys.argv else "rapid" if "--smoke-rapid-ocr" in sys.argv else None
    if smoke_engine:
        argument_index = sys.argv.index("--smoke-ocr" if smoke_engine == "paddle" else "--smoke-rapid-ocr")
        try:
            image_path = sys.argv[argument_index + 1]
        except IndexError as exc:
            raise SystemExit("--smoke-ocr requires an image path") from exc
        _run_ocr_smoke_test(image_path, smoke_engine)
        raise SystemExit(0)

    if "--no-browser" not in sys.argv:
        threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
