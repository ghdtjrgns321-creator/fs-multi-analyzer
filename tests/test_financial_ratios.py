import pandas as pd

from src.signals.ratios import build_ratio_report


def ratio_frame() -> pd.DataFrame:
    values = {
        "매출": [100.0, 120.0],
        "매출원가": [60.0, 72.0],
        "매출채권": [20.0, 30.0],
        "재고자산": [10.0, 20.0],
        "자산총계": [200.0, 220.0],
        "자본총계": [100.0, 110.0],
        "부채총계": [100.0, 110.0],
        "유동자산": [80.0, 90.0],
        "유동부채": [40.0, 45.0],
        "영업이익": [30.0, 36.0],
        "이자비용": [5.0, 6.0],
        "당기순이익": [20.0, 24.0],
        "영업활동현금흐름": [10.0, 30.0],
    }
    rows = []
    for account, amounts in values.items():
        for year, amount in zip([2022, 2023], amounts, strict=True):
            rows.append({"year": year, "fs_div": "CFS", "canonical": account, "amount": amount})
    return pd.DataFrame(rows)


def value(report: pd.DataFrame, ratio_id: str, year: int) -> float | None:
    row = report[(report["id"] == ratio_id) & (report["year"] == year)].iloc[0]
    return row["value"]


def test_build_ratio_report_returns_golden_values() -> None:
    report = build_ratio_report(ratio_frame(), [2022, 2023])

    assert value(report, "gross_profit_margin", 2023) == 40.0
    assert value(report, "roe", 2023) == 22.86
    assert value(report, "dso", 2023) == 76.04
    assert value(report, "inventory_turnover", 2023) == 4.8
    assert value(report, "dio", 2023) == 76.04
    assert value(report, "current_ratio", 2023) == 2.0
    assert value(report, "interest_coverage", 2023) == 6.0
    assert value(report, "ocf_to_net_income", 2023) == 1.25
    assert value(report, "accruals_ratio", 2023) == -2.86


def test_build_ratio_report_keeps_missing_ratio_explicit() -> None:
    report = build_ratio_report(ratio_frame(), [2023])
    row = report[(report["id"] == "roi") & (report["year"] == 2023)].iloc[0]

    assert row["status"] == "not_computed"
    assert pd.isna(row["value"])
    assert "투자원가" in row["reason"]
