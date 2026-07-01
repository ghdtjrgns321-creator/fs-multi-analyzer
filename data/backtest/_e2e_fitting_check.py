"""fitting 점검 — 다축 프로파일러가 대주/capex/관계기업 전용인지, 일반 작동인지.

분식 백테스트 회사·정상 회사에 build_account_profile을 적용해 (1)분식계정이 다축 후보(flagged)에
드는지 (2)flagged%가 회사간 안정적인지 실측. §10 단일사 일반화 금지 — 분식 다수·정상 교차.

실행: PYTHONPATH=. uv run python data/backtest/_e2e_fitting_check.py
"""

from __future__ import annotations

import csv
from pathlib import Path

from src.report.company_report import build_company_report
from src.signals.profiler import build_account_profile

LABELS = Path("data/backtest/labels.csv")
NORMALS = [("삼성전자", "00126380", [2022, 2023, 2024, 2025]), ("KAI", "00309503", [2016, 2017])]


def _fraud_cases() -> list[tuple[str, str, list[int], list[str]]]:
    """labels.csv에서 실행가능 분식사(runnable·positive)와 분식계정."""
    out = []
    with LABELS.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("label") == "positive" and r.get("runnable") == "True":
                years = [int(y) for y in (r.get("run_years") or "").split(";") if y.strip()]
                accts = [a.strip() for a in (r.get("accounts") or "").split(";") if a.strip()]
                out.append((r["company"], r["corp_code"], years, accts))
    return out


def _match(prof_keys: list[str], account: str) -> str | None:
    """분식계정명을 series_key에 부분매칭(양방향)."""
    core = account.split("(")[0].strip()  # '개발비(무형자산)'→'개발비'
    for k in prof_keys:
        if core and (core in k or k in core):
            return k
    return None


def _run(name: str, corp: str, years: list[int], accounts: list[str]) -> None:
    report = build_company_report(corp, years)
    prof = build_account_profile(report)
    if not prof:
        print(f"[{name}] 정규화 DB 없음 — skip")
        return
    rank = {p["series_key"]: (i, p) for i, p in enumerate(prof, 1)}
    flagged = sum(1 for p in prof if p["flagged"])
    print(
        f"\n[{name}] target={report.get('target_year')} leaf={len(prof)} "
        f"flagged={flagged}({flagged / max(len(prof), 1):.0%})"
    )
    if not accounts:
        return
    hit = 0
    for acct in accounts:
        key = _match(list(rank), acct)
        if key is None:
            print(f"   분식계정 '{acct}': 계정 미존재(프로파일에 없음)")
            continue
        i, p = rank[key]
        mark = "★flagged" if p["flagged"] else "미달"
        if p["flagged"]:
            hit += 1
        print(
            f"   분식계정 '{acct}'→{key!r}: 순위{i}/{len(prof)} {mark} "
            f"axes={p['tail_axes']} str={p['strength']:.2f}"
        )
    print(
        f"   >>> 분식계정 flagged 포착 {hit}/{len([a for a in accounts])} (1+이면 다축이 분식도 잡음)"
    )


def main() -> None:
    frauds = _fraud_cases()
    print(f"분식 실행가능 {len(frauds)}사 + 정상 {len(NORMALS)}사 점검")
    for name, corp, years, accts in frauds:
        _run(name, corp, years, accts)
    for name, corp, years in NORMALS:
        _run(name, corp, years, [])


if __name__ == "__main__":
    main()
