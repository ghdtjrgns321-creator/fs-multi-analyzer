"""Build the company-level L4 integrated report payload."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.analysis_tools import load_normalized_financials
from src.report.integrated import (
    build_review_queue,
    payload_for_summary,
    summarize_ratio_categories,
)
from src.schemas.findings import AccountFinding
from src.signals.mvp1 import build_mvp1_signal_report
from src.signals.ratios import build_ratio_report, load_ratio_config
from src.signals.red_flags import extract_red_flags

DEFAULT_CORP_CODE = "00126380"
DEFAULT_YEARS = [2022, 2023, 2024]


def build_company_report(
    corp_code: str = DEFAULT_CORP_CODE,
    years: list[int] | None = None,
    finding_report_path: Path | None = None,
) -> dict[str, object]:
    """Assemble deterministic L4 report inputs for one company."""

    target_years = years or DEFAULT_YEARS
    target_year = max(target_years)
    frame = load_normalized_financials(corp_code, target_years)
    signal_report = build_mvp1_signal_report(frame)
    red_flags = [
        signal
        for year in target_years[1:]
        for signal in extract_red_flags(signal_report, int(year))
    ]
    ratios = build_ratio_report(frame, target_years)
    ratio_config = load_ratio_config()
    findings = load_findings_from_report(
        finding_report_path or Path("docs/agent/FINDING_REPORT.md")
    )
    queue = build_review_queue(findings, ratios, ratio_config, target_year, red_flags)
    ratio_summary = summarize_ratio_categories(ratios, target_year)
    payload = payload_for_summary(queue, ratio_summary)
    return {
        "corp_code": corp_code,
        "years": target_years,
        "target_year": target_year,
        "review_queue": [item.to_dict() for item in queue],
        "ratio_summary": ratio_summary,
        "llm_payload": payload,
    }


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
