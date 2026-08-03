from pathlib import Path

from PIL import Image

from app.models.review import ReviewCase, UploadedFile
from app.services.document_parser import ParsedBlock, ParsedPage
from app.services.page_image_service import PageImageService


def test_persist_image_material_as_original_page_png(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.page_image_service.settings.storage_root", tmp_path / "storage")
    source = tmp_path / "source.jpg"
    Image.new("RGB", (320, 180), "white").save(source)

    case = ReviewCase(title="页面图测试")
    db_session.add(case)
    db_session.flush()
    uploaded = UploadedFile(
        case_id=case.id,
        file_type="contract",
        file_name=source.name,
        original_path=str(source),
        parse_method="ocr",
        parse_status="parsed",
    )
    db_session.add(uploaded)
    db_session.flush()

    pages = [
        ParsedPage(
            page_number=1,
            blocks=[
                ParsedBlock(
                    text="合同标题",
                    bbox=[10, 20, 120, 40],
                    confidence=0.98,
                    source="ocr",
                    order_index=0,
                )
            ],
        )
    ]

    result = PageImageService().persist(uploaded, pages, ocr_dpi=260)

    info = result[1]
    assert info.relative_path == f"cases/{case.id}/pages/{uploaded.id}/page-0001.png"
    assert info.width == 320
    assert info.height == 180
    image_path = Path(tmp_path / "storage" / info.relative_path)
    assert image_path.exists()
    with Image.open(image_path) as image:
        assert image.size == (320, 180)


def test_resolve_rejects_paths_outside_storage_root(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.page_image_service.settings.storage_root", tmp_path / "storage")

    try:
        PageImageService().resolve("../../outside.png")
    except ValueError as exc:
        assert "存储目录" in str(exc)
    else:
        raise AssertionError("path traversal must be rejected")
