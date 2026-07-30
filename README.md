# 合同 AI 审查工作台

本项目是本地 Web 版合同 AI 审查工作台的 MVP 骨架。第一阶段已包含后端基础 API、审核记录、文件上传、OCR/PDF 解析接口、OpenAI-compatible AI Provider、人工标记问题服务、前端审查工作台骨架和 Markdown 导出。

## 后端启动

```bash
cd backend
/Users/alink/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

## 前端启动

```bash
cd frontend
npm install
npm run dev
```

默认前端地址为 Vite 输出的本地地址，通常是 `http://127.0.0.1:5173`。

## 测试

```bash
cd backend
pytest -v

cd frontend
npm test
npm run build
```

## 当前边界

- PaddleOCR 尚未作为运行时依赖接入，当前先保留 OCR Provider 接口。
- 流程合规审计的日期抽取、节点比对和盖章检测将在后续实现。
- DOCX/PDF 正式报告导出将在 Markdown 导出稳定后实现。

## 免责声明

系统生成内容属于 AI 辅助审查，不替代律师最终法律意见。
