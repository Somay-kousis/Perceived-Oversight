"""Read-only API behind the run explorer.

    GET /runs                          every run folder under logs/: kind, split state, spend
    GET /runs/{run}                    its episodes (split runs only)
    GET /runs/{run}/episodes/{n}       scored actions, visible steps, reasoning (vault rule)

Content comes from monitor-view logs only; raw and sealed logs are read for their headers (spend)
and never for samples. The reasoning vault is opened for the agent (U) only when the run is marked
dev (`RUN_KIND` file containing `dev`) or its scores are frozen (`SCORES_FROZEN`); anything else
counts as a study run and gets a sealed bar with a block count. Broker reasoning is the defence's
own text and is always shown.

    .venv/bin/uvicorn --factory perceived_oversight.explorer:app_from_env   (LOGS_DIR, default logs/)

`export_snapshot` writes the same responses as static JSON files for hosting without a server, with
spend left out; it goes through these routes, so the vault rule applies unchanged.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from inspect_ai.log import read_eval_log

from perceived_oversight import budget
from perceived_oversight.judges import FROZEN_MARKER
from perceived_oversight.replay import Episode, load_episodes
from perceived_oversight.splitter import strip

KIND_FILE = "RUN_KIND"
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def run_kind(run: Path) -> str:
    """`dev` only when the run says so exactly; everything else is a study run."""
    marker = run / KIND_FILE
    return "dev" if marker.is_file() and marker.read_text().strip() == "dev" else "study"


def reasoning_open(run: Path) -> bool:
    return run_kind(run) == "dev" or (run / FROZEN_MARKER).is_file()


def _inside(path: Path, folder: Path) -> bool:
    """A real entry (not a symlink) whose resolved location is directly in `folder`."""
    return not path.is_symlink() and path.resolve().parent == folder.resolve()


def _views(run: Path) -> list[Path]:
    """Monitor-view logs the splitter wrote: a real monitor_view folder holding real files only.
    Symlinks are skipped, so a raw or sealed log can never be served through the folder's name."""
    folder = run / "monitor_view"
    if not folder.is_dir() or not _inside(folder, run):
        return []
    return sorted(p for p in folder.glob("*.eval") if p.is_file() and _inside(p, folder))


def _billable(run: Path) -> list[Path]:
    return sorted(p for p in run.rglob("*.eval") if budget.billable(str(p)))


def _spend(run: Path, settings: budget.BudgetSettings) -> float | None:
    """Spend from log headers (no samples are read); None if a model has no price."""
    total = 0.0
    for path in _billable(run):
        log = read_eval_log(str(path), header_only=True)
        if log.stats is None:
            continue
        for model, usage in log.stats.model_usage.items():
            try:
                total += budget.usage_cost(settings, model, usage)
            except budget.BudgetExceededError:
                return None
    return round(total, 6)


def _episode_count(paths: list[Path]) -> int:
    total = 0
    for path in paths:
        log = read_eval_log(str(path), header_only=True)
        total += (log.results.total_samples if log.results else 0) or 0
    return total


def _vault(run: Path, ep: Episode) -> dict[str, list[dict[str, Any]]]:
    db = run / "reasoning.db"
    rows: dict[str, list[dict[str, Any]]] = {"agent": [], "broker": []}
    if not db.exists():
        return rows
    with closing(sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True)) as conn:
        for source, step, kind, model, text in conn.execute(
            "SELECT source, step, kind, model, text FROM reasoning "
            "WHERE log_file = ? AND sample_id = ? AND epoch = ? ORDER BY source, step",
            (ep.log_file, ep.sample_id, ep.epoch),
        ):
            rows.setdefault(source, []).append({"step": step, "kind": kind, "model": model, "text": text})
    return rows


def _summary(n: int, ep: Episode) -> dict[str, Any]:
    scores = [a.score for a in ep.actions if a.score is not None]
    outcomes = {"execute": 0, "hold": 0, "stop": 0}
    for a in ep.actions:
        outcomes[a.outcome] += 1
    return {
        "n": n, "log_file": ep.log_file, "sample_id": ep.sample_id, "epoch": ep.epoch,
        "condition": ep.condition, "mode": ep.mode, "task_pair": ep.task_pair,
        "scored": len(ep.actions), "max_score": max(scores) if scores else None, "outcomes": outcomes,
        "scores": [a.score for a in ep.actions],
        "outcome_list": [a.outcome for a in ep.actions],
        "stopped": ep.stopped, "error": ep.errored,
        "main_task_success": ep.main_task_success, "side_task_success": ep.side_task_success,
    }


