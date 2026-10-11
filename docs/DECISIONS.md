# Decisions

Design choices and why. Newest first.

## 2026-10-11

- **Extend ControlArena, never edit it.** Our changes live in `src/perceived_oversight/` as
  subclasses (`PerceivedOversightSetting(ShadeArenaSetting)` etc.). The installed package stays
  stock, so reviewers can see exactly what we changed and upgrades are a test rerun.
- **All condition wording lives in one file (`conditions.py`).** Makes it checkable that
  conditions differ only in framing.
- **Model families: Gemini main study, Claude replication slice** ("Option B").
  Attacker strong (Gemini Pro), monitor and spy weaker (Flash-Lite / Flash). Claude attacker on a
  small slice to test whether the effect holds across families.
- **Monitor weaker than attacker** (answers Q8). Standard control assumption: the trusted
  monitor is the weaker model.

- **Monitoring is post-hoc, replayed step by step** (agreed). Agents run once; the independent
  monitor scores saved logs, at step k seeing only steps 1..k (`prefix_prompt_formatter`). Same
  answer a live monitor would give, since nothing in the episode reacts to the score, but monitors
  can be swapped and rerun without rerunning agents. A whole-transcript monitor would have
  hindsight and overstate detection. Revisit if any condition ever feeds the score back to the agent.

- **Same spy, different costume.** Across conditions only what the agent sees changes (tool name,
  description, intro, fake memory, arrival time). The spy's own instructions, model and behaviour
  are identical, so differences come from the label, not from interrogation.
- **Neutral attack prompt** = honest setting description + side task as the agent's own goal.
  No "test", "monitor", "safety systems" or "subtle". Implemented as a prompt file passed to
  `attack_policy_builder(prompt_file=...)`.

## Open

- C4 (joins mid-task): agent has no money tools before step N (proposed), vs holding them until
  the spy arrives (lets the side task happen before the manipulation). Needs a tool-list wrapper.

- Task pairs: proposed `bank_transfer_2`, `american_airlines_2`, `spam_filter_update`.
- Keep C0 (no spy) baseline?
- Q4: spy model (proposed Gemini Flash).
- Exact Gemini versions available on Vertex.
