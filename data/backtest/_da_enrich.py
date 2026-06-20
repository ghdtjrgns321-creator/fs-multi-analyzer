"""D-A 군집화 보강: account_id별 고유 회사수·금액 중앙값 전수 측정 (read-only).

_audit_unmapped.json의 classify_candidates(표준ID 보유·canonical 없는 미분류)에는 행수(n)와
최대금액(amax)만 있다. 군집 커버리지 판정에는 "고유 회사수"와 "중앙값"(amax는 원천 이상치로
신뢰 불가)이 필요하므로 운영 매핑 파이프라인을 그대로 재호출해 전수 재스캔한다.

_audit_unmapped.py와 동일 경로:
  build(=벡터 매핑 + _apply_statement_guard) → _dedupe_statement_rows → canonical==OTHER 잔여 중
  표준ID 보유(has_id) plain 행을 account_id로 집계. 수정 없음(read-only).
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from src.normalize.config import load_canonical_accounts, normalize_label
from src.normalize.mapper import ALIAS, EXACT, OTHER_CANONICAL, UNMAPPED, AccountMapper
from src.normalize.pipeline import _apply_statement_guard, _dedupe_statement_rows
from src.normalize.schema import validate_raw_frame

BASE = Path("data/companies")
CONFIG = Path("config/canonical_accounts.yaml")
OUT = Path("data/backtest/_da_enrich.json")
BLANK = {"", "-표준계정코드 미사용-", "nan", "NaN"}


def build(path: Path, fs: str, maps: tuple[dict, dict, dict, dict]) -> pd.DataFrame:
    id2name, id2stmt, al2name, al2stmt = maps
    raw = pd.read_csv(path, dtype=str)
    frame = validate_raw_frame(raw, fs)
    aid = frame["account_id"].astype(str)
    lbl = frame["account_nm"].astype(str).map(normalize_label)
    canon_id = aid.map(id2name)
    canon_al = lbl.map(al2name)
    canon = canon_id.where(canon_id.notna(), canon_al)
    stmt = aid.map(id2stmt).where(canon_id.notna(), lbl.map(al2stmt))
    status = np.where(canon_id.notna(), EXACT, np.where(canon_al.notna(), ALIAS, UNMAPPED))
    out = pd.DataFrame(
        {
            "year": frame["bsns_year"],
            "fs_div": frame["fs_div"],
            "sj_div": frame["sj_div"],
            "canonical": canon.fillna(OTHER_CANONICAL),
            "canonical_statement": stmt.fillna(""),
            "account_id": frame["account_id"],
            "label": frame["account_nm"],
            "amount": pd.to_numeric(frame["thstrm_amount"], errors="coerce"),
            "mapping_status": status,
            "account_detail": frame.get("account_detail", "-"),
        }
    )
    return _apply_statement_guard(out)


def is_blank_id(aid: object) -> bool:
    return str(aid or "").strip() in BLANK


def main() -> None:
    mapper = AccountMapper(load_canonical_accounts(CONFIG))
    maps = (
        {k: v.name for k, v in mapper._by_id.items()},
        {k: v.statement for k, v in mapper._by_id.items()},
        {k: v.name for k, v in mapper._by_alias.items()},
        {k: v.statement for k, v in mapper._by_alias.items()},
    )

    # account_id -> {corps: set, amounts: list[abs], n: int}
    agg: dict[str, dict] = defaultdict(lambda: {"corps": set(), "amounts": [], "n": 0})

    corp_dirs = sorted(d for d in BASE.iterdir() if d.is_dir() and d.name.isdigit())
    _lim = int(os.environ.get("LIMIT", "0"))
    if _lim:
        corp_dirs = corp_dirs[:_lim]
    files = 0
    for cdir in corp_dirs:
        corp = cdir.name
        for ydir in sorted(cdir.iterdir()):
            if not (ydir.is_dir() and ydir.name.isdigit()):
                continue
            for fs in ("CFS", "OFS"):
                p = ydir / "raw" / f"finstate_all_{fs}.csv"
                if not p.exists() or p.stat().st_size <= 5:
                    continue
                try:
                    guarded = build(p, fs, maps)
                except Exception:
                    continue
                files += 1
                deduped = _dedupe_statement_rows(guarded)
                un = deduped[deduped["canonical"] == OTHER_CANONICAL]
                if un.empty:
                    continue
                for r in un.itertuples(index=False):
                    if is_blank_id(r.account_id):
                        continue
                    s = agg[str(r.account_id)]
                    s["n"] += 1
                    s["corps"].add(corp)
                    try:
                        a = abs(float(r.amount))
                        if a == a:  # not NaN
                            s["amounts"].append(a)
                    except (ValueError, TypeError):
                        pass

    out = {}
    for aid, s in agg.items():
        amts = sorted(s["amounts"])
        med = float(np.median(amts)) if amts else 0.0
        out[aid] = {
            "n": s["n"],
            "n_companies": len(s["corps"]),
            "median_abs": med,
            "amt_count": len(amts),
        }
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"files={files} account_ids={len(out)}")
    print(f"JSON -> {OUT}")


if __name__ == "__main__":
    main()
