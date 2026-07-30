from sqlalchemy.orm import Session, selectinload

from app.models.review import AiApplication, AiMessage, EvidenceRef, Issue, ReviewCase
from app.schemas.review import ManualIssueCreate


class IssueService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_manual_issue(self, case_id: int, payload: ManualIssueCreate) -> Issue:
        review_case = self.session.get(ReviewCase, case_id)
        if review_case is None:
            raise ValueError("Review case not found")

        issue = Issue(
            case_id=case_id,
            issue_type="manual_mark",
            source="manual",
            risk_level=payload.risk_level,
            title=payload.title,
            description=payload.description,
            suggestion=payload.suggestion,
            status="pending",
            review_version=review_case.current_version,
        )
        self.session.add(issue)
        self.session.flush()

        if payload.evidence_text:
            self.session.add(EvidenceRef(issue_id=issue.id, original_text=payload.evidence_text))

        review_case.issue_count += 1
        self.session.commit()
        return self.get_issue(issue.id)

    def get_issue(self, issue_id: int) -> Issue:
        issue = self.session.get(
            Issue,
            issue_id,
            options=[selectinload(Issue.evidence_refs)],
        )
        if issue is None:
            raise ValueError("Issue not found")
        return issue

    def apply_ai_message(self, issue_id: int, message_id: int, action: str) -> Issue:
        issue = self.get_issue(issue_id)
        message = self.session.get(AiMessage, message_id)
        if message is None:
            raise ValueError("AI message not found")

        before = {
            "description": issue.description,
            "suggestion": issue.suggestion,
            "risk_level": issue.risk_level,
        }
        if action == "update_description":
            issue.description = message.content
        elif action == "update_suggestion":
            issue.suggestion = message.content
        elif action == "adjust_risk_level":
            issue.risk_level = message.content.strip().lower()
        else:
            raise ValueError("Unsupported AI application action")

        issue.source = "ai_modified_by_human"
        issue.status = "modified"
        message.is_applied = True
        self.session.add(
            AiApplication(
                message_id=message_id,
                issue_id=issue_id,
                action=action,
                before_value=before,
                after_value={
                    "description": issue.description,
                    "suggestion": issue.suggestion,
                    "risk_level": issue.risk_level,
                },
            )
        )
        self.session.commit()
        return self.get_issue(issue_id)
