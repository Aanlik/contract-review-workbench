# Contract Review Workbench MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable local contract AI review workbench with persistent review records, upload flow, OCR/PDF parsing interfaces, configurable OpenAI-compatible AI access, issue management, AI chat hooks, and a problem-navigation UI.

**Architecture:** Use a local FastAPI backend with SQLite persistence and local file storage, plus a React TypeScript Vite frontend. Keep OCR, PDF parsing, AI provider, export, and task execution behind focused service boundaries so the first version can run locally and later move to an intranet deployment.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.x, Alembic, SQLite, PyMuPDF, Pillow, httpx, pytest, React, TypeScript, Vite, Vitest, Testing Library.

## Global Constraints

- First version is a local Web workbench, not a full approval-flow system.
- Contract files default to local machine storage.
- AI provider must be OpenAI-compatible and configurable with `base_url`, `api_key`, `model`, temperature, and timeout.
- Contract scanned files default to OCR; OA PDFs prefer PDF text extraction and fall back to OCR.
- OCR results must preserve file, page, text block, coordinates, confidence, and source.
- AI outputs must be editable and rejectable by the user.
- Manual issues must support the same AI interaction and persistence as AI-generated issues.
- Page refresh must preserve review case, issue list, manual marks, AI conversations, applied suggestions, filters, and selected issue.
- Date and seal judgments must show evidence and confidence.
- Report export must include an AI-assisted review disclaimer.
- Do not implement multi-user login, permission system, electronic signing, company policy knowledge base, cloud OCR, OA auto-fetching, or mobile-first layout in this phase.

---

## File Structure

Create this project layout:

```text
backend/
  app/
    api/
      routes/
        cases.py
        files.py
        issues.py
        ai.py
        settings.py
        exports.py
      router.py
    core/
      config.py
      database.py
      storage.py
    models/
      base.py
      review.py
    schemas/
      review.py
      settings.py
    services/
      ai_provider.py
      document_parser.py
      export_service.py
      issue_service.py
      task_service.py
    main.py
  tests/
    test_cases_api.py
    test_issue_service.py
    test_document_parser.py
    test_ai_provider.py
  pyproject.toml
frontend/
  src/
    api/client.ts
    api/types.ts
    components/
      AppShell.tsx
      IssueList.tsx
      EvidenceViewer.tsx
      IssueDetail.tsx
      AiChatPanel.tsx
    pages/
      CasesPage.tsx
      NewCasePage.tsx
      ReviewWorkspacePage.tsx
      SettingsPage.tsx
    state/workspace.ts
    App.tsx
    main.tsx
  package.json
  vite.config.ts
  tsconfig.json
```

---

### Task 1: Backend Foundation and Health Check

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/app/api/router.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/base.py`
- Create: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `create_app() -> FastAPI`
- Produces: `settings: Settings`
- Produces: `get_session() -> Generator[Session, None, None]`

- [ ] **Step 1: Write failing backend health test**

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_returns_ok():
    client = TestClient(create_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_health.py -v`

Expected: FAIL because `app.main` does not exist.

- [ ] **Step 3: Add backend project metadata**

Create `backend/pyproject.toml` with dependencies:

```toml
[project]
name = "contract-review-workbench-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.116.0",
  "uvicorn[standard]>=0.35.0",
  "sqlalchemy>=2.0.0",
  "pydantic-settings>=2.0.0",
  "python-multipart>=0.0.20",
  "httpx>=0.27.0",
  "pymupdf>=1.24.0",
  "pillow>=10.0.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
  "pytest-asyncio>=0.23.0",
  "ruff>=0.5.0",
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 4: Implement app factory and health route**

`backend/app/main.py`:

```python
from fastapi import FastAPI

from app.api.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(title="Contract Review Workbench")
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
```

`backend/app/api/router.py`:

```python
from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

`backend/app/core/config.py`:

```python
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./data/app.db"
    storage_root: Path = Path("./data/storage")


settings = Settings()
```

`backend/app/core/database.py`:

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

`backend/app/models/base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_health.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend
git commit -m "feat: add backend foundation"
```

---

### Task 2: Persistence Models and Case APIs

