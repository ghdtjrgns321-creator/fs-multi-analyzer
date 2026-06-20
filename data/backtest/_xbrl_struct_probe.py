"""XBRL→CSV 컨버터 설계용 구조 탐색(읽기전용). 두산 2017 원본 zip.

확인: (1) presentation ELR role→sj_div 판정 가능한가 (2) 연결/별도 축 멤버 (3) context 기간
종류(당기/전기/전전기) (4) concept localName이 raw account_id와 어떻게 대응되나.
재현: PYTHONPATH=. uv run python data/backtest/_xbrl_struct_probe.py
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

from arelle import Cntlr, XbrlConst

ZIP = "data/companies/00159616/2017/raw/financial_statement_xbrl.zip"

tmp = tempfile.mkdtemp()
with zipfile.ZipFile(ZIP) as zf:
    zf.extractall(tmp)
ent = list(Path(tmp).glob("*.xbrl"))
print(f"인스턴스: {[p.name for p in ent]}")

c = Cntlr.Cntlr(logFileName="logToBuffer")
m = c.modelManager.load(str(ent[0]))

# 1) presentation ELR (extended link role) → 어떤 statement인가
print("\n=== presentation ELR (role → linkrole 정의) ===")
rel_set = m.relationshipSet(XbrlConst.parentChild)
for elr in rel_set.linkRoleUris:
    role_obj = m.roleTypes.get(elr)
    definition = ""
    if role_obj:
        definition = (role_obj[0].definition or "") if role_obj else ""
    # 그 ELR 하위 concept 수
    sub = m.relationshipSet(XbrlConst.parentChild, elr)
    n = len(sub.modelRelationships)
    print(f"  {elr.split('/')[-1]:40} n={n:4} | {definition[:50]}")

# 2) 연결/별도 축 멤버
print("\n=== ConsolidatedAndSeparate 축 멤버 ===")
axes = set()
members = set()
for f in m.facts[:5000]:
    ctx = f.context
    if ctx is None:
        continue
    for d, dv in (ctx.qnameDims or {}).items():
        axes.add(d.localName)
        if "Consolidated" in d.localName or "Separate" in d.localName:
            try:
                members.add(dv.memberQname.localName if dv.isExplicit else str(dv))
            except Exception:
                pass
print(f"  전체 축: {sorted(axes)}")
print(f"  연결별도 멤버: {sorted(members)}")

# 3) context 기간 종류
print("\n=== context 기간(상위 8개 endDate) ===")
ends = {}
for f in m.facts:
    ctx = f.context
    if ctx is None:
        continue
    e = ctx.endDatetime
    if e is not None:
        ends[str(e)[:10]] = ends.get(str(e)[:10], 0) + 1
for e, cnt in sorted(ends.items(), reverse=True)[:8]:
    print(f"  {e}: {cnt} facts")

# 4) 샘플 concept → localName + label
print("\n=== 샘플 concept(Assets·ProfitLoss·CurrentAssets) localName ===")
for f in m.facts:
    if f.concept is None or f.concept.qname is None:
        continue
    ln = f.concept.qname.localName
    if ln in ("Assets", "ProfitLoss", "CurrentAssets"):
        ctx = f.context
        dims = "|".join(d.localName for d in (ctx.qnameDims or {})) if ctx else ""
        print(
            f"  prefix={f.concept.qname.prefix} ln={ln} val={f.value[:18] if f.value else ''} dims={dims}"
        )
        break

c.modelManager.close()
