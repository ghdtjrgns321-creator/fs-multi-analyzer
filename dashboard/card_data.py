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


def disclosed_label(series_rows: list[dict], series_key: str) -> str:
    """공시 원문 계정명(설계3) — 최신 연도 행의 label. 없으면 빈 문자열(정준명 폴백은 호출부)."""

    rows = [
        r
        for r in series_rows or []
        if str(r.get("series_key")) == series_key and str(r.get("label") or "").strip()
    ]
    if not rows:
        return ""
    latest = max(rows, key=lambda r: int(r.get("year") or 0))
    return str(latest.get("label") or "").strip()


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
        # '1,798,862,505,633' 같은 쉼표 문자열도 축약(단위 혼재 방지 — 표에 원단위 생노출 금지).
        amount = float(str(value).replace(",", "")) if isinstance(value, str) else float(value)
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


# 근거 locator의 내부 네임스페이스 → 사람용 출처 라벨(화면에 내부 식별자 노출 금지).
_EVIDENCE_SOURCE_LABELS = {"report_extracts": "공시 본문", "note_facts": "주석", "note": "주석"}


def _is_metric_key(locator: str) -> bool:
    """지표 원시 키 판정(구 카드 폴백 — 신규 카드는 grounding resolved_kind가 담당).

    규칙은 grounding과 동일: 계정 표식(한글 라벨 / '코드|라벨' 파이프 / fs_div 접두 /
    서술 네임스페이스)이 하나도 없는 **ASCII-only 참조는 전부 지표**로 본다 — 구분자
    형식(점·콜론·언더스코어)을 예상하지 않는다(실측: LLM이 임의 형식을 발명함)."""

    prefix, _, _rest = locator.partition(":")
    if prefix in _EVIDENCE_SOURCE_LABELS or prefix in FS_DIV_LABELS:
        return False
    if "|" in locator:
        return False
    return bool(locator) and not any("가" <= ch <= "힣" for ch in locator)


def _parse_amount(value: Any) -> float | None:
    """금액 파싱('1,798,862,505,633' 허용). 서술형 텍스트는 None — 표/목록 분리 기준."""

    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _evidence_display(locator: str) -> str:
    """locator → 사람용 라벨: 'ASCII접두:'·fs_div·'코드|' 접두 제거(접두 열거 안 함)."""

    prefix, _, rest = locator.partition(":")
    if rest and not any("가" <= ch <= "힣" for ch in prefix):
        base = rest
    else:
        _, base = split_series_key(locator)
    return base.split("|")[-1].strip() or base or locator


def evidence_rows(card: Any, exclude_accounts: set[str] | None = None) -> list[dict]:
    """카드 numeric_evidence 중 **금액형**만 → 표 행(계정·연도·금액).

    서술형(비금액 값)은 narrative_evidence()가 목록으로 담당 — 금액 칸에 문장이
    잘려 들어가는 것 금지(사용자 지적). exclude_accounts: 분해 표 계정 재나열 금지.
    """

    exclude_accounts = exclude_accounts or set()
    seen: set[tuple] = set()
    out: list[dict] = []
    for ref in _get(card, "numeric_evidence") or []:
        locator = str(_get(ref, "locator") or "")
        kind = _get(ref, "resolved_kind")
        if kind in ("metric", "narrative"):
            continue  # grounding이 판정한 종류(구조화) — 지표는 미표시, 서술은 목록 담당
        if kind is None and _is_metric_key(locator):
            continue  # 구 카드 폴백(kind 없던 시절 저장분) — 형태 역추정
        raw_value = _get(ref, "value")
        amount = _parse_amount(raw_value)
        if amount is None:
            continue  # 서술형 근거 — narrative_evidence가 목록으로 렌더
        display = str(_get(ref, "display_label") or "") or _evidence_display(locator)
        _, bare_name = split_series_key(locator)
        # 중복 키 = (표시라벨, 연도, 정규화 금액) — 표기만 다른 같은 값 2행 차단.
        row_key = (display, str(_get(ref, "year") or ""), amount)
        if row_key in seen:
            continue
        seen.add(row_key)
        if (
            display in exclude_accounts
            or bare_name in exclude_accounts
            or locator in exclude_accounts
        ):
            continue  # 분해 표가 이미 보여준 계정 — 재나열 금지
        out.append(
            {
                "계정": display,
                "연도": str(_get(ref, "year") or ""),
                "금액": fmt_krw(raw_value),
            }
        )
    return out


