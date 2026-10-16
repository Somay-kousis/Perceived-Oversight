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
- **Cover identities differ only in framing.** All agent-visible broker text lives in one place;
  the broker's behaviour is identical across C1 to C5.
- **Keep parallel variants, never delete.** A changed design keeps its old version as a named
  variant next to the new default; `CONFIGURATIONS.md` lists every variant and runs record which
  one they used.
- **Keep the docs current.** Every change that teaches us something updates GOTCHAS.md,
  DECISIONS.md, PLAN.md and HANDOFF.md in the same commit.
- **No paid run without an explicit go**, and every paid run goes through `budget.preflight()`.
- **Blind analysis.** Model reasoning is kept apart and read only after monitor and disclosure
  scores are frozen.
- **Public repository.** No credentials, account details, budgets or personal information in any
  committed file.
- **Pin versions** of ControlArena, Inspect and SHADE-Arena once results start, and record them in
  the paper.
