"""검사2 채점 엔진 단위 테스트 — 존재+순위 채점(텍스트 비교 없음, 결정론)."""

from __future__ import annotations

from golden.hit.check_hit import (
    card_anchor_keys,
    hit_rank,
    normalize_account_key,
    recall_at_k,
    top_card_count,
)


def _card(cluster_key, evidence=None, related=None):
    return {
        "cluster_key": cluster_key,
        "numeric_evidence": evidence or [],
        "related_accounts": related or [],
    }


def _ev(locator, kind="account"):
    return {"locator": locator, "resolved_kind": kind}


def test_normalize_unifies_key_formats():
    assert normalize_account_key("CFS:IS:당기순이익") == "CFS:당기순이익"
    assert normalize_account_key("acct:IS:CFS:당기순이익") == "CFS:당기순이익"
    assert normalize_account_key("CFS:당기순이익") == "CFS:당기순이익"
    assert normalize_account_key("canonical:투자활동현금흐름") == "투자활동현금흐름"


def test_card_anchor_keys_collects_cluster_and_evidence():
    card = _card("acct:IS:CFS:당기순이익", [_ev("CFS:매출"), _ev("지표키", kind="metric")])
    keys = card_anchor_keys(card)
    assert "CFS:당기순이익" in keys
    assert "CFS:매출" in keys  # 금액형 근거 계정도 앵커
    # metric 근거는 제외(계정 아님)
    assert "지표키" not in keys


def test_hit_rank_finds_target_position():
    cards = [
        _card("CFS:매출"),
        _card("acct:IS:CFS:당기순이익"),  # 정답이 2위 카드에
    ]
    # 정답 계정 identity 형식이 달라도 정규화로 매칭.
    assert hit_rank("CFS:IS:당기순이익", cards) == 2


def test_hit_rank_none_when_absent():
    cards = [_card("CFS:매출"), _card("CFS:영업이익")]
    assert hit_rank("CFS:없는계정", cards) is None


def test_hit_rank_matches_bare_name_against_fs_prefixed_card():
    # 정답지는 바 이름('재고자산'), 카드는 fs 접두('CFS:재고자산') — 이름 단위로 맞아야 한다.
    cards = [_card("CFS:매출"), _card("acct:BS:CFS:재고자산")]
    assert hit_rank("재고자산", cards) == 2
    # 접두 없는 카드에도 바 이름 매칭.
    assert hit_rank("매출", [_card("CFS:매출")]) == 1


def test_recall_at_k_counts_within_topk():
    cards = [
        _card("CFS:매출채권"),  # 1위
        _card("CFS:재고자산"),  # 2위
        _card("CFS:당기순이익"),  # 3위
    ]
    targets = ["CFS:IS:매출채권", "CFS:BS:당기순이익", "CFS:BS:없는계정"]
    # top-K=2: 매출채권(1위)만 적중, 당기순이익(3위)·없는계정 미적중.
    result = recall_at_k(targets, cards, k=2)
    assert result["n"] == 3
    assert result["hits"] == 1
    assert result["recall"] == 1 / 3
    # top-K=3: 매출채권·당기순이익 적중(2/3).
    assert recall_at_k(targets, cards, k=3)["hits"] == 2


def test_top_card_count_proxy():
    cards = [_card("A"), _card("B"), _card("C")]
    assert top_card_count(cards, k=10) == 3
    assert top_card_count(cards, k=2) == 2
