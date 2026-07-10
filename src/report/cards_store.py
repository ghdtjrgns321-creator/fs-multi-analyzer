"""의심건 카드 결과 영속화 — 회사/연도 격리 JSON 저장·로드.

Phase2는 LLM 비용(회사당 수천 원)이 들므로 결과를 디스크에 남겨 세션이 끊겨도
재실행 없이 다시 본다(온보딩 마커와 같은 원칙). 카드 3섹션 + 검토범위 + 차트용
시계열 컨텍스트를 한 파일에 스냅샷한다. 손상·부재는 None graceful(재실행 유도).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from config.settings import settings

CARDS_FILE = "suspicion_cards.json"
_CARD_SECTIONS = ("account_cards", "relationship_cards", "company_cards")


def _cards_path(corp_code: str, year: object, root: Path | None = None) -> Path:
    return (root or settings.data_dir) / corp_code / str(year) / CARDS_FILE


def save_cards(
    corp_code: str,
    year: object,
    card_result: dict,
    series_rows: list[dict],
    target_year: object,
    root: Path | None = None,
) -> Path:
    """카드 결과 스냅샷 저장. AccountFinding은 model_dump로 직렬화(렌더러는 dict도 읽음)."""

    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "has_findings": bool(card_result.get("has_findings")),
        "review_scope": card_result.get("review_scope") or {},
        "external_verification": card_result.get("external_verification") or {},
        "series_rows": series_rows or [],
        "target_year": target_year,
    }
    for section in _CARD_SECTIONS:
        payload[section] = [
            card.model_dump(mode="json") if hasattr(card, "model_dump") else card
            for card in (card_result.get(section) or [])
        ]
    path = _cards_path(corp_code, year, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def load_cards(corp_code: str, year: object, root: Path | None = None) -> dict | None:
    """저장된 카드 스냅샷 로드. 부재·손상 JSON은 None(있는 척 금지 — 재실행 유도)."""

    path = _cards_path(corp_code, year, root)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload
