from fastapi.testclient import TestClient

from app.api.routes import settings as settings_route
from app.core.database import get_session
from app.main import create_app
from app.models.review import ReviewCase


def make_client(db_session):
    app = create_app()

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


def test_ai_settings_are_persisted_in_database(db_session):
    client = make_client(db_session)
    payload = {
        "base_url": "https://api.example.com/v1",
        "api_key": "sk-test",
        "model": "law-model",
        "temperature": 0.1,
        "timeout_seconds": 45,
    }

    assert client.put("/api/settings/ai", json=payload).status_code == 200

    settings_route._ai_settings = None
    fresh_client = make_client(db_session)
    response = fresh_client.get("/api/settings/ai")
    assert response.status_code == 200
    assert response.json() == payload


def test_system_settings_are_persisted_in_database(db_session):
    client = make_client(db_session)
    payload = {
        "ocr_engine": "rapidocr",
        "storage_root": "/tmp/contract-review-storage",
        "ocr_dpi": 320,
        "preprocess_images": False,
    }

    assert client.put("/api/settings/system", json=payload).status_code == 200

    fresh_client = make_client(db_session)
    response = fresh_client.get("/api/settings/system")
    assert response.status_code == 200
    assert response.json() == payload


def test_ai_settings_test_connection_uses_payload(db_session, monkeypatch):
    client = make_client(db_session)
    payload = {
        "base_url": "https://api.example.com/v1",
        "api_key": "sk-test",
        "model": "law-model",
        "temperature": 0.1,
        "timeout_seconds": 45,
    }

    class FakeProvider:
        def __init__(self, settings):
            self.settings = settings

        def chat(self, messages):
            assert self.settings.model == "law-model"
            assert "连接测试" in messages[0]["content"]
            return "连接正常"

    monkeypatch.setattr("app.api.routes.settings.OpenAICompatibleProvider", FakeProvider)
    response = client.post("/api/settings/ai/test", json=payload)

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["model"] == "law-model"
    assert response.json()["message"] == "AI 接口连接正常。"


def test_ai_settings_test_connection_returns_failure_detail(db_session, monkeypatch):
    client = make_client(db_session)
    payload = {
        "base_url": "https://api.example.com/v1",
        "api_key": "sk-test",
        "model": "law-model",
        "temperature": 0.1,
        "timeout_seconds": 45,
    }

    class FailingProvider:
        def __init__(self, settings):
            self.settings = settings

        def chat(self, messages):
            raise RuntimeError("401 Unauthorized")

    monkeypatch.setattr("app.api.routes.settings.OpenAICompatibleProvider", FailingProvider)
    response = client.post("/api/settings/ai/test", json=payload)

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert "401 Unauthorized" in response.json()["message"]


def test_case_chat_persists_user_and_ai_messages(db_session):
    review_case = ReviewCase(title="聊天测试")
    db_session.add(review_case)
    db_session.commit()
    db_session.refresh(review_case)

    client = make_client(db_session)
    response = client.post(
        f"/api/cases/{review_case.id}/chat",
        json={"message": "请解释付款风险"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["scope"] == "case"
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][0]["content"] == "请解释付款风险"
    assert body["messages"][1]["role"] == "assistant"

    history = client.get(f"/api/cases/{review_case.id}/chat").json()
    assert history["messages"][0]["content"] == "请解释付款风险"
