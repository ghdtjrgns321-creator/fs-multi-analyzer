"""G7 소계·대사 검산 — 합성 DB로 판정 분기를 고정."""

from __future__ import annotations

import duckdb
import pytest

from src.normalize.gate_identities import identity_report

COLUMNS = "corp_code, year, fs_div, sj_div, canonical, account_id, label, amount"
B = 1_000_000_000.0  # 검산 허용오차가 100만원이라 합성값도 실제 규모(십억 단위)로 둔다


def _make_db(tmp_path, rows, sce_rows=()):
    db = tmp_path / "analysis.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute(
            "CREATE TABLE normalized_financials (corp_code VARCHAR, year VARCHAR, fs_div VARCHAR, "
            "sj_div VARCHAR, canonical VARCHAR, account_id VARCHAR, label VARCHAR, amount DOUBLE)"
        )
        for sj, canonical, amount in rows:
            con.execute(
                f"INSERT INTO normalized_financials ({COLUMNS}) VALUES (?,?,?,?,?,?,?,?)",
                ["00000001", "2024", "CFS", sj, canonical, "id", canonical, amount],
            )
        con.execute(
            "CREATE TABLE sce_equity_components (corp_code VARCHAR, year VARCHAR, fs_div VARCHAR, "
            "change_role VARCHAR, component_std VARCHAR, amount DOUBLE, "
            "change_canonical VARCHAR, component_role VARCHAR)"
        )
        for row in sce_rows:
            role, component, amount = row[0], row[1], row[2]
            change_canonical = row[3] if len(row) > 3 else None
            component_role = row[4] if len(row) > 4 else None
            con.execute(
                "INSERT INTO sce_equity_components VALUES (?,?,?,?,?,?,?,?)",
                [
                    "00000001",
                    "2024",
                    "CFS",
                    role,
                    component,
                    amount,
                    change_canonical,
                    component_role,
                ],
            )
    return db


BALANCED = [
    ("BS", "자산총계", 1000 * B),
    ("BS", "유동자산", 400 * B),
    ("BS", "비유동자산", 600 * B),
    ("BS", "부채총계", 300 * B),
    ("BS", "유동부채", 100 * B),
    ("BS", "비유동부채", 200 * B),
    ("BS", "자본총계", 700 * B),
    ("BS", "자본과부채총계", 1000 * B),
]


def test_balanced_subtotals_pass(tmp_path):
    report = identity_report(_make_db(tmp_path, BALANCED))
    assert report["passed"] is True
    assert report["executed"] >= 3  # 자산·부채·대차평균이 실제로 돌았다
    assert report["violations"] == []


def test_subtotal_mismatch_blocks(tmp_path):
    rows = [(sj, c, 999 * B if c == "비유동자산" else a) for sj, c, a in BALANCED]
    report = identity_report(_make_db(tmp_path, rows))
    assert report["passed"] is False
    assert any(v["id"] == "BS_자산총계" and v["blocking"] for v in report["violations"])


def test_missing_component_skips_not_fails(tmp_path):
    """구성요소가 없으면 FAIL이 아니라 SKIP — 업종마다 표 구조가 다르다."""

    rows = [r for r in BALANCED if r[1] not in ("유동자산", "비유동자산")]
    report = identity_report(_make_db(tmp_path, rows))
    assert all(v["id"] != "BS_자산총계" for v in report["violations"])


def test_zero_executed_is_not_pass(tmp_path):
    """검산 0건은 '통과'가 아니라 '검산 못함' — 빈 검사 둔갑 금지."""

    report = identity_report(_make_db(tmp_path, [("BS", "재고자산", 10 * B)]))
    assert report["executed"] == 0
    assert report["passed"] is False
    assert "검산 0건" in report["reason"]


def test_cross_statement_cash_tie_out(tmp_path):
    """재무상태표 현금 ≠ 현금흐름표 기말현금이면 차단 — 한 표만 오매핑돼도 잡힌다."""

    rows = [*BALANCED, ("BS", "현금및현금성자산", 50 * B), ("CF", "기말현금및현금성자산", 70 * B)]
    report = identity_report(_make_db(tmp_path, rows))
    assert any(v["id"] == "TIE_현금" and v["blocking"] for v in report["violations"])


def test_sce_closing_tie_out(tmp_path):
    """재무상태표 자본총계 = 자본변동표 기말 자본총계."""

    db = _make_db(tmp_path, BALANCED, sce_rows=[("total", "-", 555 * B)])
    report = identity_report(db)
    assert any(v["id"] == "TIE_자본총계" for v in report["violations"])


def test_operating_profit_is_informational(tmp_path):
    """영업이익 식은 회사 재량이 커 기록만 — 차단하지 않는다."""

    rows = [
        *BALANCED,
        ("IS", "영업이익", 10 * B),
        ("IS", "매출총이익", 100 * B),
        ("IS", "판매비와관리비", 30 * B),
    ]
    report = identity_report(_make_db(tmp_path, rows))
    violation = next(v for v in report["violations"] if v["id"] == "IS_영업이익")
    assert violation["blocking"] is False
    assert report["passed"] is True


@pytest.mark.parametrize("missing", ["normalized_financials"])
def test_absent_db_is_not_pass(tmp_path, missing):
    report = identity_report(tmp_path / "nope.duckdb")
    assert report["passed"] is False


def test_comprehensive_income_attribution(tmp_path):
    """총포괄손익 = 지배귀속 + 비지배 — 순이익 귀속 분해와 대칭인데 빠져 있던 축."""

    rows = [
        *BALANCED,
        ("CIS", "총포괄손익", -28 * B),
        ("CIS", "지배기업귀속총포괄손익", -26 * B),
        ("CIS", "비지배지분총포괄손익", -5 * B),  # 합 -31 ≠ -28
    ]
    report = identity_report(_make_db(tmp_path, rows))
    assert any(v["id"] == "CIS_총포괄귀속" and v["blocking"] for v in report["violations"])


def test_profit_ties_income_statement_to_equity_statement(tmp_path):
    """손익 당기순이익 = 자본변동표 당기순이익 변동 — 두 표를 잇는 고리."""

    db = _make_db(
        tmp_path,
        [*BALANCED, ("IS", "당기순이익", 300 * B)],
        sce_rows=[("leaf", "-", 250 * B, "당기순이익", "marker")],
    )
    report = identity_report(db)
    violation = next(v for v in report["violations"] if v["id"] == "TIE_순이익_자본")
    assert violation["blocking"] is True
    assert violation["resid"] == 50 * B
