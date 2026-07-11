"""대형 카드 데이터 가공(card_data 순수함수) + claims 전파(card_builder) 검증.

각 함수 2+ 케이스: 정상 입력 / 빈·경계 입력(hollow 방지 §9).
"""

from __future__ import annotations

import pytest

from dashboard.card_data import (
    claim_lines,
    evidence_rows,
    fmt_krw,
    humanize_amounts,
    legs_top,
    series_points,
    split_series_key,
)
from src.schemas.findings import AccountFinding, Claim, EvidenceRef, IssueType

SERIES_ROWS = [
    {"series_key": "CFS:무형자산", "year": 2023, "amount": 2_500_000_000_000.0},
    {"series_key": "CFS:무형자산", "year": 2024, "amount": 1_964_277_226_876.0},
    {"series_key": "CFS:매출채권", "year": 2024, "amount": 900_000_000.0},
    {"series_key": "OFS:무형자산", "year": 2024, "amount": 100.0},  # 동명 별도 — 격리 확인
]


# ── split_series_key ──────────────────────────────────────────────────────
def test_split_series_key_cfs_ofs():
    assert split_series_key("CFS:무형자산") == ("연결", "무형자산")
    assert split_series_key("OFS:차입금") == ("별도", "차입금")


def test_split_series_key_no_prefix_kept_verbatim():
    assert split_series_key("(회사 전체)") == ("", "(회사 전체)")
    assert split_series_key("") == ("", "")


# ── fmt_krw ───────────────────────────────────────────────────────────────
def test_fmt_krw_units():
    assert fmt_krw(1_964_277_226_876) == "2.0조"
    assert fmt_krw(120_000_000_000) == "1,200억"
    assert fmt_krw(-350_000_000) == "-4억"
    assert fmt_krw(12_345) == "12,345"


def test_fmt_krw_non_numeric():
    assert fmt_krw(None) == "-"
    assert fmt_krw("abc") == "-"


# ── humanize_amounts (서술 큰 원숫자 → 억/조) ─────────────────────────────
def test_humanize_converts_large_won_to_eok_jo():
    out = humanize_amounts("영업이익 1,289,630,423,605 → 170,688,596,929로 감소")
    assert "1.3조원" in out and "1,707억원" in out
    assert "1,289,630,423,605" not in out  # 12자리 원단위 나열 사라짐


def test_humanize_leaves_years_percents_and_small_amounts():
    # 연도(4자리)·퍼센트·1억 미만은 불변(오변환 방지)
    assert humanize_amounts("2021년 매출 15.94% 증가") == "2021년 매출 15.94% 증가"
    assert humanize_amounts("과태료 6,000,000원") == "과태료 6,000,000원"  # 6백만 < 1억


def test_humanize_plain_digits_with_decimal():
    # 인용수치형 '170688596929.0'도 축약
    assert "1,707억원" in humanize_amounts("인용 170688596929.0 참조")


def test_humanize_does_not_mangle_decimal_fraction():
    # 버그 재현 방지: trend 0.1628882442191079의 소수부를 금액으로 오변환하면 안 됨
    text = "trend가 0.1628882442191079로 높고"
    assert humanize_amounts(text) == text  # 소수는 그대로


# ── series_points ─────────────────────────────────────────────────────────
def test_series_points_sorted_and_isolated():
    pts = series_points(SERIES_ROWS, "CFS:무형자산")
    assert [p["year"] for p in pts] == [2023, 2024]  # 연도 오름차순
    assert pts[1]["amount"] == 1_964_277_226_876.0
    # OFS 동명계정(100.0)이 섞이지 않는다(이질병합 차단)
    assert all(p["amount"] != 100.0 for p in pts)


def test_series_points_missing_key_empty():
    assert series_points(SERIES_ROWS, "CFS:없는계정") == []
    assert series_points([], "CFS:무형자산") == []


# ── evidence_rows / claim_lines ───────────────────────────────────────────
def _card(**overrides) -> AccountFinding:
    base = dict(
        account="CFS:무형자산",
        issue_type=IssueType.ASSET_VALUATION,
        materiality_score=1.0,
        anomaly_score=1.0,
        confidence="High",
        risk_level="High",
    )
    return AccountFinding(**{**base, **overrides})


