from types import SimpleNamespace

from fastapi.testclient import TestClient
from PIL import Image

from app.core.database import get_session
from app.main import create_app
from app.models.review import AppSetting, DocumentPage, ReviewCase, UploadedFile
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


def test_upload_contract_returns_ocr_failed_when_parser_crashes(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_parser.PaddleOcrProvider.recognize_page",
        lambda self, path: (_ for _ in ()).throw(ValueError("image decode failed")),
    )
    app = create_app()

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app, raise_server_exceptions=False)
    case = client.post("/api/cases", json={"title": "OCR 异常上传测试"}).json()
    response = client.post(
        f"/api/cases/{case['id']}/files",
        data={"file_type": "contract"},
        files={"file": ("contract.png", b"fake image", "image/png")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["file_name"] == "contract.png"
    assert body["parse_status"] == "ocr_failed"
    assert body["parse_method"] == "ocr"


def test_retry_ocr_endpoint_queues_failed_file(db_session, monkeypatch):
    case = ReviewCase(title="OCR 重试测试")
    db_session.add(case)
    db_session.flush()
    uploaded = UploadedFile(
        case_id=case.id,
        file_type="contract",
        file_name="failed-contract.pdf",
        original_path="/tmp/failed-contract.pdf",
        parse_method="ocr",
        parse_status="ocr_failed",
    )
    db_session.add(uploaded)
    db_session.commit()

    monkeypatch.setattr(
        "app.services.file_ingest_service.task_queue.submit",
        lambda *args, **kwargs: SimpleNamespace(task_id="task-ocr-retry"),
    )
    client = make_client(db_session)

    response = client.post(f"/api/cases/{case.id}/files/{uploaded.id}/retry-ocr")

    assert response.status_code == 202
    assert response.json() == {"task_id": "task-ocr-retry", "file_id": uploaded.id}
    db_session.refresh(uploaded)
    assert uploaded.parse_status == "processing"


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


def test_upload_accepts_split_process_material_types(db_session):
    client = make_client(db_session)
    case = client.post("/api/cases", json={"title": "分离流程材料上传"}).json()

    for file_type, file_name in [
        ("legal_review_report", "legal-report.txt"),
        ("contract_approval", "contract-approval.txt"),
        ("matter_report", "matter.txt"),
    ]:
        response = client.post(
            f"/api/cases/{case['id']}/files",
            data={"file_type": file_type},
            files={"file": (file_name, "审批材料：2026年7月20日".encode(), "text/plain")},
        )
        assert response.status_code == 201
        assert response.json()["file_type"] == file_type


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


def test_page_image_endpoint_generates_legacy_image_and_checks_case_ownership(db_session, tmp_path, monkeypatch):
    storage_root = tmp_path / "storage"
    monkeypatch.setattr("app.services.page_image_service.settings.storage_root", storage_root)
    source = tmp_path / "legacy.png"
    Image.new("RGB", (120, 80), "white").save(source)

    case = ReviewCase(title="页面图片接口")
    other_case = ReviewCase(title="其他案例")
    db_session.add_all([case, other_case])
    db_session.flush()
    uploaded = UploadedFile(
        case_id=case.id,
        file_type="contract",
        file_name=source.name,
        original_path=str(source),
        parse_status="parsed",
    )
    db_session.add(uploaded)
    db_session.flush()
    db_session.add(DocumentPage(file_id=uploaded.id, page_number=1, ocr_status="completed"))
    db_session.commit()

    client = make_client(db_session)
    response = client.get(f"/api/cases/{case.id}/documents/{uploaded.id}/pages/1/image")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.content
    page = db_session.query(DocumentPage).filter_by(file_id=uploaded.id, page_number=1).one()
    assert page.image_path == f"cases/{case.id}/pages/{uploaded.id}/page-0001.png"

    forbidden = client.get(f"/api/cases/{other_case.id}/documents/{uploaded.id}/pages/1/image")
    assert forbidden.status_code == 404


def test_page_image_endpoint_rejects_path_traversal(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.page_image_service.settings.storage_root", tmp_path / "storage")
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 60), "white").save(source)
    case = ReviewCase(title="路径安全")
    db_session.add(case)
    db_session.flush()
    uploaded = UploadedFile(
        case_id=case.id,
        file_type="contract",
        file_name=source.name,
        original_path=str(source),
        parse_status="parsed",
    )
    db_session.add(uploaded)
    db_session.flush()
    db_session.add(
        DocumentPage(
            file_id=uploaded.id,
            page_number=1,
            image_path="../../outside.png",
            ocr_status="completed",
        )
    )
    db_session.commit()

    client = make_client(db_session)
    response = client.get(f"/api/cases/{case.id}/documents/{uploaded.id}/pages/1/image")

    assert response.status_code == 404