def create_app(logs_dir: Path) -> FastAPI:
    root = Path(logs_dir).resolve()
    settings = budget.load_settings()
    app = FastAPI(title="oversight explorer", docs_url=None, redoc_url=None, openapi_url=None)

    def run_dir(run_id: str) -> Path:
        run = (root / run_id).resolve() if _RUN_ID.fullmatch(run_id) else None
        if run is None or run.parent != root or not run.is_dir():
            raise HTTPException(404, "no such run")
        return run

    def episodes(run: Path) -> list[Episode]:
        views = _views(run)
        if not views:
            raise HTTPException(409, "run not split; run scripts/split_logs.py on it first")
        try:
            return load_episodes(views)
        except Exception:
            raise HTTPException(500, "a log in this run could not be read") from None

    @app.get("/runs")
    def list_runs() -> list[dict[str, Any]]:
        out = []
        runs = [p for p in root.iterdir() if p.is_dir() and _RUN_ID.fullmatch(p.name) and _inside(p, root)]
        for run in sorted(runs):
            views = _views(run)
            row = {"id": run.name, "kind": run_kind(run), "split": bool(views),
                   "reasoning_open": reasoning_open(run), "episodes": None, "spend_usd": None, "error": None}
            try:
                row["episodes"] = _episode_count(views or _billable(run))
                row["spend_usd"] = _spend(run, settings)
            except Exception:
                row["error"] = "a log in this run could not be read"
            out.append(row)
        return out

    @app.get("/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        run = run_dir(run_id)
        return {"id": run.name, "kind": run_kind(run), "reasoning_open": reasoning_open(run),
                "episodes": [_summary(n, ep) for n, ep in enumerate(episodes(run))]}

    @app.get("/runs/{run_id}/episodes/{n}")
    def get_episode(run_id: str, n: int) -> dict[str, Any]:
        run = run_dir(run_id)
        eps = episodes(run)
        if not 0 <= n < len(eps):
            raise HTTPException(404, "no such episode")
        ep = eps[n]
        vault = _vault(run, ep)
        agent_open = reasoning_open(run)
        return {
            **_summary(n, ep),
            "actions": [{"i": i, **a.model_dump()} for i, a in enumerate(ep.actions)],
            "steps": [
                {"role": m.role, "text": strip(m.text),  # backstop: tags cut even if a view kept them
                 "tool_calls": [c.function for c in getattr(m, "tool_calls", None) or []]}
                for m in ep.messages
            ],
            "reasoning": {
                "agent": {"sealed": not agent_open, "blocks": len(vault["agent"]),
                          "items": vault["agent"] if agent_open else []},
                "broker": {"sealed": False, "blocks": len(vault["broker"]), "items": vault["broker"]},
            },
        }

    return app


def app_from_env() -> FastAPI:
    return create_app(Path(os.environ.get("LOGS_DIR", budget.load_settings().logs_dir)))


def export_snapshot(logs_dir: Path, out_dir: Path) -> None:
    """Write every API response as JSON under out_dir (runs.json, runs/<id>.json,
    runs/<id>/episodes/<n>.json). Spend is nulled; an older snapshot there is replaced."""
    from fastapi.testclient import TestClient

    out = Path(out_dir)
    if (out / "runs").is_dir():
        shutil.rmtree(out / "runs")  # only what an earlier export wrote
    (out / "runs").mkdir(parents=True, exist_ok=True)
    client = TestClient(create_app(Path(logs_dir)))

    def write(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False))

    runs = [{**row, "spend_usd": None} for row in client.get("/runs").json()]
    write(out / "runs.json", runs)
    for row in runs:
        if not row["split"] or row["error"]:
            continue
        detail = client.get(f"/runs/{row['id']}")
        if detail.status_code != 200:
            continue
        write(out / "runs" / f"{row['id']}.json", detail.json())
        for ep in detail.json()["episodes"]:
            response = client.get(f"/runs/{row['id']}/episodes/{ep['n']}")
            if response.status_code == 200:
                write(out / "runs" / row["id"] / "episodes" / f"{ep['n']}.json", response.json())