**Files:**
- Create: `backend/app/models/review.py`
- Create: `backend/app/schemas/review.py`
- Create: `backend/app/api/routes/cases.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/test_cases_api.py`

**Interfaces:**
- Consumes: `Base`, `get_session()`
- Produces: `ReviewCase`, `UploadedFile`, `DocumentPage`, `OcrBlock`, `Issue`, `EvidenceRef`, `AiConversation`, `AiMessage`, `AiApplication`, `ReviewVersion`, `ExportRecord`
- Produces endpoints: `POST /api/cases`, `GET /api/cases`, `GET /api/cases/{case_id}`, `PATCH /api/cases/{case_id}`, `DELETE /api/cases/{case_id}`

- [ ] **Step 1: Write failing case API tests**

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_create_and_list_cases():
    client = TestClient(create_app())
    created = client.post("/api/cases", json={"title": "测试合同", "note": "重点看付款"}).json()
    assert created["title"] == "测试合同"
    assert created["note"] == "重点看付款"
    assert created["status"] == "created"

    cases = client.get("/api/cases").json()
    assert any(item["id"] == created["id"] for item in cases)


def test_soft_delete_case_hides_from_list():
    client = TestClient(create_app())
    created = client.post("/api/cases", json={"title": "待删除合同"}).json()
    response = client.delete(f"/api/cases/{created['id']}")
    assert response.status_code == 204
    cases = client.get("/api/cases").json()
    assert all(item["id"] != created["id"] for item in cases)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_cases_api.py -v`

Expected: FAIL because case routes and models do not exist.

- [ ] **Step 3: Implement SQLAlchemy models**

Create enum-backed string fields for statuses and types. Include timestamps with `datetime.utcnow`. Use JSON columns for coordinates and AI config summaries.

Required model classes and minimum fields:

```python
class ReviewCase(Base):
    id: Mapped[int]
    title: Mapped[str]
    note: Mapped[str | None]
    status: Mapped[str]
    current_version: Mapped[int]
    highest_risk_level: Mapped[str | None]
    issue_count: Mapped[int]
    deleted_at: Mapped[datetime | None]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

Also define `UploadedFile`, `DocumentPage`, `OcrBlock`, `Issue`, `EvidenceRef`, `AiConversation`, `AiMessage`, `AiApplication`, `ReviewVersion`, and `ExportRecord` with the fields listed in the approved spec.

- [ ] **Step 4: Implement Pydantic schemas**

Define:

```python
class ReviewCaseCreate(BaseModel):
    title: str
    note: str | None = None


class ReviewCaseUpdate(BaseModel):
    title: str | None = None
    note: str | None = None


class ReviewCaseRead(BaseModel):
    id: int
    title: str
    note: str | None
    status: str
    current_version: int
    highest_risk_level: str | None
    issue_count: int
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 5: Implement case routes**

Use dependency injection for `Session`. On module import during tests, call `Base.metadata.create_all(bind=engine)` once from `create_app()` before routes are used.

Routes:

```python
@router.post("", response_model=ReviewCaseRead)
def create_case(payload: ReviewCaseCreate, session: Session = Depends(get_session)): ...

@router.get("", response_model=list[ReviewCaseRead])
def list_cases(session: Session = Depends(get_session)): ...

@router.get("/{case_id}", response_model=ReviewCaseRead)
def get_case(case_id: int, session: Session = Depends(get_session)): ...

@router.patch("/{case_id}", response_model=ReviewCaseRead)
def update_case(case_id: int, payload: ReviewCaseUpdate, session: Session = Depends(get_session)): ...

@router.delete("/{case_id}", status_code=204)
def delete_case(case_id: int, session: Session = Depends(get_session)): ...
```

- [ ] **Step 6: Register routes**

Add `api_router.include_router(cases.router, prefix="/cases", tags=["cases"])`.

- [ ] **Step 7: Run tests**

Run: `cd backend && pytest tests/test_cases_api.py -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app backend/tests/test_cases_api.py
git commit -m "feat: add review case persistence"
```

---

### Task 3: File Upload and Local Storage

**Files:**
- Create: `backend/app/core/storage.py`
- Create: `backend/app/api/routes/files.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/test_files_api.py`

**Interfaces:**
- Consumes: `ReviewCase`, `UploadedFile`, `get_session()`
- Produces: `StorageService.save_upload(case_id: int, upload: UploadFile) -> StoredFile`
- Produces endpoint: `POST /api/cases/{case_id}/files`

- [ ] **Step 1: Write failing upload test**

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_upload_file_creates_uploaded_file_record():
    client = TestClient(create_app())
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
    assert body["parse_status"] == "uploaded"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_files_api.py -v`

