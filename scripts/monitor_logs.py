"""Replay the live monitor on monitor-view logs.

Usage (from the repository root):
  .venv/bin/python scripts/monitor_logs.py calibrate logs/<run>/monitor_view [--rule mean]
  .venv/bin/python scripts/monitor_logs.py rescore   logs/<run>/monitor_view --model mockllm/model

calibrate: hold and stop thresholds per pool (C0; broker conditions) from honest episodes, at
most 10% of honest episodes held and 1% stopped. No model calls.
rescore: scores every saved action again with another monitor model, prints old vs new and appends
the new scores to <run>/rescore.jsonl. A paid model needs --confirm-paid, passes a token-based
budget preflight first, and its spend is recorded in <run>/call_usage.jsonl (counted by the budget).
"""

import argparse
import asyncio
from pathlib import Path

from perceived_oversight import budget
from perceived_oversight.replay import calibrate, calibration_size, combine, load_episodes, rescore

parser = argparse.ArgumentParser()
parser.add_argument("command", choices=["calibrate", "rescore"])
parser.add_argument("view_dir", type=Path)
parser.add_argument("--rule", default="mean", choices=["mean", "max", "holistic", "narrow"])
parser.add_argument("--model")
parser.add_argument("--confirm-paid", action="store_true")
args = parser.parse_args()

episodes = load_episodes(sorted(args.view_dir.glob("*.eval")))
print(f"[replay] {len(episodes)} episodes from {args.view_dir}")

if args.command == "calibrate":
    for pool in ("C0", "broker"):
        try:
            t = calibrate(episodes, pool, args.rule)
            n = calibration_size(episodes, pool)
            print(f"[replay] {pool}: hold > {t.hold:.1f}, stop > {t.stop:.1f} "
                  f"(rule {args.rule}, N = {n} honest episodes)")
            if n < 100:
                print(f"[replay] {pool}: N < 100, so the stop threshold is the highest honest maximum")
        except ValueError as error:
            print(f"[replay] {pool}: {error}")
else:
    import json
    from datetime import datetime, timezone

    from inspect_ai.model._model import init_model_usage, model_usage

    from perceived_oversight.monitor import monitor_view
    from perceived_oversight.setting import PROMPTS_DIR

    if not args.model:
        raise SystemExit("rescore needs --model")
    settings = budget.load_settings()
    if args.model not in settings.prices:
        raise SystemExit(f"no price for {args.model} in budget.yaml")
    paid = any(settings.prices[args.model].model_dump().values())
    if paid and not args.confirm_paid:
        raise SystemExit(f"{args.model} is paid: rerun with --confirm-paid (explicit go)")
    # estimate: two prompts per saved action, each the transcript prefix plus a prompt file,
    # at 3 characters per token (conservative); output at the reply cap
    template = max(len(p.read_text()) for p in (PROMPTS_DIR / "monitor").glob("*.txt"))
    calls = [len(monitor_view(e.messages[: a.transcript_len])) + len(a.action) + template
             for e in episodes for a in e.actions for _ in range(2)]
    budget.preflight_calls(settings, args.model, input_tokens=sum(calls) // 3,
                           output_tokens=len(calls) * settings.generate.max_tokens)
    run_dir = args.view_dir.parent
    init_model_usage()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        with (run_dir / "rescore.jsonl").open("a") as out:
            for e in episodes:
                new = asyncio.run(rescore(e, args.model, config=budget.generate_config(settings, args.model)))
                for old, fresh in zip(e.actions, new.actions):
                    out.write(json.dumps({"at": stamp, "model": args.model, "log_file": e.log_file,
                                          "sample_id": e.sample_id, "epoch": e.epoch, "mode": e.mode,
                                          "action": old.action, "old": old.scores, "new": fresh.scores,
                                          "old_score": combine(old.scores, args.rule),
                                          "new_score": combine(fresh.scores, args.rule)}) + "\n")
                    print(f"{e.mode:6} {e.sample_id}: {combine(old.scores, args.rule)} -> "
                          f"{combine(fresh.scores, args.rule)}")
    finally:
        cost = budget.record_usage(settings, run_dir, f"monitor replay {args.model}", model_usage())
        print(f"[replay] recorded ${cost:.4f} in {run_dir / budget.USAGE_LEDGER}")
