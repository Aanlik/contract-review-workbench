from pathlib import Path

from sqlalchemy.orm import Session

from app.models.review import AppSetting, DocumentPage, OcrBlock, UploadedFile
from app.schemas.settings import SystemSettings
from app.services.document_parser import DocumentParser, PaddleOcrProvider, RapidOcrProvider


class FileIngestService:
    def __init__(self, session: Session, parser: DocumentParser | None = None) -> None:
        self.session = session
        system_settings = self._system_settings()
        self.parser = parser or DocumentParser(
            ocr_provider=self._ocr_provider(system_settings),
            ocr_dpi=system_settings.ocr_dpi,
            preprocess_images=system_settings.preprocess_images,
        )

    def ingest(self, uploaded_file_id: int) -> UploadedFile:
        uploaded = self.session.get(UploadedFile, uploaded_file_id)
        if uploaded is None:
            raise ValueError("Uploaded file not found")

        file_path = Path(uploaded.original_path)
        try:
            parsed_pages = self.parser.extract_text(file_path, uploaded.file_type)
        except RuntimeError as exc:
            if "OCR" not in str(exc):
                raise
            uploaded.parse_method = "ocr"
            uploaded.parse_status = "needs_ocr"
            self.session.commit()
            self.session.refresh(uploaded)
            return uploaded

        uploaded.page_count = len(parsed_pages)
        uploaded.parse_method = self._detect_parse_method(parsed_pages)
        uploaded.parse_status = "parsed" if parsed_pages else "empty"

        for parsed_page in parsed_pages:
            page = DocumentPage(
                file_id=uploaded.id,
                page_number=parsed_page.page_number,
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
