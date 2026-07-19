"""파생층 커버리지 원장 — 미매핑 계정이 사슬·비율에 진입 못 하는 몫을 센다.

계정층 원장은 미매핑도 '분석됨'으로 세므로 이 누락이 안 보인다(조용한 드롭).
"""

from __future__ import annotations

from src.report.coverage import build_derived_ledger, derived_layer_accounts

COVERED = {"매출채권", "매출", "당기순이익"}


def _row(label, canonical, amount, *, status="", fs="CFS", sj="BS", year=2024):
    return {
        "year": year,
        "fs_div": fs,
        "sj_div": sj,
        "series_key": f"{fs}:{canonical or label}",
        "canonical": canonical,
        "label": label,
        "amount": amount,
        "mapping_status": status,
    }


def test_covered_account_enters():
    ledger = build_derived_ledger([_row("매출채권", "매출채권", 100.0)], 2024, COVERED)
    assert ledger["entered_n"] == 1
    assert ledger["blocked"] == []


def test_mapped_but_not_in_playbook_is_legit_exclusion():
    ledger = build_derived_ledger([_row("선급금", "선급금", 100.0)], 2024, COVERED)
    assert ledger["entered_n"] == 0
    assert len(ledger["excluded"]) == 1
    assert ledger["blocked"] == []  # 표준 이름이 있으니 진입 불가가 아니다


def test_unmapped_is_blocked_with_amount():
    rows = [_row("신종자본증권변동", "기타 중요 계정", -250.0, status="unmapped_extension_account")]
    ledger = build_derived_ledger(rows, 2024, COVERED)
    assert len(ledger["blocked"]) == 1
    assert ledger["blocked_amount"] == 250.0  # 절대값
    assert "미매핑" in ledger["blocked"][0]["reason"]


def test_unmapped_accounts_are_not_collapsed_into_one_bucket():
    """핵심 회귀 — series_key로 세면 미매핑 N종이 'fs:기타 중요 계정' 1건으로 뭉친다."""

    rows = [
        _row("신종자본증권변동", "기타 중요 계정", 100.0, status="unmapped_extension_account"),
        _row("자기주식 매입", "기타 중요 계정", 200.0, status="unmapped_extension_account"),
        _row("주식선택권 행사", "기타 중요 계정", 300.0, status="unmapped_extension_account"),
    ]
    ledger = build_derived_ledger(rows, 2024, COVERED)
    assert len(ledger["blocked"]) == 3, "미매핑은 원문 라벨로 구분돼야 한다"
    assert ledger["blocked_amount"] == 600.0


def test_cross_statement_demotion_is_not_counted_as_missing():
    """현금흐름표의 '당기순이익'은 손익계산서에서 이미 진입 — 누락으로 세면 과대계상."""

    rows = [
        _row("당기순이익", "기타 중요 계정", 900.0, status="unmapped_extension_account", sj="CF")
    ]
    ledger = build_derived_ledger(rows, 2024, COVERED)
    assert ledger["blocked"] == []
    assert "제 표에서 진입" in ledger["excluded"][0]["reason"]


def test_identity_holds():
    rows = [
        _row("매출채권", "매출채권", 100.0),
        _row("선급금", "선급금", 50.0),
        _row("신종자본증권변동", "기타 중요 계정", 30.0, status="unmapped_extension_account"),
    ]
    ledger = build_derived_ledger(rows, 2024, COVERED)
    assert ledger["reconciled"] is True
    assert ledger["population_n"] == ledger["entered_n"] + len(ledger["excluded"]) + len(
        ledger["blocked"]
    )


def test_other_years_are_out_of_population():
    rows = [_row("매출채권", "매출채권", 100.0, year=2023)]
    assert build_derived_ledger(rows, 2024, COVERED)["population_n"] == 0


def test_real_playbooks_yield_account_names():
    from src.signals.config import load_relationship_chains
    from src.signals.ratios import load_ratio_config

    names = derived_layer_accounts(load_relationship_chains(), load_ratio_config())
    assert "매출채권" in names and "당기순이익" in names
    assert len(names) > 20  # 사슬 9종 + 비율 15종이 실제로 계정을 싣고 있다
