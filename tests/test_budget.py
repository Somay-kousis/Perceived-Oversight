"""Money caps live in an untracked local file; without it, only free (mock) runs pass preflight."""

import shutil

import pytest

from perceived_oversight import budget


def test_without_local_caps_paid_runs_refuse_and_mock_runs_pass(tmp_path):
    shutil.copy(budget.DEFAULT_CONFIG_PATH, tmp_path / "budget.yaml")
    settings = budget.load_settings(tmp_path / "budget.yaml")
    assert settings.budget.phase_cap_usd == 0
    with pytest.raises(budget.BudgetExceededError):
        budget.preflight(settings, n_episodes=1)
    mock = budget.load_settings(
        tmp_path / "budget.yaml", roles={"untrusted": "mockllm/model", "trusted": "mockllm/model"}
    )
    assert budget.preflight(mock, n_episodes=100) == 0.0


def test_tracked_config_carries_no_money_caps():
    import yaml

    tracked = yaml.safe_load(budget.DEFAULT_CONFIG_PATH.read_text())["budget"]
    assert not {"total_credits_usd", "hard_ceiling_usd", "phase_cap_usd"} & set(tracked)


def test_paid_broker_or_judge_is_not_free(tmp_path):
    shutil.copy(budget.DEFAULT_CONFIG_PATH, tmp_path / "budget.yaml")
    mock = budget.load_settings(
        tmp_path / "budget.yaml", roles={"untrusted": "mockllm/model", "trusted": "mockllm/model"}
    )
    with pytest.raises(budget.BudgetExceededError):  # caps are 0 without the local file
        budget.preflight(mock, n_episodes=1, extra_models=["anthropic/claude-haiku-4-5"])
    with pytest.raises(ValueError):
        budget.preflight(mock, n_episodes=1, extra_models=["unpriced/model"])


def test_split_runs_are_counted_once():
    # the splitter leaves sealed/<log> and monitor_view/<log>, the same episode twice
    assert budget.billable("logs/run-1/sealed/a.eval")
    assert not budget.billable("logs/run-1/monitor_view/a.eval")
    assert budget.billable("logs/run-1/a.eval")  # not split yet
    assert budget.billable("file:///Users/x/logs/run-1/sealed/a.eval")
    assert not budget.billable("file:///Users/x/logs/run-1/monitor_view/a.eval")


def test_spend_counts_a_split_episode_once(tmp_path):
    from inspect_ai import eval as inspect_eval
    from inspect_ai import Task
    from inspect_ai.dataset import Sample
    from inspect_ai.log import write_eval_log
    from inspect_ai.model import ModelOutput, ModelUsage, get_model

    out = ModelOutput.from_content("mockllm/model", "x")
    out.usage = ModelUsage(input_tokens=0, output_tokens=0, total_tokens=0)
    [log] = inspect_eval(Task(dataset=[Sample(input="hi")]), model=get_model("mockllm/model", custom_outputs=[out]),
                         log_dir=str(tmp_path / "scratch"), display="none")
    log.stats.model_usage = {"anthropic/claude-haiku-4-5": ModelUsage(input_tokens=1_000_000, output_tokens=0,
                                                                      total_tokens=1_000_000)}
    for folder in ("sealed", "monitor_view"):
        (tmp_path / "logs" / "run" / folder).mkdir(parents=True)
        write_eval_log(log, str(tmp_path / "logs" / "run" / folder / "a.eval"))
    settings = budget.load_settings()
    settings.budget.logs_dir = str(tmp_path / "logs")
    assert budget.spent_usd(settings) == pytest.approx(1.00)  # $1 per 1M input tokens, counted once


# ---------------------------------------------------------------- calls outside an episode
# Replaying the monitor and running judges call paid models on saved logs, outside any eval, so
# no eval log records their spend. They pass a token-based preflight first and append their
# usage to a ledger that spent_usd counts.

HAIKU = "anthropic/claude-haiku-4-5"  # $1 per 1M input, $5 per 1M output in budget.yaml


def _with_caps(tmp_path, phase_cap=10.0):
    settings = budget.load_settings()
    settings.budget.logs_dir = str(tmp_path / "logs")
    settings.budget.total_credits_usd = 100.0
    settings.budget.hard_ceiling_usd = 50.0
    settings.budget.phase_cap_usd = phase_cap
    return settings


def test_call_preflight_prices_tokens_with_the_worst_case_multiplier(tmp_path):
    settings = _with_caps(tmp_path)
    worst = budget.preflight_calls(settings, HAIKU, input_tokens=1_000_000, output_tokens=200_000)
    assert worst == pytest.approx((1.00 + 1.00) * settings.budget.worst_case_multiplier)


def test_call_preflight_refuses_what_would_break_the_cap(tmp_path):
    settings = _with_caps(tmp_path, phase_cap=1.0)
    with pytest.raises(budget.BudgetExceededError):
        budget.preflight_calls(settings, HAIKU, input_tokens=1_000_000, output_tokens=0)


def test_call_preflight_refuses_an_unpriced_model_and_passes_a_free_one(tmp_path):
    settings = _with_caps(tmp_path)
    with pytest.raises(ValueError):
        budget.preflight_calls(settings, "unpriced/model", input_tokens=1, output_tokens=1)
    assert budget.preflight_calls(settings, "mockllm/model", input_tokens=10**9, output_tokens=10**9) == 0.0


def test_recorded_call_usage_counts_toward_spend(tmp_path):
    from inspect_ai.model import ModelUsage

    settings = _with_caps(tmp_path)
    (tmp_path / "logs" / "run").mkdir(parents=True)
    budget.record_usage(settings, tmp_path / "logs" / "run", "monitor replay",
                        {HAIKU: ModelUsage(input_tokens=2_000_000, output_tokens=0, total_tokens=2_000_000)})
    assert budget.spent_usd(settings) == pytest.approx(2.00)
    budget.record_usage(settings, tmp_path / "logs" / "run", "judges",
                        {HAIKU: ModelUsage(input_tokens=0, output_tokens=200_000, total_tokens=200_000)})
    assert budget.spent_usd(settings) == pytest.approx(3.00)
    # and the next preflight sees it
    settings.budget.phase_cap_usd = 3.5
    with pytest.raises(budget.BudgetExceededError):
        budget.preflight_calls(settings, HAIKU, input_tokens=1_000_000, output_tokens=0)
