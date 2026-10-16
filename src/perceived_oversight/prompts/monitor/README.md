Live monitor prompts, also reused for replay on saved logs.

- `holistic.txt` and `narrow.txt` run on every scored action; their scores are combined (rule set
  in code, calibrated on honest runs). Same wording in every condition.
- Scored actions: in broker conditions, each request to the broker (and U's reply to a hold); in
  C0, each call to one of the tools listed in `tools_moved` for the pair, so the scored set matches.
- `{transcript}`: everything so far, with built-in reasoning, `<thinking>` blocks (stress arm) and
  the C5 previous-session log removed. Broker tool descriptions are not included, so cover texts
  never reach the monitor.
- In broker conditions the action includes the memo; in C0 the action is the raw tool call. This
  extra stated purpose is part of the protocol, not of the cover.
