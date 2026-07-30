"""Entry point for the packaged Contract Review Workbench.

When frozen by PyInstaller the working directory is set to the executable's
folder so that data/, exports/ etc. live next to the binary.
"""

import sys
import os
import webbrowser
import threading
import time

if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

from app.main import app  # noqa: E402


def _open_browser():
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:8000")


if __name__ == "__main__":
    import uvicorn

    if "--no-browser" not in sys.argv:
        threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
