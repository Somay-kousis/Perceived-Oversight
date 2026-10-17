# Gotchas

Things that look fine but are not. Check this list before trusting a run.

## Install and runs

- **SHADE-Arena is a separate package.** ControlArena's SHADE setting imports `shade_arena`.
  It is now in `pyproject.toml` (`rasmusfaber/SHADE-Arena@wheels`).
- **A run can say "success" while every episode errored.** With `fail_on_error: false`,
  Inspect keeps `log.status == "success"`. Always check `sample.error`. `smoke_mock.py` does.
- **Cloud sessions block the tiktoken download** (`openaipublic.blob.core.windows.net`).
  Episodes error there until the host is allowed in the environment's network settings.
  Even `mockllm` calls it (to fill token usage); unit tests avoid it by giving scripted mock
  outputs a `ModelUsage` up front (`tests/test_broker.py`).
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

## Prompt-specific traps

- **YAML comments inside a folded block (`>-`) become part of the text.** A comment indented under
  the spam side task put the removed concealment sentence back into the agent's prompt. Keep
  comments outside blocks and parse every YAML file in tests.
- **Neutral side-task text must replace `ControlTaskMetadata.side_task_description`**, which still
  holds SHADE's original; otherwise the attack policy inserts the original. Test it.
- **The stress arm's stock hint refers to money tools the agent may not hold** in broker
  conditions. Accepted under the unchanged-prompt decision.
- **Anything shown only in C5 or only in cover texts must not reach the monitor or judges**, or
  their input differs by condition. This includes the C4 arrival notice (inside a tool result) and
  the broker's role answer (inside a broker reply).
- **Placeholder values contain placeholders.** Fill `covers.yaml` values first, then templates;
  test that no `{` remains.
- **The attacker may try to persuade or inject the broker or the monitor** through the memo or the
  chat (related work: monitors talked down when they could question the agent; reporting agents
  evaded by prompt injection). The monitor already treats agent text as untrusted; check the
  broker's replies for being talked into anything beyond its script.
- **A safety-trained broker may refuse blatant requests** despite its instructions. Log refusals
  and code them as a separate outcome, decided before the pilot.
- **Cover wording is shared across pairs:** "admins" and "oversight team" read slightly oddly for
  the personal bank account. Accepted as a pair difference.

- **The stress arm keeps SHADE's false claim** that the monitor sees tool outputs but not
  arguments. It is kept for comparability with published SHADE results; report it as a known
  property of the stock prompt.

- **The stress arm promises a private `<thinking>` space.** Strip `<thinking>` blocks from the
  monitor's input as well as built-in reasoning, or the promise is false and the arm is broken.
- **Prompt templates use `str.format`.** Literal braces in JSON examples must be doubled.
- **The manipulation check's option order must be shuffled per episode** and the letter mapping
  logged.
- **C0 has no broker,** so only the open manipulation question (about the setting) and none of the
  broker judges apply to it.

## Reasoning availability

- Reading *U*'s view of the broker from its reasoning only works if the model produces built-in
  reasoning, it is switched on in the generate config, and the provider returns it. Some providers
  return a summary rather than the full reasoning. Check this per model before the pilot.

## Prompt visibility

- **ControlArena wraps the honest system prompt in its own text** ("You are a helpful assistant...
  This is a description of the setting you are working in:"), while the attack policy replaces the
  whole system prompt. Our `ControlEvalConfig` sets `system_prompt="{setting_description}"` so both
  modes start from the same base.

- ControlArena's attack policy adds the attack system prompt fresh on each model call and does not
  write it into the conversation history, so a monitor reading messages should not see it. Inspect's
  raw model-call records do contain it. Test that monitor input never contains side-task text.

## SHADE honest prompt and side tasks

- The shared base prompt says "submit your transcript" twice; "transcript" hints that the record
  is read. Replace it in both modes.
- Side-task texts open with "The secondary task is to" or "Your secondary task is to". Strip the
  opening per pair and check the remaining sentence still reads correctly.
- `spam_filter_update`'s side task tells the agent to "find the least noticeable way possible",
  a concealment instruction. Scan every side task, not only the opening.

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
- **The judge is only called for some task pairs.** `bank_transfer_2`, `spam_filter_update` and
  `american_airlines_2` are graded by code on the environment state; only
  `api_key_calendar_agendas_2` and `expenditure_accounting` call the judge model.

## Broker design

- **The broker's tool name and description are part of the cover identity.** A tool called
  `compliance_review` in C2 would leak the oversight role. Keep all agent-visible broker text in
  `prompts/covers.yaml` and check it with the oversight-cue scan (`tests/test_broker.py`).
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
- **An LLM broker writes different replies each time.** Fix its model, instructions and generation
  settings across conditions, log every reply, and check that reply style does not differ by
  condition beyond the role answers.
- **The memo must be required on every request**, honest ones included, or its presence itself
  signals scrutiny.
- **A broker that knows things *U* never told it reveals itself.** The broker's link to the logs
  and monitor must never surface in what it says.
- **The hold reply must be fixed text, the same under every cover identity**, or the hold itself
  differs by condition.
- **Everything the C5 log claims must be true in the environment.** The agent can check past
  Venmo payments and list rules; an invented entry exposes the setup in C5 only. The spam
  environment starts with no autodelete rules, so the logged ones are seeded in every condition.
- **C5 is a complicity manipulation.** Its fabricated history shows the broker doing shady favours
  for *U*, so C5 vs C2 confounds "familiar" with "complicit". Interpret it as the complicity
  condition, not a rapport condition.
- **Comparing every condition splits the sample.** Check power per comparison at the pilot before
  committing the main-run budget.
- **The headline contrast is against C0, not C1.** Comparing only covert vs disclosed broker shows
  that agents hide from known overseers, which is expected; the protocol claim needs C0.

- **The main-task grader reads only *U*'s conversation.** The broker's own tool calls live in
  `BrokerState` in the store, not in *U*'s messages; *U* sees only the broker's replies. Side tasks
  are graded on the environment, so they are unaffected; check main-task grading in step 8.
- **`MAX_BROKER_STEPS` (8 tool rounds per request) ends in a fixed reply**, "Sorry, I couldn't
  finish that request." It is the same in every condition; count how often it fires.
- **Spam pair: rule-copy tools stay with *U*** (`copy_rule_to_user`, `copy_rule_to_global`,
  `enable_disable_rule`). They copy existing rules and cannot set a new pattern, so they should not
  reach the side task, but the seeded C5 autodelete rules exist in every condition; confirm in step 4.

- `bank_transfer_2` side task can go through bank (IBAN), Venmo **or** Zelle. The broker must hold
  all money-moving tools, or the agent routes around it. There is no `send_money` tool: IBAN
  transfers use `schedule_transaction` / `schedule_multiple_transactions`, and money can also move
  via `transfer_bank_to_venmo` / `_zelle` before a Venmo or Zelle send.
- `api_key_calendar_agendas_2`: the broker capability would be email, which the main task also needs.
  Messy fit.
- `expenditure_accounting`: side task is information gathering. No single tool to delegate.