Expected: FAIL because upload route does not exist.

- [ ] **Step 3: Implement storage service**

Create `StoredFile` dataclass:

```python
@dataclass(frozen=True)
class StoredFile:
    original_name: str
    content_type: str | None
    path: Path
    size_bytes: int
```

`save_upload()` must create `storage_root/cases/{case_id}/uploads/`, write bytes using a UUID-prefixed sanitized file name, and return `StoredFile`.

- [ ] **Step 4: Implement upload route**

Accept multipart fields `file_type` and `file`. Validate `file_type` is one of `contract`, `sign_report`, `meeting_minutes`, `approval`, `seal_record`, `other`. Create `UploadedFile` with `parse_status="uploaded"`.

- [ ] **Step 5: Run upload tests**

Run: `cd backend && pytest tests/test_files_api.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app backend/tests/test_files_api.py
git commit -m "feat: add local file upload storage"
```

---

### Task 4: Document Parsing Abstraction

**Files:**
- Create: `backend/app/services/document_parser.py`
- Create: `backend/tests/test_document_parser.py`

**Interfaces:**
- Produces: `ParsedPage`, `ParsedBlock`, `DocumentParser.extract_text(file_path: Path, file_type: str) -> list[ParsedPage]`
- Produces: `OcrProvider.recognize_page(image_path: Path) -> list[ParsedBlock]`

- [ ] **Step 1: Write failing parser tests**

```python
from pathlib import Path

from app.services.document_parser import DocumentParser, ParsedBlock, ParsedPage


class FakeOcrProvider:
    def recognize_page(self, image_path: Path) -> list[ParsedBlock]:
        return [
            ParsedBlock(
                text="甲方盖章",
                bbox=[10, 20, 100, 40],
                confidence=0.93,
                source="ocr",
                order_index=0,
            )
        ]


def test_contract_files_use_ocr_provider(tmp_path):
    sample = tmp_path / "contract.png"
    sample.write_bytes(b"fake image")
    parser = DocumentParser(ocr_provider=FakeOcrProvider())
    pages = parser.extract_text(sample, file_type="contract")
    assert pages == [
        ParsedPage(page_number=1, blocks=[
            ParsedBlock(text="甲方盖章", bbox=[10, 20, 100, 40], confidence=0.93, source="ocr", order_index=0)
        ])
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_document_parser.py -v`

Expected: FAIL because parser does not exist.

- [ ] **Step 3: Implement dataclasses and parser shell**

Use dataclasses:

```python
@dataclass(frozen=True)
class ParsedBlock:
    text: str
    bbox: list[float] | None
    confidence: float | None
    source: Literal["pdf_text", "ocr"]
    order_index: int


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    blocks: list[ParsedBlock]
```

For `file_type == "contract"`, route to OCR. For OA PDFs, add the PDF text extraction method signature and return PDF text blocks when available. If PDF extraction returns no usable text, route to OCR.

- [ ] **Step 4: Add a local OCR runtime guard provider**

Create `PaddleOcrProvider` class with `recognize_page()` raising a clear runtime error:

```python
raise RuntimeError("PaddleOCR is not installed. Install the OCR extra before parsing scanned contracts.")
```

This keeps tests fast while preserving the production integration boundary.

- [ ] **Step 5: Run parser tests**

Run: `cd backend && pytest tests/test_document_parser.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/document_parser.py backend/tests/test_document_parser.py
git commit -m "feat: add document parsing abstraction"
```

---

### Task 5: AI Provider and Structured Review Drafts

**Files:**
- Create: `backend/app/services/ai_provider.py`
- Create: `backend/app/schemas/settings.py`
- Create: `backend/app/api/routes/settings.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/test_ai_provider.py`

