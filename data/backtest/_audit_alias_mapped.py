"""진짜 전수 오매핑 감사 (read-only).

충돌(한 칸 2+) 여부와 무관하게, '표준ID(account_id)가 있는데 그 ID가 어떤 canonical
account_ids에도 등록되지 않아 label(이름)로 매핑된 행'을 전 회사·전 행에서 전수 추출한다.
= account_id 보유 + mapping_status==ALIAS. 이것이 등록누락/오매핑의 직접 증거다.
단독 오매핑(충돌 안 나는 흡수)도 잡힌다. LLM 없음.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from src.normalize.config import load_canonical_accounts, normalize_label
from src.normalize.mapper import ALIAS, EXACT, OTHER_CANONICAL, UNMAPPED, AccountMapper
from src.normalize.pipeline import _apply_statement_guard
from src.normalize.schema import validate_raw_frame

BASE = Path("data/companies")
CONFIG = Path("config/canonical_accounts.yaml")
OUT = Path("data/backtest/_audit_alias_mapped.json")
BLANK = {"", "-표준계정코드 미사용-", "nan", "NaN"}


def is_blank(aid: object) -> bool:
    return str(aid or "").strip() in BLANK


def to_abs(x: object) -> float:
    try:
        a = abs(float(x))  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return 0.0
    return 0.0 if a != a else a


def build(path: Path, fs: str, maps: tuple[dict, dict, dict, dict]) -> pd.DataFrame:
    """벡터 매핑(운영 mapper와 동일 dict·우선순위: account_id 1순위, alias 2순위)."""
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
            "sj_div": frame["sj_div"],
            "canonical": canon.fillna(OTHER_CANONICAL),
            "canonical_statement": stmt.fillna(""),
            "account_id": frame["account_id"],
            "label": frame["account_nm"],
            "amount": frame["thstrm_amount"],
            "mapping_status": status,
        }
    )
    return _apply_statement_guard(out)


def main() -> None:
    mapper = AccountMapper(load_canonical_accounts(CONFIG))
    maps = (
        {k: v.name for k, v in mapper._by_id.items()},
        {k: v.statement for k, v in mapper._by_id.items()},
        {k: v.name for k, v in mapper._by_alias.items()},
        {k: v.statement for k, v in mapper._by_alias.items()},
    )
    # (account_id, canonical) -> {n, amax, labels:set}
    agg: dict[tuple, dict] = defaultdict(lambda: {"n": 0, "amax": 0.0, "labels": set()})
    companies = 0
    rows_total = 0
    mapped_rows = 0
    alias_id_rows = 0  # account_id 보유 + ALIAS (오매핑 후보)
    blank_alias_rows = 0  # account_id 공백 + ALIAS (표준ID 없어 불가피)

    collected = []
    corp_dirs = sorted(d for d in BASE.iterdir() if d.is_dir() and d.name.isdigit())
    for cdir in corp_dirs:
        companies += 1
        for ydir in sorted(cdir.iterdir()):
            if not (ydir.is_dir() and ydir.name.isdigit()):
                continue
            for fs in ("CFS", "OFS"):
                p = ydir / "raw" / f"finstate_all_{fs}.csv"
                if not p.exists() or p.stat().st_size <= 5:
                    continue
                try:
                    df = build(p, fs, maps)
                except Exception:
                    continue
                rows_total += len(df)
                mapped = df[df["canonical"] != OTHER_CANONICAL]
                mapped_rows += len(mapped)
                alias = mapped[mapped["mapping_status"] == ALIAS]
                if alias.empty:
                    continue
                aid = alias["account_id"].astype(str).str.strip()
                blank_mask = aid.isin(BLANK)
                blank_alias_rows += int(blank_mask.sum())
                keep = alias[~blank_mask][["account_id", "canonical", "label", "amount"]]
                if not keep.empty:
                    collected.append(keep)

    big = (
        pd.concat(collected, ignore_index=True)
        if collected
        else pd.DataFrame(columns=["account_id", "canonical", "label", "amount"])
    )
    alias_id_rows = len(big)
    if not big.empty:
        big["_amt"] = pd.to_numeric(big["amount"], errors="coerce").abs().fillna(0.0)
        for (aid_v, canon_v), grp in big.groupby(["account_id", "canonical"]):
            slot = agg[(str(aid_v), str(canon_v))]
            slot["n"] = int(len(grp))
            slot["amax"] = float(grp["_amt"].max())
            slot["labels"] = sorted({str(x) for x in grp["label"].head(20).tolist()})[:5]

    out = {
        "coverage": {
            "companies": companies,
            "rows_total": rows_total,
            "mapped_rows": mapped_rows,
            "alias_with_id_rows": alias_id_rows,
            "blank_alias_rows": blank_alias_rows,
            "distinct_id_canonical": len(agg),
        },
        "items": [
            {
                "account_id": aid,
                "canonical": canon,
                "n": s["n"],
                "amax": s["amax"],
                "labels": sorted(s["labels"]),
            }
            for (aid, canon), s in sorted(agg.items(), key=lambda kv: -kv[1]["n"])
        ],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    c = out["coverage"]
    print(
        f"companies={c['companies']} rows={c['rows_total']} mapped={c['mapped_rows']} "
        f"alias_with_id={c['alias_with_id_rows']} blank_alias={c['blank_alias_rows']} "
        f"distinct(id,canon)={c['distinct_id_canonical']}"
    )
    print("\n빈도순 상위 40 (account_id가 canonical에 미등록 → 이름으로 매핑):")
    print(f"{'n':>6}  {'canonical':<18} account_id")
    for it in out["items"][:40]:
        print(f"{it['n']:>6}  {it['canonical']:<18} {it['account_id']}")
    print(f"\nJSON -> {OUT}")


if __name__ == "__main__":
    main()
