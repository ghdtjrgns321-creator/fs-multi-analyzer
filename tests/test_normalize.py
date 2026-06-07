from pathlib import Path

import pandas as pd

from src.normalize.config import load_canonical_accounts
from src.normalize.mapper import ALIAS, EXACT, OTHER_CANONICAL, UNMAPPED, AccountMapper
from src.normalize.pipeline import normalize_raw_file
from src.normalize.schema import parse_amount


def test_parse_amount_handles_commas_negative_and_missing() -> None:
    assert parse_amount("1,200") == 1200.0
    assert parse_amount("-300") == -300.0
    assert parse_amount("") is None
    assert parse_amount(None) is None


def test_mapper_prefers_account_id_over_alias() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    row = pd.Series({"account_id": "ifrs-full_Revenue", "account_nm": "매출채권"})

    result = mapper.map_row(row)

    assert result.canonical == "매출"
    assert result.mapping_status == EXACT


def test_new_canonical_accounts_map_standard_ids() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    cases = [
        ("ifrs-full_NoncurrentPortionOfNoncurrentBondsIssued", "사채"),
        ("ifrs-full_OtherShorttermProvisions", "충당부채"),
        ("ifrs-full_PropertyPlantAndEquipment", "유형자산"),
        ("ifrs-full_GrossProfit", "매출총이익"),
        ("ifrs-full_CashFlowsFromUsedInInvestingActivities", "투자활동현금흐름"),
        ("ifrs-full_DividendsPaidClassifiedAsFinancingActivities", "배당금지급"),
        ("ifrs-full_NoncontrollingInterests", "비지배지분"),
        ("ifrs-full_ProfitLossAttributableToOwnersOfParent", "지배기업귀속순이익"),
        ("ifrs-full_InvestmentsInAssociates", "관계기업투자"),
        ("ifrs-full_ComprehensiveIncome", "총포괄손익"),
        ("ifrs-full_OtherComprehensiveIncome", "기타포괄손익"),
        (
            "ifrs-full_OtherComprehensiveIncomeNetOfTaxGainsLossesFromInvestmentsInEquityInstruments",
            "FVOCI평가손익",
        ),
        (
            "ifrs-full_GainsLossesOnExchangeDifferencesOnTranslationNetOfTax",
            "해외사업환산손익",
        ),
        ("ifrs-full_GainsLossesOnCashFlowHedgesNetOfTax", "현금흐름위험회피손익"),
        (
            "ifrs-full_OtherComprehensiveIncomeNetOfTaxGainsLossesOnRemeasurementsOfDefinedBenefitPlans",
            "확정급여재측정손익",
        ),
        ("dart_EquityAtBeginningOfPeriod", "기초자본"),
        ("ifrs-full_DividendsPaid", "배당변동"),
        ("dart_TreasuryShareTransactions", "자기주식변동"),
        ("ifrs-full_RightofuseAssets", "사용권자산"),
        ("ifrs-full_CurrentLeaseLiabilities", "유동리스부채"),
        ("ifrs-full_NoncurrentLeaseLiabilities", "비유동리스부채"),
        ("ifrs-full_InvestmentProperty", "투자부동산"),
        ("ifrs-full_CurrentPortionOfLongtermBorrowings", "유동성장기차입금"),
        ("dart_PostemploymentBenefitObligations", "순확정급여부채"),
        (
            "ifrs-full_CurrentFinancialAssetsMeasuredAtFairValueThroughProfitOrLoss",
            "유동FVPL금융자산",
        ),
        (
            "ifrs-full_NoncurrentFinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome",
            "비유동FVOCI금융자산",
        ),
        (
            "ifrs-full_CurrentFinancialAssetsMeasuredAtAmortisedCost",
            "유동상각후원가금융자산",
        ),
    ]

    for account_id, expected in cases:
        result = mapper.map_row(pd.Series({"account_id": account_id, "account_nm": "unused"}))
        assert result.canonical == expected
        assert result.mapping_status == EXACT


def test_s4_core_unmapped_labels_map_without_overmerging() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    cases = [
        ("사용권자산", "사용권자산"),
        ("투자부동산", "투자부동산"),
        ("관계기업및공동기업 투자", "관계기업투자"),
        ("종속기업, 관계기업 및 공동기업투자", "관계기업투자"),
        ("관계기업및공동기업투자주식", "관계기업투자"),
        ("리스부채", "리스부채"),
        ("유동리스부채", "유동리스부채"),
        ("비유동리스부채", "비유동리스부채"),
        ("유동성장기부채", "유동성장기차입금"),
        ("유동성 장기차입금", "유동성장기차입금"),
        ("당기손익-공정가치 측정 금융자산", "FVPL금융자산"),
        ("기타포괄손익-공정가치 측정 금융자산", "FVOCI금융자산"),
        ("상각후원가측정금융자산", "상각후원가금융자산"),
        ("순확정급여부채", "순확정급여부채"),
        ("확정급여부채", "확정급여부채"),
    ]

    for label, expected in cases:
        result = mapper.map_row(pd.Series({"account_id": "", "account_nm": label}))
        assert result.canonical == expected
        assert result.mapping_status == ALIAS


