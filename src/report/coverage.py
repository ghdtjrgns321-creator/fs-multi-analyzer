"""커버리지 원장 — 분석 모집단 대조(근본구조 C).

§10 population-first·negative-space-proof를 런타임에 박는다. 분석 대상을 "골라 담기"가 아니라
"전체 셀 = 분석한 셀 + 제외사유 셀 + 미설명 셀"로 정합 강제한다. 미설명(이유 없이 빠진 셀)이
1건이라도 있으면 = 조용한 드롭 → 출력에 "미분석 N건"으로 드러나고 테스트가 실패한다.

이번 씨앗의 모집단 = normalized_financials 본문 셀(정규화 frame). 주석·SCE 2D는 별도 저장소라
이 원장 밖이며, SCE 본문행은 "제외: SCE 2D 별도표"로 분류한다(미설명 아님).
"""

from __future__ import annotations

from typing import Any

# 분석 명단(account_level_series)이 다루는 본문 statement. SCE는 메인에서 제외(2D 별도표 담당).
_BODY_STATEMENTS = ("BS", "IS", "CIS", "CF")
_FS_DIVS = ("CFS", "OFS")


def _base_key(canonical: Any, label: Any) -> str:
    """series_key 베이스 — _account_level_series와 동일 규칙(canonical 우선, 없으면 label)."""

    canon = "" if canonical is None else str(canonical)
    return canon if canon.strip() else ("" if label is None else str(label))


def _series_key(fs_div: Any, canonical: Any, label: Any) -> str:
    return f"{fs_div}:{_base_key(canonical, label)}"


def _real_amount(amount: Any) -> float | None:
    """실값(셀이 실재)만 통과 — None·NaN·0은 '값 없음'으로 본다. account_level_series의
    abs>0 키 선정과 같은 기준이라 NaN placeholder 행이 모집단/분석에 불일치로 새지 않는다."""

    if amount is None:
        return None
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return None
    if value != value or value == 0:  # NaN 또는 0
        return None
    return value


def build_coverage_ledger(
    frame: Any,
    account_series: list[dict],
    years: list[int],
) -> dict[str, object]:
    """본문 셀 모집단을 분석셀과 대조한다. 반환 항등식:
    population_n == analyzed_n + len(excluded) + len(unaccounted).
    """

    window = {int(y) for y in years}

    # 모집단: frame 본문 셀(fs CFS/OFS, 윈도우 연도, 잔액>0). 셀 = (fs, sj, series_key, year).
    population: dict[tuple[str, str, str, int], str] = {}  # cell -> sj_div
    if hasattr(frame, "to_dict") and not frame.empty:
        for row in frame.to_dict("records"):
            fs = str(row.get("fs_div"))
            sj = str(row.get("sj_div"))
            year_raw = row.get("year")
            if fs not in _FS_DIVS or year_raw is None or _real_amount(row.get("amount")) is None:
                continue
            try:
                year = int(year_raw)
            except (TypeError, ValueError):
                continue
            if year not in window:
                continue
            key = (fs, sj, _series_key(fs, row.get("canonical"), row.get("label")), year)
            population[key] = sj

    # 분석셀: account_level_series의 잔액>0 셀.
    analyzed: set[tuple[str, str, str, int]] = set()
    for row in account_series or []:
        if _real_amount(row.get("amount")) is None:
            continue
        try:
            year = int(row.get("year"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        analyzed.add(
            (str(row.get("fs_div")), str(row.get("sj_div")), str(row.get("series_key")), year)
        )

    excluded: list[dict[str, object]] = []
    unaccounted: list[dict[str, object]] = []
    analyzed_n = 0
    for cell, sj in population.items():
        if cell in analyzed:
            analyzed_n += 1
        elif sj == "SCE":
            # SCE 본문행(붕괴 총계)은 sce_equity_components 2D 테이블이 상위 포함 → 정당제외(중복).
            excluded.append({"cell": list(cell), "reason": "SCE 2D 테이블이 상위 포함(superseded)"})
        elif sj not in _BODY_STATEMENTS:
            excluded.append({"cell": list(cell), "reason": f"본문 외 statement({sj})"})
        else:
            unaccounted.append({"cell": list(cell)})

    return {
        "population_n": len(population),
        "analyzed_n": analyzed_n,
        "excluded": excluded,
        "unaccounted": unaccounted,
        "reconciled": len(population) == analyzed_n + len(excluded) + len(unaccounted),
    }


# ── 주석(note) 차원 원장 ────────────────────────────────────────────────────
# 포함-기본값 원칙(제외규칙 단일화): 분석 모집단 = 전 fact. 정당제외는 **완전중복·비fact 2종뿐**.
# note_facts_classified는 적재(select_for_load) 단계서 이미 무차원흡수(완전중복)·메타를 제외했으므로,
# DB에 남은 fact(detail·기타주석·차원흡수)는 전부 net-new → 분석에 전량 투입(흡수도 차원 breakdown).


def build_note_ledger(note_facts: list[dict]) -> dict[str, object]:
    """주석 fact 모집단 대조. 적재본은 이미 정당제외(완전중복·메타) 상위적용 → surfaced=population.

    population == surfaced + excluded + unaccounted. (load 단계 제외는 상위 정당이라 여기선 0.)
    """

    population_n = len(note_facts or [])
    return {
        "population_n": population_n,
        "surfaced_n": population_n,  # 적재본 전량 surface(load가 정당제외 상위적용)
        "excluded": [],
        "excluded_by_reason": {},
        "unaccounted": [],
        "reconciled": True,
    }


def surfaced_note_facts(note_facts: list[dict]) -> list[dict]:
    """분석 투입 = 적재 note fact 전량. 차원흡수(부문·지역 breakdown=net-new)도 포함.
    무차원흡수(완전중복)·메타는 적재 단계서 이미 제외됨 — 분석층에서 추가로 자르지 않는다."""

    return list(note_facts or [])


def build_sce_ledger(sce_cells: list[dict]) -> dict[str, object]:
    """자본변동표(SCE) 2D 셀 원장. 본문 ledger가 'SCE 2D가 상위 대체'로 미뤄둔 실데이터를
    여기서 전량 surface(정당제외 없음 — 변동×구성요소 셀은 전부 net-new 재무정보)."""

    population_n = len(sce_cells or [])
    return {
        "population_n": population_n,
        "surfaced_n": population_n,
        "excluded": [],
        "unaccounted": [],
        "reconciled": True,
    }


__all__ = ["build_coverage_ledger", "build_note_ledger", "build_sce_ledger", "surfaced_note_facts"]
