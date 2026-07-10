import asyncio

from src.report.investigator import InvestigationDeps, needs_tool_loop, run_investigation
from src.schemas.findings import AccountFinding, IssueType
from src.schemas.investigation import InvestigationConclusion

GATE = {"residual_pct_max": 20.0, "top_leaf_pct_min": 60.0}


def _card() -> AccountFinding:
    return AccountFinding(
        account="CFS:영업이익",
        issue_type=IssueType.EARNINGS_TAX,
        materiality_score=0.5,
        anomaly_score=0.0,
        confidence="Medium",
        cluster_key="CFS:영업이익",
    )


def _decomp(residual_pct: float, rows: list[dict], delta: float = -100.0) -> dict:
    return {
        "parent": "CFS:영업이익",
        "delta": delta,
        "residual": delta * residual_pct / 100,
        "residual_pct": residual_pct,
        "rows": rows,
    }


def test_no_decomposition_needs_loop():
    assert needs_tool_loop(None, GATE) is True


def test_clean_single_driver_skips_loop():
    rows = [
        {"account": "매출총이익", "delta": -90.0},
        {"account": "판매비와관리비", "delta": -8.0},
    ]
    assert needs_tool_loop(_decomp(residual_pct=2.0, rows=rows), GATE) is False


def test_large_residual_needs_loop():
    rows = [{"account": "매출총이익", "delta": -60.0}]
    assert needs_tool_loop(_decomp(residual_pct=40.0, rows=rows), GATE) is True


def test_dispersed_contributions_need_loop():
    rows = [
        {"account": "매출총이익", "delta": -35.0},
        {"account": "판매비와관리비", "delta": -33.0},
        {"account": "기타영업수익", "delta": -30.0},
    ]
    assert needs_tool_loop(_decomp(residual_pct=2.0, rows=rows), GATE) is True


def test_conclusion_attaches_to_card():

    from src.schemas.findings import AccountFinding, IssueType

    card = AccountFinding(
        account="CFS:영업이익",
        issue_type=IssueType.EARNINGS_TAX,
        materiality_score=0.5,
        anomaly_score=0.0,
        confidence="Medium",
        investigation=InvestigationConclusion(
            headline="매출 이탈 주도", resolved=True, method="gate_summary"
        ),
    )
    assert card.investigation.resolved is True


class _FakeResult:
    def __init__(self, output):
        self.output = output

    def usage(self):
        class _U:
            requests = 3

        return _U()


class _FakeAgent:
    def __init__(self, output):
        self._output = output
        self.last_prompt = None

    async def run(self, prompt, **kw):
        self.last_prompt = prompt
        return _FakeResult(self._output)


def test_run_investigation_returns_conclusion_and_sets_method():
    conclusion = InvestigationConclusion(headline="매출 이탈", resolved=True)
    fake = _FakeAgent(conclusion)
    out = asyncio.run(
        run_investigation(
            _card(),
            {"account_level_series": [], "target_year": 2025},
            decomposition=None,  # 분해 없음 → 도구 루프 경로
            config={"investigation": {"gate": {}, "loop": {"max_requests": 8}}},
            agent_factory=lambda **kw: fake,
        )
    )
    assert out.headline == "매출 이탈"
    assert out.method == "tool_loop"  # 게이트 미통과 → 루프 경로 표기
    assert "CFS:영업이익" in fake.last_prompt  # 카드가 프롬프트에 들어감


def test_run_investigation_failure_returns_none():
    class _Boom:
        async def run(self, prompt, **kw):
            raise RuntimeError("api down")

    out = asyncio.run(
        run_investigation(
            _card(),
            {"account_level_series": [], "target_year": 2025},
            decomposition=None,
            config={},
            agent_factory=lambda **kw: _Boom(),
        )
    )
    assert out is None  # 실패 = None — '조사 미수행' 표기(둔갑 금지)


def test_tools_read_report_deterministically():
    deps = InvestigationDeps(
        series_rows=[
            {"series_key": "CFS:매출", "year": 2024, "amount": 100.0},
            {"series_key": "CFS:매출", "year": 2025, "amount": 80.0},
        ],
        target_year=2025,
        bridges={},
        note_facts=[{"label": "반도체 부문", "value": "12345"}],
    )
    from src.report.investigator import _find_notes, _get_series, _top_changes

    assert _get_series(deps, "CFS:매출") == {2024: 100.0, 2025: 80.0}
    assert _find_notes(deps, "반도체") == [{"label": "반도체 부문", "value": "12345"}]
    movers = _top_changes(deps)
    assert movers[0]["series_key"] == "CFS:매출" and movers[0]["delta"] == -20.0
