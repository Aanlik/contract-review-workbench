# OCR Original Layout Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在审核工作台的原始页面底图上叠加 OCR 坐标框，并安全支持问题证据定位、置信度显示和历史文件按需生成页面图。

**Architecture:** 后端在文件解析入库时用 PDF 原始页面或图片生成受控 PNG 页面图，数据库只保存相对路径、页面尺寸和 OCR 块坐标；新增按案例归属校验的页面图片接口。前端在 `EvidenceViewer` 中使用原始页面图片和同尺寸 canvas 叠加 OCR 框，问题和文本块共享现有定位状态。

**Tech Stack:** FastAPI、SQLAlchemy、PyMuPDF、Pillow、React、TypeScript、Vitest、Pytest。

## Global Constraints

- 原始合同文件永远不修改，OCR 只作为叠加层和检索依据。
- 页面图片路径必须位于配置的 `storage_root` 下，不向前端返回绝对路径。
- 坐标必须使用与页面底图一致的尺寸；扫描 PDF 使用 OCR 渲染尺寸，文字层 PDF 使用 PDF 页面坐标尺寸。
- 页面图片失败时降级到现有 OCR 文本列表，不阻断审核。
- 兼容 macOS、Windows 和 PyInstaller 运行时的 `Path` 路径处理。
- 不回滚工作区已有的其他功能改动。

---

### Task 1: Persist Original Page Images

**Files:**
- Create: `backend/app/services/page_image_service.py`
- Modify: `backend/app/services/file_ingest_service.py`
- Modify: `backend/app/models/review.py:DocumentPage`
- Test: `backend/tests/test_page_image_service.py`
- Test: `backend/tests/test_files_api.py`

**Interfaces:**
- `PageImageInfo(page_number: int, relative_path: str, width: int, height: int)`。
- `PageImageService.persist(uploaded_file: UploadedFile, parsed_pages: list[ParsedPage], ocr_dpi: int) -> dict[int, PageImageInfo]`。
- `PageImageService.ensure(uploaded_file: UploadedFile, page_number: int, ocr_dpi: int) -> PageImageInfo | None`。
- `PageImageService.resolve(relative_path: str) -> Path` 校验解析路径仍在 `settings.storage_root` 下。

- [ ] **Step 1: Write failing tests for PDF and image page persistence**

Create a fake PDF renderer or a minimal Pillow image fixture so the test does not require PaddleOCR. Assert that `persist` creates `cases/{case_id}/pages/{file_id}/page-0001.png`, returns the actual width and height, and does not use the preprocessed OCR image as the source image. Add a path traversal test for `resolve("../../outside.png")`。

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_page_image_service.py -q --tb=short
```

Expected: FAIL because `PageImageService` and the page image metadata do not exist。

- [ ] **Step 3: Implement page image persistence**

Use `Path` operations only. For PDFs, render every page with PyMuPDF into the controlled page directory. Use `ocr_dpi` when any parsed block on the page has source `ocr`; use 72 DPI for PDF text-layer pages so existing PDF point coordinates line up with the PNG. For image files, open the original image with Pillow and save a PNG copy. Store relative paths such as `cases/12/pages/34/page-0001.png`。

Add `image_path`, `width`, and `height` values when constructing `DocumentPage` in `_persist_pages`. Keep the original `DocumentPage` and `OcrBlock` records if page image generation fails; store no image path and let the API/frontend degrade gracefully。

- [ ] **Step 4: Run focused tests and existing file tests**

Run:

```bash
.venv/bin/python -m pytest backend/tests/test_page_image_service.py backend/tests/test_files_api.py -q --tb=short
```

Expected: PASS, including existing upload/OCR tests。

- [ ] **Step 5: Commit only the page-image feature files**

```bash
git add backend/app/services/page_image_service.py backend/app/services/file_ingest_service.py backend/app/models/review.py backend/tests/test_page_image_service.py backend/tests/test_files_api.py
git commit -m "feat: persist original document page images"
```

### Task 2: Add Secure Page Image API

**Files:**
- Modify: `backend/app/api/routes/files.py`
- Test: `backend/tests/test_files_api.py`

**Interfaces:**
- `GET /api/cases/{case_id}/documents/{file_id}/pages/{page_number}/image` returns `image/png` for a page owned by the case。
- The endpoint calls `PageImageService.ensure` when the database page has no image path, allowing old uploads to work without re-upload。

- [ ] **Step 1: Write failing endpoint tests**

Add tests that create a case, upload or insert a parsed document page, request the owned page image, and assert status `200`, `content-type` beginning with `image/png`, and non-empty bytes. Add tests for a file from another case and an invalid page number returning `404`. Add a test that sets a malicious relative path and verifies the endpoint rejects it without reading outside storage。

- [ ] **Step 2: Run endpoint tests and verify failure**

```bash
.venv/bin/python -m pytest backend/tests/test_files_api.py -k "page_image" -q --tb=short
```

Expected: FAIL because the route is not registered。

- [ ] **Step 3: Implement the route and ownership checks**

Load the active case first, then load `UploadedFile` with both `id == file_id` and `case_id == case_id`, then load the requested page by `file_id` and `page_number`. Return `404` for missing ownership or page. Resolve only the stored relative path through `PageImageService.resolve`; never accept a path from the request. If the image is missing, call `ensure`, persist the resulting relative path and dimensions, and commit before returning `FileResponse`。

- [ ] **Step 4: Run endpoint tests and lint**

```bash
.venv/bin/python -m pytest backend/tests/test_files_api.py -q --tb=short
.venv/bin/ruff check backend/app backend/tests
```

Expected: PASS。

### Task 3: Add Original-Page Overlay to the Evidence Viewer

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/ReviewWorkspacePage.tsx`
- Modify: `frontend/src/components/EvidenceViewer.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/src/components/EvidenceViewer.test.tsx`

