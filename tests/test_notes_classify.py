"""주석 분류기(notes_classify) 테스트 — 3분류·우선순위·detail 카테고리."""

from __future__ import annotations

import pandas as pd

from src.normalize.notes_classify import (
    NoteTaxonomy,
    classify_concept,
    classify_note_facts,
    is_dimensioned,
    load_note_taxonomy,
    select_for_load,
)


def _taxonomy() -> NoteTaxonomy:
    return load_note_taxonomy()


def test_meta_concept_is_filtered():
    tax = _taxonomy()
    assert classify_concept("ConsolidatedAuditOpinion", tax) == ("메타", None)
    assert classify_concept("EntityAddress", tax) == ("메타", None)


def test_statement_concept_is_absorbed_by_canonical():
    # Assets는 본문 canonical(ifrs-full_Assets) → 흡수
    tax = _taxonomy()
    bucket, category = classify_concept("Assets", tax)
    assert bucket == "흡수"
    assert category is None


def test_detail_concept_maps_to_category():
    tax = _taxonomy()
    assert classify_concept("BorrowingsInterestRate", tax) == ("detail", "차입금조건")
    assert classify_concept("BorrowingsMaturity", tax) == ("detail", "차입금조건")


def test_priority_related_party_beats_receivable():
    # AmountsReceivableRelatedPartyTransactions: 채권 토큰보다 특수관계자가 먼저(우선순위)
    tax = _taxonomy()
    _, category = classify_concept("AmountsReceivableRelatedPartyTransactions", tax)
    assert category == "특수관계자거래"


def test_category_priority_deferred_tax_before_income_tax():
    # detail 카테고리 우선순위: 이연법인세가 법인세보다 먼저(다중매칭 시 승) — config 순서로 보장.
    tax = _taxonomy()
    names = [name for name, _ in tax.categories]
    assert names.index("이연법인세") < names.index("법인세")


def test_main_statement_concept_absorbed_after_full_registration():
    # 표준ID 전수등록 후, 본문에도 있는 개념(이연법인세·대손상각비)의 주석 총액은 본문중복 → 흡수.
    # 주석 고유 개념(차입조건·특수관계자)은 여전히 detail.
    tax = _taxonomy()
    assert classify_concept("DeferredTaxLiabilityAsset", tax)[0] == "흡수"
    assert classify_concept("BorrowingsInterestRate", tax) == ("detail", "차입금조건")


def test_unmatched_detail_falls_to_etc():
    tax = _taxonomy()
    bucket, category = classify_concept("SomeCompanySpecificXyzConcept", tax)
    assert bucket == "기타주석"
    assert category is None


def test_classify_note_facts_frame_shape():
    tax = _taxonomy()
    facts = pd.DataFrame(
        {
            "concept": ["BorrowingsMaturity", "EntityAddress", "Assets"],
            "label_ko": ["차입금, 만기", "회사 주소", "자산총계"],
            "label_en": ["", "", ""],
            "period": ["2024-01-01", "2024-01-01", "2024-12-31"],
            "unit": ["", "", "KRW"],
            "value": ["2025-10-02", "서울", "1000"],
        }
    )
    out = classify_note_facts(facts, tax)
    assert list(out["bucket"]) == ["detail", "메타", "흡수"]
    assert out.loc[0, "category"] == "차입금조건"


def test_high_priority_categories_present():
    tax = _taxonomy()
    assert "차입금조건" in tax.high_priority
    assert "특수관계자거래" in tax.high_priority


def test_is_dimensioned_only_consolidated_axis_is_false():
    # 연결/별도 축만 = 본문 총계 중복 → 무차원 취급
    assert (
        is_dimensioned("ConsolidatedAndSeparateFinancialStatementsAxis=ConsolidatedMember") is False
    )
    assert is_dimensioned("") is False


def test_is_dimensioned_segment_axis_is_true():
    assert (
        is_dimensioned(
            "ConsolidatedAndSeparateFinancialStatementsAxis=ConsolidatedMember|SegmentsAxis=PaintMember"
        )
        is True
    )


def test_select_for_load_keeps_detail_and_dimensioned_absorb_only():
    tax = _taxonomy()
    facts = pd.DataFrame(
        {
            "concept": ["BorrowingsMaturity", "EntityAddress", "Assets", "Assets"],
            "label_ko": ["차입금 만기", "주소", "자산총계", "부문자산"],
            "label_en": ["", "", "", ""],
            "period": ["2024-01-01"] * 4,
            "unit": ["", "", "KRW", "KRW"],
            "value": ["2025-10-02", "서울", "974", "813"],
            "dimensions": [
                "",  # detail → 적재
                "",  # 메타 → 제외
                "ConsolidatedAndSeparateFinancialStatementsAxis=ConsolidatedMember",  # 무차원 흡수 → 제외
                "SegmentsAxis=PaintMember",  # 유차원 흡수 → 적재
            ],
        }
    )
    loaded = select_for_load(classify_note_facts(facts, tax))
    concepts = list(loaded["concept"])
    assert "BorrowingsMaturity" in concepts  # detail
    assert "EntityAddress" not in concepts  # 메타 제외
    assert list(loaded["value"]).count("974") == 0  # 무차원 흡수 제외
    assert "813" in list(loaded["value"])  # 유차원 흡수 포함
    assert len(loaded) == 2
