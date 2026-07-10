"""별칭 제안기 UI 배선 테스트 — 사람 확인 등록(_register_suggestion)·기타 거부·import 스모크."""

from __future__ import annotations

from pathlib import Path

from dashboard.onboarding import _register_suggestion
from src.report.alias_suggest import NO_MATCH, AliasSuggestion


def test_register_suggestion_writes_alias_addition(tmp_path: Path) -> None:
    path = tmp_path / "company_quirks.yaml"
    sug = AliasSuggestion(
        alias="투자금융자산", sj_div="BS", suggested_canonical="비유동금융자산", confidence=0.9
    )
    reloaded = _register_suggestion("00688996", "2024", sug, path=path)
    entry = reloaded["00688996"]["2024"]["alias_additions"][0]
    assert entry == {"canonical": "비유동금융자산", "alias": "투자금융자산"}


def test_register_suggestion_rejects_no_match(tmp_path: Path) -> None:
    path = tmp_path / "company_quirks.yaml"
    sug = AliasSuggestion(alias="모호", sj_div="BS", suggested_canonical=NO_MATCH, confidence=0.0)
    assert _register_suggestion("00688996", "2024", sug, path=path) is None
    # 기타 제안은 디스크에 기록되지 않는다(자동적용 금지·노이즈 차단)
    assert not path.exists()


def test_onboarding_imports_with_alias_wiring() -> None:
    # 배선 후에도 onboarding 모듈이 깨지지 않는지(스모크)
    import dashboard.onboarding as ob

    assert hasattr(ob, "render_alias_suggestions")
    assert hasattr(ob, "_register_suggestion")


# ── 자동 등록(auto_register_aliases) — 임계·NO_MATCH 보류·멱등 ──────────────
def _suggestions_mixed() -> list[AliasSuggestion]:
    return [
        AliasSuggestion(
            alias="확실계정", sj_div="CF", suggested_canonical="현금흐름X", confidence=0.9
        ),
        AliasSuggestion(
            alias="애매계정", sj_div="CF", suggested_canonical="현금흐름Y", confidence=0.4
        ),
        AliasSuggestion(
            alias="보류계정", sj_div="CF", suggested_canonical=NO_MATCH, confidence=0.99
        ),
    ]


def test_auto_register_threshold_and_no_match_held(tmp_path: Path) -> None:
    """≥0.7·非기타(1건)만 window 전 연도(2개)에 등록, 저신뢰·NO_MATCH(2건)는 보류."""

    from dashboard.onboarding import auto_register_aliases
    from src.normalize.config import load_company_quirks

    path = tmp_path / "company_quirks.yaml"
    out = auto_register_aliases("00688996", [2023, 2024], _suggestions_mixed(), path=path)
    assert out == {"registered": 2, "held": 2}  # 1건 × 2연도 등록, 2건 보류

    quirks = load_company_quirks(path)
    for y in ("2023", "2024"):
        adds = quirks["00688996"][y]["alias_additions"]
        assert [(e["canonical"], e["alias"]) for e in adds] == [("현금흐름X", "확실계정")]
        assert adds[0]["reason"].startswith("auto(")  # 감사추적 — 수동 등록과 구분


def test_auto_register_idempotent_no_duplicates(tmp_path: Path) -> None:
    """같은 제안으로 2회 실행해도 yaml 항목 수 증가 0(중복 append 방지)."""

    from dashboard.onboarding import auto_register_aliases
    from src.normalize.config import load_company_quirks

    path = tmp_path / "company_quirks.yaml"
    auto_register_aliases("00688996", [2024], _suggestions_mixed(), path=path)
    second = auto_register_aliases("00688996", [2024], _suggestions_mixed(), path=path)
    assert second["registered"] == 0  # 2회째는 전부 기등록 스킵
    adds = load_company_quirks(path)["00688996"]["2024"]["alias_additions"]
    assert len(adds) == 1
