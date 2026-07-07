"""Layer 1 오케스트레이터 — 서술 파트별 리더 실행 → 저장 → 완결성 경고. 설계 §4·§7·§10.

파트를 순회하며 서술 리더(reader_focus 있는 파트)만 run_reader로 추출하고(III=재무 결정론·XII=제외는
자연 스킵), 추출물을 report_extracts에 저장한 뒤 완결성 3앵커로 누락 의심을 경고한다. 재무 결정론(Phase1)
산출물은 이미 별도 파이프라인이 만들므로 여기서 재계산하지 않는다(계산=코드, 참조만). 무키·오류는 graceful.
"""

from __future__ import annotations

from pathlib import Path

from src.notes.report_parts import ReportPart
from src.report.completeness import completeness_warnings
from src.report.reader import run_reader
from src.report.reader_assign import reader_focus


def load_report_parts(corp_code: str, year: str | int) -> tuple[list[ReportPart], str]:
    """DART 원문에서 PART 리스트 로드(review_chunks 경로 동일). 실패는 빈 리스트+사유."""

    from src.collect.opendart import DartCollector
    from src.notes.report_parts import extract_parts

    try:
        collector = DartCollector()
        report = collector.annual_report(corp_code, int(year))
        if report is None:
            return [], "사업보고서 원문 미제공"
        return extract_parts(collector.document(report.rcept_no)), ""
    except Exception as exc:  # noqa: BLE001
        return [], f"{type(exc).__name__}: {exc}"


def run_layer1(
    corp_code: str,
    year: str | int,
    parts: list[ReportPart] | None = None,
    data_dir: Path | None = None,
    model_name: str | None = None,
) -> dict:
    """서술 파트 전부 리더 실행 → report_extracts 저장 → 완결성 경고.

    반환: {status, extracts:list[ExtractedItem], warnings, usage, per_part, message}.
    parts 미지정 시 DART에서 로드. 재무(III)·제외(XII)는 reader_focus None이라 자연 스킵.
    """

    from src.db.normalized import write_report_extracts

    if parts is None:
        parts, message = load_report_parts(corp_code, year)
        if not parts:
            return {
                "status": "absent",
                "extracts": [],
                "warnings": [],
                "usage": {},
                "message": message,
            }

    items = []
    per_part: list[dict] = []
    in_tok = out_tok = 0
    for part in parts:
        focus = reader_focus(part.numeral)
        if focus is None:  # III(재무 결정론)·XII(제외) — 서술 리더 미배정
            continue
        result = run_reader(part, focus, model_name=model_name)
        status = result["status"]
        if status == "ok" and result["output"] is not None:
            items.extend(result["output"].items)
            usage = result.get("usage", {})
            in_tok += usage.get("input_tokens", 0)
            out_tok += usage.get("output_tokens", 0)
        per_part.append(
            {"part": part.numeral, "status": status, "message": result.get("message", "")}
        )

    write_report_extracts(items, corp_code, year, data_dir=data_dir)
    warnings = completeness_warnings(parts, items)

    return {
        "status": "ok",
        "extracts": items,
        "warnings": warnings,
        "usage": {"input_tokens": in_tok, "output_tokens": out_tok},
        "per_part": per_part,
        "message": "",
    }
