from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.review import ExportRecord, Issue, ReviewCase


class ExportService:
    def __init__(self, session: Session, output_root: Path | None = None) -> None:
        self.session = session
        self.output_root = output_root or settings.storage_root / "exports"

    def export_markdown(self, case_id: int, include_ai_summary: bool) -> Path:
        review_case = self.session.get(ReviewCase, case_id)
        if review_case is None:
            raise ValueError("Review case not found")

        issues = self.session.scalars(
            select(Issue)
            .where(Issue.case_id == case_id)
            .options(selectinload(Issue.evidence_refs))
            .order_by(Issue.risk_level.asc(), Issue.id.asc())
        ).all()

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
                export_scope="final",
            )
        )
        self.session.commit()
        return path

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
