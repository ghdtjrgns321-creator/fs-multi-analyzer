"""①② 별도(OFS) 비율 표면화 — ratio_time_series가 fs_div별로 계산·태그되는지.

측정상 OFS 비율은 완전 산출가능한데 company_report가 CFS만 냈다. fs_div별로 계산해 태그하면
관점이 "연결 유동비율 vs 별도 유동비율"을 구분해서 본다. ratio_fn 주입으로 실 엔진 없이 검증.
"""

from __future__ import annotations

import pandas as pd

from src.report.company_report import _ratio_time_series


def _fake_ratio_fn(computable_fs: set[str]):
    def fn(frame, years, config_path=None, fs_div="CFS"):
        if fs_div not in computable_fs:
            return pd.DataFrame(
                columns=["id", "category", "name", "year", "value", "status", "basis"]
            )
        return pd.DataFrame(
            [
                {
                    "id": "current_ratio",
                    "category": "liquidity",
                    "name": "유동비율",
                    "year": 2024,
                    "value": 2.0 if fs_div == "CFS" else 1.03,
                    "status": "computed",
                    "basis": "x",
                }
            ]
        )

    return fn


def test_both_fs_div_tagged() -> None:
    ts = _ratio_time_series(None, [2024], ["CFS", "OFS"], ratio_fn=_fake_ratio_fn({"CFS", "OFS"}))
    fs_set = {r["fs_div"] for r in ts}
    assert fs_set == {"CFS", "OFS"}
    # 같은 유동비율이 fs_div로 구분돼 값이 다르게 실린다
    by_fs = {r["fs_div"]: r["value"] for r in ts}
    assert by_fs["CFS"] == 2.0
    assert by_fs["OFS"] == 1.03


def test_ofs_absent_keeps_cfs_only() -> None:
    ts = _ratio_time_series(None, [2024], ["CFS", "OFS"], ratio_fn=_fake_ratio_fn({"CFS"}))
    assert {r["fs_div"] for r in ts} == {"CFS"}
