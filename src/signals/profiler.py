"""다축 이상 프로파일러 — self 기준선 축 계산기 (S1).

설계: docs/agent/PHASE1_SIGNAL_REDESIGN.md §3. 전 계정 시계열에 self 축(변화금액·추세·
변동성·구성비)의 **원점수**를 계산한다. 임계 리터럴 없음(정규화·통합·peer·review_queue는
S2~). 순수함수 — DB·LLM 의존 없음.

축 정의:
- delta(변화금액): |당기-전기| / 자산총계. floor 경계·valid_yoy_base 없이 변화의 절대 유의성.
- trend(추세): 단조성 × |당기-최초| / 자산총계. 다년 방향 일관성 + 누적 변화금액(비율 아님).
- volatility(변동성): 변동계수 std/|mean|.
- mix(구성비): 표(sj_div) 내 비중의 전기 대비 변화(pp).
"""

from __future__ import annotations


def delta_score(current: float | None, prior: float | None, asset: float) -> float:
    """|당기-전기| / 자산총계. 전기 결측·자산≤0이면 0(전기 크기에 의존하지 않음)."""

    if current is None or prior is None or not asset or asset <= 0:
        return 0.0
    return abs(float(current) - float(prior)) / float(asset)


def trend_score(series: list[float | None], asset: float) -> float:
    """단조성 × |당기-최초|/자산. series는 연도 오름차순(결측 None 허용)."""

    vals = [float(v) for v in series if v is not None]
    if len(vals) < 2 or not asset or asset <= 0:
        return 0.0
    diffs = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
    nonzero = [d for d in diffs if d != 0]
    if not nonzero:
        return 0.0
    pos = sum(1 for d in nonzero if d > 0)
    neg = len(nonzero) - pos
    monotonicity = max(pos, neg) / len(nonzero)  # 방향 일관성(1.0=완전 단조)
    cumulative = abs(vals[-1] - vals[0]) / float(asset)  # 누적 변화금액 비중
    return monotonicity * cumulative


def volatility_score(series: list[float | None]) -> float:
    """변동계수 = 표준편차 / |평균|. 평균 0·길이<2면 0."""

    vals = [float(v) for v in series if v is not None]
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    if mean == 0:
        return 0.0
    variance = sum((v - mean) ** 2 for v in vals) / len(vals)
    return (variance**0.5) / abs(mean)


def mix_score(current_share: float, prior_share: float) -> float:
    """표 내 비중(0~1)의 전기 대비 절대 변화."""

    return abs(float(current_share) - float(prior_share))


def account_series_map(rows: list[dict]) -> dict[str, dict[int, float]]:
    """account_level_series → series_key별 {year: amount} 시계열(동일 키·연도는 합산)."""

    out: dict[str, dict[int, float]] = {}
    for row in rows:
        amount = row.get("amount")
        if amount is None:
            continue
        key = str(row.get("series_key"))
        year_raw = row.get("year")
        if year_raw is None:
            continue
        year = int(year_raw)  # type: ignore[arg-type]
        bucket = out.setdefault(key, {})
        bucket[year] = bucket.get(year, 0.0) + float(amount)
    return out


def statement_totals(rows: list[dict]) -> dict[tuple[str, str, int], float]:
    """(fs_div, sj_div, year)별 절대금액 합 — 구성비(mix) 분모.

    fs_div를 키에 포함해 연결(CFS)·별도(OFS)의 같은 sj_div가 한 분모로 섞이지 않게 한다
    (이질병합 차단). fs_div 미지정 행은 ""로 묶여 단일 fs_div 호출에선 종전과 동일.
    """

    totals: dict[tuple[str, str, int], float] = {}
    for row in rows:
        amount = row.get("amount")
        if amount is None:
            continue
        key = (
            str(row.get("fs_div", "")),
            str(row.get("sj_div")),
            int(row.get("year")),  # type: ignore[arg-type]
        )
        totals[key] = totals.get(key, 0.0) + abs(float(amount))
    return totals


def compute_self_axes(rows: list[dict], asset: float, target_year: int) -> list[dict]:
    """전 계정에 self 4축 원점수를 계산. 반환: [{series_key, delta, trend, volatility, mix}]."""

    series = account_series_map(rows)
    totals = statement_totals(rows)
    sj_by_key: dict[str, str] = {}
    fs_by_key: dict[str, str] = {}
    for row in rows:
        key = str(row.get("series_key"))
        sj_by_key.setdefault(key, str(row.get("sj_div")))
        fs_by_key.setdefault(key, str(row.get("fs_div", "")))

    out: list[dict] = []
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
        out.append(
            {
                "series_key": key,
                "sj_div": sj,
                "delta": delta_score(current, prior, asset),
                "trend": trend_score(vals, asset),  # type: ignore[arg-type]
                "volatility": volatility_score(vals),  # type: ignore[arg-type]
                "mix": mix_score(cur_share, prior_share),
            }
        )
    return out


# ── S2: 정규화(분포 분위) + 통합강도 (PHASE1_SIGNAL_REDESIGN §4·§5) ───────────
SELF_AXES = ("delta", "trend", "volatility", "mix")
DEFAULT_TAIL = 0.8  # 분포 상위 분위 임계(개수상한 아님). 실데이터(큰 분포)선 config로 상향 가능.


