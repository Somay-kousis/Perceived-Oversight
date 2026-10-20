"""Log splitter and reasoning vault (blind analysis).

After a run, each Inspect log is split three ways:

    raw log ──▶ sealed/        the original, untouched
            ──▶ monitor_view/  the same log with every reasoning block removed (messages, output,
            │                  store) and <thinking> sections cut from text; events, timelines and
            │                  attachments are dropped, since they repeat model inputs and outputs
            └─▶ reasoning.db   SQLite vault, one row per reasoning block (agent and broker)

A final check refuses to write the view if any vaulted text still appears in it (for example
quoted inside a scorer explanation). Failed attempts (`error_retries`) keep only their error.

Replay monitors and judges read only monitor_view. The vault is opened only after monitor and
disclosure scores are frozen. Some providers return reasoning summaries or redacted reasoning
instead of the full text; the `kind` column records which.
"""

from __future__ import annotations

import re
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from inspect_ai.log import EvalLog, EvalSample, read_eval_log, write_eval_log

# <thinking> and <think> sections; an unclosed tag runs to the end of the text (cut-off output)
_TAG = re.compile(r"<(thinking|think)>(.*?)(?:</\1>|\Z)", re.DOTALL | re.IGNORECASE)
_DROPPED_FIELDS = ("events", "timelines", "events_data", "attachments")
# Structured reasoning parts across providers as they appear in serialised logs and raw events
_REASONING_TYPES = {"reasoning", "thinking", "redacted_thinking"}
_MIN_LEAK_CHECK = 20  # vaulted texts at least this long must not appear anywhere in the view

SCHEMA = """
CREATE TABLE IF NOT EXISTS reasoning (
    log_file TEXT, task TEXT, sample_id TEXT, epoch INTEGER,
    condition TEXT, arm TEXT, mode TEXT,
    source TEXT,      -- 'agent' (U's messages) or 'broker' (broker conversation)
    step INTEGER,     -- 0-based index of the assistant message within its conversation
    model TEXT,
    kind TEXT,        -- 'reasoning' (full text), 'summary' (provider summary; Anthropic thinking
                      -- is stored by Inspect as a summary), 'redacted' (no text) or 'thinking_tag'
    text TEXT
)
"""


class ReasoningLeakError(RuntimeError):
    """Vaulted reasoning text still appears in the monitor view (e.g. quoted by a scorer)."""


@dataclass
class Block:
    source: str
    step: int
    model: str | None
    kind: str
    text: str


def _tags_in(value: Any) -> list[str]:
    """Every tagged reasoning section in any string inside a JSON-like value."""
    if isinstance(value, dict):
        return [m for v in value.values() for m in _tags_in(v)]
    if isinstance(value, list):
        return [m for v in value for m in _tags_in(v)]
    if isinstance(value, str):
        return [m.group(2).strip() for m in _TAG.finditer(value)]
    return []


def _blocks_of_message(message: dict, source: str, step: int) -> list[Block]:
    """Reasoning blocks in one serialised message (assistant content, tool calls, tool results)."""
    model = message.get("model")
    content = message.get("content")
    parts = content if isinstance(content, list) else []
    found: list[Block] = []
    for part in parts:
        if not isinstance(part, dict) or part.get("type") not in _REASONING_TYPES:
            continue
        summary, full = part.get("summary"), part.get("reasoning") or part.get("thinking")
        if part.get("redacted"):
            # Inspect stores Anthropic thinking as summary=text, reasoning=signature, redacted=True
            found.append(Block(source, step, model, "summary" if summary else "redacted", summary or ""))
        else:
            if full:
                found.append(Block(source, step, model, "reasoning", full))
            if summary:
                found.append(Block(source, step, model, "summary", summary))
    found += [Block(source, step, model, "thinking_tag", m) for m in _tags_in(message) if m]
    return found


def _conversation_blocks(messages: list[dict], source: str) -> list[Block]:
    """Blocks per message; tool results count towards the assistant message that called them."""
    blocks, step = [], -1
    for m in messages:
        if not isinstance(m, dict):
            continue
        if m.get("role") == "assistant":
            step += 1
        if m.get("role") in ("assistant", "tool"):
            blocks.extend(_blocks_of_message(m, source, max(step, 0)))
    return blocks


