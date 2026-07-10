"""Phase2 카드 조립 — PHASE2_DESIGN §4 ②③.

근거검증(grounding)을 통과한 의심건을 계정별로 묶어(회사레벨은 별도 버킷) 카드를 만든다.
표수(N/4)는 내부 4관점만, 외부·동종은 참고배지(#6). 점수·확신도는 코드가 결정론으로 매긴다
(원칙①). 카드 타입은 기존 `AccountFinding` 재사용 + 메타(vote_count·badges·cluster_key 등).
"""

from __future__ import annotations

from collections import Counter

from src.report.grounding import GroundedSuspicion
from src.schemas.findings import (
    AccountFinding,
    Claim,
    Confidence,
    EvidenceRef,
    IssueType,
    RiskLevel,
)
from src.schemas.suspicion import INTERNAL_PERSPECTIVES, SuspicionItem, cluster_key

COMPANY_LEVEL_ACCOUNT = "(회사 전체)"
_RISK_ORDER = {"Low": 0, "Medium": 1, "High": 2}


def cluster_suspicions(grounded: list[GroundedSuspicion]) -> list[dict]:
    """grounded만 추려 계정 cluster_key / 회사 issue_type 으로 묶는다."""

    survivors = [g for g in grounded if g.grounded]
    buckets: dict[tuple[str, str], dict] = {}
    order: list[tuple[str, str]] = []
    for g in survivors:
        item = g.item
        key = cluster_key(item) or ""
        if item.scope == "account":
            bucket_id = ("account", key)
            bucket_cluster_key = key
        elif item.scope == "relationship":
            # 관계는 다리조합 rel: 키로 묶는다(정렬 canonical이라 A↔B==B↔A 한 카드).
            bucket_id = ("relationship", key)
            bucket_cluster_key = key
        else:
            # 회사레벨은 유형(issue_type)으로 묶어 외부·동종 중복 카드를 합친다(#3·#11).
            # cluster_key를 company:{issue}로 둬 반박 매칭(S6)·카드 식별이 None 충돌 없이 된다.
            bucket_id = ("company", item.issue_type.value)
            bucket_cluster_key = f"company:{item.issue_type.value}"
        if bucket_id not in buckets:
            buckets[bucket_id] = {
                "scope": bucket_id[0],
                "cluster_key": bucket_cluster_key,
                "sj_div": item.sj_div,
                "account_id": item.account_id,
                "items": [],
                "grounded": [],
            }
            order.append(bucket_id)
        buckets[bucket_id]["items"].append(item)
        buckets[bucket_id]["grounded"].append(g)
    return [buckets[bid] for bid in order]


def _internal_votes(items: list[SuspicionItem]) -> int:
    return len({i.perspective for i in items if i.perspective in INTERNAL_PERSPECTIVES})


def _reference_badges(items: list[SuspicionItem]) -> list[str]:
    return sorted({i.perspective for i in items if i.perspective in {"external", "industry"}})


def _max_risk(items: list[SuspicionItem]) -> RiskLevel:
    return max((i.risk_level for i in items), key=lambda r: _RISK_ORDER[r])


def _dominant_issue(items: list[SuspicionItem]) -> IssueType:
    return Counter(i.issue_type for i in items).most_common(1)[0][0]


def _dominant_subtype(items: list[SuspicionItem]) -> str:
    """비공백 subtype 중 최빈값(없으면 ""). '기타' 유형의 실제 성격 보존(#14)."""

    subtypes = [i.subtype.strip() for i in items if i.subtype and i.subtype.strip()]
    if not subtypes:
        return ""
    return Counter(subtypes).most_common(1)[0][0]


def _confidence(value_verified: bool, votes: int, mapping_status: str | None) -> Confidence:
    """매핑강도 + 근거검증 + 표수 결정론 산정(#12)."""

    score = 0
    if value_verified:
        score += 1
    if votes >= 2:
        score += 1
    if mapping_status == "exact":
        score += 1
    elif mapping_status in {"unmapped_extension_account", "OTHER", None} and votes == 0:
        score -= 1
    if score >= 2:
        return "High"
    if score == 1:
        return "Medium"
    return "Low"


def _amount_lookup(report: dict) -> tuple[dict[str, float], dict[str, str]]:
    """target_year 계정 식별자 → 절대금액 / 매핑상태."""

    year = str(report.get("target_year", ""))
    amounts: dict[str, float] = {}
    mappings: dict[str, str] = {}
    for row in report.get("account_level_series", []) or []:
        if str(row.get("year")) != year:
            continue
        try:
            amount = abs(float(row.get("amount")))
        except (TypeError, ValueError):
            continue
        status = str(row.get("mapping_status", ""))
        for field in ("series_key", "canonical", "label"):
            key = row.get(field)
            if key:
                amounts[str(key)] = amount
                mappings[str(key)] = status
    return amounts, mappings


def _signal_keys(report: dict) -> set[str]:
    """신호가 참조한 계정명 집합(anomaly 존재 판정용)."""

    snapshot = report.get("latest_signal_snapshot", {}) or {}
    keys: set[str] = set()
    for rows in snapshot.values():
        if isinstance(rows, list):
            for row in rows:
                acc = isinstance(row, dict) and row.get("account")
                if acc:
                    keys.add(str(acc))
    return keys


