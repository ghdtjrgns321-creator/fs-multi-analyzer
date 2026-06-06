"""Peer config loading for industry comparison."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from config.settings import settings
from src.peers.industry_code import industry_key

DEFAULT_PEER_CONFIG = settings.config_dir / "industry_peers.yaml"


class PeerCompany(BaseModel):
    corp_code: str
    company_name: str
    stock_code: str = ""
    industry_code: str


class IndustryPeerConfig(BaseModel):
    industry_code: str
    selection: dict[str, object] = Field(default_factory=dict)
    caveat: str = "대상 회사의 사업구조가 피어와 달라 단순 비교에 한계가 있다."
    peers: list[PeerCompany] = Field(default_factory=list)


def load_peer_config(
    industry_code: str,
    path: Path | None = None,
) -> IndustryPeerConfig:
    """Load configured peers for one DART middle-class industry key."""

    key = industry_key(industry_code)
    with (path or DEFAULT_PEER_CONFIG).open(encoding="utf-8") as file:
        payload = yaml.safe_load(file) or {}
    config = payload.get("industries", {}).get(key)
    if not config:
        raise KeyError(f"피어 미구성: industry_code={key}")
    return IndustryPeerConfig.model_validate({"industry_code": key, **config})


def filter_same_industry(
    config: IndustryPeerConfig,
    company_provider: Any | None = None,
) -> list[PeerCompany]:
    """Keep peers whose configured/live DART industry code matches the target."""

    peers = []
    for peer in config.peers:
        industry_code = peer.industry_code
        if company_provider is not None:
            profile = company_provider(peer.corp_code)
            industry_code = str(profile.get("induty_code", industry_code))
        if industry_key(industry_code) == config.industry_code:
            peers.append(peer)
    max_peers = int(config.selection.get("max_peers", len(peers)))
    return peers[:max_peers]
