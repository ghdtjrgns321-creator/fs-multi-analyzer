"""Build middle-class industry peer config from DART listed companies."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from config.settings import settings
from src.analysis_tools import load_normalized_financials
from src.collect.opendart import DartCollector
from src.peers.collect import ensure_peer_financials
from src.peers.industry_code import industry_key

CASE_FILES = (
    Path("data/backtest/known_cases_mega.json"),
    Path("data/backtest/known_cases_gap.json"),
)
ALL_KNOWN_CASE_FILES = (
    Path("data/backtest/known_cases.json"),
    Path("data/backtest/known_cases_holdout.json"),
    Path("data/backtest/known_cases_mega.json"),
    Path("data/backtest/known_cases_gap.json"),
    Path("data/backtest/known_cases_random.json"),
)
BUILD_DIR = Path("data/backtest/peer_build")
PROFILE_CACHE = BUILD_DIR / "company_profiles.jsonl"
ASSET_CACHE = BUILD_DIR / "peer_assets.jsonl"
REPORT_PATH = BUILD_DIR / "PEER_BUILD_REPORT.md"
YEARS = (2022, 2023, 2024, 2025)
MAX_PEERS = 10


def main() -> None:
    args = _args()
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    collector = DartCollector()
    corp_codes = _listed_companies(collector)
    known = _known_codes(corp_codes)
    target_codes = _case_codes(CASE_FILES, corp_codes)
    profiles = _profile_cache()
    target_industries = _target_industries(target_codes, profiles, collector)
    candidates = _candidate_profiles(corp_codes, known, target_industries, profiles, collector)
    assets = _asset_cache()
    config = _load_existing_config(args.output)
    summary = []
    for key in sorted(target_industries):
        selected, stats = _select_peers(key, candidates, assets, collector, args.years)
        if selected:
            config["industries"][key] = _industry_config(key, selected)
            _write_yaml(config, args.output)
        summary.append({**stats, "industry_code": key, "selected": len(selected)})
        print(f"{key}: selected {len(selected)} / candidates {stats['candidates']}")
    _write_report(summary, args.output)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=settings.config_dir / "industry_peers.yaml")
    parser.add_argument("--years", nargs="+", type=int, default=list(YEARS))
    return parser.parse_args()


def _load_existing_config(path: Path) -> dict[str, Any]:
    if path.exists():
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    else:
        payload = {}
    payload.setdefault("version", 1)
    payload.setdefault("industries", {})
    return payload


def _write_yaml(payload: dict[str, Any], path: Path) -> None:
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=True),
        encoding="utf-8",
    )


def _listed_companies(collector: DartCollector) -> pd.DataFrame:
    frame = collector._dart.corp_codes.copy()  # noqa: SLF001
    stock = frame["stock_code"].fillna("").astype(str).str.strip()
    return frame[stock.str.fullmatch(r"\d{6}")].copy()


def _known_codes(corp_codes: pd.DataFrame) -> set[str]:
    cases = _load_cases(ALL_KNOWN_CASE_FILES)
    stock_lookup = _stock_lookup(corp_codes)
    known = set()
    for case in cases:
        corp = str(case.get("corp_code") or "").strip()
        if not corp and case.get("stock_code"):
            corp = stock_lookup.get(str(case["stock_code"]).zfill(6), "")
        if corp:
            known.add(corp)
    return known


def _case_codes(paths: tuple[Path, ...], corp_codes: pd.DataFrame) -> set[str]:
    stock_lookup = _stock_lookup(corp_codes)
    result = set()
    for case in _load_cases(paths):
        corp = str(case.get("corp_code") or "").strip()
        if not corp and case.get("stock_code"):
            corp = stock_lookup.get(str(case["stock_code"]).zfill(6), "")
        if corp:
            result.add(corp)
    return result


def _load_cases(paths: tuple[Path, ...]) -> list[dict[str, Any]]:
    cases = []
    for path in paths:
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        cases.extend(payload.get("cases", payload if isinstance(payload, list) else []))
    return cases


def _stock_lookup(corp_codes: pd.DataFrame) -> dict[str, str]:
    return {
        str(row.stock_code).zfill(6): str(row.corp_code)
        for row in corp_codes.itertuples()
        if str(row.stock_code).strip()
    }


def _profile_cache() -> dict[str, dict[str, Any]]:
    return _jsonl_cache(PROFILE_CACHE)


def _asset_cache() -> dict[str, dict[str, Any]]:
    return _jsonl_cache(ASSET_CACHE)


def _jsonl_cache(path: Path) -> dict[str, dict[str, Any]]:
    rows = {}
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows[str(row["corp_code"])] = row
    return rows


def _profile(
    corp_code: str,
    cache: dict[str, dict[str, Any]],
    collector: DartCollector,
) -> dict[str, Any]:
    if corp_code in cache:
        return cache[corp_code]
    profile = dict(collector.company(corp_code))
    profile["corp_code"] = corp_code
    _append_jsonl(PROFILE_CACHE, profile)
    cache[corp_code] = profile
    time.sleep(0.05)
    return profile


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")


def _target_industries(
    corp_codes: set[str],
    profiles: dict[str, dict[str, Any]],
    collector: DartCollector,
) -> set[str]:
    keys = set()
    for corp_code in sorted(corp_codes):
        key = industry_key(_profile(corp_code, profiles, collector).get("induty_code"))
        if key:
            keys.add(key)
    return keys


def _candidate_profiles(
    corp_codes: pd.DataFrame,
    known: set[str],
    target_industries: set[str],
    profiles: dict[str, dict[str, Any]],
    collector: DartCollector,
) -> list[dict[str, Any]]:
    candidates = []
    for row in corp_codes.sort_values("stock_code").itertuples():
        corp_code = str(row.corp_code)
        if corp_code in known:
            continue
        try:
            profile = _profile(corp_code, profiles, collector)
        except Exception as exc:
            print(f"profile skip {corp_code}: {type(exc).__name__}")
            continue
        key = industry_key(profile.get("induty_code"))
        if key in target_industries:
            candidates.append(
                {
                    "corp_code": corp_code,
                    "company_name": str(profile.get("stock_name") or row.corp_name),
                    "stock_code": str(row.stock_code).zfill(6),
                    "industry_code": key,
                    "raw_induty_code": str(profile.get("induty_code", "")),
                }
            )
    return candidates


def _select_peers(
    industry: str,
    candidates: list[dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    collector: DartCollector,
    years: list[int],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    scoped = [row for row in candidates if row["industry_code"] == industry]
    ranked = _ranked_with_cached_assets(scoped, assets)
    needed = min(MAX_PEERS, len(scoped))
    for row in _probe_order(scoped):
        if len(ranked) >= needed:
            break
        if row["corp_code"] in {item["corp_code"] for item in ranked}:
            continue
        asset = _asset(row["corp_code"], assets, collector, years)
        if asset is not None:
            ranked.append({**row, "asset_total": asset})
    ranked = sorted(ranked, key=lambda item: (float(item["asset_total"]), item["stock_code"]))
    selected = _quantile_pick(ranked, MAX_PEERS)
    for row in selected:
        try:
            ensure_peer_financials(row["corp_code"], years, collector=collector)
        except Exception as exc:
            print(f"peer collect warning {row['corp_code']}: {type(exc).__name__}: {exc}")
    return selected, {"candidates": len(scoped), "asset_ranked": len(ranked)}


def _ranked_with_cached_assets(
    candidates: list[dict[str, Any]],
    assets: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    ranked = []
    for row in candidates:
        value = assets.get(row["corp_code"], {}).get("asset_total")
        if value is not None:
            ranked.append({**row, "asset_total": float(value)})
    return ranked


def _probe_order(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(candidates, key=lambda item: item["stock_code"])
    if len(ordered) <= MAX_PEERS:
        return ordered
    indexes = _probe_indexes(len(ordered), min(len(ordered), MAX_PEERS * 4))
    picked = [ordered[index] for index in indexes]
    picked_codes = {row["corp_code"] for row in picked}
    return [*picked, *[row for row in ordered if row["corp_code"] not in picked_codes]]


def _probe_indexes(total: int, count: int) -> list[int]:
    return sorted({round(index * (total - 1) / (count - 1)) for index in range(count)})


def _asset(
    corp_code: str,
    cache: dict[str, dict[str, Any]],
    collector: DartCollector,
    years: list[int],
) -> float | None:
    if corp_code in cache:
        value = cache[corp_code].get("asset_total")
        return float(value) if value is not None else None
    for year in sorted(years, reverse=True):
        try:
            ensure_peer_financials(corp_code, [year], collector=collector)
            frame = load_normalized_financials(corp_code, [year])
            value = _asset_from_frame(frame, year)
            if value is not None:
                row = {"corp_code": corp_code, "year": year, "asset_total": value}
                _append_jsonl(ASSET_CACHE, row)
                cache[corp_code] = row
                return value
        except Exception as exc:
            print(f"asset skip {corp_code} {year}: {type(exc).__name__}")
    _append_jsonl(ASSET_CACHE, {"corp_code": corp_code, "year": None, "asset_total": None})
    cache[corp_code] = {"corp_code": corp_code, "asset_total": None}
    return None


def _asset_from_frame(frame: pd.DataFrame, year: int) -> float | None:
    scoped = frame[(frame["year"].astype(int) == int(year)) & (frame["canonical"] == "자산총계")]
    if scoped.empty:
        return None
    for fs_div in ("CFS", "OFS"):
        rows = scoped[scoped["fs_div"] == fs_div]
        if not rows.empty:
            return float(rows.iloc[0]["amount"])
    return float(scoped.iloc[0]["amount"])


def _quantile_pick(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    if len(rows) <= count:
        return rows
    indexes = {round(index * (len(rows) - 1) / (count - 1)) for index in range(count)}
    return [rows[index] for index in sorted(indexes)]


def _industry_config(industry: str, peers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "selection": {
            "source": "OpenDART company profile induty_code",
            "rule": "middle_class_induty_code_asset_quantile_peers",
            "industry_key_length": 3,
            "max_peers": MAX_PEERS,
        },
        "caveat": "대상 회사의 사업구조가 피어와 달라 단순 비교에 한계가 있다.",
        "peers": [
            {
                "corp_code": row["corp_code"],
                "company_name": row["company_name"],
                "stock_code": row["stock_code"],
                "industry_code": industry,
            }
            for row in peers
        ],
    }


def _write_report(summary: list[dict[str, int]], output: Path) -> None:
    short = [row for row in summary if row["selected"] < MAX_PEERS]
    lines = [
        "# PEER_BUILD_REPORT",
        "",
        f"- config: `{output}`",
        f"- 업종 수: {len(summary)}",
        f"- 피어 수: {sum(row['selected'] for row in summary)}",
        f"- 10개 미만 업종 수: {len(short)}",
        "",
        "| 중분류 | 후보 | 자산확인 | 피어 |",
        "|---|---:|---:|---:|",
    ]
    for row in sorted(summary, key=lambda item: item["industry_code"]):
        lines.append(
            f"| {row['industry_code']} | {row['candidates']} | "
            f"{row['asset_ranked']} | {row['selected']} |"
        )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
