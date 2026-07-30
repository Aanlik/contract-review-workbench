from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.services.export_service import ExportService

router = APIRouter()


class ExportRequest(BaseModel):
    format: Literal["markdown", "docx", "pdf"]
    scope: Literal["final", "all", "high", "high_and_medium", "confirmed"] = "final"
    include_ai_summary: bool = False


class ExportResponse(BaseModel):
    file_path: str


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
    return ExportResponse(file_path=str(path))
