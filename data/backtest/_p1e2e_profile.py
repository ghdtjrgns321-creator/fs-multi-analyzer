"""P1 E2E 검증 0단계 — 전 회사연도 프로파일(규모·금융업·양식세대) 수집.

층화 샘플(규모×금융업×양식) 셀 경계를 데이터로 정하기 위한 사전 측정.
금융업 판별: induty_code가 raw에 없어 BS 금융 특유 계정 패턴으로 근사(은행·보험·증권·카드).
자산총계: BS 'ifrs-full_Assets'/'자산총계' 당기 금액. 양식세대: 보고연도(bsns_year).

실행: PYTHONPATH=. uv run python data/backtest/_p1e2e_profile.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path("data/companies")
OUT = Path("data/backtest/_p1e2e_profile.jsonl")

# 금융업 특유 BS 계정(전역·하드코딩 아님 — 업종 판별 근사 마커). 일반 제조/서비스엔 없음.
FIN_MARKERS = (
    "예수부채",
    "보험계약부채",
    "대출채권",
    "책임준비금",
    "보험료적립금",
    "예수금",
    "콜머니",
    "예대",
)


def profile_one(path: Path) -> dict | None:
    asset: float | None = None
    fin = False
    rows = 0
    try:
        with path.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                rows += 1
                if r.get("sj_div") != "BS":
                    continue
                nm = r.get("account_nm") or ""
                aid = r.get("account_id") or ""
                if asset is None and (nm == "자산총계" or aid == "ifrs-full_Assets"):
                    try:
                        asset = float(r.get("thstrm_amount") or 0)
                    except ValueError:
                        pass
                if any(m in nm for m in FIN_MARKERS):
                    fin = True
    except Exception:
        return None
    return {"asset": asset, "fin": fin, "rows": rows}


def main() -> None:
    out: list[dict] = []
    for cdir in sorted(ROOT.iterdir()):
        if not cdir.is_dir() or not cdir.name.isdigit():
            continue
        corp = cdir.name
        for ydir in sorted(cdir.iterdir()):
            if not ydir.is_dir():
                continue
            raw = ydir / "raw"
            cfs = raw / "finstate_all_CFS.csv"
            ofs = raw / "finstate_all_OFS.csv"
            path = cfs if cfs.exists() else (ofs if ofs.exists() else None)
            if path is None:
                continue
            prof = profile_one(path)
            if prof is None:
                continue
            note_xbrl = (raw / "notes_xbrl").exists()
            prof.update(
                corp=corp, year=ydir.name, fs=path.name.split("_")[-1].split(".")[0], note=note_xbrl
            )
            out.append(prof)

    OUT.write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in out), encoding="utf-8")

    with_asset = [o for o in out if o.get("asset")]
    fins = [o for o in out if o["fin"]]
    notes = [o for o in out if o["note"]]
    print(
        f"회사연도 총 {len(out)} | 자산총계 보유 {len(with_asset)} | 금융업 {len(fins)} | 주석보유 {len(notes)}"
    )
    if with_asset:
        assets = sorted(o["asset"] for o in with_asset)
        n = len(assets)
        q = [assets[int(n * p)] for p in (0.25, 0.5, 0.75, 0.9, 0.99)]
        print(f"자산총계 분위(원) p25/p50/p75/p90/p99: {[f'{v:,.0f}' for v in q]}")
    fin_corps = sorted({o["corp"] for o in fins})
    print(f"금융업 회사 수(고유 corp) {len(fin_corps)}: {fin_corps[:20]}")
    years = sorted({o["year"] for o in out})
    print(f"보고연도 분포: {years}")


if __name__ == "__main__":
    main()
