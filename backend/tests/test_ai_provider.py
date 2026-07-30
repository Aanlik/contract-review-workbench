from app.services.ai_provider import build_contract_review_prompt


def test_contract_review_prompt_requires_structured_json():
    messages = build_contract_review_prompt("甲方不得解除合同。", focus="站在甲方角度")
    joined = "\n".join(message["content"] for message in messages)
    assert "专业律师" in joined
    assert "JSON" in joined
    assert "风险等级" in joined
    assert "甲方不得解除合同" in joined
