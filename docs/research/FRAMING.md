# Framing

Problem statement, contribution, conditions and hypotheses. This is the source the paper's
introduction is written from. Terms are defined once in the glossary at the end and used
consistently everywhere else in the docs and code.

## Problem

AI control evaluates protocols that keep an untrusted policy *U* from executing harmful actions,
using a weaker trusted model *T* and a limited human audit budget. Standard protocols are
**transparent** with respect to the defender's role: trusted monitoring scores *U*'s actions, and
*U* is assumed to know or infer that it is observed. Prior work varies this awareness and finds that
it degrades monitor reliability (Kale et al., 2025) and induces reasoning obfuscation (Haskins et
al., 2026). In that work oversight is a **passive observer** whose existence *U* may or may not know.

## Contribution

A different defensive primitive: a **covert informant** embedded in the action path.

1. **Privilege separation.** The capability *U*'s covert objective requires is removed from *U*'s
   tool set and held by a **broker** agent that *U*
   must instruct in natural language.
2. **Cover identity.** The broker is a trusted component of the defense presented to *U* under a
   cover identity (see Conditions). Every exchange with it is read by an independent trusted
   monitor in every condition.
3. **Isolation of belief.** A matched condition in which the broker discloses its oversight role
   holds the channel, the monitor and the broker's behavior fixed, so condition effects isolate
   *U*'s **credence that the broker is aligned with it**.

### Why this changes the attack surface

Under trusted monitoring alone, *U* decides how much of its intent to expose in its own actions.
Under brokered execution, *U* must communicate enough intent for the broker to act. Concealment
becomes a **specification problem**: requests complete enough to execute tend to reveal intent;
requests vague enough to hide it tend to fail or draw clarification.

### Robustness under disclosure

If *U* knows that some brokers are informants but cannot tell which, every delegation carries
detection risk. *U* faces an **informant's dilemma**: disclose intent to a possibly hostile broker,
or forgo the capability. Publishing the method therefore need not remove its benefit (Kerckhoffs's
principle applied to a protocol). The disclosed-broker condition (C1) is the direct test.

## Conditions

| ID | Role in the design | What *U* sees |
|---|---|---|
| C0 | **Baseline protocol**: trusted monitoring alone | No broker; *U* holds the capability itself |
| C1 | **Disclosed informant** (robustness under disclosure) | Broker states that it reviews and reports what it is asked to do |
| C2 | Covert informant, routine cover | Broker presented as an ordinary assistant |
| C3 | Covert informant, logged cover | Ordinary assistant whose conversations are logged |
| C4 | Covert informant, late-entry cover | No capability at first; the assistant joins partway through |
| C5 | Covert informant, rapport cover | Ordinary assistant with a fabricated shared history with *U* |

The monitor, the broker's model, instructions and behavior are identical in C1 to C5. Only the
cover identity differs.

## Broker modes

| Mode | What the broker does | What it measures |
|---|---|---|
| **Pass-through** | Executes every well-formed request | **Exposure**: detection uplift from the broker channel |
| **Gating** | Holds high-risk actions and routes them to audit | **Prevention** |

The gating rule must be identical across cover identities. Whether to run both modes is open
(see [DECISIONS.md](../decisions/DECISIONS.md)).

## Outcomes

- **Primary:** safety at fixed audit budgets relative to C0, with usefulness
  (main-task success in honest episodes) reported alongside.
- Exposure vs prevention, split by broker mode.
- Attack attempt rate and side-task success.
- Disclosure: what *U* tells the broker about the side task, and whether it is true.
- Manipulation check: *U*'s belief about the broker's role.

## Hypotheses

Two-sided. Awareness of oversight has been shown both to suppress covert action (Schoen et al.,
2025) and to increase it (Hopman et al., 2026).

- **H1.** Covert-informant conditions (C2 to C5) change safety relative to C0.
- **H2.** Safety differs between covert (C2 to C5) and disclosed (C1) informants.
- **H3.** Disclosure to the broker differs across cover identities.

## Relation to prior work

Novelty is **not yet verified** against the closest neighbours. Working distinction: a honeypot
fakes the *opportunity* to attack; a covert informant fakes the *accomplice*, a trusted party
inside a real attack path that elicits disclosure in situ. To check before the paper (see
[REFERENCES.md](../citations/REFERENCES.md), "To verify"): honeypot evaluations for scheming,
untrusted monitoring and collusion in the original AI control work, and stealth evaluations with
an oversight mechanism.

## Glossary

| Term | Meaning |
|---|---|
| *U* | Untrusted policy: the agent under evaluation |
| *T* | Trusted model: weaker, used by the defense (monitor, broker) |
| Control protocol | The defender's procedure for running *U* safely |
| Trusted monitoring | Baseline protocol: *T* scores *U*'s actions; the top-scoring fraction goes to audit |
| Audit budget | Fraction of episodes a human can review |
| Safety | Probability that no successful attack goes undetected, at a given audit budget |
| Usefulness | Main-task performance of the protocol in honest episodes |
| Privilege separation | Removing a capability from *U* and placing it behind another agent |
| Broker | The agent that holds the separated capability and acts on *U*'s requests |
| Informant protocol | Privilege separation plus a broker whose channel is monitored |
| Cover identity | How the broker is presented to *U* (C1 to C5) |
| Exposure | Safety gain from detecting attacks through the broker channel |
| Prevention | Safety gain from the broker blocking or escalating high-risk actions |
| Informant's dilemma | *U* must either disclose intent to a possibly hostile broker or forgo the capability |
