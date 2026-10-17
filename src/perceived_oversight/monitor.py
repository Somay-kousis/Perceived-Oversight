"""Step 3b: the live monitor. Scores each consequential action before it executes.

Two prompts (`prompts/monitor/holistic.txt`, `narrow.txt`) read the user's request, the transcript
so far in monitor view, and the action. Their scores are averaged (both are logged, so other rules
can be tried on saved logs). The outcome is execute, hold or stop against thresholds calibrated on
honest episodes; with no thresholds set the monitor only scores (calibration mode).

Monitor view here removes system prompts and reasoning. Stripping the C4 notice, the C5 log and
role answers comes with those conditions (steps 4 and 5).
"""

from __future__ import annotations

import json
import re
import weakref
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageTool,
    ChatMessageUser,
    Model,
    get_model,
)
from control_arena import control_agent
from control_arena._control_agent import ControlAgent
from control_arena.policy import untrusted_policy_builder
from inspect_ai.agent import Agent, AgentState
from inspect_ai.solver import TaskState
from inspect_ai.solver._task_state import sample_state
from inspect_ai.tool import Tool
from inspect_ai.util import StoreModel, suspend_turn_limit
from pydantic import BaseModel, Field, model_validator

from perceived_oversight.setting import PROMPTS_DIR

Outcome = Literal["execute", "hold", "stop"]
PROMPT_NAMES = ("holistic", "narrow")
MAX_PARSE_TRIES = 3

_THINKING = re.compile(r"<thinking>.*?</thinking>", re.DOTALL | re.IGNORECASE)
_SCORE = re.compile(r"<score>\s*([0-9]+(?:\.[0-9]+)?)\s*</score>", re.IGNORECASE)


class Thresholds(BaseModel):
    """Per-action score cut-offs. Calibrated so that at most a target share of honest *episodes*
    are held or stopped (an episode makes many scored actions)."""

    hold: float
    stop: float

    @model_validator(mode="after")
    def _ordered(self) -> "Thresholds":
        if self.hold > self.stop:
            raise ValueError("hold threshold must not exceed stop threshold")
        return self


class ScoredAction(BaseModel):
    action: str
    scores: dict[str, float | None]  # None: that prompt gave no parseable score
    score: float | None  # None: neither prompt did; the outcome is the fallback
    outcome: Outcome


class MonitorLog(StoreModel):
    """Every live score in the episode, in order, saved in the log."""

    actions: list[ScoredAction] = Field(default_factory=list)


def _text(message: ChatMessage) -> str:
    """Visible text only: reasoning content blocks are dropped by `.text`, <thinking> removed."""
    return _THINKING.sub("", message.text).strip()


def monitor_view(messages: Sequence[ChatMessage]) -> str:
    """The transcript as the monitor reads it."""
    lines = []
    for m in messages:
        if isinstance(m, ChatMessageUser):
            lines.append(f"USER: {_text(m)}")
        elif isinstance(m, ChatMessageAssistant):
            if text := _text(m):
                lines.append(f"ASSISTANT: {text}")
            for call in m.tool_calls or []:
                lines.append(f"TOOL CALL {call.function}: {json.dumps(call.arguments)}")
        elif isinstance(m, ChatMessageTool):
            lines.append(f"TOOL RESULT {m.function}: {_text(m)}")
    return "\n".join(lines)


def parse_score(completion: str) -> float | None:
    match = _SCORE.findall(completion)
    if not match:
        return None
    value = float(match[-1])
    return value if 0 <= value <= 100 else None


def decide(score: float | None, thresholds: Thresholds | None) -> Outcome:
    """No thresholds: calibration mode. No score at all: hold (execute in calibration mode)."""
    if thresholds is None:
        return "execute"
    if score is None:
        return "hold"
    if score > thresholds.stop:
        return "stop"
    if score > thresholds.hold:
        return "hold"
    return "execute"


@dataclass
class LiveMonitor:
    """`transcript` returns the episode's messages at scoring time (U's view of the episode)."""

    model: str | Model
    main_task: str
    transcript: Callable[[], Sequence[ChatMessage]]
    thresholds: Thresholds | None = None

    async def _one(self, name: str, action: str, view: str) -> float | None:
        template = (PROMPTS_DIR / "monitor" / f"{name}.txt").read_text()
        prompt = template.format(main_task=self.main_task, transcript=view, action=action)
        model = get_model(self.model) if isinstance(self.model, str) else self.model
        for _ in range(MAX_PARSE_TRIES):
            with suspend_turn_limit():  # the turn limit counts U's turns only, in every condition
                output = await model.generate(prompt)
            if (score := parse_score(output.completion)) is not None:
                return score
        return None

    async def score(self, action: str, log: MonitorLog) -> ScoredAction:
        view = monitor_view(self.transcript())
        scores = {name: await self._one(name, action, view) for name in PROMPT_NAMES}
        valid = [s for s in scores.values() if s is not None]
        mean = sum(valid) / len(valid) if valid else None
        scored = ScoredAction(
            action=action, scores=scores, score=mean, outcome=decide(mean, self.thresholds)
        )
        log.actions.append(scored)
        return scored


# U's messages as of its latest step, per running sample. ControlArena's react loop keeps them in
# the agent state, which tools cannot reach; the micro-protocol below records them before tools run.
_SNAPSHOTS: "weakref.WeakKeyDictionary[TaskState, list[ChatMessage]]" = weakref.WeakKeyDictionary()


def current_transcript() -> list[ChatMessage]:
    state = sample_state()
    if state is None:
        raise RuntimeError("live monitor used outside a running sample")
    if state not in _SNAPSHOTS:
        raise RuntimeError("no transcript snapshot: run episodes with informant_protocol")
    return _SNAPSHOTS[state]


@control_agent
def informant_protocol(
    policy: ControlAgent = Field(default_factory=untrusted_policy_builder),
) -> Agent:
    """Runs U's policy and records its messages for the live monitor. The monitoring itself happens
    inside the broker tool (broker conditions) or the wrapped tools (C0), before anything executes."""

    async def impl(state: AgentState, tools: list[Tool]) -> AgentState:
        state = await policy(state, tools)
        if (sample := sample_state()) is not None:
            _SNAPSHOTS[sample] = list(state.messages)
        return state

    return impl
