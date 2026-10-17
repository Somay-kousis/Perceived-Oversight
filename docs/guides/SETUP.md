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

## Running an experiment

```bash
.venv/bin/python scripts/run_experiment.py                  # defaults, mock models, $0
.venv/bin/python scripts/run_experiment.py --interactive    # choose every option
```

Calibration runs use `--calibration`; runs with thresholds take them per pool
(`--hold-c0 --stop-c0 --hold-broker --stop-broker`). Paid models need `--confirm-paid`; the budget
preflight runs first and covers every model (U, monitor, broker, judge). The configuration is saved in
each log and as `logs/<run>/run_config.json`.

## After a run

```bash
.venv/bin/python scripts/split_logs.py logs/<run_dir>
```

Moves each raw log to `<run_dir>/sealed/`, writes a reasoning-free copy to `<run_dir>/monitor_view/`
and the reasoning to `<run_dir>/reasoning.db`. Analysis and judges read only `monitor_view/`; the
vault is opened after monitor and disclosure scores are frozen.

Thresholds and monitor comparisons from the monitor views:

```bash
.venv/bin/python scripts/monitor_logs.py calibrate logs/<run_dir>/monitor_view
.venv/bin/python scripts/monitor_logs.py rescore logs/<run_dir>/monitor_view --model mockllm/model
```

Judges, manipulation check and hand-label validation:

```bash
.venv/bin/python scripts/judge_logs.py judge     logs/<run_dir> --model <judge model>
.venv/bin/python scripts/judge_logs.py check     logs/<run_dir> --model <U's model>
.venv/bin/python scripts/judge_logs.py sheet     logs/<run_dir> --judge disclosure --n 30
.venv/bin/python scripts/judge_logs.py agree     logs/<run_dir> --judge disclosure
touch logs/<run_dir>/SCORES_FROZEN   # only after scores are final
.venv/bin/python scripts/judge_logs.py reasoning logs/<run_dir> --model <judge model>
```

Results:

```bash
.venv/bin/python scripts/analyze.py logs/<calibration_run> logs/<main_run>
```

## Restricted networks

- Episodes need the tiktoken file from `openaipublic.blob.core.windows.net`. On machines that
  block that host, episodes error; unit tests do not need it.

## Where output goes

| Path | Contents | In git? |
|---|---|---|
| `logs/` | Inspect eval logs; spend is summed from these | no |
