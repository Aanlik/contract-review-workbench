from typing import Literal

from pydantic import BaseModel, Field


class AiSettings(BaseModel):
    base_url: str
    api_key: str
    model: str
    temperature: float = Field(default=0.2, ge=0, le=2)
    timeout_seconds: float = Field(default=60, gt=0)


class AiConnectionTestResult(BaseModel):
    ok: bool
    model: str
    message: str
    latency_ms: int


class SystemSettings(BaseModel):
    ocr_engine: Literal["paddleocr", "rapidocr"] = "paddleocr"
    storage_root: str = "./data/storage"
    ocr_dpi: int = Field(default=260, ge=120, le=500)
    preprocess_images: bool = True