def _aggregate_evidence(items: list[SuspicionItem]) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for item in items:
        refs.extend(item.evidence)
    return refs


def _claims(items: list[SuspicionItem]) -> list[Claim]:
    """클러스터 의심건들의 주장 원문 → 카드 claims(관점·설명·인용수치). 1:1 — 누락 금지."""

    return [
        Claim(perspective=i.perspective, description=i.description, cited_value=i.cited_value)
        for i in items
    ]


def build_cards(grounded: list[GroundedSuspicion], report: dict) -> dict[str, list[AccountFinding]]:
    """grounded 의심건 → 계정 카드 + 회사레벨 카드(별도 섹션)."""

    clusters = cluster_suspicions(grounded)
    amounts, mappings = _amount_lookup(report)
    signal_keys = _signal_keys(report)

    account_cards: list[AccountFinding] = []
    company_cards: list[AccountFinding] = []
    relationship_cards: list[AccountFinding] = []
    raw_materiality: list[float] = []
    rel_raw_materiality: list[float] = []

    for cluster in clusters:
        items: list[SuspicionItem] = cluster["items"]
        grounded_items: list[GroundedSuspicion] = cluster["grounded"]
        votes = _internal_votes(items)
        value_verified = any(g.value_verified for g in grounded_items)
        scope = cluster["scope"]

        if scope == "relationship":
            # 관계 카드: 단일 계정으로 붕괴시키지 않고 다리 전체를 보유. 유의성=다리 금액 최댓값
            # (큰 계정이 엮인 관계가 상위 정렬), 이상=다리 하나라도 신호 참조시.
            legs = _relationship_legs(items)
            raw = max((amounts.get(leg, 0.0) for leg in legs), default=0.0)
            anomaly = 1.0 if any(leg in signal_keys for leg in legs) else 0.0
            relationship_cards.append(
                AccountFinding(
                    account=" ↔ ".join(legs),
                    issue_type=_dominant_issue(items),
                    subtype=_dominant_subtype(items),
                    materiality_score=raw,
                    anomaly_score=anomaly,
                    confidence=_confidence(value_verified, votes, None),
                    numeric_evidence=_aggregate_evidence(items),
                    risk_level=_max_risk(items),
                    vote_count=votes,
                    internal_total=len(INTERNAL_PERSPECTIVES),
                    reference_badges=_reference_badges(items),
                    cluster_key=cluster["cluster_key"],
                    related_accounts=legs,
                    claims=_claims(items),
                )
            )
            rel_raw_materiality.append(raw)
            continue

        is_account = scope == "account"
        key = str(cluster["account_id"] or "")
        raw = amounts.get(key, 0.0) if is_account else 0.0
        anomaly = 1.0 if key and key in signal_keys else 0.0
        prior_value, prior_year = _prior_from_change(items)
        card = AccountFinding(
            account=key if is_account else COMPANY_LEVEL_ACCOUNT,
            issue_type=_dominant_issue(items),
            subtype=_dominant_subtype(items),
            materiality_score=raw,  # 정규화는 아래에서 일괄(0..1)
            anomaly_score=anomaly,
            confidence=_confidence(
                value_verified, votes, mappings.get(key) if is_account else None
            ),
            numeric_evidence=_aggregate_evidence(items),
            risk_level=_max_risk(items),
            vote_count=votes,
            internal_total=len(INTERNAL_PERSPECTIVES),
            reference_badges=_reference_badges(items),
            cluster_key=cluster["cluster_key"],
            prior_value=prior_value,
            prior_year=prior_year,
            claims=_claims(items),
        )
        if is_account:
            account_cards.append(card)
            raw_materiality.append(raw)
        else:
            company_cards.append(card)

    # materiality 0..1 정규화(각 카드 집합 내 최대 절대금액 대비) — sort·표시용.
    _normalize_materiality(account_cards, raw_materiality)
    _normalize_materiality(relationship_cards, rel_raw_materiality)

    return {
        "account_cards": account_cards,
        "company_cards": company_cards,
        "relationship_cards": relationship_cards,
    }


def _relationship_legs(items: list[SuspicionItem]) -> list[str]:
    """클러스터 내 관계 의심건들의 다리 합집합(정렬). 같은 rel 키라 보통 동일하나 안전하게 union."""

    from src.schemas.suspicion import relationship_legs

    legs: set[str] = set()
    for item in items:
        legs.update(relationship_legs(item))
    return sorted(legs)


def _prior_from_change(items: list[SuspicionItem]) -> tuple[str | None, str | None]:
    """클러스터 내 change 의심건의 전기값·전기연도(死필드 부활). 첫 보유 건 채택."""

    for item in items:
        if item.prior_value or item.prior_year:
            return item.prior_value, item.prior_year
    return None, None


def _normalize_materiality(cards: list[AccountFinding], raw: list[float]) -> None:
    """카드 집합 내 최대 절대금액 대비 0..1 정규화(집합별 독립)."""

    max_raw = max(raw, default=0.0)
    if max_raw > 0:
        for card in cards:
            card.materiality_score = round(card.materiality_score / max_raw, 4)


__all__ = ["COMPANY_LEVEL_ACCOUNT", "build_cards", "cluster_suspicions"]
