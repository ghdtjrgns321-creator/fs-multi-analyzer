import asyncio
from types import SimpleNamespace

import pandas as pd

from src.report.crosscheck import cross_check_assessments
from src.report.external import create_external_assessment
from src.report.integrated import build_review_queue, summarize_ratio_categories
from src.report.multi_agent import build_multi_agent_report, render_multi_agent_markdown
from src.report.perspectives import PerspectiveAssessment, create_perspective_assessment
from src.report.synthesis import create_integrated_summary
from src.schemas.context import ContextBrief, ContextItem
from src.schemas.findings import AccountFinding, EvidenceRef, IssueType


def sample_finding(account: str, risk: str, score: float) -> AccountFinding:
    return AccountFinding(
        account=account,
        issue_type=IssueType.RECEIVABLES_QUALITY,
        materiality_score=score,
        anomaly_score=0.4,
        confidence="Medium",
        numeric_evidence=[
            EvidenceRef(source="financial_statement", locator=account, year="2024", value="YoY")
        ],
        counter_evidence=["반대 가능성"],
        normal_explanation=["정상 가능성"],
        confirm_question=["확인 질문"],
        next_procedure=["추가 절차"],
        risk_level=risk,
    )


def ratio_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"id": "roe", "category": "profitability", "name": "ROE", "year": 2024, "value": 9.0},
            {"id": "dso", "category": "activity", "name": "DSO", "year": 2024, "value": 48.69},
            {"id": "roi", "category": "profitability", "name": "ROI", "year": 2024, "value": None},
        ]
    )


def ratio_config() -> list[dict[str, object]]:
    return [
        {
            "id": "roe",
            "category": "profitability",
            "name": "ROE",
            "audit_basis": ["ISA/KSA 520"],
            "source": {"title": "CFI ROE", "url": "https://example.com/roe"},
        },
        {
            "id": "dso",
            "category": "activity",
            "name": "DSO",
            "audit_basis": ["ISA/KSA 520"],
            "source": {"title": "CFI DSO", "url": "https://example.com/dso"},
        },
    ]


def test_review_queue_sorts_by_risk_then_materiality_without_severity_sum() -> None:
    findings = [
        sample_finding("재고자산", "Medium", 0.9),
        sample_finding("매출채권", "High", 0.1),
    ]

    queue = build_review_queue(findings, ratio_frame(), ratio_config(), target_year=2024)

    assert queue[0].subject == "매출채권"
    assert queue[1].subject == "재고자산"
    assert any(item.subject == "DSO" for item in queue)
    assert all(item.audit_basis for item in queue)


def test_ratio_summary_groups_latest_values_by_category() -> None:
    summary = summarize_ratio_categories(ratio_frame(), target_year=2024)

    assert summary["수익성"]["ROE"] == 9.0
    assert "ROI" not in summary["수익성"]


def test_integrated_summary_accepts_mock_agent(monkeypatch) -> None:
    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            assert "review_queue" in prompt
            return SimpleNamespace(output="실제 데이터에 근거한 가능성 중심 종합 문단")

    monkeypatch.setattr("src.report.synthesis.settings.google_api_key", "fake")
    result = asyncio.run(
        create_integrated_summary({"review_queue": []}, agent_factory=FakeAgent, retry_delays=(0,))
    )

    assert "가능성" in result


def test_cross_check_marks_agreement_for_shared_risk_area() -> None:
    numeric = PerspectiveAssessment(
        perspective="numeric",
        status="completed",
        risk_areas=["매출채권 회수"],
        risk_level="Medium",
        summary="수치상 회수 둔화 가능성",
        evidence=["DSO"],
    )
    note = PerspectiveAssessment(
        perspective="note",
        status="completed",
        risk_areas=["매출채권 회수"],
        risk_level="Medium",
        summary="주석상 신용위험 언급",
        evidence=["D82242"],
    )

    result = cross_check_assessments([numeric, note])

    assert result[0].verdict == "agreement"
    assert "신호 강화" in result[0].comment


def test_cross_check_marks_conflict_when_numeric_risk_note_quiet() -> None:
    numeric = PerspectiveAssessment(
        perspective="numeric",
        status="completed",
        risk_areas=["재고 보유기간"],
        risk_level="Medium",
        summary="DIO 상승",
        evidence=["DIO"],
    )
    note = PerspectiveAssessment(
        perspective="note",
        status="completed",
        risk_areas=[],
        risk_level="Low",
        summary="주석 위험 언급 없음",
        evidence=[],
    )

    result = cross_check_assessments([numeric, note])

    assert result[0].verdict == "conflict"
    assert "주석 잠잠" in result[0].comment


