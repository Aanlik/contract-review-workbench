import importlib.util
import subprocess
import sys
from pathlib import Path
from time import perf_counter
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_api_key, encrypt_api_key
from app.core.database import get_session
from app.models.review import AppSetting
from app.schemas.settings import AiConnectionTestResult, AiSettings, SystemSettings
from app.services.ai_provider import OpenAICompatibleProvider
from app.services.task_queue import task_queue

router = APIRouter()

_ai_settings: AiSettings | None = None
_system_settings: SystemSettings | None = None


class OcrPackageStatus(BaseModel):
    installed: bool
    package: str
    import_name: str
    note: str | None = None


class OcrRuntimeStatus(BaseModel):
    current_engine: str
    current_engine_installed: bool
    install_supported: bool
    install_supported_reason: str | None = None
    engines: dict[str, OcrPackageStatus]


class OcrInstallRequest(BaseModel):
    target: Literal["rapid", "rapid-legacy", "paddle", "all"]


class OcrInstallResponse(BaseModel):
    task_id: str
    target: str
    message: str


OCR_INSTALL_TARGETS: dict[str, str] = {
    "rapid": "ocr-rapid",
    "rapid-legacy": "ocr-rapid-legacy",
    "paddle": "ocr-paddle",
    "all": "ocr-all",
}


def _encrypt_ai_value(data: dict) -> dict:
    """Return a copy with api_key encrypted."""
    encrypted = dict(data)
    if encrypted.get("api_key"):
        encrypted["api_key"] = encrypt_api_key(encrypted["api_key"])
    return encrypted


def _decrypt_ai_value(data: dict) -> dict:
    """Return a copy with api_key decrypted."""
    decrypted = dict(data)
    if decrypted.get("api_key"):
        decrypted["api_key"] = decrypt_api_key(decrypted["api_key"])
    return decrypted


def _package_installed(import_name: str) -> bool:
    return importlib.util.find_spec(import_name) is not None


def _load_system_settings_for_status(session: Session) -> SystemSettings:
    global _system_settings
    if _system_settings is not None:
        return _system_settings
    setting = session.get(AppSetting, "system")
    if setting is None:
        return SystemSettings()
    _system_settings = SystemSettings(**setting.value)
    return _system_settings


def _backend_dir() -> Path:
    return Path(__file__).resolve().parents[3]


def _run_ocr_install(task_id: str, target: str) -> dict[str, object]:
    extra = OCR_INSTALL_TARGETS[target]
    package_spec = f"{_backend_dir()}[{extra}]"
    command = [sys.executable, "-m", "pip", "install", "-e", package_spec]
    task_queue.update_progress(task_id, f"正在安装 OCR 依赖：{target}", step=1, total=3, percent=10)
    result = subprocess.run(command, capture_output=True, text=True, timeout=1800, check=False)
    task_queue.update_progress(task_id, "正在校验安装结果...", step=2, total=3, percent=80)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or f"pip install failed with code {result.returncode}")
    task_queue.update_progress(task_id, "OCR 依赖安装完成。", step=3, total=3, percent=100)
    return {
        "target": target,
        "command": " ".join(command),
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
    }


@router.put("/ai", response_model=AiSettings)
def save_ai_settings(payload: AiSettings, session: Session = Depends(get_session)):
    global _ai_settings
    _ai_settings = payload
    setting = session.get(AppSetting, "ai")
    value = _encrypt_ai_value(payload.model_dump())
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
    _ai_settings = AiSettings(**_decrypt_ai_value(setting.value))
    return _ai_settings


@router.put("/system", response_model=SystemSettings)
def save_system_settings(payload: SystemSettings, session: Session = Depends(get_session)):
    global _system_settings
    _system_settings = payload
    setting = session.get(AppSetting, "system")
    value = payload.model_dump()
    if setting is None:
        setting = AppSetting(key="system", value=value)
        session.add(setting)
    else:
        setting.value = value
    session.commit()
    return payload


@router.get("/system", response_model=SystemSettings)
def get_system_settings(session: Session = Depends(get_session)):
    global _system_settings
    if _system_settings is not None:
        return _system_settings
    setting = session.get(AppSetting, "system")
    if setting is None:
        return SystemSettings()
    _system_settings = SystemSettings(**setting.value)
    return _system_settings


@router.get("/ocr/status", response_model=OcrRuntimeStatus)
def get_ocr_runtime_status(session: Session = Depends(get_session)):
    system_settings = _load_system_settings_for_status(session)
    engines = {
        "rapidocr": OcrPackageStatus(
            installed=_package_installed("rapidocr"),
            package="rapidocr",
            import_name="rapidocr",
            note="RapidOCR 新版轻量引擎",
        ),
        "rapidocr_onnxruntime": OcrPackageStatus(
            installed=_package_installed("rapidocr_onnxruntime"),
            package="rapidocr-onnxruntime",
            import_name="rapidocr_onnxruntime",
            note="RapidOCR 旧版兼容包",
        ),
        "onnxruntime": OcrPackageStatus(
            installed=_package_installed("onnxruntime"),
            package="onnxruntime",
            import_name="onnxruntime",
        ),
        "paddleocr": OcrPackageStatus(
            installed=_package_installed("paddleocr"),
            package="paddleocr",
            import_name="paddleocr",
            note="PaddleOCR 中文高精度引擎",
        ),
    }
    current_installed = (
        engines["paddleocr"].installed
        if system_settings.ocr_engine == "paddleocr"
        else engines["rapidocr"].installed or engines["rapidocr_onnxruntime"].installed
    )
    install_supported = not getattr(sys, "frozen", False)
    return OcrRuntimeStatus(
        current_engine=system_settings.ocr_engine,
        current_engine_installed=current_installed,
        install_supported=install_supported,
        install_supported_reason=None if install_supported else "打包后的程序不支持运行时安装 OCR 依赖。",
        engines=engines,
    )


@router.post("/ocr/install", response_model=OcrInstallResponse, status_code=status.HTTP_202_ACCEPTED)
def install_ocr_dependencies(payload: OcrInstallRequest):
    if getattr(sys, "frozen", False):
        raise HTTPException(
            status_code=400,
            detail="打包后的程序不支持运行时安装 OCR 依赖，请使用包含 OCR 依赖的构建版本。",
        )
    task = task_queue.submit(_run_ocr_install, payload.target, label=f"install-ocr-{payload.target}")
    return OcrInstallResponse(
        task_id=task.task_id,
        target=payload.target,
        message=f"OCR 依赖安装任务已开始：{payload.target}",
    )


@router.post("/ai/test", response_model=AiConnectionTestResult)
def test_ai_settings(payload: AiSettings):
    started = perf_counter()
    try:
        OpenAICompatibleProvider(payload).chat(
            [
                {
                    "role": "user",
                    "content": "连接测试：请只回复「连接正常」。",
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
