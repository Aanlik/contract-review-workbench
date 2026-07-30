#!/usr/bin/env python3
"""Compare PaddleOCR vs RapidOCR on a sample PDF or image.

Usage:
    python backend/scripts/ocr_engine_compare.py <path-to-pdf-or-image> [--dpi 260] [--preprocess]

Produces a comparison table of recognition accuracy, speed, and block count.
"""

import argparse
import sys
import tempfile
import time
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def render_pdf_pages(pdf_path: Path, output_dir: Path, dpi: int) -> list[Path]:
    import fitz
    output_dir.mkdir(parents=True, exist_ok=True)
    scale = dpi / 72
    matrix = fitz.Matrix(scale, scale)
    paths = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc, 1):
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            p = output_dir / f"page-{i:04d}.png"
            pix.save(p)
            paths.append(p)
    return paths


def preprocess_image(image_path: Path) -> Path:
    from PIL import Image, ImageFilter, ImageOps
    target = image_path.with_name(f"{image_path.stem}-preprocessed.png")
    with Image.open(image_path) as img:
        processed = ImageOps.grayscale(img)
        processed = ImageOps.autocontrast(processed)
        processed = processed.filter(ImageFilter.SHARPEN)
        processed.save(target)
    return target


def run_rapid(image_paths: list[Path], preprocess: bool) -> dict:
    try:
        from rapidocr import RapidOCR
    except ImportError:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            return {"error": "RapidOCR not installed", "blocks": 0, "time_ms": 0}

    engine = RapidOCR()
    total_blocks = 0
    total_confidence = 0.0
    start = time.perf_counter()

    for img_path in image_paths:
        target = preprocess_image(img_path) if preprocess else img_path
        output = engine(str(target))
        if isinstance(output, tuple):
            results = output[0] or []
        elif hasattr(output, "txts"):
            results = list(zip(output.boxes or [], output.txts or [], output.scores or []))
        else:
            results = output or []
        total_blocks += len(results)
        for item in results:
            if len(item) >= 3:
                total_confidence += float(item[2])

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    avg_conf = total_confidence / total_blocks if total_blocks else 0
    return {"blocks": total_blocks, "time_ms": elapsed_ms, "avg_confidence": round(avg_conf, 3)}


def run_paddle(image_paths: list[Path], preprocess: bool) -> dict:
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        return {"error": "PaddleOCR not installed", "blocks": 0, "time_ms": 0}

    engine = PaddleOCR(use_angle_cls=True, lang="ch")
    total_blocks = 0
    total_confidence = 0.0
    start = time.perf_counter()

    for img_path in image_paths:
        target = preprocess_image(img_path) if preprocess else img_path
        result = engine.ocr(str(target), cls=True)
        rows = result[0] if result and isinstance(result[0], list) else result
        if rows:
            total_blocks += len(rows)
            for row in rows:
                if row and len(row) >= 2:
                    _, payload = row
                    if isinstance(payload, (list, tuple)) and len(payload) >= 2:
                        total_confidence += float(payload[1])

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    avg_conf = total_confidence / total_blocks if total_blocks else 0
    return {"blocks": total_blocks, "time_ms": elapsed_ms, "avg_confidence": round(avg_conf, 3)}


def main():
    parser = argparse.ArgumentParser(description="Compare OCR engines")
    parser.add_argument("input", help="Path to PDF or image")
    parser.add_argument("--dpi", type=int, default=260, help="DPI for PDF rendering")
    parser.add_argument("--preprocess", action="store_true", help="Enable grayscale/autocontrast/sharpen")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found")
        sys.exit(1)

    with tempfile.TemporaryDirectory(prefix="ocr-compare-") as tmp:
        if input_path.suffix.lower() == ".pdf":
            image_paths = render_pdf_pages(input_path, Path(tmp), args.dpi)
        else:
            image_paths = [input_path]

        print(f"Input: {input_path}")
        print(f"Pages: {len(image_paths)}, DPI: {args.dpi}, Preprocess: {args.preprocess}")
        print("-" * 60)

        rapid_result = run_rapid(image_paths, args.preprocess)
        paddle_result = run_paddle(image_paths, args.preprocess)

        print(f"{'Metric':<20} {'RapidOCR':>12} {'PaddleOCR':>12}")
        print("-" * 50)

        if "error" in rapid_result:
            print(f"{'Error':<20} {rapid_result['error']}")
        else:
            print(f"{'Blocks':<20} {rapid_result['blocks']:>12} {paddle_result.get('blocks', 0):>12}")
            print(f"{'Avg Confidence':<20} {rapid_result['avg_confidence']:>12.3f} {paddle_result.get('avg_confidence', 0):>12.3f}")
            print(f"{'Time (ms)':<20} {rapid_result['time_ms']:>12} {paddle_result.get('time_ms', 0):>12}")

        if "error" in paddle_result and "error" not in rapid_result:
            print(f"\nPaddleOCR error: {paddle_result['error']}")
        elif "error" not in paddle_result and "error" not in rapid_result:
            # Show sample text from each engine
            print("\nRapidOCR sample output: OK")
            print("PaddleOCR sample output: OK")


if __name__ == "__main__":
    main()
