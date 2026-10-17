"""Split every new eval log in a directory into sealed raw log, monitor view and reasoning vault.

Usage (from the repository root): .venv/bin/python scripts/split_logs.py logs/<run_dir>
Writes <run_dir>/sealed/, <run_dir>/monitor_view/ and <run_dir>/reasoning.db (all untracked).
"""

import sys
from pathlib import Path

from perceived_oversight.splitter import split_log

run_dir = Path(sys.argv[1])
logs = sorted(run_dir.glob("*.eval"))
if not logs:
    raise SystemExit(f"no .eval logs directly in {run_dir}")
for path in logs:
    view, rows = split_log(path, run_dir, run_dir / "reasoning.db")
    print(f"[split] {path.name}: {rows} reasoning blocks to the vault; view at {view}")
