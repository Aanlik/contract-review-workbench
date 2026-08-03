import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from app.core.config import settings
from app.models.review import UploadedFile
from app.services.document_parser import ParsedPage


@dataclass(frozen=True)
class PageImageInfo:
    page_number: int
    relative_path: str
    width: int
    height: int


class PageImageService:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or settings.storage_root).resolve()

    def persist(
        self,
        uploaded_file: UploadedFile,
        parsed_pages: list[ParsedPage],
        ocr_dpi: int,
    ) -> dict[int, PageImageInfo]:
        source = Path(uploaded_file.original_path)
        target_dir = self.root / "cases" / str(uploaded_file.case_id) / "pages" / str(uploaded_file.id)
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        if source.suffix.lower() == ".pdf":
            return self._render_pdf(source, target_dir, parsed_pages, ocr_dpi)
        if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
            return {1: self._copy_image(source, target_dir / "page-0001.png", 1)}
        return {}

    def ensure(self, uploaded_file: UploadedFile, page_number: int, ocr_dpi: int) -> PageImageInfo | None:
        source = Path(uploaded_file.original_path)
        target_dir = self.root / "cases" / str(uploaded_file.case_id) / "pages" / str(uploaded_file.id)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"page-{page_number:04d}.png"
        if target_path.exists():
            return self._info_for_path(target_path, page_number)

        if source.suffix.lower() == ".pdf":
            return self._render_pdf_page(source, target_path, page_number, ocr_dpi)
        if page_number == 1 and source.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
            return self._copy_image(source, target_path, 1)
        return None

    def resolve(self, relative_path: str) -> Path:
        requested = Path(relative_path)
        if requested.is_absolute():
            raise ValueError("页面图路径必须是相对路径")
        candidate = (self.root / requested).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("页面图路径超出存储目录") from exc
        return candidate

    def _render_pdf(
        self,
        source: Path,
        target_dir: Path,
        parsed_pages: list[ParsedPage],
        ocr_dpi: int,
    ) -> dict[int, PageImageInfo]:
        import fitz

        result: dict[int, PageImageInfo] = {}
        page_by_number = {page.page_number: page for page in parsed_pages}
        with fitz.open(source) as document:
            for page_number, page in enumerate(document, start=1):
                parsed_page = page_by_number.get(page_number)
                has_ocr = bool(parsed_page and any(block.source == "ocr" for block in parsed_page.blocks))
                dpi = ocr_dpi if has_ocr else 72
                target_path = target_dir / f"page-{page_number:04d}.png"
                matrix = fitz.Matrix(dpi / 72, dpi / 72)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                pixmap.save(target_path)
                result[page_number] = self._info_for_path(target_path, page_number)
        return result

    def _render_pdf_page(
        self,
        source: Path,
        target_path: Path,
        page_number: int,
        dpi: int,
    ) -> PageImageInfo | None:
        import fitz

        with fitz.open(source) as document:
            if page_number < 1 or page_number > len(document):
                return None
            page = document[page_number - 1]
            pixmap = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
            pixmap.save(target_path)
        return self._info_for_path(target_path, page_number)

    def _copy_image(self, source: Path, target_path: Path, page_number: int) -> PageImageInfo:
        with Image.open(source) as image:
            image.convert("RGB").save(target_path, format="PNG")
        return self._info_for_path(target_path, page_number)

    def _info_for_path(self, path: Path, page_number: int) -> PageImageInfo:
        with Image.open(path) as image:
            width, height = image.size
        relative_path = path.resolve().relative_to(self.root).as_posix()
        return PageImageInfo(page_number, relative_path, width, height)
