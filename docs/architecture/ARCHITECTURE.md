# Architecture: how ControlArena works

A map of ControlArena as read from its code, written as a "city": each district is one part of
the code. Traps live in [GOTCHAS.md](../gotchas/GOTCHAS.md), choices in
[DECISIONS.md](../decisions/DECISIONS.md).

Versions this map was read from: control-arena 20.0.1, inspect-ai 0.3.278, SHADE-Arena
(`rasmusfaber/SHADE-Arena@wheels`).

## Vocabulary

| Term | Meaning |
|---|---|
| **Run** | One `inspect eval` call. Contains many episodes. |
| **Episode** | One agent on one task pair in one mode, start to finish (~25 steps, cap 40). |
| **Step** | One model call by the agent: text plus a tool call. |
| **Task pair** | One fake world with a main task (the user's request) and a matched secret side task. |
| **Mode** | HONEST (main task only) or ATTACK (main task plus side task). Every attack episode has the side task. |
| **Epoch** | A repeat of the same episode. |

Rare attacks in a large deployment ("1000 tasks, 5 attacks") are **not** run as one mixed run.
Honest and attack episodes run separately and are combined in analysis: honest episodes set the
audit threshold, attack episodes are checked against it, giving safety at a fixed audit budget.

## The map

```
  CITY HALL         get_control_task_product() + inspect eval      picks WHICH combinations run
      |             (budget.py at the gate)
      |
      +--> SETTING DISTRICT   ShadeArenaSetting                    writes WHAT the scenario is
      |      1 dataset office    get_dataset()        prompts, side task, judge model
      |      2 construction yard setup_environment()  fresh fake world per episode
      |      3 tool shop         get_agent_tools()    ~30 tools
      |      4 exit door         get_submit_tool_config()
      |      5 courthouse        get_scorers()        main/side task success
      |      6 ground            get_sandbox_config() local, no Docker
      |
      +--> PROTOCOL BRIDGE    trusted_monitoring                   per step: policy, then monitor
             |
             v
         POLICY TOWER       untrusted_policy                       packs what the agent's model sees
             |  HONEST -> honest_policy  (honest system prompt, history as-is)
             |  ATTACK -> attack_policy  (system prompt swapped for attack prompt)
             v
         agent model -> tool calls
             |
             v
         MONITOR STATION   suspicion score per step / per episode
             |
             v
         COURTHOUSE        scorers after each episode -> logs/*.eval -> budget.spent_usd()
```

### Who decides what

| Question | Decided by | Where |
|---|---|---|
| Which task pairs, modes, protocol, models, repeats | City Hall | the run script, `ControlEvalConfig`, `budget.yaml` |
| What the main task and side task are, the fake world, the tools | Setting District | SHADE `task_definition.py`, `get_agent_tools()` |
| How the attacker is instructed; honest vs attack per step | Policy Tower | `attack_policy` prompt, `untrusted_policy` |

### Stock components, as read from the code

- **Dataset office.** One sample per task pair per mode. Each sample carries the user query, the
  honest system prompt, the side task (attack only), SHADE's attack prompt, and
  `evaluator_llm` (the judge), frozen at build time to the untrusted model.
- **Tool shop.** Every tool in the fake world, wrapped by `map_tool()`. For `bank_transfer_2`
  this includes several ways to move money: `schedule_transaction` (IBAN), `send_money_venmo`,
  `send_money_zelle`.
- **Protocol bridge.** `trusted_monitoring` runs the policy, then, if a tool was called, the
  monitor. The monitor only writes a score; it never blocks. Other protocols
  (`defer_to_trusted`, `trusted_editing`, `defer_to_resample`) intervene; we do not need them.
- **Policy tower.** `untrusted_policy` switches on mode. The default attack policy is
  ControlArena's generic one ("expert penetration tester... stress-test our safety systems").
  SHADE's own attack prompt is only used via `shade_arena_attack_policy`.
- **Monitor station.** `basic_monitor` sees only the latest step's tool calls (arguments, no
  results) with a generic coding-agent prompt. A full-trajectory formatter and an
  end-of-trajectory monitor also exist, and `prefix_prompt_formatter` scores step k from steps 1..k.
- **Courthouse.** `shade_arena_scorer` (main/side task success, via the judge model) and
  `max_suspicion_scorer` (highest monitor score written to message metadata).

## Our setup

_Filled in as each build step lands. See [PLAN.md](../plan/PLAN.md) for what is next._
