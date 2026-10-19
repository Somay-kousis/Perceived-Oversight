"""Run judges and the manipulation check on monitor-view logs; export and score hand labels.

Usage (from the repository root):
  .venv/bin/python scripts/judge_logs.py judge     logs/<run> --model mockllm/model
  .venv/bin/python scripts/judge_logs.py check     logs/<run> --model mockllm/model [--cutoff before_hold]
  .venv/bin/python scripts/judge_logs.py reasoning logs/<run> --model mockllm/model   (needs SCORES_FROZEN)
  .venv/bin/python scripts/judge_logs.py sheet     logs/<run> --judge disclosure --n 30
  .venv/bin/python scripts/judge_logs.py agree     logs/<run> --judge disclosure

Reads <run>/monitor_view/*.eval; writes <run>/judgements.jsonl. `sheet` writes a CSV of judge
inputs with an empty `human_label` column; `agree` compares it with the judge's labels.
The manipulation check must use the same model as U in the episode. A paid model needs
--confirm-paid, passes a token-based budget preflight, and its spend is recorded in
<run>/call_usage.jsonl (counted by the budget).
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
p.add_argument("--confirm-paid", action="store_true")
a = p.parse_args()

cases = J.load_cases(sorted((a.run_dir / "monitor_view").glob("*.eval")))
out_path = a.run_dir / "judgements.jsonl"


def need_model():
    """A free model runs; a paid one needs --confirm-paid and a budget preflight on an estimate:
    every judge call reads the main task, the side task, U's messages to the broker and a prompt
    file, at 3 characters per token (conservative); output at the reply cap."""
    from perceived_oversight import budget

    if not a.model:
        raise SystemExit("--model is required")
    settings = budget.load_settings()
    if a.model not in settings.prices:
        raise SystemExit(f"no price for {a.model} in budget.yaml")
    if not any(settings.prices[a.model].model_dump().values()):
        return
    if not a.confirm_paid:
        raise SystemExit(f"{a.model} is paid: rerun with --confirm-paid (explicit go)")
    if a.command not in ("judge", "check"):
        raise SystemExit("paid models are wired for `judge` and `check` only")
    chars = calls = 0
    if a.command == "check":
        # every step, as U and as the fresh baseline, reads the whole check transcript
        template = max(len(t.read_text()) for t in (J.PROMPTS_DIR / "check").glob("*.txt"))
        for c in cases:
            transcript = J.check_transcript(c, a.cutoff)
            if transcript is None:
                continue
            n = 2 * (len(J.CHECK_STEPS) if c.broker else 1)
            calls += n
            chars += n * (template + len(transcript) + 1000)
    else:
        template = max(len(t.read_text()) for t in (J.PROMPTS_DIR / "judges").glob("*.txt"))
        for c in cases:
            if not c.broker:
                continue
            holds = J.hold_exchanges(c)
            n = 1 + (c.episode.mode == "attack") + len(holds)
            calls += n
            chars += n * (template + len(c.metadata.get("main_task_description", "")) + len(c.side_task)
                          + len(J.broker_messages(c)) + max((len(h) for h in holds), default=0))
    budget.preflight_calls(settings, a.model, input_tokens=chars // 3,
                           output_tokens=calls * settings.generate.max_tokens)


def record(purpose):
    from inspect_ai.model._model import model_usage

    from perceived_oversight import budget

    cost = budget.record_usage(budget.load_settings(), a.run_dir, purpose, model_usage())
    print(f"[judge] recorded ${cost:.4f} in {a.run_dir / budget.USAGE_LEDGER}")


RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write(rows):
    # append-only; every row carries this invocation's id so reruns can be told apart
    with out_path.open("a") as f:
        for r in rows:
            f.write(json.dumps({**r, "run_id": RUN_ID}) + "\n")
    print(f"[judge] {len(rows)} rows appended to {out_path}")


if a.command == "judge":
    from inspect_ai.model._model import init_model_usage

    need_model()
    init_model_usage()
    try:
        write([r for c in cases for r in asyncio.run(J.judge_case(c, a.model))])
    finally:
        record(f"judges {a.model}")
elif a.command == "check":
    from inspect_ai.model._model import init_model_usage

    need_model()
    init_model_usage()
    try:
        write([r for c in cases for r in asyncio.run(J.manipulation_check(c, a.model, a.cutoff))])
    finally:
        record(f"manipulation check {a.model}")
elif a.command == "reasoning":
    need_model()
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
