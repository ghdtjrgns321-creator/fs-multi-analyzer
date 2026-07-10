"""외부 검증 에이전트(b단계) — 대상 선정·쿼리 생성·검증 실행·파이프라인 배선."""

from __future__ import annotations

import asyncio

import pytest

from src.report.external_verify import card_queries, select_top_cards, verify_cards
from src.schemas.findings import AccountFinding, IssueType


def _card(
    account: str, priority_score: float = 0.0, mat: float = 0.0, key: str | None = None
) -> AccountFinding:
    return AccountFinding(
        account=account,
        issue_type=IssueType.EARNINGS_TAX,
        materiality_score=mat,
        anomaly_score=1.0,
        confidence="High",
        priority_score=priority_score,
        cluster_key=key or f"acct:IS:{account}",
    )


# ── select_top_cards — 우선순위 연속 점수 내림 정렬, 상한 ──────────────────
def test_select_top_cards_by_priority():
    lows = [_card(f"CFS:acc{i}", priority_score=0.1 * i) for i in range(6)]
    top = select_top_cards(lows, top_n=3)
    assert [c.account for c in top] == ["CFS:acc5", "CFS:acc4", "CFS:acc3"]


# ── card_queries — 회사·연도·계정 + 분해 주도 요인 포함, ≤2개 ──────────────
def test_card_queries_include_driver_from_decomposition():
    card = _card("CFS:영업이익", mat=1.0)
    card.subtype = "영업이익 급감"
    decomp = {
        "rows": [
            {"account": "매출", "delta": -70.0},
            {"account": "판매비와관리비", "delta": +20.0},
        ],
        "residual": 0.0,
        "delta": -50.0,
    }
    queries = card_queries("테스트기업", 2025, card, decomp)
    assert 1 <= len(queries) <= 2
    assert any("테스트기업" in q and "영업이익" in q for q in queries)
    assert any("매출" in q for q in queries)  # 최대 하락 주도 요인이 검색어에


def test_card_queries_company_card_without_decomposition():
    card = _card("(회사 전체)", mat=1.0, key="company:기타")
    queries = card_queries("테스트기업", 2025, card, None)
    assert len(queries) == 1 and "테스트기업" in queries[0]


# ── verify_cards — stub 검색으로 카드 필드 채움 / 키 없음 deferred ──────────
class _Item:
    def __init__(self, claim: str, url: str, title: str = "뉴스") -> None:
        self.claim, self.source_url, self.source_title = claim, url, title


class _Brief:
    def __init__(self, items) -> None:
        self.items = items


def test_verify_cards_fills_evidence_and_checked():
    cards = [_card("CFS:영업이익", mat=1.0), _card("CFS:매출채권", mat=0.1)]

    async def fake_search(queries):
        return _Brief([_Item("판관비 절감 발표", "https://news.example/1")])

    stats = asyncio.run(
        verify_cards(
            cards,
            {"company_name": "테스트기업", "target_year": 2025},
            top_n=1,
            context_factory=fake_search,
        )
    )
    assert stats == {"status": "completed", "verified": 1, "found": 1}
    top = cards[0]
    assert top.external_checked is True
    assert top.external_evidence[0].url == "https://news.example/1"
    assert cards[1].external_checked is False  # top_n 밖 — 미수행 유지


def test_verify_cards_marks_checked_even_when_nothing_found():
    cards = [_card("CFS:영업이익", mat=1.0)]

    async def empty_search(queries):
        return _Brief([])

    asyncio.run(
        verify_cards(
            cards, {"company_name": "x", "target_year": 2025}, context_factory=empty_search
        )
    )
    assert cards[0].external_checked is True  # 검색했으나 미발견 — 은폐 금지
    assert cards[0].external_evidence == []


def test_verify_cards_deferred_without_google_key(monkeypatch):
    from config import settings as settings_module

    monkeypatch.setattr(settings_module.settings, "google_api_key", "", raising=False)
    cards = [_card("CFS:영업이익", mat=1.0)]
    stats = asyncio.run(verify_cards(cards, {"company_name": "x", "target_year": 2025}))
    assert stats["status"] == "deferred"
    assert cards[0].external_checked is False  # 아무것도 안 건드림


