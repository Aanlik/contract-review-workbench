from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
from app.services.ai_provider import OpenAICompatibleProvider, build_contract_review_prompt


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


class ReviewRunService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def reanalyze(self, case_id: int, instruction: str | None = None) -> ReviewCase:
        review_case = self.session.get(ReviewCase, case_id)
        if review_case is None:
            raise ValueError("Review case not found")

        review_case.current_version += 1
        review_case.status = "completed"
        self.session.add(
            ReviewVersion(
                case_id=case_id,
                version_number=review_case.current_version,
                trigger="reanalyze",
                review_request=instruction,
                note="基础规则审计版本",
            )
        )

        materials = self._load_materials(case_id)
        created = self._create_process_audit_issues(review_case, materials)
        created.extend(self._create_ocr_gap_issues(review_case, materials))
        created.extend(self._create_ai_contract_issues(review_case, materials, instruction))
        if not created:
            created.append(
                self._create_issue(
                    review_case,
                    issue_type="contract_risk",
                    title="需要法务人工复核合同条款",
                    risk_level="info",
                    description="系统已完成基础读取，但未发现可确定的日期或盖章异常。建议继续配置 AI 后执行专业律师视角审查。",
                    suggestion="配置 AI 后点击重新审核，或使用人工标记补充重点条款。",
                    evidence_text=None,
                )
            )

        review_case.issue_count = (
            self.session.scalar(select(func.count(Issue.id)).where(Issue.case_id == case_id))
            or len(created)
        )
        review_case.highest_risk_level = self._highest_risk(case_id)
        self.session.commit()
        self.session.refresh(review_case)
        return review_case

    def _load_materials(self, case_id: int) -> list[MaterialText]:
        files = self.session.scalars(
            select(UploadedFile).where(UploadedFile.case_id == case_id).order_by(UploadedFile.id.asc())
        ).all()
        return [self._material(file) for file in files]

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
                    return "\n".join(page.get_text() for page in document)
            except Exception:
                return ""
        return ""

    def _create_process_audit_issues(
        self,
        review_case: ReviewCase,
        materials: list[MaterialText],
    ) -> list[Issue]:
        contract_materials = [item for item in materials if item.file.file_type == "contract"]
        flow_materials = [item for item in materials if item.file.file_type != "contract"]
        contract_text = "\n".join(item.text for item in contract_materials)
        contract_date = self._extract_date_hit(contract_materials, ["合同签订日期", "签订日期", "签署日期"])
        legal_review_date = self._extract_date_hit(flow_materials, ["法务审核", "法审", "法律审核"])
        approval_date = self._extract_date_hit(flow_materials, ["审批通过", "签批", "批准"])
        flow_text = "\n".join(item.text for item in flow_materials)
        created: list[Issue] = []

        if contract_date and legal_review_date and legal_review_date.value > contract_date.value:
            created.append(
                self._create_issue(
                    review_case,
                    issue_type="process_audit",
                    title="法审日期晚于合同签订日期",
                    risk_level="high",
                    description="识别到法务审核日期晚于合同签订日期，存在先签署后法审的流程合规风险。",
                    suggestion="请核对合同实际签署日期和法审记录，如属实应补充说明并重新履行法审前置流程。",
                    evidence_text=f"合同签订日期：{contract_date.value.isoformat()}；法审日期：{legal_review_date.value.isoformat()}",
                    evidence_sources=[contract_date.source, legal_review_date.source],
                )
            )

        if contract_date and approval_date and approval_date.value > contract_date.value:
            created.append(
                self._create_issue(
                    review_case,
                    issue_type="process_audit",
                    title="合同签订日期早于审批通过日期",
                    risk_level="high",
                    description="识别到合同签订日期早于审批通过日期，存在先签后批的内控流程风险。",
                    suggestion="请核对审批通过节点和签署页日期，如属实应提交流程异常说明并补齐审批依据。",
                    evidence_text=f"合同签订日期：{contract_date.value.isoformat()}；审批通过日期：{approval_date.value.isoformat()}",
                    evidence_sources=[contract_date.source, approval_date.source],
                )
            )

        if contract_date and flow_text.strip() and not legal_review_date:
            created.append(
                self._create_issue(
                    review_case,
                    issue_type="process_audit",
                    title="未识别到法务审核记录",
                    risk_level="medium",
                    description="已识别到合同签订日期和流程材料，但未抽取到明确法务审核日期或法审节点，存在法审依据缺失风险。",
                    suggestion="请核对 OA 签报、法审意见或审批单，补充上传包含法审节点的材料，或由法务人工确认无需法审的制度依据。",
                    evidence_text="流程材料未识别到法务审核记录",
                    evidence_sources=self._first_blocks(flow_materials),
                )
            )

        if contract_date and flow_text.strip() and not approval_date:
            created.append(
                self._create_issue(
                    review_case,
                    issue_type="process_audit",
                    title="未识别到最终审批通过记录",
                    risk_level="high",
                    description="已识别到合同签订日期和流程材料，但未抽取到明确审批通过或签批完成节点，存在未完成审批即签署的内控风险。",
                    suggestion="请核对最终审批节点、签批单或会议决议，确认合同签署前审批已完成。",
                    evidence_text="流程材料未识别到最终审批通过记录",
                    evidence_sources=self._first_blocks(flow_materials),
                )
            )

        if "乙方盖章：缺失" in contract_text or "乙方盖章缺失" in contract_text:
            created.append(
                self._create_issue(
                    review_case,
                    issue_type="process_audit",
                    title="疑似合同盖章不齐全",
                    risk_level="high",
                    description="合同文本或签署页信息显示乙方盖章缺失，可能影响合同成立、证明力或后续履约追责。",
                    suggestion="请人工核对合同签章页，确认双方签字盖章是否完整。",
                    evidence_text="乙方盖章：缺失",
                    evidence_sources=self._find_blocks(contract_materials, "乙方盖章"),
                )
            )

        return created

    def _create_ocr_gap_issues(
        self,
        review_case: ReviewCase,
        materials: list[MaterialText],
    ) -> list[Issue]:
        created: list[Issue] = []
        for material in materials:
            if material.file.file_type == "contract" and not material.text.strip():
                created.append(
                    self._create_issue(
                        review_case,
                        issue_type="contract_risk",
                        title="合同扫描件 OCR 未完成",
                        risk_level="info",
                        description="该合同文件未能抽取到可审查文本，可能是纯图片扫描件且本地 OCR 引擎尚未安装或未完成识别。",
                        suggestion="请安装并启用 PaddleOCR/RapidOCR，或先上传可复制文字的 PDF/TXT 版本，也可以使用人工标记补充关键条款。",
                        evidence_text=material.file.file_name,
                    )
                )
        return created

    def _create_ai_contract_issues(
        self,
        review_case: ReviewCase,
        materials: list[MaterialText],
        instruction: str | None,
    ) -> list[Issue]:
        setting = self.session.get(AppSetting, "ai")
        if setting is None:
            return []

        contract_text = "\n".join(item.text for item in materials if item.file.file_type == "contract")
        if not contract_text.strip():
            return []

        provider = OpenAICompatibleProvider(AiSettings(**setting.value))
        try:
            response_text = provider.chat(build_contract_review_prompt(contract_text, instruction))
            payload = json.loads(response_text)
        except Exception:
            return [
                self._create_issue(
                    review_case,
                    issue_type="contract_risk",
                    title="AI 合同审查调用失败",
                    risk_level="info",
                    description="系统未能完成第三方 AI 合同审查，可能是接口配置、网络或模型返回格式异常。",
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

    def _extract_date_hit(self, materials: list[MaterialText], labels: list[str]) -> DateHit | None:
        for material in materials:
            for block in material.blocks or [MaterialBlock(text=material.text)]:
                hit = self._extract_date_from_text(block.text, labels, block)
                if hit:
                    return hit
        return self._extract_date_from_text("\n".join(material.text for material in materials), labels, None)

    def _extract_date_from_text(
        self,
        text: str,
        labels: list[str],
        source: MaterialBlock | None,
    ) -> DateHit | None:
        for label in labels:
            match = re.search(rf"{label}[^\d]*(\d{{4}})[年/-](\d{{1,2}})[月/-](\d{{1,2}})", text)
            if match:
                year, month, day = map(int, match.groups())
                return DateHit(value=date(year, month, day), label=label, source=source)
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

    def _highest_risk(self, case_id: int) -> str | None:
        levels = [
            issue.risk_level
            for issue in self.session.scalars(select(Issue).where(Issue.case_id == case_id)).all()
        ]
        for level in ["high", "medium", "low", "info"]:
            if level in levels:
                return level
        return None
