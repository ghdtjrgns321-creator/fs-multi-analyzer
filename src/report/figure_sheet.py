"""반박 서술 수치 도표(figure sheet) — 코드가 as-filed series에서 정확 수치를 계산해 LLM에 주고,
서술 숫자가 그 도표의 멤버인지 감사한다(근본수정 B/예방, 설계 spec 2026-07-14).

reader.py의 "계산 금지·원문 인용만" 가드를 반박 에이전트로 확장하는 인프라. LLM이 파생값
(증감·비율)을 직접 계산하다 내는 환각(예: 아스트 "자산 583.1억 감소" ← 실제 298.8억)을 막는다.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

# 분석 축이 되는 핵심 총계 — 어떤 카드든 도표에 항상 포함(교차 인용 대비).
KEY_TOTALS = frozenset(
    {
        "자산총계",
        "부채총계",
        "자본총계",
        "매출액",
        "매출",
        "매출원가",
        "당기순이익",
        "당기순이익(손실)",
        "영업이익",
        "영업활동현금흐름",
        "이익잉여금",
    }
)

_SCALE = {"조": 1e12, "억": 1e8, "백만원": 1e6, "백만": 1e6, "원": 1.0}
_MONEY_RE = re.compile(r"(-?\d[\d,]*(?:\.\d+)?)\s*(조|억|백만원|백만|원)")
_PCT_RE = re.compile(r"(-?\d[\d,]*(?:\.\d+)?)\s*%")
_SKIP_TOKENS = {"acct", "rel", "company", "BS", "IS", "CF", "SCE", "CFS", "OFS"}


def _field(card: Any, name: str, default: Any = None) -> Any:
    """카드가 dict든 pydantic 객체든 필드 접근."""

    if isinstance(card, dict):
        return card.get(name, default)
    return getattr(card, name, default)


def extract_figures(text: str) -> tuple[list[float], list[float]]:
    """서술 텍스트에서 금액(조/억/백만/원)·비율(%)을 파싱. 반환 (원단위 금액 abs, 비율 abs).

    단위 없는 맨숫자(연도·개수)는 금액으로 오인하지 않는다(단위 필수).
    """

    monies: list[float] = []
    pcts: list[float] = []
    for num, unit in _MONEY_RE.findall(text or ""):
        try:
            monies.append(abs(float(num.replace(",", "")) * _SCALE[unit]))
        except ValueError:
            pass
    for num in _PCT_RE.findall(text or ""):
        try:
            pcts.append(abs(float(num.replace(",", ""))))
        except ValueError:
            pass
    return monies, pcts


@dataclass(frozen=True)
class FigureSheet:
    """카드별 근거 수치 집합 + 프롬프트용 렌더. 금액은 억(0.1) · 비율은 %p(0.1) 반올림 멤버십."""

    money: frozenset[float]
    growth: frozenset[float]
    lines: tuple[str, ...]

    def contains_money(self, raw_krw: float) -> bool:
        return round(abs(raw_krw) / 1e8, 1) in self.money

    def contains_pct(self, pct: float) -> bool:
        return round(abs(pct), 1) in self.growth

    def render(self) -> str:
        return "\n".join(self.lines)


def _fmt_eok(raw_krw: float) -> str:
    return f"{raw_krw / 1e8:,.1f}억"


def build_figure_sheet(
    scope_names: Iterable[str],
    series_rows: list[dict],
    extra_amounts: Iterable[float] = (),
) -> FigureSheet:
    """스코프 계정 + 핵심 총계의 원값·델타·증감율을 as-filed series에서 계산한 도표.

    델타/증감율은 최신연도 vs 각 이전연도(다년 추이) + 연속 YoY만 — 임의 조합(합계) 배제로
    환각 흡수 방지. extra_amounts(카드 자체 note/numeric 금액)는 그대로 포함.
    """

    names = set(scope_names) | KEY_TOTALS
    # series_key(fs_div 포함)로 분리 — 동명 CFS/OFS를 병합·덮어쓰면 값이 오염된다.
    by_series: dict[str, dict[int, float]] = defaultdict(dict)
    label_of: dict[str, str] = {}
    for row in series_rows:
        if row.get("canonical") in names or row.get("label") in names:
            key = str(row.get("series_key") or f"{row.get('fs_div')}:{row.get('canonical')}")
            try:
                by_series[key][int(row["year"])] = float(row["amount"])
                label_of[key] = str(row.get("canonical") or row.get("label") or key)
            except (ValueError, TypeError, KeyError):
                pass

    money: set[float] = set()
    growth: set[float] = set()
    lines: list[str] = []
    for key in sorted(by_series):
        ys = by_series[key]
        nm = label_of[key]
        years = sorted(ys)
        for y in years:
            money.add(round(abs(ys[y]) / 1e8, 1))
        latest = years[-1]
        # 연속 YoY만 — 다년 임의쌍 델타는 집합을 넓혀 환각(583.1)을 흡수하므로 배제.
        # render도 YoY만 보여주고, B에선 LLM이 render 값만 인용하므로 이 범위가 근거의 전부다.
        pairs = {(years[i], years[i - 1]) for i in range(1, len(years))}
        for a_y, b_y in pairs:
            delta = ys[a_y] - ys[b_y]
            money.add(round(abs(delta) / 1e8, 1))
            if ys[b_y]:
                growth.add(round(abs(delta / ys[b_y] * 100), 1))
        if len(years) >= 2:
            d = ys[latest] - ys[years[-2]]
            lines.append(
                f"{nm}: {years[-2]} {_fmt_eok(ys[years[-2]])} → {latest} {_fmt_eok(ys[latest])} "
                f"(YoY 증감 {_fmt_eok(d)})"
            )
        elif years:
            lines.append(f"{nm}: {latest} {_fmt_eok(ys[latest])}")

    for amt in extra_amounts:
        try:
            money.add(round(abs(float(amt)) / 1e8, 1))
        except (ValueError, TypeError):
            pass

    return FigureSheet(frozenset(money), frozenset(growth), tuple(lines))


def audit_narrative_figures(texts: Iterable[str], sheet: FigureSheet) -> list[str]:
    """서술 텍스트들의 금액·비율이 도표 멤버인지 감사. 도표에 없는(근거없는) 표기 문자열 반환."""

    flagged: list[str] = []
    for text in texts:
        for num, unit in _MONEY_RE.findall(text or ""):
            try:
                raw = abs(float(num.replace(",", "")) * _SCALE[unit])
            except ValueError:
                continue
            if not sheet.contains_money(raw):
                flagged.append(f"{num}{unit}")
        for num in _PCT_RE.findall(text or ""):
            try:
                if not sheet.contains_pct(abs(float(num.replace(",", "")))):
                    flagged.append(f"{num}%")
            except ValueError:
                continue
    return flagged


def card_scope_names(card: Any) -> set[str]:
    """카드가 가리키는 계정명 집합 — cluster_key(접두·fs_div 제외) + related_accounts."""

    names: set[str] = set(_field(card, "related_accounts") or [])
    for part in str(_field(card, "cluster_key", "") or "").split(":"):
        for token in part.split("|"):
            token = token.strip()
            if token and token not in _SKIP_TOKENS:
                names.add(token)
    return names


__all__ = [
    "FigureSheet",
    "KEY_TOTALS",
    "audit_narrative_figures",
    "build_figure_sheet",
    "card_scope_names",
    "extract_figures",
]
