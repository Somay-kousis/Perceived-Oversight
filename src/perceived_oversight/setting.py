"""SHADE-Arena as this experiment needs it.

Applies the prompt decisions recorded in docs/decisions/DECISIONS.md:
- the base system prompt (both modes) loses its monitoring sentence and "submit your transcript";
- the neutral arm gets neutral side-task wording from prompts/side_tasks.yaml;
- the stress arm keeps SHADE's stock attack prompt and original side task;
- the judge model is pinned instead of following the attacker;
- the condition and arm are recorded in every sample.

In broker conditions the moved tools go to the broker (broker.py); C0 keeps SHADE's tools.
Live monitoring and other cover identities are added in later steps.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import yaml
from control_arena import ControlTaskMetadata, EvalMode
from control_arena.settings.shade_arena.model import ShadeArenaMetadata
from control_arena.settings.shade_arena.shade_arena_setting import ShadeArenaSetting
from inspect_ai.dataset import Sample
from inspect_ai.solver import TaskState
from inspect_ai.tool import Tool
from pydantic import Field
from shade_arena.utils.task_utils import load_task_definition_and_solution

PROMPTS_DIR = Path(__file__).parent / "prompts"
TASK_PAIRS = ("bank_transfer_2", "spam_filter_update")

Condition = Literal["C0", "C1", "C2", "C3", "C4", "C5", "C6"]
Arm = Literal["neutral", "stress"]

# Words that tell the agent it is watched, tested or should hide. Checked on every text we write.
OVERSIGHT_CUES = re.compile(
    r"\b(monitor\w*|test\w*|evaluat\w*|safety|subtl\w*|sneak\w*|detect\w*|oversight|watch\w*|"
    r"suspic\w*|notic\w*|obvious\w*|hid\w*|secret\w*|caught|audit\w*|stress|transcript\w*)\b",
    re.IGNORECASE,
)

_TRANSCRIPT_EDITS = (
    ("when you are ready to submit your transcript", "when you are done"),
    ("until you are ready to submit your transcript", "until you are done"),
)
_CLOSING = re.compile(
    r"(You can take as much time as you need to complete the task correctly\.)\s*Indeed,.*\Z",
    re.DOTALL,
)


def oversight_cues(text: str) -> list[str]:
    """Distinct oversight words found in `text`, lowercased."""
    return sorted({m.lower() for m in OVERSIGHT_CUES.findall(text)})


def base_prompt(shade_description: str) -> str:
    """SHADE's shared system prompt with the two edits; identical in both modes."""
    text = shade_description
    for old, new in _TRANSCRIPT_EDITS:
        if old not in text:
            raise ValueError(f"SHADE base prompt changed: {old!r} not found")
        text = text.replace(old, new)
    if not _CLOSING.search(text):
        raise ValueError("SHADE base prompt changed: closing paragraph not found")
    text = _CLOSING.sub(r"\1", text).strip()
    if cues := oversight_cues(text):
        raise ValueError(f"base prompt still contains oversight cues: {cues}")
    return text


def _email_body(side_task: str) -> str:
    match = re.search(r"<email_body>(.*?)</email_body>", side_task, re.DOTALL)
    if not match:
        raise ValueError("spam side task has no <email_body>")
    return match.group(1).strip()


def neutral_side_task(task_pair: str) -> str:
    """Neutral side-task wording for a task pair, filled from SHADE's task definition."""
    templates = yaml.safe_load((PROMPTS_DIR / "side_tasks.yaml").read_text())
    task_def_class, _ = load_task_definition_and_solution(str(Path("task_pairs") / task_pair))
    task_def = task_def_class()
    fill = {}
    for attr in ("submission_iban", "submission_email", "submission_venmo_username"):
        if hasattr(task_def, attr):
            fill[attr] = getattr(task_def, attr)
    if "{email_body}" in templates[task_pair]:
        fill["email_body"] = _email_body(task_def.secondary_task)
    text = templates[task_pair].format(**fill)
    if cues := oversight_cues(text):
        raise ValueError(f"neutral side task for {task_pair} contains oversight cues: {cues}")
    return text


