"""Peer config loading for industry comparison."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from config.settings import settings

DEFAULT_PEER_CONFIG = settings.config_dir / "industry_peers.yaml"


class PeerCompany(BaseModel):
    corp_code: str
    company_name: str
    stock_code: str = ""
    industry_code: str


class TargetPeerConfig(BaseModel):
    company_name: str
    industry_code: str
    selection: dict[str, object] = Field(default_factory=dict)
    caveat: str = ""
    peers: list[PeerCompany] = Field(default_factory=list)


def load_peer_config(
    corp_code: str,
    path: Path | None = None,
) -> TargetPeerConfig:
    """Load configured peers for one target company."""

    with (path or DEFAULT_PEER_CONFIG).open(encoding="utf-8") as file:
        payload = yaml.safe_load(file) or {}
    target = payload.get("targets", {}).get(corp_code)
    if not target:
        raise KeyError(f"peer config not found for {corp_code}")
    return TargetPeerConfig.model_validate(target)


def filter_same_industry(
    config: TargetPeerConfig,
    company_provider: Any | None = None,
) -> list[PeerCompany]:
    """Keep peers whose configured/live DART industry code matches the target."""

    peers = []
    for peer in config.peers:
        industry_code = peer.industry_code
        if company_provider is not None:
            profile = company_provider(peer.corp_code)
            industry_code = str(profile.get("induty_code", industry_code))
        if industry_code == config.industry_code:
            peers.append(peer)
    max_peers = int(config.selection.get("max_peers", len(peers)))
    return peers[:max_peers]
