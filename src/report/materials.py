"""Material board helpers for independent L4 perspectives."""

from __future__ import annotations

from pathlib import Path

from src.notes.indexer import find_account_note_sections, load_account_note_mappings


def numeric_material(report: dict[str, object]) -> dict[str, object]:
    """Inputs for numeric perspective only."""

    return {
        "review_queue_reference": report["review_queue"][:10],
        "ratio_summary": report["ratio_summary"],
        "ratio_time_series": report.get("ratio_time_series", []),
        "account_level_series": report.get("account_level_series", []),
        "latest_signal_snapshot": report.get("latest_signal_snapshot", {}),
        "scope": "numeric perspective only",
        "queue_role": "review_queue_reference는 변화율 중심 참고 후보이며 정답이 아니다.",
    }


def note_material(
    corp_code: str = "00126380",
    year: int = 2024,
    fs_div: str = "CFS",
) -> dict[str, object]:
    """Inputs for note perspective only."""

    notes_root = Path("data/companies") / corp_code / str(year) / "raw" / "notes"
    sections = []
    for account in _note_accounts():
        account_sections = find_account_note_sections(account, notes_root, corp_code, year, fs_div)
        limit = 2 if _priority(account) == "high" else 1
        for section in account_sections[:limit]:
            sections.append(
                {
                    "account": account,
                    "year": year,
                    "fs_div": fs_div,
                    "locator": section.locator,
                    "title": section.title,
                    "matched_keywords": section.matched_keywords,
                    "excerpt": section.text[:350],
                }
            )
    return {"note_sections": sections, "scope": "note perspective only"}


def _note_accounts() -> list[str]:
    mappings = load_account_note_mappings()
    return sorted(
        mappings,
        key=lambda account: (mappings[account].get("analysis_priority") != "high", account),
    )


def _priority(account: str) -> str:
    return str(load_account_note_mappings()[account].get("analysis_priority", "low"))


def flow_material(report: dict[str, object]) -> dict[str, object]:
    """Inputs for BS-IS-CF flow perspective only."""

    flow_keywords = (
        "현금흐름",
        "차입",
        "사채",
        "이자",
        "법인세",
        "순이익",
        "영업이익",
        "투자",
        "유형자산",
        "사업결합",
        "배당",
        "매출채권",
        "재고",
        "매입채무",
    )
    flow_items = [
        item
        for item in report["review_queue"]
        if any(keyword in str(item["subject"]) for keyword in flow_keywords)
        or str(item["subject"]) in {"영업CF/순이익", "발생액 비율"}
        or "growth_divergence" in str(item["key_evidence"])
        or "direction_mismatch" in str(item["key_evidence"])
    ]
    return {
        "flow_queue_reference": flow_items[:10],
        "review_queue_reference": report["review_queue"][:10],
        "latest_signal_snapshot": report.get("latest_signal_snapshot", {}),
        "account_level_series": report.get("account_level_series", []),
        "unmapped_material_accounts": report.get("unmapped_material_accounts", []),
        "ratio_summary": {
            key: value
            for key, value in report["ratio_summary"].items()
            if key in {"활동성", "이익의 질"}
        },
        "ratio_time_series": [
            row
            for row in report.get("ratio_time_series", [])
            if row.get("category") in {"activity", "earnings_quality"}
        ],
        "scope": "flow perspective only",
        "queue_role": "flow_queue_reference는 참고 후보이며, 계정/지표 시계열도 직접 검토한다.",
    }


def change_material(report: dict[str, object]) -> dict[str, object]:
    """Inputs for prior/current change perspective only."""

    change_items = [
        item
        for item in report["review_queue"]
        if "single_account_yoy" in str(item["key_evidence"])
        or "growth_divergence" in str(item["key_evidence"])
    ]
    return {
        "change_queue_reference": change_items[:10],
        "review_queue_reference": report["review_queue"][:10],
        "latest_signal_snapshot": report.get("latest_signal_snapshot", {}),
        "account_level_series": report.get("account_level_series", []),
        "ratio_time_series": report.get("ratio_time_series", []),
        "target_year": report["target_year"],
        "scope": "change perspective only",
        "queue_role": (
            "change_queue_reference는 참고 후보이며, "
            "수준/추세 시계열 전체를 직접 검토한다."
        ),
    }
