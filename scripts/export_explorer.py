"""Export the run explorer's data as static JSON for hosting (no server, spend left out).

Usage (from the repository root): .venv/bin/python scripts/export_explorer.py [logs_dir] [out_dir]
Defaults: logs/ and explorer/web/dist-data/ (untracked); then build with VITE_STATIC=1.
"""

import sys
from pathlib import Path

from perceived_oversight import budget
from perceived_oversight.explorer import export_snapshot

logs = Path(sys.argv[1]) if len(sys.argv) > 1 else budget.load_settings().logs_dir
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("explorer/web/dist-data")
export_snapshot(logs, out)
files = list(out.rglob("*.json"))
print(f"[export] {len(files)} files in {out}")
