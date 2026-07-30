from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.ai import AiConversationRead, ChatRequest
from app.services.ai_chat_service import AiChatService

router = APIRouter()


def serialize_conversation(service: AiChatService, conversation) -> AiConversationRead:
    return AiConversationRead(
        id=conversation.id,
        case_id=conversation.case_id,
        issue_id=conversation.issue_id,
        scope=conversation.scope,
        messages=service.list_messages(conversation.id),
    )


@router.get("/cases/{case_id}/chat", response_model=AiConversationRead)
def get_case_chat(case_id: int, session: Session = Depends(get_session)):
    try:
        service = AiChatService(session)
        conversation = service.get_or_create_conversation(case_id)
        return serialize_conversation(service, conversation)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/cases/{case_id}/chat",
    response_model=AiConversationRead,
    status_code=status.HTTP_201_CREATED,
)
def post_case_chat(
    case_id: int,
    payload: ChatRequest,
    session: Session = Depends(get_session),
):
    try:
        service = AiChatService(session)
        conversation = service.add_message(case_id, payload.message)
        return serialize_conversation(service, conversation)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/issues/{issue_id}/chat", response_model=AiConversationRead)
def get_issue_chat(issue_id: int, case_id: int, session: Session = Depends(get_session)):
    try:
        service = AiChatService(session)
        conversation = service.get_or_create_conversation(case_id, issue_id)
        return serialize_conversation(service, conversation)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/issues/{issue_id}/chat",
    response_model=AiConversationRead,
    status_code=status.HTTP_201_CREATED,
)
def post_issue_chat(
    issue_id: int,
    payload: ChatRequest,
    case_id: int,
    session: Session = Depends(get_session),
):
    try:
        service = AiChatService(session)
        conversation = service.add_message(case_id, payload.message, issue_id)
        return serialize_conversation(service, conversation)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