def test_evidence_rows_dedup_and_fields():
    ref = EvidenceRef(
        source="financial_statement", locator="무형자산", year="2024", value="1964277226876"
    )
    card = _card(numeric_evidence=[ref, ref])  # 동일 참조 2건 → 1행
    rows = evidence_rows(card)
    assert rows == [{"계정": "무형자산", "연도": "2024", "금액": "2.0조"}]  # 억/조 축약


def test_evidence_rows_empty():
    assert evidence_rows(_card()) == []


def test_claim_lines_labels_and_skips_blank():
    card = _card(
        claims=[
            Claim(perspective="numeric", description="전기 대비 30% 감소", cited_value="1.96조"),
            Claim(perspective="flow", description="  "),  # 빈 설명 — 제외
        ]
    )
    lines = claim_lines(card)
    assert len(lines) == 1
    assert lines[0]["perspective"] == "수치"  # 내부명 → 사람용 라벨
    assert lines[0]["cited_value"] == "1.96조"


def test_claim_lines_empty_card():
    assert claim_lines(_card()) == []


# ── legs_top ──────────────────────────────────────────────────────────────
def test_legs_top_orders_by_max_abs_and_limits():
    legs = ["CFS:매출채권", "CFS:무형자산", "CFS:없는계정"]
    top = legs_top(legs, SERIES_ROWS, limit=2)
    assert top == ["CFS:무형자산", "CFS:매출채권"]  # 금액 큰 순 + 상한 2


def test_legs_top_empty():
    assert legs_top([], SERIES_ROWS) == []


# ── 카드 렌더 스모크 (AppTest) — st API 오용(height=None 류)은 순수 테스트로 안 잡힘 ──
def test_render_suspicion_card_apptest_smoke():
    from streamlit.testing.v1 import AppTest

    def _app():
        import streamlit as st  # noqa: F401 — AppTest 함수 앱 컨텍스트

        from dashboard.card_view import render_suspicion_card
        from src.schemas.findings import AccountFinding, Claim, EvidenceRef, IssueType

        card = AccountFinding(
            account="CFS:영업이익",  # 브리지 대상 — "왜 움직였나" 분해 표 경로까지 렌더
            issue_type=IssueType.EARNINGS_TAX,
            materiality_score=1.0,
            anomaly_score=1.0,
            confidence="High",
            risk_level="High",
            claims=[Claim(perspective="numeric", description="급감", cited_value="0.4조")],
            numeric_evidence=[
                EvidenceRef(
                    source="financial_statement", locator="영업이익", year="2024", value="40"
                )
            ],
        )
        rows = [
            {"series_key": f"CFS:{n}", "year": y, "amount": a}
            for n, ys in {
                "영업이익": {2023: 1.0e12, 2024: 0.4e12},
                "매출총이익": {2023: 3.0e12, 2024: 2.6e12},
                "판매비와관리비": {2023: 2.0e12, 2024: 2.2e12},
                "매출": {2023: 10.0e12, 2024: 9.3e12},
                "매출원가": {2023: 7.0e12, 2024: 6.7e12},
            }.items()
            for y, a in ys.items()
        ]
        render_suspicion_card(card, rows, 2024)

    at = AppTest.from_function(_app)
    at.run()
    assert not at.exception  # st 인자 오류·렌더 크래시 없음
    body = " ".join(m.value for m in at.markdown)
    # 3섹션 헤더 통일(①주장 ②결과 분해 ③시각자료)
    assert "① 무엇이 의심스러운가" in body
    assert "② 결과 분해" in body
    assert "③ 시각자료" in body
    assert "왜 움직였나" in body  # 분해 표 섹션 렌더 확인
    # 타이틀에 부모 값 병기(얼마→얼마·변화율)
    assert "1.0조(2023)" in body and "4,000억(2024)" in body and "-60.0%" in body
    # 재귀 펼침 행('└ 매출')·부모 전체 행이 분해 표 dataframe에 존재
    decomp_tables = [df.value for df in at.dataframe if "구성" in list(df.value.columns)]
    assert decomp_tables
    rows = set(decomp_tables[0]["구성"])
    assert "└ 매출" in rows
    assert "영업이익 (전체)" in rows  # 부모 본체 행(얼마→얼마) 최상단 표기
    # 기여율 칼럼에 증감 방향 표기(▼=끌어내림, ▲=방어) — 표만 훑어도 방향 즉독
    pct = [str(v) for v in decomp_tables[0]["기여율"]]
    assert any(v.startswith("▼") for v in pct)
    assert any(v.startswith("▲") for v in pct)


