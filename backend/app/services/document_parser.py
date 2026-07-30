from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

@dataclass(frozen=True)
class ParsedBlock:
    text: str
    bbox: list[float] | None
    confidence: float | None
    source: Literal["pdf_text", "ocr"]
    order_index: int


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    blocks: list[ParsedBlock]


class OcrProvider(Protocol):
    def recognize_page(self, image_path: Path) -> list[ParsedBlock]:
        pass


class PaddleOcrProvider:
    def recognize_page(self, image_path: Path) -> list[ParsedBlock]:
        raise RuntimeError(
            "PaddleOCR is not installed. Install the OCR extra before parsing scanned contracts."
        )


class DocumentParser:
    def __init__(self, ocr_provider: OcrProvider | None = None) -> None:
        self.ocr_provider = ocr_provider or PaddleOcrProvider()

    def extract_text(self, file_path: Path, file_type: str) -> list[ParsedPage]:
        if file_path.suffix.lower() in {".txt", ".md"}:
            text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
            if not text:
                return []
            return [
                ParsedPage(
                    page_number=1,
                    blocks=[
                        ParsedBlock(
                            text=text,
                            bbox=None,
                            confidence=None,
                            source="pdf_text",
                            order_index=0,
                        )
                    ],
                )
            ]

        if file_type == "contract":
            return self._extract_with_ocr(file_path)

        if file_path.suffix.lower() == ".pdf":
            pdf_pages = self._extract_pdf_text(file_path)
            if self._has_usable_text(pdf_pages):
                return pdf_pages

        return self._extract_with_ocr(file_path)

    def _extract_with_ocr(self, file_path: Path) -> list[ParsedPage]:
        blocks = self.ocr_provider.recognize_page(file_path)
        return [ParsedPage(page_number=1, blocks=blocks)]

    def _extract_pdf_text(self, file_path: Path) -> list[ParsedPage]:
        import fitz

        pages: list[ParsedPage] = []
        with fitz.open(file_path) as document:
            for page_index, page in enumerate(document, start=1):
                blocks: list[ParsedBlock] = []
                for order_index, block in enumerate(page.get_text("blocks")):
                    x0, y0, x1, y1, text, *_ = block
                    normalized = " ".join(str(text).split())
                    if normalized:
                        blocks.append(
                            ParsedBlock(
                                text=normalized,
                                bbox=[float(x0), float(y0), float(x1), float(y1)],
                                confidence=None,
                                source="pdf_text",
                                order_index=order_index,
                            )
                        )
                pages.append(ParsedPage(page_number=page_index, blocks=blocks))
        return pages

    def _has_usable_text(self, pages: list[ParsedPage]) -> bool:
        text = "\n".join(block.text for page in pages for block in page.blocks)
        return len(text.strip()) >= 10
