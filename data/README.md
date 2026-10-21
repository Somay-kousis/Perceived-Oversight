# Data

`explorer/` is the run explorer's static snapshot, the same files the hosted explorer serves:
`runs.json` lists every run, `runs/<id>.json` holds a run and `runs/<id>/episodes/<n>.json` one
episode (monitor-view transcript, every scored request with both monitor scores, outcomes, task
results and helper reasoning). Agent reasoning is sealed: episodes show only how many blocks exist.
Spend is left out.

Written by `scripts/export_explorer.py logs data/explorer` from split logs. Raw logs and the
reasoning vault stay out of the repository (blind analysis).

Environment contents in transcripts come from SHADE-Arena's synthetic data, including credential-like
strings that are not real. Two sample Stripe keys are replaced with `[SHADE sample key]` here;
otherwise the files match the hosted explorer.
