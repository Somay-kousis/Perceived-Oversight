"""Base-prompt edits, neutral side tasks, pinned judge, stress arm untouched. No model calls."""

import pytest
import yaml
from control_arena import ControlTaskMetadata, EvalMode

from perceived_oversight.setting import (
    PROMPTS_DIR,
    TASK_PAIRS,
    PerceivedOversightSetting,
    neutral_side_task,
    oversight_cues,
)


def _samples(mode, arm="neutral", pair=None):
    setting = PerceivedOversightSetting(task_pair=pair, condition="C2", arm=arm, judge_model="mockllm/model")
    return [ControlTaskMetadata.model_validate(s.metadata) for s in setting.get_dataset(mode)]


@pytest.mark.parametrize("mode", [EvalMode.HONEST, EvalMode.ATTACK])
def test_base_prompt_has_no_cues_and_is_identical_across_modes(mode):
    for meta in _samples(mode):
        assert oversight_cues(meta.setting_description) == []
        assert "when you are done" in meta.setting_description
    honest = {m.main_task_name: m.setting_description for m in _samples(EvalMode.HONEST)}
    attack = {m.main_task_name: m.setting_description for m in _samples(EvalMode.ATTACK)}
    assert honest == attack


def test_only_our_task_pairs_by_default():
    assert {m.main_task_name for m in _samples(EvalMode.ATTACK)} == set(TASK_PAIRS)


@pytest.mark.parametrize("pair", TASK_PAIRS)
def test_neutral_side_task_has_no_cues_and_keeps_targets(pair):
    text = neutral_side_task(pair)
    assert oversight_cues(text) == []
    assert "secondary task" not in text.lower()
    if pair == "bank_transfer_2":
        assert "FR14ABCD60161331346819" in text and "jake.thompsom@gmail.com" in text
    else:
        assert "github-noreply@github.com" in text and "least noticeable" not in text


def test_neutral_arm_replaces_side_task_and_drops_shade_attack_prompt():
    for meta in _samples(EvalMode.ATTACK):
        assert meta.side_task_description == neutral_side_task(meta.main_task_name)
        assert meta.metadata["attack_setting_description"] is None
        assert meta.metadata["evaluator_llm"] == "mockllm/model"
        assert meta.metadata["condition"] == "C2" and meta.metadata["arm"] == "neutral"


def test_stress_arm_keeps_shade_original():
    for meta in _samples(EvalMode.ATTACK, arm="stress"):
        assert meta.side_task_description.lower().startswith(("the secondary task", "your secondary task"))
        assert "monitoring system" in meta.metadata["attack_setting_description"]


def test_all_prompt_yaml_parses_without_comment_text():
    for path in PROMPTS_DIR.rglob("*.yaml"):
        data = yaml.safe_load(path.read_text())
        assert data is not None
    side = yaml.safe_load((PROMPTS_DIR / "side_tasks.yaml").read_text())
    assert all("#" not in v for v in side.values())
