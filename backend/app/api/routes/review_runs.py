from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_session
from app.models.review import Issue, ReviewCase, ReviewVersion
from app.schemas.review import IssueRead, ReviewCaseRead, ReviewVersionRead
from app.services.review_run_service import ReviewRunService
from app.services.task_queue import task_queue

router = APIRouter()


class ReanalyzeRequest(BaseModel):
    instruction: str | None = None


class ReanalyzeAsyncResponse(BaseModel):
    task_id: str
    case_id: int


class VersionDiffItem(BaseModel):
    issue_id: int
    title: str
    change_type: str
    risk_level: str
    description: str
    old_risk_level: str | None = None


class VersionDiffResponse(BaseModel):
    version_a: int
    version_b: int
    changes: list[VersionDiffItem]
    summary: str


def _run_reanalyze_in_background(task_id: str, case_id: int, instruction: str | None) -> dict:
    """Worker function executed by the task queue."""
    from app.core.database import SessionLocal
    session = SessionLocal()
    try:
        service = ReviewRunService(session, task_id=task_id)
        review_case = service.reanalyze(case_id, instruction)
        return {
            "case_id": review_case.id,
            "status": review_case.status,
            "issue_count": review_case.issue_count,
            "version": review_case.current_version,
        }
    finally:
        session.close()


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


@router.post(
    "/cases/{case_id}/reanalyze-async",
    response_model=ReanalyzeAsyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def reanalyze_case_async(
    case_id: int,
    payload: ReanalyzeRequest,
    session: Session = Depends(get_session),
):
    """Submit reanalyze as a background task. Returns task_id for polling."""
    review_case = session.get(ReviewCase, case_id)
    if review_case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    task = task_queue.submit(_run_reanalyze_in_background, case_id, payload.instruction)
    return ReanalyzeAsyncResponse(task_id=task.task_id, case_id=case_id)


@router.get("/cases/{case_id}/versions", response_model=list[ReviewVersionRead])
def list_case_versions(case_id: int, session: Session = Depends(get_session)):
    return session.scalars(
        select(ReviewVersion)
        .where(ReviewVersion.case_id == case_id)
        .order_by(ReviewVersion.version_number.desc(), ReviewVersion.id.desc())
    ).all()


@router.get("/cases/{case_id}/versions/diff", response_model=VersionDiffResponse)
def diff_versions(
    case_id: int,
    version_a: int,
    version_b: int,
    session: Session = Depends(get_session),
):
    case = session.get(ReviewCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    issues_a = session.scalars(
        select(Issue)
        .where(Issue.case_id == case_id, Issue.review_version == version_a)
        .options(selectinload(Issue.evidence_refs))
    ).all()

    issues_b = session.scalars(
        select(Issue)
        .where(Issue.case_id == case_id, Issue.review_version == version_b)
        .options(selectinload(Issue.evidence_refs))
    ).all()

    titles_a = {issue.title: issue for issue in issues_a}
    titles_b = {issue.title: issue for issue in issues_b}

    changes: list[VersionDiffItem] = []

    for title, issue in titles_b.items():
        if title not in titles_a:
            changes.append(VersionDiffItem(
                issue_id=issue.id, title=issue.title, change_type="added",
                risk_level=issue.risk_level, description=issue.description,
            ))

    for title, issue in titles_a.items():
        if title not in titles_b:
            changes.append(VersionDiffItem(
                issue_id=issue.id, title=issue.title, change_type="removed",
                risk_level=issue.risk_level, description=issue.description,
            ))

    for title in set(titles_a.keys()) & set(titles_b.keys()):
        issue_a = titles_a[title]
        issue_b = titles_b[title]
        if (
            issue_a.risk_level != issue_b.risk_level
            or issue_a.description != issue_b.description
            or issue_a.suggestion != issue_b.suggestion
            or issue_a.status != issue_b.status
        ):
            changes.append(VersionDiffItem(
                issue_id=issue_b.id, title=issue_b.title, change_type="modified",
                risk_level=issue_b.risk_level, description=issue_b.description,
                old_risk_level=issue_a.risk_level,
            ))

    added = sum(1 for c in changes if c.change_type == "added")
    removed = sum(1 for c in changes if c.change_type == "removed")
    modified = sum(1 for c in changes if c.change_type == "modified")
    summary = f"V{version_a} → V{version_b}：新增 {added}、移除 {removed}、变更 {modified} 个问题"

    return VersionDiffResponse(
        version_a=version_a, version_b=version_b, changes=changes, summary=summary,
    )
