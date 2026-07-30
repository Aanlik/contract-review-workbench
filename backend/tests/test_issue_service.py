from app.models.review import ReviewCase
from app.services.issue_service import IssueService, ManualIssueCreate


def test_manual_issue_defaults_to_manual_source(db_session):
    review_case = ReviewCase(title="人工标记测试")
    db_session.add(review_case)
    db_session.commit()
    db_session.refresh(review_case)

    service = IssueService(db_session)
    issue = service.create_manual_issue(
        case_id=review_case.id,
        payload=ManualIssueCreate(
            title="人工发现付款风险",
            risk_level="medium",
            description="付款条件不清楚",
            suggestion="补充付款触发条件",
            evidence_text="付款时间另行协商",
        ),
    )
    assert issue.source == "manual"
    assert issue.issue_type == "manual_mark"
    assert issue.status == "pending"
    assert issue.evidence_refs[0].original_text == "付款时间另行协商"
