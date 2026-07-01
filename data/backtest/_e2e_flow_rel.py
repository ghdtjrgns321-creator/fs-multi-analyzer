"""flow 관계(relationship) 출력 검증 — 실 LLM E2E (대주 00112457).

근본 수리 후 flow가 scope="relationship" 카드를 실제로 내는지 확인한다(존재≠사용).
특히 연결↔별도 현금 괴리(cfs_ofs)가 관계 카드로 살아나는지 본다.
실행: PYTHONPATH=. uv run python data/backtest/_e2e_flow_rel.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.report.card_pipeline import build_suspicion_cards
from src.report.company_report import build_company_report

CORP = "00112457"
OUT = Path(f"data/backtest/_E2E_FLOW_REL_{CORP}.json")


def _card(c) -> dict:
    return {
        "account": c.account,
        "related_accounts": c.related_accounts,
        "issue_type": getattr(c.issue_type, "value", str(c.issue_type)),
        "vote_count": c.vote_count,
        "materiality": round(c.materiality_score, 2),
        "confidence": c.confidence,
        "risk": c.risk_level,
        "rebuttal_verdict": getattr(c.rebuttal_verdict, "value", c.rebuttal_verdict),
    }


def main() -> None:
    report = build_company_report(CORP, [2021, 2022, 2023, 2024])
    result = asyncio.run(build_suspicion_cards(report, run_llm=True))

    # 관점별 scope 분포
    scope_by_persp: dict[str, dict[str, int]] = {}
    flow_items: list[dict] = []
    for g in result.get("grounded", []):
        it = g.item
        d = scope_by_persp.setdefault(it.perspective, {})
        d[it.scope] = d.get(it.scope, 0) + 1
        if it.perspective == "flow":
            flow_items.append(
                {
                    "scope": it.scope,
                    "account_id": it.account_id,
                    "related_accounts": it.related_accounts,
                    "cited_value": it.cited_value,
                    "grounded": g.grounded,
                    "desc": it.description[:200],
                }
            )

    rel_cards = [_card(c) for c in result.get("relationship_cards", [])]
    payload = {
        "scope_by_perspective": scope_by_persp,
        "flow_items": flow_items,
        "relationship_cards": rel_cards,
        "counts": {
            "account_cards": len(result.get("account_cards", [])),
            "company_cards": len(result.get("company_cards", [])),
            "relationship_cards": len(rel_cards),
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"scope별 관점 분포: {scope_by_persp}")
    print(f"관계 카드 {len(rel_cards)}건:")
    for c in rel_cards:
        print(f"  - {c['account']}  vote={c['vote_count']}  {c['issue_type']}")
    print(f"저장: {OUT}")


if __name__ == "__main__":
    main()
