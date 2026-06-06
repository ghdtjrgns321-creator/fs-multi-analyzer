"""Build the company-level L4 integrated report payload."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.analysis_tools import load_normalized_financials
from src.collect.opendart import DartCollector
from src.report.integrated import (
    build_review_queue,
    payload_for_summary,
    summarize_ratio_categories,
)
from src.schemas.findings import AccountFinding
from src.signals.mvp1 import build_mvp1_signal_report
from src.signals.ratios import build_ratio_report, load_ratio_config
from src.signals.red_flags import extract_red_flags
from src.signals.universal import scan_cfs_ofs_gaps, scan_universal_signals

DEFAULT_CORP_CODE = "00126380"
DEFAULT_YEARS = [2022, 2023, 2024, 2025]


def build_company_report(
    corp_code: str = DEFAULT_CORP_CODE,
    years: list[int] | None = None,
    finding_report_path: Path | None = None,
    company_provider: Any | None = None,
) -> dict[str, object]:
    """Assemble deterministic L4 report inputs for one company."""

    target_years = years or DEFAULT_YEARS
    target_year = max(target_years)
    frame = load_normalized_financials(corp_code, target_years)
    company_profile = _company_profile(corp_code, company_provider)
    signal_report = build_mvp1_signal_report(frame, years=target_years)
    red_flags = extract_red_flags(signal_report, target_year)
    universal_signals = scan_universal_signals(frame, target_year)
    cfs_ofs_signals = scan_cfs_ofs_gaps(frame, target_year)
    ratios = build_ratio_report(frame, target_years)
    ratio_config = load_ratio_config()
    unmapped = _top_unmapped_material_accounts(frame, target_year)
    findings = _target_year_findings(
        load_findings_from_report(finding_report_path or Path("docs/agent/FINDING_REPORT.md")),
        target_year,
    )
    all_signals = red_flags + universal_signals + cfs_ofs_signals
    queue = build_review_queue(findings, ratios, ratio_config, target_year, all_signals, unmapped)
    ratio_summary = summarize_ratio_categories(ratios, target_year)
    payload = payload_for_summary(queue, ratio_summary)
    latest_snapshot = _latest_signal_snapshot(signal_report, target_year)
    latest_snapshot["universal_scan"] = _signal_rows(universal_signals)
    latest_snapshot["cfs_ofs_gaps"] = _signal_rows(cfs_ofs_signals)
    return {
        "corp_code": corp_code,
        "company_name": _company_name(company_profile, corp_code),
        "business_domain": company_profile,
        "years": target_years,
        "target_year": target_year,
        "review_queue": [item.to_dict() for item in queue],
        "ratio_summary": ratio_summary,
        "ratio_time_series": _ratio_time_series(ratios),
        "account_level_series": _account_level_series(frame, target_years, target_year),
        "latest_signal_snapshot": latest_snapshot,
        "unmapped_material_accounts": unmapped,
        "llm_payload": payload,
    }


def _company_profile(corp_code: str, company_provider: Any | None = None) -> dict[str, object]:
    provider = company_provider
    if provider is None:
        try:
            provider = DartCollector().company
        except Exception:
            return {"source": "OpenDART company profile unavailable", "corp_code": corp_code}
    try:
        profile = dict(provider(corp_code))
    except Exception:
        return {"source": "OpenDART company profile unavailable", "corp_code": corp_code}
    profile.setdefault("source", "OpenDART company profile")
    return profile


def _company_name(profile: dict[str, object], corp_code: str) -> str:
    for key in ("stock_name", "corp_name", "corp_name_eng"):
        value = str(profile.get(key, "")).strip()
        if value:
            return value
    return corp_code


def _latest_signal_snapshot(report: dict[str, object], target_year: int) -> dict[str, object]:
    return {
        "growth_divergences": _rows_for_year(report["growth_divergences"], target_year),
        "direction_checks": _rows_for_year(report["direction_checks"], target_year),
        "primary_yoy": _rows_for_year(report["primary_yoy"], target_year),
        "reference_yoy": _rows_for_year(report["reference_yoy"], target_year),
    }


def _rows_for_year(frame: Any, target_year: int) -> list[dict[str, object]]:
    if not hasattr(frame, "to_dict"):
        return []
    latest = frame[frame["year"] == target_year]
    return latest.to_dict(orient="records")


def _signal_rows(signals: list[Any]) -> list[dict[str, object]]:
    return [
        {
            "id": signal.id,
            "year": signal.year,
            "account": signal.account,
            "signal_type": signal.signal_type,
            "description": signal.description,
            "metric_value": signal.metric_value,
            "evidence": [item.model_dump(mode="json") for item in signal.evidence],
        }
        for signal in signals
    ]


def _ratio_time_series(ratios: Any) -> list[dict[str, object]]:
    if not hasattr(ratios, "to_dict") or ratios.empty:
        return []
    scoped = ratios[ratios["status"] == "computed"].copy()
    scoped = scoped.sort_values(["category", "id", "year"])
    return scoped[["id", "category", "name", "year", "value", "basis"]].to_dict("records")


def _account_level_series(
    frame: Any,
    years: list[int],
    target_year: int,
    limit: int = 40,
) -> list[dict[str, object]]:
    if not hasattr(frame, "to_dict") or frame.empty:
        return []
    fs_div = _primary_fs_div(frame, target_year)
    scoped = frame[(frame["fs_div"] == fs_div) & (frame["sj_div"].isin(["BS", "IS", "CF"]))].copy()
    if scoped.empty:
        return []
    scoped["series_key"] = scoped["canonical"].where(
        scoped["canonical"].notna() & (scoped["canonical"] != ""),
        scoped["label"],
    )
    latest = scoped[scoped["year"].astype(int) == int(target_year)].copy()
    latest["abs_amount"] = latest["amount"].abs()
    keys = latest.sort_values("abs_amount", ascending=False)["series_key"].dropna().head(limit)
    result = scoped[
        (scoped["series_key"].isin(keys))
        & (scoped["year"].astype(int).isin([int(year) for year in years]))
    ].copy()
    result = result.sort_values(["sj_div", "series_key", "year"])
    return result[
        ["year", "fs_div", "sj_div", "series_key", "canonical", "label", "amount", "mapping_status"]
    ].to_dict("records")


def _primary_fs_div(frame: Any, target_year: int) -> str:
    latest = frame[frame["year"].astype(int) == int(target_year)]
    return "CFS" if (latest["fs_div"] == "CFS").any() else "OFS"


def _top_unmapped_material_accounts(frame: Any, target_year: int) -> list[dict[str, object]]:
    if not hasattr(frame, "to_dict"):
        return []
    scoped = frame[
        (frame["year"].astype(str) == str(target_year))
        & (frame["fs_div"] == "CFS")
        & (frame["mapping_status"] == "unmapped_extension_account")
    ].copy()
    if scoped.empty:
        return []
    scoped["abs_amount"] = scoped["amount"].abs()
    scoped = scoped[scoped["abs_amount"] > 0].sort_values("abs_amount", ascending=False)
    return scoped[["year", "fs_div", "label", "account_id", "amount"]].head(5).to_dict("records")


def load_findings_from_report(path: Path) -> list[AccountFinding]:
    """Load AccountFinding JSON blocks from an existing markdown report."""

    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    findings = []
    for block in re.findall(r"```json\s*(\{.*?\})\s*```", text, flags=re.S):
        try:
            findings.append(AccountFinding.model_validate(json.loads(block)))
        except Exception:
            continue
    return findings


def _target_year_findings(findings: list[AccountFinding], target_year: int) -> list[AccountFinding]:
    latest = []
    for finding in findings:
        evidence = finding.numeric_evidence + finding.note_evidence + finding.flow_evidence
        if any(item.year == str(target_year) for item in evidence):
            latest.append(finding)
    return latest


def render_markdown(report: dict[str, Any], summary: str | None = None) -> str:
    """Render the deterministic report for CLI/docs."""

    lines = ["# INTEGRATED_REPORT — L4 통합 리포트", ""]
    lines.append("## 검토 우선순위 큐")
    lines.append("| 순위 | 대상 | 유형 | risk | score | 핵심 근거 | 근거 | 출처 |")
    lines.append("|---:|---|---|---|---:|---|---|---|")
    for idx, item in enumerate(report["review_queue"][:10], start=1):
        basis = ", ".join(item["audit_basis"])
        source = item.get("source_url") or "-"
        lines.append(
            f"| {idx} | {item['subject']} | {item['item_type']} | {item['risk_level']} | "
            f"{float(item['materiality_score']):.2f} | {item['key_evidence']} | "
            f"{basis} | {source} |"
        )
    lines.extend(["", "## 회사 전체 지표 요약"])
    for category, values in report["ratio_summary"].items():
        joined = ", ".join(f"{name} {value:.2f}" for name, value in values.items())
        lines.append(f"- {category}: {joined}")
    lines.extend(["", "## 한 단락 종합"])
    lines.append(summary or "LLM 종합 문단은 보류했다.")
    return "\n".join(lines)


def main() -> None:
    report = build_company_report()
    print(render_markdown(report))


if __name__ == "__main__":
    main()
