from app.models.review import ReviewCase, UploadedFile
from app.services.file_ingest_service import FileIngestService


def test_ingest_text_file_creates_document_page_and_ocr_block(db_session, tmp_path):
    review_case = ReviewCase(title="材料解析测试")
    db_session.add(review_case)
    db_session.commit()
    db_session.refresh(review_case)
    material = tmp_path / "sign.txt"
    material.write_text("法务审核：2026年7月20日 同意", encoding="utf-8")
    uploaded = UploadedFile(
        case_id=review_case.id,
        file_type="sign_report",
        file_name="sign.txt",
        original_path=str(material),
        parse_status="uploaded",
    )
    db_session.add(uploaded)
    db_session.commit()
    db_session.refresh(uploaded)

    FileIngestService(db_session).ingest(uploaded.id)
    db_session.refresh(uploaded)

    assert uploaded.parse_status == "parsed"
    assert uploaded.parse_method == "text"
    assert uploaded.page_count == 1
    assert uploaded.pages[0].ocr_blocks[0].text == "法务审核：2026年7月20日 同意"
    assert uploaded.pages[0].ocr_blocks[0].source == "pdf_text"


def test_ingest_scanned_contract_marks_file_as_needing_ocr(db_session, tmp_path):
    review_case = ReviewCase(title="扫描件解析测试")
    db_session.add(review_case)
    db_session.commit()
    db_session.refresh(review_case)
    image = tmp_path / "contract.png"
    image.write_bytes(b"image bytes")
    uploaded = UploadedFile(
        case_id=review_case.id,
        file_type="contract",
        file_name="contract.png",
        original_path=str(image),
        parse_status="uploaded",
    )
    db_session.add(uploaded)
    db_session.commit()
    db_session.refresh(uploaded)

    FileIngestService(db_session).ingest(uploaded.id)
    db_session.refresh(uploaded)

    assert uploaded.parse_status == "needs_ocr"
    assert uploaded.parse_method == "ocr"
