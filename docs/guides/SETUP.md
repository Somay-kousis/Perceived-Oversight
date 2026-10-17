# Setup

## Install

Python 3.11 or newer.

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

This installs ControlArena and Inspect from PyPI, and SHADE-Arena from
`rasmusfaber/SHADE-Arena@wheels` (ControlArena's SHADE setting imports it, but it is not on PyPI).

## Check that everything works ($0)

```bash
.venv/bin/pip install pytest
.venv/bin/python -m pytest -q tests          # unit tests, no model calls
.venv/bin/python scripts/smoke_mock.py       # C0 to C6, one episode per mode, all on mockllm
```

The smoke test must end with `[smoke] OK. Total spend recorded in logs: $0.00`. It fails if any
episode errored or any model other than `mockllm` was called.

## Model credentials

No credentials are needed for anything above. Paid runs need provider credentials as environment
variables, never in files inside this repository (`.env` is git-ignored, but environment variables
are preferred). Every paid run goes through `perceived_oversight.budget`, which refuses a run whose
worst case could exceed the per-episode limits in `config/budget.yaml` or the money caps in
`config/budget.local.yaml`.

Money caps (total, hard ceiling, phase cap) are per-installation: copy
`config/budget.local.example.yaml` to `config/budget.local.yaml` (not tracked) and fill it in.
Without it every paid run refuses; runs on mock models need no caps.

AWS credentials must be real values in the process environment (requests are signed locally).

## Restricted networks

- Episodes need the tiktoken file from `openaipublic.blob.core.windows.net`. On machines that
  block that host, episodes error; unit tests do not need it.

## Where output goes

| Path | Contents | In git? |
|---|---|---|
| `logs/` | Inspect eval logs; spend is summed from these | no |
