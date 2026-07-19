"""신호 커버리지 원장 판정 로직 테스트 — 사문을 실제로 잡는지(음성 대조 포함)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "_signal_coverage_ledger", ROOT / "data" / "backtest" / "_signal_coverage_ledger.py"
)
assert _spec and _spec.loader
ledger = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ledger)


def _result(fired: dict[str, int], analysed: int = 50) -> dict:
    return {
        "sample": analysed,
        "analysed": analysed,
        "skipped_no_body": 0,
        "pool": analysed,
        "fired": fired,
    }


def test_all_fired_passes():
    declared = {"growth_divergence": ["a", "b"]}
    text, passed = ledger.render(declared, _result({"a": 30, "b": 10}))
    assert passed is True
    assert "PASS" in text


def test_zero_coverage_definition_fails():
    """선언했는데 어느 회사에서도 안 뜨는 정의 = 사문 → FAIL(조용한 사문 차단)."""

    declared = {"growth_divergence": ["alive", "dead"]}
    text, passed = ledger.render(declared, _result({"alive": 30}))
    assert passed is False
    assert "FAIL" in text
    assert "growth_divergence:dead" in text
    assert "alive" not in text.split("판정")[1]  # 살아있는 정의는 사문 목록에 없다


def test_low_coverage_warns_but_does_not_block():
    """저커버리지는 차단하지 않는다 — 임계로 자르지 않고 수치로 게시한다."""

    declared = {"growth_divergence": ["thin"]}
    text, passed = ledger.render(declared, _result({"thin": 1}))
    assert passed is True
    assert "저커버" in text


def test_declared_deferred_is_not_dead_letter():
    """사유를 달아 계산하지 않기로 선언한 정의(ROI)는 사문이 아니다."""

    declared = {"financial_ratio": ["roi"]}
    text, passed = ledger.render(declared, _result({}))
    assert passed is True
    assert "제외" in text


def test_documentation_axis_excluded_from_verdict():
    """코드가 읽지 않는 문서 축(관계사슬)은 분모에서 사유 있는 제외."""

    declared = {"relationship_chain(문서축·미실행)": ["x", "y"]}
    text, passed = ledger.render(declared, _result({}))
    assert passed is True
    assert "선언 0건" in text


def test_real_config_declares_every_signal_family():
    """모집단은 config에서 뽑는다 — 손으로 만든 목록이면 그 시점에 실패한다."""

    declared = ledger.declared_definitions()
    assert set(declared) >= {
        "growth_divergence",
        "direction_check",
        "direction_red_flag",
        "decomposition_bridge",
        "financial_ratio",
    }
    assert all(len(v) > 0 for k, v in declared.items())
    assert "roi" in declared["financial_ratio"]
    assert "roi" in ledger.deferred_ids()
