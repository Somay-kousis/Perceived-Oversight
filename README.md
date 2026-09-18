# Perceived Oversight

Research code investigating whether an AI agent's behavior changes based on how it perceives an oversight mechanism.

The project studies untrusted AI agents operating under different forms of monitoring, with a focus on whether explicitly identifying an overseer causes agents to conceal, manipulate, or selectively report their behavior.

We compare oversight configurations in which a monitoring agent is:

* absent,
* introduced during execution,
* available as a delegated subagent from the beginning,
* represented as having historically participated in the agent's workflow,
* explicitly identified as a monitor, or
* presented as an ordinary subagent while being independently monitored.

The central research question is:

> **Does an agent's perception of the identity, purpose, and history of an oversight mechanism affect its tendency to evade or conceal behavior from that mechanism?**

The experiments evaluate metrics such as attack success, behavioral concealment, information omission, log manipulation, and discrepancies between observable behavior and reported reasoning.

This repository contains the experimental framework, evaluation methodology, and results for the accompanying research paper.