def _midrank_quantiles(values: list[float]) -> list[float]:
    """각 값의 mid-rank 분위 [0,1] — 동점은 평균순위. 임계 리터럴 없이 분포가 위치를 정함."""

    n = len(values)
    if n == 0:
        return []
    if n == 1:
        return [1.0]
    out: list[float] = []
    for v in values:
        less = sum(1 for x in values if x < v)
        equal = sum(1 for x in values if x == v)
        out.append((less + (equal + 1) / 2) / n)
    return out


def normalize_axes(axes: list[dict]) -> list[dict]:
    """compute_self_axes 출력에 축별 분포 분위(`{axis}_q`)를 덧붙인다(원점수→상대위치)."""

    norm = [dict(a) for a in axes]
    for axis in SELF_AXES:
        quantiles = _midrank_quantiles([float(a.get(axis, 0.0)) for a in axes])
        for i, q in enumerate(quantiles):
            norm[i][f"{axis}_q"] = q
    return norm


def compute_strength(
    normalized: list[dict],
    weights: dict[str, float] | None = None,
    tail: float = DEFAULT_TAIL,
) -> list[dict]:
    """OR 플래그(어느 축이든 분위≥tail이면 후보) + 가중합 strength(정렬). D1 확정안.

    flagged=True인 계정만 후보다. strength는 후보 정렬용(가중합 균등 시작·백테스트 보정).
    """

    weights = weights or {axis: 1.0 for axis in SELF_AXES}
    weight_sum = sum(weights.values()) or 1.0
    out: list[dict] = []
    for a in normalized:
        qs = {axis: float(a.get(f"{axis}_q", 0.0)) for axis in SELF_AXES}
        strength = sum(weights.get(axis, 0.0) * qs[axis] for axis in SELF_AXES) / weight_sum
        tail_axes = [axis for axis in SELF_AXES if qs[axis] >= tail]
        out.append({**a, "strength": strength, "flagged": bool(tail_axes), "tail_axes": tail_axes})
    return sorted(out, key=lambda x: x["strength"], reverse=True)


# ── S3: report → 다축 프로파일 (subtotal 제외·자산총계 자동추출) ──────────────
def extract_asset(rows: list[dict], target_year: int) -> float:
    """자산총계(target 연도)를 account_level_series에서 추출. 없으면 BS 최대 절대금액 대용."""

    for row in rows:
        key = str(row.get("series_key"))
        canon = str(row.get("canonical"))
        if (key == "자산총계" or canon == "자산총계") and int(row.get("year")) == target_year:  # type: ignore[arg-type]
            amount = row.get("amount")
            if amount is not None:
                return abs(float(amount))
    return 0.0


def build_account_profile(
    report: dict,
    tail: float = DEFAULT_TAIL,
    weights: dict[str, float] | None = None,
) -> list[dict]:
    """report → 전 계정 다축 self 프로파일(strength 정렬). subtotal(자산총계 등)은 후보서 제외.

    peer 수준축(①)은 미포함(S4 benchmark 연동). self 4축만으로 strength·flagged 산정.
    """

    from config.settings import settings
    from src.normalize.config import subtotal_account_names

    rows = report.get("account_level_series", []) or []
    target_year = int(report.get("target_year", 0))

    # OFS 개방·명단합집합 후에도 Phase1 다축 프로파일(suspended 재설계)은 baseline을 보존한다:
    # (1) 연결(CFS)만(별도 행이 self 분포에 섞이는 회귀 차단, fs_div 미지정은 CFS 취급),
    # (2) target_year 잔액>0 계정만(명단합집합 전 모집단 재현 — 소멸계정이 분포에 섞여
    #     percentile이 흔들리는 회귀 차단). 산물 신호엔진은 account_metrics_panel 경로가 담당.
    def _present(amount: object) -> bool:
        if amount is None:
            return False
        value = float(amount)  # type: ignore[arg-type]
        return value == value and value != 0  # NaN·0 제외(fix A 이전 abs>0 동작 재현)

    target_keys = {
        str(r.get("series_key"))
        for r in rows
        if int(r.get("year", 0)) == target_year and _present(r.get("amount"))
    }
    rows = [
        r
        for r in rows
        if str(r.get("fs_div", "CFS")) in ("", "CFS") and str(r.get("series_key")) in target_keys
    ]
    asset = extract_asset(rows, target_year)
    if not rows or asset <= 0:
        return []
    subtotals = subtotal_account_names(settings.config_dir / "canonical_accounts.yaml")
    leaf = [
        r
        for r in rows
        if str(r.get("series_key")) not in subtotals and str(r.get("canonical")) not in subtotals
    ]
    axes = compute_self_axes(leaf, asset, target_year)
    return compute_strength(normalize_axes(axes), weights=weights, tail=tail)


__all__ = [
    "account_series_map",
    "build_account_profile",
    "compute_self_axes",
    "compute_strength",
    "delta_score",
    "extract_asset",
    "mix_score",
    "normalize_axes",
    "statement_totals",
    "trend_score",
    "volatility_score",
]
