"""계정별 계산값 전수 패널 (phase 2) — 계산은 코드, 선택·랭킹은 안 한다.

전 계정에 per-account 결정론 계산값을 **하나도 고르지 않고 전부** 부착한다. 임계로 거르거나
strength로 순위 매기지 않는다(그건 LLM 몫). percentile은 "전 계정 분포 내 위치"를 알려주는
서술 통계일 뿐 판단이 아니다. 근거: PLAN §3(계산=코드, 발견=LLM).
"""

from __future__ import annotations

from src.signals.profiler import (
    _midrank_quantiles,
    account_series_map,
    delta_score,
    statement_totals,
    trend_score,
    volatility_score,
)

MIN_Z_HISTORY = 4  # universal.py와 동일 기준
# 코드가 "중요도/선택"을 정하는 필드 — 패널에 있으면 안 됨(발견=LLM 위배 가드)
DECISION_FIELDS = ("flagged", "strength", "tail_axes", "rank")


def _yoy(current: float | None, prior: float | None) -> float | None:
    """작년 대비 % — 전기 결측·0이면 None(소액기저 폭주는 LLM이 금액으로 판단)."""

    if current is None or prior is None or prior == 0:
        return None
    return (float(current) - float(prior)) / abs(float(prior)) * 100


def occurrence_state(ts: dict[int, float], target_year: int) -> str:
    """계정의 발생 상태(근본구조 B): 변화율 0/None이 죽이던 신규·소멸을 신호로 표시.

    - present: 당기·전기 모두 잔액 존재(정상 변화 대상)
    - appeared: 당기 존재, 윈도우 내 과거 전무(올해 신규 발생)
    - resumed: 당기 존재, 직전기 없음, 그러나 더 과거엔 존재(재개)
    - disappeared: 당기 없음, 과거 존재(소멸)
    잔액 = 금액이 None도 0도 아님. delta_score는 건드리지 않는 별도 신호.
    """

    nonzero = {y for y, v in ts.items() if v is not None and v != 0}
    has_target = target_year in nonzero
    prior_nonzero = {y for y in nonzero if y < target_year}
    if has_target:
        if (target_year - 1) in nonzero:
            return "present"
        return "resumed" if prior_nonzero else "appeared"
    return "disappeared" if prior_nonzero else "present"


def _z_score(vals_by_year: dict[int, float], target_year: int) -> float | None:
    """과거(target 이전) 대비 z. 이력<MIN_Z_HISTORY면 None."""

    history = [v for y, v in vals_by_year.items() if y < target_year]
    current = vals_by_year.get(target_year)
    if current is None or len(history) < MIN_Z_HISTORY:
        return None
    mean = sum(history) / len(history)
    variance = sum((v - mean) ** 2 for v in history) / len(history)
    std = variance**0.5
    if std == 0:
        return None
    return (float(current) - mean) / std


def account_metrics_panel(
    rows: list[dict], asset: float | dict[str, float], target_year: int
) -> list[dict]:
    """전 계정에 계산값 전부 부착(선택·랭킹·임계 없음). LLM이 직접 이상 판단.

    asset: 자산총계 분모. 단일 float(단일 fs_div)거나 {fs_div: 자산총계} dict(연결·별도 혼재).
    dict면 각 계정의 fs_div에 맞는 자산총계로 delta를 정규화한다(별도 계정을 연결 자산으로
    나누는 스케일 오류 차단). 구성비(mix) 분모도 fs_div별로 격리한다(statement_totals).
    """

    series = account_series_map(rows)
    totals = statement_totals(rows)
    sj_by_key: dict[str, str] = {}
    fs_by_key: dict[str, str] = {}
    for row in rows:
        key = str(row.get("series_key"))
        sj_by_key.setdefault(key, str(row.get("sj_div")))
        fs_by_key.setdefault(key, str(row.get("fs_div", "")))

    def _asset_for(fs: str) -> float:
        if isinstance(asset, dict):
            return float(asset.get(fs, 0.0))
        return float(asset)

    entries: list[dict] = []
    for key, ts in series.items():
        years = sorted(ts)
        vals = [ts[y] for y in years]
        current = ts.get(target_year)
        prior = ts.get(target_year - 1)
        sj = sj_by_key.get(key, "")
        fs = fs_by_key.get(key, "")
        cur_total = totals.get((fs, sj, target_year), 0.0)
        prior_total = totals.get((fs, sj, target_year - 1), 0.0)
        cur_share = abs(current) / cur_total if current is not None and cur_total else 0.0
        prior_share = abs(prior) / prior_total if prior is not None and prior_total else 0.0
        entries.append(
            {
                "account": key,
                "sj_div": sj,
                "fs_div": fs,
                "occurrence_state": occurrence_state(ts, target_year),
                "amounts": {y: ts[y] for y in years},
                "yoy_pct": {y: _yoy(ts.get(y), ts.get(y - 1)) for y in years},
                "delta_over_assets": delta_score(current, prior, _asset_for(fs)),
                "trend": trend_score(vals, _asset_for(fs)),  # type: ignore[arg-type]
                "volatility_cv": volatility_score(vals),  # type: ignore[arg-type]
                "mix_pct": round(cur_share * 100, 4),
                # 부호 보존(증가 +/감소 −) — LLM이 비중 방향을 직접 판단(절대값은 정보 손실).
                "mix_shift_pp": round((cur_share - prior_share) * 100, 4),
                "z_score": _z_score(ts, target_year),
            }
        )

    _attach_percentiles(entries)
    return entries


_PANEL_COLUMNS = (
    "account",
    "sj_div",
    "fs_div",
    "occurrence_state",
    "delta_over_assets",
    "trend",
    "volatility_cv",
    "mix_pct",
    "mix_shift_pp",
    "z_score",
    "amounts",
    "yoy_pct",
    "percentiles",
)


def panel_columnar(panel: list[dict]) -> dict:
    """객체 리스트 → 컬럼형({columns, rows}). 키 이름을 1회만 싣는다(무손실·토큰 절감).

    rows[i]는 columns 순서의 값 배열. amounts·yoy_pct·percentiles는 {연도/축: 값} 객체 유지
    (연도 매칭 보존). LLM 프롬프트의 키 이름 N회 반복을 제거하는 표현 변경일 뿐 정보는 동일.
    """

    if not panel:
        return {"columns": [], "rows": []}
    rows = [[entry.get(col) for col in _PANEL_COLUMNS] for entry in panel]
    return {
        "columns": list(_PANEL_COLUMNS),
        "rows": rows,
        "format": "rows[i]는 columns 순서의 값. amounts·yoy_pct·percentiles는 {연도/축:값} 객체.",
    }


def _attach_percentiles(entries: list[dict]) -> None:
    """전 계정 분포 내 위치(서술 통계). 판단 아님 — 임계·flag 없음.

    분위는 변화 '크기'(절대값) 분포 — mix_shift_pp는 부호가 있으므로 abs로 위치를 잰다.
    """

    axes = ("delta_over_assets", "trend", "volatility_cv", "mix_shift_pp")
    quantiles_by_axis = {
        name: _midrank_quantiles([abs(float(e.get(name, 0.0))) for e in entries]) for name in axes
    }
    for i, entry in enumerate(entries):
        entry["percentiles"] = {name: round(q[i], 4) for name, q in quantiles_by_axis.items()}


__all__ = ["DECISION_FIELDS", "account_metrics_panel", "occurrence_state", "panel_columnar"]
