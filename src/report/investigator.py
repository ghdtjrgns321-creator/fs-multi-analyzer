"""카드별 조사원 — 결정론 게이트 + 도구 루프(PLAN §5 조사 단계).

게이트: 분해가 이미 원인을 설명(잔차 작고 단일 leaf 지배)했으면 도구 루프를 생략하고
종합 1호출만 한다. 배제가 아니라 경로 차이 — 모든 카드가 결론을 받는다.
"""

from __future__ import annotations


def needs_tool_loop(decomposition: dict | None, gate: dict) -> bool:
    """True = 도구 루프 필요(분해 없음·잔차 큼·기여 분산). False = 종합 1호출로 충분."""

    if not decomposition:
        return True
    residual_pct = decomposition.get("residual_pct")
    if residual_pct is None or abs(residual_pct) > float(gate.get("residual_pct_max", 20.0)):
        return True
    from dashboard.card_data import waterfall_leaves  # 기존 평탄화 재사용(external_verify 선례)

    delta = abs(float(decomposition.get("delta") or 0.0))
    if not delta:
        return True
    leaves = [(n, d) for n, d in waterfall_leaves(decomposition) if n != "미설명 잔차"]
    if not leaves:
        return True
    top_share = max(abs(d) for _, d in leaves) / delta * 100
    return top_share < float(gate.get("top_leaf_pct_min", 60.0))


__all__ = ["needs_tool_loop"]
