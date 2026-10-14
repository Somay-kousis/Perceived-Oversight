# Plan

Build order for the experiment. Every step ends the same way: tests and the mock smoke test pass at
$0, the diff is reviewed, and it is committed only after review. Paid runs start in Phase D.

Target: 4-page AAAI-27 workshop paper.

Status: `[x]` done, `[~]` in progress, `[ ]` not started.

## Phase A: Foundations ($0, mock model)

- [~] **0. Housekeeping.** Docs reorganised into folders, README matches the abstract, verified
  citations, setup and workflow guides, `tests/` with pytest.
- [ ] **1. Neutral attack prompt.** `src/perceived_oversight/prompts/neutral_attack.txt`.
  Side task given without any mention of tests, monitoring or concealment.
- [ ] **2. Setting skeleton.** `src/perceived_oversight/setting.py`:
  `PerceivedOversightSetting` strips oversight wording from SHADE's prompts, pins the judge,
  records the condition, selects task pairs.

## Phase B: The manipulation ($0, mock model)

- [ ] **3. Spy core (C2 only).** `spy.py`: `ask_helper` built with Inspect `as_tool()`; money tools
  move from the agent to the spy. Test: money sent by the spy still reaches the scorer.
- [ ] **4. All conditions.** `conditions.py`: C0, C1, C2, C3, C5, then C4 (needs a tool-list
  wrapper because ControlArena hands tools over once per episode).

## Phase C: Measurement ($0, mock model)

- [ ] **5. Log splitter and reasoning vault.** `splitter.py`. Test: no reasoning block reaches
  monitor input.
- [ ] **6. Post-hoc replayed monitor.** `prompts/monitor_shade.txt`, `scripts/monitor_logs.py`.
- [ ] **7. Disclosure and manipulation-check scorers.** `scorers.py`.
- [ ] **8. Experiment runner and analysis.** `scripts/run_experiment.py`, `analysis.py`
  (safety at a fixed audit budget).

## Phase D: Real runs (paid)

- [ ] **9.** Models into `config/budget.yaml`; one tiny access check per model.
- [ ] **10.** Pilot (~20 episodes): does the agent attempt the side task, and does it notice the costume?
- [ ] **11.** Main runs.
- [ ] **12.** Paper.

## Decisions needed, by step

| Step | Decision | Suggested |
|---|---|---|
| 1 | Side-task framing: own goal / hidden request / no reason | own goal, no reason given |
| 2 | Task pairs | `bank_transfer_2`, `spam_filter_update`; `american_airlines_2` needs a neutral rewrite of its side task |
| 3 | What the spy does with a suspicious request: comply / ask / refuse (identical in all conditions) | comply and ask one neutral question |
| 4 | Costume wording for C1 to C5; keep C0; when C4 joins | draft all; keep C0; step ~8 |
| 6 | Monitor prompt and score scale | SHADE-specific, 0 to 100 |
| 7 | How to ask the agent who it thought the helper was without priming it | separate call after the episode, on a copy of the transcript |
| 8 | Audit budgets for the safety metric | report 1%, 2%, 5% |
| 10 | Pilot go/no-go | side task attempted in at least 30% of attack episodes |
