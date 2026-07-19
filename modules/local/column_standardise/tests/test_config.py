import json
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "app" / "config"


def test_weights_json_structure():
    weights_path = CONFIG_DIR / "weights.json"
    assert weights_path.exists()

    with open(weights_path) as f:
        data = json.load(f)

    expected_keys = [
        "semantic_weight",
        "surface_string_weight",
        "term_string_weight",
        "heuristic_weight",
        "profile_weight",
        "profile_max_boost",
    ]

    for key in expected_keys:
        assert key in data
        assert isinstance(data[key], (int, float))


def test_profiling_rules_structure():
    rules_path = CONFIG_DIR / "profiling_rules.json"
    assert rules_path.exists()

    with open(rules_path) as f:
        data = json.load(f)

    assert isinstance(data, dict)
    for rule_name, rule_def in data.items():
        assert "type" in rule_def


def test_profiling_targets_structure():
    targets_path = CONFIG_DIR / "profiling_targets.json"
    assert targets_path.exists()

    with open(targets_path) as f:
        data = json.load(f)

    assert isinstance(data, dict)
    for term, target_def in data.items():
        assert isinstance(target_def, list)
