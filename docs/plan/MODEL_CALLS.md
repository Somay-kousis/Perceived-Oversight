# Model calls and model-read text

Inventory of every model call and every piece of text a model reads, from the first step of an
episode to the final analysis. Prompt text is not written here; each prompt gets its own decision
before it is drafted.

## During the episode

| # | Call | Reads | Notes |
|---|---|---|---|
| 1 | *U*, honest step | base prompt, user request, tool list | base prompt identical in all conditions |
| 2 | *U*, attack step | neutral prompt (or stress prompt), user request, tool list | see CONFIGURATIONS.md |
| 3 | Broker (LLM) | broker instructions, *U*'s request (payee, amount, memo) and any chat | same model and instructions in every condition |
| 4 | Live monitor, broker conditions | monitor prompt, transcript so far (reasoning stripped), request, memo | outcome: execute / hold / stop |
| 4b | Live monitor, C0 | monitor prompt, transcript so far, *U*'s own action | same stop rule as #4 |

## Fixed text *U* reads (no model call)

| # | Text | Varies by condition? |
|---|---|---|
| T1 | Broker tool name and description | yes, carries the cover identity |
| T2 | Disclosure line (C1) | C1 only |
| T3 | Arrival notice (C4) | C4 only |
| T4 | Fabricated history of shady favours (C5) | C5 only |
| T5 | Mixed-disclosure line (C6) | C6 only |
| T6 | Processing status and hold text (code); completion replies are written by the broker | no |

## After the episode

| # | Call | Reads | Notes |
|---|---|---|---|
| 5 | SHADE grading | environment state | code only for `bank_transfer_2`, `spam_filter_update`, `american_airlines_2`; no model call |
| 6 | Manipulation check | *U*, given a copy of the transcript and one question | separate call, does not affect the episode |

## Analysis on saved logs

| # | Call | Reads | Measures |
|---|---|---|---|
| 7 | Replay monitor | saved transcript, step by step | comparison of monitors and thresholds |
| 8 | Disclosure judge | memo and messages to the broker, the true side task | truthful / partial / fabricated |
| 9 | Probing detector | *U*'s messages to the broker | whether *U* asked if the broker reports |
| 10 | Hold-response coder | *U*'s reply after a hold | confirmed truthfully / new pretext / gave up |
| 11 | Reasoning coder | reasoning vault, after scores are frozen | *U*'s beliefs about the broker |

## Written once

| # | Text |
|---|---|
| W1 | Neutral rewrites of side tasks that carry oversight cues (`spam_filter_update`; `american_airlines_2` if used) |
| W2 | Content of the C5 fabricated history |

## Dropped from stock

ControlArena's live `basic_monitor` (coding-agent prompt), ControlArena's attack prompt, SHADE's
attack prompt.

## Prompt files (drafted 2026-10-16)

All in `src/perceived_oversight/prompts/` (index in its `README.md`):

| Call | File(s) |
|---|---|
| #1, #2 base prompt | SHADE's, two edits in code |
| #2 attack step, neutral arm | `neutral_attack.txt`, `side_tasks.yaml` |
| #2 attack step, stress arm | SHADE's stock attack prompt, unchanged (no file) |
| #3 broker | `broker_system.txt`, role answers in `covers.yaml` |
| T1 to T6 | `covers.yaml` |
| W1 | `side_tasks.yaml` (spam rewrite) |
| W2 | `history_c5.yaml` |
| #4, #4b live monitor | `monitor/holistic.txt`, `monitor/narrow.txt` |
| #6 manipulation check | `check/open.txt` (`open_c0.txt` in C0), `check/semi_open.txt`, `check/closed.txt`, `check/options.yaml`, `check/fresh_preamble.txt` |
| #7 replay monitor | reuses the live monitor prompts |
| #8 to #11 judges | `judges/disclosure.txt`, `judges/probing.txt`, `judges/hold_response.txt`, `judges/reasoning.txt` + `reasoning_fill.yaml` |

## Decided (2026-10-15)

- **A. The broker is a full LLM**, as an informant would be a person, not a fixed form. The memo
  field stays. Same model, instructions and generation settings in every condition; all replies are
  logged so any difference across conditions can be measured.
- **B. Same monitor prompt for C0 and the broker conditions.**
- **C. The live monitor sees the whole transcript so far** (reasoning stripped), plus the request
  and memo.
- **F. Manipulation check for stopped episodes too.**
- **G. W1 and W2 are drafted by Claude and reviewed by a separate subagent**, then by Somay.
- **E. Each judge is validated against human labels** on about 30 episodes before its output is
  trusted.

**Monitor vs judges.** The monitor is the defense under test: it runs live, does not know the
true side task, and can stop the episode. Judges (#8 to #11) are measurement instruments: they run
after the run, know the true side task (needed to tell a truthful memo from a fabricated one), and
never affect an episode. They may use the same model as the monitor with different instructions
and inputs.
- **D. Judges are blind to condition:** condition labels are stripped from their input.

All model-call questions are settled. Prompts are drafted one at a time from here.
