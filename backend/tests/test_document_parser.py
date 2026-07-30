from pathlib import Path
import sys
from types import SimpleNamespace

from app.services.document_parser import DocumentParser, ParsedBlock, ParsedPage, RapidOcrProvider


class FakeOcrProvider:
    def recognize_page(self, image_path: Path) -> list[ParsedBlock]:
        return [
            ParsedBlock(
                text="甲方盖章",
                bbox=[10, 20, 100, 40],
                confidence=0.93,
                source="ocr",
                order_index=0,
            )
        ]


def test_contract_files_use_ocr_provider(tmp_path):
    sample = tmp_path / "contract.png"
    sample.write_bytes(b"fake image")
    parser = DocumentParser(ocr_provider=FakeOcrProvider())
    pages = parser.extract_text(sample, file_type="contract")
    assert pages == [
        ParsedPage(
            page_number=1,
            blocks=[
                ParsedBlock(
                    text="甲方盖章",
                    bbox=[10, 20, 100, 40],
                    confidence=0.93,
                    source="ocr",
                    order_index=0,
                )
            ],
        )
    ]


def test_rapidocr_provider_normalizes_runtime_results(tmp_path, monkeypatch):
    sample = tmp_path / "contract.png"
    sample.write_bytes(b"fake image")

    class FakeRapidOCR:
        def __call__(self, image_path):
            assert image_path == str(sample)
            return [
                ([[10, 20], [100, 20], [100, 40], [10, 40]], "甲方盖章", 0.93),
            ], None

    monkeypatch.setitem(
        sys.modules,
        "rapidocr_onnxruntime",
        SimpleNamespace(RapidOCR=lambda: FakeRapidOCR()),
    )

    blocks = RapidOcrProvider().recognize_page(sample)

    assert blocks == [
        ParsedBlock(
            text="甲方盖章",
            bbox=[10.0, 20.0, 100.0, 40.0],
            confidence=0.93,
            source="ocr",
            order_index=0,
        )
    ]
