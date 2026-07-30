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
        try:
            from paddleocr import PaddleOCR
        except Exception as exc:
            raise RuntimeError(
                "PaddleOCR is not installed. Install the OCR extra before parsing scanned contracts."
            ) from exc
        engine = PaddleOCR(use_angle_cls=True, lang="ch")
        result = engine.ocr(str(image_path), cls=True)
        rows = result[0] if result and isinstance(result[0], list) else result
        blocks: list[ParsedBlock] = []
        for order_index, row in enumerate(rows or []):
            bbox, payload = row
            text, confidence = payload
            blocks.append(
                ParsedBlock(
                    text=str(text),
                    bbox=normalize_ocr_bbox(bbox),
                    confidence=float(confidence),
                    source="ocr",
                    order_index=order_index,
                )
            )
        return blocks


class RapidOcrProvider:
    def recognize_page(self, image_path: Path) -> list[ParsedBlock]:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except Exception as exc:
            raise RuntimeError(
                "RapidOCR is not installed. Install rapidocr_onnxruntime before selecting RapidOCR."
            ) from exc
        engine = RapidOCR()
        result, _ = engine(str(image_path))
        return [
            ParsedBlock(
                text=str(text),
                bbox=normalize_ocr_bbox(bbox),
                confidence=float(confidence),
                source="ocr",
                order_index=order_index,
            )
            for order_index, (bbox, text, confidence) in enumerate(result or [])
        ]


def normalize_ocr_bbox(bbox) -> list[float] | None:
    if bbox is None:
        return None
    if len(bbox) == 4 and all(isinstance(item, (int, float)) for item in bbox):
        return [float(item) for item in bbox]
    points = [point for point in bbox if len(point) >= 2]
    if not points:
        return None
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return [min(xs), min(ys), max(xs), max(ys)]


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
