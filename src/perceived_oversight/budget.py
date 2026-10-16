"""Spend guardrails for every Perceived-Oversight run.

All limits come from config/budget.yaml. Call `configure()` before importing anything from
control_arena: ControlArena reads UNTRUSTED_MODEL / TRUSTED_MODEL and their *_CONFIG_PATH
files from the environment at import time, and otherwise silently falls back to its own
defaults (claude-sonnet-4-6 / gpt-5.4-mini). The SHADE-Arena evaluator also takes its
model from UNTRUSTED_MODEL, so the environment has to agree with the roles we pass in.

Inspect caps cost per episode (`cost_limit`) but has no cap across a whole run.
`preflight()` supplies that: it refuses a run whose worst case (episodes x episode cap x
multiplier), added to what the logs show has already been spent, would exceed the phase
cap or the hard ceiling.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import yaml
from inspect_ai.log import list_eval_logs, read_eval_log
from inspect_ai.model import (
    GenerateConfig,
    ModelCost,
    ModelInfo,
    ModelUsage,
    get_model_info,
    set_model_cost,
    set_model_info,
)
from pydantic import BaseModel, model_validator

if TYPE_CHECKING:
    from control_arena.eval import ControlEvalConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "budget.yaml"

_ROLE_ENV = (
    ("untrusted", "UNTRUSTED_MODEL", "UNTRUSTED_CONFIG_PATH"),
    ("trusted", "TRUSTED_MODEL", "TRUSTED_CONFIG_PATH"),
)
_FREE = {"input": 0.0, "output": 0.0, "input_cache_write": 0.0, "input_cache_read": 0.0}


class BudgetExceededError(RuntimeError):
    """A run could spend more than the budget allows."""


class Price(BaseModel):
    input: float
    input_cache_write: float
    input_cache_read: float
    output: float


class BudgetCaps(BaseModel):
    total_credits_usd: float
    hard_ceiling_usd: float
    phase_cap_usd: float
    logs_dir: str
    worst_case_multiplier: float


class Roles(BaseModel):
    untrusted: str
    trusted: str


class Limits(BaseModel):
    turn_limit: int
    max_steps: int
    token_limit: int
    working_limit_s: int
    time_limit_s: int


class GenerateDefaults(BaseModel):
    max_tokens: int
    max_retries: int
    timeout_s: int
    max_connections: int
    cache_prompt: bool


class RunDefaults(BaseModel):
    max_samples: int
    max_tasks: int
    retry_on_error: int
    fail_on_error: bool


class BudgetSettings(BaseModel):
    budget: BudgetCaps
    roles: Roles
    prices: dict[str, Price]
    episode_cost_limit_usd: dict[str, float]
    effort: dict[str, Literal["low", "medium", "high", "xhigh", "max"] | None]
    limits: Limits
    generate: GenerateDefaults
    run: RunDefaults

    @model_validator(mode="after")
    def _check(self) -> BudgetSettings:
        caps = self.budget
        if not caps.phase_cap_usd <= caps.hard_ceiling_usd <= caps.total_credits_usd:
            raise ValueError("need phase_cap_usd <= hard_ceiling_usd <= total_credits_usd")
        if caps.worst_case_multiplier < 1:
            raise ValueError("worst_case_multiplier must be >= 1")
        for role, model in self.roles.model_dump().items():
            if model not in self.prices:
                raise ValueError(f"no price for {role} model {model!r}")
        if self.roles.untrusted not in self.episode_cost_limit_usd:
            raise ValueError(f"no episode cost limit for {self.roles.untrusted!r}")
        return self

    @property
    def logs_dir(self) -> Path:
        return REPO_ROOT / self.budget.logs_dir

    @property
    def episode_cost_limit(self) -> float:
        """Per-episode cap in USD; it covers every model call in the episode."""
        return self.episode_cost_limit_usd[self.roles.untrusted]


def load_settings(
    path: Path = DEFAULT_CONFIG_PATH, roles: dict[str, str] | None = None
) -> BudgetSettings:
    """Load and validate budget.yaml, optionally overriding the model for some roles."""
    data = yaml.safe_load(path.read_text())
    if roles:
        data["roles"] = {**data["roles"], **roles}
    return BudgetSettings.model_validate(data)


def generate_config(settings: BudgetSettings, model: str) -> GenerateConfig:
    """Per-call limits applied to every model role."""
    gen = settings.generate
    return GenerateConfig(
        max_tokens=gen.max_tokens,
        max_retries=gen.max_retries,
        timeout=gen.timeout_s,
        max_connections=gen.max_connections,
        cache_prompt=gen.cache_prompt,
        effort=settings.effort.get(model),
    )


def configure(settings: BudgetSettings) -> None:
    """Register model prices and point ControlArena's env-based defaults at our roles."""
    if "control_arena" in sys.modules:
        raise RuntimeError(
            "configure() must run before control_arena is imported; "
            "ControlArena reads model defaults from the environment at import time."
        )
    # Environment first: Inspect model lookups load the ControlArena plugin, which
    # captures these variables the moment it is imported.
    config_dir = settings.logs_dir / ".budget"
    config_dir.mkdir(parents=True, exist_ok=True)
    for role, env_model, env_config in _ROLE_ENV:
        model = getattr(settings.roles, role)
        config_path = config_dir / f"{role}_generate_config.json"
        config_path.write_text(
            generate_config(settings, model).model_dump_json(exclude_none=True)
        )
        os.environ[env_model] = model
        os.environ[env_config] = str(config_path)

    for model, price in settings.prices.items():
        cost = ModelCost(**price.model_dump())
        # set_model_cost only accepts models in Inspect's database (mockllm is not).
        if get_model_info(model) is None:
            set_model_info(model, ModelInfo(cost=cost))
        else:
            set_model_cost(model, cost)
    # ControlArena tasks have no eval-level model; Inspect names it "none/none" and
    # cost_limit wants a price for it. It never makes a call.
    set_model_info("none/none", ModelInfo(cost=ModelCost(**_FREE)))

    from control_arena import protocol_arg_defaults as defaults

    resolved = {
        "untrusted": defaults.get_untrusted_model(),
        "trusted": defaults.get_trusted_model(),
    }
    if resolved != settings.roles.model_dump():
        raise RuntimeError(
            f"ControlArena resolved models {resolved}, expected {settings.roles.model_dump()}"
        )


