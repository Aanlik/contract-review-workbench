from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.services.export_service import ExportService

router = APIRouter()


class ExportRequest(BaseModel):
    format: Literal["markdown"]
    scope: Literal["final", "all", "high", "confirmed"] = "final"
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
        path = ExportService(session).export_markdown(
            case_id=case_id,
            include_ai_summary=payload.include_ai_summary,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ExportResponse(file_path=str(path))
