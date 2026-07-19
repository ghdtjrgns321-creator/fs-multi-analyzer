"""Config loader for L2 relationship-chain calculations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from config.settings import settings

DEFAULT_CONFIG = settings.config_dir / "playbooks" / "relationship_chains.yaml"


def load_l2_config(path: Path | None = None) -> dict[str, Any]:
    """Load the L2 MVP1 section from the relationship playbook."""

    with (path or DEFAULT_CONFIG).open(encoding="utf-8") as file:
        payload = yaml.safe_load(file) or {}
    config = payload.get("l2_mvp1", {})
    if not config:
        raise ValueError("l2_mvp1 config is missing")
    return config


def load_relationship_chains(path: Path | None = None) -> list[dict[str, Any]]:
    """관계사슬 정의 목록. 파생층 커버리지가 '이름으로 조회되는 계정'을 뽑는 데 쓴다."""

    with (path or DEFAULT_CONFIG).open(encoding="utf-8") as file:
        payload = yaml.safe_load(file) or {}
    return list(payload.get("relationship_chains", []) or [])
