"""SCE 자기주식 신규발생(사각#2) — change_canonical 단위 occurrence(D18 정체성).

leaf(component)는 연도간 불안정이라 안 쓰고, 표준 변동종류(change_canonical)로 신규/소멸을 센다.
자기주식취득이 올해만 있으면 appeared, 매년 있으면 present, 사라지면 disappeared.
"""

from __future__ import annotations

from src.signals.metrics_panel import sce_occurrence_states


def _row(year: int, change: str, component: str, amount: float, fs: str = "CFS") -> dict:
    return {
        "year": year,
        "fs_div": fs,
        "change_canonical": change,
        "component_std": component,
        "amount": amount,
    }


def _window() -> list[dict]:
    rows = []
    # 배당: 매년 → present
    for y in (2022, 2023, 2024):
        rows.append(_row(y, "배당", "이익잉여금", -100.0))
    # 자기주식취득: 2024만 → appeared (구성요소 2개로 쪼개져도 합쳐 판정)
    rows.append(_row(2024, "자기주식취득", "지배기업소유주지분", -1811.0))
    rows.append(_row(2024, "자기주식취득", "비지배지분", -0.0))
    # 유상증자: 2022에만 있고 이후 사라짐 → disappeared
    rows.append(_row(2022, "유상증자", "자본금", 500.0))
    return rows


def test_new_treasury_stock_is_appeared() -> None:
    states = sce_occurrence_states(_window(), 2024)
    assert states[("CFS", "자기주식취득")] == "appeared"


def test_recurring_dividend_is_present() -> None:
    states = sce_occurrence_states(_window(), 2024)
    assert states[("CFS", "배당")] == "present"


def test_vanished_capital_raise_is_disappeared() -> None:
    states = sce_occurrence_states(_window(), 2024)
    assert states[("CFS", "유상증자")] == "disappeared"
