from argparse import ArgumentParser
from pathlib import Path
import time

from app.services.document_parser import DocumentParser, PaddleOcrProvider, RapidOcrProvider


def main() -> int:
    parser = ArgumentParser(description="Run OCR smoke test against a real scanned contract PDF/image.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--engine", choices=["rapid", "paddle"], default="rapid")
    parser.add_argument("--dpi", type=int, default=260)
    parser.add_argument("--no-preprocess", action="store_true")
    args = parser.parse_args()

    provider = RapidOcrProvider() if args.engine == "rapid" else PaddleOcrProvider()
    document_parser = DocumentParser(
        ocr_provider=provider,
        ocr_dpi=args.dpi,
        preprocess_images=not args.no_preprocess,
    )
    started = time.perf_counter()
    pages = document_parser.extract_text(args.file, file_type="contract")
    elapsed = time.perf_counter() - started
    blocks = [block for page in pages for block in page.blocks]
    confidences = [block.confidence for block in blocks if block.confidence is not None]
    average_confidence = sum(confidences) / len(confidences) if confidences else 0

    print(f"file={args.file}")
    print(f"engine={args.engine} dpi={args.dpi} preprocess={not args.no_preprocess}")
    print(f"pages={len(pages)} blocks={len(blocks)} avg_confidence={average_confidence:.3f} elapsed={elapsed:.2f}s")
    print("preview:")
    print("\n".join(block.text for block in blocks[:20]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
