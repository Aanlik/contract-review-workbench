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


class UploadedFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    file_type: str
    file_name: str
    original_path: str
    content_type: str | None
    size_bytes: int
    page_count: int | None
    parse_method: str | None
    parse_status: str
    uploaded_at: datetime
