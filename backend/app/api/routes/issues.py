from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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
from app.services.audit_service import record_audit
from app.services.issue_service import IssueService

router = APIRouter()


class BatchUpdateRequest(BaseModel):
    issue_ids: list[int]
    status: str | None = None
    risk_level: str | None = None


class BatchDeleteRequest(BaseModel):
    issue_ids: list[int]


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
        issue = IssueService(session).create_manual_issue(case_id, payload)
        record_audit(session, action="create_manual_issue", entity_type="issue",
                     entity_id=issue.id, details={"case_id": case_id, "title": issue.title})
        return issue
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/issues/{issue_id}", response_model=IssueRead)
def update_issue(
    issue_id: int,
    payload: IssueUpdate,
    session: Session = Depends(get_session),
):
    issue = IssueService(session).get_issue(issue_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(issue, field, value)
    session.commit()
    record_audit(session, action="update", entity_type="issue", entity_id=issue_id, details=changes)
    return IssueService(session).get_issue(issue_id)


@router.post("/issues/{issue_id}/apply-ai-message", response_model=IssueRead)
def apply_ai_message(
    issue_id: int,
    payload: ApplyAiMessageRequest,
    session: Session = Depends(get_session),
):
    try:
        result = IssueService(session).apply_ai_message(issue_id, payload.message_id, payload.action)
        record_audit(session, action="apply_ai_message", entity_type="issue",
                     entity_id=issue_id, details={"message_id": payload.message_id, "action": payload.action})
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/ai-messages/apply", response_model=IssueRead)
def apply_ai_message_without_issue(
    payload: ApplyAiMessageRequest,
    session: Session = Depends(get_session),
):
    try:
        return IssueService(session).apply_ai_message(None, payload.message_id, payload.action)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/issues/batch-update", response_model=list[IssueRead])
def batch_update_issues(
    payload: BatchUpdateRequest,
    session: Session = Depends(get_session),
):
    issues = session.scalars(
        select(Issue)
        .where(Issue.id.in_(payload.issue_ids))
        .options(selectinload(Issue.evidence_refs))
    ).all()
    for issue in issues:
        if payload.status is not None:
            issue.status = payload.status
        if payload.risk_level is not None:
            issue.risk_level = payload.risk_level
    session.commit()
    record_audit(session, action="batch_update", entity_type="issue",
                 details={"issue_ids": payload.issue_ids, "status": payload.status, "risk_level": payload.risk_level})
    return issues


@router.post("/issues/batch-delete", status_code=204)
def batch_delete_issues(
    payload: BatchDeleteRequest,
    session: Session = Depends(get_session),
):
    issues = session.scalars(
        select(Issue).where(Issue.id.in_(payload.issue_ids))
    ).all()
    for issue in issues:
        session.delete(issue)
    session.commit()
    record_audit(session, action="batch_delete", entity_type="issue",
                 details={"issue_ids": payload.issue_ids, "count": len(payload.issue_ids)})
