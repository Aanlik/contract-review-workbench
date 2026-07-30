from datetime import datetime

from pydantic import BaseModel, ConfigDict
from typing import Literal


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


class EvidenceRefRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_id: int | None
    page_number: int | None
    ocr_block_id: int | None
    original_text: str | None
    bbox: list[float] | None
    note: str | None
    confidence: float | None


class IssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    issue_type: str
    source: str
    risk_level: str
    title: str
    description: str
    suggestion: str | None
    replacement_clause: str | None
    status: str
    review_version: int
    evidence_refs: list[EvidenceRefRead] = []


class ManualIssueCreate(BaseModel):
    title: str
    risk_level: Literal["high", "medium", "low", "info"]
    description: str
    suggestion: str | None = None
    evidence_text: str | None = None


class IssueUpdate(BaseModel):
    title: str | None = None
    risk_level: Literal["high", "medium", "low", "info"] | None = None
    description: str | None = None
    suggestion: str | None = None
    replacement_clause: str | None = None
    status: Literal["pending", "confirmed", "modified", "rejected", "needs_review"] | None = None


class ApplyAiMessageRequest(BaseModel):
    message_id: int
    action: Literal["update_description", "update_suggestion", "adjust_risk_level", "new_issue"]
