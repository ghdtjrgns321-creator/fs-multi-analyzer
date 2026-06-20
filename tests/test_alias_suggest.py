"""온보딩 LLM 별칭 제안기 테스트 — 후보검색(statement·유사도)·앵커링·임계·graceful."""

from __future__ import annotations

from src.report.alias_suggest import (
    NO_MATCH,
    AliasSuggestion,
    AliasSuggestionResult,
    _anchor,
    candidate_canonicals,
    suggest_aliases,
    to_alias_additions,
)

_SPECS = {
    "FVPL금융자산": {"statement": "BS", "aliases": ["당기손익공정가치측정금융자산"]},
    "비유동금융자산": {"statement": "BS", "aliases": ["투자금융자산"]},
    "이자비용": {"statement": "IS", "aliases": ["금융비용"]},
    "영업활동현금흐름": {"statement": "CF", "aliases": []},
    "자본총계": {"statement": "SCE", "aliases": ["자본"]},
}


def test_candidate_canonicals_filters_statement_family() -> None:
    # BS 라벨 → BS 후보만(IS/CF/SCE 제외)
    cands = candidate_canonicals("투자금융자산", "BS", specs=_SPECS)
    assert "비유동금융자산" in cands  # 정확 alias 일치 우선
    assert "이자비용" not in cands and "영업활동현금흐름" not in cands
    assert "자본총계" not in cands  # SCE 제외


def test_candidate_canonicals_is_cis_compatible() -> None:
    # CIS 라벨도 IS canonical을 후보로(같은 손익 family)
    cands = candidate_canonicals("이자비용", "CIS", specs=_SPECS)
    assert "이자비용" in cands


def test_candidate_canonicals_empty_for_unknown_sj() -> None:
    assert candidate_canonicals("무엇", "SCE", specs=_SPECS) == []


def test_anchor_demotes_out_of_candidate_to_no_match() -> None:
    # LLM이 후보 밖 canonical을 뱉으면 '기타 중요 계정'으로 강등(환각 차단)
    s = AliasSuggestion(alias="투자금융자산", suggested_canonical="존재안함", confidence=0.9)
    anchored = _anchor(s, ["비유동금융자산", "FVPL금융자산"])
    assert anchored.suggested_canonical == NO_MATCH
    assert anchored.confidence == 0.0
    # 후보 안이면 보존
    s2 = AliasSuggestion(alias="x", suggested_canonical="FVPL금융자산", confidence=0.8)
    assert _anchor(s2, ["FVPL금융자산"]).suggested_canonical == "FVPL금융자산"


def test_to_alias_additions_threshold_and_skip_no_match() -> None:
    result = AliasSuggestionResult(
        suggestions=[
            AliasSuggestion(
                alias="투자금융자산", suggested_canonical="비유동금융자산", confidence=0.85
            ),
            AliasSuggestion(
                alias="모호계정", suggested_canonical="FVPL금융자산", confidence=0.4
            ),  # 임계 미만
            AliasSuggestion(alias="없음", suggested_canonical=NO_MATCH, confidence=0.0),  # 기타
        ]
    )
    out = to_alias_additions(result, min_confidence=0.7)
    assert out == [{"canonical": "비유동금융자산", "alias": "투자금융자산"}]


def test_suggest_aliases_graceful_without_key(monkeypatch) -> None:
    from src.report import alias_suggest as mod

    monkeypatch.setattr(mod.settings, "openai_api_key", "")
    res = suggest_aliases("00000000", 2024)
    assert res["status"] == "skipped"


def test_suggest_aliases_uses_injected_agent_and_does_not_write(tmp_path, monkeypatch) -> None:
    """주입 agent로 제안만 — 디스크 미기록, 후보 밖 제안은 강등."""

    import duckdb

    from src.db.normalized import db_path

    corp, year = "00688996", 2024
    path = db_path(corp, year, tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute(
        "create table normalized_financials(label varchar, sj_div varchar, amount double,"
        " account_id varchar, mapping_status varchar)"
    )
    con.execute(
        "insert into normalized_financials values"
        " ('투자금융자산','BS',131000.0,'-표준계정코드 미사용-','unmapped_extension_account'),"
        " ('기초','SCE',56000.0,'dart_EquityAtBeginningOfPeriod','unmapped_extension_account')"
    )
    con.close()

    class _FakeAgent:
        def run_sync(self, prompt):
            class _R:
                # 배치 반환: 입력 라벨을 alias로 그대로(suggest_aliases가 alias로 매칭)
                output = AliasSuggestionResult(
                    suggestions=[
                        AliasSuggestion(
                            alias="투자금융자산",
                            sj_div="BS",
                            suggested_canonical="비유동금융자산",
                            confidence=0.9,
                        )
                    ]
                )

            return _R()

    res = suggest_aliases(
        corp,
        year,
        agent_factory=lambda: _FakeAgent(),
        data_dir=tmp_path,
        canonical_path=_write_specs(tmp_path),
    )
    sugg = res["result"].suggestions
    # SCE는 제외돼 투자금융자산 1건만
    assert len(sugg) == 1
    assert sugg[0].alias == "투자금융자산"
    assert sugg[0].suggested_canonical == "비유동금융자산"
    # 디스크에 quirk 자동기록 안 함
    assert not (tmp_path / "company_quirks.yaml").exists()


def test_suggest_aliases_batch_error_returns_empty_not_none(tmp_path) -> None:
    """배치 1회 실패 시 result=None이 아니라 빈 AliasSuggestionResult — 호출부 크래시 방어(P1-B)."""

    import duckdb

    from src.db.normalized import db_path

    corp, year = "00688997", 2024
    path = db_path(corp, year, tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute(
        "create table normalized_financials(label varchar, sj_div varchar, amount double,"
        " account_id varchar, mapping_status varchar)"
    )
    con.execute(
        "insert into normalized_financials values"
        " ('투자금융자산','BS',131000.0,'-표준계정코드 미사용-','unmapped_extension_account')"
    )
    con.close()

    class _BoomAgent:
        def run_sync(self, prompt):
            raise RuntimeError("api down")

    res = suggest_aliases(
        corp,
        year,
        agent_factory=lambda: _BoomAgent(),
        data_dir=tmp_path,
        canonical_path=_write_specs(tmp_path),
    )
    assert res["status"] == "error"
    assert res["result"] is not None  # None이면 호출부 .suggestions 크래시
    assert res["result"].suggestions == []


def _write_specs(tmp_path):
    import yaml

    p = tmp_path / "canon.yaml"
    p.write_text(
        yaml.safe_dump({"canonical_accounts": _SPECS}, allow_unicode=True), encoding="utf-8"
    )
    return p