def narrative_evidence(card: Any) -> list[dict]:
    """서술형 근거(비금액 값) → [{출처, 제목, 내용}] — 읽는 목록용(표 금지).

    내부 네임스페이스는 사람용 출처 라벨(공시 본문/주석)로 바꾼다. 중복(제목·내용) 제거."""

    seen: set[tuple] = set()
    out: list[dict] = []
    for ref in _get(card, "numeric_evidence") or []:
        raw_value = _get(ref, "value")
        if raw_value is None or _parse_amount(raw_value) is not None:
            continue
        locator = str(_get(ref, "locator") or "")
        kind = _get(ref, "resolved_kind")
        if kind == "metric" or (kind is None and _is_metric_key(locator)):
            continue  # 지표 kv 서술("target_value …")이 목록으로 새는 것 차단(구 카드는 폴백)
        prefix, _, _rest = locator.partition(":")
        source = _EVIDENCE_SOURCE_LABELS.get(prefix, "근거")
        title = str(_get(ref, "display_label") or "") or _evidence_display(locator)
        content = humanize_amounts(str(raw_value).strip())
        key = (title, content)
        if key in seen or not content:
            continue
        seen.add(key)
        out.append({"출처": source, "제목": title, "내용": content})
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


def short_headline(text: str, limit: int = 60) -> str:
    """카드 단추 라벨용 축약 — 첫 문장만, limit자 초과는 말줄임(빽빽한 목록 방지)."""

    first = str(text or "").split(". ")[0].split("다. ")[0].strip().rstrip(".")
    if len(first) > limit:
        return first[:limit] + "…"
    return first


def perspective_badge(card: Any) -> str:
    """어느 관점이 지적했나 배지 — '수치·추세 의심'. 내부 발견 관점만, 중복 1회."""

    names: list[str] = []
    internal = {"numeric", "note", "flow", "trend"}
    for claim in _get(card, "claims") or []:
        perspective = str(_get(claim, "perspective") or "")
        label = PERSPECTIVE_LABELS.get(perspective, "")
        if perspective in internal and label and label not in names:
            names.append(label)
    return "·".join(names) + " 의심" if names else ""


def card_label(card: Any, decomposition: dict | None, series_rows: list[dict]) -> str:
    """카드 단추 라벨 — 완결된 핵심 한 줄(중간 절단 금지).

    우선순위: ①조사원이 쓴 목록용 label(40자 완결 구문) ②결정론 검토포인트
    (괴리 명제·주도요인 — 항상 완결 문장) ③주장 첫 문장 축약(최후 폴백)."""

    inv = _get(card, "investigation")
    conclusion_label = str(_get(inv, "label") or "").strip() if inv else ""
    if conclusion_label:
        return humanize_amounts(conclusion_label)
    if decomposition:
        point = review_point(decomposition, series_rows)
        if point:
            return point.split(" — ")[0].split(". ")[0].rstrip(".")
    lines = claim_lines(card)
    if lines:
        return short_headline(lines[0]["description"])
    inv_headline = str(_get(inv, "headline") or "") if inv else ""
    if inv_headline:
        return short_headline(humanize_amounts(inv_headline))
    subtype = str(_get(card, "subtype") or "")
    if subtype:
        return subtype
    issue = _get(card, "issue_type")
    return str(getattr(issue, "value", issue) or "")


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
