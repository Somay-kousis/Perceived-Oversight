"""$0 end-to-end check: one episode per mode in our setting (C0, neutral arm), every role on mockllm.

Confirms the install, the budget guardrails and the eval logs work before any paid call.
Fails if any model other than mockllm shows up in the logs.

Usage: .venv/bin/python Perceived-Oversight/scripts/smoke_mock.py
"""

from perceived_oversight import budget

MOCK = "mockllm/model"
TASK_PAIR = "bank_transfer_2"

settings = budget.load_settings(roles={"untrusted": MOCK, "trusted": MOCK})
budget.configure(settings)

# ControlArena reads model defaults at import time, so import it only after configure().
from inspect_ai import eval as inspect_eval  # noqa: E402

from control_arena import EvalMode  # noqa: E402
from control_arena.eval import get_control_task_product  # noqa: E402
from control_arena.micro_protocol import trusted_monitoring_builder  # noqa: E402
from control_arena.scorers import max_suspicion_scorer  # noqa: E402
from perceived_oversight.policy import untrusted_policy  # noqa: E402
from perceived_oversight.setting import PerceivedOversightSetting  # noqa: E402

LIMIT = 1
log_dir = settings.logs_dir / "smoke"
eval_config = budget.control_eval_config(settings, limit=LIMIT, log_dir=log_dir)
tasks = get_control_task_product(
    settings=PerceivedOversightSetting(task_pair=TASK_PAIR, condition="C0", judge_model=MOCK),
    micro_protocols=trusted_monitoring_builder(policy=untrusted_policy("neutral")),
    modes=[EvalMode.HONEST, EvalMode.ATTACK],
    eval_config=eval_config,
    monitoring_scorers=[max_suspicion_scorer()],
)
budget.preflight(settings, n_episodes=len(tasks) * LIMIT)

logs = inspect_eval(tasks, **eval_config.eval_args(), **budget.eval_limits(settings))

for log in logs:
    models = set(log.stats.model_usage) if log.stats else set()
    samples = log.samples or []
    limits_hit = [s.limit.type for s in samples if s.limit is not None]
    errored = [s for s in samples if s.error is not None]
    print(
        f"[smoke] {log.eval.task} status={log.status} samples={len(samples)} "
        f"errors={len(errored)} models={sorted(models)} limits_hit={limits_hit}"
    )
    if log.status != "success":
        raise SystemExit(f"[smoke] FAILED: {log.error}")
    # fail_on_error=False keeps status "success" even when every sample errored.
    if errored:
        raise SystemExit(f"[smoke] FAILED: sample error: {errored[0].error.message[:300]}")
    if models - {MOCK}:
        raise SystemExit(f"[smoke] FAILED: unexpected non-mock models {models - {MOCK}}")

print(f"[smoke] OK. Total spend recorded in logs: ${budget.spent_usd(settings):.2f}")
