"""Audit log service — records who did what and when."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.review import AuditLog


def record_audit(
    session: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    user: str = "system",
    details: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user=user,
        details=details,
    )
    session.add(entry)
    session.commit()
    return entry


def list_audit_logs(
    session: Session,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    from sqlalchemy import select

    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    stmt = stmt.limit(limit)
    return list(session.scalars(stmt).all())
