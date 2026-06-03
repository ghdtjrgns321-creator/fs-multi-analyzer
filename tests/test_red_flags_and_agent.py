import asyncio
from types import SimpleNamespace

import pytest
from pydantic_ai.exceptions import ModelHTTPError

from src.agents.guardrails import validate_numeric_finding
from src.agents.numeric_analyst import create_numeric_finding
from src.schemas.findings import AccountFinding, EvidenceRef, IssueType
from src.signals.finding_input import select_account_signals, signals_to_prompt_payload
from src.signals.mvp1 import build_mvp1_signal_report
from src.signals.red_flags import extract_red_flags
from tests.test_analysis_tools import fixture_frame


def valid_finding() -> AccountFinding:
    return AccountFinding(
        account="매출채권",
        issue_type=IssueType.RECEIVABLES_QUALITY,
        materiality_score=0.6,
        anomaly_score=0.7,
        confidence="Medium",
        numeric_evidence=[
            EvidenceRef(
                source="financial_statement",
                locator="매출채권",
                year="2023",
                value="YoY 2.59%",
            )
        ],
        counter_evidence=["다음 연도에 회수 흐름이 개선될 가능성이 있다."],
        normal_explanation=["일시적 거래조건 변화 가능성이 있다."],
        confirm_question=["매출채권 증가 원인을 설명할 내부 자료가 있는가?"],
        next_procedure=["매출채권 연령분석표를 확인한다."],
        risk_level="Medium",
    )


def test_extract_red_flags_uses_config_thresholds(tmp_path) -> None:
    config = tmp_path / "chains.yaml"
    config.write_text(
        """
l2_mvp1:
  primary_fs_div: CFS
  reference_fs_div: CFS
  years: [2022, 2023, 2024]
  yoy_accounts: [매출, 매출채권, 재고자산, 영업활동현금흐름]
  growth_divergences:
    - id: revenue-vs-receivable
      name: 매출 vs 매출채권
      account_a: 매출
      account_b: 매출채권
  direction_checks: []
  deferred_ratios: []
  signal_thresholds:
    divergence_pp_abs: 15
    yoy_pct_abs: 120
    direction_red_flags:
      - id: revenue-down-receivable-up
        name: 매출 감소 + 매출채권 증가
        account_a: 매출
        direction_a: decrease
        account_b: 매출채권
        direction_b: increase
""",
        encoding="utf-8",
    )
    report = build_mvp1_signal_report(fixture_frame(), config)

    signals = extract_red_flags(report, 2024)

    assert {signal.signal_type for signal in signals} == {
        "growth_divergence",
        "direction_mismatch",
    }


def test_guardrails_reject_empty_evidence() -> None:
    finding = valid_finding()
    finding.numeric_evidence = []

    with pytest.raises(Exception, match="numeric_evidence"):
        validate_numeric_finding(finding)


def test_guardrails_reject_unsupported_certainty() -> None:
    finding = valid_finding()
    finding.note_cross_check = "주석 근거가 위험을 명확히 증명합니다."

    with pytest.raises(Exception, match="Unsupported assertion"):
        validate_numeric_finding(finding)


def test_numeric_agent_accepts_fake_client(monkeypatch) -> None:
    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            assert "signals" in prompt
            return SimpleNamespace(output=valid_finding())

    monkeypatch.setattr("src.agents.numeric_analyst.settings.google_api_key", "fake")

    result = asyncio.run(create_numeric_finding({"signals": []}, agent_factory=FakeAgent))

    assert result.account == "매출채권"


def test_numeric_agent_retries_503_then_succeeds(monkeypatch) -> None:
    calls = 0

    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise ModelHTTPError(
                    status_code=503,
                    model_name="gemini-3.5-flash",
                    body={"error": {"status": "UNAVAILABLE"}},
                )
            return SimpleNamespace(output=valid_finding())

    monkeypatch.setattr("src.agents.numeric_analyst.settings.google_api_key", "fake")

    result = asyncio.run(
        create_numeric_finding(
            {"signals": []},
            agent_factory=FakeAgent,
            retry_delays=(0, 0, 0),
        )
    )

    assert calls == 3
    assert result.account == "매출채권"


def test_numeric_agent_retries_503_until_final_failure(monkeypatch) -> None:
    calls = 0

    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            nonlocal calls
            calls += 1
            raise ModelHTTPError(
                status_code=503,
                model_name="gemini-3.5-flash",
                body="This model is currently experiencing high demand.",
            )

    monkeypatch.setattr("src.agents.numeric_analyst.settings.google_api_key", "fake")

    with pytest.raises(RuntimeError, match="Gemini temporary error"):
        asyncio.run(
            create_numeric_finding(
                {"signals": []},
                agent_factory=FakeAgent,
                retry_delays=(0, 0),
            )
        )

    assert calls == 3


def test_numeric_agent_does_not_retry_permanent_4xx(monkeypatch) -> None:
    calls = 0

    class FakeAgent:
        async def run(self, prompt: str) -> SimpleNamespace:
            nonlocal calls
            calls += 1
            raise ModelHTTPError(
                status_code=400,
                model_name="gemini-3.5-flash",
                body={"error": {"status": "INVALID_ARGUMENT"}},
            )

    monkeypatch.setattr("src.agents.numeric_analyst.settings.google_api_key", "fake")

    with pytest.raises(ModelHTTPError):
        asyncio.run(
            create_numeric_finding(
                {"signals": []},
                agent_factory=FakeAgent,
                retry_delays=(0, 0),
            )
        )

    assert calls == 1


def test_prompt_payload_serializes_evidence() -> None:
    report = build_mvp1_signal_report(fixture_frame())
    signals = extract_red_flags(report, 2023)

    payload = signals_to_prompt_payload(signals)

    assert isinstance(payload["signals"][0]["evidence"][0], dict)


def test_select_account_signals_generalizes_beyond_receivables() -> None:
    report = build_mvp1_signal_report(fixture_frame())
    signals = extract_red_flags(report, 2024)

    selected = select_account_signals(signals, account="재고자산", year=2024)

    assert selected
    assert all(signal.account == "재고자산" for signal in selected)


def test_select_account_signals_returns_empty_when_account_has_no_signal() -> None:
    report = build_mvp1_signal_report(fixture_frame())
    signals = extract_red_flags(report, 2023)

    assert select_account_signals(signals, account="차입금", year=2023) == []


def test_l2_config_includes_debt_and_provision_accounts() -> None:
    report = build_mvp1_signal_report(fixture_frame())
    configured = set(report["primary_yoy"]["canonical"].unique())

    assert {
        "단기차입금",
        "장기차입금",
        "사채",
        "충당부채",
        "영업이익",
        "투자활동현금흐름",
        "재무활동현금흐름",
    }.issubset(configured)
