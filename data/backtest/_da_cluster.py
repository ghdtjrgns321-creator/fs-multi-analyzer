"""D-A 미분류 분류후보 전수 군집화 (read-only, config/코드 수정 없음).

대상: _audit_unmapped.json의 classify_candidates = 표준ID(ifrs-full_*/dart_*/ifrs_*) 보유 +
canonical 미매핑(OTHER) + 비차원(plain) account_id. 운영 매핑 파이프라인(build+가드+dedupe)을
그대로 재호출해 전수 재스캔하고, 다음을 측정한다.

군집 축(§요구2): 주 sj_div(데이터에서 그 account_id 행이 실제로 쌓인 sj_div의 최빈) ×
개념계열(account_id의 IFRS 표준 영문명으로 판정 — 자기참조 금지, 현 canonical 매핑 미사용).

산출(§요구3): 군집별 종수·총행수·고유회사수(합집합)·대표 account_id 5개(행수순)·예시 라벨,
account_id별 회사수·금액 중앙값(amax 이상치 신뢰 불가 → median).

플래그(§요구4): account_id가 config 등록 account_ids에 있으면 "이미 canonical 보유(타표문
반복)", 없으면 "config 미등록(신규개념 후보)".
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.normalize.config import load_canonical_accounts, normalize_label
from src.normalize.mapper import ALIAS, EXACT, OTHER_CANONICAL, UNMAPPED, AccountMapper
from src.normalize.pipeline import _apply_statement_guard, _dedupe_statement_rows
from src.normalize.schema import validate_raw_frame

BASE = Path("data/companies")
CONFIG = Path("config/canonical_accounts.yaml")
SRC_JSON = Path("data/backtest/_audit_unmapped.json")
OUT_JSON = Path("data/backtest/_da_cluster.json")
OUT_MD = Path("data/backtest/AGENDA_DA_CLUSTERS.md")
BLANK = {"", "-표준계정코드 미사용-", "nan", "NaN"}


# ── 개념계열 판정: account_id 표준 영문명만 사용 (현 매핑 미참조) ──────────────
def local_name(aid: str) -> str:
    return aid.split("_", 1)[1] if "_" in aid else aid


_FIN_KW = (
    "financialinstrument",
    "deposit",  # 단기/장기금융상품, 보증금
    "derivative",
    "securities",
    "fairvaluethrough",
    "availableforsale",
    "heldtomaturity",
    "loansandreceivable",
    "loan",  # 대여금(자산). loanspayable는 _DEBT_KW가 먼저 처리.
    "marketablesecurities",
)
_DEBT_KW = ("borrowing", "bond", "loanspayable", "debtinstrument", "debenture", "convertible")
_FIN_DIR = (  # CF 방향성 흐름 중 재무활동 성격 키워드
    "borrowing",
    "bonds",
    "dividend",
    "issueofshares",
    "issueofequity",
    "shares",
    "treasury",
    "capital",
    "leaseliabilit",
    "financelease",
    "debenture",
)


def concept_family(aid: str, dom_sj: str = "") -> str:
    """account_id 영문 표준명 → 개념계열. dom_sj는 CF 방향성 흐름 분기에만 보조 사용
    (현금이 실제 쌓인 표문 분포 — canonical 매핑 미참조, 자기참조 아님)."""
    ln = local_name(aid).lower()
    # 현금 잔액·증감·환율효과 (CF 현금 구성)
    if "cashandcashequivalents" in ln or "cashflowsfromusedin" in ln:
        return "현금잔액·증감·환율효과"
    # 현금흐름 가산·차감 조정
    if "reconcil" in ln or "noncash" in ln or re.search(r"adjustments?(for|to)", ln):
        return "현금흐름조정"
    if "investingactivit" in ln:
        return "투자활동흐름"
    if "financingactivit" in ln:
        return "재무활동흐름"
    if "operatingactivit" in ln:
        return "영업활동흐름"
    # 세금
    if "tax" in ln:
        return "세금(법인세·이연)"
    # 기타포괄손익
    if "comprehensiveincome" in ln:
        return "기타포괄손익구성"
    # 자본 구성요소
    if (
        any(
            k in ln
            for k in (
                "retainedearning",
                "treasury",
                "sharepremium",
                "sharecapital",
                "capitalsurplus",
                "noncontrollinginterest",
                "reserve",
                "issuedcapital",
                "capitaladjustment",
            )
        )
        or ln.endswith("equity")
        or "componentsofequity" in ln
    ):
        return "자본구성요소"
    # 관계·종속·공동기업 투자
    if any(k in ln for k in ("associate", "jointventure", "subsidiar", "investmentinequity")):
        return "관계·종속기업투자"
    # 금융자산 / 금융부채 (파생·증권·예치금 포함)
    if "financialassets" in ln or ("financial" in ln and "asset" in ln):
        return "기타금융자산"
    if "financialliabilit" in ln or ("financial" in ln and "liabilit" in ln):
        return "기타금융부채"
    if "derivative" in ln:
        return "기타금융자산" if "asset" in ln else "기타금융부채"
    if "receivable" in ln:
        return "기타금융자산"
    if "payable" in ln:
        return "기타금융부채"
    if any(k in ln for k in _DEBT_KW):
        return "차입·사채"
    if any(k in ln for k in _FIN_KW):
        return "기타금융자산"
    if "provision" in ln or "employeebenefit" in ln or "definedbenefit" in ln:
        return "충당부채·종업원급여"
    if any(
        k in ln
        for k in (
            # 유형자산
            "propertyplant",
            "investmentproperty",
            "building",
            "land",
            "vehicle",
            "machinery",
            "equipment",
            "furniture",
            "construction",
            "structures",
            "rightofuseasset",
            "biological",
            # 무형자산
            "intangible",
            "goodwill",
            "copyright",
            "patent",
            "trademark",
            "franchise",
            "license",
            "developmentcost",
            "software",
            "membership",
            # 재고자산
            "inventor",
            "merchandise",
            "rawmaterial",
            "finishedgoods",
            "workinprogress",
            "suppliesgross",
        )
    ):
        return "비금융자산(유형·무형·재고)"
    # CF 방향성 흐름(활동어 없는 Purchase/Proceeds/IncreaseIn/Repayments 등) — dom_sj=CF 한정
    if dom_sj == "CF" and re.match(
        r"(purchase|proceeds|acquisition|disposal|repayments?|increasein|decreasein|"
        r"payments?(to|for)|paymentof|cashoutflow|cashinflow|acquisitionof|disposalof)",
        ln,
    ):
        return "재무활동흐름" if any(k in ln for k in _FIN_DIR) else "투자활동흐름"
    # 선급금·선급비용·선수금 등 비금융 운전 항목
    if any(k in ln for k in ("prepaid", "advancepayment", "prepayment", "advancesto")):
        return "기타비금융자산"
    # 주당손익(EPS·비금액 지표)
    if "pershare" in ln:
        return "주당손익(EPS)"
    # SCE 잔여 = 자본변동 구성요소 (자본총계가 쌓인 표문)
    if dom_sj == "SCE":
        return "자본구성요소"
    # 기타 비금융 자산·부채 (OtherCurrent/Noncurrent Assets/Liabilities 등)
    if "asset" in ln:
        return "기타비금융자산"
    if "liabilit" in ln:
        return "기타비금융부채"
    # 손익 항목
    if any(
        k in ln
        for k in (
            "revenue",
            "expense",
            "gainslosses",
            "gains",
            "losses",
            "gainon",
            "losson",
            "income",
            "cost",
            "profit",
            "impairment",
            "depreciation",
            "amortis",
            "salesof",
            "interestincome",
            "salaries",
            "wages",
            "foreignexchange",
            "translation",
            "commission",
            "premium",
            "insurance",
            "fee",
            "allowance",
            "doubtful",
            "dividendincome",
            "rentalincome",
            "donation",
        )
    ):
        return "손익항목(수익·비용·손익)"
    return "기타개념"


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
    # config 등록 account_ids (플래그 대조용)
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["canonical_accounts"]
    reg_ids: dict[str, tuple[str, str]] = {}
    for name, spec in cfg.items():
        for a in spec.get("account_ids", []):
            reg_ids[a] = (name, spec.get("statement", ""))
    # 라벨 보강용 (원 산출물의 top labels)
    src = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    id2labels = {it["account_id"]: it["labels"] for it in src["classify_candidates"]}

    # account_id별 누적: n, corp set, amounts, sj Counter
    agg: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "corps": set(), "amounts": [], "sj": Counter()}
    )

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
                    s["sj"][str(r.sj_div)] += 1
                    try:
                        a = abs(float(r.amount))
                        if a == a:
                            s["amounts"].append(a)
                    except (ValueError, TypeError):
                        pass

    # account_id별 레코드 작성
    records = []
    for aid, s in agg.items():
        dom_sj = s["sj"].most_common(1)[0][0] if s["sj"] else "?"
        fam = concept_family(aid, dom_sj)
        amts = sorted(s["amounts"])
        med = float(np.median(amts)) if amts else 0.0
        registered = aid in reg_ids
        records.append(
            {
                "account_id": aid,
                "n": s["n"],
                "n_companies": len(s["corps"]),
                "median_abs": med,
                "dom_sj": dom_sj,
                "family": fam,
                "cluster": f"{dom_sj} / {fam}",
                "flag": "타표문반복(canonical보유)" if registered else "신규개념후보",
                "registered_as": reg_ids.get(aid, ("", ""))[0],
                "labels": id2labels.get(aid, []),
                "corps": s["corps"],  # 군집 합집합용 (JSON 직전 제거)
            }
        )

    # 군집 집계
    clusters: dict[str, dict] = defaultdict(
        lambda: {
            "ids": 0,
            "rows": 0,
            "corp_union": set(),
            "new": 0,
            "repeat": 0,
            "members": [],
        }
    )
    for rec in records:
        c = clusters[rec["cluster"]]
        c["ids"] += 1
        c["rows"] += rec["n"]
        c["corp_union"] |= rec["corps"]
        if rec["flag"].startswith("신규"):
            c["new"] += 1
        else:
            c["repeat"] += 1
        c["members"].append(rec)

    cluster_out = []
    for name, c in clusters.items():
        mem = sorted(c["members"], key=lambda r: -r["n"])
        top5 = [
            {
                "account_id": m["account_id"],
                "n": m["n"],
                "n_companies": m["n_companies"],
                "median_abs": m["median_abs"],
                "label": m["labels"][0] if m["labels"] else "",
                "flag": m["flag"],
            }
            for m in mem[:5]
        ]
        cluster_out.append(
            {
                "cluster": name,
                "n_account_ids": c["ids"],
                "total_rows": c["rows"],
                "n_companies_union": len(c["corp_union"]),
                "new_concept": c["new"],
                "repeat_other_stmt": c["repeat"],
                "top5": top5,
            }
        )
    cluster_out.sort(key=lambda x: (-x["total_rows"], -x["n_companies_union"]))

    # JSON 저장 (corps set 제거)
    for rec in records:
        rec.pop("corps", None)
    total_ids = len(records)
    total_new = sum(1 for r in records if r["flag"].startswith("신규"))
    total_repeat = total_ids - total_new
    summary = {
        "files_scanned": files,
        "total_account_ids": total_ids,
        "new_concept_candidates": total_new,
        "repeat_other_stmt": total_repeat,
        "cluster_count": len(cluster_out),
        "cluster_ids_sum": sum(c["n_account_ids"] for c in cluster_out),
    }
    OUT_JSON.write_text(
        json.dumps(
            {"summary": summary, "clusters": cluster_out, "accounts": records},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"JSON -> {OUT_JSON}")


if __name__ == "__main__":
    main()
