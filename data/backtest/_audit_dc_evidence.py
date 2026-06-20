"""②D-C: 오매핑 52쌍 raw 근거 수집 (read-only).

ALIAS_MISMAP_AUDIT.md '오매핑' 표(52쌍)는 _audit_alias_mapped_report.py 의 classify()가
verdict=='오매핑' 으로 분류한 (account_id, canonical) 쌍이다. 그 분류에는 회사·연도가 없다.
본 스크립트는 동일 매핑 로직으로 raw 를 재스캔해 각 쌍의 실제 회사·연도·라벨·금액 예시를
≥2건(가능하면 distinct corp 우선)으로 떠서 검증용 JSON 을 만든다. config·코드 수정 없음.

재현: PYTHONPATH=. uv run python data/backtest/_audit_dc_evidence.py
"""

from __future__ import annotations

import json
from collections import defaultdict

# 분류기와 동일 휴리스틱(자기참조 회피) — 52쌍 재현용
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd

from src.normalize.config import load_canonical_accounts, normalize_label
from src.normalize.mapper import ALIAS, EXACT, OTHER_CANONICAL, UNMAPPED, AccountMapper
from src.normalize.pipeline import _apply_statement_guard
from src.normalize.schema import validate_raw_frame

report = import_module("data.backtest._audit_alias_mapped_report")

BASE = Path("data/companies")
CONFIG = Path("config/canonical_accounts.yaml")
IN = Path("data/backtest/_audit_alias_mapped.json")
OUT = Path("data/backtest/_audit_dc_evidence.json")
BLANK = {"", "-표준계정코드 미사용-", "nan", "NaN"}
MAX_EX = 6  # 쌍당 최대 예시 (distinct corp 우선)


def is_blank(aid: object) -> bool:
    return str(aid or "").strip() in BLANK


def build(path: Path, fs: str, maps: tuple[dict, dict, dict, dict]) -> pd.DataFrame:
    """운영 mapper와 동일(account_id 1순위, alias 2순위) + statement 가드. raw 열 보존."""
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
    detail = frame["account_detail"] if "account_detail" in frame.columns else ""
    out = pd.DataFrame(
        {
            "sj_div": frame["sj_div"],
            "canonical": canon.fillna(OTHER_CANONICAL),
            "canonical_statement": stmt.fillna(""),
            "account_id": frame["account_id"],
            "label": frame["account_nm"],
            "detail": detail,
            "amount": frame["thstrm_amount"],
            "mapping_status": status,
        }
    )
    return _apply_statement_guard(out)


def mismap_pairs() -> dict[tuple[str, str], dict]:
    """report.classify()를 그대로 적용해 verdict=='오매핑'인 (account_id, canonical) 쌍 추출."""
    d = json.loads(IN.read_text(encoding="utf-8"))
    accounts = load_canonical_accounts(CONFIG)
    reg_by_name: dict[str, set[str]] = {}
    for ac in accounts:
        reg_by_name.setdefault(ac.name, set()).update(ac.account_ids)
    pairs: dict[tuple[str, str], dict] = {}
    for it in d["items"]:
        canon = it["canonical"]
        registered = reg_by_name.get(canon, set())
        verdict, reason = report.classify(it["account_id"], registered)
        if verdict == "오매핑":
            pairs[(it["account_id"], canon)] = {
                "account_id": it["account_id"],
                "canonical": canon,
                "reason": reason,
                "n": it["n"],
                "amax": it["amax"],
                "registered": sorted(report.stem(x) for x in registered),
                "examples": [],
                "corps": set(),
            }
    return pairs


