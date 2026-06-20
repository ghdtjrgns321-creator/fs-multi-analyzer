"""미분류 잔여(기타 중요 계정) 전수 측정 (read-only).

Phase1이 canonical로 분류하지 못하고 "기타 중요 계정"으로 넘기는 잔여 행을 전 회사·전 연도·
CFS+OFS·전 sj_div에서 전수로 본다. 목적: 무엇이 아직 분류 안 되는지(분류 천장)·더 건질 수
있는 표준계정이 무엇인지 파악(수정은 다음 단계).

운영코드: statement 가드(_apply_statement_guard)·_dedupe_statement_rows를 실제 호출.
매핑 dict는 운영 AccountMapper와 동일(우선순위 account_id→alias) 벡터화.

미분류 분해:
  (a) 표준ID 보유 + 비차원(account_detail '-') = 분류후보(아직 canonical 없는 표준계정)
  (b) 차원행(account_detail에 [member]/[구성요소]) = 거시구조(분해축)
  (c) 공백 account_id = 회사 확장계정(표준ID 없음)
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from src.normalize.config import load_canonical_accounts, normalize_label
from src.normalize.mapper import ALIAS, EXACT, OTHER_CANONICAL, UNMAPPED, AccountMapper
from src.normalize.pipeline import _apply_statement_guard, _dedupe_statement_rows
from src.normalize.schema import validate_raw_frame

BASE = Path("data/companies")
CONFIG = Path("config/canonical_accounts.yaml")
OUT = Path("data/backtest/_audit_unmapped.json")
BLANK = {"", "-표준계정코드 미사용-", "nan", "NaN"}


def build(path: Path, fs: str, maps: tuple[dict, dict, dict, dict]) -> pd.DataFrame:
    """운영 매핑 dict로 벡터 매핑 + 가드. _dedupe_statement_rows 입력 컬럼 구비."""
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


def detail_kind(detail: str) -> str:
    d = str(detail or "").strip()
    if d in ("-", ""):
        return "plain"
    if "[member]" in d:
        return "member"
    if "[구성요소]" in d:
        return "구성요소"
    return "기타detail"


def is_blank_id(aid: object) -> bool:
    return str(aid or "").strip() in BLANK


def to_abs(x: object) -> float:
    try:
        a = abs(float(x))  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return 0.0
    return 0.0 if a != a else a


def main() -> None:
    mapper = AccountMapper(load_canonical_accounts(CONFIG))
    maps = (
        {k: v.name for k, v in mapper._by_id.items()},
        {k: v.statement for k, v in mapper._by_id.items()},
        {k: v.name for k, v in mapper._by_alias.items()},
        {k: v.statement for k, v in mapper._by_alias.items()},
    )

    companies = files = 0
    years: set = set()
    rows_total = 0  # _dedupe_statement_rows 후 전체
    mapped_total = 0  # canonical != 기타
    raw_rows = 0  # dedup 전(가드 후)
    # 미분류 분해 카운트 (post statement-dedup)
    unmapped_total = 0
    cat_rows: Counter = Counter()  # (detail_kind, has_id) -> rows
    sj_unmapped: Counter = Counter()  # sj_div -> unmapped rows
    sj_total: Counter = Counter()  # sj_div -> total rows
    # 분류후보: 표준ID 보유 + plain 미분류 → account_id 집계
    cand: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "amax": 0.0, "labels": Counter(), "sj": Counter()}
    )
    # 공백ID 확장계정: label 집계 (plain만)
    ext: dict[str, dict] = defaultdict(lambda: {"n": 0, "amax": 0.0, "sj": Counter()})
    # dedup 붕괴(차원 손실): raw 차원행수 vs 잔존
    dim_raw = 0
    dim_kept = 0

    corp_dirs = sorted(d for d in BASE.iterdir() if d.is_dir() and d.name.isdigit())
    _lim = int(os.environ.get("LIMIT", "0"))
    if _lim:
        corp_dirs = corp_dirs[:_lim]
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
                    guarded = build(p, fs, maps)
                except Exception:
                    continue
                files += 1
                years.add((cdir.name, ydir.name))
                raw_rows += len(guarded)
                # 차원행(raw) 카운트
                dk_raw = guarded["account_detail"].map(detail_kind)
                dim_raw += int((dk_raw != "plain").sum())

                deduped = _dedupe_statement_rows(guarded)  # 운영코드
                rows_total += len(deduped)
                # deduped는 account_detail 컬럼 제거됨 → 차원 잔존은 따로 못 봄.
                # 잔존 차원행: deduped에는 account_detail이 없으니, dedup 전후 행수차로 붕괴량 측정.
                mapped = deduped[deduped["canonical"] != OTHER_CANONICAL]
                mapped_total += len(mapped)
                un = deduped[deduped["canonical"] == OTHER_CANONICAL]
                unmapped_total += len(un)

                for sj, c in Counter(deduped["sj_div"]).items():
                    sj_total[sj] += c
                for sj, c in Counter(un["sj_div"]).items():
                    sj_unmapped[sj] += c

                if un.empty:
                    continue
                aid = un["account_id"].astype(str)
                blank = aid.map(is_blank_id)
                for r in un.itertuples(index=False):
                    has_id = not is_blank_id(r.account_id)
                    cat_rows[("has_id" if has_id else "blank_id")] += 1
                    a = to_abs(r.amount)
                    if has_id:
                        s = cand[str(r.account_id)]
                        s["n"] += 1
                        s["amax"] = max(s["amax"], a)
                        s["labels"][str(r.label)] += 1
                        s["sj"][str(r.sj_div)] += 1
                    else:
                        e = ext[normalize_label(r.label)]
                        e["n"] += 1
                        e["amax"] = max(e["amax"], a)
                        e["sj"][str(r.sj_div)] += 1

    # dedup 붕괴량(전체 기준): raw_rows - rows_total = 통째 제거된 중복/차원행
    collapsed = raw_rows - rows_total

    out = {
        "coverage": {
            "companies": companies,
            "files": files,
            "company_years": len(years),
            "raw_rows_after_guard": raw_rows,
            "rows_after_stmt_dedup": rows_total,
            "collapsed_by_stmt_dedup": collapsed,
            "dim_rows_raw": dim_raw,
            "mapped_rows": mapped_total,
            "unmapped_rows": unmapped_total,
            "unmapped_pct": round(100 * unmapped_total / max(rows_total, 1), 1),
        },
        "unmapped_breakdown_rows": dict(cat_rows),
        "sj_distribution": {
            sj: {
                "total": sj_total[sj],
                "unmapped": sj_unmapped[sj],
                "unmapped_pct": round(100 * sj_unmapped[sj] / max(sj_total[sj], 1), 1),
            }
            for sj in sorted(sj_total)
        },
        "classify_candidates": [  # 표준ID 보유인데 canonical 없음 = 더 분류 가능
            {
                "account_id": aid,
                "n": s["n"],
                "amax": s["amax"],
                "labels": [w for w, _ in s["labels"].most_common(3)],
                "sj": dict(s["sj"]),
            }
            for aid, s in sorted(cand.items(), key=lambda kv: -kv[1]["n"])
        ],
        "extension_accounts": [  # 공백ID 확장계정 (표준ID 없음)
            {"label": lb, "n": s["n"], "amax": s["amax"], "sj": dict(s["sj"])}
            for lb, s in sorted(ext.items(), key=lambda kv: -kv[1]["n"])[:200]
        ],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    c = out["coverage"]
    print(
        f"companies={c['companies']} files={c['files']} rows(dedup)={c['rows_after_stmt_dedup']:,} "
        f"mapped={c['mapped_rows']:,} unmapped={c['unmapped_rows']:,}({c['unmapped_pct']}%)"
    )
    print(
        f"raw(guard)={c['raw_rows_after_guard']:,} → stmt_dedup 붕괴={c['collapsed_by_stmt_dedup']:,} "
        f"(차원행 raw={c['dim_rows_raw']:,})"
    )
    print(f"미분류 분해: {out['unmapped_breakdown_rows']}")
    print("\nsj_div별 미분류:")
    for sj, v in out["sj_distribution"].items():
        print(f"  {sj}: {v['unmapped']:,}/{v['total']:,} ({v['unmapped_pct']}%)")
    print(f"\n분류후보(표준ID 보유·미매핑) 상위 30 / 총 {len(out['classify_candidates'])}종:")
    print(f"{'n':>6} {'amax(억)':>10}  account_id  | label")
    for it in out["classify_candidates"][:30]:
        print(
            f"{it['n']:>6} {it['amax'] / 1e8:>10,.0f}  {it['account_id']:<46} | {it['labels'][0] if it['labels'] else ''}"
        )
    print(f"\nJSON -> {OUT}")


if __name__ == "__main__":
    main()
