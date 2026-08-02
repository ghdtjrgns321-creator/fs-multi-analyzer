import asyncio
import inspect
from types import SimpleNamespace

import pandas as pd

import src.peers.benchmark as benchmark_module
import src.report.external as external_module
from src.agents.gemini_retry import MODEL_NAME
from src.report.external import create_external_assessment
from src.report.external_agentic import (
    EXTERNAL_MODEL_NAME,
    SearchKeywords,
    generate_search_keywords,
)
from src.report.industry import create_industry_assessment, industry_material
from src.report.integrated import build_review_queue, summarize_ratio_categories
from src.report.perspectives import OPENAI_MODEL_NAME as PERSPECTIVE_MODEL_NAME
from src.report.perspectives import PerspectiveAssessment, create_perspective_assessment
from src.schemas.context import ContextBrief, ContextItem
from src.schemas.findings import AccountFinding, EvidenceRef, IssueType


def sample_finding(account: str, risk: str, score: float) -> AccountFinding:
    return AccountFinding(
        account=account,
        issue_type=IssueType.REVENUE_RECEIVABLES,
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


def test_flow_material_no_queue_keeps_relational_inputs() -> None:
    # 큐(등수 힌트) 제거 후에도 흐름 관점은 관계신호(snapshot)·미매핑·시계열을 받는다.
    from src.report.materials import flow_material

    material = flow_material(
        {
            "review_queue": [{"subject": "영업이익", "key_evidence": "growth_divergence: 20"}],
            "ratio_summary": {"이익의 질": {"영업CF/순이익": 1.2}},
            "ratio_time_series": [
                {"name": "DIO", "year": 2019, "value": 1.0, "category": "activity"}
            ],
            "latest_signal_snapshot": {"growth_divergences": []},
            "account_metrics_panel": [{"account": "유형자산취득"}],
            "unmapped_material_accounts": [{"label": "확장"}],
        }
    )

    assert "flow_queue_reference" not in material
    assert "review_queue_reference" not in material
    assert "latest_signal_snapshot" in material
    # panel은 컬럼형({columns, rows})으로 전달 — 계정은 rows에 보존(중복 series는 제거).
    assert "account_level_series" not in material
    panel = material["account_metrics_panel"]
    assert panel["columns"][0] == "account"
    assert panel["rows"][0][0] == "유형자산취득"
    assert material["unmapped_material_accounts"] == [{"label": "확장"}]


def test_numeric_material_full_series_no_queue() -> None:
    # 등수 힌트(review_queue) 없이 전 계정 계산값(panel)·시계열을 받는다.
    # 중복 account_level_series는 board에서 제거(panel이 같은 계정·금액을 압축 보유).
    from src.report.materials import numeric_material

    material = numeric_material(
        {
            "review_queue": [{"subject": "매출채권"}],
            "ratio_summary": {"활동성": {"DIO": 432.0}},
            "ratio_time_series": [{"name": "DIO", "year": 2019, "value": 432.0}],
            "account_level_series": [{"series_key": "재고자산", "year": 2019, "amount": 100.0}],
            "account_metrics_panel": [{"account": "재고자산"}],
            "latest_signal_snapshot": {},
        }
    )

    assert "review_queue_reference" not in material
    assert material["ratio_time_series"][0]["name"] == "DIO"
    # 중복 series 제거 + panel 컬럼형으로 계정 보존.
    assert "account_level_series" not in material
    panel = material["account_metrics_panel"]
    assert panel["rows"][0][0] == "재고자산"
    assert "후보 목록은 제공하지 않는다" in material["judgment_role"]


def test_unmapped_material_excludes_sce_keeps_real_accounts() -> None:
    """SCE(자본변동표) 합계행은 '기타 중요 계정'에서 제외, 진짜 미매핑 BS계정은 유지.

    회귀 방지: SCE '기초'·'자본총계' 행이 unmapped material에 노이즈로 실리던 갭.
    SCE는 전용 2D 테이블이 담당(AGENDA_DD_SCE2D) → 메인 unmapped material에서 빼야 함.
    """

    from src.report.company_report import _top_unmapped_material_accounts

    frame = pd.DataFrame(
        [
            {  # 진짜 미매핑 BS 계정(무표준코드) — 유지돼야
                "corp_code": "00688996",
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "기타 중요 계정",
                "account_id": "-표준계정코드 미사용-",
                "label": "투자금융자산",
                "amount": 131_000_000_000_000.0,
                "mapping_status": "unmapped_extension_account",
            },
            {  # SCE 합계행 — 노이즈, 제외돼야
                "corp_code": "00688996",
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "SCE",
                "canonical": "기타 중요 계정",
                "account_id": "dart_EquityAtBeginningOfPeriod",
                "label": "기초",
                "amount": 56_000_000_000_000.0,
                "mapping_status": "unmapped_extension_account",
            },
        ]
    )
    out = _top_unmapped_material_accounts(frame, 2024)
    labels = {row["label"] for row in out}
    assert "투자금융자산" in labels  # 진짜 계정 유지
    assert "기초" not in labels  # SCE 노이즈 제외
    assert all(row["sj_div"] != "SCE" for row in out)


def test_unmapped_material_surfaces_for_ofs_only_company() -> None:
    """별도(OFS)만 있는 단일실체 회사도 미매핑 '기타 중요 계정'이 게시돼야 한다.

    회귀 방지: fs_div=='CFS' 하드코딩이라 OFS 전용사(연결 없는 중소기업)는 미매핑이
    통째 누락됐다(설계: unmapped는 버리지 않고 게시).
    """

    from src.report.company_report import _top_unmapped_material_accounts

    frame = pd.DataFrame(
        [
            {
                "corp_code": "00160375",
                "year": 2024,
                "fs_div": "OFS",  # 연결 없음 = OFS 전용
                "sj_div": "BS",
                "canonical": "기타 중요 계정",
                "account_id": "ext_SpecialAsset",
                "label": "특수자산",
                "amount": 5_000_000_000.0,
                "mapping_status": "unmapped_extension_account",
            }
        ]
    )
    out = _top_unmapped_material_accounts(frame, 2024)
    assert len(out) == 1
    assert out[0]["label"] == "특수자산"


def test_company_report_target_year_follows_data_not_literal(monkeypatch) -> None:
    """최신 가용연도가 2024인 회사면 target도 2024여야 한다(리터럴 2025 구동 금지, §3).

    회귀 방지: 과거엔 target=max(DEFAULT_YEARS)=2025 고정이라, 2025 미제출사는
    전 신호가 빈값(review_queue=0)으로 LLM에 아무것도 안 넘어갔다.
    """

    from src.report import company_report as company_report_module

    frame = pd.DataFrame(
        [
            {
                "corp_code": "00258801",
                "year": y,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": "자산총계",
                "account_id": "ifrs-full_Assets",
                "label": "자산총계",
                "amount": 100.0,
                "mapping_status": "exact_taxonomy_match",
            }
            for y in (2022, 2023, 2024)  # 2025 부재(미제출)
        ]
    )
    empty_signal_report = {
        "growth_divergences": pd.DataFrame(columns=["year"]),
        "direction_checks": pd.DataFrame(columns=["year"]),
        "primary_yoy": pd.DataFrame(columns=["year"]),
        "reference_yoy": pd.DataFrame(columns=["year"]),
    }
    monkeypatch.setattr(company_report_module, "load_normalized_financials", lambda *a: frame)
    monkeypatch.setattr(
        company_report_module, "build_mvp1_signal_report", lambda *a, **k: empty_signal_report
    )
    monkeypatch.setattr(company_report_module, "extract_red_flags", lambda *a, **k: [])
    monkeypatch.setattr(company_report_module, "scan_universal_signals", lambda *a, **k: [])
    monkeypatch.setattr(company_report_module, "scan_cfs_ofs_gaps", lambda *a, **k: [])
    monkeypatch.setattr(
        company_report_module,
        "build_ratio_report",
        lambda *a, **k: pd.DataFrame(
            columns=["id", "category", "name", "year", "value", "status", "basis"]
        ),
    )
    monkeypatch.setattr(company_report_module, "load_ratio_config", lambda: [])
    monkeypatch.setattr(company_report_module, "load_findings_from_report", lambda *a: [])

    # years를 명시(2025 포함)해도 데이터에 2025가 없으면 target은 2024
    report = company_report_module.build_company_report(
        corp_code="00258801",
        years=[2022, 2023, 2024, 2025],
        company_provider=lambda corp_code: {"stock_name": "카카오"},
    )
    assert report["target_year"] == 2024


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
    # SCE(2D 격자)는 평면 account_level_series에서 제외 — 전용 sce_components 테이블이 전담.
    # 평면서 합계·member 셀이 뭉개져 거짓 재작성 신호를 내던 근본원인 차단(phase3).
    assert {"BS", "CF", "CIS"} <= material_sj_divs
    assert "SCE" not in material_sj_divs


def test_ratio_summary_groups_latest_values_by_category() -> None:
    summary = summarize_ratio_categories(ratio_frame(), target_year=2024)

    assert summary["수익성"]["ROE"] == 9.0
    assert "ROI" not in summary["수익성"]


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


def test_flow_and_trend_perspectives_accept_mock_agent(monkeypatch) -> None:
    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            perspective = "flow" if '"perspective": "flow"' in prompt else "trend"
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
    trend = asyncio.run(create_perspective_assessment("trend", {}, FakeAgent, (0,)))

    assert flow.perspective == "flow"
    assert trend.perspective == "trend"


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


def test_query_generation_sanitizes_speculative_terms() -> None:
    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            return SimpleNamespace(
                output=SearchKeywords(queries=["회계부정", "삼성전자 2025 매출채권 DSO"])
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


def test_account_level_series_keeps_all_accounts_no_count_cap() -> None:
    """결함①: account_level_series가 개수상한(구 limit=40)으로 큰 계정을 떨구면 안 된다.

    강등 많은 금융사는 유의성 큰 계정이 상한 밖으로 밀려 LLM material에 누락됐다.
    PLAN §3(모든 정보 추출 → 에이전트가 가져감) — 코드가 개수로 미리 자르지 않는다.
    """

    from src.report.company_report import _account_level_series

    frame = pd.DataFrame(
        [
            {
                "corp_code": "00000000",
                "year": 2024,
                "fs_div": "CFS",
                "sj_div": "BS",
                "canonical": f"계정{i:03d}",
                "account_id": f"id{i}",
                "label": f"계정{i:03d}",
                "amount": float(1000 - i),
                "mapping_status": "exact_taxonomy_match",
            }
            for i in range(50)  # 구 상한 40 초과
        ]
    )
    out = _account_level_series(frame, [2024], 2024)
    keys = {row["series_key"] for row in out}
    assert len(keys) == 50  # 40개로 잘리지 않고 전부 전달


def test_slim_dimensions_lossless_compression() -> None:
    """XBRL 축 문자열 무손실 축약 — 변별 토큰 보존, boilerplate만 제거."""
    from src.report.company_report import _slim_dimensions

    raw = "ConsolidatedAndSeparateFinancialStatementsAxis=SeparateMember|CategoriesOfRelatedPartiesAxis=SubsidiariesMember"
    assert _slim_dimensions(raw) == "Separate·Subsidiaries"
    assert _slim_dimensions("") == ""
    assert _slim_dimensions(None) == ""
    # 연결/별도 변별 보존(stage#1 이질병합 방지와 일관)
    assert "Consolidated" in _slim_dimensions(
        "ConsolidatedAndSeparateFinancialStatementsAxis=ConsolidatedMember"
    )


def test_account_level_series_includes_ofs_and_separates_fs_div() -> None:
    """OFS 개방: account_level_series가 CFS만이 아니라 OFS 계정도 싣고,
    동명계정(차입금)이 CFS/OFS에서 series_key 접두로 분리돼 합산되지 않는다."""
    from src.report.company_report import _account_level_series

    frame = pd.DataFrame(
        [
            {
                "corp_code": "00000000",
                "year": year,
                "fs_div": fs,
                "sj_div": "BS",
                "canonical": "차입금",
                "account_id": "id",
                "label": "차입금",
                "amount": amt,
                "mapping_status": "exact_taxonomy_match",
            }
            for fs, base in (("CFS", 100.0), ("OFS", 30.0))
            for year, amt in ((2023, base), (2024, base * 2))
        ]
    )
    out = _account_level_series(frame, [2023, 2024], 2024)
    assert {row["fs_div"] for row in out} == {"CFS", "OFS"}  # OFS 포함(누락 0)
    keys = {row["series_key"] for row in out}
    assert len(keys) == 2  # CFS 차입금·OFS 차입금이 별개 키(합산 X)
    assert any(k.startswith("CFS") for k in keys)
    assert any(k.startswith("OFS") for k in keys)


def test_unmapped_material_no_head_cap_and_includes_id_label_conflict() -> None:
    """결함①: head(5) 제거 + id_label_conflict 강등(canonical='기타 중요 계정') 포함.

    회귀 방지: 금융사 핵심 손익(순이자손익 등)이 id_label_conflict로 강등되면
    canonical='기타 중요 계정'인데도 mapping_status 조건에서 빠져 누락됐다.
    """

    from src.report.company_report import _top_unmapped_material_accounts

    rows = [
        {  # 5건 초과 — head(5)로 잘리면 안 됨
            "corp_code": "00000000",
            "year": 2024,
            "fs_div": "CFS",
            "sj_div": "BS",
            "canonical": "기타 중요 계정",
            "account_id": "-표준계정코드 미사용-",
            "label": f"확장계정{i}",
            "amount": float(100 - i),
            "mapping_status": "unmapped_extension_account",
        }
        for i in range(6)
    ]
    rows.append(
        {  # id_label_conflict 강등 — canonical='기타'인데 구 조건에서 누락되던 케이스
            "corp_code": "00000000",
            "year": 2024,
            "fs_div": "CFS",
            "sj_div": "CF",
            "canonical": "기타 중요 계정",
            "account_id": "dart_NetInterestIncome",
            "label": "순이자손익",
            "amount": -196_100_000_000.0,
            "mapping_status": "id_label_conflict",
        }
    )
    out = _top_unmapped_material_accounts(pd.DataFrame(rows), 2024)
    labels = {row["label"] for row in out}
    assert "순이자손익" in labels  # id_label_conflict 강등 포함
    assert sum(1 for row in out if row["label"].startswith("확장계정")) == 6  # head(5) 아님


def test_perspective_rules_prioritize_materiality_without_ignoring_small(monkeypatch) -> None:
    """가드: 큰 항목 우선 검토하되 작아도 추세·부호 이상이면 함께 본다('무시' 강표현 금지)."""

    captured: dict[str, str] = {}

    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            captured["prompt"] = prompt
            return SimpleNamespace(
                output=PerspectiveAssessment(
                    perspective="numeric",
                    status="completed",
                    risk_areas=[],
                    risk_level="Low",
                    summary="검토",
                    evidence=[],
                )
            )

    monkeypatch.setattr("src.report.perspectives.settings.openai_api_key", "fake")
    asyncio.run(create_perspective_assessment("numeric", {}, FakeAgent, (0,)))

    assert "유의성" in captured["prompt"]  # 큰 항목 우선 가드 도달
    assert "무시" not in captured["prompt"]  # 강표현 금지(작은 잔액도 패턴 있으면 검토)
