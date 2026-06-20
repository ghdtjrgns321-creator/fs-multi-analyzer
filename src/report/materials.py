"""Material board helpers for independent L4 perspectives."""

from __future__ import annotations

import re
from pathlib import Path

from src.notes.indexer import find_account_note_sections, load_account_note_mappings
from src.report.review_chunks import QUIRKS_PATH, load_content_chunks


def _routed_events(report: dict[str, object], perspective: str) -> list[dict]:
    """S10: 이 회사의 event/report 중 해당 관점으로 라우팅된 compact 타임라인.

    별도 참조 데이터(raw/events.json·reports.json)에서 읽어 compact만 투입(토큰 bounded).
    미수집·corp 부재는 빈 리스트(graceful). 재무 숫자엔 안 섞는다(참고 맥락일 뿐).
    """

    from config.settings import settings
    from src.collect.events import routed_timeline

    corp = str(report.get("corp_code", ""))
    if not corp:
        return []
    try:
        events = routed_timeline(corp, settings.data_dir).get(perspective, [])
    except Exception:
        return []
    if len(events) <= 30:
        return events
    # silent cap 금지(§9): 잘린 건수를 명시 sentinel로 표면화.
    return events[:30] + [{"_truncated": len(events) - 30, "note": "추가 event 생략"}]


# 쉼표묶음 금액(12,345,000) — 날짜·코드를 금액으로 오인하지 않게 천단위 2그룹+ 한정.
_AMOUNT = re.compile(r"\d{1,3}(?:,\d{3}){2,}")


def _has_amounts(text: str) -> bool:
    """섹션 본문에 실질 금액(쉼표묶음)이 있나(G6 — 머리말/마커 블록 배제용)."""

    return bool(_AMOUNT.search(text or ""))


def _amount_anchored_excerpt(text: str, width: int = 350) -> str:
    """발췌를 첫 금액 근처에서 시작(머리말이 앞 350자를 잠식하던 G6 차단). 금액 없으면 앞부분."""

    if not text:
        return ""
    match = _AMOUNT.search(text)
    if not match:
        return text[:width]
    start = max(0, match.start() - 60)
    return text[start : start + width]


def _note_file_amount_excerpt(notes_root: Path, fs_div: str, locator: str) -> str:
    """같은 노트 파일(.txt)에서 금액 블록 발췌. 매칭 섹션이 금액 미반환 시 보강(G6).

    파일에 금액이 없으면 빈 문자열(원본에 없는 금액 날조 안 함).
    """

    match = re.search(r"note:(D\d+):", locator)
    if not match:
        return ""
    path = notes_root / fs_div / f"{match.group(1)}.txt"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    return _amount_anchored_excerpt(text) if _AMOUNT.search(text) else ""


def _correction_history(report: dict[str, object]) -> list[dict]:
    """S9: 이 회사의 정정공시 이력(원본/정정본·재작성 연도) compact.

    데이터 출처 신호(과거연도 재작성 = 비교 주의). UI 배지뿐 아니라 LLM material에도
    전달해 change 관점이 "FS 소급흔적"과 "정정공시로 재작성됨"을 함께 보게 한다.
    미수집·corp 부재는 빈 리스트(graceful).
    """

    from config.settings import settings
    from src.collect.correction import load_corrections

    corp = str(report.get("corp_code", ""))
    if not corp:
        return []
    try:
        rows = load_corrections(corp, settings.data_dir)
    except Exception:
        return []
    history: list[dict] = []
    for row in rows:
        year = row.get("period_year")
        if not year:
            continue
        reason = str(row.get("correction_reason", ""))
        history.append(
            {
                "year": year,
                "report_kind": str(row.get("report_kind", "")),
                "restated": "재작성" in reason,
                "is_past_year": bool(row.get("is_past_year")),
                "reason": reason[:80],
            }
        )
    # 재작성·과거연도 우선
    history.sort(key=lambda h: (not h["restated"], not h["is_past_year"], -int(h["year"])))
    return history[:20]


def numeric_material(report: dict[str, object]) -> dict[str, object]:
    """Inputs for numeric perspective only."""

    return {
        "review_queue_reference": report["review_queue"][:10],
        "ratio_summary": report["ratio_summary"],
        "ratio_time_series": report.get("ratio_time_series", []),
        "account_level_series": report.get("account_level_series", []),
        "latest_signal_snapshot": report.get("latest_signal_snapshot", {}),
        "report_event_timeline": _routed_events(report, "numeric"),
        "scope": "numeric perspective only",
        "queue_role": "review_queue_reference는 변화율 중심 참고 후보이며 정답이 아니다.",
    }


