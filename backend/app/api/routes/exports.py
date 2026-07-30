from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_session
from app.services.export_service import ExportService

router = APIRouter()


def _resolve_safe_path(requested: str) -> Path:
    """Resolve a file path and ensure it stays within the storage root.

    Prevents path traversal attacks (e.g. ../../etc/passwd) by resolving
    to absolute path and verifying it is a child of the configured storage root.
    """
    storage_root = settings.storage_root.resolve()
    target = (storage_root / requested).resolve() if not Path(requested).is_absolute() else Path(requested).resolve()

    # Ensure the resolved path is under storage_root
    try:
        target.relative_to(storage_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path outside storage root") from None

    return target


class ExportRequest(BaseModel):
    format: Literal["markdown", "docx", "pdf"]
    scope: Literal["final", "all", "high", "high_and_medium", "confirmed"] = "final"
    include_ai_summary: bool = False


class ExportResponse(BaseModel):
    file_path: str
    file_name: str


@router.post(
    "/cases/{case_id}/exports",
    response_model=ExportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_export(
    case_id: int,
    payload: ExportRequest,
    session: Session = Depends(get_session),
):
    try:
        path = ExportService(session).export_report(
            case_id=case_id,
            export_format=payload.format,
            include_ai_summary=payload.include_ai_summary,
            scope=payload.scope,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    # Return relative path so client cannot see absolute server paths
    try:
        relative = path.resolve().relative_to(settings.storage_root.resolve())
    except ValueError:
        relative = path.name
    return ExportResponse(file_path=str(relative), file_name=path.name)


@router.get("/exports/download")
def download_export(file_path: str):
    """Download a previously exported file by its path.

    Only files under the configured storage root are accessible.
    Path traversal attempts are rejected with 403.
    """
    target = _resolve_safe_path(file_path)

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Export file not found")

    # Extra safety: only serve files from exports directory
    exports_root = (settings.storage_root / "exports").resolve()
    try:
        target.relative_to(exports_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: file is not an export") from None

    return FileResponse(
        path=str(target),
        filename=target.name,
        media_type="application/octet-stream",
    )
