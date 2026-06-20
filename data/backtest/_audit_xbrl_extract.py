"""원본 vs 정정 XBRL 핵심 수치 대조 — 읽기전용.

fnlttXbrl.xml(rcept 기반)로 받은 XBRL instance에서 연결 기준
자산총계(Assets)·매출(Revenue)·당기순이익(ProfitLoss)을 추출해
원본 보고서와 정정 보고서의 수치를 직접 비교한다.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import OpenDartReader

from config.settings import settings

OUT = Path("data/backtest")
dart = OpenDartReader(settings.dart_api_key)

XBRLI = "{http://www.xbrl.org/2003/instance}"
XBRLDI = "{http://xbrl.org/2006/xbrldi}"
IFRS = "http://xbrl.iasb.org/taxonomy/2010-04-30/ifrs"

# (이름, corp_code, FY, 원본 rcept, 정정(최종) rcept)
CASES = [
    ("두산에너빌리티", "00159616", 2017, "20180330001846", "20240327001228"),
    ("셀트리온", "00413046", 2017, "20180402004060", "20220512000845"),
    ("아스트", "00409681", 2018, "20190320000749", "20210205000367"),
]

# 추출 대상 계정 (IFRS 표준 element local-name)
WANTED = {
    "Assets": "자산총계",
    "Revenue": "매출(수익)",
    "ProfitLoss": "당기순이익",
}


def download(rcept: str) -> Path:
    p = OUT / f"_xbrl_{rcept}.zip"
    if not p.exists():
        dart.finstate_xml(rcept, save_as=str(p))
    return p


def find_instance_name(zf: zipfile.ZipFile) -> str:
    for n in zf.namelist():
        if n.endswith(".xbrl"):
            return n
    raise RuntimeError("no .xbrl instance in zip")


def parse_contexts(root: ET.Element) -> dict:
    """context id -> {kind, start, end, instant, members(set of member localnames)}."""
    ctx = {}
    for c in root.findall(f"{XBRLI}context"):
        cid = c.get("id")
        period = c.find(f"{XBRLI}period")
        info = {"start": None, "end": None, "instant": None, "members": set()}
        if period is not None:
            inst = period.find(f"{XBRLI}instant")
            st = period.find(f"{XBRLI}startDate")
            en = period.find(f"{XBRLI}endDate")
            if inst is not None:
                info["instant"] = inst.text
            if st is not None:
                info["start"] = st.text
            if en is not None:
                info["end"] = en.text
        # segment/scenario explicitMember 차원
        for em in c.iter(f"{XBRLDI}explicitMember"):
            member = (em.text or "").split(":")[-1]
            info["members"].add(member)
        ctx[cid] = info
    return ctx


def pick_consolidated_fy(facts: list, ctx: dict, fy: int, period_kind: str):
    """연결(ConsolidatedMember)·해당 FY·추가차원 없는 fact 우선 선택.

    period_kind: 'instant'면 end==fy-12-31, 'duration'이면 start==fy-01-01 & end==fy-12-31.
    추가 차원이 없는(차원={ConsolidatedMember}) fact만 합계로 인정한다.
    """
    end = f"{fy}-12-31"
    start = f"{fy}-01-01"
    candidates = []
    for elem_ctx, value in facts:
        info = ctx.get(elem_ctx)
        if info is None:
            continue
        members = info["members"]
        if "ConsolidatedMember" not in members:
            continue
        # 연결 축 외 다른 차원이 붙은 것은 부분합/세부분류 → 제외
        extra = members - {"ConsolidatedMember"}
        if extra:
            continue
        if period_kind == "instant":
            if info["instant"] == end:
                candidates.append(value)
        else:
            if info["start"] == start and info["end"] == end:
                candidates.append(value)
    # 동일 값이 여러 개면 하나로, 다르면 모두 보고
    uniq = sorted(set(candidates))
    return uniq


def extract(rcept: str, fy: int) -> dict:
    zp = download(rcept)
    zf = zipfile.ZipFile(zp)
    inst = find_instance_name(zf)
    root = ET.fromstring(zf.read(inst))
    ctx = parse_contexts(root)

    # element localname -> list[(ctxRef, value)]
    facts: dict[str, list] = {k: [] for k in WANTED}
    for el in root.iter():
        if not el.tag.startswith("{" + IFRS + "}"):
            continue
        local = el.tag.split("}")[-1]
        if local not in WANTED:
            continue
        cref = el.get("contextRef")
        txt = (el.text or "").strip()
        if cref and txt:
            try:
                facts[local].append((cref, int(float(txt))))
            except ValueError:
                pass

    result = {}
    for local in WANTED:
        kind = "instant" if local == "Assets" else "duration"
        vals = pick_consolidated_fy(facts[local], ctx, fy, kind)
        result[local] = vals
    return result


def main():
    report = []
    for name, corp, fy, orig_rcept, corr_rcept in CASES:
        print(f"\n=== {name} ({corp}) FY{fy} ===")
        orig = extract(orig_rcept, fy)
        corr = extract(corr_rcept, fy)
        row = {
            "name": name,
            "corp": corp,
            "fy": fy,
            "orig_rcept": orig_rcept,
            "corr_rcept": corr_rcept,
            "orig": orig,
            "corr": corr,
            "diff": {},
        }
        for local, label in WANTED.items():
            o = orig[local]
            c = corr[local]
            ov = o[0] if len(o) == 1 else None
            cv = c[0] if len(c) == 1 else None
            d = (cv - ov) if (ov is not None and cv is not None) else None
            row["diff"][local] = {"label": label, "orig": o, "corr": c, "delta": d}
            print(f"  {label:12s} 원본={o}  정정={c}  Δ={d}")
        report.append(row)

    (OUT / "_audit_orig_vs_corr_values.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\nsaved -> data/backtest/_audit_orig_vs_corr_values.json")


if __name__ == "__main__":
    main()
