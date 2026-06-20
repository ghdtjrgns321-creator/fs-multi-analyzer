"""XBRL→finstate_all 컨버터 차원 해석 테스트 (T1: SCE member 코드→한글 라벨 회귀).

원본 교체 컨버터가 account_detail에 XBRL member 코드("ComponentsOfEquityAxis=RetainedEarnings
Member")를 기록해 SCE 분류기(한글 alias)가 전부 unmatched가 된 회귀를 막는다. member→한글
라벨 변환과 SCE 표 총계행(CSA 마커) 보존을 검증한다.
"""

from __future__ import annotations

from data.backtest._xbrl_to_finstate_csv import _member_ko, resolve_sce_dimensions


class _FakeDV:
    """Arelle 차원값 stub — isExplicit/memberQname/member.label만 흉내."""

    def __init__(self, local_name: str, ko: str | None, explicit: bool = True) -> None:
        self.isExplicit = explicit
        self._local = local_name
        self._ko = ko

        class _QName:
            localName = local_name

        class _Member:
            def label(self_inner, lang: str = "ko") -> str:  # noqa: N805
                if ko is None:
                    raise RuntimeError("no label")
                return ko

        self.memberQname = _QName()
        self.member = _Member()

    def __str__(self) -> str:
        return self._local


def test_member_ko_resolves_korean_label() -> None:
    ln, ko = _member_ko(_FakeDV("RetainedEarningsMember", "이익잉여금 [member]"))
    assert ln == "RetainedEarningsMember"
    assert ko == "이익잉여금 [member]"


def test_member_ko_preserves_code_when_no_korean_label() -> None:
    # 한글 라벨 해석 실패 시 코드 보존(소실 금지) — udf 커스텀 member 안전망.
    ln, ko = _member_ko(_FakeDV("udf_CE_X_SomethingMember", None))
    assert ln == "udf_CE_X_SomethingMember"
    assert ko == "udf_CE_X_SomethingMember"


def test_resolve_sce_marker_row_uses_csa_korean_label() -> None:
    # CSA 축만(구성요소 없음) = SCE 표 총계행 → 한글 마커("연결재무제표 [member]").
    members = [
        (
            "ConsolidatedAndSeparateFinancialStatementsAxis",
            "ConsolidatedMember",
            "연결재무제표 [member]",
        ),
    ]
    fs, component_detail, csa_marker = resolve_sce_dimensions(members)
    assert fs == "CFS"
    assert component_detail == ""  # 본문 라우팅용(비면 무차원/마커)
    assert csa_marker == "연결재무제표 [member]"


def test_resolve_sce_separate_marker_is_ofs() -> None:
    members = [
        (
            "ConsolidatedAndSeparateFinancialStatementsAxis",
            "SeparateMember",
            "별도재무제표 [member]",
        ),
    ]
    fs, component_detail, csa_marker = resolve_sce_dimensions(members)
    assert fs == "OFS"
    assert csa_marker == "별도재무제표 [member]"


def test_resolve_sce_component_detail_is_korean_leaf() -> None:
    # CSA + 구성요소축 → component_detail에 한글 leaf(분류기 alias 매칭 대상).
    members = [
        (
            "ConsolidatedAndSeparateFinancialStatementsAxis",
            "ConsolidatedMember",
            "연결재무제표 [member]",
        ),
        ("ComponentsOfEquityAxis", "RetainedEarningsMember", "이익잉여금 [member]"),
    ]
    fs, component_detail, csa_marker = resolve_sce_dimensions(members)
    assert fs == "CFS"
    # leaf(마지막 |세그먼트)가 한글 구성요소 — 분류기가 이익잉여금으로 인식
    assert component_detail.split("|")[-1] == "이익잉여금 [member]"


def test_resolve_no_dimension_is_body_row() -> None:
    # 무차원 fact(본문 BS/IS/CF 잔액/손익) → component_detail 빈값·마커 없음.
    fs, component_detail, csa_marker = resolve_sce_dimensions([])
    assert fs == "CFS"
    assert component_detail == ""
    assert csa_marker is None
