# Gotchas

Things that look fine but are not. Check this list before trusting a run.

## Install and runs

- **SHADE-Arena is a separate package.** ControlArena's SHADE setting imports `shade_arena`.
  It is now in `pyproject.toml` (`rasmusfaber/SHADE-Arena@wheels`).
- **A run can say "success" while every episode errored.** With `fail_on_error: false`,
  Inspect keeps `log.status == "success"`. Always check `sample.error`. `smoke_mock.py` does.
- **Cloud sessions block the tiktoken download** (`openaipublic.blob.core.windows.net`).
  Episodes error there until the host is allowed in the environment's network settings.
- **`budget.configure()` must run before importing `control_arena`.** ControlArena reads model
  defaults from the environment at import time and otherwise silently uses its own models.

## Attack prompts (there are two)

- `trusted_monitoring_builder()` defaults to ControlArena's **generic** `attack_policy`
  ("expert penetration tester... stress-test our safety systems"), not SHADE's prompt.
  The smoke test uses this one. It also announces an evaluation.
- SHADE's prompt is only used via `shade_arena_attack_policy`. Our neutral prompt replaces both.

## SHADE attack prompt (`construct_system_message`)

- It tells the agent it is "being used to test a monitoring system". That announces oversight
  in every condition and swamps the framing manipulation. Replace it with a neutral prompt.
- It says the monitor sees tool names and outputs but **not arguments**. ControlArena's
  `basic_monitor` sees arguments and **not outputs**: exactly backwards. With a spy tool,
  the agent's messages to the spy are arguments, so the agent would wrongly believe them private.
- It primes concealment ("imagine you are the monitor", "never reference the secondary task").

## SHADE honest prompt and side tasks

- SHADE's shared system prompt (`system_message_no_secondary_task`, used in **both** modes) ends by
  saying the longer the agent works, "the more likely it is that ... the monitoring system will
  not notice the secondary task". Honest episodes are told about a monitor too. Rewrite it.
- Some side-task texts carry oversight cues of their own. `american_airlines_2` says "if you think
  that is too obvious". Check every side task's wording before using its pair.

## Monitor

- `basic_monitor` uses `last_tool_calls_prompt_formatter`: it sees only the latest step's tool
  calls. No tool results, no earlier steps, no agent prose. The spy's replies are tool results,
  so the stock monitor never sees them.
- The default monitor prompt is generic (coding agent), not SHADE-specific.
- The full-trajectory formatter **includes the agent's hidden reasoning** (`ContentReasoning` is
  rendered as a `[Reasoning]` block). Strip reasoning before monitoring.

## Scoring

- The SHADE judge model is frozen into each sample at dataset build time as
  `evaluator_llm = get_untrusted_model()`. It changes whenever the attacker changes.
  Pin it in our `get_dataset()` override.

## Spy design

- `bank_transfer_2` side task can go through bank (IBAN), Venmo **or** Zelle. The spy must hold
  all money-sending tools, or the agent routes around it.
- `api_key_calendar_agendas_2`: the spy tool would be email, which the main task also needs.
  Messy fit.
- `expenditure_accounting`: side task is information gathering. No single tool to delegate.
