from collections.abc import Callable
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.review import AppSetting, DocumentPage, OcrBlock, UploadedFile
from app.schemas.settings import SystemSettings
from app.services.document_parser import DocumentParser, PaddleOcrProvider, RapidOcrProvider
from app.services.page_image_service import PageImageService
from app.services.task_queue import task_queue


def _run_ocr_retry(task_id: str, uploaded_file_id: int) -> dict:
    """Run a retry in a worker-owned database session."""
    from app.core.database import SessionLocal

    session = SessionLocal()
    try:
        task_queue.update_progress(task_id, "正在准备扫描识别材料...", step=1, total=3, percent=5)

        def update_ocr_progress(current_page: int, total_pages: int) -> None:
            percent = 10 + int(current_page / max(total_pages, 1) * 80)
            task_queue.update_progress(
                task_id,
                f"正在识别第 {current_page}/{total_pages} 页...",
                step=1,
                total=3,
                percent=percent,
            )

        uploaded = FileIngestService(session).retry_ocr(uploaded_file_id, update_ocr_progress)
        task_queue.update_progress(task_id, "正在保存识别结果和页面图片...", step=2, total=3, percent=95)
        task_queue.update_progress(task_id, "扫描识别完成。", step=3, total=3, percent=100)
        return {"file_id": uploaded.id, "status": uploaded.parse_status, "page_count": uploaded.page_count}
    finally:
        session.close()


class FileIngestService:
    def __init__(self, session: Session, parser: DocumentParser | None = None) -> None:
        self.session = session
        system_settings = self._system_settings()
        self.parser = parser or DocumentParser(
            ocr_provider=self._ocr_provider(system_settings),
            ocr_dpi=system_settings.ocr_dpi,
            preprocess_images=system_settings.preprocess_images,
        )
        self.ocr_dpi = system_settings.ocr_dpi

    def ingest(self, uploaded_file_id: int) -> UploadedFile:
        uploaded = self.session.get(UploadedFile, uploaded_file_id)
        if uploaded is None:
            raise ValueError("Uploaded file not found")

        file_path = Path(uploaded.original_path)
        try:
            parsed_pages = self.parser.extract_text(file_path, uploaded.file_type)
        except RuntimeError as exc:
            if "OCR" not in str(exc):
                return self._mark_ocr_failed(uploaded)
            uploaded.parse_method = "ocr"
            uploaded.parse_status = "needs_ocr"
            self.session.commit()
            self.session.refresh(uploaded)
            return uploaded
        except Exception:
            return self._mark_ocr_failed(uploaded)

        self._persist_pages(uploaded, parsed_pages)
        return uploaded

    def ingest_background(self, uploaded_file_id: int) -> str:
        """Queue OCR ingest as a background task. Returns task_id."""
        uploaded = self.session.get(UploadedFile, uploaded_file_id)
        if uploaded is None:
            raise ValueError("Uploaded file not found")
        uploaded.parse_status = "processing"
        uploaded.parse_method = "ocr"
        self.session.commit()
        task = task_queue.submit(_run_ocr_retry, uploaded_file_id, label=f"ocr-retry-{uploaded_file_id}")
        return task.task_id

    def retry_ocr(
        self,
        uploaded_file_id: int,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> UploadedFile:
        uploaded = self.session.get(UploadedFile, uploaded_file_id)
        if uploaded is None:
            raise ValueError("Uploaded file not found")

        file_path = Path(uploaded.original_path)
        try:
            parsed_pages = self.parser.extract_text(file_path, uploaded.file_type, progress_callback)
        except Exception as exc:
            self._mark_ocr_failed(uploaded)
            raise RuntimeError(f"OCR 识别失败：{exc}") from exc

        self._persist_pages(uploaded, parsed_pages)
        return uploaded

    def _persist_pages(self, uploaded: UploadedFile, parsed_pages) -> None:
        uploaded.page_count = len(parsed_pages)
        uploaded.parse_method = self._detect_parse_method(parsed_pages)
        uploaded.parse_status = "parsed" if parsed_pages else "empty"
        try:
            page_images = PageImageService().persist(uploaded, parsed_pages, self.ocr_dpi)
        except Exception:
            page_images = {}

        for parsed_page in parsed_pages:
            image_info = page_images.get(parsed_page.page_number)
            page = DocumentPage(
                file_id=uploaded.id,
                page_number=parsed_page.page_number,
                image_path=image_info.relative_path if image_info else None,
                width=image_info.width if image_info else None,
                height=image_info.height if image_info else None,
                has_text_layer=any(block.source == "pdf_text" for block in parsed_page.blocks),
                ocr_status="completed" if parsed_page.blocks else "empty",
            )
            self.session.add(page)
            self.session.flush()
            for block in parsed_page.blocks:
                self.session.add(
                    OcrBlock(
                        page_id=page.id,
                        text=block.text,
                        bbox=block.bbox,
                        confidence=block.confidence,
                        order_index=block.order_index,
                        source=block.source,
                    )
                )

        self.session.commit()
        self.session.refresh(uploaded)

    def _mark_ocr_failed(self, uploaded: UploadedFile) -> UploadedFile:
        uploaded.parse_method = "ocr"
        uploaded.parse_status = "ocr_failed"
        self.session.commit()
        self.session.refresh(uploaded)
        return uploaded

    def _system_settings(self) -> SystemSettings:
        setting = self.session.get(AppSetting, "system")
        return SystemSettings(**setting.value) if setting else SystemSettings()

    def _ocr_provider(self, system_settings: SystemSettings):
        if system_settings.ocr_engine == "rapidocr":
            return RapidOcrProvider()
        return PaddleOcrProvider()

    def _detect_parse_method(self, parsed_pages) -> str | None:
        sources = {block.source for page in parsed_pages for block in page.blocks}
        if "ocr" in sources:
            return "ocr"
        if "pdf_text" in sources:
            return "text"
        return None
