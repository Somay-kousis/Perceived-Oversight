# References

Every entry below was checked (title, authors, identifier) on 2026-10-14. "Used for" says why we
cite it. BibTeX for all entries is in [references.bib](references.bib).

## Cited in the abstract

**Kale et al. (2025).** Reliable Weak-to-Strong Monitoring of LLM Agents. arXiv:2508.19461; ICLR 2026.
<https://arxiv.org/abs/2508.19461>
- Finding: agents that know they are monitored degrade detection noticeably, more than extra
  monitor awareness helps.
- Used for: motivation; prior work varies awareness of a passive monitor, the gap we move past.

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

## Closest prior work (novelty check, 2026-10-17)

Checked from abstracts, search excerpts and code repositories; full texts were not reachable from
the cloud environment. Read the starred ones in full before submission.

- ★ **Krakovna, Lindner, Ho, Farquhar, Shah (2026).** Realistic honeypot evaluations for scheming
  propensity. arXiv:2605.29729. Plants opportunities; no counterpart agent.
- ★ **Phuong, Zimmermann, et al. (2025).** Evaluating Frontier Models for Stealth and Situational
  Awareness. arXiv:2505.01420. Oversight disclosed or passive; one task has an openly reviewing
  manager.
- ★ **Greenblatt et al. (2023).** AI Control: Improving Safety Despite Intentional Subversion.
  arXiv:2312.06942. Honeypots with fake collusion signals test the untrusted *monitor*.
- ★ Shutdown sabotage propensities in multi-agent systems. arXiv:2609.28274 (authors not
  confirmed). Capability-denied agent recruits a neutral peer; closest structure.
- ★ Kutasov et al. (2025). Control evaluations in SHADE-Arena, including deferring critical actions.
  arXiv:2511.02997.
- Factor(U,T) control protocol. arXiv:2512.14745 (authors not confirmed).
- Hasan (2026). Honeypot Protocol. arXiv:2604.13301 (Apart hackathon).
- Wehner and Kraprayoon. Honeypots for AI agent insider threats (IAPS report; year not confirmed).
- Potter et al. (2026). Peer-preservation. arXiv:2604.19784.
- Scheurer, Balesni, Hobbhahn (2023). arXiv:2311.07590.
- Finnveden (2025). Being honest with AIs (Redwood Research blog).
- Debenedetti et al. (2025). CaMeL. arXiv:2503.18813.

Full notes: kept outside the repository (research_notes/Novelty check).