def test_s4_core_labels_do_not_overmerge_trade_accounts() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    for label in ["리스채권", "기타수취채권", "장기매출채권 및 기타비유동채권"]:
        result = mapper.map_row(pd.Series({"account_id": "", "account_nm": label}))
        assert result.canonical not in {"매출채권", "매입채무", "리스부채"}


def test_subsidiary_investment_separated_from_associate() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    # 종속기업투자(단독)는 종속기업투자 canonical로 — account_id·alias 모두
    result = mapper.map_row(
        pd.Series(
            {"account_id": "ifrs-full_InvestmentsInSubsidiaries", "account_nm": "종속기업투자"}
        )
    )
    assert result.canonical == "종속기업투자"
    assert result.mapping_status == EXACT
    for label in [
        "종속기업투자",
        "종속기업투자주식",
        "종속기업에 대한 투자자산",
        "종속기업투자자산",
        "종속기업지분투자",
        "종속기업에 대한 투자",
    ]:
        result = mapper.map_row(pd.Series({"account_id": "", "account_nm": label}))
        assert result.canonical == "종속기업투자"
        assert result.mapping_status == ALIAS

    # 관계기업투자(단독)는 관계기업투자로 — 종속과 안 섞임
    for account_id in [
        "ifrs-full_InvestmentsInAssociates",
        "ifrs-full_InvestmentAccountedForUsingEquityMethod",
    ]:
        result = mapper.map_row(pd.Series({"account_id": account_id, "account_nm": "관계기업투자"}))
        assert result.canonical == "관계기업투자"

    # 종속+관계 통합값은 분리 불가 → 관계기업투자(대표)에 유지
    for label in ["종속기업및관계기업투자주식", "종속기업, 관계기업 및 공동기업투자"]:
        result = mapper.map_row(pd.Series({"account_id": "", "account_nm": label}))
        assert result.canonical == "관계기업투자"
    result = mapper.map_row(
        pd.Series(
            {
                "account_id": "ifrs-full_InvestmentsInSubsidiariesJointVenturesAndAssociates",
                "account_nm": "x",
            }
        )
    )
    assert result.canonical == "관계기업투자"


def test_current_noncurrent_split_account_ids() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    cases = [
        # 비유동이 유동 칸에 흡수되던 것 → 별도 canonical로 분리
        ("ifrs-full_NoncurrentTradeReceivables", "비유동매출채권"),
        ("dart_LongTermTradeReceivablesGross", "비유동매출채권"),
        ("ifrs-full_NoncurrentPayablesToTradeSuppliers", "비유동매입채무"),
        ("ifrs-full_NoncurrentContractAssets", "비유동계약자산"),
        ("dart_LongTermDueFromCustomersForContractWork", "비유동계약자산"),
        ("ifrs-full_NoncurrentContractLiabilities", "비유동계약부채"),
        ("dart_CurrentPortionOfBonds", "유동성사채"),
        ("ifrs-full_NoncurrentProvisions", "장기충당부채"),
        ("ifrs_NoncurrentProvisions", "장기충당부채"),
        ("dart_NonCurrentProvisionsForProductWarranties", "장기충당부채"),
        ("dart_CurrentProvisionForConstructionLosses", "공사손실충당부채"),
        # 유동분은 유동 canonical 유지(과병합 방지)
        ("ifrs-full_CurrentContractAssets", "계약자산"),
        ("ifrs-full_CurrentContractLiabilities", "계약부채"),
        ("dart_BondsIssued", "사채"),
        ("ifrs-full_CurrentProvisions", "충당부채"),
    ]
    for account_id, expected in cases:
        result = mapper.map_row(pd.Series({"account_id": account_id, "account_nm": "x"}))
        assert result.canonical == expected, f"{account_id} -> {result.canonical} != {expected}"
        assert result.mapping_status == EXACT


