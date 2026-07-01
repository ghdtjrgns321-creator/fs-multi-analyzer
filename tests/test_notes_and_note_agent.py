import asyncio
from types import SimpleNamespace

from src.agents.note_analyst import _contains_grounded_value, create_note_enriched_finding
from src.notes.indexer import (
    NoteSection,
    find_account_note_sections,
    load_account_note_mappings,
    parse_note_html,
)
from src.report.materials import note_material
from src.schemas.findings import AccountFinding, EvidenceRef, IssueType

FIXTURE_HTML = """
<html><body>
<p>[D822420] 7. 매출채권 및 미수금</p>
<table><tr><th>항목</th><th>2023</th></tr><tr><td>매출채권</td><td>36,671</td></tr></table>
<p>연체되거나 손상된 금융자산에 대한 공시 [개요][ 문장영역 ]</p>
<p>매출채권은 신용위험에 노출되어 있으며 회수 가능성을 검토한다.</p>
<p>대손충당금은 기대신용손실 기준으로 인식한다.</p>
</body></html>
"""


def base_finding() -> AccountFinding:
    return AccountFinding(
        account="매출채권",
        issue_type=IssueType.REVENUE_RECEIVABLES,
        materiality_score=80.0,
        anomaly_score=75.0,
        confidence="High",
        numeric_evidence=[
            EvidenceRef(
                source="financial_statement",
                locator="매출채권",
                year="2023",
                value="YoY 2.59%",
            )
        ],
        flow_evidence=[
            EvidenceRef(
                source="cash_flow",
                locator="영업활동현금흐름",
                year="2023",
                value="direction decrease",
            )
        ],
        confirm_question=["매출채권 회수가능성을 확인했는가?"],
        next_procedure=["매출채권 연령분석표를 확인한다."],
        risk_level="Medium",
    )


def test_parse_note_html_splits_sections_and_preserves_metadata() -> None:
    sections = parse_note_html(
        FIXTURE_HTML,
        corp_code="00126380",
        year=2023,
        fs_div="CFS",
        note_code="D82242",
        note_name="매출채권 및 기타채권",
    )

    assert sections[0].locator == "note:D82242:CFS:2023:0"
    assert sections[0].current_year == "2023"
    assert sections[0].prior_year == "2022"
    assert "36,671" in sections[0].text
    assert any("신용위험" in section.text for section in sections)


def test_find_account_note_sections_uses_mapping_and_keywords(tmp_path) -> None:
    note_dir = tmp_path / "CFS"
    note_dir.mkdir()
    note_path = note_dir / "D82242.html"
    note_path.write_text(FIXTURE_HTML, encoding="utf-8")
    mapping_path = tmp_path / "note_mappings.yaml"
    mapping_path.write_text(
        """
account_notes:
  매출채권:
    note_code: D82242
    note_name: 매출채권 및 기타채권
    keywords: [신용위험, 연체, 대손, 회수]
""",
        encoding="utf-8",
    )

    sections = find_account_note_sections(
        "매출채권",
        notes_root=tmp_path,
        corp_code="00126380",
        year=2023,
        fs_div="CFS",
        mapping_path=mapping_path,
    )

    assert [section.note_code for section in sections] == ["D82242"]
    assert "신용위험" in sections[0].matched_keywords
    assert "대손" in sections[0].matched_keywords


def test_inventory_note_sections_use_d82638_mapping(tmp_path) -> None:
    note_dir = tmp_path / "CFS"
    note_dir.mkdir()
    (note_dir / "D82638.html").write_text(
        """
<html><body>
<p>[D826380] 재고자산</p>
<p>재고자산 평가손실과 순실현가능가치를 검토한다.</p>
</body></html>
""",
        encoding="utf-8",
    )
    mapping_path = tmp_path / "note_mappings.yaml"
    mapping_path.write_text(
        """
account_notes:
  재고자산:
    note_code: D82638
    note_name: 재고자산
    keywords: [평가손실, 순실현가능가치]
""",
        encoding="utf-8",
    )

    sections = find_account_note_sections(
        "재고자산",
        notes_root=tmp_path,
        corp_code="00126380",
        year=2024,
        fs_div="CFS",
        mapping_path=mapping_path,
    )

    assert sections[0].locator == "note:D82638:CFS:2024:0"
    assert sections[0].matched_keywords == ["평가손실", "순실현가능가치"]


