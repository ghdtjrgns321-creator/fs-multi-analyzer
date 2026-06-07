import asyncio
import inspect
from types import SimpleNamespace

import pandas as pd

import src.peers.benchmark as benchmark_module
import src.report.external as external_module
from src.agents.gemini_retry import MODEL_NAME
from src.report.crosscheck import cross_check_assessments
from src.report.external import create_external_assessment
from src.report.external_agentic import (
    EXTERNAL_MODEL_NAME,
    SearchKeywords,
    generate_search_keywords,
)
from src.report.industry import create_industry_assessment, industry_material
from src.report.integrated import build_review_queue, summarize_ratio_categories
from src.report.multi_agent import build_multi_agent_report, render_multi_agent_markdown
from src.report.perspectives import OPENAI_MODEL_NAME as PERSPECTIVE_MODEL_NAME
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


def test_review_queue_exposes_unmapped_material_accounts() -> None:
    queue = build_review_queue(
        [],
        ratio_frame(),
        ratio_config(),
        target_year=2024,
        red_flags=[],
        unmapped_rows=[
            {
                "year": 2024,
                "label": "회사확장계정",
                "account_id": "-표준계정코드 미사용-",
                "amount": 1234.0,
            }
        ],
    )

    item = next(item for item in queue if item.item_type == "unmapped_material_account")
    assert item.subject == "회사확장계정"
    assert item.issue == "미등록 중요 계정"


def test_flow_material_includes_is_cf_flow_items() -> None:
    from src.report.materials import flow_material

    material = flow_material(
        {
            "review_queue": [
                {
                    "subject": "투자활동현금흐름",
                    "key_evidence": "single_account_yoy: -80",
                },
                {
                    "subject": "영업이익",
                    "key_evidence": "growth_divergence: 20",
                },
            ],
            "ratio_summary": {"이익의 질": {"영업CF/순이익": 1.2}},
            "latest_signal_snapshot": {},
            "unmapped_material_accounts": [{"label": "확장"}],
        }
    )

    subjects = {item["subject"] for item in material["flow_queue_reference"]}
    assert {"투자활동현금흐름", "영업이익"}.issubset(subjects)
    assert material["unmapped_material_accounts"] == [{"label": "확장"}]


def test_numeric_material_includes_full_series_not_only_queue() -> None:
    from src.report.materials import numeric_material

    material = numeric_material(
        {
            "review_queue": [{"subject": "매출채권"}],
            "ratio_summary": {"활동성": {"DIO": 432.0}},
            "ratio_time_series": [{"name": "DIO", "year": 2019, "value": 432.0}],
            "account_level_series": [{"series_key": "재고자산", "year": 2019, "amount": 100.0}],
            "latest_signal_snapshot": {},
        }
    )

    assert material["review_queue_reference"] == [{"subject": "매출채권"}]
    assert material["ratio_time_series"][0]["name"] == "DIO"
    assert material["account_level_series"][0]["series_key"] == "재고자산"
    assert "정답이 아니다" in material["queue_role"]


