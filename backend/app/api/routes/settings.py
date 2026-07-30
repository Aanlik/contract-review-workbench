from fastapi import APIRouter

from app.schemas.settings import AiSettings

router = APIRouter()

_ai_settings: AiSettings | None = None


@router.put("/ai", response_model=AiSettings)
def save_ai_settings(payload: AiSettings):
    global _ai_settings
    _ai_settings = payload
    return payload


@router.get("/ai", response_model=AiSettings | None)
def get_ai_settings():
    return _ai_settings
