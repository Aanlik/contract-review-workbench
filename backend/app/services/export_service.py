from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.review import ExportRecord, Issue, ReviewCase


class ExportService:
    def __init__(self, session: Session, output_root: Path | None = None) -> None:
        self.session = session
        self.output_root = output_root or settings.storage_root / "exports"

    def export_markdown(
        self,
        case_id: int,
        include_ai_summary: bool,
        scope: str = "final",
    ) -> Path:
        review_case = self.session.get(ReviewCase, case_id)
        if review_case is None:
            raise ValueError("Review case not found")

        issues = list(
            self.session.scalars(
                select(Issue)
                .where(Issue.case_id == case_id)
                .options(selectinload(Issue.evidence_refs))
                .order_by(Issue.risk_level.asc(), Issue.id.asc())
            ).all()
        )
        issues = self._filter_issues(issues, scope)

        target_dir = self.output_root / "cases" / str(case_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"review-case-{case_id}-v{review_case.current_version}.md"
        path.write_text(
            self._render_markdown(review_case, list(issues), include_ai_summary),
            encoding="utf-8",
        )

        self.session.add(
            ExportRecord(
                case_id=case_id,
                export_format="markdown",
                file_path=str(path),
                export_scope=scope,
            )
        )
        self.session.commit()
        return path

    def export_report(
        self,
        case_id: int,
        export_format: str,
        include_ai_summary: bool,
        scope: str = "final",
    ) -> Path:
        if export_format == "markdown":
            return self.export_markdown(case_id, include_ai_summary, scope)
        if export_format == "docx":
            return self._export_docx(case_id, include_ai_summary, scope)
        if export_format == "pdf":
            return self._export_printable_html(case_id, include_ai_summary, scope)
        raise ValueError("Unsupported export format")

    def _export_docx(self, case_id: int, include_ai_summary: bool, scope: str) -> Path:
        try:
            from docx import Document
        except Exception:
            return self.export_markdown(case_id, include_ai_summary, scope)
        markdown_path = self.export_markdown(case_id, include_ai_summary, scope)
        document = Document()
        for line in markdown_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                document.add_heading(line.removeprefix("# "), level=1)
            elif line.startswith("## "):
                document.add_heading(line.removeprefix("## "), level=2)
            elif line.startswith("### "):
                document.add_heading(line.removeprefix("### "), level=3)
            elif line:
                document.add_paragraph(line)
        path = markdown_path.with_suffix(".docx")
        document.save(path)
        return path

    def _export_printable_html(self, case_id: int, include_ai_summary: bool, scope: str) -> Path:
        markdown_path = self.export_markdown(case_id, include_ai_summary, scope)
        html = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>合同审查报告</title>"
            "<style>body{font-family:system-ui,sans-serif;line-height:1.7;max-width:920px;margin:40px auto;color:#1e2930;}"
            "h1,h2,h3{color:#142029} pre{white-space:pre-wrap}</style></head><body><pre>"
            + self._escape_html(markdown_path.read_text(encoding="utf-8"))
            + "</pre></body></html>"
        )
        path = markdown_path.with_suffix(".html")
        path.write_text(html, encoding="utf-8")
        return path

    def _filter_issues(self, issues: list[Issue], scope: str) -> list[Issue]:
        if scope == "all":
            return issues
        if scope in {"high", "high_and_medium"}:
            return [issue for issue in issues if issue.risk_level in {"high", "medium"}]
        if scope == "confirmed":
            return [issue for issue in issues if issue.status == "confirmed"]
        return [issue for issue in issues if issue.status != "rejected"]

    def _escape_html(self, text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def _render_markdown(
        self,
        review_case: ReviewCase,
        issues: list[Issue],
        include_ai_summary: bool,
    ) -> str:
        lines = [
            f"# {review_case.title} 审查报告",
            "",
            "## 基本信息",
            "",
            f"- 审核版本：V{review_case.current_version}",
            f"- 审核状态：{review_case.status}",
            f"- 问题数量：{len(issues)}",
            "",
            "## 摘要结论",
            "",
            "请业务人员和法务结合原始合同、流程材料及证据定位进行最终判断。",
            "",
            "## 问题清单",
            "",
        ]
        if not issues:
            lines.extend(["暂无已记录问题。", ""])
        for issue in issues:
            lines.extend(
                [
                    f"### {issue.title}",
                    "",
                    f"- 类型：{issue.issue_type}",
                    f"- 来源：{issue.source}",
                    f"- 风险等级：{issue.risk_level}",
                    f"- 状态：{issue.status}",
                    "",
                    issue.description,
                    "",
                ]
            )
            if issue.suggestion:
                lines.extend(["**修改建议**", "", issue.suggestion, ""])
            for evidence in issue.evidence_refs:
                lines.extend(
                    [
                        "**证据**",
                        "",
                        f"- 页码：{evidence.page_number or '未关联'}",
                        f"- 原文：{evidence.original_text or '无'}",
                        f"- 置信度：{evidence.confidence if evidence.confidence is not None else '未提供'}",
                        "",
                    ]
                )

        if include_ai_summary:
            lines.extend(["## AI 对话摘要", "", "当前导出未包含逐条对话全文。", ""])

        lines.extend(
            [
                "## 免责声明",
                "",
                "本报告为 AI 辅助审查结果，不替代律师最终法律意见。请结合原始文件、业务背景和人工复核结论使用。",
                "",
            ]
        )
        return "\n".join(lines)
