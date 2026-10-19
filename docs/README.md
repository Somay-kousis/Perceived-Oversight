# Documentation

Everything about the project that is not code, one folder per kind of document.

| Folder | What goes in it | Start with |
|---|---|---|
| [research/](research/) | Problem and contribution, methods as built, results | [FRAMING.md](research/FRAMING.md), [METHODS.md](research/METHODS.md), [RESULTS.md](research/RESULTS.md), [MODEL_SCREENING.md](research/MODEL_SCREENING.md), [PILOT_DEBUG.md](research/PILOT_DEBUG.md) |
| [plan/](plan/) | Build order and status, every configurable option, every model call | [PLAN.md](plan/PLAN.md), [CONFIGURATIONS.md](plan/CONFIGURATIONS.md), [MODEL_CALLS.md](plan/MODEL_CALLS.md) |
| [architecture/](architecture/) | How ControlArena works and where the experiment plugs in | [ARCHITECTURE.md](architecture/ARCHITECTURE.md) |
| [decisions/](decisions/) | Design choices with their rationale, dated, and open questions | [DECISIONS.md](decisions/DECISIONS.md) |
| [gotchas/](gotchas/) | Traps that look fine but are not; check before trusting a run | [GOTCHAS.md](gotchas/GOTCHAS.md) |
| [citations/](citations/) | Cited papers, verified, with what each is used for | [REFERENCES.md](citations/REFERENCES.md) |
| [guides/](guides/) | Installation and running | [SETUP.md](guides/SETUP.md) |

## Conventions

- **One topic, one place.** A fact lives in one document; others link to it.
- **Decisions are dated**, newest first; superseded decisions are marked, not removed.
- **Superseded designs stay available as named variants**, listed in CONFIGURATIONS.md; every run
  records which variants it used.
- **ControlArena, Inspect and SHADE-Arena are extended, never modified** (subclasses and wrappers in
  `src/perceived_oversight/`). Versions are pinned and reported with results.
- **Blind analysis.** Agent reasoning is stored separately and read only after monitor and
  disclosure scores are frozen.
- **Citations are verified** (title, authors, identifier) before they enter REFERENCES.md.
- **No credentials, account details or budgets** in tracked files; money caps live in the untracked
  `config/budget.local.yaml`.
