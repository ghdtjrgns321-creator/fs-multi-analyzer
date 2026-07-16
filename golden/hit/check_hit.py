"""검사2 채점 엔진 — 순수함수(LLM·네트워크 0), 설계 §3.2.

LLM 문구는 매 실행 달라지므로 텍스트를 비교하지 않는다. 정답 계정이 카드 큐에 **존재하는가와
그 순위**만 본다 → 비결정론이어도 점수(recall@K·rank)가 안정적이다.

카드는 표시 순서(우선순위 정렬)대로 들어온다고 가정한다(build_card_report가 이미 정렬).
"""

from __future__ import annotations

from typing import Any

# 계정 식별자 정규화 — 카드 locator·재표시 identity의 서로 다른 형식을 (fs_div, 계정명)으로 통일.
_NAMESPACES = frozenset({"acct", "canonical", "note_facts", "note", "note_disclosure"})
_SJ_DIVS = frozenset({"BS", "IS", "CF", "CIS", "SCE"})
_FS_DIVS = frozenset({"CFS", "OFS"})


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def normalize_account_key(key: str) -> str:
    """계정 키를 'fs_div:계정명'(또는 계정명)으로 정규화.

    'CFS:IS:당기순이익'·'acct:IS:CFS:당기순이익'·'CFS:당기순이익' → 'CFS:당기순이익'.
    'canonical:투자활동현금흐름' → '투자활동현금흐름'. LLM 발명 접두·sj_div 토큰을 제거하고
    fs_div(CFS/OFS)와 마지막 계정명 토큰만 남긴다.
    """

    tokens = [t.strip() for t in str(key or "").split(":") if t.strip()]
    fs_div = ""
    name_parts: list[str] = []
    for token in tokens:
        if token in _NAMESPACES or token in _SJ_DIVS:
            continue
        if token in _FS_DIVS:
            fs_div = token
            continue
        name_parts.append(token)
    name = name_parts[-1] if name_parts else ""
    return f"{fs_div}:{name}" if fs_div else name


def card_anchor_keys(card: Any) -> set[str]:
    """카드가 가리키는 계정 앵커 키 집합(정규화) — cluster_key·account + 금액형 근거 locator."""

    keys: set[str] = set()
    for field in ("cluster_key", "account"):
        value = _get(card, field)
        if value:
            keys.add(normalize_account_key(str(value)))
    for ref in _get(card, "numeric_evidence") or []:
        if _get(ref, "resolved_kind") in ("metric", "narrative"):
            continue
        locator = _get(ref, "locator")
        if locator:
            keys.add(normalize_account_key(str(locator)))
    for leg in _get(card, "related_accounts") or []:
        keys.add(normalize_account_key(str(leg)))
    keys.discard("")
    return keys


def _key_name(key: str) -> str:
    """정규화 키의 계정명 부분(fs_div 접두 제거, 'code|label' 파이프도 제거)."""

    name = str(key).split(":")[-1]
    return name.split("|")[-1].strip()


def hit_rank(target: str, ordered_cards: list[Any]) -> int | None:
    """정답 계정이 처음 등장하는 카드의 1-기반 순위. 없으면 None.

    **이름 단위 매칭** — 정답지(labels.csv)는 바 계정명('재고자산')이고 카드 앵커는 fs_div 접두
    ('CFS:재고자산')다. CFS/OFS 어느 표든 '그 계정을 짚었나'가 판정 기준이므로 계정명으로 맞춘다.
    """

    target_name = _key_name(normalize_account_key(target))
    if not target_name:
        return None
    for position, card in enumerate(ordered_cards or [], start=1):
        card_names = {_key_name(k) for k in card_anchor_keys(card)}
        if target_name in card_names:
            return position
    return None


def recall_at_k(targets: list[str], ordered_cards: list[Any], k: int) -> dict[str, Any]:
    """정답 계정 목록의 top-K 적중률. 분모 N=고유 정답 계정 수, ranks로 계정별 순위 노출."""

    unique = sorted({normalize_account_key(t) for t in targets if normalize_account_key(t)})
    ranks = {t: hit_rank(t, ordered_cards) for t in unique}
    hits = [t for t, r in ranks.items() if r is not None and r <= k]
    n = len(unique)
    return {
        "k": k,
        "n": n,
        "hits": len(hits),
        "recall": (len(hits) / n) if n else 0.0,
        "ranks": ranks,
        "missed": [t for t, r in ranks.items() if r is None or r > k],
    }


def top_card_count(ordered_cards: list[Any], k: int) -> int:
    """대조군 거짓양성 프록시 — 상위 K 안에 실제로 존재하는 카드 수(정상사는 적어야 정상)."""

    return min(k, len(ordered_cards or []))


def score_report(md_lines: dict[str, Any]) -> str:
    """채점 결과 dict → 채점표 마크다운(계정별 적중·순위 + 헤더 recall@K)."""

    r = md_lines
    lines = [
        f"# 검사2 적중 채점 — {r.get('corp', '')}/{r.get('year', '')}",
        "",
        f"- recall@{r.get('k')} = {r.get('hits')}/{r.get('n')} ({r.get('recall', 0.0):.2f})",
        f"- 미적중: {r.get('missed', [])}",
        "",
        "| 정답 계정 | 순위 | 적중 |",
        "| --- | --- | --- |",
    ]
    for target, rank in (r.get("ranks") or {}).items():
        hit = "O" if rank is not None and rank <= r.get("k", 0) else "X"
        lines.append(f"| {target} | {rank if rank is not None else '-'} | {hit} |")
    return "\n".join(lines) + "\n"


__all__ = [
    "card_anchor_keys",
    "hit_rank",
    "normalize_account_key",
    "recall_at_k",
    "score_report",
    "top_card_count",
]