# ── 차트 데이터 helpers — waterfall_leaves·index_points·yoy_labels ─────────
def test_waterfall_leaves_flattens_children_and_sums_to_delta():
    from dashboard.card_data import waterfall_leaves
    from src.report.decomposition import decompose_change, load_bridges

    rows = [
        {"series_key": f"CFS:{n}", "year": y, "amount": a}
        for n, ys in {
            "영업이익": {2023: 100.0, 2024: 40.0},
            "매출총이익": {2023: 300.0, 2024: 260.0},
            "판매비와관리비": {2023: 200.0, 2024: 220.0},
            "매출": {2023: 1000.0, 2024: 930.0},
            "매출원가": {2023: 700.0, 2024: 670.0},
        }.items()
        for y, a in ys.items()
    ]
    out = decompose_change(rows, "CFS:영업이익", 2024, load_bridges())
    leaves = waterfall_leaves(out)
    names = [n for n, _ in leaves]
    assert "매출총이익" not in names  # 소계는 children로 대체(이중계상 방지)
    assert set(names) == {"매출", "매출원가", "판매비와관리비"}
    assert sum(d for _, d in leaves) == pytest.approx(out["delta"], abs=1.0)  # 워터폴 항등


def test_contribution_figure_diverging_bars_by_polarity():
    from dashboard.card_view import WF_DOWN, WF_UP, contribution_figure

    out = {
        "parent": "CFS:영업이익",
        "prior_year": 2024,
        "year": 2025,
        "parent_prior": 4590.0,
        "parent_current": 1707.0,
        "delta": -2883.0,
        "residual": 0.0,
        "rows": [
            {"account": "매출총이익", "delta": -4162.0},
            {"account": "판매비와관리비", "delta": 1279.0},
        ],
    }
    fig = contribution_figure(out)
    bar = fig.data[0]
    assert bar.orientation == "h"
    # 음(하락)=빨강, 양(방어)=초록 극성 매핑
    color_by_name = dict(zip(bar.y, bar.marker.color))
    assert color_by_name["매출총이익"] == WF_DOWN  # 하락 요인 빨강
    assert color_by_name["판매비와관리비"] == WF_UP  # 방어 요인 초록
    # 기여Δ가 x값(원단위)
    assert set(bar.x) == {-4162.0, 1279.0}
    # 토네이도 정렬 — 최대 크기(매출총이익 |−4162|)가 plotly 맨 위(=y 리스트 마지막)
    assert bar.y[-1] == "매출총이익"


def test_waterfall_leaves_keeps_residual_leaf():
    from dashboard.card_data import waterfall_leaves

    out = {
        "rows": [{"account": "매출총이익", "delta": -40.0}],
        "residual": -20.0,
        "delta": -60.0,
    }
    leaves = waterfall_leaves(out)
    assert ("미설명 잔차", -20.0) in leaves  # 잔차 숨김 금지


def test_index_points_first_is_100():
    from dashboard.card_data import index_points

    pts = index_points([{"year": 2020, "amount": 50.0}, {"year": 2021, "amount": 60.0}])
    assert pts[0]["amount"] == pytest.approx(100.0, abs=0.01)
    assert pts[1]["amount"] == pytest.approx(120.0, abs=0.01)
    assert index_points([]) == []
    assert index_points([{"year": 2020, "amount": 0.0}]) == []  # 기준 0 — 지수화 불가


def test_contribution_cell_style_direction_and_intensity():
    from dashboard.card_data import contribution_cell_style

    strong_down = contribution_cell_style(-144.3)
    weak_up = contribution_cell_style(44.3)
    assert "227,73,72" in strong_down  # 음수=빨강
    assert "27,175,122" in weak_up  # 양수=초록
    # 강도: |기여율| 클수록 alpha 큼(-144.3 > +44.3), 상한 0.5 캡
    a_strong = float(strong_down.split(",")[-1].rstrip(")"))
    a_weak = float(weak_up.split(",")[-1].rstrip(")"))
    assert a_strong > a_weak
    assert a_strong <= 0.5
    assert float(contribution_cell_style(-9999).split(",")[-1].rstrip(")")) == 0.5  # 캡


