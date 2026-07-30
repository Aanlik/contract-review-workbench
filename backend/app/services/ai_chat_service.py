from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review import AiConversation, AiMessage, AppSetting, Issue, ReviewCase
from app.schemas.settings import AiSettings
from app.services.ai_provider import OpenAICompatibleProvider


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

        ai_settings = self._load_ai_settings()
        if ai_settings:
            assistant_content = self._call_ai(conversation, content, ai_settings, issue_id)
            model_name = ai_settings.model
        else:
            assistant_content = self._build_local_assistant_reply(content, issue_id)
            model_name = "local-draft"

        self.session.add(
            AiMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=assistant_content,
                model=model_name,
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

    def _load_ai_settings(self) -> AiSettings | None:
        setting = self.session.get(AppSetting, "ai")
        if setting is None:
            return None
        try:
            return AiSettings(**setting.value)
        except Exception:
            return None

    def _call_ai(
        self,
        conversation: AiConversation,
        user_content: str,
        ai_settings: AiSettings,
        issue_id: int | None,
    ) -> str:
        scope = "当前问题" if issue_id is not None else "整份合同"
        system_prompt = (
            "你是一名专业法律顾问，负责协助业务人员和法务审查合同。"
            "请用专业但易懂的中文回答，必要时给出修改建议。"
            f"当前讨论范围：{scope}。"
        )

        history = self.list_messages(conversation.id)
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-10:]:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_content})

        try:
            return OpenAICompatibleProvider(ai_settings).chat(messages)
        except Exception as exc:
            return f"AI 调用失败（{exc}），消息已保存。请检查 AI 配置后重试。"

    def _build_local_assistant_reply(self, content: str, issue_id: int | None) -> str:
        scope = "当前问题" if issue_id is not None else "整份合同"
        return (
            f"已记录你对{scope}的追问：{content}\n\n"
            "当前未配置可调用的第三方 AI 或尚未触发真实模型调用，"
            "系统先保存该互动。配置 AI 后可重新分析并应用为风险说明、修改建议或新增问题。"
        )