def test_statement_guard_demotes_cross_statement_keeps_is_cis() -> None:
    from src.normalize.pipeline import _apply_statement_guard

    frame = pd.DataFrame(
        [
            # BS 잔액 — 유지
            {
                "canonical": "재고자산",
                "canonical_statement": "BS",
                "sj_div": "BS",
                "mapping_status": EXACT,
            },
            # CF 증감조정이 BS 잔액 칸으로 흡수된 행 — 강등돼야
            {
                "canonical": "재고자산",
                "canonical_statement": "BS",
                "sj_div": "CF",
                "mapping_status": ALIAS,
            },
            # IS 계정이 포괄손익(CIS)으로 통합신고 — 호환, 유지
            {
                "canonical": "이자비용",
                "canonical_statement": "IS",
                "sj_div": "CIS",
                "mapping_status": EXACT,
            },
            # CIS 계정이 자본변동(SCE) 칸으로 흡수 — 강등돼야
            {
                "canonical": "총포괄손익",
                "canonical_statement": "CIS",
                "sj_div": "SCE",
                "mapping_status": EXACT,
            },
            # 이미 기타계정 — 그대로
            {
                "canonical": OTHER_CANONICAL,
                "canonical_statement": "",
                "sj_div": "CF",
                "mapping_status": UNMAPPED,
            },
        ]
    )
    out = _apply_statement_guard(frame)
    verdict = list(zip(out["canonical"], out["sj_div"], out["mapping_status"], strict=True))
    assert verdict[0] == ("재고자산", "BS", EXACT)  # 잔액 보존
    assert verdict[1] == (OTHER_CANONICAL, "CF", UNMAPPED)  # CF→BS 흡수 차단
    assert verdict[2] == ("이자비용", "CIS", EXACT)  # IS↔CIS 호환 보존
    assert verdict[3] == (OTHER_CANONICAL, "SCE", UNMAPPED)  # CIS→SCE 흡수 차단
    assert verdict[4] == (OTHER_CANONICAL, "CF", UNMAPPED)  # 기존 기타계정 불변


def test_normalize_raw_file_statuses(tmp_path: Path) -> None:
    raw = pd.DataFrame(
        [
            {
                "corp_code": "00126380",
                "bsns_year": "2024",
                "sj_div": "BS",
                "account_id": "ifrs-full_CashAndCashEquivalents",
                "account_nm": "현금및현금성자산",
                "thstrm_amount": "1,000",
            },
            {
                "corp_code": "00126380",
                "bsns_year": "2024",
                "sj_div": "BS",
                "account_id": "-표준계정코드 미사용-",
                "account_nm": "단기차입금",
                "thstrm_amount": "-200",
            },
            {
                "corp_code": "00126380",
                "bsns_year": "2024",
                "sj_div": "BS",
                "account_id": "-표준계정코드 미사용-",
                "account_nm": "미매핑",
                "thstrm_amount": "",
            },
        ]
    )
    path = tmp_path / "raw.csv"
    raw.to_csv(path, index=False)
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    frame = normalize_raw_file(path, "CFS", mapper)

    assert frame["fs_div"].tolist() == ["CFS", "CFS", "CFS"]
    assert frame["mapping_status"].tolist() == [EXACT, ALIAS, UNMAPPED]
    assert frame["amount"].tolist()[:2] == [1000.0, -200.0]


def test_normalize_raw_file_preserves_prior_period_amounts(tmp_path: Path) -> None:
    raw = pd.DataFrame(
        [
            {
                "corp_code": "00126380",
                "bsns_year": "2024",
                "sj_div": "BS",
                "account_id": "ifrs-full_CashAndCashEquivalents",
                "account_nm": "현금및현금성자산",
                "thstrm_amount": "1,000",
                "frmtrm_amount": "900",
                "bfefrmtrm_amount": "800",
            },
            {
                "corp_code": "00126380",
                "bsns_year": "2024",
                "sj_div": "BS",
                "account_id": "-표준계정코드 미사용-",
                "account_nm": "단기차입금",
                "thstrm_amount": "-200",
                "frmtrm_amount": "-300",
                "bfefrmtrm_amount": "",
            },
        ]
    )
    path = tmp_path / "raw.csv"
    raw.to_csv(path, index=False)
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    frame = normalize_raw_file(path, "CFS", mapper)

    assert frame.columns.tolist() == [
        "corp_code",
        "year",
        "fs_div",
        "sj_div",
        "canonical",
        "account_id",
        "label",
        "amount",
        "prior_amount",
        "prior2_amount",
        "mapping_status",
    ]
    assert frame["amount"].tolist() == [1000.0, -200.0]
    assert frame["prior_amount"].tolist() == [900.0, -300.0]
    assert frame.iloc[0]["prior2_amount"] == 800.0
    assert pd.isna(frame.iloc[1]["prior2_amount"])
