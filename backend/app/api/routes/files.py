from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.routes.cases import get_active_case
from app.core.database import get_session
from app.core.storage import StorageService
from app.models.review import AppSetting, DocumentPage, UploadedFile
from app.schemas.review import CaseDocumentRead, DocumentPageRead, OcrBlockRead, UploadedFileRead
from app.schemas.settings import SystemSettings
from app.services.file_ingest_service import FileIngestService
from app.services.page_image_service import PageImageService

router = APIRouter()

AllowedFileType = Literal[
    "contract",
    "legal_review_report",
    "contract_approval",
    "matter_report",
    "sign_report",
    "meeting_minutes",
    "approval",
    "seal_record",
    "other",
]

ALLOWED_FILE_TYPES = {
    "contract",
    "legal_review_report",
    "contract_approval",
    "matter_report",
    "sign_report",
    "meeting_minutes",
    "approval",
    "seal_record",
    "other",
}


@router.get("/cases/{case_id}/files", response_model=list[UploadedFileRead])
def list_case_files(case_id: int, session: Session = Depends(get_session)):
    get_active_case(case_id, session)
    return session.scalars(
        select(UploadedFile)
        .where(UploadedFile.case_id == case_id)
        .order_by(UploadedFile.uploaded_at.asc(), UploadedFile.id.asc())
    ).all()


@router.get("/cases/{case_id}/documents", response_model=list[CaseDocumentRead])
def list_case_documents(case_id: int, session: Session = Depends(get_session)):
    get_active_case(case_id, session)
    files = session.scalars(
        select(UploadedFile)
        .where(UploadedFile.case_id == case_id)
        .options(selectinload(UploadedFile.pages).selectinload("*"))
        .order_by(UploadedFile.uploaded_at.asc(), UploadedFile.id.asc())
    ).all()
    documents: list[CaseDocumentRead] = []
    for uploaded in files:
        pages = sorted(uploaded.pages, key=lambda page: page.page_number)
        documents.append(
            CaseDocumentRead(
                id=uploaded.id,
                file_type=uploaded.file_type,
                file_name=uploaded.file_name,
                parse_method=uploaded.parse_method,
                parse_status=uploaded.parse_status,
                pages=[
                    DocumentPageRead(
                        id=page.id,
                        page_number=page.page_number,
                        image_path=page.image_path,
                        width=page.width,
                        height=page.height,
                        has_text_layer=page.has_text_layer,
                        ocr_status=page.ocr_status,
                        blocks=[
                            OcrBlockRead.model_validate(block)
                            for block in sorted(page.ocr_blocks, key=lambda item: item.order_index)
                        ],
                    )
                    for page in pages
                ],
            )
        )
    return documents


@router.get("/cases/{case_id}/documents/{file_id}/pages/{page_number}/image")
def get_document_page_image(
    case_id: int,
    file_id: int,
    page_number: int,
    session: Session = Depends(get_session),
):
    get_active_case(case_id, session)
    uploaded = session.scalar(
        select(UploadedFile).where(UploadedFile.id == file_id, UploadedFile.case_id == case_id)
    )
    if uploaded is None:
        raise HTTPException(status_code=404, detail="Document not found")

    page = session.scalar(
        select(DocumentPage).where(DocumentPage.file_id == file_id, DocumentPage.page_number == page_number)
    )
    if page is None:
        raise HTTPException(status_code=404, detail="Document page not found")

    image_service = PageImageService()
    image_path = None
    if page.image_path:
        try:
            candidate = image_service.resolve(page.image_path)
        except ValueError:
            raise HTTPException(status_code=404, detail="Page image not found") from None
        if candidate.is_file():
            image_path = candidate

    if image_path is None:
        system_setting = session.get(AppSetting, "system")
        system_settings = SystemSettings(**system_setting.value) if system_setting else SystemSettings()
        try:
            info = image_service.ensure(uploaded, page_number, system_settings.ocr_dpi)
        except Exception:
            info = None
        if info is None:
            raise HTTPException(status_code=404, detail="Page image not available")
        page.image_path = info.relative_path
        page.width = info.width
        page.height = info.height
        session.commit()
        image_path = image_service.resolve(info.relative_path)

    return FileResponse(str(image_path), media_type="image/png")


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
    return FileIngestService(session).ingest(uploaded.id)
