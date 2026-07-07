"""사업보고서 subsection을 주제 폴더로 결정론 라우팅 + 커버리지 장부.

판단(LLM) 없음 — 제목 패턴(config YAML) 매칭만. 미매칭은 "기타"로 surface, "해당없음"은 정당제외.
설계 §6·§8·§9(DISCLOSURE_DECOMPOSITION_DESIGN.md).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.notes.report_parts import ReportPart, SubSection, split_subsections

DEFAULT_ROUTING_PATH = Path("config/playbooks/report_section_routing.yaml")

# body 라우터가 다루지 않는 PART — III(재무제표+주석)은 구조화 파이프(finstate/XBRL),
# XII(상세표)는 중복 상세표. 이 둘은 서술 라우팅 대상이 아니다(설계 §4·§6).
_EXCLUDE_NUMERALS = frozenset({"III", "XII"})

# 본문이 사실상 비었다고 볼 "해당없음" 문구(공백제거·소문자 비교).
_EMPTY_PATTERNS = (
    "해당사항 없음",
    "해당사항이 없습니다",
    "해당 사항 없음",
    "해당사항없음",
    "해당없음",
)


def load_routing(path: Path = DEFAULT_ROUTING_PATH) -> dict:
    """주제→제목패턴 매핑 YAML 로드(없으면 빈 topics)."""

    if not path.exists():
        return {"topics": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"topics": {}}


def _norm(text: str) -> str:
    """공백 제거·소문자 — 제목 부분문자열 비교용."""

    return re.sub(r"\s+", "", text).lower()


def route_title(title: str, routing: dict) -> str | None:
    """제목이 매칭되는 첫 주제 반환(우선순위=YAML 순서). 미매칭 None."""

    norm_title = _norm(title)
    for topic, patterns in (routing.get("topics") or {}).items():
        if any(_norm(p) in norm_title for p in patterns):
            return topic
    return None


def is_empty_section(text: str) -> bool:
    """본문이 사실상 '해당없음'이면 True(정당제외 대상). 짧고 해당없음 문구면 빈 섹션."""

    stripped = text.strip()
    if not stripped:
        return True
    compact = _norm(stripped)
    return len(compact) < 40 and any(_norm(p) in compact for p in _EMPTY_PATTERNS)


@dataclass
class RoutingResult:
    """해체 결과 — 주제별 폴더 + 정당제외 + 기타 + 장부."""

    routed: dict[str, list[SubSection]] = field(default_factory=dict)
    ignored: list[SubSection] = field(default_factory=list)  # 해당없음(정당제외)
    other: list[SubSection] = field(default_factory=list)  # 미매칭(기타)
    ledger: dict = field(default_factory=dict)


def route_report(parts: list[ReportPart], routing: dict | None = None) -> RoutingResult:
    """PART들을 subsection으로 쪼개 주제 폴더에 라우팅 + 커버리지 장부 항등식 산출."""

    routing = routing if routing is not None else load_routing()
    result = RoutingResult()
    population = 0
    for part in parts:
        if part.numeral in _EXCLUDE_NUMERALS:  # 재무제표·주석·상세표는 구조화 파이프 담당
            continue
        for sub in split_subsections(part):
            population += 1
            if is_empty_section(sub.text):
                result.ignored.append(sub)
                continue
            topic = route_title(sub.title, routing)
            if topic is None:
                result.other.append(sub)
            else:
                result.routed.setdefault(topic, []).append(sub)
    routed_count = sum(len(v) for v in result.routed.values())
    result.ledger = {
        "population": population,
        "routed": routed_count,
        "ignored": len(result.ignored),
        "other": len(result.other),
        "identity_ok": population == routed_count + len(result.ignored) + len(result.other),
    }
    return result
