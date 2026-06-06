"""Deterministic industry baseline from peer ratios."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from src.analysis_tools import load_normalized_financials
from src.collect.opendart import DartCollector
from src.peers.collect import ensure_peer_financials
from src.peers.config import filter_same_industry, load_peer_config
from src.signals.ratios import build_ratio_report


def build_industry_benchmark(
    corp_code: str,
    years: list[int],
    *,
    peer_config_path: Path | None = None,
    collector: DartCollector | None = None,
    company_profile: dict[str, object] | None = None,
    ensure_data: Callable[..., None] = ensure_peer_financials,
) -> dict[str, object]:
    """Build peer median and target percentile for latest-year ratios."""

    target_year = max(years)
    target_profile = company_profile or _target_profile(corp_code, collector)
    industry_code = str(target_profile.get("induty_code", "")).strip()
    if not industry_code:
        raise RuntimeError("피어 미구성: 대상 회사 induty_code 없음")
    config = load_peer_config(industry_code, peer_config_path)
    provider = collector.company if collector else None
    peers = filter_same_industry(config, provider)
    if not peers:
        raise RuntimeError(f"피어 미구성: industry_code={industry_code}")
    peer_years = sorted({target_year - 1, target_year})
    for peer in peers:
        ensure_data(peer.corp_code, peer_years, collector=collector)
    target_ratios = _ratios(corp_code, years, target_year)
    peer_rows = []
    for peer in peers:
        ratios = _ratios(peer.corp_code, peer_years, target_year)
        peer_rows.extend(
            {**row, "corp_code": peer.corp_code, "company_name": peer.company_name}
            for row in ratios
        )
    return {
        "target_corp_code": corp_code,
        "target_company": _profile_name(target_profile, corp_code),
        "target_year": target_year,
        "industry_code": industry_code,
        "basis": {
            "standard": "ISA/KSA 520",
            "procedure": "industry_comparison",
            "gist": "동종업계 지표 비교는 분석적 절차의 참고 관점이다.",
        },
        "caveat": config.caveat,
        "peers": [peer.model_dump() for peer in peers],
        "baseline": _baseline(target_ratios, peer_rows),
    }


def _target_profile(
    corp_code: str,
    collector: DartCollector | None,
) -> dict[str, object]:
    if collector is None:
        return {"corp_code": corp_code}
    return dict(collector.company(corp_code))


def _profile_name(profile: dict[str, object], corp_code: str) -> str:
    for key in ("stock_name", "corp_name", "corp_name_eng"):
        value = str(profile.get(key, "")).strip()
        if value:
            return value
    return corp_code


def _ratios(corp_code: str, years: list[int], target_year: int) -> list[dict[str, Any]]:
    frame = load_normalized_financials(corp_code, years)
    ratios = build_ratio_report(frame, years)
    latest = ratios[(ratios["year"] == target_year) & (ratios["status"] == "computed")]
    return latest[["id", "category", "name", "value"]].to_dict(orient="records")


def _baseline(
    target_rows: list[dict[str, Any]],
    peer_rows: list[dict[str, Any]],
) -> list[dict[str, object]]:
    rows = []
    peer_frame = pd.DataFrame(peer_rows)
    for target in target_rows:
        values = peer_frame[peer_frame["id"] == target["id"]]
        peer_values = values["value"].dropna().astype(float).tolist()
        if not peer_values:
            continue
        target_value = float(target["value"])
        percentile = sum(value <= target_value for value in peer_values) / len(peer_values) * 100
        rows.append(
            {
                "id": target["id"],
                "category": target["category"],
                "name": target["name"],
                "target_value": round(target_value, 2),
                "peer_median": round(float(pd.Series(peer_values).median()), 2),
                "target_percentile": round(percentile, 1),
                "peer_count": len(peer_values),
                "peer_values": values[["company_name", "value"]].to_dict(orient="records"),
            }
        )
    return rows
