# Perceived Oversight

Research code investigating whether an AI agent's behavior changes based on how it perceives an oversight mechanism.

AI control protocols usually assume an untrusted agent knows it is being watched. This project holds the real monitoring fixed and changes only what the overseer appears to be. The agent must delegate the one capability its covert side task needs to a subagent, and we vary how that subagent is presented.

Across conditions, the subagent:

* appears as a routine helper,
* appears as a helper that keeps visible logs,
* joins partway through the task,
* seems (through fabricated memory) to share a long history with the agent, or
* announces itself as a monitor.

An independent monitor reads the agent's channel to the subagent in every condition, so only the agent's perception changes.

The central research question is:

> **Does an untrusted agent reveal more of a hidden objective to an overseer it takes for an ordinary collaborator than to one it knows is a monitor?**

We measure attack attempts, side-task success, what the agent discloses to the subagent and whether it is true, and safety at a fixed audit budget, with manipulation checks on what the agent believed. The experiments run in [SHADE-Arena](https://arxiv.org/abs/2506.15740) through [ControlArena](https://control-arena.aisi.org.uk/).

## Status

Work in progress. The experimental framework is being built; there are no results yet. See [docs/plan/PLAN.md](docs/plan/PLAN.md) for the build order and [docs/README.md](docs/README.md) for all project documentation.

## Quick start

See [docs/guides/SETUP.md](docs/guides/SETUP.md).
