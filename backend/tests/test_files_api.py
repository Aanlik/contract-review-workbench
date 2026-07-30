from fastapi.testclient import TestClient

from app.core.database import get_session
from app.main import create_app
from app.models.review import AppSetting
from app.services.document_parser import ParsedBlock


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


def test_upload_contract_uses_configured_rapidocr_engine(db_session, monkeypatch):
    db_session.add(
        AppSetting(
            key="system",
            value={"ocr_engine": "rapidocr", "storage_root": "./data/storage"},
        )
    )
    db_session.commit()
    monkeypatch.setattr(
        "app.services.document_parser.RapidOcrProvider.recognize_page",
        lambda self, path: [
            ParsedBlock(
                text="合同签订日期：2026年7月18日",
                bbox=[0, 0, 100, 20],
                confidence=0.96,
                source="ocr",
                order_index=0,
            )
        ],
    )

    client = make_client(db_session)
    case = client.post("/api/cases", json={"title": "RapidOCR 上传测试"}).json()
    response = client.post(
        f"/api/cases/{case['id']}/files",
        data={"file_type": "contract"},
        files={"file": ("contract.png", b"fake image", "image/png")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["parse_status"] == "parsed"
    assert body["parse_method"] == "ocr"


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


def test_list_case_files_returns_uploaded_materials(db_session):
    client = make_client(db_session)
    case = client.post("/api/cases", json={"title": "文件列表测试"}).json()
    client.post(
        f"/api/cases/{case['id']}/files",
        data={"file_type": "sign_report"},
        files={"file": ("sign.txt", "审批通过：2026年7月20日".encode(), "text/plain")},
    )

    response = client.get(f"/api/cases/{case['id']}/files")
    assert response.status_code == 200
    files = response.json()
    assert files[0]["file_name"] == "sign.txt"
    assert files[0]["parse_status"] == "parsed"


def test_list_case_documents_returns_pages_and_blocks(db_session):
    client = make_client(db_session)
    case = client.post("/api/cases", json={"title": "文档文本块测试"}).json()
    client.post(
        f"/api/cases/{case['id']}/files",
        data={"file_type": "contract"},
        files={"file": ("contract.txt", "合同签订日期：2026年7月18日".encode(), "text/plain")},
    )

    response = client.get(f"/api/cases/{case['id']}/documents")

    assert response.status_code == 200
    documents = response.json()
    assert documents[0]["file_name"] == "contract.txt"
    assert documents[0]["pages"][0]["page_number"] == 1
    assert documents[0]["pages"][0]["blocks"][0]["text"] == "合同签订日期：2026年7月18日"