def strip(value: Any) -> Any:
    """A copy of a JSON-like value with reasoning parts removed and tagged sections cut."""
    if isinstance(value, dict):
        return {k: strip(v) for k, v in value.items()}
    if isinstance(value, list):
        return [strip(v) for v in value if not (isinstance(v, dict) and v.get("type") in _REASONING_TYPES)]
    if isinstance(value, str):
        return _TAG.sub("", value)
    return value


def _clean_retries(retries: Any) -> Any:
    """Failed attempts keep only their error; their events (raw model calls) are dropped."""
    if not isinstance(retries, list):
        return retries
    return [{k: v for k, v in r.items() if k != "events"} if isinstance(r, dict) else r for r in retries]


def _broker_messages(sample: dict) -> list[dict]:
    store = sample.get("store") or {}
    return next((v for k, v in store.items() if k.endswith("BrokerState:messages")), []) or []


def split_sample(sample: EvalSample) -> tuple[EvalSample, list[Block]]:
    data = sample.model_dump(mode="json")
    blocks = _conversation_blocks(data.get("messages") or [], "agent")
    blocks += _conversation_blocks(_broker_messages(data), "broker")
    kept = {k: v for k, v in data.items() if k not in _DROPPED_FIELDS}
    kept["error_retries"] = _clean_retries(kept.get("error_retries"))
    return EvalSample.model_validate(strip(kept)), blocks


def _row_meta(log: EvalLog, sample: EvalSample) -> tuple[str, str, str]:
    meta = sample.metadata or {}
    inner = meta.get("metadata") or {}
    mode = str(meta.get("eval_mode", ""))
    return str(inner.get("condition", "")), str(inner.get("arm", "")), mode


def split_log(path: Path, out_dir: Path, db_path: Path, allow_unfinished: bool = False) -> tuple[Path, int]:
    """Split one log. Returns the monitor-view path and the number of vault rows written.

    Safe to rerun: rows for the same log file are replaced. Fails (writing nothing) if any vaulted
    text would still appear in the monitor view. A run that was killed (status "started") is
    refused unless `allow_unfinished`; then its finished episodes are split and the view keeps the
    status, so readers can tell."""
    log = read_eval_log(str(path), resolve_attachments=True)
    if log.status != "success" and not (allow_unfinished and log.status == "started"):
        raise ValueError(f"{path.name}: log status is {log.status!r}; split only finished runs")
    rows: list[tuple] = []
    clean_samples = []
    for sample in log.samples or []:
        clean, blocks = split_sample(sample)
        clean_samples.append(clean)
        condition, arm, mode = _row_meta(log, sample)
        rows += [
            (path.name, log.eval.task, str(sample.id), sample.epoch, condition, arm, mode,
             b.source, b.step, b.model, b.kind, b.text)
            for b in blocks
        ]
    header = strip(log.model_copy(update={"samples": None}).model_dump(mode="json"))
    view = EvalLog.model_validate(header).model_copy(update={"samples": clean_samples})
    dumped = view.model_dump_json()
    leaked = [r[-1][:60] for r in rows if len(r[-1]) >= _MIN_LEAK_CHECK and r[-1] in dumped]
    if leaked:
        raise ReasoningLeakError(f"{path.name}: reasoning still in the view (e.g. {leaked[0]!r})")
    view_dir, sealed_dir = out_dir / "monitor_view", out_dir / "sealed"
    view_dir.mkdir(parents=True, exist_ok=True)
    sealed_dir.mkdir(parents=True, exist_ok=True)
    view_path = view_dir / path.name
    write_eval_log(view, str(view_path))
    with sqlite3.connect(db_path) as db:
        db.execute(SCHEMA)
        db.execute("DELETE FROM reasoning WHERE log_file = ?", (path.name,))
        db.executemany("INSERT INTO reasoning VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    shutil.move(str(path), sealed_dir / path.name)
    return view_path, len(rows)
