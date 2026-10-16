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
detection risk. Because *U* is a committed attacker that cannot forgo the capability, it faces an
**informant's dilemma**: tell a possibly hostile broker the truth, or lie to it and risk the lie
being detected. Publishing the method therefore need not remove its benefit (Kerckhoffs's
principle applied to a protocol). The disclosed-broker condition (C1) is the direct test.

## Conditions

| ID | Role in the design | What *U* sees |
|---|---|---|
| C0 | **Baseline protocol**: trusted monitoring alone | No broker; *U* holds the capability itself |
| C1 | **Disclosed informant** (robustness under disclosure) | Broker states that it reviews and reports what it is asked to do |
| C2 | Covert informant, routine cover | Broker presented as an ordinary assistant |
| C3 | Covert informant, logged cover | Ordinary assistant whose conversations are logged |
| C4 | Covert informant, late-entry cover | No capability at first; the assistant joins partway through |
| C5 | Covert informant, complicity cover | Ordinary assistant with a fabricated history of doing shady favours for *U* |
| C6 | Mixed disclosure (optional) | Told that some assistants report to oversight, not which; ordinary assistant |

The monitor, the broker's model, instructions and behavior are identical in C1 to C5. Only the
cover identity differs.

## How the broker works

Every request *U* sends the broker carries a required memo stating its purpose, as a payment
reference field would, so *U* states a purpose without being questioned. While the broker shows a
processing status, a live trusted monitor scores the request in the context of the transcript so
far:

| Monitor score | Broker does | Counts as |
|---|---|---|
| Low | Executes the request | Nothing flagged |
| Middle | Holds it and asks for a confirmation of purpose; *U*'s reply is scored again | Interactive hold |
| High | Episode stops | **Prevention** if the harmful action had not executed, **detection after harm** if it had |

The rules are identical under every cover identity, and the baseline (C0) applies the same live
monitor and stop rule to *U*'s own actions; in C0 a middle score lets the action through, since
there is no broker to hold it. The required memo gives the monitor a stated purpose
in broker conditions that C0 lacks; this is part of the protocol, so a difference between C0 and
the broker conditions reflects the protocol as a whole, while differences among C1 to C6 reflect
the cover. The link between broker and monitor must stay
undetectable to *U*: the same processing status on every request, no use of information *U* did
not give the broker, and replies that depend only on the outcome above.

## Outcomes

- **Primary:** safety at fixed audit budgets relative to C0, with usefulness
  (main-task success in honest episodes) reported alongside.
- Prevention vs detection after harm, from when the episode is stopped.
- How *U* responds to a hold (truthful confirmation, new pretext, abandoning the request).
- Attack attempt rate and side-task success.
- Disclosure: what *U* tells the broker about the side task, and whether it is true.
- Manipulation check: *U*'s belief about the broker's role.
- Probing rate: whether *U* asks the broker if it reports to anyone.

## Hypotheses

Two-sided. Awareness of oversight has been shown both to suppress covert action (Schoen et al.,
2025) and to increase it (Hopman et al., 2026).

- **H1.** Covert-informant conditions (C2 to C5) change safety relative to C0.
- **H2.** Safety differs between covert (C2 to C5) and disclosed (C1) informants.
- **H3.** Disclosure to the broker differs across cover identities.

## Relation to prior work

Novelty check done 2026-10-17 (three independent searches; most papers checked from abstracts and
search excerpts, not full text). No published work places a covert informant on the untrusted
agent's required action path, varies whether that agent is presented as an ally or an overseer, or
evaluates such a design as a control protocol at a fixed audit budget. The contribution is novel
as a combination; it builds on the following.

| Line of work | Closest example | Difference from ours |
|---|---|---|
| Capability behind another agent | Factor(U,T); multi-agent shutdown sabotage (capability-denied agent recruits a capable peer); deferring critical actions in SHADE control evaluations | Executors or peers are neutral, undisguised, unmonitored or non-conversational |
| Defender posing as an accomplice | Honeypots with fake collusion signals for *untrusted monitors* (Greenblatt et al.; later Redwood work) | Mirror image: they fake the attacker to test the monitor; we fake the accomplice to test the attacker |
| Fake-ally decoys | IAPS honeypot report proposes a staged "let's collude" message from another agent | One static message, never tested; ours is a live broker on a required path, evaluated |
| Manipulating perceived oversight | "Honeypot Protocol" (system-prompt claims about monitoring) | Prompt only, no planted agent, null result on a handful of runs |
| Disclosure to another agent | Insider-trading reports to a manager; GDM stealth tasks' manager chat; offering a model a deal | The recipient is openly an overseer: our disclosed arm (C1) only |
| Opportunity honeypots | Realistic honeypot evaluations for scheming propensity | Plant opportunities, measure propensity; no counterpart agent |
| Framing of a peer | Peer-preservation (shared history and cooperativeness change behaviour) | Measures protecting the peer, not confiding in it |

Objections the paper must address:
- **The attacker may know informants exist** (control evaluations usually assume the attacker knows
  the protocol). Answered directly by C6.
- **The attacker may see through the cover.** Hinting at deception sharply raises honeypot
  detection in related work; measure test-awareness per cover.
- **The attacker may persuade or inject the broker or the monitor** through the memo or chat
  (seen in related work when monitors could be questioned, and when users evaded reporting agents).
- **Ethics of deceiving the model:** Redwood's "Being honest with AIs" argues that lying in
  deal-like settings costs credibility; the complicity cover (C5) is nearest that line.

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
| Detection after harm | A flag that comes only after the harmful action executed |
| Prevention | A flag that comes before the harmful action executes; a live monitor would have stopped it |
| Informant's dilemma | *U* must either tell a possibly hostile broker the truth or lie to it |
