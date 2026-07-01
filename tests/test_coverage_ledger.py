"""근본구조 C·D — 커버리지 원장 대조 + 차원 자가테스트.

분석 모집단(본문 셀) = 분석셀 + 제외사유셀 + 미설명셀. 이유 없이 빠진 셀(unaccounted)이
1건이라도 있으면 = 조용한 드롭. 신규·소멸·OFS전용을 심어 각각 명단에 들고 미설명 0인지 단언.
SCE는 제외사유로 분류돼야 한다(미설명 아님).
"""

from __future__ import annotations

import pandas as pd

from src.report.company_report import _account_level_series
from src.report.coverage import (
    build_coverage_ledger,
    build_note_ledger,
    build_sce_ledger,
    surfaced_note_facts,
)
from src.signals.metrics_panel import account_metrics_panel


def _row(fs: str, sj: str, canon: str, year: int, amt: float) -> dict:
    return {
        "corp_code": "x",
        "year": year,
        "fs_div": fs,
        "sj_div": sj,
        "canonical": canon,
        "account_id": canon,
        "label": canon,
        "amount": amt,
        "mapping_status": "exact_taxonomy_match",
    }


def _frame() -> pd.DataFrame:
    rows = [
        # 정상: 2023·2024 둘 다 (present)
        _row("CFS", "BS", "정상계정", 2023, 1_000.0),
        _row("CFS", "BS", "정상계정", 2024, 1_200.0),
        # 소멸: 2023만 (disappeared) — fix A 전이면 명단서 누락되던 사각
        _row("CFS", "BS", "소멸계정", 2023, 5_000.0),
        # 신규: 2024만 (appeared)
        _row("CFS", "BS", "신규계정", 2024, 3_000.0),
        # OFS 전용 (별도에만)
        _row("OFS", "BS", "별도전용계정", 2024, 2_000.0),
        # SCE 셀 — 본문 명단서 제외돼야(제외사유 SCE 2D)
        _row("CFS", "SCE", "자본총계", 2024, 9_000.0),
        # 자산총계
        _row("CFS", "BS", "자산총계", 2023, 100_000.0),
        _row("CFS", "BS", "자산총계", 2024, 100_000.0),
        _row("OFS", "BS", "자산총계", 2024, 50_000.0),
    ]
    return pd.DataFrame(rows)


def test_ledger_identity_holds() -> None:
    frame = _frame()
    series = _account_level_series(frame, [2023, 2024], 2024)
    ledger = build_coverage_ledger(frame, series, [2023, 2024])
    # 항등식: 모집단 == 분석 + 제외 + 미설명
    assert ledger["reconciled"] is True
    assert ledger["population_n"] == (
        ledger["analyzed_n"] + len(ledger["excluded"]) + len(ledger["unaccounted"])
    )


def test_no_unaccounted_after_union_population() -> None:
    # fix A(명단=합집합) 적용 후 본문 셀에 이유 없이 빠진 게 없어야 한다.
    frame = _frame()
    series = _account_level_series(frame, [2023, 2024], 2024)
    ledger = build_coverage_ledger(frame, series, [2023, 2024])
    assert ledger["unaccounted"] == []


def test_sce_classified_as_excluded_not_unaccounted() -> None:
    frame = _frame()
    series = _account_level_series(frame, [2023, 2024], 2024)
    ledger = build_coverage_ledger(frame, series, [2023, 2024])
    reasons = [e["reason"] for e in ledger["excluded"]]
    assert any("SCE" in r for r in reasons)
    # SCE 자본총계 셀이 unaccounted로 새지 않음
    assert all("자본총계" not in str(u["cell"]) for u in ledger["unaccounted"])


def _note_facts() -> list[dict]:
    return [
        {
            "label_ko": "매출 등, 특수관계자거래",
            "value": "195674381000000",
            "bucket": "detail",
            "category": "특수관계자거래",
        },
        {
            "label_ko": "소송 진행 중",
            "value": "당사는 손해배상 청구 소송에 피소되었다",
            "bucket": "detail",
            "category": "약정_우발",
        },
        {
            "label_ko": "현금및현금성자산",
            "value": "537056000000",
            "bucket": "흡수",
            "category": "금융상품",
        },
        {"label_ko": "주석 목차", "value": "", "bucket": "메타", "category": "메타"},
    ]


def test_note_ledger_surfaces_all_loaded() -> None:
    # 뒤집기: 적재본은 load 단계서 정당제외(완전중복·메타) 상위적용 → 전량 surface.
    led = build_note_ledger(_note_facts())
    assert led["reconciled"] is True
    assert led["surfaced_n"] == led["population_n"]  # 전량(흡수 차원 breakdown 포함)
    assert led["excluded"] == []
    assert led["unaccounted"] == []


def test_surfaced_note_facts_returns_all_including_dimensioned_absorbed() -> None:
    # 차원흡수(부문·지역 breakdown=net-new)도 포함 — 분석층에서 추가로 안 자른다.
    surfaced = surfaced_note_facts(_note_facts())
    assert len(surfaced) == len(_note_facts())  # 전량
    assert any(f["bucket"] == "흡수" for f in surfaced)  # 차원흡수 포함


def test_sce_ledger_surfaces_all() -> None:
    # SCE 2D 셀은 전량 surface(정당제외 0 — 변동×구성요소는 전부 net-new 재무정보).
    cells = [
        {"change": "당기순이익", "component": "이익잉여금", "amount": 344_514.0},
        {"change": "배당", "component": "이익잉여금", "amount": -98_000.0},
        {"change": "자기주식취득", "component": "기타자본", "amount": -18_118.0},
    ]
    led = build_sce_ledger(cells)
    assert led["reconciled"] is True
    assert led["surfaced_n"] == 3 == led["population_n"]
    assert led["excluded"] == [] and led["unaccounted"] == []


def test_dimension_selftest_appeared_disappeared_ofs_all_in_panel() -> None:
    # D: 신규·소멸·OFS전용 셀이 분석 명단(패널)에 모두 뜨고 occurrence_state가 정확.
    frame = _frame()
    series = _account_level_series(frame, [2023, 2024], 2024)
    asset = {"CFS": 100_000.0, "OFS": 50_000.0}
    panel = {p["account"]: p for p in account_metrics_panel(series, asset, 2024)}
    assert panel["CFS:소멸계정"]["occurrence_state"] == "disappeared"
    assert panel["CFS:신규계정"]["occurrence_state"] == "appeared"
    assert panel["OFS:별도전용계정"]["occurrence_state"] == "appeared"
    assert panel["CFS:정상계정"]["occurrence_state"] == "present"