def test_cross_check_normalizes_korean_english_risk_area() -> None:
    numeric = PerspectiveAssessment(
        perspective="numeric",
        status="completed",
        risk_areas=["Revenue Recognition", "Inventory Management"],
        risk_level="Medium",
        summary="numeric",
        evidence=[],
    )
    note = PerspectiveAssessment(
        perspective="note",
        status="completed",
        risk_areas=["매출채권 회수"],
        risk_level="Medium",
        summary="note",
        evidence=[],
    )

    result = cross_check_assessments([numeric, note])

    assert result[0].verdict == "agreement"
    assert result[0].risk_area == "매출채권/수익"


def test_cross_check_external_agreement_is_not_exculpatory() -> None:
    numeric = PerspectiveAssessment(
        perspective="numeric",
        status="completed",
        risk_areas=["매출채권"],
        risk_level="Medium",
        summary="매출채권 검토 필요",
        evidence=[],
    )
    external = PerspectiveAssessment(
        perspective="external",
        status="completed",
        risk_areas=["매출채권/수익"],
        risk_level="Low",
        summary="출처 기반 외부 맥락",
        evidence=["기사: https://example.com"],
    )

    result = cross_check_assessments([numeric, external])

    assert result[0].verdict == "agreement"
    assert "약화하지 않는다" in result[0].comment


def test_perspective_assessment_accepts_mock_agent(monkeypatch) -> None:
    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            assert "perspective" in prompt
            return SimpleNamespace(
                output=PerspectiveAssessment(
                    perspective="numeric",
                    status="completed",
                    risk_areas=["수익성"],
                    risk_level="Medium",
                    summary="수익성 급락 후 회복 가능성을 검토한다.",
                    evidence=["ROE 9.00"],
                )
            )

    monkeypatch.setattr("src.report.perspectives.settings.google_api_key", "fake")
    result = asyncio.run(
        create_perspective_assessment("numeric", {"review_queue": []}, FakeAgent, (0,))
    )

    assert result.perspective == "numeric"
    assert result.status == "completed"


def test_multi_agent_report_has_five_independent_perspectives() -> None:
    result = asyncio.run(build_multi_agent_report(run_llm=False))

    perspectives = {item["perspective"] for item in result["perspective_assessments"]}

    assert perspectives == {"numeric", "note", "flow", "change", "external"}
    assert set(result["materials"]) == {"numeric", "note", "flow", "change", "external"}


def test_flow_and_change_perspectives_accept_mock_agent(monkeypatch) -> None:
    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            perspective = "flow" if '"perspective": "flow"' in prompt else "change"
            return SimpleNamespace(
                output=PerspectiveAssessment(
                    perspective=perspective,
                    status="completed",
                    risk_areas=["현금흐름"],
                    risk_level="Medium",
                    summary=f"{perspective} 관점 평가",
                    evidence=["grounded"],
                )
            )

    monkeypatch.setattr("src.report.perspectives.settings.google_api_key", "fake")

    flow = asyncio.run(create_perspective_assessment("flow", {}, FakeAgent, (0,)))
    change = asyncio.run(create_perspective_assessment("change", {}, FakeAgent, (0,)))

    assert flow.perspective == "flow"
    assert change.perspective == "change"


def test_external_perspective_accepts_mock_context() -> None:
    async def fake_context(query: str, retry_delays: tuple[float, ...]) -> ContextBrief:
        assert "삼성전자" in query
        assert retry_delays == (0,)
        return ContextBrief(
            items=[
                ContextItem(
                    claim="매출채권 관련 업황 맥락이 보도되었다.",
                    source_title="기사",
                    source_url="https://example.com/news",
                )
            ]
        )

    report = {
        "target_year": 2024,
        "review_queue": [{"subject": "매출채권"}, {"subject": "재고자산"}],
    }

    result = asyncio.run(create_external_assessment(report, fake_context, retry_delays=(0,)))

    assert result.perspective == "external"
    assert result.status == "completed"
    assert result.risk_level == "Low"
    assert result.evidence == ["기사: https://example.com/news"]


def test_renderer_shows_external_source_url() -> None:
    rendered = render_multi_agent_markdown(
        {
            "review_queue": [],
            "ratio_summary": {},
            "perspective_assessments": [
                PerspectiveAssessment(
                    perspective="external",
                    status="completed",
                    risk_areas=["현금흐름"],
                    risk_level="Low",
                    summary="출처 기반 맥락",
                    evidence=["기사: https://example.com/news"],
                ).model_dump(mode="json")
            ],
            "cross_check": [],
            "summary": None,
        }
    )

    assert "https://example.com/news" in rendered
