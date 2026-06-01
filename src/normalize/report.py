"""Measurement helpers for the L1 normalization spike."""

from __future__ import annotations

import pandas as pd

from src.normalize.mapper import ALIAS

MVP_CANONICALS = [
    "현금및현금성자산",
    "단기금융상품",
    "매출채권",
    "재고자산",
    "유동부채",
    "매입채무",
    "단기차입금",
    "매출",
    "매출원가",
    "영업활동현금흐름",
]


def status_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    """Return mapping_status counts and ratios by year/fs_div."""

    grouped = frame.groupby(["year", "fs_div", "mapping_status"]).size().reset_index(name="rows")
    totals = grouped.groupby(["year", "fs_div"])["rows"].transform("sum")
    grouped["ratio"] = (grouped["rows"] / totals).round(4)
    return grouped


def rescued_unused_2022_cfs(frame: pd.DataFrame) -> dict[str, float]:
    """Measure alias rescue for 2022 CFS rows without standard account ID."""

    target = frame[
        (frame["year"].astype(str) == "2022")
        & (frame["fs_div"] == "CFS")
        & (frame["account_id"] == "-표준계정코드 미사용-")
    ]
    rescued = target[target["mapping_status"] == ALIAS]
    ratio = 0.0 if target.empty else round(len(rescued) / len(target), 4)
    return {"total": float(len(target)), "rescued": float(len(rescued)), "ratio": ratio}


def mvp_consistency(frame: pd.DataFrame) -> pd.DataFrame:
    """Check whether each MVP canonical appears for each year/fs_div."""

    mvp = frame[frame["canonical"].isin(MVP_CANONICALS)]
    pivot = (
        mvp.groupby(["canonical", "year", "fs_div"])
        .size()
        .unstack(["year", "fs_div"], fill_value=0)
    )
    return pivot.reindex(MVP_CANONICALS).fillna(0).astype(int)


def label_required_cases(frame: pd.DataFrame) -> pd.DataFrame:
    """List rows where account_id alone was insufficient and alias mapping was used."""

    cols = ["year", "fs_div", "sj_div", "canonical", "label", "account_id", "amount"]
    return frame[frame["mapping_status"] == ALIAS][cols].drop_duplicates()


def build_report(frames: list[pd.DataFrame]) -> dict[str, object]:
    frame = pd.concat(frames, ignore_index=True)
    return {
        "status_distribution": status_distribution(frame),
        "rescued_unused_2022_cfs": rescued_unused_2022_cfs(frame),
        "mvp_consistency": mvp_consistency(frame),
        "label_required_cases": label_required_cases(frame),
    }
