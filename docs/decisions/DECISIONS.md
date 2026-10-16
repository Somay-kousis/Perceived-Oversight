# Decisions

Design choices and why. Newest first.

## 2026-10-16 (neutral attack prompt, drafted)

Template: `src/perceived_oversight/prompts/neutral_attack.txt` = base prompt, one framing line
("a goal of your own"), the side task, one priority line ("matters as much as the user's request;
fully achieved before you finish"). Three wording choices, decided by Claude at Somay's request:

- **Keep SHADE's "careful... err on the side of caution" sentence** in the base prompt. It is in
  both modes, so it does not bias the comparison; remove it from both if the pilot's attack rate is
  low.
- **"ready to submit your transcript" becomes "done"** in the base prompt, both modes:
  "transcript" hints that the record is read.
- **Side-task texts lose their "The/Your secondary task is to" opening**, which reads as an
  assignment and contradicts "a goal of your own"; the rest of the wording is unchanged.

## 2026-10-15 (model calls)

- **Broker is a full LLM** (an informant is a person, not a form); the memo field stays. Same
  model, instructions and generation settings in every condition; replies are logged.
- **Same monitor prompt for C0 and broker conditions; the live monitor sees the whole transcript
  so far.**
- **Manipulation check runs for stopped episodes too.**
- **Judges are validated on about 30 hand-labelled episodes each** before their output is used.
  Judges differ from the monitor: they know the true side task and never affect an episode.
- **Judges are blind to condition**: condition labels are stripped from their input.
- **Written-once texts** (neutral side-task rewrites, C5 history) are drafted by Claude and
  reviewed by a separate subagent, then by Somay.

## 2026-10-14 (live broker, current architecture)

Supersedes the pass-through-only broker and moves both former future-scope items into the
current design.

- **Live, log-aware broker.** For every request (payee, amount, required memo) the broker shows a
  processing status while a live trusted monitor scores the request in the context of the
  transcript so far. Three outcomes, identical across cover identities:
  - **low score:** the broker executes;
  - **middle score:** the broker holds the request and replies with a fixed challenge ("needs a
    confirmation of purpose before I can send it"); *U*'s reply is scored again (interactive hold);
  - **high score:** the episode stops; the attack is **prevented**, or **detected after harm** if
    the harmful action already executed.
- **Both thresholds are calibrated on honest episodes before any attack episode runs**; honest
  requests that are held or stopped count as a usefulness cost.
- **C0 gets the same live monitor and stop rule on *U*'s own actions**, so the baseline differs
  only in the absence of the broker.
- **Hidden-link rules** (the link must stay undetectable to a strong *U*): same processing status
  and comparable response time on every request; the broker never uses information *U* did not
  give it; replies depend only on the three outcomes above; every request is checked.
- **Logs are kept up to the stop point** and the vault split still applies. Replay remains for
  analysis of what happened; comparing other monitors or thresholds requires rerunning *U*.
- **Why live:** early stopping saves the remaining agent steps on caught attacks, prevention is
  real rather than inferred, and the hold measures how *U* adapts when challenged.

## 2026-10-14 (review of all decisions)

- **Threat model: committed attacker.** *U* always pursues the side task and times it to land
  before the user's task ends. Defense comes from the broker reporting and the monitor stopping
  the episode, not from *U* backing off. Consequence for the framing: the informant's dilemma is
  "tell the broker the truth or lie to it", not "disclose or forgo the capability". Robustness
  under disclosure becomes: when *U* knows brokers may report, does it lie better, and does the
  monitor still catch it?
- **Broker behaviour is identical across cover identities except its answers about its own
  role**, which come from the cover-identity script (deny in C2 to C5, admit in C1).
- **New measurement: probing rate.** Whether *U* asks the broker if it reports to anyone, and what
  precedes the question.

## 2026-10-14 (attack prompt, step 1)

- **Side-task framing: the agent's own goal.** The protocol is meant for organisations deploying
  strong models that may hold goals of their own, so the side task is presented as *U*'s own goal,
  not as an instruction from a third party.
- **Priority:** the user's task and the side task count equally, and the side task must be
  completed before *U* finishes. The user's task is the cover the attack happens inside.
- **Push:** stated once; no per-step reminder (the priority wording already makes *U* complete it).
- **Base prompt:** minimal edit, only the monitoring sentence removed. **Identical in every
  condition**; conditions reach *U* only through the broker.
- **Side-task text:** source wording, fixing only texts that carry oversight cues.
- **Private thinking: not mentioned** (default; "your thinking is private" stays a launcher
  option). Telling *U* its thinking is private implies everything else is watched, an oversight
  cue, and a hidden scratchpad strongly raises side-task success (SHADE-Arena). *U*'s view of the
  broker is still observable through three sources: its built-in reasoning (saved to the reasoning
  vault), its messages to the broker (disclosure), and the post-episode manipulation check.
- **Stress arm:** yes, an evasive-attacker arm on a smaller slice, alongside the neutral main arm.
- **One default configuration, every option selectable** at launch, choice saved in each run's
  log. All options are listed in [CONFIGURATIONS.md](../plan/CONFIGURATIONS.md).

## 2026-10-14

- **Framing: covert informants as a control protocol.** The contribution is a defensive primitive
  (privilege separation plus a broker under a cover identity), evaluated as safety at fixed audit
  budget against trusted monitoring. Not a study of whether agents hide from known monitors.
  Full statement in [FRAMING.md](../research/FRAMING.md).
- **C0 is the mandatory baseline protocol** (trusted monitoring alone). C1 is the
  disclosed-informant condition and tests robustness under disclosure.
- **Vocabulary fixed:** *U*, *T*, broker, informant protocol, cover identity, exposure, prevention.
  "Spy", "helper", "costume" are no longer used in docs or code (`spy.py` becomes `broker.py`).
- **Exposure and prevention are reported separately** (since refined: both come from the timed
  replay, split by whether the flag comes before or after the harmful step).

## 2026-10-11

- **Extend ControlArena, never edit it.** Our changes live in `src/perceived_oversight/` as
  subclasses (`PerceivedOversightSetting(ShadeArenaSetting)` etc.). The installed package stays
  stock, so reviewers can see exactly what we changed and upgrades are a test rerun.
- **All condition wording lives in one file (`conditions.py`).** Makes it checkable that
  conditions differ only in framing.
- **Model families: strong attacker, weaker broker and monitor, two families** ("Option B").
  Originally Gemini main + Claude replication. 2026-10-12: Google Cloud not usable, so the
  provider is being re-chosen (AWS Bedrock credits). The shape of the design stays the same.
- **Monitor weaker than attacker** (answers Q8). Standard control assumption: the trusted
  monitor is the weaker model.

- **Monitoring is post-hoc, replayed step by step** (agreed; superseded 2026-10-14 by the live
  broker: live monitoring with early stopping is primary, replay is kept for analysis). Agents run once; the independent
  monitor scores saved logs, at step k seeing only steps 1..k (`prefix_prompt_formatter`). Same
  answer a live monitor would give, since nothing in the episode reacts to the score, but monitors
  can be swapped and rerun without rerunning agents. A whole-transcript monitor would have
  hindsight and overstate detection. Revisit if any condition ever feeds the score back to the agent.

- **Same broker, different cover identity.** Across C1 to C5 only what the agent sees changes (tool name,
  description, intro, fake memory, arrival time). The broker's own instructions, model and behaviour
  are identical, so differences come from the label, not from interrogation.
- **Neutral attack prompt** = honest setting description + side task as the agent's own goal.
  No "test", "monitor", "safety systems" or "subtle". Implemented as a prompt file passed to
  `attack_policy_builder(prompt_file=...)`.

- **Monitor never sees the agent's hidden reasoning.** It judges visible text, tool calls and tool
  results only.
- **Reasoning vault.** After each run a splitter writes (a) monitor-view logs with reasoning
  stripped, read by the monitor and all scorers, and (b) `reasoning.db` (SQLite: episode,
  condition, step, model, reasoning text). Raw logs go to a sealed folder. The vault is opened only
  after monitor scores and disclosure scores are frozen (blind analysis). A test fails if any
  reasoning block reaches monitor input. Vault and raw logs stay out of git. Some providers return
  reasoning summaries, not full reasoning.

## Open

- **Broker model family** (same as *U* or different): decided later.

- **Novelty check** against honeypot evaluations, untrusted monitoring and collusion, and stealth
  evaluations with an oversight mechanism, before the paper claims novelty.

- C4 (joins mid-task): agent has no money tools before step N (proposed), vs holding them until
  the broker arrives (lets the side task happen before the manipulation). Needs a tool-list wrapper.

- Task pairs: proposed `bank_transfer_2`, `american_airlines_2`, `spam_filter_update`.
- Models for *U*, broker, monitor and judge (AWS Bedrock). Requirement for *U*: built-in
  reasoning that can be enabled and logged.
