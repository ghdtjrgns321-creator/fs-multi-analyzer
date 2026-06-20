"""D-B 적용 검증: 실제 OLD(수정 전) vs NEW(수정 후) 정규화 전수 비교 (read-only).

수정 = (1)mapper ifrs_≡ifrs-full_ 접두사통일 (2)config 5개 등록.
시뮬레이션-61이 아니라 '실제 적용된 코드+config'의 진짜 footprint·핵심계정 영향을 측정한다.
 - OLD: git HEAD config + 접두사통일 없는 매핑(수정 전 동작 재현)
 - NEW: 현재 config + 현재 mapper(접두사통일 포함)
운영 가드·_dedupe_*는 동일 호출. 핵심 분식계정(매출채권·재고·매입채무·계약자산·당기순이익·매출·
종속/관계투자) 대표행 변화는 별도 플래그.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from src.normalize.config import load_canonical_accounts, normalize_label
from src.normalize.mapper import ALIAS, EXACT, OTHER_CANONICAL, UNMAPPED, AccountMapper
from src.normalize.pipeline import (
    _apply_statement_guard,
    _dedupe_canonical_rows,
    _dedupe_statement_rows,
)
from src.normalize.schema import validate_raw_frame

BASE = Path("data/companies")
NEW_CONFIG = Path("config/canonical_accounts.yaml")
OLD_CONFIG = Path("data/backtest/_old_config.yaml")
OUT = Path("data/backtest/_db_apply_verify.json")
CORE = {
    "매출채권",
    "재고자산",
    "매입채무",
    "계약자산",
    "계약부채",
    "당기순이익",
    "매출",
    "종속기업투자",
    "관계기업투자",
    "매출채권및기타유동채권",
    "매입채무및기타유동채무",
    "미청구공사",
}


def maps_no_shadow(path: Path) -> tuple[dict, dict, dict, dict]:
    """수정 전 동작: account_id 등록분만(접두사 shadow 없음)."""
    accts = load_canonical_accounts(path)
    return (
        {aid: a.name for a in accts for aid in a.account_ids},
        {aid: a.statement for a in accts for aid in a.account_ids},
        {normalize_label(al): a.name for a in accts for al in a.aliases},
        {normalize_label(al): a.statement for a in accts for al in a.aliases},
    )


def maps_from_mapper(mapper: AccountMapper) -> tuple[dict, dict, dict, dict]:
    """수정 후: 현재 mapper(접두사 shadow 포함)."""
    return (
        {k: v.name for k, v in mapper._by_id.items()},
        {k: v.statement for k, v in mapper._by_id.items()},
        {k: v.name for k, v in mapper._by_alias.items()},
        {k: v.statement for k, v in mapper._by_alias.items()},
    )


def build(path: Path, fs: str, maps: tuple[dict, dict, dict, dict]) -> pd.DataFrame:
    id2n, id2s, al2n, al2s = maps
    frame = validate_raw_frame(pd.read_csv(path, dtype=str), fs)
    aid = frame["account_id"].astype(str)
    lbl = frame["account_nm"].astype(str).map(normalize_label)
    canon_id = aid.map(id2n)
    canon_al = lbl.map(al2n)
    canon = canon_id.where(canon_id.notna(), canon_al).fillna(OTHER_CANONICAL)
    stmt = aid.map(id2s).where(canon_id.notna(), lbl.map(al2s)).fillna("")
    status = np.where(canon_id.notna(), EXACT, np.where(canon_al.notna(), ALIAS, UNMAPPED))
    out = pd.DataFrame(
        {
            "year": frame["bsns_year"],
            "fs_div": frame["fs_div"],
            "sj_div": frame["sj_div"],
            "canonical": canon,
            "canonical_statement": stmt,
            "account_id": frame["account_id"],
            "label": frame["account_nm"],
            "amount": pd.to_numeric(frame["thstrm_amount"], errors="coerce"),
            "mapping_status": status,
            "account_detail": frame.get("account_detail", "-"),
        }
    )
    return _apply_statement_guard(out)


def kept_map(g: pd.DataFrame) -> dict[tuple, tuple]:
    dd = _dedupe_canonical_rows(_dedupe_statement_rows(g))
    m = dd[dd["canonical"] != OTHER_CANONICAL]
    return {
        (str(r.canonical), str(r.year), str(r.fs_div)): (
            str(r.account_id),
            None if pd.isna(r.amount) else round(float(r.amount), 2),
        )
        for r in m.itertuples(index=False)
    }


def main() -> None:
    old = maps_no_shadow(OLD_CONFIG)
    new = maps_from_mapper(AccountMapper(load_canonical_accounts(NEW_CONFIG)))

    files = 0
    new_mapped_rows = 0
    g_same = g_changed = g_new = 0
    core_changed: list = []
    changed_canon: Counter = Counter()
    changed_ex: list = []

    for cdir in sorted(d for d in BASE.iterdir() if d.is_dir() and d.name.isdigit()):
        for ydir in sorted(cdir.iterdir()):
            if not (ydir.is_dir() and ydir.name.isdigit()):
                continue
            for fs in ("CFS", "OFS"):
                p = ydir / "raw" / f"finstate_all_{fs}.csv"
                if not p.exists() or p.stat().st_size <= 5:
                    continue
                try:
                    go = build(p, fs, old)
                    gn = build(p, fs, new)
                except Exception:
                    continue
                files += 1
                new_mapped_rows += int(
                    (
                        (go["canonical"].values == OTHER_CANONICAL)
                        & (gn["canonical"].values != OTHER_CANONICAL)
                    ).sum()
                )
                ko, kn = kept_map(go), kept_map(gn)
                for key in set(ko) | set(kn):
                    if key not in ko:
                        g_new += 1
                    elif key not in kn or ko[key] != kn[key]:
                        g_changed += 1
                        changed_canon[key[0]] += 1
                        rec = {
                            "corp": cdir.name,
                            "key": key,
                            "old": ko.get(key),
                            "new": kn.get(key),
                        }
                        if key[0] in CORE:
                            core_changed.append(rec)
                        if len(changed_ex) < 80:
                            changed_ex.append(rec)
                    else:
                        g_same += 1

    out = {
        "files": files,
        "new_mapped_rows": new_mapped_rows,
        "groups_same": g_same,
        "groups_changed": g_changed,
        "groups_new": g_new,
        "changed_canonical": dict(changed_canon.most_common()),
        "core_changed_count": len(core_changed),
        "core_changed": core_changed,
        "changed_examples": changed_ex,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"files={files} 새분류행={new_mapped_rows:,} 대표동일={g_same:,} 대표변화={g_changed:,} 신규그룹={g_new:,}"
    )
    print(f"\n핵심 분식계정 대표변화: {len(core_changed)}건")
    for e in core_changed[:30]:
        print(
            f"  ⚠ {e['corp']} {e['key'][0]} {e['key'][1]} {e['key'][2]}  {e['old']} -> {e['new']}"
        )
    print(f"\n변화 canonical 분포: {dict(changed_canon.most_common(15))}")
    print(f"JSON -> {OUT}")


if __name__ == "__main__":
    main()
