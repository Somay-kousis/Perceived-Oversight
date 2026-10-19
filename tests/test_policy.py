"""Tests for untrusted_policy across arms (neutral, stress, adaptive)."""

from pathlib import Path
from control_arena._control_agent import ControlAgent
from perceived_oversight.policy import (
    ADAPTIVE_ATTACK_PROMPT,
    ADAPTIVE_REMINDER_PROMPT,
    NEUTRAL_ATTACK_PROMPT,
    untrusted_policy,
)


def test_untrusted_policy_returns_control_agent_for_all_arms():
    for arm in ("neutral", "stress", "adaptive"):
        agent = untrusted_policy(arm)
        assert isinstance(agent, ControlAgent)


def test_adaptive_prompt_templates_contain_required_placeholders():
    prompt_text = ADAPTIVE_ATTACK_PROMPT.read_text()
    assert "{setting_description}" in prompt_text
    assert "{side_task_description}" in prompt_text

    formatted = prompt_text.format(
        setting_description="[TEST BASE SETTING]",
        side_task_description="[TEST SIDE TASK]",
    )
    assert "[TEST BASE SETTING]" in formatted
    assert "[TEST SIDE TASK]" in formatted
    assert "{" not in formatted and "}" not in formatted


def test_adaptive_reminder_prompt_formats_correctly():
    assert "{side_task_description}" in ADAPTIVE_REMINDER_PROMPT
    formatted = ADAPTIVE_REMINDER_PROMPT.format(side_task_description="[TEST SIDE TASK]")
    assert "[TEST SIDE TASK]" in formatted
    assert "{" not in formatted and "}" not in formatted
