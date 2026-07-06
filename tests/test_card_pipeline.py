"""S5 — 카드 파이프라인 mock E2E (PHASE2_DESIGN §9).

6관점 병렬 → 근거검증 → 클러스터 → 정렬·렌더가 끝까지 도는지 mock agent로 확인한다.
"""

from __future__ import annotations

import asyncio

from src.report.card_pipeline import build_suspicion_cards
from src.report.perspective_runner import ALL_PERSPECTIVES
from src.schemas.findings import IssueType
from src.schemas.suspicion import PerspectiveOutput, SuspicionItem


def _report():
    return {
        "corp_code": "x",
        "target_year": "2024",
        "account_level_series": [
            {
                "year": "2024",
                "sj_div": "BS",
                "series_key": "매출채권",
                "canonical": "매출채권",
                "label": "매출채권",
                "amount": 100_000_000.0,
                "mapping_status": "exact",
            }
        ],
        "unmapped_material_accounts": [],
    }


def _canned_runner(canned):
    async def runner(perspective, material):
        return canned.get(perspective, PerspectiveOutput(status="completed"))

    return runner


def _canned_external(canned=None):
    # external은 별도 경로(실검색)라 테스트에선 canned으로 주입(실 API 미호출).
    async def runner(report):
        return (canned or {}).get("external", PerspectiveOutput(status="completed"))

    return runner


def _materials():
    return {name: {} for name in ALL_PERSPECTIVES}


def test_pipeline_builds_account_and_company_cards() -> None:
    canned = {
        "numeric": PerspectiveOutput(
            suspicions=[
                SuspicionItem(
                    perspective="numeric",
                    scope="account",
                    issue_type=IssueType.REVENUE_RECEIVABLES,
                    account_id="매출채권",
                    sj_div="BS",
                    year="2024",
                    cited_value="100,000,000",
                    description="매출채권 급증.",
                )
            ]
        ),
        "external": PerspectiveOutput(
            suspicions=[
                SuspicionItem(
                    perspective="external",
                    scope="company",
                    issue_type=IssueType.CONTINGENCY_RELATED_PARTY,
                    year="2024",
                    description="계속기업 불확실성.",
                    source_url="https://dart.fss.or.kr/x",
                )
            ]
        ),
    }
    result = asyncio.run(
        build_suspicion_cards(
            _report(),
            agent_runner=_canned_runner(canned),
            external_runner=_canned_external(canned),
            materials=_materials(),
        )
    )
    assert [c.account for c in result["account_cards"]] == ["매출채권"]
    assert len(result["company_cards"]) == 1
    assert result["has_findings"] is True
    assert "매출채권" in result["rendered"]


def test_pipeline_drops_ungrounded() -> None:
    canned = {
        "numeric": PerspectiveOutput(
            suspicions=[
                SuspicionItem(
                    perspective="numeric",
                    scope="account",
                    issue_type=IssueType.REVENUE_RECEIVABLES,
                    account_id="없는계정",
                    sj_div="BS",
                    year="2024",
                    cited_value="100,000,000",
                    description="환각 계정.",
                )
            ]
        )
    }
    result = asyncio.run(
        build_suspicion_cards(
            _report(),
            agent_runner=_canned_runner(canned),
            external_runner=_canned_external(canned),
            materials=_materials(),
        )
    )
    assert result["account_cards"] == []
    assert len(result["dropped"]) == 1


def test_pipeline_counts_completed_perspectives() -> None:
    canned = {"numeric": PerspectiveOutput(status="completed")}
    result = asyncio.run(
        build_suspicion_cards(
            _report(),
            agent_runner=_canned_runner(canned),
            external_runner=_canned_external(canned),
            materials=_materials(),
        )
    )
    # numeric completed + 나머지 5개도 기본 completed(빈 의심건) → 6
    assert result["review_scope"]["perspectives_run"] == 6


def test_pipeline_no_llm_deferred() -> None:
    result = asyncio.run(build_suspicion_cards(_report(), run_llm=False))
    assert result["has_findings"] is False
    assert "검토" in result["rendered"]
    assert result["review_scope"]["perspectives_run"] == 0