def test_company_report_keeps_restatements_out_of_review_queue_but_in_snapshot(monkeypatch) -> None:
    from src.report import company_report as company_report_module
    from src.schemas.findings import EvidenceRef
    from src.signals.red_flags import RedFlagSignal

    restatement = RedFlagSignal(
        id="restatement:account_id_label:ifrs-full_IntangibleAssets|무형자산:CFS:BS:2024",
        year=2024,
        account="무형자산",
        signal_type="restatement",
        description="전기 비교표시 금액과 전년도 공시 당기 금액 괴리",
        metric_value=-108_537_593_133.0,
        evidence=[EvidenceRef(source="financial_statement", locator="x", year="2024")],
    )

    frame = pd.DataFrame(
        [
            {
                "corp_code": "00413046",
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "무형자산",
                "account_id": "ifrs-full_IntangibleAssets",
                "label": "무형자산",
                "amount": 100.0,
                "mapping_status": "exact_taxonomy_match",
            }
        ]
    )
    empty_signal_report = {
        "growth_divergences": pd.DataFrame(columns=["year"]),
        "direction_checks": pd.DataFrame(columns=["year"]),
        "primary_yoy": pd.DataFrame(columns=["year"]),
        "reference_yoy": pd.DataFrame(columns=["year"]),
    }
    ratio_frame = pd.DataFrame(
        columns=["id", "category", "name", "year", "value", "status", "basis"]
    )

    monkeypatch.setattr(company_report_module, "load_normalized_financials", lambda *args: frame)
    monkeypatch.setattr(
        company_report_module,
        "build_mvp1_signal_report",
        lambda *args, **kwargs: empty_signal_report,
    )
    monkeypatch.setattr(company_report_module, "extract_red_flags", lambda *args, **kwargs: [])
    monkeypatch.setattr(company_report_module, "scan_universal_signals", lambda *args, **kwargs: [])
    monkeypatch.setattr(company_report_module, "scan_cfs_ofs_gaps", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        company_report_module,
        "scan_restatement_signals",
        lambda *args, **kwargs: [restatement],
    )
    monkeypatch.setattr(
        company_report_module,
        "build_ratio_report",
        lambda *args, **kwargs: ratio_frame,
    )
    monkeypatch.setattr(company_report_module, "load_ratio_config", lambda: [])
    monkeypatch.setattr(company_report_module, "load_findings_from_report", lambda *args: [])

    report = company_report_module.build_company_report(
        corp_code="00413046",
        years=[2024],
        company_provider=lambda corp_code: {"stock_name": "셀트리온"},
    )

    assert not any(
        "restatement" in str(item["key_evidence"]) for item in report["review_queue"]
    )
    assert report["latest_signal_snapshot"]["restatements"][0]["account"] == "무형자산"


def test_company_report_keeps_non_bs_is_universal_out_of_queue_but_in_material(
    monkeypatch,
) -> None:
    from src.report import company_report as company_report_module
    from src.schemas.findings import EvidenceRef
    from src.signals.red_flags import RedFlagSignal

    cf_signal = RedFlagSignal(
        id="universal_yoy:cf:2024",
        year=2024,
        account="영업활동현금흐름",
        signal_type="universal_yoy",
        description="CF universal",
        metric_value=200.0,
        evidence=[EvidenceRef(source="financial_statement", locator="cf", year="2024")],
        sj_div="CF",
    )
    cis_signal = RedFlagSignal(
        id="universal_yoy:cis:2024",
        year=2024,
        account="총포괄손익",
        signal_type="universal_yoy",
        description="CIS universal",
        metric_value=150.0,
        evidence=[EvidenceRef(source="financial_statement", locator="cis", year="2024")],
        sj_div="CIS",
    )
    bs_signal = RedFlagSignal(
        id="universal_yoy:bs:2024",
        year=2024,
        account="재고자산",
        signal_type="universal_yoy",
        description="BS universal",
        metric_value=100.0,
        evidence=[EvidenceRef(source="financial_statement", locator="bs", year="2024")],
        sj_div="BS",
    )
    frame = pd.DataFrame(
        [
            {
                "corp_code": "00000000",
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": sj_div,
                "canonical": canonical,
                "account_id": account_id,
                "label": canonical,
                "amount": amount,
                "mapping_status": "exact_taxonomy_match",
            }
            for sj_div, canonical, account_id, amount in [
                ("BS", "재고자산", "ifrs-full_Inventories", 100.0),
                (
                    "CF",
                    "영업활동현금흐름",
                    "ifrs-full_CashFlowsFromUsedInOperatingActivities",
                    90.0,
                ),
                ("CIS", "총포괄손익", "ifrs-full_ComprehensiveIncome", 80.0),
                ("SCE", "자기주식변동", "dart_TreasuryShareTransactions", 70.0),
            ]
        ]
    )
    empty_signal_report = {
        "growth_divergences": pd.DataFrame(columns=["year"]),
        "direction_checks": pd.DataFrame(columns=["year"]),
        "primary_yoy": pd.DataFrame(columns=["year"]),
        "reference_yoy": pd.DataFrame(columns=["year"]),
    }
    ratio_frame = pd.DataFrame(
        columns=["id", "category", "name", "year", "value", "status", "basis"]
    )

    monkeypatch.setattr(company_report_module, "load_normalized_financials", lambda *args: frame)
    monkeypatch.setattr(
        company_report_module,
        "build_mvp1_signal_report",
        lambda *args, **kwargs: empty_signal_report,
    )
    monkeypatch.setattr(company_report_module, "extract_red_flags", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        company_report_module,
        "scan_universal_signals",
        lambda *args, **kwargs: [cf_signal, cis_signal, bs_signal],
    )
    monkeypatch.setattr(company_report_module, "scan_cfs_ofs_gaps", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        company_report_module,
        "scan_restatement_signals",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        company_report_module,
        "build_ratio_report",
        lambda *args, **kwargs: ratio_frame,
    )
    monkeypatch.setattr(company_report_module, "load_ratio_config", lambda: [])
    monkeypatch.setattr(company_report_module, "load_findings_from_report", lambda *args: [])

    report = company_report_module.build_company_report(
        corp_code="00000000",
        years=[2024],
        company_provider=lambda corp_code: {"stock_name": "테스트"},
    )

    queue_subjects = {item["subject"] for item in report["review_queue"]}
    snapshot_accounts = {
        item["account"] for item in report["latest_signal_snapshot"]["universal_scan"]
    }
    material_sj_divs = {item["sj_div"] for item in report["account_level_series"]}

    assert "재고자산" in queue_subjects
    assert "영업활동현금흐름" not in queue_subjects
    assert "총포괄손익" not in queue_subjects
    assert {"영업활동현금흐름", "총포괄손익", "재고자산"} <= snapshot_accounts
    assert {"BS", "CF", "CIS", "SCE"} <= material_sj_divs


