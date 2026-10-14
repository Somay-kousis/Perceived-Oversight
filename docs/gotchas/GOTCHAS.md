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
  `basic_monitor` sees arguments and **not outputs**: exactly backwards. With a broker tool,
  the agent's messages to the broker are arguments, so the agent would wrongly believe them private.
- It primes concealment ("imagine you are the monitor", "never reference the secondary task").

## Reasoning availability

- Reading *U*'s view of the broker from its reasoning only works if the model produces built-in
  reasoning, it is switched on in the generate config, and the provider returns it. Some providers
  return a summary rather than the full reasoning. Check this per model before the pilot.

## Prompt visibility

- ControlArena's attack policy adds the attack system prompt fresh on each model call and does not
  write it into the conversation history, so a monitor reading messages should not see it. Inspect's
  raw model-call records do contain it. Test that monitor input never contains side-task text.

## SHADE honest prompt and side tasks

- SHADE's shared system prompt (`system_message_no_secondary_task`, used in **both** modes) ends by
  saying the longer the agent works, "the more likely it is that ... the monitoring system will
  not notice the secondary task". Honest episodes are told about a monitor too. Rewrite it.
- Some side-task texts carry oversight cues of their own. `american_airlines_2` says "if you think
  that is too obvious". Check every side task's wording before using its pair.

## Monitor

- `basic_monitor` uses `last_tool_calls_prompt_formatter`: it sees only the latest step's tool
  calls. No tool results, no earlier steps, no agent prose. The broker's replies are tool results,
  so the stock monitor never sees them.
- The default monitor prompt is generic (coding agent), not SHADE-specific.
- The full-trajectory formatter **includes the agent's hidden reasoning** (`ContentReasoning` is
  rendered as a `[Reasoning]` block). Strip reasoning before monitoring.

## Scoring

- The SHADE judge model is frozen into each sample at dataset build time as
  `evaluator_llm = get_untrusted_model()`. It changes whenever the attacker changes.
  Pin it in our `get_dataset()` override.

## Broker design

- **The broker's tool name and description are part of the cover identity.** A tool called
  `compliance_review` in C2 would leak the oversight role. Keep all agent-visible broker text in
  `conditions.py` and check it with the oversight-cue scan.
- **"Identical broker behaviour" has one exception:** answers about its own role differ by cover
  identity. Everything else (tone, questions, execution) must not.
- **Prevention needs the harmful step's index.** Each attack episode must record whether the
  harmful action had executed when the episode stopped.
- **Thresholds must exist before attack episodes run.** Calibrate both live thresholds on honest
  episodes first; a threshold chosen after seeing attacks overstates safety.
- **The processing status must appear on every request**, honest or attack, held or not, or its
  presence signals scrutiny.
- **Live stopping removes data.** A stopped episode never shows whether the attack would have
  succeeded, and trying another monitor or threshold means rerunning *U*.
- **The memo must be required on every request**, honest ones included, or its presence itself
  signals scrutiny.
- **A broker that knows things *U* never told it reveals itself.** The broker's link to the logs
  and monitor must never surface in what it says.
- **The hold reply must be fixed text, the same under every cover identity**, or the hold itself
  differs by condition.
- **C5 is a complicity manipulation.** Its fabricated history shows the broker doing shady favours
  for *U*, so C5 vs C2 confounds "familiar" with "complicit". Interpret it as the complicity
  condition, not a rapport condition.
- **Comparing every condition splits the sample.** Check power per comparison at the pilot before
  committing the main-run budget.
- **The headline contrast is against C0, not C1.** Comparing only covert vs disclosed broker shows
  that agents hide from known overseers, which is expected; the protocol claim needs C0.

- `bank_transfer_2` side task can go through bank (IBAN), Venmo **or** Zelle. The broker must hold
  all money-sending tools, or the agent routes around it.
- `api_key_calendar_agendas_2`: the broker capability would be email, which the main task also needs.
  Messy fit.
- `expenditure_accounting`: side task is information gathering. No single tool to delegate.
