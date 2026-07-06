"""전과정 산출물 평가 — 독립 회계분석 대조용 자료 추출.

목적: 내가(회계전문가) DART raw로 한 독립 분석을 프로젝트 산출물과 1:1 대조한다.
  ③ 전처리: raw 핵심계정(oracle) vs normalized DB 금액 1:1 대조(불일치 건수).
  ④ Phase1: review_queue·account_series·ratio 실제 내용 덤프.
  ⑤ Phase2: grounded 의심건을 관점별로 + 카드(반박 verdict·근거) 덤프.

oracle 값은 raw CSV에서 내가 읽은 검증 기댓값(테스트 oracle — 분석 구동값 아님).
실행: PYTHONPATH=. uv run python data/backtest/_e2e_eval.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import duckdb

from config.settings import settings
from src.db.normalized import db_path
from src.report.card_pipeline import build_suspicion_cards
from src.report.company_report import build_company_report

CORP = sys.argv[1] if len(sys.argv) > 1 else "00112457"  # 대상 corp(인자화)
YEAR = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
ROOT = settings.data_dir
OUT = Path(f"data/backtest/_E2E_EVAL_{CORP}_{YEAR}.json")

# ── ③ oracle: raw CFS에서 직접 읽은 핵심계정(원 단위). (sj_div, canonical, year) → 기댓값 ──
# 2024(제63기)·2023(제62기) 두 연도 = ripple 2케이스 교차.
ORACLE = {
    2024: {
        ("BS", "자산총계"): 111411700508,
        ("BS", "부채총계"): 27901796683,
        ("BS", "자본총계"): 83509903825,
        ("BS", "유동자산"): 34391894547,
        ("BS", "비유동자산"): 77019805961,
        ("BS", "유동부채"): 15352456641,
        ("BS", "비유동부채"): 12549340042,
        ("BS", "현금및현금성자산"): 10958272295,
        ("BS", "이익잉여금"): 51280618150,
        ("BS", "단기차입금"): 3105125786,
        ("CIS", "매출"): 106038654753,
        ("CIS", "매출원가"): 81134897169,
        ("CIS", "매출총이익"): 24903757584,
        ("CIS", "영업이익"): 10025103418,
        ("CIS", "당기순이익"): 8315526894,
        ("CF", "영업활동현금흐름"): 11330064730,
        ("CF", "투자활동현금흐름"): -2548740883,
        ("CF", "재무활동현금흐름"): -7186142192,
    },
    2023: {
        ("BS", "자산총계"): 111337641407,
        ("BS", "부채총계"): 34658284670,
        ("BS", "자본총계"): 76679356737,
        ("CIS", "매출"): 105014557386,
        ("CIS", "영업이익"): 7684213963,
        ("CIS", "당기순이익"): 10149663332,
        ("CF", "영업활동현금흐름"): 11613190263,
    },
}


def _db_amounts(year: int) -> dict[tuple[str, str], int]:
    """normalized DB의 (sj_div, canonical) → amount(원, round). CFS 한정."""
    path = db_path(CORP, year, ROOT)
    if not path.exists():
        return {}
    con = duckdb.connect(str(path), read_only=True)
    try:
        rows = con.execute(
            "SELECT sj_div, canonical, amount FROM normalized_financials "
            "WHERE fs_div='CFS' AND amount IS NOT NULL"
        ).fetchall()
    finally:
        con.close()
    # CIS↔IS 통합 가능 → canonical 키로 모으되 sj_div도 보존(매출 등은 IS로 갈 수 있음).
    out: dict[tuple[str, str], int] = {}
    for sj, canon, amt in rows:
        out[(sj, str(canon))] = round(float(amt))
        out[("*", str(canon))] = round(float(amt))  # sj 무관 보조키(CIS/IS 흡수)
    return out


def _preprocess_check() -> dict:
    rows = []
    mismatches = 0
    for year, oracle in ORACLE.items():
        db = _db_amounts(year)
        for (sj, canon), expected in oracle.items():
            got = db.get((sj, canon))
            if got is None:
                got = db.get(("*", canon))  # sj_div 재분류 흡수
            ok = got is not None and round(float(expected)) == got
            if not ok:
                mismatches += 1
            rows.append(
                {
                    "year": year,
                    "sj_div": sj,
                    "canonical": canon,
                    "raw_oracle": expected,
                    "db_amount": got,
                    "match": ok,
                }
            )
    return {"checked": len(rows), "mismatches": mismatches, "rows": rows}


def main() -> None:
    report = build_company_report(CORP, [2021, 2022, 2023, 2024])

    # ④ Phase1 자료
    phase1 = {
        "company_name": report.get("company_name"),
        "target_year": report.get("target_year"),
        "review_queue": report.get("review_queue"),
        "ratio_summary": report.get("ratio_summary"),
        "ratio_time_series": report.get("ratio_time_series"),
        "unmapped_material_accounts": report.get("unmapped_material_accounts"),
        "account_series_count": len(report.get("account_level_series", [])),  # type: ignore[arg-type]
    }

    # ③ 전처리 1:1 대조 — ORACLE은 대주(00112457) 전용. 타 corp는 스킵.
    preprocess = (
        _preprocess_check()
        if CORP == "00112457"
        else {"checked": 0, "mismatches": 0, "rows": [], "skipped": f"ORACLE 없음(corp={CORP})"}
    )

    # ⑤ Phase2 관점별 의심건 + 카드
    result = asyncio.run(build_suspicion_cards(report, run_llm=True))

    by_persp: dict[str, list] = {}
    for g in result.get("grounded", []):
        it = g.item
        by_persp.setdefault(it.perspective, []).append(
            {
                "scope": it.scope,
                "issue_type": it.issue_type.value
                if hasattr(it.issue_type, "value")
                else str(it.issue_type),
                "account_id": it.account_id,
                "year": it.year,
                "cited_value": it.cited_value,
                "description": it.description[:300],
                "grounded": g.grounded,
                "value_verified": g.value_verified,
                "reason": g.reason[:120],
            }
        )

    def _card(c) -> dict:
        return {
            "account": c.account,
            "issue_type": c.issue_type.value
            if hasattr(c.issue_type, "value")
            else str(c.issue_type),
            "vote_count": c.vote_count,
            "materiality": round(c.materiality_score, 2),
            "anomaly": round(c.anomaly_score, 2),
            "confidence": c.confidence,
            "risk": c.risk_level,
            "rebuttal_verdict": getattr(c.rebuttal_verdict, "value", c.rebuttal_verdict),
            "counter_evidence": c.counter_evidence,
            "normal_explanation": c.normal_explanation,
            "confirm_question": c.confirm_question,
            "next_procedure": c.next_procedure,
            "reference_badges": c.reference_badges,
        }

    phase2 = {
        "account_cards": [_card(c) for c in result.get("account_cards", [])],
        "company_cards": [_card(c) for c in result.get("company_cards", [])],
        "grounded_by_perspective": by_persp,
        "grounded_total": len(result.get("grounded", [])),
        "dropped": [
            {
                "perspective": g.item.perspective,
                "desc": g.item.description[:150],
                "reason": g.reason[:150],
            }
            for g in result.get("dropped", [])
        ],
        "rebuttal_entries": result.get("rebuttal_entries"),
    }

    OUT.write_text(
        json.dumps(
            {"preprocess": preprocess, "phase1": phase1, "phase2": phase2},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"전처리 대조: {preprocess['checked']}건 중 불일치 {preprocess['mismatches']}건")
    print(
        f"Phase1 queue: {len(phase1['review_queue'])}건 · unmapped: {len(phase1['unmapped_material_accounts'])}건"
    )
    print(
        f"Phase2 grounded: {phase2['grounded_total']} · 관점별: {{ {', '.join(f'{k}:{len(v)}' for k, v in by_persp.items())} }}"
    )
    print(
        f"  account_cards: {len(phase2['account_cards'])} · company_cards: {len(phase2['company_cards'])} · dropped: {len(phase2['dropped'])}"
    )
    print(f"저장: {OUT}")


if __name__ == "__main__":
    main()
