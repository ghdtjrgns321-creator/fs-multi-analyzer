"""Industry peer perspective for L4 multi-agent review."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.agents.gemini_retry import DEFAULT_RETRY_DELAYS
from src.peers.benchmark import build_industry_benchmark
from src.report.perspectives import (
    PerspectiveAssessment,
    create_perspective_assessment,
    deferred_assessment,
)


def industry_material(
    report: dict[str, object],
    benchmark_factory: Callable[..., dict[str, object]] = build_industry_benchmark,
) -> dict[str, object]:
    """Build deterministic material for the industry perspective."""

    benchmark = benchmark_factory(
        str(report["corp_code"]),
        list(report["years"]),  # type: ignore[arg-type]
        company_profile=report.get("business_domain"),
    )
    return {
        "scope": "industry reference perspective only; no judgment-field mutation",
        "company_name": report.get("company_name", report["corp_code"]),
        "target_year": report["target_year"],
        "review_queue_reference": report["review_queue"][:5],  # type: ignore[index]
        "ratio_time_series": report.get("ratio_time_series", []),
        "benchmark": benchmark,
        "rules": [
            "피어는 지표 baseline 계산에만 사용했다.",
            "피어 주석·교차·5축 분석은 수행하지 않았다.",
            "review_queue_reference는 참고 후보일 뿐이며, "
            "benchmark와 ratio_time_series를 직접 검토한다.",
            "대상 회사의 사업구조가 피어와 달라 단순 비교에 한계가 있음을 명시한다.",
            "업종 비교는 ISA/KSA 520 분석적 절차의 참고 신호일 뿐 확정 근거가 아니다.",
        ],
    }


async def create_industry_assessment(
    report: dict[str, object],
    benchmark_factory: Callable[..., dict[str, object]] = build_industry_benchmark,
    agent_factory: Callable[..., Any] | None = None,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
) -> PerspectiveAssessment:
    """Evaluate the target company against peer-ratio baseline."""

    try:
        material = industry_material(report, benchmark_factory)
        if agent_factory is None:
            return await create_perspective_assessment(
                "industry",
                material,
                retry_delays=retry_delays,
            )
        return await create_perspective_assessment(
            "industry",
            material,
            agent_factory=agent_factory,
            retry_delays=retry_delays,
        )
    except Exception as exc:
        return deferred_assessment("industry", str(exc) or exc.__class__.__name__)
