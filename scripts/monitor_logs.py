"""Replay the live monitor on monitor-view logs.

Usage (from the repository root):
  .venv/bin/python scripts/monitor_logs.py calibrate logs/<run>/monitor_view [--rule mean]
  .venv/bin/python scripts/monitor_logs.py rescore   logs/<run>/monitor_view --model mockllm/model

calibrate: hold and stop thresholds per pool (C0; broker conditions) from honest episodes, at
most 10% of honest episodes held and 1% stopped. No model calls.
rescore: scores every saved action again with another monitor model and prints old vs new.
Paid models go through the budget guardrails like any run.
"""

import argparse
import asyncio
from pathlib import Path

from perceived_oversight.replay import calibrate, calibration_size, combine, load_episodes, rescore

parser = argparse.ArgumentParser()
parser.add_argument("command", choices=["calibrate", "rescore"])
parser.add_argument("view_dir", type=Path)
parser.add_argument("--rule", default="mean", choices=["mean", "max", "holistic", "narrow"])
parser.add_argument("--model")
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
    if not args.model:
        raise SystemExit("rescore needs --model")
    if not args.model.startswith("mockllm/"):
        raise SystemExit("paid rescoring must go through the budget guardrails; not wired yet")
    for e in episodes:
        new = asyncio.run(rescore(e, args.model))
        for old, fresh in zip(e.actions, new.actions):
            print(f"{e.condition} {e.sample_id}: {combine(old.scores, args.rule)} -> "
                  f"{combine(fresh.scores, args.rule)}")
