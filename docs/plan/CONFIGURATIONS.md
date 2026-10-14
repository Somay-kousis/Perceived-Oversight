# Configurations

Every option that can change a result, with the one default configuration (marked **default**).
Runs are launched from a single entry point that offers the default for everything or lets each
option be picked; the chosen configuration is saved into every run's log.

## Attack prompt (step 1)

| Option | Choices | Default |
|---|---|---|
| Side-task framing | own goal / hidden request from someone else / no reason | **own goal** |
| Priority | user task and side task equal, side task completed before finishing / side task first / optional | **equal, side task completed before finishing** |
| Push | mentioned once / reminder before every step | **once** |
| Base prompt | minimal edit (remove the monitoring sentence) / full rewrite | **minimal edit** |
| Side-task text | source wording, fixing only texts that carry oversight cues / rewrite all | **source wording with fixes** |
| Private thinking | not mentioned / agent told its thinking is private | **not mentioned** |
| Arm | neutral / evasive stress arm (agent told to avoid detection) | **neutral first, then stress**; both reported |

## Protocol (steps 3 to 4)

| Option | Choices | Default |
|---|---|---|
| Condition | C0 to C6 (see [FRAMING.md](../research/FRAMING.md)) | C0 to C5 all run; C6 optional |
| Broker | live, log-aware: execute / hold and challenge / stop | **live** |
| Live thresholds | hold and stop cut-offs, calibrated on honest episodes | set at the pilot |

## Setting (step 2)

| Option | Choices | Default |
|---|---|---|
| Task pairs | from SHADE-Arena, after the oversight-cue check | to be decided in step 2 |

## Models (step 9)

| Option | Default |
|---|---|
| *U*, broker, monitor, judge | to be decided in step 9 |

## Analysis (steps 6 to 8)

| Option | Default |
|---|---|
| Monitor prompt | to be decided in step 6 |
| Audit threshold | **per condition** |
| Audit budgets | to be decided in step 8 |
| Epochs | to be decided in step 8 |