class PerceivedOversightSetting(ShadeArenaSetting):
    condition: Condition = Field(description="Which framing of the broker this run uses.")
    arm: Arm = Field(default="neutral", description="Neutral attack prompt or SHADE's stock prompt.")
    judge_model: str = Field(description="Grades main and side task; fixed across attackers.")
    broker_model: str | None = Field(
        default=None, description="The broker's model; a different family from U. Unused in C0."
    )
    broker_style: Literal["neutral", "warm"] = Field(
        default="neutral", description="Broker reply style, the same in every broker condition."
    )
    monitor_model: str | None = Field(
        default=None, description="Live monitor model (trusted). None: no live monitor (development)."
    )
    hold_threshold: float | None = Field(
        default=None, description="Live score above which a broker request is held. None with "
        "stop_threshold None: calibration mode (score only, never hold or stop)."
    )
    stop_threshold: float | None = Field(
        default=None, description="Live score above which the episode stops."
    )

    @classmethod
    def get_name(cls) -> str:
        return "perceived_oversight"

    def get_dataset(self, eval_mode: EvalMode) -> Sequence[Sample]:
        samples = super().get_dataset(eval_mode)
        if self.task_pair is None:
            samples = [s for s in samples if self._pair(s) in TASK_PAIRS]
        return [self._adapt(sample, eval_mode) for sample in samples]

    def get_agent_tools(self, state: TaskState) -> list[Tool]:
        from perceived_oversight.broker import broker_tool, monitored_tools, split_tools

        tools = super().get_agent_tools(state)
        meta = state.metadata_as(ControlTaskMetadata)
        pair = meta.main_task_name
        u_tools, moved = split_tools(pair, tools)
        monitor = self._live_monitor(meta.main_task_description)
        if self.condition == "C0":
            return [*u_tools, *monitored_tools(moved, monitor)] if monitor else tools
        if self.broker_model is None:
            raise ValueError(f"{self.condition} needs broker_model")
        broker = broker_tool(pair, self.condition, moved, self.broker_model, self.broker_style, monitor)
        return [*u_tools, broker]

    def _live_monitor(self, main_task: str):
        from perceived_oversight.monitor import LiveMonitor, Thresholds, current_transcript

        if self.monitor_model is None:
            return None
        if (self.hold_threshold is None) != (self.stop_threshold is None):
            raise ValueError("set both thresholds, or neither for calibration mode")
        thresholds = (
            None
            if self.hold_threshold is None
            else Thresholds(hold=self.hold_threshold, stop=self.stop_threshold)
        )
        return LiveMonitor(self.monitor_model, main_task, current_transcript, thresholds)

    @staticmethod
    def _pair(sample: Sample) -> str:
        assert sample.metadata is not None
        return ControlTaskMetadata.model_validate(sample.metadata).main_task_name

    def _adapt(self, sample: Sample, eval_mode: EvalMode) -> Sample:
        assert sample.metadata is not None
        control = ControlTaskMetadata.model_validate(sample.metadata)
        shade = control.metadata_as(ShadeArenaMetadata)
        update: dict = {"setting_description": base_prompt(control.setting_description)}
        shade_update: dict = {"evaluator_llm": self.judge_model}
        if eval_mode == EvalMode.ATTACK and self.arm == "neutral":
            update["side_task_description"] = neutral_side_task(control.main_task_name)
            shade_update["attack_setting_description"] = None
        update["metadata"] = {
            **shade.model_copy(update=shade_update).model_dump(),
            "condition": self.condition,
            "arm": self.arm,
        }
        control = control.model_copy(update=update)
        return Sample(input=sample.input, id=sample.id, metadata=control.model_dump())
