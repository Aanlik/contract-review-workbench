from fastapi.testclient import TestClient

from app.core.database import get_session
from app.main import create_app


def make_client(db_session):
    app = create_app()

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


def test_upload_file_creates_uploaded_file_record(db_session):
    client = make_client(db_session)
    case = client.post("/api/cases", json={"title": "上传测试"}).json()
    response = client.post(
        f"/api/cases/{case['id']}/files",
        data={"file_type": "contract"},
        files={"file": ("contract.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["file_name"] == "contract.pdf"
    assert body["file_type"] == "contract"
    assert body["parse_status"] in {"uploaded", "needs_ocr"}


def test_upload_text_flow_file_is_parsed_immediately(db_session):
    client = make_client(db_session)
    case = client.post("/api/cases", json={"title": "解析测试"}).json()
    response = client.post(
        f"/api/cases/{case['id']}/files",
        data={"file_type": "sign_report"},
        files={"file": ("sign.txt", "法务审核：2026年7月20日".encode(), "text/plain")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["parse_status"] == "parsed"
    assert body["parse_method"] == "text"
    assert body["page_count"] == 1
