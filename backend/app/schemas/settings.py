from pydantic import BaseModel, Field


class AiSettings(BaseModel):
    base_url: str
    api_key: str
    model: str
    temperature: float = Field(default=0.2, ge=0, le=2)
    timeout_seconds: float = Field(default=60, gt=0)
