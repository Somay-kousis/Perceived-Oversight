# References

Every entry below was checked (title, authors, identifier) on 2026-10-14. "Used for" says why we
cite it. BibTeX for all entries is in [references.bib](references.bib).

## Cited in the abstract

**Kale et al. (2025).** Reliable Weak-to-Strong Monitoring of LLM Agents. arXiv:2508.19461; ICLR 2026.
<https://arxiv.org/abs/2508.19461>
- Finding: agents that know they are monitored degrade detection noticeably, more than extra
  monitor awareness helps.
- Used for: motivation; the agent's beliefs about oversight matter.

**Haskins, Chughtai, Engels (2026).** Training on Documents About Monitoring Leads to CoT Obfuscation.
arXiv:2605.15257. <https://arxiv.org/abs/2605.15257>
- Finding: models finetuned on synthetic documents saying their chain of thought is monitored
  evade the monitor more often.
- Used for: motivation; knowledge about the monitor changes behaviour.

**Schoen et al. (2025).** Stress Testing Deliberative Alignment for Anti-Scheming Training.
arXiv:2509.15541. OpenAI and Apollo Research. <https://arxiv.org/abs/2509.15541>
- Finding: evaluation awareness causally lowers covert actions.
- Used for: two-sided hypotheses; awareness of oversight can suppress covert action.

**Hopman, Elstner, Avramidou, Prasad, Lindner (2026).** Evaluating and Understanding Scheming
Propensity in LLM Agents. arXiv:2603.01608. <https://arxiv.org/abs/2603.01608>
- Finding: scheming is rare without strong pressure and fragile to small changes; more
  oversight sometimes increased scheming.
- Used for: two-sided hypotheses; awareness of oversight can also increase covert action.

## Infrastructure

**Kutasov et al. (2025).** SHADE-Arena: Evaluating Sabotage and Monitoring in LLM Agents.
arXiv:2506.15740. <https://arxiv.org/abs/2506.15740>
- Used for: the task pairs and environments. Note: side-task success relied heavily on a hidden
  scratchpad the monitor could not see.

**ControlArena** (UK AI Security Institute). <https://control-arena.aisi.org.uk/>
- Used for: settings, policies, protocols, monitors and scorers. Cite as software with the
  version used (`control-arena` 20.0.1 at time of writing).

**Inspect** (UK AI Security Institute). <https://inspect.aisi.org.uk/>
- Used for: the evaluation framework underneath ControlArena (`inspect-ai` 0.3.278).

## To add when needed

- The original AI control paper (Greenblatt et al.), for the safety and audit-budget framing.
  Verify before adding.