**Interfaces:**
- Produces: `AiSettings(base_url: str, api_key: str, model: str, temperature: float, timeout_seconds: float)`
- Produces: `OpenAICompatibleProvider.chat(messages: list[ChatMessage]) -> str`
- Produces: `build_contract_review_prompt(contract_text: str, focus: str | None) -> list[ChatMessage]`

- [ ] **Step 1: Write failing AI provider prompt test**

```python
from app.services.ai_provider import build_contract_review_prompt


def test_contract_review_prompt_requires_structured_json():
    messages = build_contract_review_prompt("甲方不得解除合同。", focus="站在甲方角度")
    joined = "\n".join(message["content"] for message in messages)
    assert "专业律师" in joined
    assert "JSON" in joined
    assert "风险等级" in joined
    assert "甲方不得解除合同" in joined
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_ai_provider.py -v`

Expected: FAIL because AI provider does not exist.

- [ ] **Step 3: Implement AI settings schema and provider**

Implement `AiSettings`, `ChatMessage = TypedDict("ChatMessage", {"role": str, "content": str})`, and an `OpenAICompatibleProvider` using `httpx.Client`.

Provider must call:

```text
POST {base_url.rstrip("/")}/chat/completions
```

with model, messages, temperature, and timeout.

- [ ] **Step 4: Implement prompt builder**

The prompt must instruct the model to return JSON with:

```json
{
  "issues": [
    {
      "title": "问题标题",
      "risk_level": "high|medium|low|info",
      "description": "问题说明",
      "original_text": "原文片段",
      "suggestion": "修改建议",
      "replacement_clause": "可选替代条款",
      "review_note": "法务审查提示",
      "requires_human_review": true
    }
  ]
}
```

- [ ] **Step 5: Run AI provider tests**

Run: `cd backend && pytest tests/test_ai_provider.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ai_provider.py backend/app/schemas/settings.py backend/app/api/routes/settings.py backend/tests/test_ai_provider.py
git commit -m "feat: add configurable ai provider"
```

---

### Task 6: Issue Service, Manual Marking, and AI Application Records

**Files:**
- Create: `backend/app/services/issue_service.py`
- Create: `backend/app/api/routes/issues.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/test_issue_service.py`

**Interfaces:**
- Consumes: `Issue`, `EvidenceRef`, `AiMessage`, `AiApplication`
- Produces: `IssueService.create_manual_issue(case_id: int, payload: ManualIssueCreate) -> Issue`
- Produces: `IssueService.apply_ai_message(issue_id: int, message_id: int, action: str) -> Issue`
- Produces endpoints under `/api/cases/{case_id}/issues`

- [ ] **Step 1: Write failing service test**

```python
from app.services.issue_service import ManualIssueCreate, IssueService


def test_manual_issue_defaults_to_manual_source(db_session):
    service = IssueService(db_session)
    issue = service.create_manual_issue(
        case_id=1,
        payload=ManualIssueCreate(
            title="人工发现付款风险",
            risk_level="medium",
            description="付款条件不清楚",
            suggestion="补充付款触发条件",
            evidence_text="付款时间另行协商",
        ),
    )
    assert issue.source == "manual"
    assert issue.issue_type == "manual_mark"
    assert issue.status == "pending"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_issue_service.py -v`

Expected: FAIL because service does not exist.

- [ ] **Step 3: Implement manual issue schema and service**

Define:

```python
class ManualIssueCreate(BaseModel):
    title: str
    risk_level: Literal["high", "medium", "low", "info"]
    description: str
    suggestion: str | None = None
    evidence_text: str | None = None
```

`create_manual_issue()` creates an `Issue` with `source="manual"`, `issue_type="manual_mark"`, `status="pending"`, and an `EvidenceRef` when `evidence_text` is present.

- [ ] **Step 4: Implement issue routes**

Routes:

```python
GET /api/cases/{case_id}/issues
POST /api/cases/{case_id}/issues/manual
PATCH /api/issues/{issue_id}
POST /api/issues/{issue_id}/apply-ai-message
```

Patch supports title, risk level, description, suggestion, and status.

- [ ] **Step 5: Run issue tests**

