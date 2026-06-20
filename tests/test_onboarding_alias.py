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
