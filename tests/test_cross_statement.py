"""다중표 id 매핑(cross_statement) 테스트 — 강등 행 구제·기존 매핑 불변·SCE 무영향."""

from __future__ import annotations

import pandas as pd

from src.normalize.config import CanonicalAccount
from src.normalize.mapper import CROSS_STATEMENT, OTHER_CANONICAL, AccountMapper
from src.normalize.pipeline import _rescue_cross_statement

# OCI 개념: SCE에 등록(자본변동) + CIS canonical이 cross로 같은 회사신고 id를 주장.
_SCE = CanonicalAccount(
    name="해외사업환산손익(SCE)",
    statement="SCE",
    account_ids=("ifrs-full_OtherComprehensiveIncomeNetOfTaxExchangeDifferencesOnTranslation",),
    aliases=(),
)
_CIS = CanonicalAccount(
    name="해외사업환산손익",
    statement="CIS",
    account_ids=("ifrs-full_GainsLossesOnExchangeDifferencesOnTranslationNetOfTax",),
    aliases=("해외사업환산손익",),
    cross_statement_ids=(
        "ifrs-full_OtherComprehensiveIncomeNetOfTaxExchangeDifferencesOnTranslation",
    ),
)
_OCI_ID = "ifrs-full_OtherComprehensiveIncomeNetOfTaxExchangeDifferencesOnTranslation"


def test_cross_statement_match_compatible_and_incompatible() -> None:
    mapper = AccountMapper([_SCE, _CIS])
    # CIS 행 → cross로 CIS canonical 구제
    hit = mapper.cross_statement_match(_OCI_ID, "CIS")
    assert hit is not None and hit.canonical == "해외사업환산손익"
    assert hit.mapping_status == CROSS_STATEMENT
    # BS 행 → 호환 statement 없음 → None
    assert mapper.cross_statement_match(_OCI_ID, "BS") is None
    # 미등록 id → None
    assert mapper.cross_statement_match("ifrs-full_Unknown", "CIS") is None


def test_rescue_only_remaps_demoted_rows_keeps_existing() -> None:
    mapper = AccountMapper([_SCE, _CIS])
    frame = pd.DataFrame(
        [
            {  # 강등된 OCI 행(CIS) — 구제 대상
                "account_id": _OCI_ID,
                "sj_div": "CIS",
                "canonical": OTHER_CANONICAL,
                "canonical_statement": "",
                "mapping_status": "unmapped_extension_account",
            },
            {  # 이미 매핑된 행 — 절대 불변
                "account_id": "ifrs-full_Revenue",
                "sj_div": "IS",
                "canonical": "매출액",
                "canonical_statement": "IS",
                "mapping_status": "exact_taxonomy_match",
            },
            {  # SCE 행(같은 id, 강등 아님=매핑됨) — 구제 비대상(기타 아님)
                "account_id": _OCI_ID,
                "sj_div": "SCE",
                "canonical": "해외사업환산손익(SCE)",
                "canonical_statement": "SCE",
                "mapping_status": "exact_taxonomy_match",
            },
        ]
    )
    out = _rescue_cross_statement(frame.copy(), mapper)
    # 강등 OCI → CIS canonical로 구제
    assert out.iloc[0]["canonical"] == "해외사업환산손익"
    assert out.iloc[0]["mapping_status"] == CROSS_STATEMENT
    # 기존 매핑 2건 불변
    assert out.iloc[1]["canonical"] == "매출액"
    assert out.iloc[2]["canonical"] == "해외사업환산손익(SCE)"


def test_account_without_cross_ids_unaffected() -> None:
    # cross_statement_ids 없는 일반 canonical만 있으면 _by_cross 비고, 구제 없음(무해)
    plain = CanonicalAccount(
        name="매출액", statement="IS", account_ids=("ifrs-full_Revenue",), aliases=()
    )
    mapper = AccountMapper([plain])
    assert mapper.cross_statement_match("ifrs-full_Revenue", "CF") is None
