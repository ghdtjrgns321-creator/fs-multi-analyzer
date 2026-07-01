"""삼성 DART 원본(raw) 전수 재구성 — 프로젝트 정규화 미경유(독립 회계분석용).

각 연도 finstate JSON에는 당기/전기/전전기 3년치가 들어있다. 여러 연도 파일을 합쳐
계정별 다년 시계열을 raw 그대로 복원한다(매퍼·게이트 안 탐). 이것을 LLM이 직접 읽고
회계사 관점으로 이상점을 독립 판단한 뒤 프로젝트 산출물과 대조한다(§10 population-first).

실행: PYTHONPATH=. uv run python data/backtest/_samsung_raw_consolidate.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CORP = sys.argv[1] if len(sys.argv) > 1 else "00126380"  # 대상 corp(인자화)
FILE_YEARS = [2021, 2022, 2023, 2024]  # 각 파일이 ±2년 보유 → 2019~2024 커버
ROOT = Path("data/companies") / CORP


def _amt(v: str | None) -> float | None:
    if v in (None, "", "-"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _load(fs_div: str) -> list[dict]:
    rows: list[dict] = []
    for y in FILE_YEARS:
        p = ROOT / str(y) / "raw" / f"finstate_all_{fs_div}.json"
        if p.exists():
            rows.extend(json.load(open(p, encoding="utf-8")))
    return rows


def _series(rows: list[dict]) -> dict:
    """(sj_div, account_nm) → {year: amount}. 당기/전기/전전기 3컬럼을 연도로 펼쳐 합본."""
    out: dict[tuple, dict[int, float]] = {}
    for r in rows:
        key = (r["sj_div"], r["account_nm"])
        base = int(r["bsns_year"])
        for col, yr in (
            ("thstrm_amount", base),
            ("frmtrm_amount", base - 1),
            ("bfefrmtrm_amount", base - 2),
        ):
            a = _amt(r.get(col))
            if a is not None:
                out.setdefault(key, {})[yr] = a  # 최신 파일이 우선(뒤 덮어씀)
    return out


def _print_div(rows: list[dict], sj: str, label: str, fs: str) -> None:
    series = {k: v for k, v in _series(rows).items() if k[0] == sj}
    years = sorted({y for v in series.values() for y in v})
    print(f"\n## [{fs}] {label} ({sj}) — {len(series)}과목, 연도 {years}")
    # 최신연도 절대금액 내림차순
    latest = max(years) if years else 0
    ordered = sorted(series.items(), key=lambda kv: -abs(kv[1].get(latest, 0) or 0))
    for (_, name), ts in ordered:
        cells = []
        for y in years:
            val = ts.get(y)
            cells.append(f"{y}:{val / 1e8:>14,.0f}" if val is not None else f"{y}:{'·':>14}")
        # YoY (최신/직전)
        cur, prev = ts.get(latest), ts.get(latest - 1)
        yoy = (
            f"{(cur - prev) / abs(prev) * 100:+.0f}%"
            if cur is not None and prev not in (None, 0)
            else "-"
        )
        print(f"  {name:28s} {'  '.join(cells)}  YoY={yoy}")


def main() -> None:
    print(f"=== 삼성전자 {CORP} DART 원본 전수 재구성 (단위: 억원, 매퍼 미경유) ===")
    for fs in ("CFS", "OFS"):
        rows = _load(fs)
        print(f"\n{'=' * 78}\n{fs} ({'연결' if fs == 'CFS' else '별도'}) — raw {len(rows)}행")
        for sj, label in [
            ("BS", "재무상태표"),
            ("IS", "손익계산서"),
            ("CIS", "포괄손익"),
            ("CF", "현금흐름표"),
            ("SCE", "자본변동표"),
        ]:
            _print_div(rows, sj, label, fs)


if __name__ == "__main__":
    main()
