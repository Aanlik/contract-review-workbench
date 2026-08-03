import os
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from PIL import Image, ImageFilter, ImageOps


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


class PdfRenderer(Protocol):
    def render(self, file_path: Path, output_dir: Path, dpi: int) -> list[Path]:
        pass


class PaddleOcrProvider:
    def recognize_page(self, image_path: Path) -> list[ParsedBlock]:
        _configure_bundled_paddle_models()
        try:
            from paddleocr import PaddleOCR
        except Exception as exc:
            raise RuntimeError(
                "PaddleOCR is not installed. Install the OCR extra before parsing scanned contracts."
            ) from exc

        if hasattr(PaddleOCR, "predict"):
            return self._recognize_with_v3(PaddleOCR, image_path)

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

    def _recognize_with_v3(self, paddle_ocr, image_path: Path) -> list[ParsedBlock]:
        engine = paddle_ocr(lang="ch", use_textline_orientation=True)
        results = engine.predict(str(image_path))
        if isinstance(results, dict) or hasattr(results, "to_dict"):
            results = [results]

        blocks: list[ParsedBlock] = []
        for result in results:
            data = result.to_dict() if hasattr(result, "to_dict") else result
            polygons = data.get("dt_polys") or []
            texts = data.get("rec_texts") or []
            scores = data.get("rec_scores") or []
            for polygon, text, score in zip(polygons, texts, scores, strict=False):
                blocks.append(
                    ParsedBlock(
                        text=str(text),
                        bbox=normalize_ocr_bbox(polygon),
                        confidence=float(score),
                        source="ocr",
                        order_index=len(blocks),
                    )
                )
        return blocks


def _configure_bundled_paddle_models() -> None:
    """Point PaddleX at models shipped inside a frozen application."""
    if not getattr(sys, "frozen", False):
        return
    base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    model_dir = base_dir / "ocr-models"
    if model_dir.is_dir():
        os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(model_dir))


class RapidOcrProvider:
    def recognize_page(self, image_path: Path) -> list[ParsedBlock]:
        try:
            from rapidocr import RapidOCR
        except Exception:
            try:
                from rapidocr_onnxruntime import RapidOCR
            except Exception as legacy_exc:
                raise RuntimeError(
                    "RapidOCR is not installed. Install rapidocr before selecting RapidOCR."
                ) from legacy_exc
        engine = RapidOCR()
        output = engine(str(image_path))
        result = self._normalize_rapidocr_output(output)
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

    def _normalize_rapidocr_output(self, output):
        if isinstance(output, tuple):
            return output[0]
        if all(hasattr(output, attr) for attr in ("boxes", "txts", "scores")):
            boxes = [] if output.boxes is None else list(output.boxes)
            txts = [] if output.txts is None else list(output.txts)
            scores = [] if output.scores is None else list(output.scores)
            return list(zip(boxes, txts, scores, strict=False))
        if hasattr(output, "to_dict"):
            data = output.to_dict()
            return list(
                zip(
                    data.get("boxes") or [],
                    data.get("txts") or [],
                    data.get("scores") or [],
                    strict=False,
                )
            )
        return output


class PdfPageRenderer:
    def render(self, file_path: Path, output_dir: Path, dpi: int) -> list[Path]:
        import fitz

        output_dir.mkdir(parents=True, exist_ok=True)
        scale = dpi / 72
        matrix = fitz.Matrix(scale, scale)
        paths: list[Path] = []
        with fitz.open(file_path) as document:
            for page_index, page in enumerate(document, start=1):
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image_path = output_dir / f"page-{page_index:04d}.png"
                pixmap.save(image_path)
                paths.append(image_path)
        return paths


class ImagePreprocessor:
    def preprocess(self, image_path: Path) -> Path:
        target_path = image_path.with_name(f"{image_path.stem}-preprocessed{image_path.suffix}")
        try:
            with Image.open(image_path) as image:
                processed = ImageOps.grayscale(image)
                processed = ImageOps.autocontrast(processed)
                processed = processed.filter(ImageFilter.SHARPEN)
                processed.save(target_path)
            return target_path
        except Exception:
            return image_path


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
    def __init__(
        self,
        ocr_provider: OcrProvider | None = None,
        pdf_renderer: PdfRenderer | None = None,
        preprocessor: ImagePreprocessor | None = None,
        ocr_dpi: int = 260,
        preprocess_images: bool = True,
    ) -> None:
        self.ocr_provider = ocr_provider or PaddleOcrProvider()
        self.pdf_renderer = pdf_renderer or PdfPageRenderer()
        self.preprocessor = preprocessor or ImagePreprocessor()
        self.ocr_dpi = ocr_dpi
        self.preprocess_images = preprocess_images

    def extract_text(
        self,
        file_path: Path,
        file_type: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[ParsedPage]:
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
            return self._extract_with_ocr(file_path, progress_callback)

        if file_path.suffix.lower() == ".pdf":
            pdf_pages = self._extract_pdf_text(file_path)
            if self._has_usable_text(pdf_pages):
                return pdf_pages

        return self._extract_with_ocr(file_path, progress_callback)

    def _extract_with_ocr(
        self,
        file_path: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[ParsedPage]:
        if file_path.suffix.lower() == ".pdf":
            with tempfile.TemporaryDirectory(prefix="contract-ocr-pages-") as temp_dir:
                try:
                    image_paths = self.pdf_renderer.render(file_path, Path(temp_dir), self.ocr_dpi)
                except Exception as exc:
                    raise RuntimeError(f"OCR PDF rendering failed: {exc}") from exc
                pages: list[ParsedPage] = []
                total_pages = len(image_paths)
                for page_number, image_path in enumerate(image_paths, start=1):
                    ocr_path = self.preprocessor.preprocess(image_path) if self.preprocess_images else image_path
                    pages.append(
                        ParsedPage(
                            page_number=page_number,
                            blocks=self.ocr_provider.recognize_page(ocr_path),
                        )
                    )
                    if progress_callback:
                        progress_callback(page_number, total_pages)
                return pages
        ocr_path = self.preprocessor.preprocess(file_path) if self.preprocess_images else file_path
        blocks = self.ocr_provider.recognize_page(ocr_path)
        if progress_callback:
            progress_callback(1, 1)
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
