from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models.review import ReviewVersion
from app.schemas.review import ReviewCaseRead, ReviewVersionRead
from app.services.review_run_service import ReviewRunService

router = APIRouter()


class ReanalyzeRequest(BaseModel):
    instruction: str | None = None


@router.post(
    "/cases/{case_id}/reanalyze",
    response_model=ReviewCaseRead,
    status_code=status.HTTP_201_CREATED,
)
def reanalyze_case(
    case_id: int,
    payload: ReanalyzeRequest,
    session: Session = Depends(get_session),
):
    try:
        return ReviewRunService(session).reanalyze(case_id, payload.instruction)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/cases/{case_id}/versions", response_model=list[ReviewVersionRead])
def list_case_versions(case_id: int, session: Session = Depends(get_session)):
    return session.scalars(
        select(ReviewVersion)
        .where(ReviewVersion.case_id == case_id)
        .order_by(ReviewVersion.version_number.desc(), ReviewVersion.id.desc())
    ).all()
