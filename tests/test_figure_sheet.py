"""반박 서술 수치 도표(figure_sheet) 단위 테스트 — 근본수정 B(예방).

도표=코드가 as-filed series에서 계산한 정확 수치 집합. 감사=서술 숫자가 도표 멤버인지 대조.
발단: 아스트 2020 반박 "전체 자산 583.1억 감소"(실제 298.8억) 환각 — 도표에 583.1 없어 flag돼야 한다.
"""

from __future__ import annotations

from src.report.figure_sheet import (
    audit_narrative_figures,
    build_figure_sheet,
    card_scope_names,
    extract_figures,
)

# 아스트 2020 실측 값(as-filed)
_INV_2020, _INV_2019 = 168_532_992_835.0, 152_615_809_899.0  # 재고 1685.3 / 1526.2
_ASSET_2020, _ASSET_2019 = 520_443_461_969.0, 550_327_734_361.0  # 자산총계 5204.4 / 5503.3


def _series() -> list[dict]:
    def row(year, name, amt, sj="BS"):
        return {
            "year": year,
            "fs_div": "CFS",
            "sj_div": sj,
            "series_key": f"CFS:{name}",
            "canonical": name,
            "label": name,
            "amount": amt,
        }

    return [
        row("2019", "재고자산", _INV_2019),
        row("2020", "재고자산", _INV_2020),
        row("2019", "자산총계", _ASSET_2019),
        row("2020", "자산총계", _ASSET_2020),
    ]


# ---- extract_figures ----


def test_extract_figures_parses_money_and_pct():
    monies, pcts = extract_figures("재고 159.2억 증가(1,685.3억), 6.4조, 300백만원, 10.43% 상승")
    m = {round(x / 1e8, 1) for x in monies}
    assert 159.2 in m and 1685.3 in m
    assert 64000.0 in m  # 6.4조 = 64000억
    assert 3.0 in m  # 300백만원 = 3억
    assert any(abs(p - 10.43) < 0.01 for p in pcts)


def test_extract_figures_bare_number_ignored_without_unit():
    # 단위 없는 맨숫자(연도·개수 등)는 금액으로 오인하지 않는다.
    monies, pcts = extract_figures("2021년 3개 항목")
    assert monies == [] and pcts == []


# ---- build_figure_sheet ----


def test_sheet_includes_grounded_excludes_hallucination():
    sheet = build_figure_sheet({"재고자산", "자산총계"}, _series())
    assert sheet.contains_money(_INV_2020)  # 1685.3 원값
    assert sheet.contains_money(_INV_2020 - _INV_2019)  # 159.2 델타
    assert sheet.contains_money(_ASSET_2019 - _ASSET_2020)  # 298.8 자산총계 델타
    assert not sheet.contains_money(58_310_000_000.0)  # 583.1억 환각 — 도표에 없음
    assert sheet.contains_pct(10.43)  # 재고 증감율


def test_company_card_scope_uses_extra_amounts():
    # company 카드는 앵커계정이 없어도 자체 근거(note 금액)가 도표에 들어간다.
    sheet = build_figure_sheet(set(), _series(), extra_amounts=[75_369_000_000.0])
    assert sheet.contains_money(75_369_000_000.0)  # 753.69억 note 금액
    assert not sheet.contains_money(58_310_000_000.0)  # 583.1 여전히 없음


# ---- audit_narrative_figures ----


def test_audit_flags_ungrounded_number():
    sheet = build_figure_sheet({"재고자산", "자산총계"}, _series())
    flagged = audit_narrative_figures(
        [
            "증가폭은 159.2억원으로 재고잔액 1,685.3억 대비 10.43% 증가",
            "전체 자산은 583.1억원 감소했는데",
        ],
        sheet,
    )
    assert any("583.1" in f for f in flagged)
    assert not any("159.2" in f for f in flagged)  # 도표 내 값은 통과


def test_audit_clean_when_all_grounded():
    sheet = build_figure_sheet({"재고자산", "자산총계"}, _series())
    flagged = audit_narrative_figures(
        ["재고 159.2억 증가, 자산총계 298.8억 감소, 10.43% 상승"], sheet
    )
    assert flagged == []


# ---- card_scope_names ----


def test_card_scope_names_from_cluster_key_and_related():
    card = {
        "cluster_key": "rel:CFS:매출|CFS:매출원가|CFS:재고자산",
        "related_accounts": ["당기순이익"],
    }
    names = card_scope_names(card)
    assert {"매출", "매출원가", "재고자산", "당기순이익"} <= names
    assert "rel" not in names and "CFS" not in names  # 접두·fs_div 토큰 제외
