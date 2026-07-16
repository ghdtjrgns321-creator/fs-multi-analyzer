"""account_metrics_panel 컬럼형 직렬화 — 무손실 + 토큰 절감.

객체 리스트(키 이름 N회 반복)를 {columns, rows}로 바꿔 키 이름을 1회만 싣는다.
정보 손실 0(계정 수·필드 값 보존), JSON 크기는 감소해야 한다.
"""

from __future__ import annotations

import json

from src.signals.metrics_panel import panel_columnar


def _sample_panel() -> list[dict]:
    return [
        {
            "account": "CFS:매출채권",
            "disclosed_label": "매출채권",
            "sj_div": "BS",
            "fs_div": "CFS",
            "occurrence_state": "present",
            "presentation_change": None,
            "restated_prior_mismatch": None,
            "amounts": {2023: 100.0, 2024: 180.0},
            "yoy_pct": {2023: None, 2024: 80.0},
            "delta_over_assets": 0.05,
            "trend": 0.3,
            "volatility_cv": 0.2,
            "mix_pct": 12.5,
            "mix_shift_pp": 1.1,
            "z_score": 1.8,
            "percentiles": {"delta_over_assets": 0.9, "trend": 0.7},
        },
        {
            "account": "CFS:재고자산",
            "disclosed_label": "재고자산",
            "sj_div": "BS",
            "fs_div": "CFS",
            "occurrence_state": "present",
            "presentation_change": None,
            "restated_prior_mismatch": None,
            "amounts": {2023: 50.0, 2024: 55.0},
            "yoy_pct": {2023: None, 2024: 10.0},
            "delta_over_assets": 0.01,
            "trend": 0.1,
            "volatility_cv": 0.05,
            "mix_pct": 6.0,
            "mix_shift_pp": -0.2,
            "z_score": None,
            "percentiles": {"delta_over_assets": 0.3, "trend": 0.2},
        },
    ]


def _restore(columnar: dict) -> list[dict]:
    cols = columnar["columns"]
    return [dict(zip(cols, row)) for row in columnar["rows"]]


def test_columnar_is_lossless() -> None:
    panel = _sample_panel()
    columnar = panel_columnar(panel)
    restored = _restore(columnar)
    # 계정 수 보존
    assert len(restored) == len(panel)
    # 전 계정·전 필드 값 보존
    for orig, rest in zip(panel, restored):
        for field, value in orig.items():
            assert rest[field] == value, f"{orig['account']}.{field} 손실"


def test_columnar_shrinks_size() -> None:
    panel = _sample_panel()
    obj_chars = len(json.dumps(panel, ensure_ascii=False))
    col_chars = len(json.dumps(panel_columnar(panel), ensure_ascii=False))
    assert col_chars < obj_chars, "컬럼형이 더 크면 절감 실패"


def test_columnar_empty() -> None:
    out = panel_columnar([])
    assert out["columns"] == [] or out["rows"] == []
    assert out["rows"] == []
