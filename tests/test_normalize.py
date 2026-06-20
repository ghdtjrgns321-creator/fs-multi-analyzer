from pathlib import Path

import pandas as pd

from src.normalize.config import load_canonical_accounts, load_sce_components
from src.normalize.mapper import (
    ALIAS,
    EXACT,
    ID_LABEL_CONFLICT,
    OTHER_CANONICAL,
    UNMAPPED,
    AccountMapper,
)
from src.normalize.pipeline import normalize_company_year, normalize_raw_file
from src.normalize.sce import extract_sce_components, sce_balance, sce_horizontal_identity
from src.normalize.schema import parse_amount


def test_parse_amount_handles_commas_negative_and_missing() -> None:
    assert parse_amount("1,200") == 1200.0
    assert parse_amount("-300") == -300.0
    assert parse_amount("") is None
    assert parse_amount(None) is None


def test_mapper_prefers_account_id_over_alias() -> None:
    # id(매출)와 label 정확 alias(매출채권)가 다른 모순 — id 우선으로 canonical은 '매출' 유지.
    # N5(라운드1): 매핑은 id-first 그대로, mapping_status에 모순 흔적만 부여(측정·리뷰 노출).
    from src.normalize.mapper import ID_LABEL_CONFLICT

    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    row = pd.Series({"account_id": "ifrs-full_Revenue", "account_nm": "매출채권"})

    result = mapper.map_row(row)

    assert result.canonical == "매출", "id 우선(매핑 무변경)"
    assert result.mapping_status == ID_LABEL_CONFLICT


def test_sce_change_row_id_label_conflict_prefers_label() -> None:
    # T3(SCE 한정): 자본변동표 변동행은 id-label 모순 시 label(한글 공시명) 우선 + 모순 흔적.
    # 세토피아 사례: dart_StockDividends(배당금의 지급(SCE)) 슬롯에 '주식선택권'(주식보상) 신고.
    from src.normalize.mapper import ID_LABEL_CONFLICT

    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    row = pd.Series({"account_id": "dart_StockDividends", "account_nm": "주식선택권"})

    result = mapper.map_change_row(row)

    assert result.canonical == "주식선택권", "label(한글 공시명) 우선"
    assert result.canonical != "배당금의 지급(SCE)", "id로 배당 단정 금지"
    assert result.mapping_status == ID_LABEL_CONFLICT


def test_main_map_row_stays_id_first_flags_conflict() -> None:
    # 본문 매퍼는 모순이어도 id-first 유지(canonical 무변경, 464행 무회귀). N5(라운드1 확정):
    # id≠label 정확 alias면 mapping_status에 id_label_conflict 흔적만 남겨 측정·리뷰 대상 노출.
    from src.normalize.mapper import ID_LABEL_CONFLICT

    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    row = pd.Series({"account_id": "dart_StockDividends", "account_nm": "주식선택권"})

    result = mapper.map_row(row)

    assert result.canonical == "배당금의 지급(SCE)", "본문은 id 우선 유지(매핑 무변경)"
    assert result.mapping_status == ID_LABEL_CONFLICT, "모순 흔적만 부여(매핑 동작 불변)"


def test_main_map_row_no_conflict_when_label_agrees_or_unmapped() -> None:
    # 과잉 발화 방지: label이 미매핑이거나 id와 같은 canonical을 가리키면 EXACT 유지.
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    # label 미매핑 → EXACT
    r1 = mapper.map_row(pd.Series({"account_id": "ifrs-full_Revenue", "account_nm": "zzz미매핑"}))
    assert r1.mapping_status == EXACT
    # id·label 동일 canonical(매출) → EXACT
    r2 = mapper.map_row(pd.Series({"account_id": "ifrs-full_Revenue", "account_nm": "매출액"}))
    assert r2.canonical == "매출"
    assert r2.mapping_status == EXACT


def test_sce_change_row_label_unmapped_keeps_id() -> None:
    # 모순이 아닐 때(label 미매핑)는 SCE 변동행도 id 우선 — 과잉 발화 방지.
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    r = mapper.map_change_row(
        pd.Series({"account_id": "ifrs-full_Revenue", "account_nm": "unused_label"})
    )
    assert r.canonical == "매출"
    assert r.mapping_status == EXACT


def test_ifrs_namespace_variant_maps_like_ifrs_full() -> None:
    # D-B: ifrs_X 와 ifrs-full_X 는 동일 IFRS 개념의 namespace 변형 → 같은 canonical·EXACT.
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    cases = [
        ("ifrs_Inventories", "재고자산"),
        ("ifrs_Revenue", "매출"),
        ("ifrs_ProfitLoss", "당기순이익"),
        ("ifrs_FinanceCosts", "이자비용"),
        ("ifrs_Equity", "자본총계"),
    ]
    for account_id, expected in cases:
        result = mapper.map_row(pd.Series({"account_id": account_id, "account_nm": "unused"}))
        assert result.canonical == expected, account_id
        assert result.mapping_status == EXACT, account_id


def test_foreign_currency_years_excluded_for_cross_year_signals() -> None:
    # D-F: 통화전환 회사(두산밥캣류 KRW→USD)는 target 통화와 다른 연도를 신호에서 제외.
    from src.signals.sanity import exclude_foreign_currency_years

    frame = pd.DataFrame(
        {
            "year": ["2021", "2022", "2023", "2024"],
            "currency": ["KRW", "KRW", "USD", "USD"],
            "canonical": ["매출"] * 4,
            "amount": [1.3e12, 1.4e12, 1.1e9, 1.2e9],
        }
    )
    kept = exclude_foreign_currency_years(frame, target_year=2024)
    assert set(kept["year"]) == {"2023", "2024"}, "USD target → KRW연도 제외"

    kept_old = exclude_foreign_currency_years(frame, target_year=2021)
    assert set(kept_old["year"]) == {"2021", "2022"}, "KRW target → USD연도 제외"

    # 통화 컬럼 없거나 단일통화면 no-op (하위호환)
    no_cur = frame.drop(columns=["currency"])
    assert len(exclude_foreign_currency_years(no_cur, target_year=2024)) == 4
    uniform = frame.assign(currency="KRW")
    assert len(exclude_foreign_currency_years(uniform, target_year=2024)) == 4


def test_da_chunk1_cf_canonicals_registered() -> None:
    # D-A Chunk1: CF 핵심 흐름 신설 canonical이 표준ID로 EXACT 매핑.
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    cases = [
        ("dart_CashAndCashEquivalentsAtEndOfPeriodCf", "기말현금및현금성자산"),
        ("dart_CashAndCashEquivalentsAtBeginningOfPeriodCf", "기초현금및현금성자산"),
        ("ifrs-full_IncreaseDecreaseInCashAndCashEquivalents", "현금및현금성자산순증감"),
        ("ifrs-full_EffectOfExchangeRateChangesOnCashAndCashEquivalents", "현금환율변동효과"),
        ("dart_PurchaseOfShortTermFinancialInstruments", "단기금융상품취득"),
        ("dart_ProceedsFromSalesOfShortTermFinancialInstruments", "단기금융상품처분"),
        ("dart_PurchaseOfLongTermFinancialInstruments", "장기금융상품취득"),
        ("dart_ProceedsFromSalesOfLongTermFinancialInstruments", "장기금융상품처분"),
        ("dart_IncreaseInGuaranteeDeposits", "임차보증금증가"),
        ("dart_DecreaseInGuaranteeDeposits", "임차보증금감소"),
        ("ifrs-full_DividendsReceivedClassifiedAsOperatingActivities", "배당금수취"),
        (
            "ifrs-full_ProceedsFromSalesOfIntangibleAssetsClassifiedAsInvestingActivities",
            "무형자산처분",
        ),
        ("dart_PaymentsOfFinanceLeaseLiabilitiesClassifiedAsFinancingActivities", "리스부채상환"),
        ("dart_ProceedsFromShortTermBorrowings", "단기차입금증가"),
        ("dart_RepaymentsOfShortTermBorrowings", "단기차입금상환"),
        ("ifrs-full_ProceedsFromGovernmentGrantsClassifiedAsInvestingActivities", "정부보조금수취"),
        ("ifrs-full_AdjustmentsForReconcileProfitLoss", "당기순이익조정가감"),
    ]
    for account_id, expected in cases:
        result = mapper.map_row(pd.Series({"account_id": account_id, "account_nm": "x"}))
        assert result.canonical == expected, account_id
        assert result.mapping_status == EXACT, account_id


def test_da_chunk2_sce_canonicals_registered() -> None:
    # D-A Chunk2: SCE 자본변동 이벤트 신설 canonical.
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    cases = [
        ("ifrs-full_IncreaseDecreaseThroughSharebasedPaymentTransactions", "주식기준보상"),
        (
            "ifrs-full_IncreaseDecreaseThroughChangesInOwnershipInterestsInSubsidiariesThatDoNotResultInLossOfControl",
            "종속기업소유지분변동",
        ),
        ("dart_PaymentForStockIssueCost", "신주발행비"),
        ("dart_ProceedsFromExerciseOfShareOptions", "주식선택권행사"),
        ("ifrs-full_ChangesInEquity", "자본증감합계"),
    ]
    for account_id, expected in cases:
        result = mapper.map_row(pd.Series({"account_id": account_id, "account_nm": "x"}))
        assert result.canonical == expected, account_id
        assert result.mapping_status == EXACT, account_id


