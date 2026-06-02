import pandas as pd

from src.analysis_tools import compare_growth, compute_ratio
from src.signals.mvp1 import build_mvp1_signal_report


def fixture_frame() -> pd.DataFrame:
    rows = []
    values = {
        "매출": [100.0, 150.0, 120.0],
        "매출채권": [50.0, 55.0, 66.0],
        "재고자산": [20.0, 30.0, 60.0],
        "매출원가": [80.0, 100.0, 110.0],
        "영업활동현금흐름": [10.0, 8.0, 12.0],
    }
    for account, amounts in values.items():
        for year, amount in zip([2022, 2023, 2024], amounts, strict=True):
            rows.append({"year": year, "fs_div": "CFS", "canonical": account, "amount": amount})
    return pd.DataFrame(rows)


def test_compare_growth_returns_golden_divergence() -> None:
    result = compare_growth(fixture_frame(), "매출", "매출채권", [2022, 2023, 2024])

    assert result["growth_a_pct"].tolist() == [50.0, -20.0]
    assert result["growth_b_pct"].tolist() == [10.0, 20.0]
    assert result["divergence_pp"].tolist() == [40.0, -40.0]


def test_compute_ratio_handles_zero_denominator() -> None:
    frame = fixture_frame()
    frame.loc[len(frame)] = {"year": 2024, "fs_div": "CFS", "canonical": "분모", "amount": 0.0}

    result = compute_ratio(frame, "매출", "분모", [2024])

    assert result.iloc[0]["ratio_pct"] is None


def test_signal_report_uses_configured_accounts(tmp_path) -> None:
    config = tmp_path / "chains.yaml"
    config.write_text(
        """
l2_mvp1:
  primary_fs_div: CFS
  reference_fs_div: CFS
  years: [2022, 2023, 2024]
  yoy_accounts: [매출, 매출채권]
  growth_divergences:
    - id: revenue-vs-receivable
      name: 매출 vs 매출채권
      account_a: 매출
      account_b: 매출채권
  direction_checks:
    - id: receivable-vs-cf
      name: 매출채권 vs 영업활동현금흐름
      growth_account: 매출채권
      flow_account: 영업활동현금흐름
  deferred_ratios: []
""",
        encoding="utf-8",
    )

    report = build_mvp1_signal_report(fixture_frame(), config)

    assert report["growth_divergences"]["divergence_pp"].tolist() == [40.0, -40.0]
    assert report["direction_checks"]["direction_same"].tolist() == [False, True]
    assert len(report["primary_yoy"]) == 4
