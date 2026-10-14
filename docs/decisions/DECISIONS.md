# Decisions

Design choices and why. Newest first.

## 2026-10-14

- **Framing: covert informants as a control protocol.** The contribution is a defensive primitive
  (privilege separation plus a broker under a cover identity), evaluated as safety at fixed audit
  budget against trusted monitoring. Not a study of whether agents hide from known monitors.
  Full statement in [FRAMING.md](../research/FRAMING.md).
- **C0 is the mandatory baseline protocol** (trusted monitoring alone). C1 is the
  disclosed-informant condition and tests robustness under disclosure.
- **Vocabulary fixed:** *U*, *T*, broker, informant protocol, cover identity, exposure, prevention.
  "Spy", "helper", "costume" are no longer used in docs or code (`spy.py` becomes `broker.py`).
- **Exposure and prevention are reported separately.**

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

- **Monitoring is post-hoc, replayed step by step** (agreed). Agents run once; the independent
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

- **Broker mode:** pass-through (exposure only), gating (prevention), or both. Suggested: both.
- **Novelty check** against honeypot evaluations, untrusted monitoring and collusion, and stealth
  evaluations with an oversight mechanism, before the paper claims novelty.

- C4 (joins mid-task): agent has no money tools before step N (proposed), vs holding them until
  the broker arrives (lets the side task happen before the manipulation). Needs a tool-list wrapper.

- Task pairs: proposed `bank_transfer_2`, `american_airlines_2`, `spam_filter_update`.
- Models for *U*, broker, monitor and judge (AWS Bedrock; see Bedrock catalog).