def test_da_chunk7_cf_flows_registered() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    cases = [
        ("dart_ProceedsFromBonds", "사채발행"),
        ("dart_RepaymentsOfBonds", "사채상환"),
        ("dart_ProceedsFromConvertibleBonds", "전환사채발행"),
        ("ifrs-full_ProceedsFromIssuingShares", "주식발행"),
        ("dart_PurchaseOfOtherFinancialAssets", "기타금융자산취득"),
        ("dart_PurchaseOfOtherNonCurrentFinancialAssets", "비유동기타금융자산취득"),
        ("dart_ProceedsFromSalesOfOtherFinancialAssets", "기타금융자산처분"),
        ("dart_ProceedsFromSalesOfInvestmentsInSubsidiaries", "종속기업투자처분"),
        ("dart_ProceedsFromSalesOfInvestmentsInAssociates", "관계기업투자처분"),
        ("ifrs-full_PurchaseOfInvestmentProperty", "투자부동산취득"),
        ("dart_DispositionOfTreasuryShares", "자기주식처분"),
        ("ifrs-full_ProceedsFromBorrowingsClassifiedAsFinancingActivities", "차입금증가"),
        # 기존 리스부채상환에 ifrs 변형 등록
        ("ifrs-full_PaymentsOfLeaseLiabilitiesClassifiedAsFinancingActivities", "리스부채상환"),
    ]
    for account_id, expected in cases:
        result = mapper.map_row(pd.Series({"account_id": account_id, "account_nm": "x"}))
        assert result.canonical == expected, account_id
        assert result.mapping_status == EXACT, account_id


def test_da_chunk6_cf_adjustments_registered() -> None:
    # D-A Chunk6: CF 가감조정. BS/IS 잔액과 다른 칸(증감/조정)으로.
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    cases = [
        ("dart_AdjustmentsForDepreciationExpense", "감가상각비"),
        ("ifrs-full_AdjustmentsForAmortisationExpense", "무형자산상각비"),
        ("dart_AdjustmentsForBadDebtExpenses", "대손상각비"),
        ("dart_AdjustmentsForProvisionForSeveranceIndemnities", "퇴직급여"),
        ("dart_AdjustmentsForLossesOnForeignExchangeTranslations", "외화환산손실조정"),
        ("dart_AdjustmentsForGainOnDispositionOfTangibleAssets", "유형자산처분이익조정"),
        ("dart_AdjustmentsForWritedownsOfInventories", "재고자산평가손실"),
        ("dart_AdjustmentsForInterestExpenses", "이자비용조정"),
        ("ifrs-full_AdjustmentsForIncomeTaxExpense", "법인세비용조정"),
        ("ifrs-full_AdjustmentsForDecreaseIncreaseInInventories", "재고자산증감"),
        ("ifrs-full_AdjustmentsForDecreaseIncreaseInTradeAccountReceivable", "매출채권증감"),
        ("ifrs-full_AdjustmentsForIncreaseDecreaseInTradeAccountPayable", "매입채무증감"),
        (
            "dart_AdjustmentsForIncreasedecreaseInPostemploymentBenefitObligations",
            "퇴직급여채무증감",
        ),
    ]
    for account_id, expected in cases:
        result = mapper.map_row(pd.Series({"account_id": account_id, "account_nm": "x"}))
        assert result.canonical == expected, account_id
        assert result.mapping_status == EXACT, account_id
    # BS 잔액 canonical은 그대로 유지(증감과 분리)
    assert (
        mapper.map_row(
            pd.Series({"account_id": "ifrs-full_Inventories", "account_nm": "재고자산"})
        ).canonical
        == "재고자산"
    )


def test_da_chunk5_cis_is_registered() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    cases = [
        ("ifrs-full_ProfitLossFromContinuingOperations", "계속영업이익"),
        ("ifrs-full_ProfitLossFromDiscontinuedOperations", "중단영업이익"),
        ("ifrs-full_BasicEarningsLossPerShareFromContinuingOperations", "계속영업기본주당이익"),
        ("ifrs-full_DilutedEarningsLossPerShareFromContinuingOperations", "계속영업희석주당이익"),
        ("ifrs-full_OtherComprehensiveIncomeNetOfTaxGainsLossesOnRevaluation", "자산재평가손익"),
        # 지분법기타포괄손익: 재분류가능·불가능을 lump 분리(distinct 항목·소실 방지)
        (
            "ifrs-full_ShareOfOtherComprehensiveIncomeOfAssociatesAndJointVenturesAccountedForUsingEquityMethodThatWillBeReclassifiedToProfitOrLossNetOfTax",
            "지분법기타포괄손익재분류가능",
        ),
        (
            "ifrs-full_ShareOfOtherComprehensiveIncomeOfAssociatesAndJointVenturesAccountedForUsingEquityMethodThatWillNotBeReclassifiedToProfitOrLossNetOfTax",
            "지분법기타포괄손익재분류불가능",
        ),
        # FVOCI 적립금변동은 평가손익과 분리(lump 분리)
        (
            "dart_ChangesInReserveOfGainsAndLossesOnFinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome",
            "FVOCI적립금변동",
        ),
        ("dart_ChangesInForeignExchangeRates", "환율변동효과"),
    ]
    for account_id, expected in cases:
        result = mapper.map_row(pd.Series({"account_id": account_id, "account_nm": "x"}))
        assert result.canonical == expected, account_id
        assert result.mapping_status == EXACT, account_id


def _sce_stock_balance_raw(stock_label: str = "소계", stock_amount: str = "1,100") -> pd.DataFrame:
    rows = [
        ("dart_EquityAtBeginningOfPeriod", "기초자본", "1,000"),
        ("ifrs-full_ProfitLoss", "당기순이익", "100"),
        ("dart_ChangesInEquity", stock_label, stock_amount),
        ("ifrs-full_Equity", "자본총계", "1,100"),
    ]
    return pd.DataFrame(
        [
            {
                "corp_code": "00000000",
                "bsns_year": "2023",
                "fs_div": "CFS",
                "sj_div": "SCE",
                "account_id": account_id,
                "account_nm": label,
                "account_detail": "연결재무제표 [member]",
                "thstrm_amount": amount,
                "frmtrm_amount": "",
                "bfefrmtrm_amount": "",
                "currency": "KRW",
            }
            for account_id, label, amount in rows
        ]
    )


def test_n1e_restatement_marker_normalizes_spaces() -> None:
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))

    assert (
        comp_map.classify_change_role("기타 중요 계정", "회계정책변경 효과반영후자본")
        == "restated_begin"
    )


def test_n1d_stock_balance_row_excluded_from_sce_leaf_sum() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))

    out = extract_sce_components(_sce_stock_balance_raw(), mapper, comp_map)
    stock_rows = out[(out["change_label"] == "소계") & (out["component_std"] == "-")]

    assert stock_rows["change_role"].tolist() == ["stock_balance"]
    balance = sce_balance(out, "CFS")
    assert balance["ok"] is True
    assert balance["leaf_sum"] == 100.0


def test_stock_balance_marker_stays_leaf_when_cumulative_check_fails() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))

    out = extract_sce_components(_sce_stock_balance_raw(stock_amount="1,150"), mapper, comp_map)
    stock_rows = out[(out["change_label"] == "소계") & (out["component_std"] == "-")]

    assert stock_rows["change_role"].tolist() == ["leaf"]


def _sce_rows_for_round6(cells: list[tuple[str, str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "corp_code": "00000000",
                "bsns_year": "2023",
                "fs_div": "CFS",
                "sj_div": "SCE",
                "account_id": account_id,
                "account_nm": label,
                "account_detail": detail,
                "thstrm_amount": amount,
                "frmtrm_amount": "",
                "bfefrmtrm_amount": "",
                "currency": "KRW",
            }
            for account_id, label, detail, amount in cells
        ]
    )