def test_new_note_categories_are_configured() -> None:
    mappings = load_account_note_mappings()

    assert mappings["단기차입금"]["note_code"] == "D82240"
    assert mappings["사채"]["note_code"] == "D82245"
    assert mappings["충당부채"]["note_code"] == "D82757"
    assert mappings["유형자산"]["analysis_priority"] == "low"


def test_provision_note_sections_use_d82757_mapping(tmp_path) -> None:
    note_dir = tmp_path / "CFS"
    note_dir.mkdir()
    (note_dir / "D82757.html").write_text(
        """
<html><body>
<p>[D827570] 충당부채</p>
<p>충당부채와 우발부채, 소송 및 보증 지급가능성을 검토한다.</p>
</body></html>
""",
        encoding="utf-8",
    )
    mapping_path = tmp_path / "note_mappings.yaml"
    mapping_path.write_text(
        """
account_notes:
  충당부채:
    note_code: D82757
    note_name: 충당부채
    keywords: [충당부채, 우발부채, 소송, 보증]
""",
        encoding="utf-8",
    )

    sections = find_account_note_sections(
        "충당부채",
        notes_root=tmp_path,
        corp_code="00126380",
        year=2025,
        fs_div="CFS",
        mapping_path=mapping_path,
    )

    assert sections[0].locator == "note:D82757:CFS:2025:0"
    assert "우발부채" in sections[0].matched_keywords
    assert "소송" in sections[0].matched_keywords


def test_note_material_uses_yaml_mappings_for_new_categories() -> None:
    material = note_material(year=2025)
    accounts = {section["account"] for section in material["note_sections"]}
    locators = {section["locator"] for section in material["note_sections"]}

    assert {"단기차입금", "사채", "충당부채"}.issubset(accounts)
    assert any(locator.startswith("note:D82240") for locator in locators)
    assert any(locator.startswith("note:D82245") for locator in locators)
    assert any(locator.startswith("note:D82757") for locator in locators)


def test_note_analyst_accepts_mock_and_fills_note_evidence(monkeypatch) -> None:
    sections = _fixture_sections()
    risk_section = next(section for section in sections if "신용위험" in section.text)
    enriched = base_finding()
    enriched.note_evidence = [
        EvidenceRef(
            source="note",
            locator=risk_section.locator,
            year="2023",
            value="신용위험에 노출되어 있으며 회수 가능성을 검토한다",
        )
    ]
    enriched.note_cross_check = "숫자상 회수가능성 신호와 주석의 신용위험 언급이 같은 방향이다."

    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            assert "note_sections" in prompt
            return SimpleNamespace(output=enriched)

    monkeypatch.setattr("src.agents.note_analyst.settings.google_api_key", "fake")

    result = asyncio.run(
        create_note_enriched_finding(
            base_finding(),
            sections,
            agent_factory=FakeAgent,
            retry_delays=(0,),
        )
    )

    assert result.note_evidence[0].source == "note"
    assert result.note_cross_check.startswith("숫자상")


def test_note_grounding_accepts_whitespace_only_differences() -> None:
    text = "장기차입금\n6,479,517,000,000\n만기상환일\n2027-01-01"
    assert _contains_grounded_value(text, "장기차입금 6,479,517,000,000")


def _fixture_sections() -> list[NoteSection]:
    return parse_note_html(
        FIXTURE_HTML,
        "00126380",
        2023,
        "CFS",
        "D82242",
        "매출채권 및 기타채권",
    )
