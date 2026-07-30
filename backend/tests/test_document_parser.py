import sys
from pathlib import Path
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
        "rapidocr",
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


def test_rapidocr_provider_supports_new_output_object(tmp_path, monkeypatch):
    sample = tmp_path / "contract.png"
    sample.write_bytes(b"fake image")

    class FakeOutput:
        boxes = [[[10, 20], [100, 20], [100, 40], [10, 40]]]
        txts = ["甲方盖章"]
        scores = [0.93]

    class FakeRapidOCR:
        def __call__(self, image_path):
            return FakeOutput()

    monkeypatch.setitem(
        sys.modules,
        "rapidocr",
        SimpleNamespace(RapidOCR=lambda: FakeRapidOCR()),
    )

    blocks = RapidOcrProvider().recognize_page(sample)

    assert blocks[0].text == "甲方盖章"
    assert blocks[0].bbox == [10.0, 20.0, 100.0, 40.0]
    assert blocks[0].confidence == 0.93


def test_scanned_contract_pdf_is_rendered_to_page_images_before_ocr(tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"image")
    pdf_path.write_bytes(b"%PDF fake")
    seen_paths: list[Path] = []

    class FakeRenderer:
        def render(self, file_path: Path, output_dir: Path, dpi: int):
            assert file_path == pdf_path
            assert dpi == 260
            return [image_path]

    class RecordingOcrProvider:
        def recognize_page(self, path: Path) -> list[ParsedBlock]:
            seen_paths.append(path)
            return [
                ParsedBlock(
                    text="合同签订日期：2026年7月18日",
                    bbox=[1, 2, 30, 12],
                    confidence=0.96,
                    source="ocr",
                    order_index=0,
                )
            ]

    parser = DocumentParser(
        ocr_provider=RecordingOcrProvider(),
        pdf_renderer=FakeRenderer(),
        ocr_dpi=260,
        preprocess_images=False,
    )
    pages = parser.extract_text(pdf_path, file_type="contract")

    assert seen_paths == [image_path]
    assert pages == [
        ParsedPage(
            page_number=1,
            blocks=[
                ParsedBlock(
                    text="合同签订日期：2026年7月18日",
                    bbox=[1, 2, 30, 12],
                    confidence=0.96,
                    source="ocr",
                    order_index=0,
                )
            ],
        )
    ]
