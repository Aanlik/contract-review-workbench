from typing import Literal, TypedDict

import httpx

from app.schemas.settings import AiSettings


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class OpenAICompatibleProvider:
    def __init__(self, settings: AiSettings) -> None:
        self.settings = settings

    def chat(self, messages: list[ChatMessage], *, max_retries: int = 3) -> str:
        url = f"{self.settings.base_url.rstrip('/')}/chat/completions"
        headers = self._headers()
        payload = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": self.settings.temperature,
        }
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=self.settings.timeout_seconds) as client:
                    response = client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                return data["choices"][0]["message"]["content"]
            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                last_exc = exc
                if attempt < max_retries - 1:
                    import time
                    time.sleep(min(2 ** attempt, 8))
        raise last_exc  # type: ignore[misc]

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.api_key}"}


def build_contract_review_prompt(contract_text: str, focus: str | None = None) -> list[ChatMessage]:
    focus_text = focus or "全面审查合同法律风险、合规风险和商业履约风险"
    system = (
        "你是一名专业律师，负责审查中文商务合同。"
        "你的结论必须审慎、可追溯，并提醒需要人工复核的不确定事项。"
    )
    user = f"""
请基于以下审核重点审查合同：{focus_text}

请只返回 JSON，不要返回 Markdown。JSON 结构必须为：
{{
  "issues": [
    {{
      "title": "问题标题",
      "risk_level": "high|medium|low|info",
      "description": "问题说明",
      "original_text": "原文片段",
      "suggestion": "修改建议",
      "replacement_clause": "可选替代条款",
      "review_note": "法务审查提示",
      "requires_human_review": true
    }}
  ]
}}

字段要求：
- 风险等级必须根据对我方不利程度、可执行性、合规影响判断。
- 原文片段必须来自合同文本，不能编造。
- 修改建议要让业务人员能理解，也要便于法务继续修改。

合同文本：
{contract_text}
""".strip()
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_matter_consistency_prompt(
    contract_text: str,
    matter_text: str,
    focus: str | None = None,
) -> list[ChatMessage]:
    focus_text = focus or "核对审批同意的事项与拟签订合同的主体、内容和范围、金额及履约边界"
    system = (
        "你是一名专业律师，负责审查中文商务合同的流程合规性。"
        "你要把事项审批材料当作授权边界，把合同正文当作拟签署内容，谨慎识别超出审批范围的变化。"
    )
    user = f"""
请基于以下审核重点，核对事项签报或会议纪要与合同正文是否一致：{focus_text}

请只返回 JSON，不要返回 Markdown。JSON 结构必须为：
{{
  "issues": [
    {{
      "title": "问题标题",
      "risk_level": "high|medium|low|info",
      "description": "问题说明",
      "original_text": "来自合同或事项材料的原文片段",
      "suggestion": "修改或补充审批建议",
      "replacement_clause": "可选替代条款",
      "review_note": "法务审查提示",
      "requires_human_review": true
    }}
  ]
}}

判断要求：
- 重点比较审批同意事项与合同的主体、标的、服务内容、合同范围、金额、期限和付款边界。
- 仅当存在实质差异、审批授权不足或无法确认时列出问题；一致时返回空 issues。
- 原文片段必须来自下方材料，不能编造。
- 不能仅因为材料是扫描件或表述简略就直接认定不一致，应提示人工复核。

合同正文：
{contract_text}

事项签报或会议纪要：
{matter_text}
""".strip()
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
