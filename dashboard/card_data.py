"""의심건 카드 표시용 순수 데이터 가공 — Streamlit 없이 테스트 가능한 함수만.

카드(AccountFinding)와 Phase1 account_level_series를 화면 재료(제목·금액 축약·시계열·
근거 표)로 바꾼다. 렌더링(st.*)은 card_view가 담당(SRP).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# 관점 내부명 → 사람용 라벨(주장 칩 표기).
PERSPECTIVE_LABELS = {
    "numeric": "수치",
    "note": "주석",
    "flow": "흐름",
    "trend": "추세",
    "external": "외부",
    "industry": "동종",
}
FS_DIV_LABELS = {"CFS": "연결", "OFS": "별도"}


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def split_series_key(key: str) -> tuple[str, str]:
    """'CFS:무형자산' → ('연결', '무형자산'). 접두 없으면 라벨 없이 원문 유지."""

    text = str(key or "")
    prefix, _, rest = text.partition(":")
    if rest and prefix in FS_DIV_LABELS:
        return FS_DIV_LABELS[prefix], rest
    return "", text


def fmt_krw(value: Any) -> str:
    """원화 금액을 조/억 축약(부호 보존). 숫자 아님 → '-'. 표에는 원단위 전체를 병기한다."""

    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "-"
    sign = "-" if amount < 0 else ""
    v = abs(amount)
    if v >= 1e12:
        return f"{sign}{v / 1e12:,.1f}조"
    if v >= 1e8:
        return f"{sign}{v / 1e8:,.0f}억"
    return f"{sign}{v:,.0f}"


# 서술 속 큰 원단위 금액(쉼표그룹 또는 7자리+, 정수부 .0 허용)을 억/조 축약으로.
# `(?<![\d.])` — 앞이 숫자·소수점이면 미매치(0.1628…의 소수부를 금액으로 오인하지 않음).
_LONG_AMOUNT = re.compile(r"(?<![\d.])(?:\d{1,3}(?:,\d{3})+|\d{7,})(?:\.0+)?(?!\d)")


def humanize_amounts(text: str) -> str:
    """LLM 서술의 12자리 원숫자를 사람이 읽을 억/조로 치환. 1억 미만·연도·%는 불변.

    '1,289,630,423,605' → '1.3조', '170688596929.0' → '1,707억'. '2021'(연도)·'15.94%'는
    자릿수 미달로 건드리지 않는다(오변환 방지). 렌더 시점 적용이라 캐시된 카드도 즉시 반영된다.
    """

    def _repl(m: re.Match[str]) -> str:
        raw = m.group()
        try:
            val = float(raw.replace(",", ""))
        except ValueError:
            return raw
        if abs(val) < 1e8:  # 1억 미만은 그대로(작은 수 오변환 방지)
            return raw
        return fmt_krw(val) + "원"

    return _LONG_AMOUNT.sub(_repl, text or "")


def series_points(rows: list[dict], series_key: str) -> list[dict]:
    """account_level_series에서 이 계정의 (연도, 금액) 시계열을 연도 오름차순으로."""

    points = [
        {"year": int(r["year"]), "amount": float(r["amount"])}
        for r in rows or []
        if str(r.get("series_key")) == str(series_key) and r.get("amount") is not None
    ]
    return sorted(points, key=lambda p: p["year"])


def evidence_rows(card: Any, exclude_accounts: set[str] | None = None) -> list[dict]:
    """카드 numeric_evidence → 표 행(계정·연도·금액). 동일 (locator,year,value) 중복 제거.

    exclude_accounts: 분해 표에 이미 나온 계정명 — 같은 숫자를 두 번 대지 않는다(중복 노이즈).
    locator의 fs_div 접두를 벗긴 이름으로 비교한다("CFS:영업이익" ↔ "영업이익").
    """

    exclude_accounts = exclude_accounts or set()
    seen: set[tuple] = set()
    out: list[dict] = []
    for ref in _get(card, "numeric_evidence") or []:
        row_key = (_get(ref, "locator"), _get(ref, "year"), _get(ref, "value"))
        if row_key in seen:
            continue
        seen.add(row_key)
        locator = str(_get(ref, "locator") or "")
        if locator.startswith("ratio:"):
            continue  # 원시 지표 키(ratio:… = 3 류)는 못 읽는 노이즈 — 주장 서술이 대신함
        _, bare_name = split_series_key(locator)
        if bare_name in exclude_accounts or locator in exclude_accounts:
            continue  # 분해 표가 이미 보여준 계정 — 재나열 금지
        raw_value = _get(ref, "value")
        out.append(
            {
                "계정": locator,
                "연도": str(_get(ref, "year") or ""),
                "금액": fmt_krw(raw_value) if fmt_krw(raw_value) != "-" else str(raw_value or "-"),
            }
        )
    return out


def decomposition_accounts(out: dict | None) -> set[str]:
    """분해 표에 등장하는 계정명 집합(부모+전 leaf·소계) — 근거 수치 중복 제거 기준."""

    if not out:
        return set()
    _, parent_name = split_series_key(str(out.get("parent", "")))
    names = {parent_name}

    def collect(rows: list[dict]) -> None:
        for r in rows:
            names.add(str(r.get("account", "")))
            if r.get("children"):
                collect(r["children"])

    collect(out.get("rows") or [])
    return names


def claim_lines(card: Any) -> list[dict]:
    """카드 claims → 표시 행(관점 라벨·설명·인용수치). 빈 설명은 제외."""

    out: list[dict] = []
    for claim in _get(card, "claims") or []:
        description = str(_get(claim, "description") or "").strip()
        if not description:
            continue
        perspective = str(_get(claim, "perspective") or "")
        out.append(
            {
                "perspective": PERSPECTIVE_LABELS.get(perspective, perspective),
                "description": humanize_amounts(description),
                "cited_value": _get(claim, "cited_value"),
            }
        )
    return out


def waterfall_leaves(out: dict) -> list[tuple[str, float]]:
    """분해 결과를 워터폴 leaf 기여 목록으로 평탄화(소계는 children로 대체 — 이중계상 방지).

    children이 있는 행(매출총이익 등)은 자신 대신 하위 기여를 쓰고, 하위 미설명분이
    유의하면(>0.5% of 행Δ) 별도 leaf로 보존. 최상위 미설명 잔차도 0이 아니면 leaf로.
    Σleaves == 부모 delta (부동소수 오차 내) — 워터폴 시작+기여=끝 항등 유지.
    """

    leaves: list[tuple[str, float]] = []

    def collect(rows: list[dict]) -> None:
        for r in rows:
            if r.get("delta") is None:
                continue  # 결측 구성은 잔차가 흡수(표에서 '결측'으로 이미 노출)
            if r.get("children"):
                collect(r["children"])
                resid = float(r.get("child_residual") or 0.0)
                if abs(resid) > 0.005 * max(abs(r["delta"]), 1.0):
                    leaves.append((f"{r['account']} 기타", resid))
            else:
                leaves.append((str(r["account"]), float(r["delta"])))

    collect(out.get("rows") or [])
    residual = float(out.get("residual") or 0.0)
    delta = float(out.get("delta") or 0.0)
    if abs(residual) > 0.001 * max(abs(delta), 1.0):
        leaves.append(("미설명 잔차", residual))
    return leaves


def contribution_cell_style(pct: float | None) -> str:
    """기여율 셀 배경 CSS — 방향(빨강=끌어내림/초록=방어) × 강도(|기여율| 비례, 상한 0.5).

    표만 훑어도 어느 행이 세게 끌어내렸는지 색 농도로 읽히게 한다. 잔차·빈 값은 무색.
    """

    if pct is None or pct == 0:
        return ""
    alpha = round(min(0.12 + abs(pct) / 300, 0.5), 3)
    rgb = "227,73,72" if pct < 0 else "27,175,122"  # 워터폴 극성 색과 동일 계열
    return f"background-color: rgba({rgb},{alpha})"


def key_driver_sentence(out: dict) -> str:
    """분해 결과에서 최대 하락·방어 요인을 한 문장으로(결정론 — LLM 없이 '왜'의 핵심 제공)."""

    leaves = [(name, d) for name, d in waterfall_leaves(out) if name != "미설명 잔차" and d]
    if not leaves:
        return ""
    down = min(leaves, key=lambda x: x[1])  # 가장 큰 음(하락 주도)
    up = max(leaves, key=lambda x: x[1])  # 가장 큰 양(방어)
    parts = []
    if down[1] < 0:
        parts.append(f"{down[0]} {fmt_krw(down[1])}원이 하락을 주도")
    if up[1] > 0 and up[0] != down[0]:
        parts.append(f"{up[0]} {fmt_krw(up[1])}원이 일부 방어")
    return ", ".join(parts) + "." if parts else ""


def review_point(out: dict | None, series_rows: list[dict]) -> str:
    """두괄식 검토 포인트 — 괴리 명제("매출 -6.7%인데 영업이익 -62.8%") + 주도·방어 결합.

    "떨어졌다" 자체가 아니라 "왜 이 낙폭이 비정상인가"를 카드 첫 줄에 찍는다(결정론 —
    분해·시계열만 사용, LLM 없음). 괴리 배수 ≥2일 때만 괴리 명제를 붙인다(정상 비례
    변동에 헛경고 금지). 분해 없으면 ""(두괄식 강요 금지).
    """

    if not out:
        return ""
    fs_div, _, _ = str(out.get("parent", "")).partition(":")
    _, parent_name = split_series_key(str(out.get("parent", "")))
    parts: list[str] = []
    p_pct = out.get("change_pct")
    sales = {p["year"]: p["amount"] for p in series_points(series_rows, f"{fs_div}:매출")}
    prior, cur = sales.get(out.get("prior_year")), sales.get(out.get("year"))
    if parent_name != "매출" and p_pct is not None and prior and cur is not None:
        s_pct = round((cur - prior) / abs(prior) * 100, 1)
        if s_pct and abs(p_pct) / abs(s_pct) >= 2:
            ratio = abs(p_pct) / abs(s_pct)
            parts.append(
                f"매출은 {s_pct:+.1f}%인데 {parent_name}은 {p_pct:+.1f}% "
                f"({ratio:.1f}배 괴리) — 비용·원가 구조 변화가 검토 포인트"
            )
    driver = key_driver_sentence(out)
    if driver:
        parts.append(driver.rstrip("."))
    return ". ".join(parts) + "." if parts else ""


def conclusion_view(card: Any) -> dict | None:
    """조사 결론 → 표시 재료(금액 축약 적용). 없으면 None('조사 미수행' 캡션은 view가)."""

    inv = _get(card, "investigation")
    if not inv:
        return None
    texts = lambda key: [humanize_amounts(str(t)) for t in (_get(inv, key) or [])]  # noqa: E731
    return {
        "headline": humanize_amounts(str(_get(inv, "headline") or "")),
        "cause_path": texts("cause_path"),
        "anomaly_points": texts("anomaly_points"),
        "open_questions": texts("open_questions"),
        "resolved": bool(_get(inv, "resolved")),
        "method": str(_get(inv, "method") or ""),
        "tool_requests": int(_get(inv, "tool_requests") or 0),
    }


CARD_GROUPS_PATH = Path("config/card_groups.yaml")


def load_card_groups(path: Path = CARD_GROUPS_PATH) -> dict:
    """카드 표시 그룹 설정(order·by_issue_type). 파일 부재는 빈 dict(그룹핑 생략 graceful)."""

    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload.get("card_groups", {}) or {}


def group_cards(cards: list, groups: dict | None = None) -> list[tuple[str, list]]:
    """카드를 넓은 주제 그룹으로 묶는다(1차 구조 — 점수 전체 줄세우기 대체).

    그룹 순서는 config order, 그룹 안은 표수 내림 → 점수 내림(점수는 같은 주제 안의
    순서로만 쓰인다). 매핑에 없는 issue_type은 마지막 그룹('기타')으로 — 드롭 0."""

    cfg = groups if groups is not None else load_card_groups()
    mapping = cfg.get("by_issue_type") or {}
    order = list(cfg.get("order") or [])
    fallback = order[-1] if order else "기타"
    buckets: dict[str, list] = {}
    for card in cards:
        issue = _get(card, "issue_type")
        issue = str(getattr(issue, "value", issue) or "")
        buckets.setdefault(mapping.get(issue, fallback), []).append(card)
    for group in buckets.values():
        group.sort(
            key=lambda c: (
                int(_get(c, "vote_count") or 0),
                float(_get(c, "priority_score") or 0.0),
            ),
            reverse=True,
        )
    ordered = [g for g in order if g in buckets] + [g for g in buckets if g not in order]
    return [(g, buckets[g]) for g in ordered]


def sort_cards(cards: list) -> list:
    """카드 정렬 — 연속 우선순위 내림, 동점이면 유의성 내림(라벨 폐지, PLAN §5)."""

    return sorted(
        cards,
        key=lambda c: (
            float(_get(c, "priority_score") or 0.0),
            float(_get(c, "materiality_score") or 0.0),
        ),
        reverse=True,
    )


def card_headline(card: Any, out: dict | None, series_rows: list[dict]) -> str:
    """단추 라벨용 한 줄 헤드라인 — 괴리 명제 > 주도 문장 > claims 첫 문장 > subtype 순 폴백."""

    point = review_point(out, series_rows)
    if point:
        return point.split(" — ")[0].split(". ")[0]  # 첫 절만(라벨은 짧게)
    lines = claim_lines(card)
    if lines:
        first = lines[0]["description"].split(". ")[0]
        return first[:60] + ("…" if len(first) > 60 else "")
    subtype = str(_get(card, "subtype") or "")
    if subtype:
        return subtype
    issue = _get(card, "issue_type")
    return str(getattr(issue, "value", issue) or "")


def index_points(points: list[dict]) -> list[dict]:
    """시계열을 첫 관측=100 지수로. 관계 카드는 절대금액 스케일 차이 대신 '벌어짐'을 본다."""

    if not points:
        return []
    base = points[0]["amount"]
    if not base:
        return []
    return [{"year": p["year"], "amount": p["amount"] / abs(base) * 100} for p in points]


def yoy_labels(points: list[dict]) -> list[str]:
    """막대 위 전년비 % 라벨(첫해는 빈칸). 급변이 어느 해인지 막대만 봐도 읽히게."""

    labels = [""]
    for prev, cur in zip(points, points[1:], strict=False):
        if prev["amount"]:
            labels.append(f"{(cur['amount'] - prev['amount']) / abs(prev['amount']) * 100:+.0f}%")
        else:
            labels.append("")
    return labels


def legs_top(related: list[str], rows: list[dict], limit: int = 4) -> list[str]:
    """관계 카드 다리 중 최대 절대금액 상위 limit개(차트 시리즈 상한 — 색 4슬롯 고정)."""

    def max_abs(key: str) -> float:
        pts = series_points(rows, key)
        return max((abs(p["amount"]) for p in pts), default=0.0)

    return sorted(related or [], key=max_abs, reverse=True)[:limit]
