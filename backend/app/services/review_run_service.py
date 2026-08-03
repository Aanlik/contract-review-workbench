import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_api_key
from app.models.review import (
    AppSetting,
    DocumentPage,
    EvidenceRef,
    Issue,
    OcrBlock,
    ReviewCase,
    ReviewVersion,
    UploadedFile,
)
from app.schemas.settings import AiSettings
from app.services.ai_provider import (
    OpenAICompatibleProvider,
    build_contract_review_prompt,
    build_matter_consistency_prompt,
)


@dataclass(frozen=True)
class MaterialBlock:
    text: str
    file_id: int | None = None
    page_number: int | None = None
    ocr_block_id: int | None = None
    bbox: list[float] | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class MaterialText:
    file: UploadedFile
    text: str
    blocks: list[MaterialBlock]


@dataclass(frozen=True)
class DateHit:
    value: date
    label: str
    source: MaterialBlock | None


# Progress steps
STEPS = [
    "加载材料和解析文本",
    "流程合规审计",
    "OCR 识别检查",
    "AI 合同法律风险审查",
    "生成审核结果",
]


class ReviewRunService:
    def __init__(self, session: Session, task_id: str | None = None) -> None:
        self.session = session
        self.task_id = task_id

    def _report_progress(self, step_index: int, detail: str = "") -> None:
        if not self.task_id:
            return
        from app.services.task_queue import task_queue
        label = STEPS[step_index] if step_index < len(STEPS) else detail
        task_queue.update_progress(
            self.task_id,
            progress=f"{label}" + (f" — {detail}" if detail else ""),
            step=step_index + 1,
            total=len(STEPS),
        )

    def reanalyze(self, case_id: int, instruction: str | None = None) -> ReviewCase:
        review_case = self.session.get(ReviewCase, case_id)
        if review_case is None:
            raise ValueError("Review case not found")

        review_case.current_version += 1
        review_case.status = "analyzing"
        self.session.add(
            ReviewVersion(
                case_id=case_id,
                version_number=review_case.current_version,
                trigger="reanalyze",
                review_request=instruction,
                note="基础规则审计版本",
            )
        )
        self.session.commit()

        # Step 1: Load materials
        self._report_progress(0, "正在读取上传文件和 OCR 文本...")
        materials = self._load_materials(case_id)
        file_count = len(materials)
        block_count = sum(len(m.blocks) for m in materials)
        self._report_progress(0, f"已加载 {file_count} 个文件，{block_count} 个文本块")

        # Step 2: Process audit
        self._report_progress(1, "正在检查签报日期、合同签订日期和盖章...")
        created = self._create_process_audit_issues(review_case, materials)
        self._report_progress(1, f"流程审计发现 {len(created)} 个问题")

        # Step 3: OCR gap check
        self._report_progress(2, "正在检查 OCR 识别覆盖率...")
        ocr_issues = self._create_ocr_gap_issues(review_case, materials)
        created.extend(ocr_issues)
        if ocr_issues:
            self._report_progress(2, f"发现 {len(ocr_issues)} 个识别缺口")
        else:
            self._report_progress(2, "OCR 覆盖正常")

        # Step 4: AI contract review
        self._report_progress(3, "正在调用 AI 进行法律风险审查...")
        ai_issues = self._create_ai_contract_issues(review_case, materials, instruction)
        created.extend(ai_issues)
        matter_issues = self._create_matter_consistency_issues(review_case, materials, instruction)
        created.extend(matter_issues)
        self._report_progress(3, f"AI 审查发现 {len(ai_issues) + len(matter_issues)} 个问题")

        # Step 5: Finalize
        self._report_progress(4, "正在汇总审核结果...")
        if not created:
            created.append(
                self._create_issue(
                    review_case,
                    issue_type="contract_risk",
                    title="需要法务人工复核合同条款",
                    risk_level="info",
                    description=(
                        "系统已完成基础读取，但未发现可确定的日期或盖章异常。"
                        "建议继续配置 AI 后执行专业律师视角审查。"
                    ),
                    suggestion="配置 AI 后点击重新审核，或使用人工标记补充重点条款。",
                    evidence_text=None,
                )
            )

        review_case.issue_count = len(created)
        review_case.highest_risk_level = self._highest_risk(case_id, review_case.current_version)
        review_case.status = "completed"
        self.session.commit()
        self.session.refresh(review_case)
        return review_case

    def _load_materials(self, case_id: int) -> list[MaterialText]:
        files = self.session.scalars(
            select(UploadedFile).where(UploadedFile.case_id == case_id).order_by(UploadedFile.id.asc())
        ).all()
        result: list[MaterialText] = []
        for i, file in enumerate(files):
            self._report_progress(0, f"正在加载第 {i + 1}/{len(files)} 个文件: {file.file_name}")
            result.append(self._material(file))
        return result

    def _material(self, uploaded_file: UploadedFile) -> MaterialText:
        persisted_blocks = self._read_persisted_blocks(uploaded_file.id)
        if any(block.text.strip() for block in persisted_blocks):
            return MaterialText(
                file=uploaded_file,
                text="\n".join(block.text for block in persisted_blocks),
                blocks=persisted_blocks,
            )
        fallback_text = self._read_text(Path(uploaded_file.original_path))
        fallback_blocks = [MaterialBlock(text=fallback_text)] if fallback_text.strip() else []
        return MaterialText(file=uploaded_file, text=fallback_text, blocks=fallback_blocks)

    def _read_persisted_blocks(self, uploaded_file_id: int) -> list[MaterialBlock]:
        rows = self.session.execute(
            select(OcrBlock, DocumentPage)
            .join(DocumentPage, OcrBlock.page_id == DocumentPage.id)
            .where(DocumentPage.file_id == uploaded_file_id)
            .order_by(DocumentPage.page_number.asc(), OcrBlock.order_index.asc())
        ).all()
        return [
            MaterialBlock(
                text=ocr_block.text,
                file_id=page.file_id,
                page_number=page.page_number,
                ocr_block_id=ocr_block.id,
                bbox=ocr_block.bbox,
                confidence=ocr_block.confidence,
            )
            for ocr_block, page in rows
        ]

    def _read_text(self, path: Path) -> str:
        if path.suffix.lower() in {".txt", ".md"}:
            if not path.exists():
                return ""
            return path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix.lower() == ".pdf":
            try:
                import fitz

                with fitz.open(path) as document:
                    return "\n".join(page.get_text() for page in document).strip()
            except Exception:
                return ""
        if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            return ""
        return ""

    def _create_process_audit_issues(
        self,
        review_case: ReviewCase,
        materials: list[MaterialText],
    ) -> list[Issue]:
        created: list[Issue] = []
        contract_materials = [m for m in materials if m.file.file_type == "contract"]
        legal_materials = [
            m for m in materials if m.file.file_type in {"legal_review_report", "sign_report"}
        ]
        approval_materials = [
            m for m in materials if m.file.file_type in {"contract_approval", "approval", "sign_report"}
        ]

        if not contract_materials:
            return created

        contract_blocks = [block for m in contract_materials for block in m.blocks]
        contract_text = "\n".join(block.text for block in contract_blocks)

        contract_sign_date = self._extract_date(contract_text, ["签订日期", "签署日期", "签约日期", "签字日期"])
        contract_effective_date = self._extract_date(contract_text, ["生效日期", "生效时间", "合同生效"])

        approval_labels = ["签批日期", "审批日期", "批准日期", "签报日期", "最终审批", "审批通过"]
        legal_review_date = self._extract_date(
            "\n".join(block.text for m in legal_materials for block in m.blocks),
            ["法审日期", "法审时间", "法律审查", "法务审查日期", "法审完成", "法务审核"],
        )
        approval_hit = self._extract_approval_date_hit(approval_materials, approval_labels)
        approval_date = approval_hit.value if approval_hit else None

        reference_date = contract_sign_date or contract_effective_date
        contract_date_hit = self._extract_date_hit(
            contract_materials,
            ["签订日期", "签署日期", "签约日期", "签字日期", "生效日期", "生效时间", "合同生效"],
        )
        if reference_date and legal_review_date and legal_review_date > reference_date:
            legal_hit = self._extract_date_hit(
                legal_materials,
                ["法审日期", "法审时间", "法律审查", "法务审查日期", "法审完成", "法务审核"],
            )
            created.append(
                self._create_issue(
                    review_case,
                    issue_type="process_audit",
                    title="法审日期晚于合同签订日期",
                    risk_level="high",
                    description=(
                        f"合同签订日期为 {reference_date}，但法审完成日期为 {legal_review_date}。"
                        "法审应在合同签订前完成，否则合同条款可能未经法律审查即生效，存在合规风险。"
                    ),
                    suggestion="请确认合同签订流程是否合规，法审是否在签订前完成。如有异常需追溯审批流程。",
                    evidence_text=None,
                    evidence_sources=[
                        contract_date_hit.source if contract_date_hit else None,
                        legal_hit.source if legal_hit else None,
                    ],
                )
            )

        if reference_date and approval_date and approval_date > reference_date:
            created.append(
                self._create_issue(
                    review_case,
                    issue_type="process_audit",
                    title="合同签订日期早于审批通过日期",
                    risk_level="high",
                    description=(
                        f"合同签订日期为 {reference_date}，但签批完成日期为 {approval_date}。"
                        "合同不应在审批通过前签订，否则可能违反内部审批制度。"
                    ),
                    suggestion="请核实审批流程是否在合同签订前全部完成。",
                    evidence_text=None,
                    evidence_sources=[
                        contract_date_hit.source if contract_date_hit else None,
                        approval_hit.source if approval_hit else None,
                    ],
                )
            )

        # 法审签报和合同签批文件是必需的流程证据；事项签报/会议纪要不参与这两个日期判断。
        if legal_review_date is None:
            created.append(
                self._create_issue(
                    review_case,
                    issue_type="process_audit",
                    title="未识别到法务审核记录",
                    risk_level="medium",
                    description=(
                        "在法审签报材料中未检测到法审、法律审查或法务审查日期。"
                        "合同可能未经法务审核即进入签批流程，也可能是扫描件 OCR 未完整识别。"
                    ),
                    suggestion="请上传法审签报并确认其中包含法务审核结论和日期。",
                    evidence_text=None,
                )
            )

        if approval_date is None:
            created.append(
                self._create_issue(
                    review_case,
                    issue_type="process_audit",
                    title="未识别到最终审批通过记录",
                    risk_level="medium",
                    description=(
                        "在合同签批文件材料中未检测到审批通过、最终审批或签批日期。"
                        "合同可能缺少最终审批环节，也可能是扫描件 OCR 未完整识别。"
                    ),
                    suggestion="请上传合同签批文件并确认其中包含最终审批通过结论和日期。",
                    evidence_text=None,
                )
            )

        seal_keywords = ["公章", "合同专用章", "盖章", "印章"]
        has_seal_text = any(
            keyword in contract_text for keyword in seal_keywords
        )
        if not has_seal_text:
            created.append(
                self._create_issue(
                    review_case,
                    issue_type="process_audit",
                    title="合同可能缺少盖章信息",
                    risk_level="medium",
                    description=(
                        "在合同文本中未检测到公章、合同专用章等盖章相关描述。"
                        "可能是因为合同为扫描件未完整 OCR 识别，也可能确实缺少盖章。"
                    ),
                    suggestion="请人工确认合同是否已加盖公章或合同专用章。",
                    evidence_text=None,
                )
            )

        return created

    def _create_matter_consistency_issues(
        self,
        review_case: ReviewCase,
        materials: list[MaterialText],
        instruction: str | None,
    ) -> list[Issue]:
        contract_materials = [m for m in materials if m.file.file_type == "contract"]
        matter_materials = [m for m in materials if m.file.file_type in {"matter_report", "meeting_minutes"}]
        if not contract_materials or not matter_materials:
            return []

        contract_text = "\n".join(block.text for m in contract_materials for block in m.blocks).strip()
        matter_text = "\n".join(block.text for m in matter_materials for block in m.blocks).strip()
        if not contract_text or not matter_text:
            return []

        ai_settings = self._load_ai_settings()
        if ai_settings is None:
            return [
                self._create_issue(
                    review_case,
                    issue_type="process_audit",
                    title="事项材料与合同内容范围未完成一致性复核",
                    risk_level="info",
                    description="已上传事项签报或会议纪要，但尚未配置 AI，无法完成审批事项与合同内容、范围的专业比对。",
                    suggestion="配置 AI 后重新审核，或由法务人工核对合同主体、内容、范围、金额和期限。",
                    evidence_text=None,
                )
            ]

        try:
            provider = OpenAICompatibleProvider(ai_settings)
            response_text = provider.chat(build_matter_consistency_prompt(contract_text, matter_text, instruction))
            payload = self._parse_ai_json_response(response_text)
        except Exception as exc:
            return [
                self._create_issue(
                    review_case,
                    issue_type="process_audit",
                    title="事项材料与合同内容范围一致性复核失败",
                    risk_level="info",
                    description=(
                        "系统未能完成事项签报/会议纪要与合同正文的 AI 一致性比对。"
                        f"{self._describe_ai_failure(exc)}"
                    ),
                    suggestion="请检查 AI 接口配置后重新审核，或由法务人工核对审批事项与合同内容、范围。",
                    evidence_text=None,
                )
            ]

        created: list[Issue] = []
        for item in payload.get("issues", []):
            original_text = item.get("original_text")
            evidence_sources = self._find_blocks(materials, original_text) if original_text else []
            issue = self._create_issue(
                review_case,
                issue_type="process_audit",
                title=str(item.get("title") or "审批事项与合同内容范围可能不一致"),
                risk_level=self._normalize_risk(str(item.get("risk_level") or "needs_review")),
                description=str(item.get("description") or ""),
                suggestion=str(item.get("suggestion") or ""),
                evidence_text=original_text,
                evidence_sources=evidence_sources,
            )
            issue.replacement_clause = item.get("replacement_clause")
            created.append(issue)
        return created

    def _create_ocr_gap_issues(
        self,
        review_case: ReviewCase,
        materials: list[MaterialText],
    ) -> list[Issue]:
        created: list[Issue] = []
        for material in materials:
            if material.file.file_type != "contract":
                continue
            if material.file.parse_status in {"needs_ocr", "ocr_failed"}:
                created.append(
                    self._create_issue(
                        review_case,
                        issue_type="contract_risk",
                        title="合同扫描件 OCR 未完成",
                        risk_level="medium",
                        description=(
                            f"文件 {material.file.file_name} 的 OCR 识别状态为 {material.file.parse_status}。"
                            "扫描件合同需要 OCR 识别后才能进行文本审查。"
                        ),
                        suggestion="请重新上传该文件，或联系技术人员检查 OCR 引擎配置。",
                        evidence_text=None,
                    )
                )
            elif not material.text.strip() and material.file.file_name.lower().endswith(
                (".png", ".jpg", ".jpeg", ".tif", ".tiff")
            ):
                created.append(
                    self._create_issue(
                        review_case,
                        issue_type="contract_risk",
                        title="合同扫描件 OCR 未完成",
                        risk_level="medium",
                        description=(
                            f"文件 {material.file.file_name} 为图片扫描件，未提取到可审查文本。"
                            "需要 OCR 识别后才能进行合同条款审查。"
                        ),
                        suggestion="请重新上传该文件，确保 OCR 引擎已正确配置。",
                        evidence_text=None,
                    )
                )
        return created

    def _create_ai_contract_issues(
        self,
        review_case: ReviewCase,
        materials: list[MaterialText],
        instruction: str | None,
    ) -> list[Issue]:
        contract_text = "\n".join(
            block.text for m in materials if m.file.file_type == "contract" for block in m.blocks
        ).strip()

        if not contract_text:
            return []

        ai_settings = self._load_ai_settings()
        if ai_settings is None:
            return [
                self._create_issue(
                    review_case,
                    issue_type="contract_risk",
                    title="未配置 AI 接口，跳过专业律师审查",
                    risk_level="info",
                    description="当前未配置 AI Base URL 和 API Key，无法调用第三方 AI 进行合同法律风险审查。",
                    suggestion="请在设置页面配置 AI 接口后，点击重新审核。",
                    evidence_text=None,
                )
            ]

        provider = OpenAICompatibleProvider(ai_settings)
        try:
            response_text = provider.chat(build_contract_review_prompt(contract_text, instruction))
            payload = self._parse_ai_json_response(response_text)
        except Exception as exc:
            return [
                self._create_issue(
                    review_case,
                    issue_type="contract_risk",
                    title="AI 合同审查调用失败",
                    risk_level="info",
                    description=(
                        "系统未能完成第三方 AI 合同审查。"
                        f"{self._describe_ai_failure(exc)}"
                    ),
                    suggestion="请检查 AI Base URL、API Key、模型名，并重新审核。",
                    evidence_text=None,
                )
            ]

        created: list[Issue] = []
        for item in payload.get("issues", []):
            issue = self._create_issue(
                review_case,
                issue_type="contract_risk",
                title=str(item.get("title") or "合同风险"),
                risk_level=self._normalize_risk(str(item.get("risk_level") or "info")),
                description=str(item.get("description") or ""),
                suggestion=str(item.get("suggestion") or ""),
                evidence_text=item.get("original_text"),
            )
            issue.replacement_clause = item.get("replacement_clause")
            created.append(issue)
        return created

    def _load_ai_settings(self) -> AiSettings | None:
        setting = self.session.get(AppSetting, "ai")
        if setting is None:
            return None
        try:
            values = dict(setting.value)
            values["api_key"] = decrypt_api_key(values.get("api_key", ""))
            return AiSettings(**values)
        except Exception:
            return None

    def _parse_ai_json_response(self, response_text: str) -> dict:
        cleaned = response_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
        payload = json.loads(cleaned)
        if not isinstance(payload, dict):
            raise ValueError("智能审查响应必须是 JSON 对象")
        return payload

    def _describe_ai_failure(self, error: Exception) -> str:
        if isinstance(error, httpx.ReadTimeout):
            return "模型响应超时，请增加智能审查接口的超时时间后重试。"
        if isinstance(error, httpx.HTTPStatusError):
            return f"接口返回 HTTP {error.response.status_code}，请检查接口地址、密钥和模型名称。"
        if isinstance(error, json.JSONDecodeError):
            return "模型返回内容不是有效 JSON，请检查模型是否支持结构化输出。"
        if isinstance(error, ValueError):
            return "模型未返回可解析的审查内容，请检查模型是否支持结构化输出或提高输出上限。"
        return "可能是接口配置、网络或模型返回格式异常。"

    def _extract_date_hit(self, materials: list[MaterialText], labels: list[str]) -> DateHit | None:
        for material in materials:
            for block in material.blocks or [MaterialBlock(text=material.text)]:
                hit = self._extract_date_from_text(block.text, labels, block)
                if hit:
                    return hit
        return self._extract_date_from_text("\n".join(material.text for material in materials), labels, None)

    def _extract_approval_date_hit(self, materials: list[MaterialText], labels: list[str]) -> DateHit | None:
        labeled_hit = self._extract_date_hit(materials, labels)
        if labeled_hit:
            return labeled_hit

        candidates: list[DateHit] = []
        for material in materials:
            for block in material.blocks or [MaterialBlock(text=material.text)]:
                for line in block.text.splitlines():
                    if not re.search(r"批准|审批通过|同意|签批", line):
                        continue
                    hit = self._extract_date_from_text(
                        line,
                        [""],
                        block,
                    )
                    if hit:
                        candidates.append(hit)
        return max(candidates, key=lambda candidate: candidate.value) if candidates else None

    def _extract_date_from_text(
        self,
        text: str,
        labels: list[str],
        source: MaterialBlock | None,
    ) -> DateHit | None:
        for label in labels:
            prefix = rf"{label}[^\d]*?" if label else r"[^\d]*?"
            match = re.search(rf"{prefix}(\d{{4}})[年/-](\d{{1,2}})[月/-](\d{{1,2}})", text)
            if match:
                year, month, day = map(int, match.groups())
                try:
                    return DateHit(value=date(year, month, day), label=label, source=source)
                except ValueError:
                    continue
        return None

    def _find_blocks(self, materials: list[MaterialText], text: str) -> list[MaterialBlock]:
        return [
            block
            for material in materials
            for block in material.blocks
            if text in block.text
        ]

    def _first_blocks(self, materials: list[MaterialText]) -> list[MaterialBlock]:
        return [material.blocks[0] for material in materials if material.blocks]

    def _extract_date(self, text: str, labels: list[str]) -> date | None:
        hit = self._extract_date_from_text(text, labels, None)
        if hit:
            return hit.value
        return None

    def _create_issue(
        self,
        review_case: ReviewCase,
        issue_type: str,
        title: str,
        risk_level: str,
        description: str,
        suggestion: str,
        evidence_text: str | None,
        evidence_sources: list[MaterialBlock | None] | None = None,
    ) -> Issue:
        issue = Issue(
            case_id=review_case.id,
            issue_type=issue_type,
            source="ai",
            risk_level=risk_level,
            title=title,
            description=description,
            suggestion=suggestion,
            status="pending",
            review_version=review_case.current_version,
        )
        self.session.add(issue)
        self.session.flush()
        source_refs = [source for source in evidence_sources or [] if source is not None]
        if source_refs:
            for source in source_refs:
                self.session.add(
                    EvidenceRef(
                        issue_id=issue.id,
                        file_id=source.file_id,
                        page_number=source.page_number,
                        ocr_block_id=source.ocr_block_id,
                        original_text=source.text,
                        bbox=source.bbox,
                        confidence=source.confidence or 0.9,
                    )
                )
        elif evidence_text:
            self.session.add(EvidenceRef(issue_id=issue.id, original_text=evidence_text, confidence=0.9))
        return issue

    def _normalize_risk(self, risk_level: str) -> str:
        normalized = risk_level.strip().lower()
        return normalized if normalized in {"high", "medium", "low", "info"} else "info"

    def _highest_risk(self, case_id: int, review_version: int | None = None) -> str | None:
        filters = [Issue.case_id == case_id]
        if review_version is not None:
            filters.append(Issue.review_version == review_version)
        levels = [
            issue.risk_level
            for issue in self.session.scalars(select(Issue).where(*filters)).all()
        ]
        for level in ["high", "medium", "low", "info"]:
            if level in levels:
                return level
        return None
