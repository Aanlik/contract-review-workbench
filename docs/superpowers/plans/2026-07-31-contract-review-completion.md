# Contract Review Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the local contract review MVP into a practical workbench for Chinese scanned contracts, process compliance audit, evidence annotation, configurable AI/OCR, cleanup, versioning, and richer exports.

**Architecture:** Keep the existing FastAPI + SQLite + local storage backend and React/Vite frontend. Add narrow service boundaries instead of replacing the current structure: provider compatibility in `ai_provider.py`, system settings in settings routes, cleanup in storage/case services, process audit helpers in `review_run_service.py`, and evidence annotation in the existing workbench components.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, PyMuPDF, optional PaddleOCR/RapidOCR, Markdown/DOCX/PDF export fallbacks, React, TypeScript, Vite, Vitest.

## Global Constraints

- Preserve local-first storage and do not add login or permission systems in this phase.
- Use OpenAI-compatible AI settings and keep providers configurable.
- OCR must preserve text, page, confidence, bbox, and source when the runtime is available.
- AI/manual issues must stay editable, rejectable, persistent, and linked to evidence.
- Page refresh must preserve selected case, selected issue, filters, and conversations.
- Exports must include an AI-assisted review disclaimer.
- Use TDD for behavior changes.

---

### Task 1: Provider and System Settings Completion

**Files:**
- Modify: `backend/app/schemas/settings.py`
- Modify: `backend/app/api/routes/settings.py`
- Modify: `backend/app/services/ai_provider.py`
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/SettingsPage.tsx`
- Test: `backend/tests/test_settings_and_chat_api.py`

**Interfaces:**
- Produces: `SystemSettings(ocr_engine, storage_root)`
- Produces: `GET /api/settings/system`
- Produces: `PUT /api/settings/system`
- Updates: `OpenAICompatibleProvider.chat()` to support provider-specific auth headers.

- [ ] Write failing tests for persisted system settings and MiMo `api-key` auth header.
- [ ] Run targeted tests and verify they fail.
- [ ] Implement schemas, routes, and provider header selection.
- [ ] Run targeted tests and verify they pass.

### Task 2: Cleanup, Export Scope, and Versions

**Files:**
- Modify: `backend/app/api/routes/cases.py`
- Modify: `backend/app/core/storage.py`
- Modify: `backend/app/api/routes/exports.py`
- Modify: `backend/app/services/export_service.py`
- Modify: `backend/app/api/routes/review_runs.py`
- Modify: frontend cases/workspace API and pages.
- Test: backend API tests.

**Interfaces:**
- Produces: `DELETE /api/cases/{case_id}?delete_files=true`
- Produces: export scope filtering for `all`, `final`, `high_and_medium`, `confirmed`.
- Produces: `GET /api/cases/{case_id}/versions`

- [ ] Write failing tests for file cleanup, export filtering, and version list.
- [ ] Implement minimal backend and frontend support.
- [ ] Run tests and build.

### Task 3: OCR Runtime and Process Audit Rules

**Files:**
- Modify: `backend/app/services/document_parser.py`
- Modify: `backend/app/services/review_run_service.py`
- Test: `backend/tests/test_document_parser.py`, `backend/tests/test_review_run_api.py`

**Interfaces:**
- Updates: `PaddleOcrProvider` and `RapidOcrProvider` optional runtime adapters.
- Updates: process audit issues for missing legal review, missing final approval, meeting decision after signing, low confidence evidence.

- [ ] Write failing tests using monkeypatched OCR modules and persisted OCR blocks.
- [ ] Implement adapters and deterministic audit rules.
- [ ] Run backend tests.

### Task 4: Evidence Annotation Workbench

**Files:**
- Modify: `frontend/src/components/EvidenceViewer.tsx`
- Modify: `frontend/src/components/IssueDetail.tsx`
- Modify: `frontend/src/styles.css`
- Test: frontend component tests.

**Interfaces:**
- Produces: underlined evidence spans for selected issue OCR block/text.
- Produces: right-side annotation notes with AI/manual source and suggestions.

- [ ] Write failing component test for highlighted evidence text.
- [ ] Implement evidence matching and underline styling.
- [ ] Run frontend tests and build.

### Task 5: Rich Report Export and Final Verification

**Files:**
- Modify: `backend/app/services/export_service.py`
- Modify: `backend/app/api/routes/exports.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/ReviewWorkspacePage.tsx`
- Test: backend export tests.

**Interfaces:**
- Produces: Markdown with scope options, optional `.docx` when `python-docx` is available, printable HTML/PDF fallback when PDF renderer is unavailable.

- [ ] Write failing export tests for scope and disclaimer.
- [ ] Implement export routing and fallback behavior.
- [ ] Run `PYTHONPATH=backend pytest -q`, `npm test -- --run`, `npm run build`.
- [ ] Restart local backend and smoke test health.
