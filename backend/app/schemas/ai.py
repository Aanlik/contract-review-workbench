from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    message: str


class AiMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    model: str | None
    is_applied: bool
    created_at: datetime


class AiConversationRead(BaseModel):
    id: int
    case_id: int
    issue_id: int | None
    scope: str
    messages: list[AiMessageRead]
