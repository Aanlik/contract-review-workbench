from fastapi.testclient import TestClient

from app.core.database import get_session
from app.main import create_app
from app.models.review import AppSetting, DocumentPage, OcrBlock, ReviewCase, UploadedFile


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

    versions = client.get(f"/api/cases/{review_case.id}/versions").json()
    assert versions[0]["version_number"] == 2
    assert versions[0]["trigger"] == "reanalyze"
    assert versions[0]["review_request"] == "重点看流程"


def test_reanalyze_uses_configured_ai_to_create_contract_risk(db_session, tmp_path, monkeypatch):
    review_case = ReviewCase(title="AI 合同审查")
    db_session.add(review_case)
    db_session.commit()
    db_session.refresh(review_case)
    contract = tmp_path / "contract.txt"
    contract.write_text("甲方不得以任何理由解除本合同。", encoding="utf-8")
    db_session.add(
        UploadedFile(
            case_id=review_case.id,
            file_type="contract",
            file_name="contract.txt",
            original_path=str(contract),
            parse_status="uploaded",
        )
    )
    db_session.add(
        AppSetting(
            key="ai",
            value={
                "base_url": "https://api.example.com/v1",
                "api_key": "sk-test",
                "model": "law-model",
                "temperature": 0.1,
                "timeout_seconds": 45,
            },
        )
    )
    db_session.commit()

    class FakeProvider:
        def __init__(self, settings):
            self.settings = settings

        def chat(self, messages):
            return """
            {
              "issues": [
                {
                  "title": "解除权限制过严",
                  "risk_level": "high",
                  "description": "该条款排除甲方法定解除权，显著不利。",
                  "original_text": "甲方不得以任何理由解除本合同。",
                  "suggestion": "补充重大违约、履约不能、不可抗力等解除情形。",
                  "replacement_clause": "甲方可在乙方重大违约时解除合同。",
                  "review_note": "需结合交易背景复核",
                  "requires_human_review": true
                }
              ]
            }
            """

    monkeypatch.setattr("app.services.review_run_service.OpenAICompatibleProvider", FakeProvider)

    client = make_client(db_session)
    response = client.post(f"/api/cases/{review_case.id}/reanalyze", json={"instruction": "法律风险"})
    assert response.status_code == 201
    issues = client.get(f"/api/cases/{review_case.id}/issues").json()
    assert any(issue["title"] == "解除权限制过严" for issue in issues)


def test_reanalyze_flags_scanned_contract_when_text_is_unavailable(db_session, tmp_path):
    review_case = ReviewCase(title="扫描件合同")
    db_session.add(review_case)
    db_session.commit()
    db_session.refresh(review_case)
    image = tmp_path / "contract.png"
    image.write_bytes(b"not real image text")
    db_session.add(
        UploadedFile(
            case_id=review_case.id,
            file_type="contract",
            file_name="contract.png",
            original_path=str(image),
            parse_status="uploaded",
        )
    )
    db_session.commit()

    client = make_client(db_session)
    response = client.post(f"/api/cases/{review_case.id}/reanalyze", json={"instruction": "首次审核"})
    assert response.status_code == 201
    issues = client.get(f"/api/cases/{review_case.id}/issues").json()
    assert any(issue["title"] == "合同扫描件 OCR 未完成" for issue in issues)


def test_reanalyze_flags_missing_legal_review_and_final_approval(db_session, tmp_path):
    review_case = ReviewCase(title="缺少签批合同")
    db_session.add(review_case)
    db_session.commit()
    db_session.refresh(review_case)
    contract = tmp_path / "contract.txt"
    contract.write_text("合同签订日期：2026年7月18日\n甲方盖章：有\n乙方盖章：有", encoding="utf-8")
    sign_report = tmp_path / "sign.txt"
    sign_report.write_text("经办人提交：2026年7月17日\n未见法审或审批通过节点", encoding="utf-8")
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
    response = client.post(f"/api/cases/{review_case.id}/reanalyze", json={"instruction": "流程审计"})
    assert response.status_code == 201
    issues = client.get(f"/api/cases/{review_case.id}/issues").json()
    titles = {issue["title"] for issue in issues}
    assert "未识别到法务审核记录" in titles
    assert "未识别到最终审批通过记录" in titles


def test_reanalyze_uses_persisted_ocr_blocks_when_source_file_is_missing(db_session, tmp_path):
    review_case = ReviewCase(title="OCR 入库审核")
    db_session.add(review_case)
    db_session.commit()
    db_session.refresh(review_case)
    missing_contract = tmp_path / "missing-contract.txt"
    missing_flow = tmp_path / "missing-flow.txt"
    contract_file = UploadedFile(
        case_id=review_case.id,
        file_type="contract",
        file_name="contract.txt",
        original_path=str(missing_contract),
        parse_status="parsed",
    )
    flow_file = UploadedFile(
        case_id=review_case.id,
        file_type="sign_report",
        file_name="sign.txt",
        original_path=str(missing_flow),
        parse_status="parsed",
    )
    db_session.add_all([contract_file, flow_file])
    db_session.flush()
    contract_page = DocumentPage(file_id=contract_file.id, page_number=1, ocr_status="completed")
    flow_page = DocumentPage(file_id=flow_file.id, page_number=1, ocr_status="completed")
    db_session.add_all([contract_page, flow_page])
    db_session.flush()
    db_session.add_all(
        [
            OcrBlock(
                page_id=contract_page.id,
                text="合同签订日期：2026年7月18日",
                source="pdf_text",
                order_index=0,
            ),
            OcrBlock(
                page_id=flow_page.id,
                text="法务审核：2026年7月20日 同意",
                source="pdf_text",
                order_index=0,
            ),
        ]
    )
    db_session.commit()

    client = make_client(db_session)
    response = client.post(f"/api/cases/{review_case.id}/reanalyze", json={"instruction": "看日期"})
    assert response.status_code == 201
    issues = client.get(f"/api/cases/{review_case.id}/issues").json()
    issue = next(issue for issue in issues if issue["title"] == "法审日期晚于合同签订日期")
    assert {ref["file_id"] for ref in issue["evidence_refs"]} == {contract_file.id, flow_file.id}
    assert {ref["page_number"] for ref in issue["evidence_refs"]} == {1}
    assert {ref["ocr_block_id"] for ref in issue["evidence_refs"]} == {
        contract_page.ocr_blocks[0].id,
        flow_page.ocr_blocks[0].id,
    }