# ── 파이프라인 배선 — verifier가 카드 필드를 실제로 채우는지 ────────────────
def test_pipeline_wires_external_verifier():
    from src.report.card_pipeline import build_suspicion_cards
    from src.schemas.suspicion import PerspectiveOutput, SuspicionItem

    canned = {
        "numeric": PerspectiveOutput(
            suspicions=[
                SuspicionItem(
                    perspective="numeric",
                    scope="account",
                    issue_type=IssueType.REVENUE_RECEIVABLES,
                    account_id="매출채권",
                    sj_div="BS",
                    year="2024",
                    cited_value="100,000,000",
                    description="급증.",
                )
            ]
        )
    }

    async def runner(perspective, material):
        return canned.get(perspective, PerspectiveOutput(status="completed"))

    async def fake_verifier(cards, report, decompositions):
        for c in cards:
            c.external_checked = True
        return {"status": "completed", "verified": len(cards), "found": 0}

    async def fake_investigation(card, report, decomposition, **kw):
        # 기본 investigation_runner는 실 OpenAI 호출 — 단위테스트는 fake로 차단.
        return None

    async def fake_rebuttal(cards, context, **kw):
        # 기본 rebuttal_runner도 실 OpenAI 호출(run_rebuttal) — fake로 차단.
        from src.schemas.suspicion import RebuttalOutput

        return RebuttalOutput()

    report = {
        "corp_code": "x",
        "target_year": "2024",
        "account_level_series": [
            {
                "year": "2024",
                "sj_div": "BS",
                "series_key": "매출채권",
                "canonical": "매출채권",
                "label": "매출채권",
                "amount": 100_000_000.0,
                "mapping_status": "exact",
            }
        ],
        "unmapped_material_accounts": [],
    }
    from src.report.perspective_runner import ALL_PERSPECTIVES

    result = asyncio.run(
        build_suspicion_cards(
            report,
            agent_runner=runner,
            investigation_runner=fake_investigation,
            rebuttal_runner=fake_rebuttal,
            external_verifier=fake_verifier,
            materials={name: {} for name in ALL_PERSPECTIVES},
        )
    )
    [card] = result["account_cards"]
    assert card.external_checked is True  # verifier가 파이프라인 카드에 실제 반영
    assert result["external_verification"]["status"] == "completed"


# ── review_point / evidence_rows 중복 제거 (card_data) ─────────────────────
def test_review_point_flags_divergence_and_driver():
    from dashboard.card_data import review_point

    rows = [
        {"series_key": "CFS:매출", "year": 2024, "amount": 1000.0},
        {"series_key": "CFS:매출", "year": 2025, "amount": 933.0},  # -6.7%
    ]
    out = {
        "parent": "CFS:영업이익",
        "prior_year": 2024,
        "year": 2025,
        "change_pct": -62.8,
        "delta": -60.0,
        "residual": 0.0,
        "rows": [
            {"account": "매출총이익", "delta": -80.0},
            {"account": "판매비와관리비", "delta": +20.0},
        ],
    }
    text = review_point(out, rows)
    assert "매출은 -6.7%인데 영업이익은 -62.8%" in text
    assert "배 괴리" in text
    assert "매출총이익" in text and "주도" in text  # 주도 요인 결합
    assert review_point(None, rows) == ""  # 분해 없으면 두괄식 생략


def test_review_point_skips_divergence_for_sales_card():
    from dashboard.card_data import review_point

    rows = [
        {"series_key": "CFS:매출", "year": 2024, "amount": 1000.0},
        {"series_key": "CFS:매출", "year": 2025, "amount": 900.0},
    ]
    out = {
        "parent": "CFS:매출",
        "prior_year": 2024,
        "year": 2025,
        "change_pct": -10.0,
        "delta": -100.0,
        "residual": 0.0,
        "rows": [],
    }
    assert "괴리" not in review_point(out, rows)  # 부모=매출이면 괴리 명제 없음


def test_evidence_rows_excludes_decomposition_accounts():
    from dashboard.card_data import evidence_rows
    from src.schemas.findings import EvidenceRef

    card = _card("CFS:영업이익", mat=1.0)
    card.numeric_evidence = [
        EvidenceRef(source="financial_statement", locator="CFS:영업이익", year="2025", value="1"),
        EvidenceRef(source="financial_statement", locator="매출총이익", year="2025", value="2"),
        EvidenceRef(
            source="financial_statement", locator="ratio:operating_margin", year="2025", value="3"
        ),
    ]
    # ratio: 원시 지표 키는 사람이 못 읽는 노이즈 — 항상 제외. 분해 표 계정 2건도 제외 → 0건.
    rows = evidence_rows(card, exclude_accounts={"영업이익", "매출총이익"})
    assert rows == []
    # exclude 미지정이어도 ratio:는 빠지고 계정 참조만 남는다.
    assert [r["계정"] for r in evidence_rows(card)] == ["CFS:영업이익", "매출총이익"]


def test_decomposition_accounts_collects_parent_and_children():
    from dashboard.card_data import decomposition_accounts

    out = {
        "parent": "CFS:영업이익",
        "rows": [
            {"account": "매출총이익", "children": [{"account": "매출"}, {"account": "매출원가"}]},
            {"account": "판매비와관리비"},
        ],
    }
    assert decomposition_accounts(out) == {
        "영업이익",
        "매출총이익",
        "매출",
        "매출원가",
        "판매비와관리비",
    }
    assert decomposition_accounts(None) == set()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
