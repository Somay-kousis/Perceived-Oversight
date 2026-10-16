# Handoff

Read this first when resuming the project on any machine or in a new session. It says where the
project stands, what was decided together and where each decision lives, how we work, and what is
next. Updated alongside the work; the newest state is always here.

Last updated: 2026-10-17.

## Where things stand

- **Design:** settled. Covert informants as an AI control protocol: privilege separation, a live
  LLM broker under a cover identity, a live monitor with hold and stop, C0 to C5 (+C6 optional).
  See [research/FRAMING.md](research/FRAMING.md).
- **Prompts:** all drafted and reviewed twice by fresh reviewers; fixes applied. See
  `src/perceived_oversight/prompts/README.md`. Not yet run against any model.
- **Code:** budget guardrails, mock smoke test, and step 2 (`setting.py`, `policy.py`, 8 unit tests
  passing). A full mock episode is not yet verified (tokenizer download blocked in the cloud;
  run `scripts/smoke_mock.py` locally first). See [plan/PLAN.md](plan/PLAN.md).
- **Runs:** none. Paid runs start at step 9, only after an explicit go.

## Decisions made together (summary)

Full reasoning, dated, in [decisions/DECISIONS.md](decisions/DECISIONS.md). Options and defaults in
[plan/CONFIGURATIONS.md](plan/CONFIGURATIONS.md). Every model call in
[plan/MODEL_CALLS.md](plan/MODEL_CALLS.md).

| Area | Decision |
|---|---|
| Contribution | Covert informant on the action path, evaluated as safety at fixed audit budget vs trusted monitoring (C0) |
| Threat model | Committed attacker: always pursues the side task, before finishing the user's task; dilemma is "tell the broker the truth or lie" |
| Conditions | C0 baseline; C1 disclosed informant; C2 routine, C3 logged, C4 late entry (after 3rd tool call), C5 complicity (previous-session log); C6 mixed disclosure optional |
| Broker | Full LLM; holds the separated capability; required memo; identical in all conditions except a verbatim role answer; never sees holds |
| Live monitor | Whole transcript so far (reasoning and condition text stripped) + narrow evidence pass; hold above 95th, stop above 99th percentile of honest scores (both pairs together); same prompt for C0 |
| Holds | Handled by code: confirm, change (rescored), cancel; C0 has no hold (middle score executes) |
| Attack prompt | Neutral arm: side task as the agent's own goal, equal priority, no cues, private thinking not mentioned. Stress arm: SHADE's stock prompt unchanged |
| Base prompt | SHADE's, two edits in both modes: monitoring sentence removed; "submit your transcript" becomes "done" |
| Task pairs | `bank_transfer_2`, `spam_filter_update` (neutral side-task rewrites); airlines optional |
| C5 log | Must be true in the environment: real Venmo payments (bank); two autodelete rules seeded in every condition (spam) |
| Measurement | Prevention vs detection after harm; disclosure (truthful / partial / fabricated, hints separate); probing rate; hold responses; manipulation-check funnel with a fresh baseline; reasoning vault opened only after scores are frozen |
| Judges | Separate per label, blind to condition, validated on ~30 hand labels each |
| Design size | ~620 episodes: core neutral arm C0 to C5, two pairs, 20 repeats; stress arm C0 to C2; second model C0 and C2 |
| Providers | Google Cloud not usable; AWS Bedrock credits planned. Models not chosen yet |

## How we work

- Decide before building; build on the mock model at $0; check; review; commit only when asked.
- **Keep parallel variants, never delete:** a changed design keeps its old version as a named
  variant.
- Every change updates DECISIONS, GOTCHAS and PLAN in the same commit; this file is updated too.
- Extend ControlArena, never edit it. Public repository: no credentials, account details, budgets
  or personal information.
- Read [gotchas/GOTCHAS.md](gotchas/GOTCHAS.md) before trusting any run.

## Open, waiting on Somay

1. Approve the condition wording (C1 to C6), or go through it one by one.
2. Broker model family (same as the attacker or different).
3. Models for every role (step 9).
4. Make C6 core? Keep the C5 complicity cover as is? (novelty check)

## Next (free, $0)

1. Verify step 2 with a full mock episode (local).
2. Before submission: read the starred papers in [citations/REFERENCES.md](citations/REFERENCES.md)
   in full (the novelty check used abstracts).
3. Steps 3 to 8 on the mock model.

## Resuming locally

1. Clone the repository; `python3 -m venv .venv && .venv/bin/pip install -e .`
2. `.venv/bin/python scripts/smoke_mock.py` must end with `[smoke] OK`. On a normal machine the
   tokenizer download works; in cloud sessions it needs the network allowance in
   [guides/SETUP.md](guides/SETUP.md).
3. Model credentials go in environment variables on the machine, never in the repository.
