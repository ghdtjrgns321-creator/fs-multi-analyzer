"""조사원·연속점수 설정 로더 — config/investigation.yaml (PLAN §5 조사 단계).

임계(게이트)·가중치(점수)를 코드에 박지 않는다(원칙 3). 파일 부재는 빈 dict(graceful).
"""

from __future__ import annotations

from pathlib import Path

import yaml

INVESTIGATION_PATH = Path("config/investigation.yaml")


def load_investigation_config(path: Path = INVESTIGATION_PATH) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


__all__ = ["INVESTIGATION_PATH", "load_investigation_config"]
