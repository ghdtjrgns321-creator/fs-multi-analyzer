"""회사 분석 준비 상태 판정 + 준비 파이프라인 (A안: raw 보존·준비 때 재정규화).

상태(UI_WORKFLOW.md): A 미수집(raw 없음) / B 수집됨·미준비(raw 있음, prep 마커 없음) /
C 준비완료(마커 + 게이트 PASS). 준비 = (필요시)수집 → 재정규화 → 주석분류 → 게이트 → prep 마커.
raw는 보존하고 파생물(DB)만 최신 코드로 다시 만든다. DART 재호출은 raw 없는 연도에만.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timezone
from pathlib import Path

from config.settings import settings

RAW_CFS = "finstate_all_CFS.csv"
RAW_OFS = "finstate_all_OFS.csv"
PREP_MARKER = "prep.json"
ONBOARDING_MARKER = "onboarding.json"


def _root(root: Path | None) -> Path:
    return root or settings.data_dir


def raw_present(corp: str, year: object, root: Path | None = None) -> bool:
    """이 회사연도 raw 재무제표(CFS 또는 OFS)가 있는지 — 재정규화 가능 여부."""

    ydir = _root(root) / corp / str(year) / "raw"
    return (ydir / RAW_CFS).exists() or (ydir / RAW_OFS).exists()


def raw_years(corp: str, root: Path | None = None) -> list[int]:
    """raw가 있는 사업연도 오름차순 — 분석 준비가 가능한(연도 드롭다운) 후보."""

    cdir = _root(root) / corp
    if not cdir.is_dir():
        return []
    ys = [
        int(y.name)
        for y in cdir.iterdir()
        if y.is_dir() and y.name.isdigit() and raw_present(corp, y.name, root)
    ]
    return sorted(ys)


def _marker_path(corp: str, year: object, root: Path | None = None) -> Path:
    return _root(root) / corp / str(year) / PREP_MARKER


def read_prep_marker(corp: str, year: object, root: Path | None = None) -> dict | None:
    """prep 마커(준비 이력) 로드. 없거나 깨지면 None(미준비로 취급)."""

    path = _marker_path(corp, year, root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_prep_marker(
    corp: str,
    year: object,
    gate_passed: bool,
    window: list[int] | None = None,
    root: Path | None = None,
) -> dict:
    """prep 마커 기록 — 이 연도가 최신 코드로 재정규화·게이트 됐음을 표시(최신성 판별 스탬프)."""

    marker = {
        "prepared_at": datetime.now(UTC).isoformat(),
        "gate_passed": bool(gate_passed),
        "window": window or [],
    }
    path = _marker_path(corp, year, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(marker, ensure_ascii=False), encoding="utf-8")
    return marker


def prepared_years(corp: str, root: Path | None = None) -> list[int]:
    """게이트 PASS 마커가 있는 연도 — 바로 Phase1 가능한 '준비완료' 연도."""

    out = [
        y
        for y in raw_years(corp, root)
        if (m := read_prep_marker(corp, y, root)) and m.get("gate_passed")
    ]
    return sorted(out)


def _onb_marker_path(corp: str, year: object, root: Path | None = None) -> Path:
    return _root(root) / corp / str(year) / ONBOARDING_MARKER


def read_onboarding_marker(corp: str, year: object, root: Path | None = None) -> dict | None:
    """온보딩 완료 마커 로드. 없으면 None."""

    path = _onb_marker_path(corp, year, root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_onboarding_marker(
    corp: str, year: object, chunks: int = 0, root: Path | None = None
) -> dict:
    """온보딩(LLM 사전 검토) 완료를 영속 기록 — 이미 하면 다시 요구하지 않기 위함."""

    marker = {"completed_at": datetime.now(UTC).isoformat(), "chunks": int(chunks)}
    path = _onb_marker_path(corp, year, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(marker, ensure_ascii=False), encoding="utf-8")
    return marker


def onboarding_done(corp: str, year: object, root: Path | None = None) -> bool:
    """이 회사연도 온보딩(LLM 사전 검토)이 이미 완료됐는지 — 완료면 재실행을 요구하지 않는다."""

    return read_onboarding_marker(corp, year, root) is not None


def company_state(corp: str, root: Path | None = None) -> dict:
    """회사 상태 판정 — A 미수집 / B 수집됨·미준비 / C 준비완료(일부라도)."""

    ry = raw_years(corp, root)
    py = prepared_years(corp, root)
    state = "A" if not ry else ("B" if not py else "C")
    return {"state": state, "raw_years": ry, "prepared_years": py}


def prepare_company(
    corp: str,
    target_year: int,
    window: list[int],
    progress: Callable[[str], None] | None = None,
) -> dict:
    """분석 준비 파이프라인 — (필요시)수집 → 재정규화 → 주석분류 → 게이트 → 마커.

    window 연도를 재정규화(신호 컨텍스트), target_year만 게이트·마커. 실데이터 디렉토리에서만
    동작(게이트·주석로더가 settings.data_dir 고정). 각 단계 진행상황을 progress 콜백으로 흘린다.
    """

    def log(msg: str) -> None:
        if progress:
            progress(msg)

    root = settings.data_dir
    missing = [y for y in window if not raw_present(corp, y, root)]
    if missing:
        log(f"수집(DART) — {missing}")
        from src.collect.spike import collect_company_years

        collect_company_years(corp, tuple(missing), data_dir=root)

    present = [y for y in window if raw_present(corp, y, root)]
    log(f"재정규화 — {present}")
    from src.normalize.spike import normalize_company_years

    normalize_company_years(corp, tuple(present), data_dir=root)

    log("주석 숫자 분류")
    from src.collect.load_notes_classified import run as load_notes_run

    load_notes_run([corp], force=True)

    log(f"온보딩 게이트 — {target_year}")
    from src.normalize.onboarding_gate import run_gate

    gate = run_gate(corp, str(target_year))
    passed = bool(gate.get("gate_passed"))
    write_prep_marker(corp, target_year, passed, window=present, root=root)
    return {"gate": gate, "gate_passed": passed, "collected": bool(missing), "window": present}
