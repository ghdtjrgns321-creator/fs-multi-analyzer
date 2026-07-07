"""Material board helpers for independent L4 perspectives."""

from __future__ import annotations

import re
from pathlib import Path

from src.db.normalized import read_report_extracts
from src.notes.indexer import find_account_note_sections, load_account_note_mappings
from src.signals.metrics_panel import panel_columnar


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


def numeric_material(report: dict[str, object]) -> dict[str, object]:
    """Inputs for numeric perspective only."""

    return {
        # 코드가 추린 등수 힌트(review_queue)는 주지 않는다 — 전 계정 계산값을 전부 주고
        # 무엇이 유의한지는 관점이 직접 고른다(PLAN §3: 발견=LLM, 주의 편향 제거).
        # account_level_series는 싣지 않는다 — panel이 같은 계정·금액을 압축 보유(중복 제거).
        "ratio_summary": report["ratio_summary"],
        "ratio_time_series": report.get("ratio_time_series", []),
        "account_metrics_panel": panel_columnar(report.get("account_metrics_panel", [])),
        "latest_signal_snapshot": report.get("latest_signal_snapshot", {}),
        "report_event_timeline": _routed_events(report, "numeric"),
        "scope": "numeric perspective only",
        "judgment_role": (
            "코드가 추린 후보 목록은 제공하지 않는다. 무엇이 이상한지는 account_metrics_panel"
            "(전 계정 계산값, columns/rows 컬럼형)을 직접 훑어 스스로 판단한다."
        ),
    }


def note_material(
    corp_code: str = "00126380",
    year: int = 2024,
    fs_div: str = "CFS",
    note_facts: list[dict] | None = None,
    data_dir: Path | None = None,
) -> dict[str, object]:
    """Inputs for note perspective only.

    주석 섹션 외에, Layer 1 서술 리더가 사업보고서 본문에서 추출한 항목(report_extracts)을
    함께 싣는다. 리더 미실행 회사는 빈 리스트로 graceful(정상 경로 무영향).

    note_facts: XBRL 주석 fact 전량(detail+기타주석, 흡수·메타 제외). 특수관계자·지급보증·
    우발 등 본문 10계정 HTML 파이프가 못 보던 것을 전부 싣는다(자의적 컷 없음, 비용 수용).
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
    # Layer 1 서술 리더가 사업보고서 본문에서 추출한 항목(report_extracts)을 싣는다.
    # 미실행 시 silent 0 금지(§9): 본문 위험 누락 가능성을 명시 경고로 표면화.
    extracts = read_report_extracts(corp_code, year, data_dir=data_dir)
    if extracts:
        report_extracts_role = (
            "report_extracts는 Layer 1 서술 리더가 사업보고서 본문(사업·경영진단·감사·지배구조·특수관계·"
            "우발·제재)에서 추출한 감사 검토 관심 항목이다. 각 item은 part·label·statement(원문 수치 인용)·"
            "evidence·why_relevant를 갖는다. 부정 확정이 아니라 정상 설명 가능성을 전제로 검토한다."
        )
    else:
        report_extracts_role = (
            "[경고] Layer 1 서술 추출물 없음 — 사업보고서 본문의 소송·특수관계·우발·약정 등 서술형 "
            "감사관심사항이 이 분석에 포함되지 않았다. 온보딩에서 Layer 1 리더를 실행해야 한다."
        )
    facts = note_facts or []
    note_facts_role = (
        "note_facts는 XBRL 주석에서 추출한 정량·서술 fact 전량이다(흡수=본문중복·메타 제외). "
        "특수관계자 거래·지급보증·약정·우발(소송 등)이 여기 포함된다. value가 숫자면 금액, "
        "문장이면 서술형 공시다. dimensions로 연결/별도·거래상대를 구분한다."
        if facts
        else "[주석 fact 없음] 이 회사-연도는 분류된 주석 fact가 적재되지 않았다."
    )
    return {
        "note_sections": sections,
        "report_extracts": extracts,
        "report_extracts_role": report_extracts_role,
        "note_facts": facts,
        "note_facts_role": note_facts_role,
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

    # 큐(등수 힌트)는 주지 않는다. 흐름 관점에 필요한 관계신호(growth_divergences·
    # direction_checks·cfs_ofs_gaps)는 latest_signal_snapshot에 전수로 들어 있다.
    ratio_summary = report["ratio_summary"]
    ratio_summary = ratio_summary if isinstance(ratio_summary, dict) else {}
    return {
        # account_level_series는 싣지 않는다 — panel이 같은 계정·금액을 압축 보유(중복 제거).
        "latest_signal_snapshot": report.get("latest_signal_snapshot", {}),
        "account_metrics_panel": panel_columnar(report.get("account_metrics_panel", [])),
        "unmapped_material_accounts": report.get("unmapped_material_accounts", []),
        "ratio_summary": {
            key: value for key, value in ratio_summary.items() if key in {"활동성", "이익의 질"}
        },
        "ratio_time_series": [
            row
            for row in report.get("ratio_time_series", [])  # type: ignore[union-attr]
            if row.get("category") in {"activity", "earnings_quality"}
        ],
        "report_event_timeline": _routed_events(report, "flow"),
        "scope": "flow perspective only",
        "judgment_role": (
            "코드가 추린 후보 목록은 제공하지 않는다. 무엇이 이상한지는 account_metrics_panel"
            "(전 계정 계산값, columns/rows 컬럼형)·관계신호(latest_signal_snapshot)·지표 시계열에서"
            " 직접 판단한다."
        ),
    }


def trend_material(report: dict[str, object]) -> dict[str, object]:
    """Inputs for the trend(추세) perspective only.

    당해 급변(yoy 튐)은 numeric 전담. 추세 관점은 account_metrics_panel의 trend(다년 기울기)로
    다년 단조 방향(점점 증가/감소·완만 드리프트·가속)만 본다. 소급재작성은 추세와 무관해 제거됨."""

    latest_snapshot = report.get("latest_signal_snapshot", {})
    return {
        # account_level_series는 싣지 않는다 — panel이 같은 계정·금액을 압축 보유(중복 제거).
        "latest_signal_snapshot": latest_snapshot,
        "account_metrics_panel": panel_columnar(report.get("account_metrics_panel", [])),
        "ratio_time_series": report.get("ratio_time_series", []),
        "target_year": report["target_year"],
        "report_event_timeline": _routed_events(report, "trend"),
        # 자본변동표(SCE) 2D 셀 — 자본 변동(배당·유상증자·자기주식·순이익)은 추세 관점 소관.
        "sce_cells": report.get("sce_cells", []),
        "sce_role": (
            "sce_cells는 자본변동표 2D(변동×구성요소). 배당·유상증자·자기주식취득·기타자본변동 등 "
            "본문 패널에 없는 자본거래를 담는다. change=변동사건, component=자본 구성요소. "
            "occurrence_state는 이 변동종류의 신규/소멸: appeared=올해 신규 발생(예: 자기주식 첫 취득), "
            "disappeared=과거 있다 당기 소멸, present=매년 반복. 신규(appeared) 자본거래를 우선 검토한다."
        ),
        "scope": "trend perspective only",
        "judgment_role": (
            "코드가 추린 후보 목록은 제공하지 않는다. 당해 급변(yoy 튐)은 numeric 소관이다. "
            "추세 관점은 account_metrics_panel(전 계정 계산값, columns/rows 컬럼형)의 trend(다년 기울기)로 "
            "여러 해에 걸쳐 점점 증가/감소하거나 완만히 드리프트·가속하는 계정을 직접 골라 판단한다."
        ),
    }
