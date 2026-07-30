from fastapi.testclient import TestClient

from app.core.database import get_session
from app.main import create_app


def make_client(db_session):
    app = create_app()

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


def test_create_and_list_cases(db_session):
    client = make_client(db_session)
    created = client.post("/api/cases", json={"title": "测试合同", "note": "重点看付款"}).json()
    assert created["title"] == "测试合同"
    assert created["note"] == "重点看付款"
    assert created["status"] == "created"

    cases = client.get("/api/cases").json()
    assert any(item["id"] == created["id"] for item in cases)


def test_soft_delete_case_hides_from_list(db_session):
    client = make_client(db_session)
    created = client.post("/api/cases", json={"title": "待删除合同"}).json()
    response = client.delete(f"/api/cases/{created['id']}")
    assert response.status_code == 204
    cases = client.get("/api/cases").json()
    assert all(item["id"] != created["id"] for item in cases)


def test_delete_case_can_remove_local_files(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.storage_root", tmp_path)
    client = make_client(db_session)
    created = client.post("/api/cases", json={"title": "清理文件合同"}).json()
    case_dir = tmp_path / "cases" / str(created["id"])
    case_dir.mkdir(parents=True)
    (case_dir / "contract.txt").write_text("合同原文", encoding="utf-8")

    response = client.delete(f"/api/cases/{created['id']}?delete_files=true")

    assert response.status_code == 204
    assert not case_dir.exists()