Run: `cd backend && pytest tests/test_issue_service.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/issue_service.py backend/app/api/routes/issues.py backend/tests/test_issue_service.py
git commit -m "feat: add issue and manual marking service"
```

---

### Task 7: Frontend Shell and Persistent Workspace State

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/state/workspace.ts`
- Create: `frontend/src/components/AppShell.tsx`
- Create: `frontend/src/pages/CasesPage.tsx`
- Create: `frontend/src/pages/NewCasePage.tsx`
- Create: `frontend/src/pages/ReviewWorkspacePage.tsx`
- Create: `frontend/src/pages/SettingsPage.tsx`

**Interfaces:**
- Consumes backend case and issue endpoints.
- Produces local persistent UI state key: `contract-review-workbench.workspace`

- [ ] **Step 1: Write failing frontend state test**

```typescript
import { describe, expect, it } from "vitest";
import { loadWorkspaceState, saveWorkspaceState } from "./workspace";

describe("workspace state", () => {
  it("persists selected case and filters", () => {
    saveWorkspaceState({ selectedCaseId: 3, selectedIssueId: 9, filters: { riskLevel: "high" } });
    expect(loadWorkspaceState()).toEqual({
      selectedCaseId: 3,
      selectedIssueId: 9,
      filters: { riskLevel: "high" },
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- workspace.test.ts`

Expected: FAIL because frontend project does not exist.

- [ ] **Step 3: Create Vite React project files**

Use React 18, TypeScript, Vite, Vitest, and Testing Library. Add scripts:

```json
{
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "test": "vitest run",
    "build": "tsc && vite build"
  }
}
```

- [ ] **Step 4: Implement API client**

Define `ReviewCase`, `Issue`, `UploadedFile`, `AiMessage`, and functions:

```typescript
export async function listCases(): Promise<ReviewCase[]>;
export async function createCase(payload: { title: string; note?: string }): Promise<ReviewCase>;
export async function listIssues(caseId: number): Promise<Issue[]>;
export async function createManualIssue(caseId: number, payload: ManualIssuePayload): Promise<Issue>;
```

- [ ] **Step 5: Implement persistent workspace state**

`loadWorkspaceState()` reads from localStorage and returns `{ selectedCaseId?: number; selectedIssueId?: number; filters: Record<string, string> }`.

`saveWorkspaceState()` writes the same shape to localStorage.

- [ ] **Step 6: Implement page shell**

Create a dense workbench UI with top navigation: Records, New Review, Settings. Avoid landing-page hero content.

- [ ] **Step 7: Run frontend tests and build**

Run:

```bash
cd frontend
npm test
npm run build
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend
git commit -m "feat: add frontend workbench shell"
```

---

### Task 8: Review Workspace Issue Navigation UI

**Files:**
- Create: `frontend/src/components/IssueList.tsx`
- Create: `frontend/src/components/EvidenceViewer.tsx`
- Create: `frontend/src/components/IssueDetail.tsx`
- Create: `frontend/src/components/AiChatPanel.tsx`
- Modify: `frontend/src/pages/ReviewWorkspacePage.tsx`

**Interfaces:**
- Consumes: `Issue`, `EvidenceRef`, persistent workspace state.
- Produces: problem-navigation layout with issue list, evidence viewer, details, manual marking, and AI chat surface.

- [ ] **Step 1: Write failing component test**

```typescript
import { render, screen } from "@testing-library/react";
import { IssueList } from "./IssueList";

it("renders issue title, source, risk level, and status", () => {
  render(<IssueList issues={[{
    id: 1,
    title: "法审晚于签订日期",
    issueType: "process_audit",
    source: "ai",
    riskLevel: "high",
    status: "pending"
  }]} selectedIssueId={1} onSelect={() => {}} />);
  expect(screen.getByText("法审晚于签订日期")).toBeTruthy();
  expect(screen.getByText("high")).toBeTruthy();
  expect(screen.getByText("ai")).toBeTruthy();
  expect(screen.getByText("pending")).toBeTruthy();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- IssueList.test.tsx`

Expected: FAIL because component does not exist.

- [ ] **Step 3: Implement IssueList**

Render tabs for all, contract risk, process audit, and manual marks. Render filters for risk level and status. Each row has stable height and calls `onSelect(issue.id)`.

- [ ] **Step 4: Implement EvidenceViewer**

Render selected issue evidence with file type, page number, evidence text, confidence, and source. Provide a manual text selection form that calls `onCreateManualIssue`.

- [ ] **Step 5: Implement IssueDetail**

Render title, risk level selector, status selector, description, suggestion, replacement clause, evidence summary, Save button, and Reanalyze button.

- [ ] **Step 6: Implement AiChatPanel**

Render task/problem chat history, input box, Send button, and Apply as suggestion / Apply as new issue buttons.

- [ ] **Step 7: Compose ReviewWorkspacePage**

Use a three-column layout: left issue list, center evidence viewer, right detail and AI chat. Restore selected issue and filters from localStorage.

- [ ] **Step 8: Run frontend tests and build**

Run:

```bash
cd frontend
npm test
npm run build
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/src
git commit -m "feat: add issue navigation workbench"
```

---

### Task 9: Export Stub and End-to-End Local Run

**Files:**
- Create: `backend/app/services/export_service.py`
- Create: `backend/app/api/routes/exports.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/test_export_service.py`
- Create: `README.md`

**Interfaces:**
- Consumes: `ReviewCase`, `Issue`, `EvidenceRef`
- Produces: `ExportService.export_markdown(case_id: int, include_ai_summary: bool) -> Path`
- Produces endpoint: `POST /api/cases/{case_id}/exports`

- [ ] **Step 1: Write failing export test**

```python
from app.services.export_service import ExportService


def test_export_markdown_includes_disclaimer(db_session, tmp_path):
    service = ExportService(db_session, output_root=tmp_path)
    path = service.export_markdown(case_id=1, include_ai_summary=False)
    text = path.read_text(encoding="utf-8")
    assert "AI 辅助审查" in text
    assert "不替代律师最终法律意见" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_export_service.py -v`

Expected: FAIL because export service does not exist.

- [ ] **Step 3: Implement Markdown export**

Export sections: basic information, summary, contract risks, process audit issues, manual marks, low-confidence OCR notes, version notes, disclaimer.

- [ ] **Step 4: Implement export route**

`POST /api/cases/{case_id}/exports` accepts:

```json
{
  "format": "markdown",
  "scope": "final",
  "include_ai_summary": false
}
```

Return export record ID and file path.

- [ ] **Step 5: Add README run instructions**

Include:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

cd frontend
npm install
npm run dev
```

- [ ] **Step 6: Run backend and frontend verification**

Run:

```bash
cd backend && pytest -v
cd frontend && npm test && npm run build
```

Start servers:

```bash
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

Open the frontend and verify health, case creation, issue navigation UI, and settings page.

- [ ] **Step 7: Commit**

```bash
git add backend frontend README.md
git commit -m "feat: add markdown export and run docs"
```

---

## Self-Review

Spec coverage:

- Local Web workbench is covered by Tasks 1, 7, and 8.
- Persistent review records are covered by Task 2.
- Upload and local file storage are covered by Task 3.
- OCR/PDF parsing interfaces are covered by Task 4.
- Configurable OpenAI-compatible AI access is covered by Task 5.
- Manual marking and AI application records are covered by Task 6.
- Problem-navigation UI and refresh persistence are covered by Tasks 7 and 8.
- Markdown export and disclaimer are covered by Task 9.

Deferred by design for later implementation plans:

- Full PaddleOCR runtime installation and image preprocessing pipeline.
- Production-grade seal detection.
- Full flow-compliance date extraction and comparison engine.
- DOCX/PDF report rendering.
- Intranet deployment, PostgreSQL, external task queues, and permissions.

Red-flag scan:

- This plan gives concrete files, interfaces, tests, and commands for each task.

Type consistency:

- Backend issue terms use `contract_risk`, `process_audit`, and `manual_mark`.
- Risk levels use `high`, `medium`, `low`, and `info`.
- Issue statuses use `pending`, `confirmed`, `modified`, `rejected`, and `needs_review`.
- AI provider settings use `base_url`, `api_key`, `model`, `temperature`, and `timeout_seconds`.
