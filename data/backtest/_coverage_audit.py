"""Deterministic DART coverage audit harness (read-only).

Reuses production functions on real collected data to trace each account's fate
through L0->L1->L2. No code modification, no LLM. Emits JSON for report assembly.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import duckdb
import pandas as pd

from src.signals import universal as U
from src.signals.config import load_l2_config
from src.signals.sanity import exclude_asset_sanity_years

BASE = Path("data/companies")

FRAUD = {
    "00159616": "두산에너빌리티",
    "00409681": "아스트",
    "00118345": "디아이동일",
    "00657783": "모델솔루션",
    "00413046": "셀트리온",
    "01091382": "세토피아",
    "00108649": "티피씨메카트로닉스",
    "00127699": "유네코",
    "01098792": "본느",
    "00480756": "이트론",
    "00526696": "웨이브일렉트로닉스",
    "00141273": "웰바이오텍",
    "00125521": "에스엘",
    "00116426": "이렘",
    "00351454": "더테크놀로지",
    "00163716": "한창",
}
NORMAL = {
    "00164779": "SK하이닉스",
    "00356361": "LG화학",
    "00157070": "한국단자공업",
    "00139083": "아진산업",
    "00100601": "강원에너지",
    "00102432": "계룡건설산업",
    "00148364": "하림지주",
    "00120526": "롯데쇼핑",
    "00164645": "HMM",
    "00176914": "다우기술",
}
SAMSUNG = {"00126380": "삼성전자"}


def collected_years(cc: str) -> list[int]:
    d = BASE / cc
    if not d.exists():
        return []
    return sorted(
        int(p.name)
        for p in d.iterdir()
        if p.is_dir() and p.name.isdigit() and (p / "analysis.duckdb").exists()
    )


def load_all_years(cc: str) -> pd.DataFrame:
    frames = []
    for y in collected_years(cc):
        path = BASE / cc / str(y) / "analysis.duckdb"
        with duckdb.connect(str(path), read_only=True) as con:
            frames.append(con.execute("SELECT * FROM normalized_financials").fetchdf())
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def raw_sjdiv_counts(cc: str) -> dict:
    """Count raw finstate rows per sj_div across collected years (CFS+OFS)."""
    out = {"BS": 0, "IS": 0, "CIS": 0, "CF": 0, "SCE": 0, "_total": 0}
    for y in collected_years(cc):
        for fs in ("CFS", "OFS"):
            p = BASE / cc / str(y) / "raw" / f"finstate_all_{fs}.csv"
            if not p.exists() or p.stat().st_size <= 5:
                continue
            try:
                df = pd.read_csv(p, dtype=str)
            except Exception:
                continue
            if "sj_div" not in df.columns:
                continue
            for k, v in df["sj_div"].value_counts().to_dict().items():
                out[k] = out.get(k, 0) + int(v)
                out["_total"] += int(v)
    return out


def funnel(cc: str, target_year: int) -> dict:
    """Reproduce scan_universal_signals funnel with per-account instrumentation."""
    frame = load_all_years(cc)
    if frame.empty:
        return {"error": "no data"}
    thresholds = load_l2_config()["signal_thresholds"]
    fs_div = U.preferred_fs_div(frame, target_year)
    scoped = U._scan_frame(frame, fs_div)
    scoped = exclude_asset_sanity_years(scoped, thresholds)
    if scoped.empty:
        return {"error": "empty after scan"}
    # normalized-but-dropped statements (CIS/CF/SCE) -- count before BS/IS narrowing
    sjdiv_norm = frame[frame["fs_div"] == fs_div]["sj_div"].value_counts().to_dict()
    scoped = scoped[scoped["sj_div"].isin(["BS", "IS"])].copy()
    if scoped.empty:
        return {"error": "no BS/IS"}
    scoped = U._aggregate_series(scoped)
    scale_frame = scoped.copy()
    floors = U.scale_floors(scale_frame, thresholds, fs_div)
    floor = floors.get(target_year, U._abs_min(thresholds))
    # subtotal universe
    subtotals = U.subtotal_account_names(U.settings.config_dir / "canonical_accounts.yaml")
    in_target = scoped[scoped["year"] == target_year]
    n_subtotal = int(in_target["canonical"].isin(subtotals).sum())
    scoped_ns = U._exclude_subtotal_rows(scoped)
    grp_all = scoped_ns.groupby(["year", "sj_div"])["abs_amount"].transform("sum")
    scoped_ns = scoped_ns.copy()
    scoped_ns["mix_pct"] = scoped_ns["abs_amount"] / grp_all * 100
    grouped = scoped_ns.groupby("scan_key", sort=False)

    yoy_t = float(thresholds.get("yoy_pct_abs", 50))
    mix_t = float(thresholds.get("mix_shift_pp_abs", 5))
    z_t = float(thresholds.get("z_score_abs", 2))

    total = 0
    below_floor = 0
    above_floor = 0
    fired = 0
    no_prior = 0
    short_hist = 0
    below_thresh = 0
    floor_miss_accounts = []
    fired_accounts = []
    fate_rows = []

    for _key, rows in grouped:
        rows = rows.sort_values("year")
        cur = U._row_for_year(rows, target_year)
        if cur is None:
            continue  # account not present in target year -> not in universe
        total += 1
        acct = U._account_name(cur)
        amt = float(cur.amount)
        if abs(amt) < floor:
            below_floor += 1
            floor_miss_accounts.append((acct, amt))
            fate_rows.append(
                {"account": acct, "sj_div": cur.sj_div, "amount": amt, "fate": "floor미달"}
            )
            continue
        above_floor += 1
        prior = U._row_for_year(rows, target_year - 1)
        history = rows[rows["year"] < target_year]["amount"]
        prior_floor = floors.get(target_year - 1, U._abs_min(thresholds))
        sig = []
        # YoY + mix
        if prior is not None and U._valid_yoy_base(cur, prior, prior_floor):
            pa = float(prior.amount)
            if pa and not math.isclose(pa, 0.0):
                yoy = (amt - pa) / abs(pa) * 100
                if abs(yoy) >= yoy_t:
                    sig.append("yoy")
            mix_pp = float(cur.mix_pct) - float(prior.mix_pct)
            if abs(mix_pp) >= mix_t:
                sig.append("mix")
        # z
        if len(history) >= U.MIN_Z_HISTORY:
            std = float(history.std(ddof=0))
            if not math.isclose(std, 0.0):
                z = (amt - float(history.mean())) / std
                cap = float(thresholds.get("universal_z_score_cap", 10))
                z = max(-cap, min(cap, z))
                if abs(z) >= z_t:
                    sig.append("z")
        if sig:
            fired += 1
            fired_accounts.append((acct, ",".join(sig)))
            fate_rows.append(
                {
                    "account": acct,
                    "sj_div": cur.sj_div,
                    "amount": amt,
                    "fate": "신호발생:" + ",".join(sig),
                }
            )
        else:
            # diagnostic reason
            if prior is None:
                no_prior += 1
            if len(history) < U.MIN_Z_HISTORY:
                short_hist += 1
            below_thresh += 1
            reason = "임계미달"
            if prior is None and len(history) < U.MIN_Z_HISTORY:
                reason = "신규+이력부족"
            elif prior is None:
                reason = "신규(YoY불가)"
            elif len(history) < U.MIN_Z_HISTORY:
                reason = "이력부족(z불가)"
            fate_rows.append({"account": acct, "sj_div": cur.sj_div, "amount": amt, "fate": reason})

    return {
        "corp_code": cc,
        "target_year": target_year,
        "fs_div_used": fs_div,
        "floor": floor,
        "sjdiv_norm_in_fsdiv": sjdiv_norm,
        "n_subtotal_excluded": n_subtotal,
        "total_accounts": total,
        "below_floor": below_floor,
        "above_floor": above_floor,
        "fired": fired,
        "no_signal": above_floor - fired,
        "diag_no_prior": no_prior,
        "diag_short_hist": short_hist,
        "below_thresh_total": below_thresh,
        "floor_miss_accounts": floor_miss_accounts,
        "fired_accounts": fired_accounts,
        "fate_rows": fate_rows,
    }


if __name__ == "__main__":
    import sys

    cc = sys.argv[1]
    ty = int(sys.argv[2])
    print(json.dumps(funnel(cc, ty), ensure_ascii=False, default=str, indent=2))
