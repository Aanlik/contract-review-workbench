from pathlib import Path

from app.services.document_parser import DocumentParser, ParsedBlock, ParsedPage


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
