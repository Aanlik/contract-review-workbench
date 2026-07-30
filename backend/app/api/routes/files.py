from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.routes.cases import get_active_case
from app.core.database import get_session
from app.core.storage import StorageService
from app.models.review import UploadedFile
from app.schemas.review import UploadedFileRead

router = APIRouter()

AllowedFileType = Literal[
    "contract",
    "sign_report",
    "meeting_minutes",
    "approval",
    "seal_record",
    "other",
]

ALLOWED_FILE_TYPES = {
    "contract",
    "sign_report",
    "meeting_minutes",
    "approval",
    "seal_record",
    "other",
}


@router.post(
    "/cases/{case_id}/files",
    response_model=UploadedFileRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_case_file(
    case_id: int,
    file_type: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    get_active_case(case_id, session)
    if file_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported file type")

    stored = StorageService().save_upload(case_id, file)
    uploaded = UploadedFile(
        case_id=case_id,
        file_type=file_type,
        file_name=stored.original_name,
        original_path=str(stored.path),
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
        parse_status="uploaded",
    )
    session.add(uploaded)
    session.commit()
    session.refresh(uploaded)
    return uploaded
