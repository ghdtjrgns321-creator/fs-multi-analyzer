"""XBRL 주석 추출기(notes_xbrl) 검증.

추출은 실제 OpenDART XBRL zip(삼성 보유분)을 결정론 오프라인 자산으로 사용한다.
zip이 없는 환경에서는 skip(추출은 외부 수집물 의존).
"""

from pathlib import Path

import pytest

from src.collect.notes_xbrl import extract_note_facts, save_note_facts

SAMSUNG_ZIP = Path("data/companies/00126380/2024/raw/financial_statement_xbrl.zip")


@pytest.mark.skipif(not SAMSUNG_ZIP.exists(), reason="XBRL zip 미수집 환경")
def test_extract_note_facts_includes_nonfinancial_notes() -> None:
    facts = extract_note_facts(SAMSUNG_ZIP)

    # 본문 5표만이면 수백 미만 — 주석 포함이면 수천 건
    assert len(facts) > 2000
    concepts = {f.concept for f in facts}
    # 비금융 주석 개념이 실제로 들어있어야 한다(차입금·관계기업·특수관계자)
    joined = " ".join(concepts)
    assert "Borrowings" in joined or "BondsIssued" in joined
    assert any("RelatedParty" in c for c in concepts)


@pytest.mark.skipif(not SAMSUNG_ZIP.exists(), reason="XBRL zip 미수집 환경")
def test_save_note_facts_writes_tsv(tmp_path: Path) -> None:
    facts = extract_note_facts(SAMSUNG_ZIP)

    stats = save_note_facts(facts, tmp_path)

    assert (tmp_path / "note_facts.tsv").exists()
    assert stats["fact_count"] == len(facts)
    assert stats["distinct_concepts"] > 100
