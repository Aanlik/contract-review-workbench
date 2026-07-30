from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReviewCaseCreate(BaseModel):
    title: str
    note: str | None = None


class ReviewCaseUpdate(BaseModel):
    title: str | None = None
    note: str | None = None


class ReviewCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    note: str | None
    status: str
    current_version: int
    highest_risk_level: str | None
    issue_count: int
    created_at: datetime
    updated_at: datetime
