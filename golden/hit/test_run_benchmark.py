"""검사2 오케스트레이터 — dry-run은 실LLM·실DART를 호출하지 않는다(실행 게이트)."""

from __future__ import annotations

import asyncio

from golden.hit.build_labels import Label, LabelSet
from golden.hit.run_benchmark import load_benchmarks, report_markdown, score_benchmark


def _label_set():
    labels = [
        Label(corp_code="00117212", year=2020, account_key="CFS:매출채권", source="restated_later"),
    ]
    excluded = [
        Label(corp_code="00117212", year=2020, account_key="CFS:재고자산", source="restated_later"),
    ]
    return LabelSet(corp_code="00117212", year=2020, labels=labels, excluded=excluded)


def test_dry_run_does_not_execute():
    # execute=False(기본): 실LLM 카드 생성 없이 준비상태만. 호출돼도 네트워크·비용 0.
    result = asyncio.run(score_benchmark("00117212", 2020, _label_set()))
    assert result["executed"] is False
    assert result["registered_labels"] == 1
    assert result["excluded_labels"] == 1


def test_report_markdown_dry_run():
    result = asyncio.run(score_benchmark("00117212", 2020, _label_set()))
    md = report_markdown(result)
    assert "준비상태" in md
    assert "등록 정답지 1건" in md


def test_load_benchmarks_registry():
    # 등록부에 후보 2사가 있고, 채점은 미검증(verified=false)이어야 한다.
    benchmarks = load_benchmarks()
    corps = {b["corp_code"] for b in benchmarks}
    assert {"00117212", "00258801"} <= corps
    assert all(b.get("verified") is False for b in benchmarks)  # 원본대조·채점 미실행
