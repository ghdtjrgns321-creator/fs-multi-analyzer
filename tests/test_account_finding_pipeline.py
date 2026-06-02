import asyncio
from types import SimpleNamespace

from src.agents.account_finding import run_account_finding
from src.schemas.findings import AccountFinding, EvidenceRef, IssueType
from src.signals.mvp1 import build_mvp1_signal_report
from tests.test_analysis_tools import fixture_frame


def inventory_finding() -> AccountFinding:
    return AccountFinding(
        account="재고자산",
        issue_type=IssueType.INVENTORY_OBSOLESCENCE,
        materiality_score=0.5,
        anomaly_score=0.6,
        confidence="Medium",
        numeric_evidence=[
            EvidenceRef(
                source="financial_statement",
                locator="재고자산",
                year="2024",
                value="YoY 100.00%",
            )
        ],
        counter_evidence=["단기 수요 회복에 대비한 보유 가능성이 있다."],
        normal_explanation=["생산 계획 변경에 따른 일시적 증가 가능성이 있다."],
        confirm_question=["재고자산 평가손실 검토 자료가 있는가?"],
        next_procedure=["재고 연령분석표와 평가충당금 산정을 확인한다."],
        risk_level="Medium",
    )


def test_inventory_account_pipeline_uses_generic_config(monkeypatch, tmp_path) -> None:
    note_dir = tmp_path / "CFS"
    note_dir.mkdir()
    (note_dir / "D82638.html").write_text(
        """
<html><body>
<p>[D826380] 재고자산</p>
<p>재고자산 평가손실과 순실현가능가치 검토 내용이 포함되어 있다.</p>
</body></html>
""",
        encoding="utf-8",
    )

    class NumericAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            assert "재고자산" in prompt
            return SimpleNamespace(output=inventory_finding())

    class NoteAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            finding = inventory_finding()
            finding.note_evidence = [
                EvidenceRef(
                    source="note",
                    locator="note:D82638:CFS:2024:0",
                    year="2024",
                    value="재고자산 평가손실과 순실현가능가치",
                )
            ]
            finding.note_cross_check = "재고 신호와 주석의 평가손실 언급을 함께 검토한다."
            return SimpleNamespace(output=finding)

    monkeypatch.setattr("src.agents.numeric_analyst.settings.google_api_key", "fake")
    monkeypatch.setattr("src.agents.note_analyst.settings.google_api_key", "fake")
    monkeypatch.setattr(
        "src.agents.account_finding.run_signal_spike",
        lambda corp_code: build_mvp1_signal_report(fixture_frame()),
    )

    result = asyncio.run(
        run_account_finding(
            "재고자산",
            2024,
            notes_root=tmp_path,
            numeric_agent_factory=NumericAgent,
            note_agent_factory=NoteAgent,
        )
    )

    assert result["finding"]["account"] == "재고자산"
    assert result["finding"]["note_evidence"][0]["locator"] == "note:D82638:CFS:2024:0"