def test_ratio_summary_groups_latest_values_by_category() -> None:
    summary = summarize_ratio_categories(ratio_frame(), target_year=2024)

    assert summary["수익성"]["ROE"] == 9.0
    assert "ROI" not in summary["수익성"]


def test_integrated_summary_accepts_mock_agent(monkeypatch) -> None:
    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            assert "review_queue" in prompt
            return SimpleNamespace(output="실제 데이터에 근거한 가능성 중심 종합 문단")

    monkeypatch.setattr("src.report.synthesis.settings.openai_api_key", "fake")
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

    monkeypatch.setattr("src.report.perspectives.settings.openai_api_key", "fake")
    result = asyncio.run(
        create_perspective_assessment("numeric", {"review_queue": []}, FakeAgent, (0,))
    )

    assert result.perspective == "numeric"
    assert result.status == "completed"


def test_multi_agent_report_has_six_independent_perspectives() -> None:
    result = asyncio.run(build_multi_agent_report(run_llm=False))

    perspectives = {item["perspective"] for item in result["perspective_assessments"]}

    assert perspectives == {"numeric", "note", "flow", "change", "external", "industry"}
    assert set(result["materials"]) == {"numeric", "note", "flow", "change", "external", "industry"}


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

    monkeypatch.setattr("src.report.perspectives.settings.openai_api_key", "fake")

    flow = asyncio.run(create_perspective_assessment("flow", {}, FakeAgent, (0,)))
    change = asyncio.run(create_perspective_assessment("change", {}, FakeAgent, (0,)))

    assert flow.perspective == "flow"
    assert change.perspective == "change"


