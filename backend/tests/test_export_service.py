from app.models.review import ExportRecord, Issue, ReviewCase
from app.services.export_service import ExportService


def test_export_markdown_includes_disclaimer(db_session, tmp_path):
    review_case = ReviewCase(title="导出测试合同")
    db_session.add(review_case)
    db_session.commit()
    db_session.refresh(review_case)

    service = ExportService(db_session, output_root=tmp_path)
    path = service.export_markdown(case_id=review_case.id, include_ai_summary=False)
    text = path.read_text(encoding="utf-8")
    assert "合同审核报告" in text
    assert "仅供参考" in text


def test_export_markdown_filters_high_and_medium_scope(db_session, tmp_path):
    review_case = ReviewCase(title="导出范围合同")
    db_session.add(review_case)
    db_session.flush()
    db_session.add_all(
        [
            Issue(
                case_id=review_case.id,
                issue_type="contract_risk",
                source="ai",
                risk_level="high",
                title="高风险问题",
                description="高风险说明",
                status="pending",
            ),
            Issue(
                case_id=review_case.id,
                issue_type="contract_risk",
                source="ai",
                risk_level="low",
                title="低风险问题",
                description="低风险说明",
                status="pending",
            ),
        ]
    )
    db_session.commit()

    service = ExportService(db_session, output_root=tmp_path)
    path = service.export_markdown(
        case_id=review_case.id,
        include_ai_summary=False,
        scope="high_and_medium",
    )
    text = path.read_text(encoding="utf-8")

    assert "高风险问题" in text
    assert "低风险问题" not in text
    assert db_session.query(ExportRecord).one().export_scope == "high_and_medium"


def test_export_printable_pdf_fallback_includes_disclaimer(db_session, tmp_path):
    review_case = ReviewCase(title="PDF 导出合同")
    db_session.add(review_case)
    db_session.commit()

    service = ExportService(db_session, output_root=tmp_path)
    path = service.export_report(
        case_id=review_case.id,
        export_format="pdf",
        include_ai_summary=False,
        scope="final",
    )

    assert path.suffix == ".html"
    text = path.read_text(encoding="utf-8")
    assert "PDF 导出合同" in text
    assert "仅供参考" in text
