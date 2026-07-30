
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_session
from app.main import create_app


def make_client(db_session):
    app = create_app()

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


def test_download_rejects_path_traversal(db_session):
    client = make_client(db_session)
    # Attempt to read /etc/passwd via path traversal
    response = client.get("/api/exports/download", params={"file_path": "../../../etc/passwd"})
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


def test_download_rejects_absolute_path_outside_storage(db_session):
    client = make_client(db_session)
    response = client.get("/api/exports/download", params={"file_path": "/etc/hosts"})
    assert response.status_code == 403


def test_download_rejects_non_export_file(db_session, tmp_path):
    """Even if a file is inside storage root, it must be in exports/ subdirectory."""
    # Create a file inside storage root but not in exports/
    storage = settings.storage_root.resolve()
    storage.mkdir(parents=True, exist_ok=True)
    secret = storage / "secret.txt"
    secret.write_text("secret content")

    client = make_client(db_session)
    try:
        relative = str(secret.relative_to(storage))
        response = client.get("/api/exports/download", params={"file_path": relative})
        assert response.status_code == 403
        assert "not an export" in response.json()["detail"]
    finally:
        secret.unlink(missing_ok=True)


def test_download_accepts_valid_export_file(db_session, tmp_path):
    """A real export file under storage_root/exports/ should be downloadable."""
    exports = settings.storage_root.resolve() / "exports" / "cases" / "1"
    exports.mkdir(parents=True, exist_ok=True)
    export_file = exports / "test-report.md"
    export_file.write_text("# Test Report")

    client = make_client(db_session)
    try:
        relative = str(export_file.relative_to(settings.storage_root.resolve()))
        response = client.get("/api/exports/download", params={"file_path": relative})
        assert response.status_code == 200
        assert b"Test Report" in response.content
    finally:
        export_file.unlink(missing_ok=True)


def test_download_rejects_encoded_traversal(db_session):
    """URL-encoded traversal sequences should also be rejected."""
    client = make_client(db_session)
    response = client.get("/api/exports/download", params={"file_path": "..%2F..%2Fetc%2Fpasswd"})
    assert response.status_code in (403, 404)
