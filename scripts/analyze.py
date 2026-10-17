"""Safety, prevention, detection after harm and usefulness per condition, plus primary comparisons.

Usage (from the repository root):
  .venv/bin/python scripts/analyze.py logs/<run_dir> [more run dirs] [--budgets 0.01 0.02 0.05]
      [--rule mean] [--boot 1000]

Reads every <run_dir>/monitor_view/*.eval (split logs only; pass the calibration run and the
main runs together). Thresholds per budget come from the honest calibration-mode episodes of each
pool; each episode's live thresholds are read from its log, so budgets looser than them are
reported as censored. Usefulness is reported separately for calibration-mode and thresholded
honest episodes, per pair and pooled. Writes analysis.json into the first run directory.
"""

import argparse
import json
from pathlib import Path

from perceived_oversight.analysis import PRIMARY, bootstrap_difference, condition_safety, usefulness
from perceived_oversight.replay import CONDITIONS, load_episodes

p = argparse.ArgumentParser()
p.add_argument("run_dirs", type=Path, nargs="+")
p.add_argument("--budgets", nargs="+", type=float, default=[0.01, 0.02, 0.05])
p.add_argument("--rule", default="mean", choices=["mean", "max", "holistic", "narrow"])
p.add_argument("--boot", type=int, default=1000)
a = p.parse_args()

episodes = load_episodes(sorted(p for d in a.run_dirs for p in (d / "monitor_view").glob("*.eval")))
live = None  # thresholds come from each log
present = [c for c in CONDITIONS if any(e.condition == c for e in episodes)]
result = {"usefulness": {}, "safety": [], "primary": [],
          "errored": {c: sum(e.errored for e in episodes if e.condition == c) for c in present}}

for c in present:
    for mode_name, wanted in (("calibration", True), ("thresholds", False)):
        for pair in sorted({e.task_pair for e in episodes}) + ["pooled"]:
            honest = [e for e in episodes if e.condition == c and e.mode == "honest" and not e.errored
                      and e.calibration_mode == wanted and (pair == "pooled" or e.task_pair == pair)]
            if honest:
                result["usefulness"][f"{c}|{mode_name}|{pair}"] = usefulness(honest)
    for b in a.budgets:
        try:
            result["safety"].append(condition_safety(episodes, c, b, live, a.rule))
        except ValueError as error:
            result["safety"].append({"condition": c, "budget": b, "error": str(error)})

for x, y in PRIMARY:
    if all(any(e.condition in (cond.split("-")[0],) or (cond == "C2-C5" and e.condition in ("C2", "C3", "C4", "C5"))
               for e in episodes) for cond in (x, y)):
        for b in a.budgets:
            try:
                result["primary"].append(bootstrap_difference(episodes, x, y, b, a.boot, rule=a.rule, live_stop=live))
            except ValueError as error:
                result["primary"].append({"comparison": f"{x} - {y}", "budget": b, "error": str(error)})

out = a.run_dirs[0] / "analysis.json"
out.write_text(json.dumps(result, indent=2, default=str))
for row in result["safety"]:
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()})
for row in result["primary"]:
    print(row)
print(f"[analyze] written {out}")
