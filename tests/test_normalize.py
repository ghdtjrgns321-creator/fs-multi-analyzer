from pathlib import Path

import pandas as pd

from src.normalize.config import load_canonical_accounts
from src.normalize.mapper import ALIAS, EXACT, UNMAPPED, AccountMapper
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
    ]

    for account_id, expected in cases:
        result = mapper.map_row(pd.Series({"account_id": account_id, "account_nm": "unused"}))
        assert result.canonical == expected
        assert result.mapping_status == EXACT


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
