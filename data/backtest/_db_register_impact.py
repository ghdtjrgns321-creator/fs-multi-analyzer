"""D-B 측정: 등록누락 표준ID를 canonical account_ids에 등록하면 정규화 결과가 바뀌나? (read-only)

등록누락 = 같은 개념인데 account_id가 config에 미등록 → 현재 이름(alias)으로 매핑됨.
등록하면 mapping_status가 ALIAS→EXACT로 바뀐다(칸=canonical은 그대로). 위험:
 ① 이전엔 미분류였던 같은 account_id의 다른 라벨 행이 새로 그 canonical에 매핑(분류 변화).
 ② 충돌 그룹에서 _canonical_score가 올라 대표행이 바뀜.
before(현행)/after(61 id 등록) 두 매핑으로 전 파일을 운영코드(가드·_dedupe_*)로 정규화해 diff한다.
config·코드는 수정하지 않는다(메모리 내 mapper만 확장).
"""

from __future__ import annotations

import importlib.util
import json
import os
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
CONFIG = Path("config/canonical_accounts.yaml")
ALIAS_JSON = Path("data/backtest/_audit_alias_mapped.json")
OUT = Path("data/backtest/_db_register_impact.json")

# 분류기(classify/stem) 재사용 — 등록누락 판정 동일 로직
_spec = importlib.util.spec_from_file_location(
    "_clf", "data/backtest/_audit_alias_mapped_report.py"
)
_clf = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_clf)  # type: ignore[union-attr]


def to_abs(x: object) -> float:
    try:
        a = abs(float(x))  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return 0.0
    return 0.0 if a != a else a


def map_cols(aid: pd.Series, lbl: pd.Series, maps: tuple[dict, dict, dict, dict]):
    id2n, id2s, al2n, al2s = maps
    canon_id = aid.map(id2n)
    canon_al = lbl.map(al2n)
    canon = canon_id.where(canon_id.notna(), canon_al).fillna(OTHER_CANONICAL)
    stmt = aid.map(id2s).where(canon_id.notna(), lbl.map(al2s)).fillna("")
    status = np.where(canon_id.notna(), EXACT, np.where(canon_al.notna(), ALIAS, UNMAPPED))
    return canon, stmt, status


def build(path: Path, fs: str, maps: tuple[dict, dict, dict, dict]) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=str)
    frame = validate_raw_frame(raw, fs)
    aid = frame["account_id"].astype(str)
    lbl = frame["account_nm"].astype(str).map(normalize_label)
    canon, stmt, status = map_cols(aid, lbl, maps)
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


def kept_map(guarded: pd.DataFrame) -> dict[tuple, tuple]:
    """운영 dedup 후 (canonical,year,fs_div)별 대표 (account_id, amount)."""
    dd = _dedupe_canonical_rows(_dedupe_statement_rows(guarded))
    m = dd[dd["canonical"] != OTHER_CANONICAL]
    out = {}
    for r in m.itertuples(index=False):
        out[(str(r.canonical), str(r.year), str(r.fs_div))] = (
            str(r.account_id),
            None if pd.isna(r.amount) else round(float(r.amount), 2),
        )
    return out


def main() -> None:
    accounts = load_canonical_accounts(CONFIG)
    mapper = AccountMapper(accounts)
    reg_by_name: dict[str, set] = {}
    stmt_by_name: dict[str, str] = {}
    for ac in accounts:
        reg_by_name.setdefault(ac.name, set()).update(ac.account_ids)
        stmt_by_name[ac.name] = ac.statement

    # 등록누락 61쌍 산출 (분류기 동일 판정)
    items = json.loads(ALIAS_JSON.read_text(encoding="utf-8"))["items"]
    register: dict[str, str] = {}  # account_id -> canonical name
    for it in items:
        canon = it["canonical"]
        verdict, _ = _clf.classify(it["account_id"], reg_by_name.get(canon, set()))
        if verdict == "등록누락":
            register[it["account_id"]] = canon

    before_maps = (
        {k: v.name for k, v in mapper._by_id.items()},
        {k: v.statement for k, v in mapper._by_id.items()},
        {k: v.name for k, v in mapper._by_alias.items()},
        {k: v.statement for k, v in mapper._by_alias.items()},
    )
    id2n_a = dict(before_maps[0])
    id2s_a = dict(before_maps[1])
    for aid, canon in register.items():
        id2n_a[aid] = canon
        id2s_a[aid] = stmt_by_name.get(canon, "")
    after_maps = (id2n_a, id2s_a, before_maps[2], before_maps[3])

    companies = files = 0
    new_mapped_rows = 0  # 행단위: before OTHER → after canonical (가드 후)
    groups_same = groups_changed = groups_new = 0
    changed_examples: list = []
    new_examples: list = []
    canon_rowdelta: Counter = Counter()  # canonical -> after행 - before행 (kept group 기준)

    corp_dirs = sorted(d for d in BASE.iterdir() if d.is_dir() and d.name.isdigit())
    lim = int(os.environ.get("LIMIT", "0"))
    if lim:
        corp_dirs = corp_dirs[:lim]
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
                    gb = build(p, fs, before_maps)
                    ga = build(p, fs, after_maps)
                except Exception:
                    continue
                files += 1
                # 행단위 새 매핑 (같은 frame 순서)
                new_mapped_rows += int(
                    (
                        (gb["canonical"].values == OTHER_CANONICAL)
                        & (ga["canonical"].values != OTHER_CANONICAL)
                    ).sum()
                )
                kb = kept_map(gb)
                ka = kept_map(ga)
                cc = cdir.name
                for key in set(kb) | set(ka):
                    if key not in kb:
                        groups_new += 1
                        canon_rowdelta[key[0]] += 1
                        if len(new_examples) < 40:
                            new_examples.append({"corp": cc, "key": key, "after": ka[key]})
                    elif key not in ka:
                        # 사라짐(이론상 없음)
                        groups_changed += 1
                        if len(changed_examples) < 500:
                            changed_examples.append(
                                {"corp": cc, "key": key, "before": kb[key], "after": None}
                            )
                    elif kb[key] != ka[key]:
                        groups_changed += 1
                        if len(changed_examples) < 500:
                            changed_examples.append(
                                {"corp": cc, "key": key, "before": kb[key], "after": ka[key]}
                            )
                    else:
                        groups_same += 1

    out = {
        "coverage": {"companies": companies, "files": files},
        "register_pairs": [{"account_id": a, "canonical": c} for a, c in sorted(register.items())],
        "register_count": len(register),
        "impact": {
            "new_mapped_rows": new_mapped_rows,
            "groups_same": groups_same,
            "groups_changed": groups_changed,
            "groups_new": groups_new,
        },
        "changed_examples": changed_examples,
        "new_examples": new_examples,
        "canon_new_group_delta": dict(canon_rowdelta.most_common()),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    im = out["impact"]
    print(f"companies={companies} files={files} register={len(register)}쌍")
    print(f"새매핑 행(미분류→canonical)={im['new_mapped_rows']:,}")
    print(
        f"대표행 동일={im['groups_same']:,}  대표행변화={im['groups_changed']:,}  신규그룹={im['groups_new']:,}"
    )
    if changed_examples:
        print("\n[대표행 변화 예시 — 위험]")
        for e in changed_examples[:15]:
            print(f"  {e['key']}  before={e['before']} → after={e['after']}")
    else:
        print("\n대표행 변화 0건 (등록은 기존 분류를 안 바꿈 = 안전).")
    print(f"\nJSON -> {OUT}")


if __name__ == "__main__":
    main()
