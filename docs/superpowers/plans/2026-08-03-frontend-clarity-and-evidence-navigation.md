# 前端可读性与证据定位改造实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 提升浅色主题可读性、完成界面中文化、支持最多 4 份事项签报/会议纪要上传，并让问题点击自动定位到合同 OCR 证据。

**Architecture:** 保持现有 React/Vite 结构和后端 API 不变。用统一语义文案映射和 CSS 设计令牌处理显示层；新建审核页把事项材料从单个 File 改为 File[]，逐文件复用既有上传 API；证据查看器接收由问题证据生成的导航目标，在合同文档中选择页、展开合同模块并滚动到对应 OCR 块。

**Tech Stack:** React 18, TypeScript, Vite, Vitest, Testing Library, 原生 CSS, Playwright。

## Global Constraints

- 所有用户可见文本使用中文；内部 API 路径、请求字段和枚举值保持现状。
- 事项签报 / 会议纪要为可选材料，最多选择 4 个，超过上限必须在提交前显示中文错误。
- 浅色主题正文和辅助文字必须在白色背景上保持 WCAG AA 可读性，不使用低对比度白字或浅灰字。
- 问题证据优先按 fileId + pageNumber + ocrBlockId 定位；缺少证据时默认打开合同 OCR 文档并显示无具体定位提示。
- 不修改现有 macOS/Windows 打包文件和 releases/ 产物。

### Task 1: 语义化中文显示与浅色主题对比度

**Files:**
- Modify: frontend/src/components/IssueList.tsx
- Modify: frontend/src/components/IssueDetail.tsx
- Modify: frontend/src/components/EvidenceViewer.tsx
- Modify: frontend/src/components/VersionComparison.tsx
- Modify: frontend/src/pages/NewCasePage.tsx
- Modify: frontend/src/pages/ReviewWorkspacePage.tsx
- Modify: frontend/src/pages/SettingsPage.tsx
- Modify: frontend/src/pages/CasesPage.tsx
- Modify: frontend/src/pages/AuditLogPage.tsx
- Modify: frontend/src/styles.css
- Test: frontend/src/components/IssueList.test.tsx

**Interfaces:** 新增前端本地映射函数或常量，将 high/medium/low/info、pending/confirmed/modified/rejected/needs_review、ai/manual/system、parsed/processing/needs_ocr/ocr_failed 和导出格式转换为中文；保留筛选和请求使用的英文 value。

- [ ] Step 1: 写显示映射回归测试，验证问题列表显示“高风险”“人工标记”“待处理”，而不显示英文枚举。
- [ ] Step 2: 运行测试确认当前失败：在 frontend 目录运行 npm test -- --run src/components/IssueList.test.tsx。
- [ ] Step 3: 实现中文映射，替换问题列表、问题详情、证据材料、版本对比、设置和导出控件中的可见英文。
- [ ] Step 4: 调整浅色 CSS 令牌，将辅助文字、状态标签和禁用态改为白底可读的深色值，清理浅色主题下的透明白字。
- [ ] Step 5: 运行该测试与 npm run build。

### Task 2: 事项材料最多 4 个并逐文件上传

**Files:**
- Modify: frontend/src/pages/NewCasePage.tsx
- Test: frontend/src/pages/NewCasePage.test.tsx

**Interfaces:** matterMaterials: File[] 保存当前选择的事项材料；handleMatterMaterialsChange(files: FileList | null) 只保留前 4 个文件并设置中文提示；提交时逐个调用 uploadCaseFile(caseId, "matter_report", file, onProgress)。

- [ ] Step 1: 写多文件选择和上限测试，验证 multiple 属性、4 个文件显示和第五个文件的中文提示。
- [ ] Step 2: 运行 npm test -- --run src/pages/NewCasePage.test.tsx，确认当前实现因单文件状态而失败。
- [ ] Step 3: 将事项材料状态改为 File[]，增加 multiple、中文无障碍标签、文件数量和逐项移除按钮。
- [ ] Step 4: 改造提交循环，逐个上传事项材料、更新进度、持久化全部文件名；无材料时跳过。
- [ ] Step 5: 运行该测试和 npm run build。

### Task 3: 问题点击后跳转合同 OCR 证据

**Files:**
- Modify: frontend/src/pages/ReviewWorkspacePage.tsx
- Modify: frontend/src/components/EvidenceViewer.tsx
- Modify: frontend/src/components/IssueList.tsx
- Modify: frontend/src/styles.css
- Test: frontend/src/components/EvidenceViewer.test.tsx

**Interfaces:** EvidenceViewer 新增 focusRequest 属性，形状为 issueId、fileId、pageNumber、ocrBlockId；查看器维护 selectedDocumentId 和 selectedPageId，并为 OCR 文本块渲染稳定的 DOM 标识；工作区在 selectedIssue 变化时从首个证据引用生成目标，无证据时指定 contract 文档。

- [ ] Step 1: 写定位测试，验证选中问题后合同模块展开、目标页可见、目标块带 focused 标记。
- [ ] Step 2: 运行 npm test -- --run src/components/EvidenceViewer.test.tsx，确认当前实现没有合同优先切换和块级定位而失败。
- [ ] Step 3: 按 fileId 找文档、按 pageNumber 找页、优先使用 ocrBlockId；用 useEffect 设置页面并调用 scrollIntoView({ block: "center" })，证据缺失时回退合同第一页。
- [ ] Step 4: 增加中文定位状态，显示“已定位到第 X 页”或“暂无具体证据定位”，目标块增加高亮样式。
- [ ] Step 5: 运行该测试和 npm run build。

### Task 4: 全量回归与浏览器验收

**Files:** 只在必要时修改 Tasks 1-3 中的文件。

- [ ] Step 1: 在 frontend 目录运行 npm test。
- [ ] Step 2: 运行 npm run build。
- [ ] Step 3: 保持后端 127.0.0.1:8000，启动前端开发服务，使用 Playwright 检查浅色主题文字、事项材料 4 文件选择/移除、中文枚举和问题点击后的合同 OCR 定位。
- [ ] Step 4: 运行 git diff --check 和 git status --short，确认没有修改打包产物、个人测试文件或无关文件。
