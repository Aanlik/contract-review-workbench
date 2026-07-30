from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.storage import StorageService
from app.models.review import ReviewCase
from app.schemas.review import ReviewCaseCreate, ReviewCaseRead, ReviewCaseUpdate

router = APIRouter()


def get_active_case(case_id: int, session: Session) -> ReviewCase:
    review_case = session.get(ReviewCase, case_id)
    if review_case is None or review_case.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Review case not found")
    return review_case


@router.post("", response_model=ReviewCaseRead)
def create_case(payload: ReviewCaseCreate, session: Session = Depends(get_session)):
    review_case = ReviewCase(title=payload.title, note=payload.note)
    session.add(review_case)
    session.commit()
    session.refresh(review_case)
    return review_case


@router.get("", response_model=list[ReviewCaseRead])
def list_cases(session: Session = Depends(get_session)):
    return session.scalars(
        select(ReviewCase)
        .where(ReviewCase.deleted_at.is_(None))
        .order_by(ReviewCase.updated_at.desc())
    ).all()


@router.get("/{case_id}", response_model=ReviewCaseRead)
def get_case(case_id: int, session: Session = Depends(get_session)):
    return get_active_case(case_id, session)


@router.patch("/{case_id}", response_model=ReviewCaseRead)
def update_case(
    case_id: int,
    payload: ReviewCaseUpdate,
    session: Session = Depends(get_session),
):
    review_case = get_active_case(case_id, session)
    if payload.title is not None:
        review_case.title = payload.title
    if payload.note is not None:
        review_case.note = payload.note
    session.commit()
    session.refresh(review_case)
    return review_case


@router.delete("/{case_id}", status_code=204)
def delete_case(
    case_id: int,
    delete_files: bool = False,
    session: Session = Depends(get_session),
):
    review_case = get_active_case(case_id, session)
    review_case.deleted_at = datetime.now(UTC)
    if delete_files:
        StorageService().delete_case_files(case_id)
    session.commit()
    return Response(status_code=204)
