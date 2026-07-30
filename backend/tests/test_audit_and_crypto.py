"""Tests for audit logging and API key encryption."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from app.core.crypto import decrypt_api_key, encrypt_api_key
from app.core.database import get_session
from app.main import create_app
from app.services.audit_service import list_audit_logs, record_audit


def _make_client(db_session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: (yield db_session)
    return TestClient(app)


def test_encrypt_decrypt_roundtrip():
    original = "sk-test-key-12345"
    encrypted = encrypt_api_key(original)
    assert encrypted != original
    assert decrypt_api_key(encrypted) == original


def test_encrypt_empty_string():
    assert encrypt_api_key("") == ""
    assert decrypt_api_key("") == ""


def test_decrypt_plaintext_fallback():
    """If a key is stored in plaintext, decrypt should return it as-is."""
    plaintext = "sk-plain-text-key"
    assert decrypt_api_key(plaintext) == plaintext


def test_audit_record_created(db_session):
    record_audit(db_session, action="create", entity_type="case", entity_id=1, user="test", details={"title": "test"})
    logs = list_audit_logs(db_session)
    assert len(logs) == 1
    assert logs[0].action == "create"
    assert logs[0].entity_type == "case"
    assert logs[0].entity_id == 1


def test_audit_filter_by_entity(db_session):
    record_audit(db_session, action="create", entity_type="case", entity_id=1)
    record_audit(db_session, action="update", entity_type="issue", entity_id=2)
    case_logs = list_audit_logs(db_session, entity_type="case")
    assert len(case_logs) == 1
    issue_logs = list_audit_logs(db_session, entity_type="issue")
    assert len(issue_logs) == 1


def test_audit_case_create_endpoint(db_session):
    client = _make_client(db_session)
    response = client.post("/api/cases", json={"title": "audit test case"})
    assert response.status_code == 200
    case_id = response.json()["id"]
    audit_resp = client.get("/api/audit/logs", params={"entity_type": "case", "entity_id": case_id})
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    assert len(logs) >= 1
    assert logs[0]["action"] == "create"


def test_ai_settings_encrypted_in_db(db_session):
    """API key should be encrypted in the database, not plaintext."""
    # Clear global cache
    from app.api.routes import settings as settings_route
    settings_route._ai_settings = None
    
    client = _make_client(db_session)
    settings_data = {
        "base_url": "https://api.example.com/v1",
        "api_key": "sk-secret-key-abc",
        "model": "test-model",
        "temperature": 0.2,
        "timeout_seconds": 30,
    }
    resp = client.put("/api/settings/ai", json=settings_data)
    assert resp.status_code == 200
    # Read directly from DB to verify encryption
    db_session.expire_all()
    from app.models.review import AppSetting
    row = db_session.get(AppSetting, "ai")
    assert row is not None, "No AppSetting row found for key 'ai'"
    assert row.value["api_key"] != "sk-secret-key-abc"  # Should be encrypted
    # But reading through API should return decrypted
    settings_route._ai_settings = None  # clear cache to force DB read
    resp2 = client.get("/api/settings/ai")
    assert resp2.json()["api_key"] == "sk-secret-key-abc"
