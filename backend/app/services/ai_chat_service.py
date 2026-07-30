from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review import AiConversation, AiMessage, Issue, ReviewCase


class AiChatService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create_conversation(
        self,
        case_id: int,
        issue_id: int | None = None,
    ) -> AiConversation:
        review_case = self.session.get(ReviewCase, case_id)
        if review_case is None:
            raise ValueError("Review case not found")

        if issue_id is not None and self.session.get(Issue, issue_id) is None:
            raise ValueError("Issue not found")

        scope = "issue" if issue_id is not None else "case"
        conversation = self.session.scalar(
            select(AiConversation).where(
                AiConversation.case_id == case_id,
                AiConversation.issue_id == issue_id,
                AiConversation.scope == scope,
            )
        )
        if conversation is None:
            conversation = AiConversation(case_id=case_id, issue_id=issue_id, scope=scope)
            self.session.add(conversation)
            self.session.commit()
            self.session.refresh(conversation)
        return conversation

    def add_message(
        self,
        case_id: int,
        content: str,
        issue_id: int | None = None,
    ) -> AiConversation:
        conversation = self.get_or_create_conversation(case_id, issue_id)
        self.session.add(
            AiMessage(conversation_id=conversation.id, role="user", content=content)
        )
        assistant_content = self._build_local_assistant_reply(content, issue_id)
        self.session.add(
            AiMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=assistant_content,
                model="local-draft",
            )
        )
        self.session.commit()
        return conversation

    def list_messages(self, conversation_id: int) -> list[AiMessage]:
        return self.session.scalars(
            select(AiMessage)
            .where(AiMessage.conversation_id == conversation_id)
            .order_by(AiMessage.id.asc())
        ).all()

    def _build_local_assistant_reply(self, content: str, issue_id: int | None) -> str:
        scope = "当前问题" if issue_id is not None else "整份合同"
        return (
            f"已记录你对{scope}的追问：{content}\n\n"
            "当前未配置可调用的第三方 AI 或尚未触发真实模型调用，"
            "系统先保存该互动。配置 AI 后可重新分析并应用为风险说明、修改建议或新增问题。"
        )
