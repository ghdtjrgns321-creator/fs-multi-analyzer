"""External context brief schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ContextItem(BaseModel):
    """One sourced external context item."""

    claim: str = Field(min_length=1)
    source_title: str = ""
    source_url: str = ""


class ContextBrief(BaseModel):
    """Reference-only external context, kept separate from Finding judgment."""

    items: list[ContextItem] = Field(default_factory=list)
