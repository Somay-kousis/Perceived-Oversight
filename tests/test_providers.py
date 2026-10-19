"""Bedrock provider extension: reasoning for models Inspect's Bedrock provider does not configure.

Found 2026-10-19: DeepSeek V3.2 on Bedrock returns a reasoning block only when the request carries
`reasoning_effort` (tiny live calls), and Inspect's Bedrock provider forwards it only for gpt-oss,
Claude and Nova. Without it U thinks out loud in visible text and the reasoning vault stays empty.
"""

import pytest
from inspect_ai.model import ContentReasoning, ContentText, GenerateConfig, get_model

from perceived_oversight import budget
from perceived_oversight.providers import PROVIDER, split_leaked_answer

DEEPSEEK = f"{PROVIDER}/deepseek.v3.2"


def _api(model: str):
    return get_model(model).api


def test_deepseek_gets_reasoning_effort_from_effort():
    api = _api(DEEPSEEK)
    assert api.reasoning_config(GenerateConfig(effort="high")) == {"reasoning_effort": "high"}


def test_deepseek_gets_reasoning_effort_from_reasoning_effort():
    api = _api(DEEPSEEK)
    assert api.reasoning_config(GenerateConfig(reasoning_effort="low")) == {"reasoning_effort": "low"}


def test_kimi_gets_reasoning_effort_too():
    """2026-10-19: Kimi K3 thinks at max by default (Moonshot docs); pinning it puts the setting
    in every request log. Bedrock accepted the field in probes."""
    api = _api(f"{PROVIDER}/us.moonshotai.kimi-k3")
    assert api.reasoning_config(GenerateConfig(effort="max")) == {"reasoning_effort": "max"}


def test_no_effort_sends_nothing():
    assert _api(DEEPSEEK).reasoning_config(GenerateConfig()) == {}


@pytest.mark.parametrize("model", ["openai.gpt-oss-120b-1:0", "amazon.nova-pro-v1:0"])
def test_other_models_behave_as_stock_bedrock(model):
    ours = _api(f"{PROVIDER}/{model}")
    stock = _api(f"bedrock/{model}")
    config = GenerateConfig(reasoning_effort="medium")
    assert ours.reasoning_config(config) == stock.reasoning_config(config)


def test_unknown_non_deepseek_model_gets_nothing_extra():
    assert _api(f"{PROVIDER}/qwen.qwen3-32b-v1:0").reasoning_config(GenerateConfig(effort="high")) == {}


# Found 2026-10-19 (live two-turn probe, 1 of 2 tries): DeepSeek sometimes closes its thinking with
# a literal "</thinking>" inside the reasoning block and writes the answer there too, so the
# visible reply is empty. The part after the tag is the answer and moves to a text block.


def test_answer_inside_reasoning_after_closing_tag_moves_to_text():
    content = [ContentReasoning(reasoning="I have 40.75. I should tell the user.</thinking>The result is 40.75.")]
    out = split_leaked_answer(content)
    assert [c.type for c in out] == ["reasoning", "text"]
    assert out[0].reasoning == "I have 40.75. I should tell the user."
    assert out[1].text == "The result is 40.75."


def test_leaked_answer_goes_before_an_existing_text_block():
    content = [ContentReasoning(reasoning="plan</think>Sure."), ContentText(text="More.")]
    out = split_leaked_answer(content)
    assert [(c.type, getattr(c, "text", None)) for c in out][1:] == [("text", "Sure."), ("text", "More.")]


def test_reasoning_without_closing_tag_is_unchanged():
    content = [ContentReasoning(reasoning="just thinking"), ContentText(text="Answer.")]
    assert split_leaked_answer(content) == content


def test_nothing_after_the_tag_leaves_no_empty_text_block():
    out = split_leaked_answer([ContentReasoning(reasoning="done thinking</thinking>  ")])
    assert [c.type for c in out] == ["reasoning"] and out[0].reasoning == "done thinking"


def test_config_runs_kimi_at_max_with_a_deliberately_weak_monitor():
    """2026-10-19: U Kimi K3 at max (AA 43.6); live monitor gpt-oss-120b (AA 12), a large
    capability gap, after Claude Haiku 5.5 (AA 29.5) stopped every attack (C0 safety 1.0). Haiku 5.5
    stays priced for a replay-only stronger-monitor comparison."""
    kimi = f"{PROVIDER}/us.moonshotai.kimi-k3"
    settings = budget.load_settings()
    assert settings.roles.untrusted == kimi
    assert settings.effort[kimi] == "max" and kimi in settings.prices
    assert settings.roles.trusted == "bedrock/openai.gpt-oss-120b-1:0"
    assert "anthropic/claude-haiku-5-5" in settings.prices  # kept for replay


def test_config_keeps_deepseek_through_the_extension_with_reasoning_on():
    settings = budget.load_settings()
    # high: live probe 2026-10-19, only high returns a reasoning block (low and medium return none)
    assert settings.effort[DEEPSEEK] == "high"
    assert DEEPSEEK in settings.prices
    assert budget.generate_config(settings, DEEPSEEK).effort == "high"
