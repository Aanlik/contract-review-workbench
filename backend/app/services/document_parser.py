import hashlib
import json
import os
import shutil
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
    def __init__(self) -> None:
        self._engine = None

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

        engine = self._engine or PaddleOCR(use_angle_cls=True, lang="ch")
        self._engine = engine
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
        engine = self._engine
        if engine is None:
            engine = paddle_ocr(
                lang="ch",
                use_textline_orientation=True,
                device="cpu",
                engine_config={"run_mode": "paddle"},
            )
            self._engine = engine
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
    """Use a verified writable copy of models shipped with a frozen application."""
    if not getattr(sys, "frozen", False):
        return
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    bundled_model_dir = base_dir / "ocr-models"
    if bundled_model_dir.is_dir():
        runtime_model_dir = _paddle_runtime_model_dir()
        prepare_paddle_model_cache(bundled_model_dir, runtime_model_dir)
        os.environ["PADDLE_PDX_CACHE_HOME"] = str(runtime_model_dir)


def _paddle_runtime_model_dir() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "ContractReviewWorkbench" / "ocr-models"


def prepare_paddle_model_cache(bundled_model_dir: Path, runtime_model_dir: Path) -> None:
    """Validate model files and atomically restore a damaged runtime cache."""
    manifest = _read_model_manifest(bundled_model_dir)
    if not _model_cache_is_valid(bundled_model_dir, manifest):
        raise RuntimeError("内置 PaddleOCR 模型文件不完整，请重新下载完整安装包。")
    if _model_cache_is_valid(runtime_model_dir, manifest):
        return

    staging_dir = runtime_model_dir.with_name(f".{runtime_model_dir.name}-staging")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundled_model_dir, staging_dir)
    if runtime_model_dir.exists():
        shutil.rmtree(runtime_model_dir)
    staging_dir.replace(runtime_model_dir)


def _read_model_manifest(model_dir: Path) -> list[dict[str, str | int]]:
    manifest_path = model_dir / "model-manifest.json"
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = data["files"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RuntimeError("内置 PaddleOCR 模型清单无效，请重新下载完整安装包。") from exc
    if not isinstance(files, list) or not files:
        raise RuntimeError("内置 PaddleOCR 模型清单为空，请重新下载完整安装包。")
    return files


def _model_cache_is_valid(model_dir: Path, manifest: list[dict[str, str | int]]) -> bool:
    for entry in manifest:
        relative_path = entry.get("path")
        expected_size = entry.get("size")
        expected_hash = entry.get("sha256")
        if not (
            isinstance(relative_path, str)
            and isinstance(expected_size, int)
            and isinstance(expected_hash, str)
        ):
            return False
        candidate = model_dir / relative_path
        if not candidate.is_file() or candidate.stat().st_size != expected_size:
            return False
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if digest != expected_hash:
            return False
    return True


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
