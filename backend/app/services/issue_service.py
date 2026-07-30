from sqlalchemy.orm import Session, selectinload

from app.models.review import AiApplication, AiConversation, AiMessage, EvidenceRef, Issue, ReviewCase
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

    def apply_ai_message(self, issue_id: int | None, message_id: int, action: str) -> Issue:
        message = self.session.get(AiMessage, message_id)
        if message is None:
            raise ValueError("AI message not found")
        if action == "new_issue":
            return self._create_issue_from_ai_message(message)

        if issue_id is None:
            raise ValueError("Issue not found")

        issue = self.get_issue(issue_id)

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

    def _create_issue_from_ai_message(self, message: AiMessage) -> Issue:
        conversation = self.session.get(AiConversation, message.conversation_id)
        if conversation is None:
            raise ValueError("AI conversation not found")
        review_case = self.session.get(ReviewCase, conversation.case_id)
        if review_case is None:
            raise ValueError("Review case not found")

        issue = Issue(
            case_id=conversation.case_id,
            issue_type="manual_mark",
            source="ai_modified_by_human",
            risk_level="medium",
            title="AI 建议新增问题",
            description=message.content,
            suggestion=message.content,
            status="pending",
            review_version=review_case.current_version,
        )
        self.session.add(issue)
        self.session.flush()
        message.is_applied = True
        review_case.issue_count += 1
        self.session.add(
            AiApplication(
                message_id=message.id,
                issue_id=issue.id,
                action="new_issue",
                before_value=None,
                after_value={"description": issue.description},
            )
        )
        self.session.commit()
        return self.get_issue(issue.id)