def note_material(
    corp_code: str = "00126380",
    year: int = 2024,
    fs_div: str = "CFS",
    quirks_path: Path = QUIRKS_PATH,
) -> dict[str, object]:
    """Inputs for note perspective only.

    주석 섹션 외에, 온보딩이 사업보고서 원문에서 선별한 검토관심 청크(content_chunks,
    S7 Step4)를 함께 싣는다. 선별이 없는 회사는 빈 리스트로 graceful(정상 경로 무영향).
    """

    notes_root = Path("data/companies") / corp_code / str(year) / "raw" / "notes"
    sections = []
    for account in _note_accounts():
        account_sections = find_account_note_sections(account, notes_root, corp_code, year, fs_div)
        limit = 2 if _priority(account) == "high" else 1
        # G6: 금액(쉼표묶음) 보유 섹션을 우선(stable) — 머리말/마커 블록만 실리던 갭 차단.
        # 금액 없는 섹션만 있는 빈 노트는 순서 불변(원본에 없는 금액 날조 안 함).
        ordered = sorted(account_sections, key=lambda s: not _has_amounts(s.text))
        for section in ordered[:limit]:
            excerpt = _amount_anchored_excerpt(section.text)
            # G6 잔여: 매칭 섹션엔 금액이 없지만 같은 노트 파일 다른 블록엔 있을 때
            # (find_account_note_sections가 금액 섹션 미반환), 노트 파일에서 직접 금액 발췌.
            if not _has_amounts(excerpt):
                file_excerpt = _note_file_amount_excerpt(notes_root, fs_div, section.locator)
                if file_excerpt:
                    excerpt = file_excerpt
            sections.append(
                {
                    "account": account,
                    "year": year,
                    "fs_div": fs_div,
                    "locator": section.locator,
                    "title": section.title,
                    "matched_keywords": section.matched_keywords,
                    "excerpt": excerpt,
                }
            )
    # S7 온보딩 LLM이 선별한 검토관심 청크(content_chunks)만 싣는다(키워드 fallback 제거).
    # fallback을 남기면 'S7 미실행인데 키워드가 대충 채워 통과'라는 hollow-PASS 착각이 생긴다(§9).
    review_chunks = load_content_chunks(corp_code, year, quirks_path)
    if review_chunks:
        report_review_role = (
            "report_review_chunks는 사업보고서 원문에서 온보딩이 선별한 검토 관심 공시 종류 후보다. "
            "부정 확정이 아니라 정상 설명 가능성을 전제로 검토한다."
        )
    else:
        # S7 미선별/실패 시 silent 0 금지(§9): 본문 위험 누락 가능성을 명시 경고로 표면화.
        report_review_role = (
            "[경고] S7 검토관심 청크 미선별 — 사업보고서 본문의 소송·특수관계·우발·약정 등 "
            "서술형 감사관심사항이 이 분석에 포함되지 않았다. 온보딩에서 S7 청크선별을 실행해야 한다."
        )
    return {
        "note_sections": sections,
        "report_review_chunks": review_chunks,
        "report_review_role": report_review_role,
        "scope": "note perspective only",
    }


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
        "report_event_timeline": _routed_events(report, "flow"),
        "scope": "flow perspective only",
        "queue_role": "flow_queue_reference는 참고 후보이며, 계정/지표 시계열도 직접 검토한다.",
    }


def change_material(report: dict[str, object]) -> dict[str, object]:
    """Inputs for prior/current change perspective only."""

    latest_snapshot = report.get("latest_signal_snapshot", {})
    restatements = (
        latest_snapshot.get("restatements", []) if isinstance(latest_snapshot, dict) else []
    )
    change_items = [
        item
        for item in report["review_queue"]
        if "single_account_yoy" in str(item["key_evidence"])
        or "growth_divergence" in str(item["key_evidence"])
        or "restatement" in str(item["key_evidence"])
    ]
    return {
        "change_queue_reference": change_items[:10],
        "restatement_signals": restatements[:20] if isinstance(restatements, list) else [],
        "review_queue_reference": report["review_queue"][:10],
        "latest_signal_snapshot": latest_snapshot,
        "account_level_series": report.get("account_level_series", []),
        "ratio_time_series": report.get("ratio_time_series", []),
        "target_year": report["target_year"],
        "report_event_timeline": _routed_events(report, "change"),
        "restatement_history": _correction_history(report),
        "scope": "change perspective only",
        "queue_role": (
            "change_queue_reference는 참고 후보이며, 수준/추세 시계열 전체를 직접 검토한다."
        ),
    }
