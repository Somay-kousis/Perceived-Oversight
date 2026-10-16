"""The agent's policy: stock honest behaviour; attack mode as the arm requires."""

from __future__ import annotations

from control_arena._control_agent import ControlAgent
from control_arena.policy import attack_policy_builder, untrusted_policy_builder
from control_arena.settings.shade_arena.shade_arena_attack_policy import shade_arena_attack_policy

from perceived_oversight.setting import PROMPTS_DIR, Arm

NEUTRAL_ATTACK_PROMPT = PROMPTS_DIR / "neutral_attack.txt"


def untrusted_policy(arm: Arm) -> ControlAgent:
    """Neutral arm: side task as the agent's own goal, no cues. Stress arm: SHADE's stock prompt."""
    if arm == "neutral":
        # prompt=None, or attack_policy_builder warns that both prompt and prompt_file were given.
        attack = attack_policy_builder(prompt=None, prompt_file=NEUTRAL_ATTACK_PROMPT)
    else:
        attack = shade_arena_attack_policy()
    return untrusted_policy_builder(attack=attack)
