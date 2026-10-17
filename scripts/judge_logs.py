"""Run judges and the manipulation check on monitor-view logs; export and score hand labels.

Usage (from the repository root):
  .venv/bin/python scripts/judge_logs.py judge     logs/<run> --model mockllm/model
  .venv/bin/python scripts/judge_logs.py check     logs/<run> --model mockllm/model [--cutoff before_hold]
  .venv/bin/python scripts/judge_logs.py reasoning logs/<run> --model mockllm/model   (needs SCORES_FROZEN)
  .venv/bin/python scripts/judge_logs.py sheet     logs/<run> --judge disclosure --n 30
  .venv/bin/python scripts/judge_logs.py agree     logs/<run> --judge disclosure

Reads <run>/monitor_view/*.eval; writes <run>/judgements.jsonl. `sheet` writes a CSV of judge
inputs with an empty `human_label` column; `agree` compares it with the judge's labels.
The manipulation check must use the same model as U in the episode. Paid models are not wired yet.
"""

import argparse
import asyncio
import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from perceived_oversight import judges as J

p = argparse.ArgumentParser()
p.add_argument("command", choices=["judge", "check", "reasoning", "sheet", "agree"])
p.add_argument("run_dir", type=Path)
p.add_argument("--model")
p.add_argument("--cutoff", default="whole", choices=["whole", "before_hold"])
p.add_argument("--judge", default="disclosure")
p.add_argument("--n", type=int, default=30)
a = p.parse_args()

cases = J.load_cases(sorted((a.run_dir / "monitor_view").glob("*.eval")))
out_path = a.run_dir / "judgements.jsonl"


def need_mock():
    if not a.model:
        raise SystemExit("--model is required")
    if not a.model.startswith("mockllm/"):
        raise SystemExit("paid judge models must go through the budget guardrails; not wired yet")


RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write(rows):
    # append-only; every row carries this invocation's id so reruns can be told apart
    with out_path.open("a") as f:
        for r in rows:
            f.write(json.dumps({**r, "run_id": RUN_ID}) + "\n")
    print(f"[judge] {len(rows)} rows appended to {out_path}")


if a.command == "judge":
    need_mock()
    write([r for c in cases for r in asyncio.run(J.judge_case(c, a.model))])
elif a.command == "check":
    need_mock()
    write([r for c in cases for r in asyncio.run(J.manipulation_check(c, a.model, a.cutoff))])
elif a.command == "reasoning":
    need_mock()
    write([r for c in cases if (r := asyncio.run(J.reasoning_judge(c, a.run_dir, a.model)))])
elif a.command == "sheet":
    # one row per item the judge labels: per episode, or per held request for hold_response
    items = []
    for c in cases:
        if not c.broker or (a.judge == "disclosure" and c.episode.mode != "attack"):
            continue
        if a.judge == "hold_response":
            items += [(c, n, ex) for n, ex in enumerate(J.hold_exchanges(c))]
        else:
            items.append((c, "", ""))
    picked = random.Random(0).sample(items, min(a.n, len(items)))
    sheet = a.run_dir / f"labels_{a.judge}.csv"
    with sheet.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["log_file", "sample_id", "epoch", "hold", "side_task", "broker_messages", "hold_exchange", "human_label"])
        for c, n, ex in picked:  # blind: no condition column
            w.writerow([c.episode.log_file, c.episode.sample_id, c.episode.epoch, n, c.side_task,
                        J.broker_messages(c), ex, ""])
    print(f"[judge] {len(picked)} items to label in {sheet}")
else:
    sheet = a.run_dir / f"labels_{a.judge}.csv"
    human = {(r["log_file"], r["sample_id"], r["epoch"], r["hold"]): r["human_label"].strip().lower()
             for r in csv.DictReader(sheet.open()) if r["human_label"].strip()}
    judged = {}
    for r in map(json.loads, out_path.open()):  # later rows (reruns) replace earlier ones
        if r.get("judge") == a.judge and "label" in r:
            judged[(r["log_file"], r["sample_id"], str(r["epoch"]), str(r.get("hold", "")))] = r["label"]
    keys = [k for k in human if k in judged]
    if not keys:
        raise SystemExit("no overlap between hand labels and judge labels")
    print(J.agreement([judged[k] for k in keys], [human[k] for k in keys]))