**Interfaces:**
- `documentPageImageUrl(caseId: number, fileId: number, pageNumber: number): string` returns `/api/cases/{caseId}/documents/{fileId}/pages/{pageNumber}/image`。
- `EvidenceViewer` receives `caseId` and passes it to the image URL helper。
- `BboxOverlay` accepts `showAllBlocks: boolean` and `onBlockClick: (blockId: number) => void`。

- [ ] **Step 1: Write failing frontend tests**

Extend the EvidenceViewer fixture with `width`, `height`, and a page image marker or mock the image URL helper. Assert that a page image is rendered, its source uses the case/file/page endpoint, and the `仅显示问题框` control exists. Keep the existing issue focus and OCR text assertions unchanged。

- [ ] **Step 2: Run the focused frontend test and verify failure**

```bash
cd frontend
npm test -- --run src/components/EvidenceViewer.test.tsx
```

Expected: FAIL because the EvidenceViewer currently renders only an empty canvas container。

- [ ] **Step 3: Implement the bottom-image and overlay layer**

Render an `<img>` with `position: absolute` and a same-size canvas above it. Use the stored page width/height as the drawing coordinate system and CSS width for responsive scaling. Draw all blocks lightly in the default mode; in issue-only mode draw only evidence/highlighted blocks. Use green/yellow/red confidence colors and orange/red evidence colors。

Make the canvas interactive: map the pointer position from displayed CSS coordinates back to page coordinates, find the topmost matching OCR bbox, call `onBlockClick`, set the focused block, and scroll the matching text element into view. Keep the canvas pointer-events disabled when the page has no coordinate-bearing blocks。

Add a compact mode control with labels `显示全部识别框` and `仅显示问题框`. When the image fails to load or the page has no image URL, show the existing text list and a localized non-blocking status。

- [ ] **Step 4: Pass the case ID and verify frontend behavior**

Update the `ReviewWorkspacePage` render call to pass `caseId`. Run:

```bash
cd frontend
npm test -- --run src/components/EvidenceViewer.test.tsx
npm run build
```

Expected: PASS and a successful TypeScript/Vite build。

### Task 4: Verify History, Coordinate Alignment, and Regression Coverage

**Files:**
- Modify: `backend/tests/test_review_run_api.py` for a page-image-backed evidence fixture
- Modify: `frontend/src/components/EvidenceViewer.test.tsx` for responsive overlay assertions
- Test: `backend/tests/test_page_image_service.py` for legacy lazy generation

- [ ] **Step 1: Add alignment regression assertions**

Use a page fixture with width `100`, height `200`, and bbox `[10, 20, 40, 60]`. Assert that the overlay uses those same dimensions and that evidence block selection still targets the same OCR block after the page image is present。

- [ ] **Step 2: Add legacy lazy-generation coverage**

Create a `DocumentPage` with `image_path=None` and a valid original uploaded PDF/image, call the image endpoint, and assert that the response succeeds and the database page now stores a safe relative path。

- [ ] **Step 3: Run the complete test suite**

```bash
.venv/bin/ruff check backend/app backend/tests
.venv/bin/python -m pytest backend/tests/ -q --tb=short
cd frontend
npm test -- --run
npm run build
```

Expected: all backend and frontend tests pass; existing issue navigation, manual marking, AI chat, OCR status, and export behavior remain unchanged。

- [ ] **Step 4: Run a browser smoke check**

Open the running app, select a case with a scanned document, click an AI or manual issue with evidence, confirm the original page image loads, confirm the evidence box is visible, toggle issue-only mode, refresh the page, and confirm the selected issue/page state remains usable。

- [ ] **Step 5: Review the final diff**

```bash
git diff --check
git status --short
git diff --stat
```

Confirm no local API keys, uploaded PDFs, generated page images, or personal data are staged。
