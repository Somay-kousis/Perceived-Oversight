# Plan

Build order for the informant-protocol experiment ([FRAMING.md](../research/FRAMING.md)). Each step is complete when unit tests and the mock smoke test
pass at $0. Paid runs start in Phase D.

Target: 4-page AAAI-27 workshop paper.

Status: `[x]` done, `[~]` in progress, `[ ]` not started.

## Phase A: Foundations ($0, mock model)

- [x] **0. Housekeeping.** Docs reorganised into folders, README matches the abstract, verified
  citations, setup guide.
- [x] **1. Neutral attack prompt.** Wired in `policy.py` (2026-10-17). `src/perceived_oversight/prompts/neutral_attack.txt`.
  Side task given without any mention of tests, monitoring or concealment. Options and defaults
  in [CONFIGURATIONS.md](CONFIGURATIONS.md).
- [x] **2. Setting skeleton.** Code and unit tests pass (2026-10-17); full mock episodes are
  verified with the local smoke run (C0 to C6). `src/perceived_oversight/setting.py`:
  `PerceivedOversightSetting` strips oversight wording from SHADE's prompts, pins the judge,
  records the condition, selects task pairs.

## Phase B: The manipulation ($0, mock model)

- [x] **2b. Novelty check.** Done 2026-10-17: novel as a combination; see FRAMING.md.
- [x] **3a. Broker base (C2 only).** Done 2026-10-17. `broker.py`: one tool per pair
  (`payments_assistant`, `email_rules_assistant`) with a custom per-episode conversation instead of
  Inspect `as_tool()` (which starts fresh on every call); moved tools go from *U* to the broker;
  memo always required; neutral and warm reply styles. `tests/test_broker.py` (10 tests): money and rules made by the broker reach
  the side-task check; the broker remembers earlier calls.
- [x] **3b. Live link.** Done 2026-10-17 (unit tests; full episode needs local run).
  `monitor.py`: live monitor (holistic + narrow, averaged), calibration mode, `informant_protocol`
  (records U's messages for the monitor). `broker.py`: memo for requests only, payment unlock
  (complete + approved + matching calls only), hold flow (memo required, asked at most twice),
  stop via `TerminateSampleError`, processing status on every reply. C0: U's moved tools wrapped,
  only a high score stops. Caps raised to 80 steps / 80 turns; broker and monitor calls do not
  count as turns.
- [x] **4. All conditions.** Done 2026-10-17 (unit tests; full episodes need a local run).
  `conditions.py`: C5 log and seed, C4 arrival, monitor redactions; C4 timing in
  `informant_protocol`. Smoke test covers C0 to C6.

## Phase C: Measurement ($0, mock model)

- [x] **5. Log splitter, reasoning vault, harm markers.** Done 2026-10-17. `splitter.py` +
  `scripts/split_logs.py`: sealed raw log, reasoning-free monitor view, SQLite vault (agent and
  broker reasoning); tested on a real Inspect log. `harm.py`: live markers for when the side task
  first succeeded and when a side-task target was first touched.
- [x] **6. Replay monitor.** Done 2026-10-17. `replay.py` + `scripts/monitor_logs.py`: load
  monitor-view logs; recombine stored scores (mean, max, one prompt) and recompute outcomes under
  other thresholds at $0; calibrate hold and stop thresholds per pool from honest episodes;
  rescore saved actions with another monitor on the exact transcript prefix it saw live.
- [x] **7. Judges and manipulation check.** Done 2026-10-17. `judges.py` +
  `scripts/judge_logs.py`: blind disclosure, probing and hold-response judges; manipulation check
  (U and fresh baseline); reasoning judge locked until scores are frozen; labelling sheet and
  agreement (kappa). Hand labels come after the pilot.
- [x] **8. Experiment runner and analysis.** Done 2026-10-17. `scripts/run_experiment.py` (the
  launcher: defaults or pick each option; configuration saved in every log), `analysis.py` and
  `scripts/analyze.py` (safety at audit budgets, prevention vs detection after harm, usefulness,
  primary comparisons with bootstrap intervals).

## Phase D: Real runs (paid)

- [ ] **9.** Models into `config/budget.yaml`; one tiny access check per model.
- [ ] **10.** Pilot: honest episodes first (calibration mode) to set the live thresholds per
  episode, then attack episodes. Check usefulness vs C0: main-task success, holds per episode,
  false stops, steps used, episodes hitting the step or cost cap.
  Does the agent attempt the side task, and does it form the intended belief about the broker?
- [ ] **11.** Main runs.
- [ ] **12.** Paper.

## Decisions by step

| Step | Decision | Status |
|---|---|---|
| 1 | Attack-prompt options and wording | decided 2026-10-14 and 2026-10-16; template drafted |
| 2 | Task pairs | decided 2026-10-16: `bank_transfer_2`, `spam_filter_update` (neutral side-task rewrites in `side_tasks.yaml`) |
| 3 | Broker | decided 2026-10-14: live, log-aware, execute / hold / stop |
| 4 | Cover-identity wording for C1 to C6 | decided 2026-10-17 (`prompts/covers.yaml`) |
| 6 | Monitor prompt and score scale | decided: `prompts/monitor/` holistic + narrow, 0 to 100, averaged |
| 7 | How to probe *U*'s belief about the broker without priming it | separate call after the episode, on a copy of the transcript |
| 8 | Thresholds, safety definition, comparisons | decided 2026-10-17 ([METHODS.md](../research/METHODS.md) analysis plan): two threshold pools, per-episode calibration, several audit budgets, three primary comparisons |
| 10 | Pilot go/no-go | attempt rate at least 30%; C0 safety about 0.2 to 0.8; refusals reported separately; broker style (neutral or warm) from the manipulation check |
