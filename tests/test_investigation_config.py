from pathlib import Path

from src.report.investigation_config import INVESTIGATION_PATH, load_investigation_config


def test_load_real_config_has_gate_and_weights():
    cfg = load_investigation_config()
    gate = cfg["investigation"]["gate"]
    assert gate["residual_pct_max"] > 0
    assert gate["top_leaf_pct_min"] > 0
    assert cfg["investigation"]["loop"]["max_requests"] >= 1
    weights = cfg["priority"]["weights"]
    assert set(weights) == {"materiality", "votes", "anomaly", "confidence"}


def test_missing_file_returns_empty(tmp_path: Path):
    assert load_investigation_config(tmp_path / "none.yaml") == {}
