"""신 XBRL 주석(note_facts) 분류 — 본문 canonical 재사용 + detail 토큰분류(Option 2).

note_facts.tsv의 concept(namespace 없는 local name)을 3분류한다(계산·해석 없음, 분류만):
  흡수    = 본문 canonical_accounts account_id의 stem과 일치 → 본문 중복(분석은 본문이 담당)
  메타    = meta_tokens 포함 → 표지·감사·연락처 노이즈
  detail  = note_categories 토큰(우선순위 순) → IFRS 주석 카테고리, 미매칭은 기타주석
카테고리·토큰은 config/playbooks/note_mappings.yaml에 외부화(코드 하드코딩 금지).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from config.settings import settings
from src.normalize.config import load_canonical_accounts

PREFIXES = ("ifrs-full_", "ifrs_", "dart_")
NOTE_FACT_COLUMNS = ["concept", "label_ko", "label_en", "period", "unit", "value", "dimensions"]
CLASSIFIED_COLUMNS = [
    "concept",
    "label_ko",
    "period",
    "unit",
    "value",
    "dimensions",
    "bucket",
    "category",
]
# bucket ∈ {흡수, 메타, detail, 기타주석}. category는 detail일 때만 채워진다.


@dataclass(frozen=True)
class NoteTaxonomy:
    meta_tokens: tuple[str, ...]
    categories: tuple[tuple[str, tuple[str, ...]], ...]  # 우선순위 순서 보존
    high_priority: frozenset[str]
    canon_stems: frozenset[str]


def _stem(account_id: str) -> str:
    for prefix in PREFIXES:
        if account_id.startswith(prefix):
            return account_id[len(prefix) :].lower()
    return account_id.lower()


def load_note_taxonomy(
    mapping_path: Path | None = None, canonical_path: Path | None = None
) -> NoteTaxonomy:
    """note_mappings.yaml(분류 토큰) + canonical_accounts.yaml(흡수 stem)을 로드."""

    config_dir = settings.config_dir
    mapping_path = mapping_path or (config_dir / "playbooks" / "note_mappings.yaml")
    canonical_path = canonical_path or (config_dir / "canonical_accounts.yaml")

    payload = yaml.safe_load(mapping_path.read_text(encoding="utf-8")) or {}
    meta = tuple(str(t).lower() for t in payload.get("meta_tokens", []))
    categories = tuple(
        (str(name), tuple(str(t).lower() for t in tokens))
        for name, tokens in (payload.get("note_categories") or {}).items()
    )
    high = frozenset(str(x) for x in payload.get("note_high_priority", []))
    stems = {
        _stem(account_id)
        for account in load_canonical_accounts(canonical_path)
        for account_id in account.account_ids
    }
    return NoteTaxonomy(meta, categories, high, frozenset(stems))


def classify_concept(concept: str, taxonomy: NoteTaxonomy) -> tuple[str, str | None]:
    """concept → (bucket, category). 우선순위: 메타 → 흡수 → detail 카테고리 → 기타주석."""

    lowered = concept.lower()
    if any(token in lowered for token in taxonomy.meta_tokens):
        return ("메타", None)
    if _stem(concept) in taxonomy.canon_stems:
        return ("흡수", None)
    for category, tokens in taxonomy.categories:
        if any(token in lowered for token in tokens):
            return ("detail", category)
    return ("기타주석", None)


def classify_note_facts(facts: pd.DataFrame, taxonomy: NoteTaxonomy) -> pd.DataFrame:
    """note_facts 프레임에 bucket·category 분류열을 붙인다."""

    if facts.empty:
        return pd.DataFrame(columns=CLASSIFIED_COLUMNS)
    scoped = facts.copy()
    pairs = [classify_concept(str(concept), taxonomy) for concept in scoped["concept"]]
    scoped["bucket"] = [bucket for bucket, _ in pairs]
    scoped["category"] = [category for _, category in pairs]
    for column in CLASSIFIED_COLUMNS:
        if column not in scoped:
            scoped[column] = None
    return scoped[CLASSIFIED_COLUMNS]


# 연결/별도 축만 있는 흡수 행 = 본문 총계 중복. 그 외 축이 있으면 부문·건별 분해(고가치).
_CONSOLIDATED_AXIS = "ConsolidatedAndSeparateFinancialStatementsAxis"


def is_dimensioned(dimensions: object) -> bool:
    """CFS/OFS(연결·별도) 외 축을 가지면 True(부문·자산종류·차입건별 등 분해)."""

    text = str(dimensions or "")
    if not text:
        return False
    return any(kv.split("=")[0] != _CONSOLIDATED_AXIS for kv in text.split("|") if kv)


def select_for_load(classified: pd.DataFrame) -> pd.DataFrame:
    """DuckDB 적재 대상만 남긴다: detail·기타주석 전체 + 유차원 흡수. 메타·무차원흡수 제외."""

    if classified.empty:
        return classified
    bucket = classified["bucket"]
    keep_bucket = bucket.isin(["detail", "기타주석"])
    absorb_dim = (bucket == "흡수") & classified["dimensions"].map(is_dimensioned)
    return classified[keep_bucket | absorb_dim].reset_index(drop=True)


def _note_facts_path(corp_code: str, year: int | str, data_dir: Path | None = None) -> Path:
    root = data_dir or settings.data_dir
    return root / corp_code / str(year) / "raw" / "notes_xbrl" / "note_facts.tsv"


def read_note_facts(path: Path) -> pd.DataFrame:
    """note_facts.tsv를 읽는다(없으면 빈 프레임)."""

    if not path.exists():
        return pd.DataFrame(columns=NOTE_FACT_COLUMNS)
    return pd.read_csv(path, sep="\t", dtype=str).fillna("")


def classify_company_year(
    corp_code: str,
    year: int | str,
    data_dir: Path | None = None,
    taxonomy: NoteTaxonomy | None = None,
) -> pd.DataFrame:
    """한 회사연도의 주석 facts를 분류한 정제 테이블을 반환."""

    taxonomy = taxonomy or load_note_taxonomy()
    facts = read_note_facts(_note_facts_path(corp_code, year, data_dir))
    return classify_note_facts(facts, taxonomy)
