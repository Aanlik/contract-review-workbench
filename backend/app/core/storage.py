from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings


@dataclass(frozen=True)
class StoredFile:
    original_name: str
    content_type: str | None
    path: Path
    size_bytes: int


def sanitize_file_name(file_name: str) -> str:
    keep = []
    for char in Path(file_name).name:
        if char.isalnum() or char in {".", "-", "_"}:
            keep.append(char)
        else:
            keep.append("_")
    sanitized = "".join(keep).strip("._")
    return sanitized or "upload"


class StorageService:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or settings.storage_root

    def save_upload(self, case_id: int, upload: UploadFile) -> StoredFile:
        target_dir = self.root / "cases" / str(case_id) / "uploads"
        target_dir.mkdir(parents=True, exist_ok=True)
        original_name = upload.filename or "upload"
        target_path = target_dir / f"{uuid4().hex}-{sanitize_file_name(original_name)}"
        contents = upload.file.read()
        target_path.write_bytes(contents)
        return StoredFile(
            original_name=original_name,
            content_type=upload.content_type,
            path=target_path,
            size_bytes=len(contents),
        )
