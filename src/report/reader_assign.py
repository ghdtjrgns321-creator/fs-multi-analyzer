"""파트→서술 리더 focus 배정(결정론). 설계 §4 macro-block 5종.

사업보고서가 준 목차 배치대로 각 PART를 서술 리더 블록에 매핑하고, 그 블록의 focus 프롬프트를
반환한다. III(재무 결정론=Phase1)·XII(상세표=구조화 API 중복)는 서술 리더 미배정 → None.
블록 정의·focus 문구는 config/playbooks/reader_focus.yaml(하드코딩 금지).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

DEFAULT_FOCUS_PATH = Path("config/playbooks/reader_focus.yaml")


@lru_cache(maxsize=8)
def load_focus_map(path: Path = DEFAULT_FOCUS_PATH) -> dict[str, str]:
    """PART 로마숫자 → focus 프롬프트 평면 맵(블록 parts 전개). 없으면 빈 맵."""

    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    focus_map: dict[str, str] = {}
    for block in (raw.get("blocks") or {}).values():
        focus = (block.get("focus") or "").strip()
        for numeral in block.get("parts") or []:
            focus_map[numeral] = focus
    return focus_map


def reader_focus(numeral: str, path: Path = DEFAULT_FOCUS_PATH) -> str | None:
    """해당 PART의 서술 리더 focus 반환. 재무결정론(III)·제외(XII) 등 미배정은 None."""

    return load_focus_map(path).get(numeral)
