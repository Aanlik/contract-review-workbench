from app.models.review import ReviewCase
from app.services.export_service import ExportService


def test_export_markdown_includes_disclaimer(db_session, tmp_path):
    review_case = ReviewCase(title="导出测试合同")
    db_session.add(review_case)
    db_session.commit()
    db_session.refresh(review_case)

    service = ExportService(db_session, output_root=tmp_path)
    path = service.export_markdown(case_id=review_case.id, include_ai_summary=False)
    text = path.read_text(encoding="utf-8")
    assert "AI 辅助审查" in text
    assert "不替代律师最终法律意见" in text
