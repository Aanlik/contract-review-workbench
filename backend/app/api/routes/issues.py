from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_session
from app.models.review import Issue
from app.schemas.review import (
    ApplyAiMessageRequest,
    IssueRead,
    IssueUpdate,
    ManualIssueCreate,
)
from app.services.issue_service import IssueService

router = APIRouter()


@router.get("/cases/{case_id}/issues", response_model=list[IssueRead])
def list_case_issues(case_id: int, session: Session = Depends(get_session)):
    return session.scalars(
        select(Issue)
        .where(Issue.case_id == case_id)
        .options(selectinload(Issue.evidence_refs))
        .order_by(Issue.id.asc())
    ).all()


@router.post("/cases/{case_id}/issues/manual", response_model=IssueRead, status_code=201)
def create_manual_issue(
    case_id: int,
    payload: ManualIssueCreate,
    session: Session = Depends(get_session),
):
    try:
        return IssueService(session).create_manual_issue(case_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/issues/{issue_id}", response_model=IssueRead)
def update_issue(
    issue_id: int,
    payload: IssueUpdate,
    session: Session = Depends(get_session),
):
    issue = IssueService(session).get_issue(issue_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(issue, field, value)
    session.commit()
    return IssueService(session).get_issue(issue_id)


@router.post("/issues/{issue_id}/apply-ai-message", response_model=IssueRead)
def apply_ai_message(
    issue_id: int,
    payload: ApplyAiMessageRequest,
    session: Session = Depends(get_session),
):
    try:
        return IssueService(session).apply_ai_message(issue_id, payload.message_id, payload.action)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
