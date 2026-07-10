from src.report.investigator import needs_tool_loop

GATE = {"residual_pct_max": 20.0, "top_leaf_pct_min": 60.0}


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
    from src.schemas.investigation import InvestigationConclusion

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
