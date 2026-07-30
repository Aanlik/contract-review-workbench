"""Full integration test: covers the complete case lifecycle end-to-end."""

from fastapi.testclient import TestClient

from app.core.database import get_session
from app.main import create_app


def make_client(db_session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: (yield db_session)
    return TestClient(app)


def test_full_case_lifecycle(db_session, tmp_path):
    """End-to-end: create → upload → analyze → issues → chat → export → delete."""
    client = make_client(db_session)

    # 1. Health
    assert client.get("/api/health").json()["status"] == "ok"

    # 2. Settings
    r = client.get("/api/settings/system")
    assert r.status_code == 200
    assert "ocr_engine" in r.json()

    r = client.put("/api/settings/system", json={
        "ocr_engine": "rapidocr", "storage_root": "./data/storage",
        "ocr_dpi": 260, "preprocess_images": True,
    })
    assert r.status_code == 200
    assert r.json()["ocr_engine"] == "rapidocr"

    # 3. AI test connection
    r = client.post("/api/settings/ai/test", json={
        "base_url": "https://api.example.com", "api_key": "sk-test",
        "model": "test", "temperature": 0.1, "timeout_seconds": 5,
    })
    assert r.status_code == 200
    assert "message" in r.json()

    # 4. Create case
    r = client.post("/api/cases", json={"title": "集成测试合同", "note": "上线前测试"})
    assert r.status_code == 200
    case_id = r.json()["id"]
    assert r.json()["title"] == "集成测试合同"

    # 5. List cases
    r = client.get("/api/cases")
    assert any(c["id"] == case_id for c in r.json())

    # 6. Search cases
    r = client.get("/api/cases", params={"q": "集成"})
    assert any(c["id"] == case_id for c in r.json())
    r = client.get("/api/cases", params={"q": "不存在"})
    assert len(r.json()) == 0

    # 7. Get / update case
    r = client.get(f"/api/cases/{case_id}")
    assert r.json()["title"] == "集成测试合同"
    r = client.patch(f"/api/cases/{case_id}", json={"note": "已更新"})
    assert r.json()["note"] == "已更新"

    # 8. Upload files
    contract = tmp_path / "contract.txt"
    contract.write_text("合同签订日期：2026年8月1日\n甲方盖章：有\n乙方盖章：有", encoding="utf-8")
    r = client.post(f"/api/cases/{case_id}/files",
                    data={"file_type": "contract"}, files={"file": ("contract.txt", contract.read_bytes())})
    assert r.status_code == 201
    assert r.json()["parse_status"] in ("parsed", "uploaded")

    sign_report = tmp_path / "sign.txt"
    sign_report.write_text("法务审核：2026年7月30日 同意\n审批通过：2026年7月29日", encoding="utf-8")
    r = client.post(f"/api/cases/{case_id}/files",
                    data={"file_type": "sign_report"}, files={"file": ("sign.txt", sign_report.read_bytes())})
    assert r.status_code == 201

    # 9. List files / documents
    r = client.get(f"/api/cases/{case_id}/files")
    assert len(r.json()) == 2
    r = client.get(f"/api/cases/{case_id}/documents")
    assert len(r.json()) >= 1

    # 10. Reanalyze
    r = client.post(f"/api/cases/{case_id}/reanalyze", json={"instruction": "全面审核"})
    assert r.status_code == 201
    assert r.json()["current_version"] >= 2

    # 11. Issues
    r = client.get(f"/api/cases/{case_id}/issues")
    assert len(r.json()) >= 1
    issue_id = r.json()[0]["id"]

    # 12. Update issue
    r = client.patch(f"/api/issues/{issue_id}", json={"status": "confirmed"})
    assert r.json()["status"] == "confirmed"

    # 13. Manual issue
    r = client.post(f"/api/cases/{case_id}/issues/manual", json={
        "title": "人工标记", "risk_level": "medium",
        "description": "测试标记", "evidence_text": "证据原文",
    })
    assert r.status_code == 201
    manual_id = r.json()["id"]

    # 14. Batch update
    r = client.post("/api/issues/batch-update", json={"issue_ids": [issue_id], "status": "needs_review"})
    assert r.status_code == 200
    assert all(i["status"] == "needs_review" for i in r.json())

    # 15. Batch delete
    r = client.post("/api/issues/batch-delete", json={"issue_ids": [manual_id]})
    assert r.status_code == 204

    # 16. AI Chat
    r = client.post(f"/api/cases/{case_id}/chat", json={"message": "分析风险"})
    assert r.status_code == 201
    assert len(r.json()["messages"]) >= 2
    msg_id = [m["id"] for m in r.json()["messages"] if m["role"] == "assistant"][-1]

    r = client.get(f"/api/cases/{case_id}/chat")
    assert r.status_code == 200

    # 17. Apply AI message
    r = client.post(f"/api/issues/{issue_id}/apply-ai-message",
                    json={"message_id": msg_id, "action": "update_suggestion"})
    assert r.status_code == 200

    # 18. Issue chat
    r = client.post(f"/api/issues/{issue_id}/chat?case_id={case_id}", json={"message": "详细分析"})
    assert r.status_code == 201

    # 19. Versions
    r = client.get(f"/api/cases/{case_id}/versions")
    assert len(r.json()) >= 1

    r = client.get(f"/api/cases/{case_id}/versions/diff",
                   params={"version_a": 1, "version_b": r.json()[0]["version_number"]})
    assert r.status_code == 200
    assert "changes" in r.json()

    # 20. Exports
    r = client.post(f"/api/cases/{case_id}/exports",
                    json={"format": "markdown", "scope": "final"})
    assert r.status_code == 201
    md_path = r.json()["file_path"]

    r = client.post(f"/api/cases/{case_id}/exports",
                    json={"format": "docx", "scope": "final"})
    assert r.status_code == 201

    r = client.post(f"/api/cases/{case_id}/exports",
                    json={"format": "pdf", "scope": "final"})
    assert r.status_code == 201

    # 21. Download security
    r = client.get("/api/exports/download", params={"file_path": md_path})
    assert r.status_code == 200

    r = client.get("/api/exports/download", params={"file_path": "../../../etc/passwd"})
    assert r.status_code == 403

    r = client.get("/api/exports/download", params={"file_path": "/etc/hosts"})
    assert r.status_code == 403

    # 22. Tasks
    r = client.get("/api/tasks")
    assert r.status_code == 200

    r = client.post(f"/api/cases/{case_id}/reanalyze-async", json={"instruction": "async test"})
    assert r.status_code == 202
    task_id = r.json()["task_id"]

    r = client.get(f"/api/tasks/{task_id}")
    assert r.status_code == 200
    assert r.json()["task_id"] == task_id

    # 23. Delete case
    r = client.delete(f"/api/cases/{case_id}", params={"delete_files": True})
    assert r.status_code == 204

    r = client.get(f"/api/cases/{case_id}")
    assert r.status_code == 404
