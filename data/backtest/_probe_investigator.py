"""조사원 프로브 — 저장된 카드 상위 N장에 실 LLM 조사를 태워 품질·비용 실측.

사용: uv run python data/backtest/_probe_investigator.py <corp_code> <year> [n_cards]
전면 배선 전 게이트 통과율·왕복 수·결론 품질을 사람이 확인하는 용도(비용 수백 원).

cards_store.load_cards는 {"account_cards": [...], "relationship_cards": [...],
"company_cards": [...], "series_rows": [...], "target_year": ...} 형태 dict(또는 부재시
None)를 반환한다. 각 카드는 model_dump(mode="json")으로 저장된 dict이므로
AccountFinding.model_validate로 복원해야 vote_count·account 등 속성 접근이 된다.
note_facts는 save_cards가 스냅샷에 남기지 않으므로 이 프로브에서는 빈 리스트로 진행한다
(find_notes 도구가 빈 결과를 반환할 뿐 실패하지 않음 — graceful degrade).
"""

from __future__ import annotations

import asyncio
import json
import sys

from src.report.card_order import card_sort_key
from src.report.cards_store import load_cards
from src.report.decomposition import decompose_change, load_bridges
from src.report.investigation_config import load_investigation_config
from src.report.investigator import needs_tool_loop, run_investigation
from src.schemas.findings import AccountFinding

_CARD_SECTIONS = ("account_cards", "relationship_cards", "company_cards")


async def main(corp: str, year: int, n_cards: int = 3) -> None:
    stored = load_cards(corp, year)
    if stored is None:
        print(f"저장된 카드 없음: {corp}/{year} — Phase2를 먼저 실행하세요.")
        return

    cards = [
        AccountFinding.model_validate(raw)
        for section in _CARD_SECTIONS
        for raw in (stored.get(section) or [])
    ]
    cards.sort(key=card_sort_key)  # 화면·리포트와 같은 사전식 정렬(표수 → 금액)
    cards = cards[:n_cards]
    if not cards:
        print(f"카드 0건: {corp}/{year}")
        return

    series_rows = stored.get("series_rows") or []
    target_year = int(stored.get("target_year") or year)
    report = {"account_level_series": series_rows, "target_year": target_year}
    bridges = load_bridges()
    gate = (load_investigation_config().get("investigation") or {}).get("gate", {})

    for card in cards:
        decomp = decompose_change(series_rows, card.account, target_year, bridges)
        gate_path = "루프" if needs_tool_loop(decomp, gate) else "요약"
        print(f"\n=== {card.account} | 게이트: {gate_path}")
        conclusion = await run_investigation(card, report, decomp)
        if conclusion is None:
            print("  실패/미수행")
            continue
        print(json.dumps(conclusion.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"사용: uv run python {sys.argv[0]} <corp_code> <year> [n_cards]")
        sys.exit(1)
    corp_code = sys.argv[1]
    target = int(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    asyncio.run(main(corp_code, target, n))
