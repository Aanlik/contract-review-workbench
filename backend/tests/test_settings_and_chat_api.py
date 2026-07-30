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
