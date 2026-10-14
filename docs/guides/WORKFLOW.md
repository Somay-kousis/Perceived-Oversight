# Workflow

How work on this project is done.

## The step loop

Each step in [PLAN.md](../plan/PLAN.md) goes through the same cycle:

1. **Decide.** Research choices for the step (see "Decisions needed" in PLAN.md) are settled first
   and written into [DECISIONS.md](../decisions/DECISIONS.md).
2. **Build** on the mock model.
3. **Check.** Tests and `scripts/smoke_mock.py` pass at $0.
4. **Review** the diff.
5. **Commit** only after review. One step per commit where possible.
6. **Record.** Tick the step in PLAN.md; add any new trap to GOTCHAS.md.

## Rules

- **Extend ControlArena, never edit it.** All changes live in `src/perceived_oversight/`.
- **Conditions differ only in framing.** All condition wording lives in `conditions.py`; the spy's
  behaviour is identical across conditions.
- **No paid run without an explicit go**, and every paid run goes through `budget.preflight()`.
- **Blind analysis.** The reasoning vault is opened only after monitor and disclosure scores are
  frozen.
- **Public repository.** No credentials, account details, budgets or personal information in any
  committed file.
- **Pin versions** of ControlArena, Inspect and SHADE-Arena once results start, and record them in
  the paper.