def test_n1f_delta_restated_added_before_stock_balance() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round6(
        [
            ("dart_EquityAtBeginningOfPeriod", "기초자본", "연결재무제표 [member]", "31,300"),
            ("", "재무제표 재작성효과", "연결재무제표 [member]", "2,572"),
            ("", "수정 후 금액", "연결재무제표 [member]", "33,872"),
            ("ifrs-full_Equity", "자본총계", "연결재무제표 [member]", "33,872"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    stock = out[(out["change_label"] == "수정 후 금액") & (out["component_std"] == "-")]
    balance = sce_balance(out, "CFS")

    assert stock["change_role"].tolist() == ["stock_balance"]
    assert set(out.loc[out["change_label"] == "수정 후 금액", "change_role"]) == {"stock_balance"}
    assert balance["ok"] is True
    assert balance["leaf_sum"] == 2572.0


def test_n1f_balance_restated_still_replaces_running_balance() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round6(
        [
            ("dart_EquityAtBeginningOfPeriod", "기초자본", "연결재무제표 [member]", "1,000"),
            ("", "기초자본(조정후)", "연결재무제표 [member]", "1,000"),
            ("ifrs-full_Equity", "자본총계", "연결재무제표 [member]", "1,000"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    adjusted = out[(out["change_label"] == "기초자본(조정후)") & (out["component_std"] == "-")]
    balance = sce_balance(out, "CFS")

    assert adjusted["change_role"].tolist() == ["restated_begin"]
    assert balance["ok"] is True
    assert balance["leaf_sum"] == 0.0


def test_n1g_missing_bare_total_uses_component_sum_for_sce_balance() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round6(
        [
            ("dart_EquityAtBeginningOfPeriod", "기초자본", "연결재무제표 [member]", "1,000"),
            ("", "재무제표 재작성효과", "이익잉여금 [member]", "-514"),
            ("ifrs-full_Equity", "자본총계", "연결재무제표 [member]", "486"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    derived = out[
        (out["change_label"] == "재무제표 재작성효과")
        & (out["component_std"] == "-")
        & (out["component_role"] == "derived_total")
    ]
    balance = sce_balance(out, "CFS")

    assert derived["amount"].tolist() == [-514.0]
    assert balance["ok"] is True


def _sce_rows_for_round7(cells: list[tuple[str, str, str, str]]) -> pd.DataFrame:
    rows = []
    for account_id, account_nm, account_detail, amount in cells:
        rows.append(
            {
                "corp_code": "x",
                "bsns_year": "2025",
                "sj_div": "SCE",
                "fs_div": "CFS",
                "account_id": account_id,
                "account_nm": account_nm,
                "account_detail": account_detail,
                "thstrm_amount": amount,
                "frmtrm_amount": "",
                "bfefrmtrm_amount": "",
                "currency": "KRW",
            }
        )
    return pd.DataFrame(rows)


def test_n2d_mixed_sign_component_sum_keeps_raw_signs_and_net_derived_bare() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round7(
        [
            ("", "자본 내 대체", "자본금 [member]", "-33018"),
            ("", "자본 내 대체", "자본잉여금 [member]", "33018"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    components = out[
        (out["change_label"] == "자본 내 대체")
        & (out["component_std"].isin(["자본금", "자본잉여금"]))
    ].sort_values("component_std")
    derived = out[
        (out["change_label"] == "자본 내 대체")
        & (out["component_std"] == "-")
        & (out["component_role"] == "derived_total")
    ]

    by_component = dict(zip(components["component_std"], components["amount"], strict=True))
    assert by_component == {"자본금": -33018.0, "자본잉여금": 33018.0}
    assert derived["amount"].tolist() == [0.0]


def test_n2d_positive_deduction_changes_apply_to_bare_and_component() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round7(
        [
            ("ifrs-full_DividendsPaid", "배당", "연결재무제표 [member]", "100"),
            ("ifrs-full_DividendsPaid", "배당", "이익잉여금 [member]", "100"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    bare = out[(out["change_label"] == "배당") & (out["component_std"] == "-")]
    component = out[(out["change_label"] == "배당") & (out["component_std"] == "이익잉여금")]

    assert bare["amount"].tolist() == [-100.0]
    assert component["amount"].tolist() == [-100.0]


def test_n2e_noncontrolling_interest_dividend_is_registered_as_deduction() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    row = pd.Series(
        {
            "account_id": "ifrs-full_DividendsRecognisedAsDistributionsToNoncontrollingInterests",
            "account_nm": "비지배지분에 대한 배당금",
        }
    )

    mapped = mapper.map_change_row(row)

    assert mapped.canonical in comp_map.deductions
    assert comp_map.deduction_sign(mapped.canonical, "비지배지분에 대한 배당금") == "minus"


def test_member_sign_deduction_applies_to_grand_and_member_cells() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round7(
        [
            ("ifrs-full_DividendsPaid", "배당", "연결재무제표 [member]", "100"),
            ("ifrs-full_DividendsPaid", "배당", "이익잉여금 [member]", "100"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    cells = out[out["change_label"] == "배당"]
    by_component = dict(zip(cells["component_std"], cells["amount"], strict=True))

    assert by_component["-"] == -100.0
    assert by_component["이익잉여금"] == -100.0


def test_member_sign_mixed_transfer_members_keep_raw_signs() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round7(
        [
            ("", "FVOCI 처분", "기타자본구성요소 [member]", "-882"),
            ("", "FVOCI 처분", "이익잉여금 [member]", "882"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    components = out[
        (out["change_label"] == "FVOCI 처분")
        & (out["component_std"].isin(["기타자본구성요소", "이익잉여금"]))
    ].sort_values("component_std")

    assert dict(zip(components["component_std"], components["amount"], strict=True)) == {
        "기타자본구성요소": -882.0,
        "이익잉여금": 882.0,
    }


def test_member_sign_deduction_member_sum_equals_grand() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round7(
        [
            ("ifrs-full_DividendsPaid", "배당", "연결재무제표 [member]", "300"),
            ("ifrs-full_DividendsPaid", "배당", "이익잉여금 [member]", "100"),
            ("ifrs-full_DividendsPaid", "배당", "비지배지분 [member]", "200"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    cells = out[out["change_label"] == "배당"]
    grand = cells.loc[cells["component_std"] == "-", "amount"].sum()
    member_sum = cells.loc[~cells["component_std"].isin(["-"]), "amount"].sum()

    assert member_sum == grand == -300.0


def test_member_sign_non_deduction_opposite_members_preserved_not_guessed() -> None:
    # 비차감 행에서 member가 grand과 부호 반대여도(원공시 내부 모순) Phase1은 충실히 보존한다.
    # 모순 해결(부호 뒤집기)은 "grand이 진실"이라는 추측이라 하지 않는다 — 가로항등·검산이 노출한다.
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round7(
        [
            ("", "신종자본증권 전환권행사", "연결재무제표 [member]", "600"),
            ("", "신종자본증권 전환권행사", "자본금 [member]", "-100"),
            ("", "신종자본증권 전환권행사", "자본잉여금 [member]", "-500"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    cells = out[out["change_label"] == "신종자본증권 전환권행사"]
    grand = cells.loc[cells["component_std"] == "-", "amount"].sum()
    member_sum = cells.loc[~cells["component_std"].isin(["-"]), "amount"].sum()

    assert grand == 600.0
    assert member_sum == -600.0  # raw 부호 보존(뒤집지 않음)


def _horizontal_df(rows: list[tuple[str, float]], fs_div: str = "CFS") -> pd.DataFrame:
    """가로항등 테스트용 sce_df: (component_std, amount) 한 변동행."""

    return pd.DataFrame(
        [
            {
                "fs_div": fs_div,
                "change_label": "연결대상범위의 변동",
                "change_role": "leaf",
                "component_std": comp,
                "amount": amount,
            }
            for comp, amount in rows
        ]
    )


def test_sce_horizontal_identity_flags_grand_vs_member_contradiction() -> None:
    # 00141477형: 공시 grand 부호가 지배+비지배 합과 정확히 반대(원공시 내부 모순).
    df = _horizontal_df(
        [
            ("-", 2_126_881_891),
            ("지배기업소유주지분", -12_867_283_357),
            ("비지배지분", 10_740_401_465),
        ]
    )
    out = sce_horizontal_identity(df, "CFS")
    assert len(out) == 1
    assert out[0]["change_label"] == "연결대상범위의 변동"
    assert abs(out[0]["diff"]) > 1_000


def test_sce_horizontal_identity_consistent_no_flag() -> None:
    # grand == 지배 + 비지배 정확히 성립 → anomaly 없음.
    df = _horizontal_df(
        [
            ("-", 3_000),
            ("지배기업소유주지분", 2_000),
            ("비지배지분", 1_000),
        ]
    )
    assert sce_horizontal_identity(df, "CFS") == []


def test_sce_horizontal_identity_rounding_within_tolerance_no_flag() -> None:
    # 원 단위 반올림 ±몇원 잔차는 모순이 아니다(거짓양성 차단).
    df = _horizontal_df(
        [
            ("-", 5_000_000_002),
            ("지배기업소유주지분", 3_000_000_000),
            ("비지배지분", 2_000_000_000),
        ]
    )
    assert sce_horizontal_identity(df, "CFS") == []


def test_sce_horizontal_identity_skips_when_nci_missing() -> None:
    # 비지배지분 미공시(단일기업·NCI 없음) 변동행은 가로항등 적용 불가 → skip.
    df = _horizontal_df(
        [
            ("-", 5_000),
            ("지배기업소유주지분", 2_000),
        ]
    )
    assert sce_horizontal_identity(df, "CFS") == []


def test_sce_horizontal_identity_immaterial_diff_below_materiality_no_flag() -> None:
    # 총계 51.7억 대비 100만원(0.02%) 차이는 비물질 반올림 → anomaly 아님(00147295형).
    df = _horizontal_df(
        [
            ("-", -5_171_000_000),
            ("지배기업소유주지분", -5_170_000_000),
            ("비지배지분", 0),
        ]
    )
    assert sce_horizontal_identity(df, "CFS") == []


def _sce_rows_for_round8(cells: list[tuple[str, str, str, str, str]]) -> pd.DataFrame:
    rows = []
    for account_id, account_nm, account_detail, amount, prior_amount in cells:
        rows.append(
            {
                "corp_code": "x",
                "bsns_year": "2025",
                "sj_div": "SCE",
                "fs_div": "CFS",
                "account_id": account_id,
                "account_nm": account_nm,
                "account_detail": account_detail,
                "thstrm_amount": amount,
                "frmtrm_amount": prior_amount,
                "bfefrmtrm_amount": "",
                "currency": "KRW",
            }
        )
    return pd.DataFrame(rows)


def test_n2f_parent_leaf_equal_to_child_sum_retagged_as_subtotal() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round8(
        [
            (
                "",
                "기초자본",
                "연결재무제표 [member]",
                "100000",
                "",
            ),
            (
                "dart_OtherComprehensiveIncomeNetOfTaxChangeInFairValueOfFinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome",
                "(1) 기타포괄손익-공정가치측정금융자산 평가이익",
                "연결재무제표 [member]",
                "13036",
                "42",
            ),
            (
                "dart_OtherComprehensiveIncomeNetOfTaxDisposalOfFinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome",
                "기타포괄손익-공정가치측정금융자산처분손익",
                "연결재무제표 [member]",
                "0",
                "0",
            ),
            (
                "ifrs-full_OtherComprehensiveIncomeNetOfTaxFinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome",
                "기타포괄손익-공정가치측정금융자산관련손익 합계",
                "연결재무제표 [member]",
                "13036",
                "42",
            ),
            (
                "ifrs-full_Equity",
                "자본총계",
                "연결재무제표 [member]",
                "113036",
                "",
            ),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    parent = out[out["change_label"] == "기타포괄손익-공정가치측정금융자산관련손익 합계"]
    children = out[
        out["change_label"].isin(
            [
                "(1) 기타포괄손익-공정가치측정금융자산 평가이익",
                "기타포괄손익-공정가치측정금융자산처분손익",
            ]
        )
    ]

    assert parent["change_role"].tolist() == ["subtotal"]
    assert set(children["change_role"]) == {"leaf"}


def test_n2f_strong_parent_signal_single_child_exact_match_retagged() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round8(
        [
            (
                "",
                "기초자본",
                "연결재무제표 [member]",
                "100000",
                "",
            ),
            (
                "dart_OtherComprehensiveIncomeNetOfTaxChangeInFairValueOfFinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome",
                "기타포괄손익-공정가치측정금융자산평가손익",
                "연결재무제표 [member]",
                "26742",
                "-5055",
            ),
            (
                "ifrs-full_OtherComprehensiveIncomeNetOfTaxFinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome",
                "기타포괄손익-공정가치측정금융자산관련손익 합계",
                "연결재무제표 [member]",
                "26742",
                "-5055",
            ),
            (
                "ifrs-full_Equity",
                "자본총계",
                "연결재무제표 [member]",
                "126742",
                "",
            ),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    parent = out[out["change_label"] == "기타포괄손익-공정가치측정금융자산관련손익 합계"]
    child = out[out["change_label"] == "기타포괄손익-공정가치측정금융자산평가손익"]

    assert parent["change_role"].tolist() == ["subtotal"]
    assert child["change_role"].tolist() == ["leaf"]


def test_n2f_independent_leaf_with_nonmatching_vector_stays_leaf() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round8(
        [
            ("", "평가손익", "연결재무제표 [member]", "90", "1"),
            ("", "처분손익", "연결재무제표 [member]", "5", "1"),
            ("", "관련손익 합계", "연결재무제표 [member]", "100", "2"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)

    assert set(out["change_role"]) == {"leaf"}


def test_dedid_annual_dividend_id_is_deduction_even_when_canonical_is_not() -> None:
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))

    assert (
        comp_map.deduction_sign(
            "기타 중요 계정",
            "현금배당금",
            "dart_AnnualDividendsPaid",
        )
        == "minus"
    )


def test_n2f_equal_amount_simple_duplicate_without_zero_child_stays_leaf() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round8(
        [
            ("", "독립 변동 A", "연결재무제표 [member]", "100", "10"),
            ("", "독립 변동 B", "연결재무제표 [member]", "100", "10"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)

    assert out["change_role"].tolist() == ["leaf", "leaf"]


def test_n4c_current_nan_prior_different_blank_rows_survive(tmp_path: Path) -> None:
    raw = pd.DataFrame(
        [
            {
                "corp_code": "00000000",
                "bsns_year": "2023",
                "sj_div": "BS",
                "account_id": "-표준계정코드 미사용-",
                "account_nm": "전환사채",
                "account_detail": "-",
                "thstrm_amount": "",
                "frmtrm_amount": "",
                "bfefrmtrm_amount": "",
            },
            {
                "corp_code": "00000000",
                "bsns_year": "2023",
                "sj_div": "BS",
                "account_id": "-표준계정코드 미사용-",
                "account_nm": "전환사채",
                "account_detail": "-",
                "thstrm_amount": "",
                "frmtrm_amount": "6,395,852,761",
                "bfefrmtrm_amount": "",
            },
            {
                "corp_code": "00000000",
                "bsns_year": "2023",
                "sj_div": "BS",
                "account_id": "-표준계정코드 미사용-",
                "account_nm": "전환사채",
                "account_detail": "-",
                "thstrm_amount": "",
                "frmtrm_amount": "6,395,852,761",
                "bfefrmtrm_amount": "",
            },
        ]
    )
    path = tmp_path / "raw.csv"
    raw.to_csv(path, index=False)
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    frame = normalize_raw_file(path, "OFS", mapper)
    prior_values = pd.to_numeric(frame["prior_amount"], errors="coerce").dropna().tolist()

    assert prior_values == [6395852761.0]
    assert len(frame[frame["label"] == "전환사채"]) == 2


def test_da_chunk4_cf_remaining_registered() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    cases = [
        ("dart_PurchaseOfFairValueFinancialAsset", "FVPL금융자산취득"),
        ("dart_ProceedsFromSalesOfFairValueFinancialAsset", "FVPL금융자산처분"),
        ("dart_PurchaseOfShortTermLoansAndReceivables", "단기대여금증가"),
        ("dart_ProceedsFromSalesOfLongTermLoansAndReceivables", "장기대여금감소"),
        ("dart_IncreaseInLoans", "대여금증가"),
        ("dart_IncreaseInGuaranteeDepositsAsFinancialActivities", "임대보증금증가"),
        ("dart_PurchaseOfInvestmentsInSubsidiaries", "종속기업투자취득"),
        ("dart_PurchaseOfInvestmentsInAssociates", "관계기업투자취득"),
        ("ifrs-full_RepaymentsOfBorrowingsClassifiedAsFinancingActivities", "차입금상환"),
        (
            "ifrs-full_IncreaseDecreaseInCashAndCashEquivalentsBeforeEffectOfExchangeRateChanges",
            "환율효과반영전현금증감",
        ),
    ]
    for account_id, expected in cases:
        result = mapper.map_row(pd.Series({"account_id": account_id, "account_nm": "x"}))
        assert result.canonical == expected, account_id
        assert result.mapping_status == EXACT, account_id


def test_da_chunk3_bs_canonicals_registered() -> None:
    # D-A Chunk3: BS 신설 canonical + 기존칸 등록 대표 검증.
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    cases = [
        ("ifrs-full_CurrentTaxAssets", "당기법인세자산"),
        ("ifrs-full_OtherCurrentFinancialAssets", "기타유동금융자산"),
        ("ifrs-full_OtherNoncurrentFinancialAssets", "기타비유동금융자산"),
        ("ifrs-full_OtherCurrentFinancialLiabilities", "기타유동금융부채"),
        ("dart_CurrentDerivativeAsset", "유동파생상품자산"),
        ("dart_CurrentDerivativeLiabilities", "유동파생상품부채"),
        ("dart_LongTermDepositsNotClassifiedAsCashEquivalents", "장기금융상품"),
        ("dart_CapitalSurplus", "자본잉여금"),
        ("dart_ElementsOfOtherStockholdersEquity", "기타자본구성요소"),
        ("dart_ConvertibleBonds", "전환사채"),
        (
            "ifrs-full_NoncurrentAssetsOrDisposalGroupsClassifiedAsHeldForSaleOrAsHeldForDistributionToOwners",
            "매각예정자산",
        ),
        ("dart_ShortTermTradePayables", "매입채무"),
        ("dart_IssuedCapitalOfCommonStock", "자본금"),
    ]
    for account_id, expected in cases:
        result = mapper.map_row(pd.Series({"account_id": account_id, "account_nm": "x"}))
        assert result.canonical == expected, account_id
        assert result.mapping_status == EXACT, account_id


def test_dc_noncurrent_receivable_payable_registered() -> None:
    # D-C: 비유동 채권/채무 표준ID는 라벨이 유동 통합("매출채권및기타채권")이어도 비유동 칸으로.
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    cases = [
        ("dart_LongTermTradeAndOtherNonCurrentReceivablesGross", "비유동매출채권"),
        ("ifrs-full_NoncurrentReceivables", "비유동매출채권"),
        ("dart_LongTermTradeAndOtherNonCurrentPayables", "비유동매입채무"),
        ("ifrs-full_NoncurrentPayables", "비유동매입채무"),
    ]
    from src.normalize.mapper import ID_LABEL_CONFLICT

    for account_id, expected in cases:
        # 라벨은 일부러 유동 통합 alias로 줘도 account_id 우선이라 비유동으로 가야 함.
        # N5: id≠label canonical(유동/비유동 계열 차이 = 패턴②) → canonical은 id-first 유지 +
        # mapping_status에 모순 흔적. 실데이터는 보통 label이 비유동/통합 동명이라 EXACT 다수.
        result = mapper.map_row(
            pd.Series({"account_id": account_id, "account_nm": "매출채권및기타채권"})
        )
        assert result.canonical == expected, account_id
        assert result.mapping_status == ID_LABEL_CONFLICT, account_id


def test_db_explicit_registered_variants() -> None:
    # D-B: 접두사통일로 안 잡히는 5개(dart_/ifrs-full_BondsIssued)는 config 명시 등록.
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    cases = [
        ("dart_OtherCurrentAssets", "기타유동자산"),
        ("dart_IncreaseDecreaseThroughChangesInAccountingPolicies", "회계정책변경효과"),
        (
            "dart_OtherComprehensiveIncomeThatWillBeReclassifiedToProfitOrLossNetOfTax",
            "재분류가능기타포괄손익",
        ),
        (
            "dart_OtherComprehensiveIncomeThatWillNotBeReclassifiedToProfitOrLossNetOfTax",
            "재분류불가능기타포괄손익",
        ),
        ("ifrs-full_BondsIssued", "사채"),
    ]
    for account_id, expected in cases:
        result = mapper.map_row(pd.Series({"account_id": account_id, "account_nm": "unused"}))
        assert result.canonical == expected, account_id
        assert result.mapping_status == EXACT, account_id


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
            "FVOCI지분상품평가손익",
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

    # lump 분리(소실 방지): account_id별 distinct canonical로 정밀 매핑
    cases = [
        ("ifrs-full_InvestmentsInAssociates", "관계기업투자"),
        ("ifrs-full_InvestmentAccountedForUsingEquityMethod", "지분법적용투자"),
        ("ifrs-full_InvestmentsInSubsidiariesJointVenturesAndAssociates", "종속관계공동기업투자"),
    ]
    for account_id, expected in cases:
        result = mapper.map_row(pd.Series({"account_id": account_id, "account_nm": "x"}))
        assert result.canonical == expected, account_id

    # label-only(account_id 공백)는 대표 canonical(관계기업투자)로 fallback 유지
    for label in [
        "종속기업및관계기업투자주식",
        "종속기업, 관계기업 및 공동기업투자",
        "관계기업및공동기업 투자",
    ]:
        result = mapper.map_row(pd.Series({"account_id": "", "account_nm": label}))
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


def test_pure_vs_combined_trade_accounts_separated() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    # 순수 매출채권/매입채무 — 순수 canonical
    for account_id in ["dart_ShortTermTradeReceivable", "ifrs-full_CurrentTradeReceivables"]:
        result = mapper.map_row(pd.Series({"account_id": account_id, "account_nm": "매출채권"}))
        assert result.canonical == "매출채권"
    result = mapper.map_row(
        pd.Series(
            {
                "account_id": "ifrs-full_TradeAndOtherCurrentPayablesToTradeSuppliers",
                "account_nm": "매입채무",
            }
        )
    )
    assert result.canonical == "매입채무"

    # "및 기타채권/채무" 통합 — 별도 canonical(순수계정 안 덮음)
    result = mapper.map_row(
        pd.Series(
            {
                "account_id": "ifrs-full_TradeAndOtherCurrentReceivables",
                "account_nm": "매출채권 및 기타유동채권",
            }
        )
    )
    assert result.canonical == "매출채권및기타유동채권"
    result = mapper.map_row(pd.Series({"account_id": "", "account_nm": "매출채권 및 기타채권"}))
    assert result.canonical == "매출채권및기타유동채권"
    result = mapper.map_row(
        pd.Series(
            {
                "account_id": "ifrs-full_TradeAndOtherCurrentPayables",
                "account_nm": "매입채무및기타채무",
            }
        )
    )
    assert result.canonical == "매입채무및기타유동채무"


def test_statement_guard_demotes_cross_statement_keeps_is_cis() -> None:
    # _apply_statement_guard는 _arbitrate_conflicts(1단 표 호환성 심판)에 흡수됐다. 비충돌 행
    # (label_canonical 빈문자)에 대해서는 기존 statement_guard 강등 동작이 그대로 보존돼야 한다.
    from src.normalize.pipeline import _arbitrate_conflicts

    frame = pd.DataFrame(
        [
            # BS 잔액 — 유지
            {
                "canonical": "재고자산",
                "canonical_statement": "BS",
                "label_canonical": "",
                "label_statement": "",
                "sj_div": "BS",
                "mapping_status": EXACT,
            },
            # CF 증감조정이 BS 잔액 칸으로 흡수된 행 — 강등돼야
            {
                "canonical": "재고자산",
                "canonical_statement": "BS",
                "label_canonical": "",
                "label_statement": "",
                "sj_div": "CF",
                "mapping_status": ALIAS,
            },
            # IS 계정이 포괄손익(CIS)으로 통합신고 — 호환, 유지
            {
                "canonical": "이자비용",
                "canonical_statement": "IS",
                "label_canonical": "",
                "label_statement": "",
                "sj_div": "CIS",
                "mapping_status": EXACT,
            },
            # CIS 계정이 자본변동(SCE) 칸으로 흡수 — 강등돼야
            {
                "canonical": "총포괄손익",
                "canonical_statement": "CIS",
                "label_canonical": "",
                "label_statement": "",
                "sj_div": "SCE",
                "mapping_status": EXACT,
            },
            # 이미 기타계정 — 그대로
            {
                "canonical": OTHER_CANONICAL,
                "canonical_statement": "",
                "label_canonical": "",
                "label_statement": "",
                "sj_div": "CF",
                "mapping_status": UNMAPPED,
            },
        ]
    )
    out = _arbitrate_conflicts(frame)
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
        "currency",
    ]
    assert frame["amount"].tolist() == [1000.0, -200.0]
    assert frame["prior_amount"].tolist() == [900.0, -300.0]
    assert frame.iloc[0]["prior2_amount"] == 800.0
    assert pd.isna(frame.iloc[1]["prior2_amount"])


def test_n4_distinct_exact_account_ids_both_survive(tmp_path: Path) -> None:
    # N4(라운드1): 서로 다른 표준 account_id 2행이 같은 canonical로 수렴하면 distinct line item이다.
    # 강등 보존 가드가 ALIAS에만 걸려 EXACT 비대표 행이 드롭되던 진짜 소실(00120526/2024 CFS
    # '장기차입금의 상환' 25,953,661,360 증발). distinct EXACT id는 둘 다 생존해야 한다.
    raw = pd.DataFrame(
        [
            {
                "corp_code": "00120526",
                "bsns_year": "2024",
                "sj_div": "CF",
                "account_id": "ifrs-full_RepaymentsOfNoncurrentBorrowings",
                "account_nm": "유동성장기차입금의 상환",
                "account_detail": "-",
                "thstrm_amount": "1666760970300",  # 대표(대금액)
            },
            {
                "corp_code": "00120526",
                "bsns_year": "2024",
                "sj_div": "CF",
                "account_id": "dart_RepaymentsOfLongTermBorrowings",
                "account_nm": "장기차입금의 상환",
                "account_detail": "-",
                "thstrm_amount": "25953661360",  # 비대표(소금액) — 소실되던 행
            },
        ]
    )
    path = tmp_path / "raw.csv"
    raw.to_csv(path, index=False)
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    frame = normalize_raw_file(path, "CFS", mapper)

    amounts = sorted(pd.to_numeric(frame["amount"], errors="coerce").dropna().tolist())
    assert amounts == [25953661360.0, 1666760970300.0], "두 표준 id 행 모두 생존(소실 0)"
    # 대표는 canonical 유지, 비대표는 기타로 강등 보존(이중계상 방지)
    canon = set(frame["canonical"])
    assert "비유동차입금상환" in canon
    assert OTHER_CANONICAL in canon


def test_n2_n3_hybrid_bond_and_dividend_deductions_registered() -> None:
    # N2/N3(라운드1): 신종자본증권 상환/배당/이자·배당금지급 변형은 자본 차감인데 raw가 양수로
    # 신고돼 검산이 raw 부호에 의존(연도마다 통과/실패 비결정)했다. sce_deduction_changes에
    # 등록해 -abs 결정화한다(하드코딩 아닌 config 데이터 등록).
    from src.normalize.config import load_sce_components

    comp = load_sce_components(Path("config/canonical_accounts.yaml"))
    for canonical in [
        "신종자본증권배당",
        "신종자본증권의 배당",
        "신종자본증권상환",
        "신종자본증권의 상환",
        "신종자본증권 이자",
        "신종자본증권 이자지급",
        "배당금지급",
    ]:
        assert canonical in comp.deductions, f"{canonical} 차감 목록 등록 필요"
    # 발행(가산)은 차감에 넣지 않는다(부호 보존)
    assert "신종자본증권발행" not in comp.deductions
    assert "신종자본증권의 발행" not in comp.deductions


def test_sce_change_role_classification() -> None:
    # N1/D5(라운드1): SCE 변동행 role 표준화. 검산은 leaf만 합산(소계·총계·개시·조정후개시 제외).
    from src.normalize.config import load_sce_components

    comp = load_sce_components(Path("config/canonical_accounts.yaml"))
    # 개시(기초자본 canonical)
    assert comp.classify_change_role("기초자본", "기초자본") == "begin"
    # 총계
    assert comp.classify_change_role("자본총계", "자본 총계") == "total"
    # 소계(총포괄손익·기타포괄손익·자본증감합계)
    assert comp.classify_change_role("총포괄손익", "총포괄손익") == "subtotal"
    assert comp.classify_change_role("기타포괄손익", "기타포괄손익") == "subtotal"
    assert comp.classify_change_role("자본증감합계", "자본증감합계") == "subtotal"
    # 조정후 개시(스톡) — canonical은 기타지만 label로 식별, 검산서 제외
    assert comp.classify_change_role("기타 중요 계정", "기초자본(조정후)") == "restated_begin"
    assert (
        comp.classify_change_role("기타 중요 계정", "회계정책 변경 후, 기초자본")
        == "restated_begin"
    )
    # leaf(실 변동) — 회계정책변경효과 FLOW·당기순이익·차감변동 등은 합산 대상
    assert comp.classify_change_role("기타 중요 계정", "회계정책변경효과") == "leaf"
    assert comp.classify_change_role("당기순이익", "당기순이익(손실)") == "leaf"
    assert comp.classify_change_role("신종자본증권상환", "신종자본증권 상환") == "leaf"
    # 순서 잠금: 소계 canonical 행의 label에 marker(기초자본)가 섞여도 subtotal 우선(결정적 판정).
    assert comp.classify_change_role("총포괄손익", "기초자본 총합 포괄손익") == "subtotal"


def test_sce_balance_leaf_only_excludes_subtotal_and_restated() -> None:
    # N1/D5: 검산 helper는 leaf만 합산. 소계(기타포괄손익)·조정후개시 스톡을 합산하면 이중계상.
    # 00134176/2023 축소 재현: 기초 45,858.59 + leaf(9.4+29.4+2,554.579) = 기말 48,451.99.
    from src.normalize.sce import sce_balance

    df = pd.DataFrame(
        [
            ("기초자본", "기초자본", "begin", 45858.59),
            ("FVOCI적립금변동", "기타포괄손익...평가이익", "leaf", 9.403),
            ("확정급여제도의 재측정손익", "확정급여제도의 재측정손익", "leaf", 29.418),
            ("당기순이익", "총당기순이익", "leaf", 2554.579),
            ("기타포괄손익", "기타포괄손익", "subtotal", 38.822),  # 소계 — 제외돼야
            ("기타 중요 계정", "기초자본(조정후)", "restated_begin", 99999.0),  # 스톡 — 제외
            ("자본총계", "자본총계", "total", 48451.99),
        ],
        columns=["change_canonical", "change_label", "change_role", "amount"],
    )
    df["fs_div"] = "CFS"
    df["component_std"] = "-"

    res = sce_balance(df, "CFS")

    assert res["computable"] is True
    assert abs(res["diff"]) < 0.01, f"leaf-only 검산 0 근접 기대, got {res['diff']}"
    assert abs(res["begin"] - 45858.59) < 0.01
    assert abs(res["end"] - 48451.99) < 0.01


def test_r1_subtotal_label_variants_classified() -> None:
    # R1(라운드2): 소계 라벨 변형이 role 분류 밖이라 leaf로 이중계상되던 것.
    # 총포괄이익→총포괄손익 alias / '소유주와의 거래' 계열(합계·등)→소계. config 데이터 등록.
    from src.normalize.config import load_sce_components

    comp = load_sce_components(Path("config/canonical_accounts.yaml"))
    # 총포괄이익은 총포괄손익 alias → canonical 총포괄손익 → subtotal
    assert comp.classify_change_role("총포괄손익", "총포괄이익") == "subtotal"
    # '소유주와의 거래 합계' canonical → subtotal
    assert comp.classify_change_role("소유주와의 거래 합계", "소계") == "subtotal"
    # unmapped 변형('자본에 직접 반영된 소유주와의 거래 등')은 label marker로 subtotal
    assert (
        comp.classify_change_role("기타 중요 계정", "자본에 직접 반영된 소유주와의 거래 등")
        == "subtotal"
    )
    # 일반 leaf(소유주 단어 없는)는 영향 없음
    assert comp.classify_change_role("당기순이익", "당기순이익(손실)") == "leaf"


def test_r1_total_comprehensive_income_variant_alias() -> None:
    # R1: 총포괄이익이 총포괄손익 canonical로 매핑(alias)돼야 소계로 분류 가능.
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    r = mapper.map_row(pd.Series({"account_id": "", "account_nm": "총포괄이익"}))
    assert r.canonical == "총포괄손익"


def test_r1v_current_period_total_comprehensive_income_maps_only_for_sce_change() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    change = mapper.map_change_row(pd.Series({"account_id": "", "account_nm": "당기총포괄손익"}))
    main = mapper.map_row(pd.Series({"account_id": "", "account_nm": "당기총포괄손익"}))
    profit = mapper.map_row(
        pd.Series({"account_id": "ifrs-full_ProfitLoss", "account_nm": "당기순이익"})
    )
    comp = load_sce_components(Path("config/canonical_accounts.yaml"))

    assert change.canonical == "총포괄손익"
    assert comp.classify_change_role(change.canonical, "당기총포괄손익") == "subtotal"
    assert main.canonical == OTHER_CANONICAL
    assert profit.canonical == "당기순이익"


def test_r10_comprehensive_income_suffix_subtotal_retagged_only_when_vector_matches() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round7(
        [
            ("", "기초자본", "연결재무제표 [member]", "100"),
            ("ifrs-full_ProfitLoss", "당기순이익", "연결재무제표 [member]", "10"),
            ("ifrs-full_OtherComprehensiveIncome", "기타포괄손익", "연결재무제표 [member]", "20"),
            ("", "총포괄이익 소계", "연결재무제표 [member]", "30"),
            ("", "검산불일치 소계", "연결재무제표 [member]", "31"),
            ("ifrs-full_Equity", "자본총계", "연결재무제표 [member]", "130"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    roles = {
        label: set(group["change_role"])
        for label, group in out.groupby("change_label", dropna=False)
    }

    assert roles["총포괄이익 소계"] == {"subtotal"}
    assert roles["검산불일치 소계"] == {"leaf"}


def test_r11_same_label_subtotal_blocks_retagged_by_adjacent_source_order() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round7(
        [
            ("", "기초자본", "연결재무제표 [member]", "100"),
            ("ifrs-full_ProfitLoss", "당기순이익", "연결재무제표 [member]", "10"),
            ("ifrs-full_OtherComprehensiveIncome", "기타포괄손익", "연결재무제표 [member]", "20"),
            ("", "소계", "연결재무제표 [member]", "30"),
            ("ifrs-full_IssueOfEquity", "유상증자", "연결재무제표 [member]", "7"),
            ("ifrs-full_PurchaseOfTreasuryShares", "자기주식 취득", "연결재무제표 [member]", "2"),
            ("", "소계", "연결재무제표 [member]", "5"),
            ("", "기타", "연결재무제표 [member]", "0"),
            ("", "소계", "연결재무제표 [member]", "99"),
            ("ifrs-full_Equity", "자본총계", "연결재무제표 [member]", "135"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    subtotal_rows = out[(out["change_label"] == "소계") & (out["component_std"] == "-")]

    assert subtotal_rows["change_role"].tolist() == ["subtotal", "subtotal", "leaf"]


def test_r11_nested_child_component_excluded_from_derived_bare_total_preserves_net_zero() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round7(
        [
            ("", "기초자본", "연결재무제표 [member]", "1,000"),
            (
                "",
                "FVOCI 처분",
                "기타자본구성요소 [member]",
                "-882",
            ),
            (
                "",
                "FVOCI 처분",
                "기타자본구성요소 [member]|평가손익 [member]",
                "-882",
            ),
            ("", "FVOCI 처분", "이익잉여금 [member]", "882"),
            ("ifrs-full_Equity", "자본총계", "연결재무제표 [member]", "1,000"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    derived = out[
        (out["change_label"] == "FVOCI 처분")
        & (out["component_std"] == "-")
        & (out["component_role"] == "derived_total")
    ]
    components = out[
        (out["change_label"] == "FVOCI 처분")
        & (out["component_std"].isin(["기타자본구성요소", "이익잉여금"]))
    ]
    balance = sce_balance(out, "CFS")

    assert derived["amount"].tolist() == [0.0]
    assert sorted(components["amount"].tolist()) == [-882.0, 882.0]
    assert balance["ok"] is True


def test_r11_id_label_conflict_total_comprehensive_income_subtotal() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round7(
        [
            ("ifrs-full_ProfitLoss", "당기순이익", "연결재무제표 [member]", "10"),
            ("ifrs-full_OtherComprehensiveIncome", "기타포괄손익", "연결재무제표 [member]", "20"),
            ("ifrs-full_IssueOfEquity", "총포괄손익 소계", "연결재무제표 [member]", "30"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    row = out[(out["change_label"] == "총포괄손익 소계") & (out["component_std"] == "-")].iloc[0]

    assert row["change_canonical"] == "총포괄손익"
    assert row["change_role"] == "subtotal"
    assert row["change_status"] == ID_LABEL_CONFLICT


def test_r12_structural_aggregate_label_retagged_only_when_balance_self_verifies() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round7(
        [
            ("", "기초자본", "연결재무제표 [member]", "1000"),
            (
                "ifrs-full_PurchaseOfTreasuryShares",
                "자기주식 취득",
                "연결재무제표 [member]",
                "485947",
            ),
            ("", "자기주식 소각", "연결재무제표 [member]", "-81"),
            ("", "자기주식 거래 합계", "연결재무제표 [member]", "-486028"),
            ("ifrs-full_Equity", "자본총계", "연결재무제표 [member]", "-485028"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    aggregate = out[(out["change_label"] == "자기주식 거래 합계") & (out["component_std"] == "-")]
    balance = sce_balance(out, "CFS")

    assert aggregate["change_role"].tolist() == ["subtotal"]
    assert balance["ok"] is True


def test_r12_current_only_stock_vector_retagged_as_restated_begin() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round8(
        [
            ("", "기초자본", "연결재무제표 [member]", "1000", "900"),
            ("", "기초자본", "자본금 [member]", "100", "80"),
            ("", "기초자본", "이익잉여금 [member]", "900", "820"),
            ("", "회계정책변경에 따른 증가(감소)", "연결재무제표 [member]", "1000", ""),
            ("", "회계정책변경에 따른 증가(감소)", "자본금 [member]", "100", ""),
            ("", "회계정책변경에 따른 증가(감소)", "이익잉여금 [member]", "900", ""),
            ("ifrs-full_Equity", "자본총계", "연결재무제표 [member]", "1000", ""),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    stock = out[out["change_label"] == "회계정책변경에 따른 증가(감소)"]
    balance = sce_balance(out, "CFS")

    assert set(stock["change_role"]) == {"restated_begin"}
    assert balance["ok"] is True


def test_r12_structural_duplicate_equal_amount_stays_leaf_when_exclusion_breaks_balance() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round7(
        [
            ("", "기초자본", "연결재무제표 [member]", "100000"),
            ("", "독립 변동", "연결재무제표 [member]", "10000"),
            ("", "독립 합계", "연결재무제표 [member]", "10000"),
            ("ifrs-full_Equity", "자본총계", "연결재무제표 [member]", "120000"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    duplicate = out[(out["change_label"] == "독립 합계") & (out["component_std"] == "-")]
    balance = sce_balance(out, "CFS")

    assert duplicate["change_role"].tolist() == ["leaf"]
    assert balance["ok"] is True


def test_r12_current_only_stock_vector_requires_matching_disclosed_sign() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round8(
        [
            ("", "기초자본", "연결재무제표 [member]", "100", ""),
            ("", "기초자본", "자본금 [member]", "100", ""),
            ("", "회계정책변경에 따른 증가(감소)", "연결재무제표 [member]", "-100", ""),
            ("", "회계정책변경에 따른 증가(감소)", "자본금 [member]", "-100", ""),
            ("ifrs-full_Equity", "자본총계", "연결재무제표 [member]", "0", ""),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    stock_like = out[out["change_label"] == "회계정책변경에 따른 증가(감소)"]

    assert set(stock_like["change_role"]) == {"leaf"}


def test_r12_stock_vector_wins_when_stock_and_aggregate_signals_overlap() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round7(
        [
            ("", "기초자본", "연결재무제표 [member]", "100"),
            ("", "조정 A", "연결재무제표 [member]", "60"),
            ("", "조정 B", "연결재무제표 [member]", "40"),
            ("", "회계정책변경 합계", "연결재무제표 [member]", "100"),
            ("ifrs-full_Equity", "자본총계", "연결재무제표 [member]", "200"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    overlapping = out[(out["change_label"] == "회계정책변경 합계") & (out["component_std"] == "-")]

    assert overlapping["change_role"].tolist() == ["restated_begin"]


def test_r12_overcollapse_guard_keeps_true_leaf_when_exclusion_breaks_balance() -> None:
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp_map = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = _sce_rows_for_round7(
        [
            ("", "기초자본", "연결재무제표 [member]", "100000"),
            ("", "독립 변동 A", "연결재무제표 [member]", "10000"),
            ("", "독립 변동 B", "연결재무제표 [member]", "20000"),
            ("", "우연 일치 합계", "연결재무제표 [member]", "30000"),
            ("ifrs-full_Equity", "자본총계", "연결재무제표 [member]", "160000"),
        ]
    )

    out = extract_sce_components(raw, mapper, comp_map)
    accidental = out[(out["change_label"] == "우연 일치 합계") & (out["component_std"] == "-")]
    balance = sce_balance(out, "CFS")

    assert accidental["change_role"].tolist() == ["leaf"]
    assert balance["ok"] is True


def test_crossfs_same_label_different_account_id_flags_conflict(tmp_path: Path) -> None:
    raw_dir = tmp_path / "00000000" / "2025" / "raw"
    raw_dir.mkdir(parents=True)
    rows = [
        {
            "corp_code": "00000000",
            "bsns_year": "2025",
            "sj_div": "CF",
            "account_nm": "발행사채의 증가",
            "account_detail": "-",
            "thstrm_amount": "1375000000000",
            "frmtrm_amount": "",
            "bfefrmtrm_amount": "",
            "currency": "KRW",
        }
    ]
    cfs_row = rows[0] | {"fs_div": "CFS", "account_id": "ifrs-full_ProceedsFromIssuingShares"}
    pd.DataFrame([cfs_row]).to_csv(raw_dir / "finstate_all_CFS.csv", index=False)
    pd.DataFrame([rows[0] | {"fs_div": "OFS", "account_id": "dart_ProceedsFromBonds"}]).to_csv(
        raw_dir / "finstate_all_OFS.csv",
        index=False,
    )

    frame = normalize_company_year("00000000", "2025", data_dir=tmp_path)

    flagged = frame[frame["label"] == "발행사채의 증가"].sort_values("fs_div")
    # CFS는 주식발행 id(ifrs-full_ProceedsFromIssuingShares)지만 라벨이 '발행사채의 증가'다.
    # 주식발행 id는 label_priority라 라벨이 채택되어 '사채의 발행'으로 교정된다(과거엔 id 우선해
    # 주식발행으로 오매핑 — 00148504 결함). 교차충돌 플래그(id_label_conflict)는 그대로 유지된다.
    assert flagged["canonical"].tolist() == ["사채의 발행", "사채발행"]
    assert flagged["mapping_status"].tolist() == [ID_LABEL_CONFLICT, ID_LABEL_CONFLICT]


def test_r2_combined_treasury_sign_branches_by_label(tmp_path: Path) -> None:
    # R2(라운드2): 통합 canonical '자기주식변동'은 취득(+신고)·처분(+신고) 양방향이라 무조건 -abs
    # 불가. label로 분기: 취득/소각/감자→-abs, 처분/발행/재발행→+abs(역버그 방지).
    from src.normalize.config import load_canonical_accounts as _l
    from src.normalize.config import load_sce_components
    from src.normalize.pipeline import sce_components_company_year  # noqa: F401 (경로 확인용)
    from src.normalize.sce import extract_sce_components

    comp = load_sce_components(Path("config/canonical_accounts.yaml"))
    mapper = AccountMapper(_l(Path("config/canonical_accounts.yaml")))
    raw = pd.DataFrame(
        [
            {
                "corp_code": "x",
                "bsns_year": "2023",
                "sj_div": "SCE",
                "fs_div": "CFS",
                "account_id": "ifrs-full_PurchaseOfTreasuryShares",
                "account_nm": "자기주식 취득",
                "account_detail": "연결재무제표",
                "thstrm_amount": "571745",
            },
            {
                "corp_code": "x",
                "bsns_year": "2023",
                "sj_div": "SCE",
                "fs_div": "CFS",
                "account_id": "ifrs-full_SaleOfTreasuryShares",
                "account_nm": "자기주식 처분",
                "account_detail": "연결재무제표",
                "thstrm_amount": "300000",
            },
        ]
    )
    out = extract_sce_components(raw, mapper, comp)
    by_label = {r["change_label"]: r["amount"] for _, r in out.iterrows()}
    assert by_label["자기주식 취득"] == -571745.0, "취득은 -abs(차감)"
    assert by_label["자기주식 처분"] == 300000.0, "처분은 +abs 보존(역버그 방지)"


def test_r4_ending_capital_maps_to_total() -> None:
    # R4(라운드2): blank-id '기말자본'이 자본총계로 매핑돼야 SCE total 식별·검산 가능.
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    r = mapper.map_row(pd.Series({"account_id": "", "account_nm": "기말자본"}))
    assert r.canonical == "자본총계"
    from src.normalize.config import load_sce_components

    comp = load_sce_components(Path("config/canonical_accounts.yaml"))
    assert comp.classify_change_role("자본총계", "기말자본") == "total"


def test_r3_leafless_subtotal_adopted_as_leaf() -> None:
    # R3(라운드2): subtotal의 bare leaf 자식이 없으면(구성 leaf가 CIS에만 공시) 그 subtotal을
    # leaf로 채택해야 검산이 맞는다. 자식이 있으면 제외(D5 무회귀).
    from src.normalize.sce import sce_balance

    # 자식 없는 소계: 기타포괄손익 -296백만만 있고 OCI leaf 부재 → 채택. 00169215/2025 원 단위 재현.
    M = 1_000_000
    leafless = pd.DataFrame(
        [
            ("기초자본", "기초자본", "begin", 41589.88 * M),
            ("당기순이익", "당기순이익(손실)", "leaf", -4132.294 * M),
            ("주식기준보상", "주식기준보상거래", "leaf", 713.397 * M),
            ("기타포괄손익", "기타포괄손익", "subtotal", -296.0425 * M),
            ("자본총계", "자본총계", "total", 37874.94 * M),
        ],
        columns=["change_canonical", "change_label", "change_role", "amount"],
    )
    leafless["fs_div"] = "CFS"
    leafless["component_std"] = "-"
    res = sce_balance(leafless, "CFS")
    assert res["ok"] is True, f"자식 없는 소계 채택 시 검산 OK 기대, diff={res['diff']}"

    # 자식 있는 소계(D5): 기타포괄손익 소계 + OCI leaf 동시 → 소계 제외(무회귀)
    with_children = pd.DataFrame(
        [
            ("기초자본", "기초자본", "begin", 45858.59 * M),
            ("FVOCI적립금변동", "FVOCI 평가이익", "leaf", 9.403 * M),
            ("확정급여재측정손익", "확정급여 재측정", "leaf", 29.418 * M),
            ("당기순이익", "총당기순이익", "leaf", 2554.579 * M),
            ("기타포괄손익", "기타포괄손익", "subtotal", 38.822 * M),
            ("자본총계", "자본총계", "total", 48451.99 * M),
        ],
        columns=["change_canonical", "change_label", "change_role", "amount"],
    )
    with_children["fs_div"] = "CFS"
    with_children["component_std"] = "-"
    res2 = sce_balance(with_children, "CFS")
    assert res2["ok"] is True, f"자식 있는 소계 제외 시 검산 OK 기대, diff={res2['diff']}"


def test_r3b_partial_subtotal_residual_adopted() -> None:
    # R3-b(라운드3): 기타포괄손익 소계 중 일부 leaf만 bare로 공시된 경우
    # 소계 전체가 아니라 미공시 잔여만 leaf 합산에 보정해야 한다.
    from src.normalize.sce import sce_balance

    M = 1_000_000
    df = pd.DataFrame(
        [
            ("기초자본", "기초자본", "begin", 1000.0 * M),
            ("당기순이익", "당기순이익", "leaf", 200.0 * M),
            ("확정급여재측정손익", "확정급여재측정손익", "leaf", -188.0 * M),
            ("기타포괄손익", "기타포괄손익", "subtotal", -183.0 * M),
            ("자본총계", "자본총계", "total", 1017.0 * M),
        ],
        columns=["change_canonical", "change_label", "change_role", "amount"],
    )
    df["fs_div"] = "OFS"
    df["component_std"] = "-"

    res = sce_balance(df, "OFS")

    assert res["ok"] is True, f"부분자식 소계 잔여 보정 후 검산 OK 기대, diff={res['diff']}"
    assert res["adopted_subtotal"] is True
    assert res["adopted_canonicals"] == ["기타포괄손익"]


def test_m1_equity_method_retained_earnings_not_oci_alias() -> None:
    # M1(라운드3): '지분법이익잉여금'은 OCI가 아니라 이익잉여금 실질의 SCE leaf다.
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    result = mapper.map_change_row(pd.Series({"account_id": "", "account_nm": "지분법이익잉여금"}))

    assert result.canonical == "지분법이익잉여금변동"
    assert result.canonical != "지분법기타포괄손익재분류가능"


def _n1c_sce_raw_rows(change_id: str, change_label: str, current: list[float]) -> list[dict]:
    begin_id = "dart_EquityAtBeginningOfPeriod"
    begin_label = "기초자본"
    prior = [900.0, 40.0, 110.0]
    components = ["연결재무제표", "자본금", "이익잉여금"]
    rows = []
    for account_id, label, values in [
        (begin_id, begin_label, current),
        (change_id, change_label, current),
    ]:
        for component, amount, prior_amount in zip(components, values, prior, strict=True):
            rows.append(
                {
                    "corp_code": "x",
                    "bsns_year": "2025",
                    "sj_div": "SCE",
                    "fs_div": "CFS",
                    "account_id": account_id,
                    "account_nm": label,
                    "account_detail": component,
                    "thstrm_amount": str(amount),
                    "frmtrm_amount": str(prior_amount),
                }
            )
    return rows


def test_n1c_vector_identical_stock_retagged_as_restated_begin() -> None:
    # N1-c(라운드4): 변동 concept으로 태깅됐더라도 구성요소 벡터가 begin과 완전 동일하면
    # 수정후 기초 스톡으로 보아 leaf 합산에서 제외해야 한다.
    from src.normalize.config import load_sce_components
    from src.normalize.sce import extract_sce_components

    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp = load_sce_components(Path("config/canonical_accounts.yaml"))
    raw = pd.DataFrame(
        _n1c_sce_raw_rows(
            "dart_IncreaseDecreaseThroughCorrectionsOfErrors",
            "오류수정에 따른 증가(감소)",
            [1000.0, 50.0, 150.0],
        )
    )

    out = extract_sce_components(raw, mapper, comp)
    roles = set(out.loc[out["change_label"] == "오류수정에 따른 증가(감소)", "change_role"])

    assert roles == {"restated_begin"}


def test_n1c_vector_different_correction_kept_as_leaf() -> None:
    # 역버그 가드: begin과 벡터가 다르면 같은 correction concept이라도 진짜 델타로 유지한다.
    from src.normalize.config import load_sce_components
    from src.normalize.sce import extract_sce_components

    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
    comp = load_sce_components(Path("config/canonical_accounts.yaml"))
    rows = _n1c_sce_raw_rows(
        "dart_IncreaseDecreaseThroughCorrectionsOfErrors",
        "오류수정에 따른 증가(감소)",
        [1000.0, 50.0, 150.0],
    )
    rows[-1]["thstrm_amount"] = "155.0"
    raw = pd.DataFrame(rows)

    out = extract_sce_components(raw, mapper, comp)
    roles = set(out.loc[out["change_label"] == "오류수정에 따른 증가(감소)", "change_role"])

    assert roles == {"leaf"}


def test_blank_account_id_same_label_current_noncurrent_both_survive(tmp_path: Path) -> None:
    # T2: account_id가 placeholder('-표준계정코드 미사용-')인 동명 유동/비유동 행이 dedup 키
    # 충돌로 한쪽이 소실되던 회귀(세토피아 CFS 파생상품부채 945·리스부채 298 증발). placeholder는
    # 식별자가 아니므로 금액으로 서로 다른 line item을 분별해 둘 다 생존해야 한다.
    raw = pd.DataFrame(
        [
            {
                "corp_code": "01091382",
                "bsns_year": "2019",
                "sj_div": "BS",
                "account_id": "-표준계정코드 미사용-",
                "account_nm": "파생상품부채",
                "account_detail": "-",
                "thstrm_amount": "4435767233",  # 유동
            },
            {
                "corp_code": "01091382",
                "bsns_year": "2019",
                "sj_div": "BS",
                "account_id": "-표준계정코드 미사용-",
                "account_nm": "파생상품부채",
                "account_detail": "-",
                "thstrm_amount": "944653799",  # 비유동
            },
            {  # 진짜 정확 중복(동일 금액)은 여전히 1행으로 dedup
                "corp_code": "01091382",
                "bsns_year": "2019",
                "sj_div": "BS",
                "account_id": "-표준계정코드 미사용-",
                "account_nm": "파생상품부채",
                "account_detail": "-",
                "thstrm_amount": "944653799",
            },
        ]
    )
    path = tmp_path / "raw.csv"
    raw.to_csv(path, index=False)
    mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))

    frame = normalize_raw_file(path, "CFS", mapper)

    amounts = sorted(frame[frame["label"] == "파생상품부채"]["amount"].tolist())
    assert amounts == [944653799.0, 4435767233.0], "유동·비유동 둘 다 생존(정확중복만 제거)"