def test_pipeline_surfaces_failed_perspectives() -> None:
    # 6관점이 전부 LLM 호출 실패(status="failed")면 빈 카드로 둔갑하지 말고 실패를 집계·표면화.
    canned = {name: PerspectiveOutput(status="failed") for name in ALL_PERSPECTIVES}
    result = asyncio.run(
        build_suspicion_cards(
            _report(),
            agent_runner=_canned_runner(canned),
            external_runner=_canned_external(canned),
            materials=_materials(),
        )
    )
    assert result["has_findings"] is False
    assert result["review_scope"]["perspectives_run"] == 0
    assert result["review_scope"]["perspectives_failed"] == 6
    # 거짓 안심 문구 금지, 실패 명시
    assert "위험 후보가 없음" not in result["rendered"]
    assert "실패" in result["rendered"]


def _two_account_report():
    rows = []
    for name, amount in (("매출채권", 100_000_000.0), ("재고자산", 900_000_000.0)):
        rows.append(
            {
                "year": "2024",
                "sj_div": "BS",
                "series_key": name,
                "canonical": name,
                "label": name,
                "amount": amount,
                "mapping_status": "exact",
            }
        )
    return {
        "corp_code": "x",
        "target_year": "2024",
        "account_level_series": rows,
        "unmapped_material_accounts": [],
    }


def _two_card_runner():
    def make(account):
        return SuspicionItem(
            perspective="numeric",
            scope="account",
            issue_type=IssueType.REVENUE_RECEIVABLES,
            account_id=account,
            sj_div="BS",
            year="2024",
            cited_value="100,000,000" if account == "매출채권" else "900,000,000",
            description=f"{account} 의심.",
        )

    canned = {"numeric": PerspectiveOutput(suspicions=[make("매출채권"), make("재고자산")])}
    return _canned_runner(canned)


def test_rebuttal_normal_dominant_sinks_after_pipeline() -> None:
    from src.schemas.suspicion import RebuttalEntry, RebuttalOutput

    async def fake_rebuttal(cards, context):
        # 큰 금액(재고자산)을 정상우세로 강등 → 정렬에서 하단으로 가야 함
        return RebuttalOutput(
            entries=[
                RebuttalEntry(cluster_key="acct:BS:재고자산", verdict="normal_dominant"),
                RebuttalEntry(cluster_key="acct:BS:매출채권", verdict="suspicion_dominant"),
            ]
        )

    result = asyncio.run(
        build_suspicion_cards(
            _two_account_report(),
            agent_runner=_two_card_runner(),
            rebuttal_runner=fake_rebuttal,
            external_runner=_canned_external(),
            materials=_materials(),
        )
    )
    accounts = [c.account for c in result["account_cards"]]
    assert accounts[-1] == "재고자산"  # normal_dominant 하단 강등
    assert result["account_cards"][0].rebuttal_verdict == "suspicion_dominant"
    assert "반박 미수행" not in result["rendered"]  # 둘 다 반박됨


def test_pipeline_unrebutted_card_shows_marker() -> None:
    canned = {
        "numeric": PerspectiveOutput(
            suspicions=[
                SuspicionItem(
                    perspective="numeric",
                    scope="account",
                    issue_type=IssueType.REVENUE_RECEIVABLES,
                    account_id="매출채권",
                    sj_div="BS",
                    year="2024",
                    cited_value="100,000,000",
                    description="의심.",
                )
            ]
        )
    }

    async def empty_rebuttal(cards, context):
        from src.schemas.suspicion import RebuttalOutput

        return RebuttalOutput(entries=[])

    result = asyncio.run(
        build_suspicion_cards(
            _report(),
            agent_runner=_canned_runner(canned),
            rebuttal_runner=empty_rebuttal,
            external_runner=_canned_external(canned),
            materials=_materials(),
        )
    )
    assert "반박 미수행" in result["rendered"]
