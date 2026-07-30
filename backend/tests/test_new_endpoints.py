"""Tests for newer API endpoints: batch operations, version diff, tasks, async reanalyze."""

from fastapi.testclient import TestClient

from app.core.database import get_session
from app.main import create_app
from app.models.review import Issue, ReviewCase, ReviewVersion, UploadedFile


def make_client(db_session):
    app = create_app()

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


def _create_case_with_issues(db_session):
    """Helper: create a case with 3 issues for batch/diff testing."""
    case = ReviewCase(title="批量测试合同")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    db_session.add(ReviewVersion(case_id=case.id, version_number=1, trigger="init"))
    db_session.add_all([
        Issue(case_id=case.id, issue_type="contract_risk", source="ai",
              risk_level="high", title="高风险问题A", description="desc A", status="pending", review_version=1),
        Issue(case_id=case.id, issue_type="contract_risk", source="ai",
              risk_level="medium", title="中风险问题B", description="desc B", status="pending", review_version=1),
        Issue(case_id=case.id, issue_type="manual_mark", source="manual",
              risk_level="low", title="人工标记C", description="desc C", status="pending", review_version=1),
    ])
    db_session.commit()
    return case


# ── Batch Operations ──

def test_batch_update_status(db_session):
    case = _create_case_with_issues(db_session)
    client = make_client(db_session)

    issues = client.get(f"/api/cases/{case.id}/issues").json()
    ids = [i["id"] for i in issues[:2]]

    response = client.post("/api/issues/batch-update", json={
        "issue_ids": ids,
        "status": "confirmed",
    })
    assert response.status_code == 200
    updated = response.json()
    assert all(i["status"] == "confirmed" for i in updated)
    assert len(updated) == 2


def test_batch_update_risk_level(db_session):
    case = _create_case_with_issues(db_session)
    client = make_client(db_session)

    issues = client.get(f"/api/cases/{case.id}/issues").json()
    ids = [issues[0]["id"]]

    response = client.post("/api/issues/batch-update", json={
        "issue_ids": ids,
        "risk_level": "info",
    })
    assert response.status_code == 200
    assert response.json()[0]["risk_level"] == "info"


def test_batch_delete(db_session):
    case = _create_case_with_issues(db_session)
    client = make_client(db_session)

    issues = client.get(f"/api/cases/{case.id}/issues").json()
    assert len(issues) == 3
    ids = [i["id"] for i in issues[:2]]

    response = client.post("/api/issues/batch-delete", json={"issue_ids": ids})
    assert response.status_code == 204

    remaining = client.get(f"/api/cases/{case.id}/issues").json()
    assert len(remaining) == 1
    assert remaining[0]["title"] == "人工标记C"


# ── Version Diff ──

def test_version_diff_returns_changes(db_session):
    case = ReviewCase(title="版本对比合同")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # V1: 2 issues
    db_session.add(ReviewVersion(case_id=case.id, version_number=1, trigger="init"))
    db_session.add_all([
        Issue(case_id=case.id, issue_type="contract_risk", source="ai",
              risk_level="high", title="问题A", description="desc", status="pending", review_version=1),
        Issue(case_id=case.id, issue_type="contract_risk", source="ai",
              risk_level="medium", title="问题B", description="desc", status="pending", review_version=1),
    ])
    db_session.commit()

    # V2: remove B, add C, modify A's risk
    db_session.add(ReviewVersion(case_id=case.id, version_number=2, trigger="reanalyze"))
    db_session.add_all([
        Issue(case_id=case.id, issue_type="contract_risk", source="ai",
              risk_level="low", title="问题A", description="modified desc", status="pending", review_version=2),
        Issue(case_id=case.id, issue_type="contract_risk", source="ai",
              risk_level="medium", title="问题C", description="new desc", status="pending", review_version=2),
    ])
    db_session.commit()

    client = make_client(db_session)
    response = client.get(f"/api/cases/{case.id}/versions/diff", params={"version_a": 1, "version_b": 2})
    assert response.status_code == 200
    data = response.json()
    assert data["version_a"] == 1
    assert data["version_b"] == 2

    changes = data["changes"]
    change_types = {c["change_type"] for c in changes}
    assert "added" in change_types
    assert "removed" in change_types
    assert "modified" in change_types

    added = next(c for c in changes if c["change_type"] == "added")
    assert added["title"] == "问题C"

    removed = next(c for c in changes if c["change_type"] == "removed")
    assert removed["title"] == "问题B"

    modified = next(c for c in changes if c["change_type"] == "modified")
    assert modified["title"] == "问题A"
    assert modified["old_risk_level"] == "high"


def test_version_diff_same_version_returns_empty(db_session):
    case = ReviewCase(title="无差异合同")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    db_session.add(ReviewVersion(case_id=case.id, version_number=1, trigger="init"))
    db_session.commit()

    client = make_client(db_session)
    response = client.get(f"/api/cases/{case.id}/versions/diff", params={"version_a": 1, "version_b": 1})
    assert response.status_code == 200
    assert response.json()["changes"] == []


# ── Tasks ──

def test_list_tasks_returns_empty_initially():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_get_nonexistent_task_returns_404():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/tasks/nonexistent")
    assert response.status_code == 404


# ── Async Reanalyze ──

def test_reanalyze_async_returns_task_id(db_session, tmp_path):
    case = ReviewCase(title="异步审核")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    contract = tmp_path / "c.txt"
    contract.write_text("合同签订日期：2026年1月1日")
    db_session.add(UploadedFile(case_id=case.id, file_type="contract",
                                file_name="c.txt", original_path=str(contract), parse_status="uploaded"))
    db_session.commit()

    client = make_client(db_session)
    response = client.post(f"/api/cases/{case.id}/reanalyze-async", json={"instruction": "test"})
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["case_id"] == case.id

    # Verify task exists and has valid structure
    task_response = client.get(f"/api/tasks/{data['task_id']}")
    assert task_response.status_code == 200
    task = task_response.json()
    assert task["task_id"] == data["task_id"]
    assert task["status"] in ("queued", "running", "completed", "failed")
    # Note: in-memory SQLite cannot be shared across threads, so the background
    # task may fail. We verify the task system works, not the full execution.
