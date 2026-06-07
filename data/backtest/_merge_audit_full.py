"""canonical 이질계정 병합 전수 감사 (read-only).

수집된 전 회사(data/companies/*)·전 연도·CFS+OFS·전 sj_div(BS/IS/CIS/CF/SCE)를 대상으로,
한 (canonical, year, fs_div) 그룹에 서로 다른 account_id(IFRS 표준ID)가 2개 이상 모여
정규화 중복제거(`_dedupe_canonical_rows`)에서 한 계정이 통째로 버려지는(소실/오염) 케이스를
전수 식별한다.

운영코드 재현 원칙: 감사 대상 로직(_dedupe_statement_rows, _dedupe_canonical_rows, _canonical_score,
AccountMapper.map_row, parse_amount, validate_raw_frame)을 **재구현하지 않고 실제 import·호출**한다.
DataFrame 조립부만 normalize_raw_file과 동일하게 미러링한다(데이터 준비일 뿐 감사 대상 아님).

자기참조 금지(§10): 이질 여부 판정은 이 단계에서 하지 않는다. 여기서는 '어떤 account_id가 같은
canonical 칸에 모여 누가 keep/누가 drop되는지'만 운영코드로 계측해 덤프한다. 동질/이질 분류는
account_id 표준명 실질로 후속 분석(_merge_audit_classify.py)에서 한다.
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from config.settings import settings
from src.normalize.config import load_canonical_accounts
from src.normalize.mapper import OTHER_CANONICAL, AccountMapper
from src.normalize.pipeline import (
    _apply_statement_guard,
    _dedupe_canonical_rows,
    _dedupe_statement_rows,
)
from src.normalize.schema import parse_amount, validate_raw_frame

BASE = Path("data/companies")
CONFIG = Path("config/canonical_accounts.yaml")
OUT_JSON = Path("data/backtest/_merge_audit_full.json")


def build_output(path: Path, fs_div: str, mapper: AccountMapper) -> pd.DataFrame:
    """normalize_raw_file의 output 조립부를 그대로 미러링 (statement 가드 적용, dedupe 직전 상태)."""
    raw = pd.read_csv(path, dtype=str)
    frame = validate_raw_frame(raw, fs_div)
    mapped = frame.apply(mapper.map_row, axis=1)
    output = pd.DataFrame(
        {
            "corp_code": frame["corp_code"],
            "year": frame["bsns_year"],
            "fs_div": frame["fs_div"],
            "sj_div": frame["sj_div"],
            "canonical": [m.canonical for m in mapped],
            "canonical_statement": [m.statement for m in mapped],
            "account_id": frame["account_id"],
            "label": frame["account_nm"],
            "amount": [
                parse_amount(v, settings.amount_round_digits) for v in frame["thstrm_amount"]
            ],
            "mapping_status": [m.mapping_status for m in mapped],
            "account_detail": frame.get("account_detail", ""),
        }
    )
    return _apply_statement_guard(output)  # 운영코드 가드 적용 후 측정


def abs_amt(x: object) -> float:
    try:
        a = abs(float(x))  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return 0.0
    return 0.0 if a != a else a  # NaN(미기재 금액) → 0


def id_token(aid: object) -> str:
    s = str(aid or "").strip()
    return s if s and s.lower() != "nan" else "∅"  # 표준계정코드 미사용(공백)


def main() -> None:
    mapper = AccountMapper(load_canonical_accounts(CONFIG))

    # 집계 구조
    # canon -> combo(tuple sorted ids) -> {n, drop_sum, drop_max, examples[], kept:Counter}
    combos: dict[str, dict[tuple, dict]] = defaultdict(
        lambda: defaultdict(
            lambda: {"n": 0, "drop_sum": 0.0, "drop_max": 0.0, "examples": [], "kept": Counter()}
        )
    )
    canon_group_total: Counter = Counter()  # canonical별 검사한 (corp,year,fs) 그룹 총수(매핑된 것)
    canon_collision: Counter = Counter()  # canonical별 충돌(2+ distinct id) 그룹수

    companies_total = 0
    companies_with_data = 0
    years_seen: set[tuple] = set()
    files_read = 0
    files_failed: list[tuple] = []

    corp_dirs = sorted([d for d in BASE.iterdir() if d.is_dir() and d.name.isdigit()])
    limit = int(os.environ.get("LIMIT", "0"))
    if limit:
        corp_dirs = corp_dirs[:limit]
    for cdir in corp_dirs:
        companies_total += 1
        cc = cdir.name
        had_data = False
        for ydir in sorted(cdir.iterdir()):
            if not (ydir.is_dir() and ydir.name.isdigit()):
                continue
            for fs in ("CFS", "OFS"):
                p = ydir / "raw" / f"finstate_all_{fs}.csv"
                if not p.exists() or p.stat().st_size <= 5:
                    continue
                try:
                    output = build_output(p, fs, mapper)
                except Exception as exc:  # noqa: BLE001 - 감사: 실패도 수치로 보고
                    files_failed.append((cc, ydir.name, fs, type(exc).__name__))
                    continue
                files_read += 1
                had_data = True
                years_seen.add((cc, ydir.name))

                stmt = _dedupe_statement_rows(output)  # 운영코드 호출
                canon = _dedupe_canonical_rows(stmt)  # 운영코드 호출

                mapped_rows = stmt[stmt["canonical"] != OTHER_CANONICAL]
                if mapped_rows.empty:
                    continue
                # 살아남은 account_id (canonical별 1행)
                kept_by_canon = {
                    row.canonical: id_token(row.account_id)
                    for row in canon[canon["canonical"] != OTHER_CANONICAL].itertuples(index=False)
                }

                for cv, grp in mapped_rows.groupby("canonical", sort=False):
                    canon_group_total[cv] += 1
                    # id별 max abs amount, sj_div/label 예시
                    id_amt: dict[str, float] = {}
                    id_meta: dict[str, tuple] = {}
                    for r in grp.itertuples(index=False):
                        tok = id_token(r.account_id)
                        a = abs_amt(r.amount)
                        if tok not in id_amt or a > id_amt[tok]:
                            id_amt[tok] = a
                            id_meta[tok] = (str(r.sj_div), str(r.label))
                    if len(id_amt) < 2:
                        continue  # 충돌 아님(동일 id뿐)
                    canon_collision[cv] += 1
                    kept = kept_by_canon.get(cv, "")
                    drop_total = sum(v for k, v in id_amt.items() if k != kept)
                    combo = tuple(sorted(id_amt))
                    slot = combos[cv][combo]
                    slot["n"] += 1
                    slot["drop_sum"] += drop_total
                    slot["drop_max"] = max(slot["drop_max"], drop_total)
                    slot["kept"][kept] += 1
                    if len(slot["examples"]) < 4:
                        slot["examples"].append(
                            {
                                "corp": cc,
                                "year": ydir.name,
                                "fs": fs,
                                "kept": kept,
                                "ids": {
                                    k: {
                                        "amt": id_amt[k],
                                        "sj": id_meta[k][0],
                                        "label": id_meta[k][1],
                                    }
                                    for k in id_amt
                                },
                            }
                        )
        if had_data:
            companies_with_data += 1

    # 직렬화
    out = {
        "coverage": {
            "companies_total": companies_total,
            "companies_with_data": companies_with_data,
            "company_years": len(years_seen),
            "files_read": files_read,
            "files_failed": len(files_failed),
            "files_failed_detail": files_failed[:50],
        },
        "canonicals": {},
    }
    for cv in sorted(combos):
        out["canonicals"][cv] = {
            "groups_examined": canon_group_total[cv],
            "collision_groups": canon_collision[cv],
            "combos": [
                {
                    "ids": list(combo),
                    "n": slot["n"],
                    "drop_sum": slot["drop_sum"],
                    "drop_max": slot["drop_max"],
                    "kept": dict(slot["kept"]),
                    "examples": slot["examples"],
                }
                for combo, slot in sorted(combos[cv].items(), key=lambda kv: -kv[1]["n"])
            ],
        }
    # 충돌 없던 canonical도 분모 기록(빈 PASS 차단 근거)
    out["canonicals_no_collision"] = {
        cv: canon_group_total[cv] for cv in sorted(canon_group_total) if cv not in combos
    }

    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    cov = out["coverage"]
    print(
        f"companies_total={cov['companies_total']} with_data={cov['companies_with_data']} "
        f"company_years={cov['company_years']} files_read={cov['files_read']} "
        f"files_failed={cov['files_failed']}"
    )
    print(
        f"canonicals_with_collision={len(combos)} / total_canonicals_seen={len(canon_group_total)}"
    )
    print(f"\n{'canonical':<22}{'collide_grp':>11}{'examined':>9}{'drop_sum(억)':>14}")
    rows = sorted(combos, key=lambda c: -sum(s["drop_sum"] for s in combos[c].values()))
    for cv in rows:
        ds = sum(s["drop_sum"] for s in combos[cv].values())
        print(f"{cv:<22}{canon_collision[cv]:>11}{canon_group_total[cv]:>9}{ds / 1e8:>14,.0f}")
    print(f"\nJSON -> {OUT_JSON}")


if __name__ == "__main__":
    main()
