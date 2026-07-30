from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.services.audit_service import list_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
def get_audit_logs(
    entity_type: str | None = Query(None),
    entity_id: int | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session),
):
    logs = list_audit_logs(session, entity_type=entity_type, entity_id=entity_id, limit=limit)
    return [
        {
            "id": log.id,
            "action": log.action,
            "entityType": log.entity_type,
            "entityId": log.entity_id,
            "user": log.user,
            "details": log.details,
            "createdAt": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
