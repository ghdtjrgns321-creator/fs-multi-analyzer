"""이관 원장 판정 — 원본 항목 전량이 설명되는지 하나의 결론으로 모은다.

  모집단 = 원본에 있던 모든 항목(재무제표 raw 행 · 자본변동표 raw 행 · 주석 fact)
         = 적재된 것 + 사유가 붙은 제외 + 미설명

미설명이 1건이라도 있으면 통과가 아니다. 원본이 없어 대조 자체를 못 하면(checkable=False)
그것도 통과가 아니다 — 빈 검사를 통과로 세지 않는다.

임계는 없다. "몇 %를 실었나"가 아니라 "설명 못 하는 항목이 있나"만 묻는다.
"""

from __future__ import annotations

from pathlib import Path

from src.normalize.ledger_financials import financial_ledger, sce_transfer
from src.normalize.ledger_notes import note_ledger


def transfer_ledger(corp_code: str, year: str, base_dir: Path) -> dict:
    """세 원본 축의 원장을 계산하고 미설명 0 여부로 판정한다."""

    financials = financial_ledger(corp_code, year, base_dir)
    sce = sce_transfer(corp_code, year, base_dir)
    notes = note_ledger(corp_code, year, base_dir)

    unexplained = len(financials["unexplained"]) + sce["unexplained"] + notes["unexplained"]
    uncheckable = [
        name
        for name, axis in (("재무제표", financials), ("자본변동표", sce), ("주석", notes))
        if not axis["checkable"]
    ]
    return {
        "passed": not unexplained and not uncheckable,
        "unexplained": unexplained,
        "uncheckable": uncheckable,
        "financials": financials,
        "sce": sce,
        "notes": notes,
    }


def ledger_lines(ledger: dict) -> list[str]:
    """사람이 읽는 원장 요약 — 축별로 '원본 N = 적재 + 사유제외 + 미설명'을 보인다."""

    lines: list[str] = []
    financials = ledger["financials"]
    if financials["checkable"]:
        excluded = " · ".join(f"{k} {v}" for k, v in financials["excluded"].items()) or "없음"
        lines.append(
            f"재무제표 원본 {financials['total']}행 = 적재 {financials['loaded']} + "
            f"제외({excluded}) + 미설명 {len(financials['unexplained'])}"
        )
    else:
        lines.append("재무제표 — 원본 CSV 없음(대조 불가)")

    sce = ledger["sce"]
    if sce["raw_rows"]:
        lines.append(
            f"자본변동표 원본 {sce['raw_rows']}행 → 2D 셀 {sce['cells']} · "
            f"미설명 {sce['unexplained']}"
        )

    notes = ledger["notes"]
    if notes["checkable"] and notes["total"]:
        excluded = " · ".join(f"{k} {v}" for k, v in notes["excluded"].items()) or "없음"
        lines.append(
            f"주석 원본 {notes['total']}건 = 적재 {notes['loaded']} + "
            f"제외({excluded}) + 미설명 {notes['unexplained']}"
        )
    elif not notes["checkable"]:
        lines.append("주석 — 원본 XBRL 없음(수집 사유 기록도 없음 — 대조 불가)")
    return lines
