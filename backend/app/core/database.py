import sys
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _resolve_db_url(url: str) -> str:
    """Resolve SQLite URL to an absolute path, handling cross-platform differences."""
    if not url.startswith("sqlite:///"):
        return url

    raw_path = url.removeprefix("sqlite:///")

    if raw_path == ":memory:":
        return url

    p = Path(raw_path)
    if not p.is_absolute():
        if getattr(sys, "frozen", False):
            base = Path(sys.executable).parent
        else:
            base = Path.cwd()
        p = (base / p).resolve()

    p.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{p.as_posix()}"


resolved_url = _resolve_db_url(settings.database_url)
engine = create_engine(resolved_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