def main() -> None:
    mapper = AccountMapper(load_canonical_accounts(CONFIG))
    maps = (
        {k: v.name for k, v in mapper._by_id.items()},
        {k: v.statement for k, v in mapper._by_id.items()},
        {k: v.name for k, v in mapper._by_alias.items()},
        {k: v.statement for k, v in mapper._by_alias.items()},
    )
    pairs = mismap_pairs()
    print(f"오매핑 쌍(분류기 재현): {len(pairs)}")

    found_rows = defaultdict(int)  # 쌍별 전체 발견 행수(분모 교차검증)
    corp_dirs = sorted(d for d in BASE.iterdir() if d.is_dir() and d.name.isdigit())
    for ci, cdir in enumerate(corp_dirs):
        corp = cdir.name
        for ydir in sorted(cdir.iterdir()):
            if not (ydir.is_dir() and ydir.name.isdigit()):
                continue
            year = ydir.name
            for fs in ("CFS", "OFS"):
                p = ydir / "raw" / f"finstate_all_{fs}.csv"
                if not p.exists() or p.stat().st_size <= 5:
                    continue
                try:
                    df = build(p, fs, maps)
                except Exception:
                    continue
                alias = df[df["mapping_status"] == ALIAS]
                if alias.empty:
                    continue
                for _, r in alias.iterrows():
                    aid = str(r["account_id"]).strip()
                    if is_blank(aid):
                        continue
                    key = (str(r["account_id"]), str(r["canonical"]))
                    if key not in pairs:
                        continue
                    found_rows[key] += 1
                    slot = pairs[key]
                    # 전 매칭 행 보관(단일사 쌍도 다른 연도 행 확보 → 쌍당 ≥2건 보장)
                    slot["examples"].append(
                        {
                            "corp": corp,
                            "year": year,
                            "fs": fs,
                            "sj_div": str(r["sj_div"]),
                            "label": str(r["label"]),
                            "detail": str(r.get("detail", "")),
                            "amount": str(r["amount"]),
                            "canon_stmt": str(r["canonical_statement"]),
                        }
                    )
                    slot["corps"].add(corp)
        if (ci + 1) % 300 == 0:
            print(f"  ...{ci + 1}/{len(corp_dirs)} corps scanned")

    # 예시 정리: distinct corp 우선 정렬 후 상위 6, 금액 큰 순
    def amt(e):
        try:
            return abs(float(e["amount"]))
        except (ValueError, TypeError):
            return 0.0

    items = []
    for (aid, canon), slot in pairs.items():
        exs = sorted(slot["examples"], key=amt, reverse=True)
        # ① distinct corp 대표 1건씩 우선(다회사 다양성) → ② 6 미만이면 같은 corp 다른 행 보충
        seen_corp: set[str] = set()
        rep: list[dict] = []
        for e in exs:
            if e["corp"] not in seen_corp:
                rep.append(e)
                seen_corp.add(e["corp"])
            if len(rep) >= MAX_EX:
                break
        if len(rep) < MAX_EX:
            for e in exs:
                if e in rep:
                    continue
                rep.append(e)
                if len(rep) >= MAX_EX:
                    break
        items.append(
            {
                "account_id": aid,
                "canonical": canon,
                "reason": slot["reason"],
                "n_json": slot["n"],
                "n_found": found_rows[(aid, canon)],
                "amax": slot["amax"],
                "registered": slot["registered"],
                "distinct_corps": len(slot["corps"]),
                "examples": rep,
            }
        )
    items.sort(key=lambda x: -x["n_json"])

    OUT.write_text(
        json.dumps({"pair_count": len(items), "items": items}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"\n쌍={len(items)} -> {OUT}")
    miss = [it for it in items if len(it["examples"]) < 2]
    print(f"예시 행<2 쌍(전수 자체가 1건): {len(miss)}")
    for it in miss:
        print(
            f"  {it['canonical']} <- {report.stem(it['account_id'])} (예시={len(it['examples'])}, n={it['n_found']})"
        )
    # 분모 교차검증: n_json vs n_found
    mism = [it for it in items if it["n_found"] != it["n_json"]]
    print(f"\nn_json != n_found 쌍: {len(mism)}")
    for it in mism[:20]:
        print(
            f"  {it['canonical']} <- {report.stem(it['account_id'])}: json={it['n_json']} found={it['n_found']}"
        )


if __name__ == "__main__":
    main()
