"""외부 검증 에이전트(b단계) — 대상 선정·쿼리 생성·검증 실행·파이프라인 배선."""

from __future__ import annotations

import asyncio

import pytest

from src.report.external_verify import card_queries, select_external_targets, verify_cards
from src.schemas.findings import AccountFinding, IssueType
from src.schemas.investigation import InvestigationConclusion


def _card(account: str, votes: int = 0, mat: float = 0.0, key: str | None = None) -> AccountFinding:
    """정렬 성분만으로 카드 생성 — 가중합 점수 폐지 후 순위는 표수 → 금액 사전식."""

    return AccountFinding(
        account=account,
        issue_type=IssueType.EARNINGS_TAX,
        materiality_score=mat,
        anomaly_score=1.0,
        confidence="High",
        vote_count=votes,
        cluster_key=key or f"acct:IS:{account}",
    )


# ── select_external_targets — 선정 = 조사 미해결 전부 ──────────────────────
def test_select_targets_excludes_only_resolved():
    resolved = _card("CFS:영업이익")
    resolved.investigation = InvestigationConclusion(headline="원인 완결", resolved=True)
    unresolved = _card("CFS:매출채권")
    unresolved.investigation = InvestigationConclusion(headline="미해결", resolved=False)
    no_investigation = _card("CFS:재고자산")  # 조사 실패·미수행 — 미확인이라 포함
    targets = select_external_targets([resolved, unresolved, no_investigation])
    assert {c.account for c in targets} == {"CFS:매출채권", "CFS:재고자산"}


def test_select_targets_excludes_resolved_regardless_of_rank():
    # 우선순위 상위 K장 예외 폐지 — 순위와 무관하게 resolved면 제외한다.
    top = _card("CFS:순이익", votes=3)
    top.investigation = InvestigationConclusion(headline="원인 완결", resolved=True)
    low_resolved = _card("CFS:영업이익", votes=1)
    low_resolved.investigation = InvestigationConclusion(headline="원인 완결", resolved=True)
    unresolved = _card("CFS:매출채권", votes=2)
    targets = select_external_targets([low_resolved, top, unresolved])
    assert [c.account for c in targets] == ["CFS:매출채권"]


def test_select_targets_hard_cap_drops_lowest_ranked():
    cards = [_card(f"CFS:acc{i}", mat=0.1 * i) for i in range(6)]
    capped = select_external_targets(cards, hard_cap=3)
    assert [c.account for c in capped] == ["CFS:acc5", "CFS:acc4", "CFS:acc3"]


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
    cards = [_card(f"CFS:acc{i}", mat=1.0 - 0.1 * i) for i in range(5)]
    # 상위 3장 밖의 카드가 조사 완결 — 검색 대상에서 제외된다(상위 K장은 resolved여도 포함).
    cards[4].investigation = InvestigationConclusion(headline="원인 완결", resolved=True)

    async def fake_search(queries):
        return _Brief([_Item("판관비 절감 발표", "https://news.example/1")])

    stats = asyncio.run(
        verify_cards(
            cards,
            {"company_name": "테스트기업", "target_year": 2025},
            context_factory=fake_search,
        )
    )
    assert stats == {"status": "completed", "verified": 4, "found": 4}
    top = cards[0]
    assert top.external_checked is True
    assert top.external_evidence[0].url == "https://news.example/1"
    assert cards[4].external_checked is False  # 하위 조사 완결 카드 — 검색 불필요, 미수행 유지


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
    # exclude 미지정이어도 ratio:는 빠지고 계정 참조만 남는다(표시는 fs_div 접두 벗긴 라벨).
    assert [r["계정"] for r in evidence_rows(card)] == ["영업이익", "매출총이익"]


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


# ── 설계4a: 외부 인용 금액 ↔ 내부 공시값 대사 ──────────────────────────────
def test_figure_to_won_parses_controlled_formats():
    from src.report.external_verify import figure_to_won

    assert figure_to_won("1,478억") == 1_478e8
    assert figure_to_won("4조 2,810억") == 4_2810e8
    assert figure_to_won("1.5조") == 1.5e12
    assert figure_to_won("532,893백만") == 532_893e6
    assert figure_to_won("190,475,674,544") == 190_475_674_544
    assert figure_to_won("증가했다") is None  # 금액 아님 — 대조불가


def test_verify_cards_marks_figure_check_match_and_mismatch():
    from src.schemas.investigation import InvestigationConclusion as _IC  # noqa: F401

    cards = [_card("CFS:영업활동현금흐름", mat=1.0)]
    report = {
        "company_name": "테스트기업",
        "target_year": 2025,
        # 내부 정답: 영업활동현금흐름 4,464억 / 영업권 손상 1,423억
        "account_level_series": [
            {"series_key": "CFS:영업활동현금흐름", "year": 2025, "amount": 446_400_000_000.0},
            {"series_key": "CFS:영업권", "year": 2025, "amount": 142_300_000_000.0},
        ],
    }

    async def fake_search(queries):
        ok = _Item("영업활동현금흐름 4,464억 기록", "https://news.example/ok")
        ok.figures = ["4,464억"]
        wrong = _Item("영업권 손상 1,478억 인식", "https://news.example/wrong")
        wrong.figures = ["1,478억"]  # 실제 공시 1,423억 — 결함④-a 실사례
        prose = _Item("업황 부진 지속", "https://news.example/prose")
        return _Brief([ok, wrong, prose])

    asyncio.run(verify_cards(cards, report, context_factory=fake_search))
    refs = {r.url.rsplit("/", 1)[-1]: r for r in cards[0].external_evidence}
    assert refs["ok"].figure_check == "match"
    assert refs["wrong"].figure_check == "mismatch"  # 저장은 하되 '공시와 상이' 마킹
    assert refs["wrong"].claimed_figures == ["1,478억"]
    assert refs["prose"].figure_check == "uncheckable"


# ── 설계4c: 리다이렉트 URL 해소 — 성공 시 원 기사 주소, 실패 시 원본 유지 ────
def test_verify_cards_resolves_redirect_urls_with_resolver():
    cards = [_card("CFS:영업이익", mat=1.0)]

    async def fake_search(queries):
        return _Brief([_Item("기사", "https://vertexaisearch.cloud.google.com/redirect/abc")])

    async def fake_resolver(url):
        return "https://news.example/original-article"

    asyncio.run(
        verify_cards(
            cards,
            {"company_name": "x", "target_year": 2025},
            context_factory=fake_search,
            url_resolver=fake_resolver,
        )
    )
    assert cards[0].external_evidence[0].url == "https://news.example/original-article"


def test_resolve_final_url_keeps_original_on_failure():
    from src.report.external_verify import resolve_final_url

    # 연결 불가 주소 — 예외를 삼키고 원본 URL을 유지한다(출처 도메인은 source에 보존).
    url = "http://127.0.0.1:9/unreachable"
    assert asyncio.run(resolve_final_url(url, timeout=0.2)) == url


def test_external_hard_cap_reads_config_and_fallback():
    """존재≠사용 차단 — hard_cap이 config를 실제로 읽고, 값 바꾸면 선정 수가 바뀐다."""

    from src.report.external_verify import external_hard_cap

    assert external_hard_cap({"external": {"hard_cap": 7}}) == 7
    assert external_hard_cap({}) == 30  # 폴백
    assert external_hard_cap() == 30  # 실제 config/investigation.yaml 값

    cards = [_card(account=f"CFS:acc{i}", mat=0.01 * i) for i in range(40)]
    assert len(select_external_targets(cards, hard_cap=7)) == 7
    assert len(select_external_targets(cards)) == 30  # 안전핀(실컨피그)
