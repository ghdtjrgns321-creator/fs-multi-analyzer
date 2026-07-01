"""Phase1 누락 근본원인 — capex·관계기업이 universal scan 어느 조건서 탈락했는지 재현.

universal.py 로직(floor=자산×1%∨1억, YoY≥50%, valid_yoy_base=전기≥prior_floor·동부호)을
실 DB 시계열로 그대로 계산해 탈락 지점을 특정한다. account_series 포함여부로 Phase1탈락 vs
관점미선택을 구분한다. 단일 회사 일반화 금지(§10) — capex·관계기업 각각 독립 판정.

실행: PYTHONPATH=. uv run python data/backtest/_e2e_signal_probe.py
"""

from __future__ import annotations

import duckdb

from config.settings import settings
from src.db.normalized import db_path
from src.report.company_report import build_company_report
from src.signals.config import load_l2_config

CORP = "00112457"
YEARS = [2021, 2022, 2023, 2024]
ROOT = settings.data_dir

T = load_l2_config()["signal_thresholds"]
YOY = float(T["yoy_pct_abs"])
PCT = float(T["universal_min_pct_of_assets"])
ABS_MIN = float(T["universal_min_abs_amount"])


def series(label_like: str, sj: str) -> dict[int, float]:
    """CFS에서 label LIKE인 계정의 연도별 amount(원)."""
    out: dict[int, float] = {}
    for y in YEARS:
        p = db_path(CORP, y, ROOT)
        if not p.exists():
            continue
        con = duckdb.connect(str(p), read_only=True)
        try:
            rows = con.execute(
                "SELECT amount FROM normalized_financials "
                "WHERE fs_div='CFS' AND sj_div=? AND label LIKE ? AND amount IS NOT NULL",
                [sj, f"%{label_like}%"],
            ).fetchall()
        finally:
            con.close()
        if rows:
            out[y] = float(sum(r[0] for r in rows))
    return out


def asset_floor() -> dict[int, float]:
    out: dict[int, float] = {}
    a = series("자산총계", "BS")
    for y, amt in a.items():
        out[y] = max(abs(amt) * PCT / 100, ABS_MIN)
    return out


def judge(name: str, ser: dict[int, float], floors: dict[int, float]) -> None:
    print(f"\n=== {name} ===")
    yrs = sorted(ser)
    for y in yrs:
        f = floors.get(y, ABS_MIN)
        print(
            f"  {y}: {ser[y]:>16,.0f}원 ({ser[y] / 1e6:>9,.0f}백만) floor={f / 1e6:,.0f}백만 "
            f"{'>=floor' if abs(ser[y]) >= f else '<floor(스캔제외)'}"
        )
    if 2024 in ser and 2023 in ser:
        cur, pri = ser[2024], ser[2023]
        floor24 = floors.get(2024, ABS_MIN)
        floor23 = floors.get(2023, ABS_MIN)
        yoy = (cur - pri) / abs(pri) * 100 if pri else float("nan")
        valid_base = abs(pri) >= floor23 and cur * pri > 0
        print(f"  YoY(2024/2023) = {yoy:+.1f}%  (임계 {YOY}%)")
        print(
            f"  current>=floor24: {abs(cur) >= floor24}  | prior>=prior_floor23: {abs(pri) >= floor23} "
            f"({pri / 1e6:,.0f} vs {floor23 / 1e6:,.0f}백만)"
        )
        print(f"  valid_yoy_base: {valid_base}")
        # 신호 발생 판정
        fires = abs(cur) >= floor24 and valid_base and abs(yoy) >= YOY
        if not (abs(cur) >= floor24):
            reason = "현재값 floor 미달"
        elif not valid_base:
            reason = "valid_yoy_base False(전기 기저 floor 미달 또는 부호상이)"
        elif abs(yoy) < YOY:
            reason = f"YoY {abs(yoy):.1f}% < 임계 {YOY}%"
        else:
            reason = "-"
        print(f"  >>> universal_yoy 신호 발생? {fires}  (미발생 사유: {reason})")
    n_hist = len([y for y in yrs if y < 2024])
    print(
        f"  z_score 이력 연도수: {n_hist} (필요 4) → {'가능' if n_hist >= 4 else '불가(이력부족)'}"
    )


def main() -> None:
    floors = asset_floor()
    print(f"임계: YoY≥{YOY}% · floor=자산×{PCT}%∨{ABS_MIN / 1e8:.0f}억")
    print(
        "자산총계/floor: " + ", ".join(f"{y}:{floors[y] / 1e6:,.0f}백만" for y in sorted(floors))
    )

    capex = series("유형자산의 취득", "CF")
    assoc = series("관계기업에 대한 투자", "BS")
    judge("유형자산취득(capex, CF)", capex, floors)
    judge("관계기업투자(BS)", assoc, floors)
    equity_loss = series("지분법손실", "CF")
    judge("지분법손실(CF)", equity_loss, floors)

    # account_level_series 포함 여부(Phase2 관점에 데이터 전달됐나)
    report = build_company_report(CORP, YEARS)
    series_keys = {str(r.get("series_key")) for r in report.get("account_level_series", [])}
    print("\n=== account_level_series 포함 여부(Phase2 관점 전달) ===")
    for key in ["유형자산취득", "관계기업투자", "지분법손실", "유형자산", "단기차입금"]:
        hit = [k for k in series_keys if key in k]
        print(f"  '{key}': {'포함 ' + str(hit) if hit else '미포함'}")
    print(f"  series_keys 총 {len(series_keys)}종")


if __name__ == "__main__":
    main()
