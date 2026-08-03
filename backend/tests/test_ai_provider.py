from app.schemas.settings import AiSettings
from app.services.ai_provider import (
    OpenAICompatibleProvider,
    build_contract_review_prompt,
    build_matter_consistency_prompt,
)


def test_contract_review_prompt_requires_structured_json():
    messages = build_contract_review_prompt("甲方不得解除合同。", focus="站在甲方角度")
    joined = "\n".join(message["content"] for message in messages)
    assert "专业律师" in joined
    assert "JSON" in joined
    assert "风险等级" in joined
    assert "甲方不得解除合同" in joined
    assert "不审查 OA 签批" in joined


def test_matter_consistency_prompt_contains_both_materials():
    messages = build_matter_consistency_prompt(
        "合同名称：服务器采购\n合同范围：供货并安装",
        "事项签报：同意采购服务器，范围为设备供货",
    )
    joined = "\n".join(message["content"] for message in messages)
    assert "合同正文" in joined
    assert "事项签报或会议纪要" in joined
    assert "内容和范围" in joined
    assert "服务器采购" in joined


def test_provider_uses_bearer_auth_header(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("app.services.ai_provider.httpx.Client", FakeClient)
    provider = OpenAICompatibleProvider(
        AiSettings(
            base_url="https://api.example.com/v1",
            api_key="sk-test-key",
            model="test-model",
        )
    )

    assert provider.chat([{"role": "user", "content": "hello"}]) == "ok"
    assert captured["url"] == "https://api.example.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-test-key"
    assert captured["json"]["max_tokens"] == 8192
    assert captured["json"]["response_format"] == {"type": "json_object"}
