from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.storage import StorageService
from app.models.review import ReviewCase
from app.schemas.review import ReviewCaseCreate, ReviewCaseRead, ReviewCaseUpdate
from app.services.audit_service import record_audit

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
    record_audit(session, action="create", entity_type="case", entity_id=review_case.id,
                 details={"title": review_case.title})
    return review_case


@router.get("", response_model=list[ReviewCaseRead])
def list_cases(
    q: str | None = Query(None, description="搜索关键词（匹配标题和备注）"),
    status: str | None = Query(None, description="按状态筛选"),
    risk_level: str | None = Query(None, description="按最高风险等级筛选"),
    sort_by: str = Query("updated_at", description="排序字段：updated_at/created_at/title/issue_count"),
    sort_order: str = Query("desc", description="排序方向：asc/desc"),
    session: Session = Depends(get_session),
):
    stmt = select(ReviewCase).where(ReviewCase.deleted_at.is_(None))

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(ReviewCase.title.ilike(pattern), ReviewCase.note.ilike(pattern))
        )
    if status:
        stmt = stmt.where(ReviewCase.status == status)
    if risk_level:
        stmt = stmt.where(ReviewCase.highest_risk_level == risk_level)

    sort_column = {
        "updated_at": ReviewCase.updated_at,
        "created_at": ReviewCase.created_at,
        "title": ReviewCase.title,
        "issue_count": ReviewCase.issue_count,
    }.get(sort_by, ReviewCase.updated_at)

    if sort_order == "asc":
        stmt = stmt.order_by(sort_column.asc())
    else:
        stmt = stmt.order_by(sort_column.desc())

    return session.scalars(stmt).all()


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
    changes = {}
    if payload.title is not None:
        changes["title"] = payload.title
        review_case.title = payload.title
    if payload.note is not None:
        changes["note"] = payload.note
        review_case.note = payload.note
    session.commit()
    session.refresh(review_case)
    record_audit(session, action="update", entity_type="case", entity_id=case_id, details=changes)
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
    record_audit(session, action="delete", entity_type="case", entity_id=case_id,
                 details={"delete_files": delete_files})
    return Response(status_code=204)