def test_contribution_cell_style_blank_for_none_and_zero():
    from dashboard.card_data import contribution_cell_style

    assert contribution_cell_style(None) == ""  # 잔차·전체 행 무색
    assert contribution_cell_style(0) == ""


# ── card_headline / sort_cards (단추 라벨·정렬) ────────────────────────────
def test_card_headline_prefers_divergence_clause():
    from dashboard.card_data import card_headline

    rows = [
        {"series_key": "CFS:매출", "year": 2024, "amount": 1000.0},
        {"series_key": "CFS:매출", "year": 2025, "amount": 933.0},
    ]
    out = {
        "parent": "CFS:영업이익",
        "prior_year": 2024,
        "year": 2025,
        "change_pct": -62.8,
        "delta": -60.0,
        "residual": 0.0,
        "rows": [{"account": "매출총이익", "delta": -80.0}],
    }
    headline = card_headline(_card(), out, rows)
    assert "매출은 -6.7%인데 영업이익은 -62.8%" in headline
    assert "주도" not in headline  # 라벨은 첫 절만(짧게)


def test_card_headline_falls_back_to_claim_then_subtype():
    from dashboard.card_data import card_headline
    from src.schemas.findings import Claim

    with_claim = _card(claims=[Claim(perspective="numeric", description="급증 의심. 상세는 뒤")])
    assert card_headline(with_claim, None, []) == "급증 의심"
    with_subtype = _card(subtype="손상 확대")
    assert card_headline(with_subtype, None, []) == "손상 확대"


def test_sort_cards_priority_desc():
    from dashboard.card_data import sort_cards

    a = {"priority_score": 0.2, "materiality_score": 0.9}
    b = {"priority_score": 0.8, "materiality_score": 0.1}
    assert sort_cards([a, b])[0] is b


def test_render_cards_section_expander_apptest():
    from streamlit.testing.v1 import AppTest

    def _app():
        from dashboard.card_view import render_cards_section
        from src.schemas.findings import AccountFinding, IssueType

        cards = [
            AccountFinding(
                account="CFS:영업이익",
                issue_type=IssueType.EARNINGS_TAX,
                subtype="영업이익 급감",
                materiality_score=1.0,
                anomaly_score=1.0,
                confidence="High",
                risk_level="High",
            )
        ]
        render_cards_section("계정별 의심 후보", cards, [], 2025)

    at = AppTest.from_function(_app)
    at.run()
    assert not at.exception  # expander 중첩 등 렌더 크래시 없음
    assert len(at.expander) == 1  # 카드 1장 = 단추 1개


def test_yoy_labels_first_blank_rest_filled():
    from dashboard.card_data import yoy_labels

    pts = [{"year": y, "amount": a} for y, a in [(2022, 100.0), (2023, 120.0), (2024, 60.0)]]
    labels = yoy_labels(pts)
    assert labels == ["", "+20%", "-50%"]  # 첫해 빈칸 + n-1개 채움


# ── conclusion_view (조사 결론 → 표시 재료) ────────────────────────────────
def test_conclusion_view_humanizes_and_maps():
    from dashboard.card_data import conclusion_view

    card = {
        "investigation": {
            "headline": "매출 1,289,630,423,605 감소가 주도",
            "cause_path": ["영업이익 -62.8%", "매출총이익 기여 -84%"],
            "anomaly_points": [],
            "open_questions": ["부문별 단가 정보 없음"],
            "resolved": False,
            "method": "tool_loop",
            "tool_requests": 5,
        }
    }
    view = conclusion_view(card)
    assert "1.3조" in view["headline"]  # 12자리 원숫자 축약
    assert view["resolved"] is False and view["method"] == "tool_loop"


def test_conclusion_view_none_when_missing():
    from dashboard.card_data import conclusion_view

    assert conclusion_view({}) is None


