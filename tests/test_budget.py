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
