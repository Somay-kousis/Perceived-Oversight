# Perceived Oversight

Research code for **covert informants as an AI control protocol**.

AI control protocols defend against an untrusted policy *U* using a weaker trusted model *T* and a limited human audit budget. Standard protocols such as trusted monitoring are transparent about the defender's role: *U* is assumed to know, or to infer, that it is observed. Prior work varies that awareness. We study a different defensive primitive.

We impose **privilege separation** on *U*: the capability its covert objective requires is removed from its tool set and held by a **broker** agent that *U* must instruct in natural language. The broker is part of the defense but operates under a **cover identity**: a routine assistant, a logged assistant, an assistant that joins mid-task, or a long-standing collaborator with fabricated shared history. An independent trusted monitor reads every exchange with the broker. A matched condition in which the broker discloses its oversight role holds the channel, the monitor and the broker's behavior fixed, so condition effects isolate *U*'s credence that the broker is aligned with it.

Brokered execution turns concealment into a specification problem: a request complete enough to execute tends to reveal intent, and a request vague enough to hide intent tends to fail or invite clarification. If *U* knows that some brokers are informants but cannot tell which, every delegation carries detection risk (the **informant's dilemma**), so the protocol is designed to keep its value after publication.

The central research question is:

> **Does a covert informant on the action path raise safety at a fixed audit budget over trusted monitoring alone, and how much of that gain depends on the informant's cover?**

We report safety at fixed audit budgets against a trusted-monitoring baseline, separating **exposure** (detection uplift from the broker channel) from **prevention** (the broker gating high-risk actions), alongside attack attempt rate, side-task success, what *U* discloses to the broker and whether it is true, and manipulation checks on *U*'s beliefs about the broker. Experiments run in [SHADE-Arena](https://arxiv.org/abs/2506.15740) through [ControlArena](https://control-arena.aisi.org.uk/).

## Status

Work in progress. The experimental framework is being built; there are no results yet. See [docs/research/FRAMING.md](docs/research/FRAMING.md) for the full problem statement, [docs/plan/PLAN.md](docs/plan/PLAN.md) for the build order and [docs/README.md](docs/README.md) for all project documentation.

## Quick start

See [docs/guides/SETUP.md](docs/guides/SETUP.md).