# The system prompt is the setting description alone, so honest mode gets exactly the base prompt
# that the attack prompt builds on (ControlArena's default wraps it in extra text).
SYSTEM_PROMPT = "{setting_description}"


def control_eval_config(
    settings: BudgetSettings, *, limit: int, epochs: int = 1, log_dir: Path | None = None
) -> ControlEvalConfig:
    """ControlEvalConfig carrying every per-episode and per-run limit from budget.yaml."""
    from control_arena.eval import ControlEvalConfig

    lim, run = settings.limits, settings.run
    return ControlEvalConfig(
        untrusted_model=settings.roles.untrusted,
        untrusted_config=generate_config(settings, settings.roles.untrusted),
        trusted_model=settings.roles.trusted,
        trusted_config=generate_config(settings, settings.roles.trusted),
        max_steps=lim.max_steps,
        token_limit=lim.token_limit,
        working_limit=lim.working_limit_s,
        time_limit=lim.time_limit_s,
        limit=limit,
        epochs=epochs,
        max_samples=run.max_samples,
        max_tasks=run.max_tasks,
        retry_on_error=run.retry_on_error,
        fail_on_error=run.fail_on_error,
        log_dir=str(log_dir or settings.logs_dir),
        system_prompt=SYSTEM_PROMPT,
    )


def eval_limits(settings: BudgetSettings) -> dict[str, Any]:
    """Sample limits that ControlEvalConfig does not carry; pass to inspect_ai.eval/eval_set."""
    return {
        "cost_limit": settings.episode_cost_limit,
        "turn_limit": settings.limits.turn_limit,
    }


def usage_cost(settings: BudgetSettings, model: str, usage: ModelUsage) -> float:
    """Cost of one log's usage: Inspect's recorded total_cost, else priced from tokens."""
    if usage.total_cost is not None:
        return usage.total_cost
    price = settings.prices.get(model)
    if price is None:
        raise BudgetExceededError(
            f"logs contain usage for unpriced model {model!r}; add it to budget.yaml"
        )
    return (
        usage.input_tokens * price.input
        + (usage.input_tokens_cache_write or 0) * price.input_cache_write
        + (usage.input_tokens_cache_read or 0) * price.input_cache_read
        + usage.output_tokens * price.output
    ) / 1_000_000


def spent_usd(settings: BudgetSettings) -> float:
    """Total spend recorded in every eval log under the logs directory."""
    if not settings.logs_dir.exists():
        return 0.0
    total = 0.0
    for info in list_eval_logs(str(settings.logs_dir), recursive=True):
        log = read_eval_log(info, header_only=True)
        if log.stats is None:
            continue
        for model, usage in log.stats.model_usage.items():
            total += usage_cost(settings, model, usage)
    return total


def preflight(settings: BudgetSettings, *, n_episodes: int) -> float:
    """Refuse a run whose worst case could break the phase cap or hard ceiling.

    Returns the worst-case cost of the run in USD.
    """
    if n_episodes < 1:
        raise ValueError("n_episodes must be >= 1")
    worst_case = (
        n_episodes * settings.episode_cost_limit * settings.budget.worst_case_multiplier
    )
    spent = spent_usd(settings)
    cap = min(settings.budget.phase_cap_usd, settings.budget.hard_ceiling_usd)
    print(
        f"[budget] untrusted={settings.roles.untrusted} trusted={settings.roles.trusted} | "
        f"{n_episodes} episodes x ${settings.episode_cost_limit:.2f} cap "
        f"x {settings.budget.worst_case_multiplier} = worst case ${worst_case:.2f} | "
        f"spent ${spent:.2f} | phase cap ${settings.budget.phase_cap_usd:.2f}"
    )
    if spent + worst_case > cap:
        raise BudgetExceededError(
            f"worst case ${worst_case:.2f} + spent ${spent:.2f} exceeds cap ${cap:.2f}. "
            "Run fewer episodes, lower the episode cap, or raise phase_cap_usd in "
            "config/budget.yaml on purpose."
        )
    return worst_case
