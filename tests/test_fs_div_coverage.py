"""파생층 fs_div 커버리지 원장(③) — CFS-고정 누락 전수 포착.

raw 계정층은 CFS+OFS 열렸는데 파생층(비율)이 CFS 고정으로 빠진 걸 음의공간 대조로 잡는다.
"fs_div에 계정 있고 비율 산출 가능한데 미표면화" = gap.
"""

from __future__ import annotations

import pandas as pd

from src.report.coverage import build_fs_div_coverage


def _frame() -> pd.DataFrame:
    rows = []
    for fs in ("CFS", "OFS"):
        for canon, amt in (("유동자산", 100.0), ("유동부채", 50.0)):
            rows.append(
                {"year": 2024, "fs_div": fs, "sj_div": "BS", "canonical": canon, "amount": amt}
            )
    return pd.DataFrame(rows)


def _account_series() -> list[dict]:
    out = []
    for fs in ("CFS", "OFS"):
        for canon in ("유동자산", "유동부채"):
            out.append(
                {
                    "year": "2024",
                    "fs_div": fs,
                    "sj_div": "BS",
                    "series_key": f"{fs}:{canon}",
                    "amount": 100.0,
                }
            )
    return out


def _fake_ratio_fn(frame, years, fs_div="CFS"):
    # 어느 fs_div든 유동비율 1개 산출된다고 가정(엔진은 fs_div 무관하게 계산 가능).
    return pd.DataFrame([{"id": "current_ratio", "year": 2024, "value": 2.0, "status": "ok"}])


def test_ofs_ratio_gap_detected() -> None:
    # 현재 파이프라인은 CFS 비율만 표면화 → OFS는 계정 있고 산출 가능한데 미표면화 = gap.
    cov = build_fs_div_coverage(
        _frame(),
        _account_series(),
        [2024],
        2024,
        report_ratio_fs_divs={"CFS"},
        ratio_fn=_fake_ratio_fn,
    )
    assert cov["population_fs_div"] == ["CFS", "OFS"]
    assert cov["per_fs_div"]["OFS"]["accounts_n"] == 2
    assert cov["per_fs_div"]["OFS"]["ratios_computable_n"] == 1
    gap_fs = {g["fs_div"] for g in cov["gaps"]}
    assert "OFS" in gap_fs
    assert "CFS" not in gap_fs  # CFS는 표면화됨 → gap 아님


def test_no_gap_when_both_surfaced() -> None:
    cov = build_fs_div_coverage(
        _frame(),
        _account_series(),
        [2024],
        2024,
        report_ratio_fs_divs={"CFS", "OFS"},
        ratio_fn=_fake_ratio_fn,
    )
    assert cov["gaps"] == []
