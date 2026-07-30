from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class ReviewCase(Base):
    __tablename__ = "review_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(index=True)
    note: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(default="created")
    current_version: Mapped[int] = mapped_column(default=1)
    highest_risk_level: Mapped[str | None] = mapped_column(default=None)
    issue_count: Mapped[int] = mapped_column(default=0)
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    files: Mapped[list["UploadedFile"]] = relationship(back_populates="case")
    issues: Mapped[list["Issue"]] = relationship(back_populates="case")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("review_cases.id"), index=True)
    file_type: Mapped[str]
    file_name: Mapped[str]
    original_path: Mapped[str]
    content_type: Mapped[str | None] = mapped_column(default=None)
    size_bytes: Mapped[int] = mapped_column(default=0)
    page_count: Mapped[int | None] = mapped_column(default=None)
    parse_method: Mapped[str | None] = mapped_column(default=None)
    parse_status: Mapped[str] = mapped_column(default="uploaded")
    uploaded_at: Mapped[datetime] = mapped_column(default=utcnow)

    case: Mapped[ReviewCase] = relationship(back_populates="files")
    pages: Mapped[list["DocumentPage"]] = relationship(back_populates="file")


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("uploaded_files.id"), index=True)
    page_number: Mapped[int]
    image_path: Mapped[str | None] = mapped_column(default=None)
    width: Mapped[float | None] = mapped_column(default=None)
    height: Mapped[float | None] = mapped_column(default=None)
    has_text_layer: Mapped[bool] = mapped_column(default=False)
    ocr_status: Mapped[str] = mapped_column(default="pending")

    file: Mapped[UploadedFile] = relationship(back_populates="pages")
    ocr_blocks: Mapped[list["OcrBlock"]] = relationship(back_populates="page")


class OcrBlock(Base):
    __tablename__ = "ocr_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("document_pages.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    bbox: Mapped[list[float] | None] = mapped_column(JSON, default=None)
    confidence: Mapped[float | None] = mapped_column(default=None)
    order_index: Mapped[int] = mapped_column(default=0)
    source: Mapped[str]

    page: Mapped[DocumentPage] = relationship(back_populates="ocr_blocks")


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("review_cases.id"), index=True)
    issue_type: Mapped[str]
    source: Mapped[str]
    risk_level: Mapped[str]
    title: Mapped[str]
    description: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text, default=None)
    replacement_clause: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(default="pending")
    review_version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    case: Mapped[ReviewCase] = relationship(back_populates="issues")
    evidence_refs: Mapped[list["EvidenceRef"]] = relationship(back_populates="issue")


class EvidenceRef(Base):
    __tablename__ = "evidence_refs"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True)
    file_id: Mapped[int | None] = mapped_column(ForeignKey("uploaded_files.id"), default=None)
    page_number: Mapped[int | None] = mapped_column(default=None)
    ocr_block_id: Mapped[int | None] = mapped_column(ForeignKey("ocr_blocks.id"), default=None)
    original_text: Mapped[str | None] = mapped_column(Text, default=None)
    bbox: Mapped[list[float] | None] = mapped_column(JSON, default=None)
    note: Mapped[str | None] = mapped_column(Text, default=None)
    confidence: Mapped[float | None] = mapped_column(default=None)

    issue: Mapped[Issue] = relationship(back_populates="evidence_refs")


class AiConversation(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("review_cases.id"), index=True)
    issue_id: Mapped[int | None] = mapped_column(ForeignKey("issues.id"), default=None)
    scope: Mapped[str] = mapped_column(default="case")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AiMessage(Base):
    __tablename__ = "ai_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("ai_conversations.id"), index=True)
    role: Mapped[str]
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(default=None)
    is_applied: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AiApplication(Base):
    __tablename__ = "ai_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("ai_messages.id"), index=True)
    issue_id: Mapped[int | None] = mapped_column(ForeignKey("issues.id"), default=None)
    action: Mapped[str]
    before_value: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    after_value: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ReviewVersion(Base):
    __tablename__ = "review_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("review_cases.id"), index=True)
    version_number: Mapped[int]
    trigger: Mapped[str]
    ai_config_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    review_request: Mapped[str | None] = mapped_column(Text, default=None)
    note: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ExportRecord(Base):
    __tablename__ = "export_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("review_cases.id"), index=True)
    export_format: Mapped[str]
    file_path: Mapped[str]
    export_scope: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
