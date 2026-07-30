from fastapi.testclient import TestClient

from app.core.database import get_session
from app.main import create_app
from app.models.review import ReviewCase, UploadedFile


def make_client(db_session):
    app = create_app()

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


def test_reanalyze_creates_new_version_and_seed_issues(db_session, tmp_path):
    review_case = ReviewCase(title="流程审计合同")
    db_session.add(review_case)
    db_session.commit()
    db_session.refresh(review_case)
    contract = tmp_path / "contract.txt"
    contract.write_text("合同签订日期：2026年7月18日\n甲方盖章：有\n乙方盖章：缺失", encoding="utf-8")
    sign_report = tmp_path / "sign.txt"
    sign_report.write_text("法务审核：2026年7月20日 同意\n审批通过：2026年7月19日", encoding="utf-8")
    db_session.add_all(
        [
            UploadedFile(
                case_id=review_case.id,
                file_type="contract",
                file_name="contract.txt",
                original_path=str(contract),
                parse_status="uploaded",
            ),
            UploadedFile(
                case_id=review_case.id,
                file_type="sign_report",
                file_name="sign.txt",
                original_path=str(sign_report),
                parse_status="uploaded",
            ),
        ]
    )
    db_session.commit()

    client = make_client(db_session)
    response = client.post(f"/api/cases/{review_case.id}/reanalyze", json={"instruction": "重点看流程"})
    assert response.status_code == 201
    body = response.json()
    assert body["current_version"] == 2
    assert body["issue_count"] >= 2

    issues = client.get(f"/api/cases/{review_case.id}/issues").json()
    titles = {issue["title"] for issue in issues}
    assert "法审日期晚于合同签订日期" in titles
    assert "合同签订日期早于审批通过日期" in titles
