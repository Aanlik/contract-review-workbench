from time import perf_counter

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models.review import AppSetting
from app.schemas.settings import AiConnectionTestResult, AiSettings
from app.services.ai_provider import OpenAICompatibleProvider

router = APIRouter()

_ai_settings: AiSettings | None = None


@router.put("/ai", response_model=AiSettings)
def save_ai_settings(payload: AiSettings, session: Session = Depends(get_session)):
    global _ai_settings
    _ai_settings = payload
    setting = session.get(AppSetting, "ai")
    value = payload.model_dump()
    if setting is None:
        setting = AppSetting(key="ai", value=value)
        session.add(setting)
    else:
        setting.value = value
    session.commit()
    return payload


@router.get("/ai", response_model=AiSettings | None)
def get_ai_settings(session: Session = Depends(get_session)):
    global _ai_settings
    if _ai_settings is not None:
        return _ai_settings
    setting = session.get(AppSetting, "ai")
    if setting is None:
        return None
    _ai_settings = AiSettings(**setting.value)
    return _ai_settings


@router.post("/ai/test", response_model=AiConnectionTestResult)
def test_ai_settings(payload: AiSettings):
    started = perf_counter()
    try:
        OpenAICompatibleProvider(payload).chat(
            [
                {
                    "role": "user",
                    "content": "连接测试：请只回复“连接正常”。",
                }
            ]
        )
    except Exception as exc:
        return AiConnectionTestResult(
            ok=False,
            model=payload.model,
            message=f"AI 接口连接失败：{exc}",
            latency_ms=int((perf_counter() - started) * 1000),
        )
    return AiConnectionTestResult(
        ok=True,
        model=payload.model,
        message="AI 接口连接正常。",
        latency_ms=int((perf_counter() - started) * 1000),
    )
