import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.database import engine
from app.models import review  # noqa: F401
from app.models.base import Base


def _find_frontend_dist() -> Path | None:
    """Locate the frontend dist directory in various packaging scenarios."""
    candidates = []

    if getattr(sys, "frozen", False):
        # PyInstaller single-file: data extracted to _MEIPASS
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "frontend" / "dist")
        # PyInstaller onedir: data in _internal/
        base = Path(sys.executable).parent
        candidates.append(base / "_internal" / "frontend" / "dist")
        candidates.append(base / "frontend" / "dist")

    # Dev mode
    base = Path.cwd()
    candidates.append(base / "frontend" / "dist")
    candidates.append(base / "dist")
    here = Path(__file__).resolve().parent
    candidates.append(here.parent.parent / "frontend" / "dist")

    for p in candidates:
        if p.is_dir() and (p / "index.html").exists():
            return p
    return None


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    app = FastAPI(title="Contract Review Workbench")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    dist_dir = _find_frontend_dist()
    if dist_dir is not None:
        app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="static-assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            file_path = dist_dir / full_path
            if file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(dist_dir / "index.html"))

    return app


app = create_app()
