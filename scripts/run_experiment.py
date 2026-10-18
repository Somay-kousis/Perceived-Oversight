"""Experiment launcher: the default configuration for everything, or pick each option.

Usage (from the repository root):
  .venv/bin/python scripts/run_experiment.py                       # defaults, mock models, $0
  .venv/bin/python scripts/run_experiment.py --interactive         # choose every option
  .venv/bin/python scripts/run_experiment.py --conditions C0 C2 --epochs 2 --calibration

Every option and its default is listed in docs/plan/CONFIGURATIONS.md. The full configuration is
saved into each log (eval metadata) and as run_config.json in the run directory. Any non-mock
model needs --confirm-paid, and every run passes the budget preflight first.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from perceived_oversight import budget

MOCK = "mockllm/model"
CONDITIONS = ["C0", "C1", "C2", "C3", "C4", "C5", "C6"]
DEFAULTS = {
    "conditions": CONDITIONS,
    "task_pairs": ["bank_transfer_2", "spam_filter_update"],
    "modes": ["honest", "attack"],
    "arm": "neutral",
    "epochs": 1,
    "untrusted_model": MOCK,
    "monitor_model": MOCK,
    "broker_model": MOCK,
    "judge_model": MOCK,
    "broker_style": "neutral",
    "c5_variant": None,
    "calibration": True,
    # per pool (METHODS: C0 actions and broker requests are calibrated separately)
    "hold_c0": None,
    "stop_c0": None,
    "hold_broker": None,
    "stop_broker": None,
}
CHOICES = {
    "arm": ["neutral", "stress"],
    "broker_style": ["neutral", "warm"],
    "c5_variant": [None, "real_entries", "rapport_only"],
}


def parse() -> dict:
    p = argparse.ArgumentParser()
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--conditions", nargs="+", choices=CONDITIONS)
    p.add_argument("--task-pairs", nargs="+")
    p.add_argument("--modes", nargs="+", choices=["honest", "attack"])
    p.add_argument("--arm", choices=CHOICES["arm"])
    p.add_argument("--epochs", type=int)
    p.add_argument("--untrusted-model")
    p.add_argument("--monitor-model")
    p.add_argument("--broker-model")
    p.add_argument("--judge-model")
    p.add_argument("--broker-style", choices=CHOICES["broker_style"])
    p.add_argument("--c5-variant", choices=["real_entries", "rapport_only"])
    p.add_argument("--calibration", action="store_true", help="score only, never hold or stop")
    p.add_argument("--hold-c0", type=float)
    p.add_argument("--stop-c0", type=float)
    p.add_argument("--hold-broker", type=float)
    p.add_argument("--stop-broker", type=float)
    p.add_argument("--run-name")
    p.add_argument("--confirm-paid", action="store_true")
    a = vars(p.parse_args())
    config = dict(DEFAULTS)
    for key in DEFAULTS:
        if a.get(key) is not None and a.get(key) is not False:
            config[key] = a[key]
    thresholds_given = any(a[k] is not None for k in ("hold_c0", "stop_c0", "hold_broker", "stop_broker"))
    if thresholds_given and a["calibration"]:
        raise SystemExit("--calibration and thresholds exclude each other")
    if thresholds_given:
        config["calibration"] = False
    if a["interactive"]:
        config = interactive(config)
    config["run_name"] = a["run_name"] or datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    config["confirm_paid"] = a["confirm_paid"]
    return config


def interactive(config: dict) -> dict:
    print("Press Enter to keep the default shown in brackets.")
    for key, default in DEFAULTS.items():
        options = CHOICES.get(key)
        hint = f" options {options}" if options else ""
        raw = input(f"{key}{hint} [{config[key]}]: ").strip()
        if not raw:
            continue
        try:
            if isinstance(default, list):
                config[key] = raw.split()
            elif isinstance(default, bool):
                config[key] = raw.lower() in ("y", "yes", "true", "1")
            elif key == "epochs":
                config[key] = int(raw)
            elif key.startswith(("hold_", "stop_")):
                config[key] = float(raw)
                config["calibration"] = False
            else:
                config[key] = None if raw == "None" else raw
        except ValueError:
            raise SystemExit(f"invalid value for {key}: {raw!r}")
    return config


def validate(config: dict, settings: budget.BudgetSettings) -> None:
    bad = [c for c in config["conditions"] if c not in CONDITIONS]
    if bad:
        raise SystemExit(f"unknown conditions {bad}")
    for key, options in CHOICES.items():
        if config[key] not in options:
            raise SystemExit(f"{key} must be one of {options}")
    if config["epochs"] < 1:
        raise SystemExit("epochs must be at least 1")
    models = {config[k] for k in ("untrusted_model", "monitor_model", "broker_model", "judge_model")}
    paid = {m for m in models if not m.startswith("mockllm/")}
    if paid and not config["confirm_paid"]:
        raise SystemExit(f"paid models {sorted(paid)} need --confirm-paid (explicit go)")
    missing = [m for m in models if m not in settings.prices]
    if missing:
        raise SystemExit(f"no price in config/budget.yaml for {missing}; cost limits would not apply")
    if not config["calibration"]:
        for pool in ("c0", "broker"):
            needed = pool == "c0" and "C0" in config["conditions"] or pool == "broker" and any(
                c != "C0" for c in config["conditions"])
            if needed and (config[f"hold_{pool}"] is None or config[f"stop_{pool}"] is None):
                raise SystemExit(f"set --hold-{pool} and --stop-{pool}, or use --calibration")


def build_setting(pair: str, cond: str, config: dict, settings: budget.BudgetSettings, thresholds: dict):
    """One setting; the monitor and broker get the budget.yaml generate settings for their models."""
    from perceived_oversight.setting import PerceivedOversightSetting

    return PerceivedOversightSetting(
        task_pair=pair, condition=cond, arm=config["arm"], judge_model=config["judge_model"],
        broker_model=config["broker_model"], monitor_model=config["monitor_model"],
        broker_style=config["broker_style"], c5_variant=config["c5_variant"], **thresholds,
        monitor_config=budget.generate_config(settings, config["monitor_model"]),
        broker_config=budget.generate_config(settings, config["broker_model"]),
    )


def main() -> None:
    config = parse()
    settings = budget.load_settings(roles={"untrusted": config["untrusted_model"], "trusted": config["monitor_model"]})
    validate(config, settings)
    budget.configure(settings)

    # ControlArena reads model defaults at import time, so import it only after configure().
    from control_arena import EvalMode
    from control_arena.eval import get_control_task_product
    from inspect_ai import eval as inspect_eval

    from perceived_oversight.monitor import informant_protocol
    from perceived_oversight.policy import untrusted_policy

    run_dir = settings.logs_dir / config["run_name"]
    if run_dir.exists():
        raise SystemExit(f"{run_dir} exists; choose another --run-name (runs never share a folder)")
    run_dir.mkdir(parents=True)
    (run_dir / "run_config.json").write_text(json.dumps(config, indent=2))

    def thresholds(cond: str) -> dict:
        if config["calibration"]:
            return {}
        pool = "c0" if cond == "C0" else "broker"
        return {"hold_threshold": config[f"hold_{pool}"], "stop_threshold": config[f"stop_{pool}"]}

    settings_list = [
        build_setting(pair, cond, config, settings, thresholds(cond))
        for cond in config["conditions"] for pair in config["task_pairs"]
    ]
    modes = [EvalMode.HONEST if m == "honest" else EvalMode.ATTACK for m in config["modes"]]
    eval_config = budget.control_eval_config(settings, limit=1, epochs=config["epochs"], log_dir=run_dir)
    tasks = get_control_task_product(
        settings=settings_list,
        micro_protocols=informant_protocol(policy=untrusted_policy(config["arm"])),
        modes=modes,
        eval_config=eval_config,
    )
    n_episodes = len(tasks) * config["epochs"]
    budget.preflight(settings, n_episodes=n_episodes,
                     extra_models=[config["broker_model"], config["judge_model"], config["monitor_model"]])
    logs = inspect_eval(tasks, **eval_config.eval_args(), **budget.eval_limits(settings),
                        metadata={"run_config": config})
    errored = sum(1 for log in logs for s in (log.samples or []) if s.error is not None)
    failed_logs = [log for log in logs if log.status != "success"]
    print(f"[run] {len(logs)} logs ({len(failed_logs)} not successful), {n_episodes} episodes, "
          f"{errored} errored, in {run_dir}")
    print(f"[run] next: .venv/bin/python scripts/split_logs.py {run_dir}")
    if errored or failed_logs:
        sys.exit(1)


if __name__ == "__main__":
    main()
