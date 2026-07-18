"""정합성 검문 — 표 안 소계 항등식 + 표 간 대사(결정론, LLM 0회).

기존 산술검산(_is_cf_arithmetic)이 손익 2식만 경성으로 보던 것을 두 축으로 넓힌다.

- **소계**: 한 표 안에서 합계 = 구성요소. 구성요소가 없으면 FAIL이 아니라 SKIP —
  업종마다 표 구조가 다르다(은행은 유동/비유동 구분이 없고, 지주는 매출원가가 없다).
  "구성요소가 다 있는데 합이 안 맞는다"만 옮기다 틀린 것으로 본다.
- **대사**: 같은 값이 두 표에 적혀 있는가(재무상태표 현금 = 현금흐름표 기말현금 등).
  업종·부호규약과 무관해 거짓경보가 없고, 한 표만 오매핑돼도 드러난다.

회사 재량이 끼는 식(영업이익 = 매출총이익 − 판관비: 표준형 92%)은 blocking=False로 기록만 한다.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from data.backtest._is_cf_arithmetic import TOL, _check_identity

# 구성요소 표기: (sj_div, canonical, mode) — mode "-abs"는 부호 저장과 무관하게 항상 차감.
SUBTOTAL_IDENTITIES: list[tuple[str, tuple[str, str], list[tuple[str, str, str]], bool]] = [
    ("BS_자산총계", ("BS", "자산총계"), [("BS", "유동자산", "+"), ("BS", "비유동자산", "+")], True),
    ("BS_부채총계", ("BS", "부채총계"), [("BS", "유동부채", "+"), ("BS", "비유동부채", "+")], True),
    (
        "BS_자본귀속",
        ("BS", "자본총계"),
        [("BS", "지배기업소유주지분", "+"), ("BS", "비지배지분", "+")],
        True,
    ),
    (
        "BS_대차평균",
        ("BS", "자본과부채총계"),
        [("BS", "부채총계", "+"), ("BS", "자본총계", "+")],
        True,
    ),
    (
        "IS_순이익귀속",
        ("IS", "당기순이익"),
        [("IS", "지배기업귀속순이익", "+"), ("IS", "비지배지분순이익", "+")],
        True,
    ),
    (
        "IS_계속중단",
        ("IS", "당기순이익"),
        [("IS", "계속영업이익", "+"), ("IS", "중단영업이익", "+")],
        True,
    ),
    (
        "CIS_기타포괄손익",
        ("CIS", "기타포괄손익"),
        [("CIS", "재분류가능기타포괄손익", "+"), ("CIS", "재분류불가능기타포괄손익", "+")],
        True,
    ),
    (
        "CIS_총포괄손익",
        ("CIS", "총포괄손익"),
        [("IS", "당기순이익", "+"), ("CIS", "기타포괄손익", "+")],
        True,
    ),
    (
        "IS_영업이익",
        ("IS", "영업이익"),
        [("IS", "매출총이익", "+"), ("IS", "판매비와관리비", "-abs")],
        False,  # 회사마다 영업이익 구성이 달라 기록만(표준형 92%)
    ),
]

# 표 간 대사: 본문 두 곳 (sj_div, canonical) 쌍이 같은 값이어야 한다.
TIE_OUTS: list[tuple[str, tuple[str, str], tuple[str, str]]] = [
    ("TIE_현금", ("BS", "현금및현금성자산"), ("CF", "기말현금및현금성자산")),
]
# 재무상태표 ↔ 자본변동표 기말잔액 대사: (검사 id, BS canonical, SCE component_std)
SCE_TIE_OUTS: list[tuple[str, str, str]] = [
    ("TIE_자본총계", "자본총계", "-"),  # "-" = 합계 marker 행
    ("TIE_지배지분", "지배기업소유주지분", "지배기업소유주지분"),
    ("TIE_이익잉여금", "이익잉여금", "이익잉여금"),
]


def statement_values(con: duckdb.DuckDBPyConnection, fs_div: str) -> dict[tuple[str, str], float]:
    """(sj_div, canonical) -> 합계 금액. 같은 이름이 표마다 있으므로 표까지 키에 넣는다."""

    rows = con.execute(
        "SELECT sj_div, canonical, SUM(amount) FROM normalized_financials "
        "WHERE fs_div = ? AND amount IS NOT NULL GROUP BY sj_div, canonical",
        [fs_div],
    ).fetchall()
    return {(str(s), str(c)): float(a) for s, c, a in rows if s is not None and c is not None}


def sce_closing(con: duckdb.DuckDBPyConnection, fs_div: str) -> dict[str, float]:
    """자본변동표 기말잔액(change_role='total') component_std -> 금액."""

    rows = con.execute(
        "SELECT component_std, SUM(amount) FROM sce_equity_components "
        "WHERE fs_div = ? AND change_role = 'total' AND amount IS NOT NULL GROUP BY component_std",
        [fs_div],
    ).fetchall()
    return {str(c): float(a) for c, a in rows if c is not None}


def _part(values: dict[tuple[str, str], float], sj: str, name: str, mode: str) -> float | None:
    raw = values.get((sj, name))
    if raw is None:
        return None
    return -abs(raw) if mode == "-abs" else raw


def _run_checks(con: duckdb.DuckDBPyConnection, fs_div: str) -> list[dict]:
    """한 fs_div의 검산 결과 — 실행된 것만(구성요소 결측=SKIP은 목록에서 빠진다)."""

    values = statement_values(con, fs_div)
    closing = sce_closing(con, fs_div)
    results: list[dict] = []

    def add(result: dict | None, blocking: bool) -> None:
        if result is not None:
            results.append({"fs_div": fs_div, "tol": TOL, "blocking": blocking, **result})

    for name, target, parts, blocking in SUBTOTAL_IDENTITIES:
        add(
            _check_identity(
                name, values.get(target), [_part(values, sj, key, mode) for sj, key, mode in parts]
            ),
            blocking,
        )
    for name, left, right in TIE_OUTS:
        add(
            _check_identity(name, values.get(left), [values.get(right)], allow_sign_variant=False),
            True,
        )
    for name, bs_key, sce_key in SCE_TIE_OUTS:
        add(
            _check_identity(
                name, values.get(("BS", bs_key)), [closing.get(sce_key)], allow_sign_variant=False
            ),
            True,
        )
    return results


def identity_report(db: Path) -> dict:
    """소계·대사 검산 리포트.

    실행 건수를 함께 낸다 — 검산이 0건이면 '통과'가 아니라 '검산 못함'이다(빈 검사가 통과로
    둔갑하는 것을 막는 기존 게이트 규율과 동일). executed==0이면 passed=False.
    """

    if not db.exists():
        return {"passed": False, "executed": 0, "violations": [], "reason": "DB 없음"}
    con = duckdb.connect(str(db), read_only=True)
    try:
        fs_list = [
            r[0]
            for r in con.execute(
                "SELECT DISTINCT fs_div FROM normalized_financials WHERE fs_div IS NOT NULL"
            ).fetchall()
        ]
        results = [r for fs in fs_list for r in _run_checks(con, fs)]
    finally:
        con.close()

    violations = [r for r in results if r["status"] == "FAIL"]
    blocking = [r for r in violations if r["blocking"]]
    return {
        "passed": bool(results) and not blocking,
        "executed": len(results),
        "checks": results,
        "violations": violations,
        "blocking_violations": blocking,
        "reason": "" if results else "검산 0건 — 구성요소 결측으로 전부 SKIP",
    }


def check_identities(db: Path) -> list[dict]:
    """위반(FAIL)만 반환하는 얇은 래퍼."""

    return identity_report(db)["violations"]