# ── card_builder claims 전파 (클러스터 items N건 → claims N건) ─────────────
def test_build_cards_fills_claims_one_per_item():
    from src.report.card_builder import build_cards
    from src.report.grounding import GroundedSuspicion
    from src.schemas.suspicion import SuspicionItem

    items = [
        SuspicionItem(
            perspective=p,
            scope="account",
            issue_type=IssueType.ASSET_VALUATION,
            account_id="CFS:무형자산",
            sj_div="BS",
            year="2024",
            cited_value="1964277226876",
            description=f"{p} 관점 의심 사유",
        )
        for p in ("numeric", "trend")
    ]
    grounded = [
        GroundedSuspicion(item=i, grounded=True, value_verified=True, reason="ok") for i in items
    ]
    cards = build_cards(grounded, {"target_year": 2024, "account_level_series": SERIES_ROWS})
    [card] = cards["account_cards"]
    assert len(card.claims) == 2  # items 2건 → claims 2건(누락 금지)
    assert {c.perspective for c in card.claims} == {"numeric", "trend"}
    assert all(c.description.endswith("의심 사유") for c in card.claims)


# --- 넓은 주제 그룹핑(group_cards) — 사용자 결정 2026-07-11: 점수 정렬 대신 주제 묶음 1차 ---

_GROUP_CFG = {
    "order": ["손익·수익성", "재무상태", "현금흐름", "우발·특수관계", "기타"],
    "by_issue_type": {
        "earnings_tax": "손익·수익성",
        "asset_valuation": "재무상태",
        "cash_flow": "현금흐름",
    },
}


def test_group_cards_order_and_vote_sort():
    from dashboard.card_data import group_cards

    cards = [
        {"issue_type": "cash_flow", "vote_count": 1, "priority_score": 0.5},
        {"issue_type": "earnings_tax", "vote_count": 1, "priority_score": 0.9},
        {"issue_type": "earnings_tax", "vote_count": 2, "priority_score": 0.1},
        {"issue_type": "asset_valuation", "vote_count": 1, "priority_score": 0.4},
    ]
    groups = group_cards(cards, _GROUP_CFG)
    assert [label for label, _ in groups] == ["손익·수익성", "재무상태", "현금흐름"]  # 빈 그룹 생략
    incomes = groups[0][1]
    assert incomes[0]["vote_count"] == 2  # 그룹 안은 표수 우선(점수보다)
    assert incomes[1]["priority_score"] == 0.9


def test_group_cards_unknown_issue_falls_back_to_last_group():
    from dashboard.card_data import group_cards

    groups = group_cards([{"issue_type": "낯선유형", "vote_count": 0}], _GROUP_CFG)
    assert groups == [("기타", [{"issue_type": "낯선유형", "vote_count": 0}])]


def test_group_cards_real_config_covers_all_issue_types():
    from dashboard.card_data import group_cards, load_card_groups
    from src.schemas.findings import IssueType

    cfg = load_card_groups()
    mapping = cfg["by_issue_type"]
    missing = [t.value for t in IssueType if t.value not in mapping]
    assert missing == []  # enum 10종 전부 매핑(누락 시 이 목록에 나옴)
    cards = [{"issue_type": t.value, "vote_count": 0} for t in IssueType]
    grouped_total = sum(len(g) for _, g in group_cards(cards, cfg))
    assert grouped_total == len(cards)  # 드롭 0


# --- 카드 단추 라벨 슬림화 — 첫 문장 축약 + 관점 이름 배지(사용자 피드백 2026-07-11) ---


def test_short_headline_takes_first_sentence_and_truncates():
    from dashboard.card_data import short_headline

    three = "당기순이익의 적자 전환은 세전이익 악화에서 설명된다. 핵심은 영업이익 감소다. 잔차는 0이다."
    assert short_headline(three) == "당기순이익의 적자 전환은 세전이익 악화에서 설명된다"
    long_one = "가" * 80
    out = short_headline(long_one)
    assert out.endswith("…") and len(out) == 61  # 60자 + 말줄임
    assert short_headline("") == ""


def test_perspective_badge_names_dedup_and_internal_only():
    from dashboard.card_data import perspective_badge

    card = {
        "claims": [
            {"perspective": "numeric", "description": "a"},
            {"perspective": "trend", "description": "b"},
            {"perspective": "numeric", "description": "c"},  # 중복 → 1회
            {"perspective": "external", "description": "d"},  # 비내부 → 제외
        ]
    }
    assert perspective_badge(card) == "수치·추세 의심"
    assert perspective_badge({"claims": []}) == ""
