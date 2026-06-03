"""L4 multi-agent report orchestration: independent views -> cross-check."""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

from src.agents.gemini_retry import DEFAULT_RETRY_DELAYS
from src.report.company_report import build_company_report, render_markdown
from src.report.crosscheck import CrossCheckResult, cross_check_assessments
from src.report.external import create_external_assessment, external_material
from src.report.industry import create_industry_assessment, industry_material
from src.report.integrated import payload_for_summary
from src.report.materials import change_material, flow_material, note_material, numeric_material
from src.report.perspectives import (
    LLM_TIMEOUT_SECONDS,
    PerspectiveAssessment,
    create_perspective_assessment,
    deferred_assessment,
)
from src.report.synthesis import create_integrated_summary


async def build_multi_agent_report(
    run_llm: bool = True,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> dict[str, object]:
    """Build deterministic queue, independent assessments, cross-check, and synthesis."""

    report = build_company_report()
    assessments = await _assess(report, run_llm, retry_delays)
    cross = cross_check_assessments(assessments)
    summary = None
    if run_llm and any(item.status == "completed" for item in assessments):
        summary_payload = payload_for_summary_items(report, assessments, cross)
        try:
            summary = await asyncio.wait_for(
                create_integrated_summary(summary_payload, retry_delays=retry_delays),
                timeout=LLM_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            summary = f"LLM 종합 문단은 보류했다: {type(exc).__name__}"
    return {
        **report,
        "perspective_assessments": [item.model_dump(mode="json") for item in assessments],
        "cross_check": [item.model_dump(mode="json") for item in cross],
        "summary": summary,
        "materials": {
            "numeric": numeric_material(report),
            "note": _note_material(report),
            "flow": flow_material(report),
            "change": change_material(report),
            "external": external_material(report),
            "industry": _industry_material(report) if run_llm else _deferred_material(),
        },
    }


def payload_for_summary_items(
    report: dict[str, object],
    assessments: list[PerspectiveAssessment],
    cross: list[CrossCheckResult],
) -> dict[str, object]:
    """Prepare grounded synthesis payload with cross-check results."""

    payload = payload_for_summary(
        [],
        report["ratio_summary"],  # type: ignore[arg-type]
    )
    payload["review_queue"] = report["review_queue"][:8]
    payload["perspective_assessments"] = [item.model_dump(mode="json") for item in assessments]
    payload["cross_check"] = [item.model_dump(mode="json") for item in cross]
    return payload


def render_multi_agent_markdown(result: dict[str, Any]) -> str:
    """Render full L4 multi-agent report."""

    text = render_markdown(result, result.get("summary"))
    lines = [text, "", "## 관점별 독립 평가"]
    for item in result["perspective_assessments"]:
        areas = ", ".join(item["risk_areas"]) or "-"
        evidence = "; ".join(item.get("evidence", []))
        suffix = f" evidence: {evidence}" if item["perspective"] == "external" and evidence else ""
        lines.append(
            f"- {item['perspective']} / {item['status']} / {item['risk_level']}: "
            f"{item['summary']} (risk_area: {areas}){suffix}"
        )
    lines.extend(["", "## 일치/충돌"])
    for item in result["cross_check"]:
        lines.append(
            f"- {item['verdict']} / {item['risk_area']}: {item['comment']} "
            f"({', '.join(item['perspectives'])})"
        )
    return "\n".join(lines)


async def _assess(
    report: dict[str, object],
    run_llm: bool,
    retry_delays: tuple[float, ...],
) -> list[PerspectiveAssessment]:
    if not run_llm:
        return [
            deferred_assessment("numeric", "LLM 실행을 생략했다."),
            deferred_assessment("note", "LLM 실행을 생략했다."),
            deferred_assessment("flow", "LLM 실행을 생략했다."),
            deferred_assessment("change", "LLM 실행을 생략했다."),
            deferred_assessment("external", "LLM 실행을 생략했다."),
            deferred_assessment("industry", "LLM 실행을 생략했다."),
        ]
    return [
        await create_perspective_assessment(
            "numeric",
            numeric_material(report),
            retry_delays=retry_delays,
        ),
        await create_perspective_assessment(
            "note",
            _note_material(report),
            retry_delays=retry_delays,
        ),
        await create_perspective_assessment(
            "flow",
            flow_material(report),
            retry_delays=retry_delays,
        ),
        await create_perspective_assessment(
            "change",
            change_material(report),
            retry_delays=retry_delays,
        ),
        await create_external_assessment(report, retry_delays=retry_delays),
        await create_industry_assessment(report, retry_delays=retry_delays),
    ]


def _note_material(report: dict[str, object]) -> dict[str, object]:
    return note_material(year=int(report["target_year"]))


def _industry_material(report: dict[str, object]) -> dict[str, object]:
    try:
        return industry_material(report)
    except Exception as exc:
        return {"status": "deferred", "reason": str(exc) or exc.__class__.__name__}


def _deferred_material() -> dict[str, object]:
    return {"status": "deferred", "reason": "LLM/peer benchmark 실행을 생략했다."}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(build_multi_agent_report(run_llm=not args.no_llm))
    print(render_multi_agent_markdown(result))


if __name__ == "__main__":
    main()
