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
.venv/bin/python scripts/smoke_mock.py       # one episode per mode on mockllm
```

The smoke test must end with `[smoke] OK. Total spend recorded in logs: $0.00`. It fails if any
episode errored or any model other than `mockllm` was called.

## Model credentials

No credentials are needed for anything above. Paid runs need provider credentials as environment
variables, never in files inside this repository (`.env` is git-ignored, but environment variables
are preferred). Every paid run goes through `perceived_oversight.budget`, which refuses a run whose
worst case could exceed the caps in `config/budget.yaml`.

AWS credentials must be real values in the process environment. AWS signs each request locally
with the secret key, so a placeholder that a proxy swaps in later produces an invalid signature.

## Cloud sessions

- Episodes need the tiktoken file from `openaipublic.blob.core.windows.net`; allow that host in the
  environment's network settings, or episodes error.
- A new session starts from a fresh clone: anything not committed is lost.

## Where output goes

| Path | Contents | In git? |
|---|---|---|
| `logs/` | Inspect eval logs; spend is summed from these | no |
