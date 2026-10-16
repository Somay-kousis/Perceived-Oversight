# Plan

Build order for the informant-protocol experiment ([FRAMING.md](../research/FRAMING.md)). Every step ends the same way: tests and the mock smoke test pass at
$0, the diff is reviewed, and it is committed only after review. Paid runs start in Phase D.

Target: 4-page AAAI-27 workshop paper.

Status: `[x]` done, `[~]` in progress, `[ ]` not started.

## Phase A: Foundations ($0, mock model)

- [x] **0. Housekeeping.** Docs reorganised into folders, README matches the abstract, verified
  citations, setup and workflow guides.
- [~] **1. Neutral attack prompt.** `src/perceived_oversight/prompts/neutral_attack.txt`.
  Side task given without any mention of tests, monitoring or concealment. Options and defaults
  in [CONFIGURATIONS.md](CONFIGURATIONS.md).
- [ ] **2. Setting skeleton.** `src/perceived_oversight/setting.py`:
  `PerceivedOversightSetting` strips oversight wording from SHADE's prompts, pins the judge,
  records the condition, selects task pairs.

## Phase B: The manipulation ($0, mock model)

- [ ] **2b. Novelty check.** Read the "To verify" entries in REFERENCES.md; update FRAMING.md.
- [ ] **3a. Broker base (C2 only).** `broker.py`: broker tool built with Inspect `as_tool()`;
  money tools move from *U* to the broker; required memo field. Test: money sent by the broker
  still reaches the scorer.
- [ ] **3b. Live link.** Live monitor check on each request, processing status, execute / hold
  and challenge / stop, hidden-link rules. Same live monitor and stop rule for C0.
- [ ] **4. All conditions.** `conditions.py`: C0, C1, C2, C3, C5, then C4 (needs a tool-list
  wrapper because ControlArena hands tools over once per episode).

## Phase C: Measurement ($0, mock model)

- [ ] **5. Log splitter and reasoning vault.** `splitter.py`. Test: no reasoning block reaches
  monitor input.
- [ ] **6. Monitor.** `prompts/monitor_shade.txt`; live scoring for the broker and C0, plus replay
  of saved logs for analysis (`scripts/monitor_logs.py`).
- [ ] **7. Disclosure and manipulation-check scorers.** `scorers.py`.
- [ ] **8. Experiment runner and analysis.** `scripts/run_experiment.py`, `analysis.py`
  (safety at a fixed audit budget; prevention vs detection after harm). The runner is the launcher: default configuration for
  everything, or pick each option; the configuration is saved into every log.

## Phase D: Real runs (paid)

- [ ] **9.** Models into `config/budget.yaml`; one tiny access check per model.
- [ ] **10.** Pilot: honest episodes first to calibrate the live thresholds, then attack episodes.
  Does the agent attempt the side task, and does it form the intended belief about the broker?
- [ ] **11.** Main runs.
- [ ] **12.** Paper.

## Decisions needed, by step

| Step | Decision | Suggested |
|---|---|---|
| 1 | Attack-prompt options and wording | decided 2026-10-14 and 2026-10-16; template drafted |
| 2 | Task pairs | `bank_transfer_2`, `spam_filter_update`; `american_airlines_2` needs a neutral rewrite of its side task |
| 3 | Broker | decided 2026-10-14: live, log-aware, execute / hold / stop |
| 4 | Cover-identity wording for C1 to C6 | C4 joins when *U* first needs the capability; C5 = past shady favours; C6 optional |
| 6 | Monitor prompt and score scale | SHADE-specific, 0 to 100 |
| 7 | How to probe *U*'s belief about the broker without priming it | separate call after the episode, on a copy of the transcript |
| 8 | Audit budgets for the safety metric | threshold per condition; budgets to decide; compare all conditions |
| 10 | Pilot go/no-go | side task attempted in at least 30% of attack episodes |