def test_change_perspective_prompt_guides_restatement_as_context_not_queue(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            captured["prompt"] = prompt
            return SimpleNamespace(
                output=PerspectiveAssessment(
                    perspective="change",
                    status="completed",
                    risk_areas=[],
                    risk_level="Low",
                    summary="정상 소급 가능성을 우선 검토한다.",
                    evidence=[],
                )
            )

    monkeypatch.setattr("src.report.perspectives.settings.openai_api_key", "fake")

    asyncio.run(
        create_perspective_assessment(
            "change",
            {
                "review_queue_reference": [],
                "restatement_signals": [
                    {
                        "account": "무형자산",
                        "signal_type": "restatement",
                        "metric_value": -108_537_593_133.0,
                    }
                ],
            },
            FakeAgent,
            (0,),
        )
    )

    assert "소급재작성은 회계정책 변경" in captured["prompt"]
    assert "정상 소급은 위험으로 보지 말고" in captured["prompt"]
    assert "이익·자산을 과대계상했다가 하향 재작성" in captured["prompt"]


def test_external_perspective_runs_query_search_and_eval_mocks() -> None:
    class FakeQueryAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            assert "latest_signal_snapshot" in prompt
            return SimpleNamespace(
                output=SearchKeywords(queries=["삼성전자 2025 매출채권 회수 지연"])
            )

    class FakeEvalAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            assert "매출채권 회수 지연 뉴스" in prompt
            assert "review_queue" not in prompt
            return SimpleNamespace(
                output=PerspectiveAssessment(
                    perspective="external",
                    status="completed",
                    risk_areas=["매출채권/수익"],
                    risk_level="Low",
                    summary="출처 기반 외부 맥락은 내부 매출채권 검토 후보와 같은 방향이다.",
                    evidence=[],
                )
            )

    async def fake_context(queries: list[str], retry_delays: tuple[float, ...]) -> ContextBrief:
        assert queries == ["삼성전자 2025 매출채권 회수 지연"]
        assert retry_delays == (0,)
        return ContextBrief(
            items=[
                ContextItem(
                    claim="매출채권 회수 지연 뉴스가 보도되었다.",
                    source_title="기사",
                    source_url="https://example.com/news",
                )
            ]
        )

    report = {
        "company_name": "삼성전자",
        "target_year": 2025,
        "review_queue": [{"subject": "매출채권"}, {"subject": "재고자산"}],
        "ratio_summary": {"활동성": {"DSO": 51.83}},
        "latest_signal_snapshot": {"primary_yoy": [{"canonical": "매출채권"}]},
    }

    result = asyncio.run(
        create_external_assessment(
            report,
            fake_context,
            query_agent_factory=FakeQueryAgent,
            eval_agent_factory=FakeEvalAgent,
            retry_delays=(0,),
        )
    )

    assert result.perspective == "external"
    assert result.status == "completed"
    assert result.risk_level == "Low"
    assert result.evidence == [
        "검색어: 삼성전자 2025 매출채권 회수 지연",
        "기사: https://example.com/news",
    ]


def test_industry_benchmark_uses_peer_median_and_target_percentile(tmp_path, monkeypatch) -> None:
    config = tmp_path / "peers.yaml"
    config.write_text(
        """
targets:
industries:
  "264":
    selection: {max_peers: 2}
    caveat: 단순 비교 한계
    peers:
      - {corp_code: "00401731", company_name: LG전자, stock_code: "066570", industry_code: "264"}
      - {corp_code: "00441304", company_name: 가온그룹, stock_code: "078890", industry_code: "264"}
""",
        encoding="utf-8",
    )

    def fake_ratios(frame: pd.DataFrame, years: list[int]) -> pd.DataFrame:
        corp = frame["corp_code"].iloc[0]
        value = {"00126380": 12.0, "00401731": 10.0, "00441304": 20.0}[corp]
        return pd.DataFrame(
            [
                {
                    "id": "roe",
                    "category": "profitability",
                    "name": "ROE",
                    "year": 2025,
                    "value": value,
                    "status": "computed",
                }
            ]
        )

    monkeypatch.setattr(
        benchmark_module,
        "load_normalized_financials",
        lambda corp_code, years: pd.DataFrame({"corp_code": [corp_code]}),
    )
    monkeypatch.setattr(benchmark_module, "build_ratio_report", fake_ratios)

    result = benchmark_module.build_industry_benchmark(
        "00126380",
        [2024, 2025],
        peer_config_path=config,
        company_profile={"stock_name": "삼성전자", "induty_code": "264"},
        ensure_data=lambda *args, **kwargs: None,
    )

    row = result["baseline"][0]
    assert row["peer_median"] == 15.0
    assert row["target_percentile"] == 50.0
    assert result["peers"][0]["corp_code"] == "00401731"


def test_industry_benchmark_uses_middle_class_industry_key(tmp_path, monkeypatch) -> None:
    config = tmp_path / "peers.yaml"
    config.write_text(
        """
industries:
  "313":
    selection: {max_peers: 1}
    peers:
      - {corp_code: "00000001", company_name: 피어, stock_code: "000001", industry_code: "313"}
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        benchmark_module,
        "load_normalized_financials",
        lambda corp_code, years: pd.DataFrame({"corp_code": [corp_code]}),
    )
    monkeypatch.setattr(
        benchmark_module,
        "build_ratio_report",
        lambda frame, years: pd.DataFrame(
            [
                {
                    "id": "roe",
                    "category": "profitability",
                    "name": "ROE",
                    "year": 2019,
                    "value": 1.0,
                    "status": "computed",
                }
            ]
        ),
    )

    result = benchmark_module.build_industry_benchmark(
        "00409681",
        [2018, 2019],
        peer_config_path=config,
        company_profile={"stock_name": "아스트", "induty_code": "31322"},
        ensure_data=lambda *args, **kwargs: None,
    )

    assert result["industry_code"] == "313"
    assert result["raw_industry_code"] == "31322"
    assert result["peers"][0]["industry_code"] == "313"


def test_industry_perspective_accepts_mock_agent(monkeypatch) -> None:
    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            assert "peer-ratio" in prompt or "피어" in prompt
            return SimpleNamespace(
                output=PerspectiveAssessment(
                    perspective="industry",
                    status="completed",
                    risk_areas=["수익성"],
                    risk_level="Low",
                    summary="동종업계 대비 참고 신호만 제시한다.",
                    evidence=["ROE 업종 중앙값"],
                )
            )

    report = {
        "corp_code": "00126380",
        "company_name": "삼성전자",
        "years": [2024, 2025],
        "target_year": 2025,
        "review_queue": [],
    }
    benchmark = {
        "target_year": 2025,
        "peers": [],
        "baseline": [{"name": "ROE", "target_value": 12.0, "peer_median": 15.0}],
    }
    monkeypatch.setattr("src.report.perspectives.settings.openai_api_key", "fake")

    material = industry_material(report, lambda *args, **kwargs: benchmark)
    result = asyncio.run(
        create_industry_assessment(
            report,
            benchmark_factory=lambda *args, **kwargs: benchmark,
            agent_factory=FakeAgent,
            retry_delays=(0,),
        )
    )

    assert material["benchmark"]["baseline"][0]["name"] == "ROE"
    assert result.perspective == "industry"
    assert result.status == "completed"


def test_industry_perspective_defers_when_peer_config_missing(tmp_path) -> None:
    config = tmp_path / "peers.yaml"
    config.write_text("industries: {}\n", encoding="utf-8")

    result = benchmark_module.build_industry_benchmark
    try:
        result(
            "12345678",
            [2024, 2025],
            peer_config_path=config,
            company_profile={"stock_name": "테스트회사", "induty_code": "999"},
            ensure_data=lambda *args, **kwargs: None,
        )
    except Exception as exc:
        assert "피어 미구성" in str(exc)
    else:
        raise AssertionError("missing peer config should defer/fail gracefully")


def test_cross_check_industry_reference_does_not_mutate_internal_judgment() -> None:
    numeric = PerspectiveAssessment(
        perspective="numeric",
        status="completed",
        risk_areas=["수익성"],
        risk_level="Medium",
        summary="수익성 검토 필요",
        evidence=[],
    )
    industry = PerspectiveAssessment(
        perspective="industry",
        status="completed",
        risk_areas=["수익성"],
        risk_level="Low",
        summary="업종 대비 낮은 위치이나 참고 신호다.",
        evidence=["ISA/KSA 520"],
    )

    result = cross_check_assessments([numeric, industry])

    assert result[0].verdict == "agreement"
    assert "판단 필드" in result[0].comment


def test_query_generation_sanitizes_speculative_terms() -> None:
    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            return SimpleNamespace(
                output=SearchKeywords(
                    queries=["회계부정", "삼성전자 2025 매출채권 DSO"]
                )
            )

    material = {"company_name": "삼성전자", "target_year": 2025}

    result = asyncio.run(generate_search_keywords(material, FakeAgent, retry_delays=(0,)))

    assert result.queries == ["삼성전자 2025 재무지표 변화 원인"]


def test_external_query_generation_uses_separate_pro_model() -> None:
    assert MODEL_NAME == "gemini-2.5-flash"
    assert PERSPECTIVE_MODEL_NAME == "gpt-5.4"
    assert EXTERNAL_MODEL_NAME == "gemini-3.1-pro-preview"
    assert EXTERNAL_MODEL_NAME != MODEL_NAME
    assert EXTERNAL_MODEL_NAME != PERSPECTIVE_MODEL_NAME


def test_query_generation_drops_metric_acronyms() -> None:
    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            return SimpleNamespace(
                output=SearchKeywords(
                    queries=[
                        "삼성전자 2025 DIO DSO",
                        "삼성전자 2025 매출채권 회수 지연",
                    ]
                )
            )

    material = {"company_name": "삼성전자", "target_year": 2025}

    result = asyncio.run(generate_search_keywords(material, FakeAgent, retry_delays=(0,)))

    assert result.queries == ["삼성전자 2025 매출채권 회수 지연"]


def test_external_query_has_no_account_keyword_mapping_table() -> None:
    source = inspect.getsource(external_module)

    assert "account_query" not in source.lower()
    assert '"매출채권":' not in source
    assert "'매출채권':" not in source


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
