import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_base_dir() -> Path:
    """Return the base directory for data storage.

    When running as a PyInstaller bundle the data lives next to the
    executable; otherwise it is relative to the working directory.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path.cwd()


_base = _get_base_dir()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_base / ".env"),
        env_file_encoding="utf-8",
    )

    database_url: str = f"sqlite:///{(_base / 'data' / 'app.db').as_posix()}"
    storage_root: Path = _base / "data" / "storage"


settings = Settings()

# Ensure data directories exist
(settings.storage_root).mkdir(parents=True, exist_ok=True)
(_base / "data").mkdir(parents=True, exist_ok=True)
