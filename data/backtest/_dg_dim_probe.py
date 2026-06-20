"""저장된 XBRL zip을 dimension 보존해 재추출 — 흡수 concept의 '날아간 차원'이 무엇인지 직접 확인.

현 extract_note_facts는 context.qnameDims(세그먼트·차원 멤버)를 버린다. 여기선 그걸 살려
Assets/Equity의 복수값이 어떤 축(세그먼트/연결제거/구성요소)에 붙는지 라벨로 본다.
"""

from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

ZIP = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path("data/companies/00100939/2025/raw/financial_statement_xbrl.zip")
)
TARGETS = {"Assets", "Equity", "Liabilities"}

from arelle import Cntlr

tmp = tempfile.mkdtemp()
with zipfile.ZipFile(ZIP) as zf:
    zf.extractall(tmp)
entries = list(Path(tmp).glob("*.xbrl"))
print(f"zip={ZIP}  .xbrl={len(entries)}개")
cntlr = Cntlr.Cntlr(logFileName="logToBuffer")
model = cntlr.modelManager.load(str(entries[0]))

for concept in TARGETS:
    facts = [
        f
        for f in model.facts
        if f.concept is not None
        and f.concept.qname is not None
        and f.concept.qname.localName == concept
    ]
    print(f"\n===== {concept}: {len(facts)} facts =====")
    seen = []
    for f in facts:
        ctx = f.context
        period = ctx.endDatetime.date().isoformat() if ctx is not None and ctx.endDatetime else ""
        # 차원: qnameDims = {dimQname: dimValue(member)}
        dims = []
        if ctx is not None:
            for dim_qn, dim_val in (ctx.qnameDims or {}).items():
                axis = dim_qn.localName
                try:
                    member = (
                        dim_val.memberQname.localName
                        if dim_val.isExplicit
                        else str(
                            dim_val.typedMember.text if dim_val.typedMember is not None else ""
                        )
                    )
                except Exception:
                    member = str(dim_val)
                dims.append(f"{axis}={member}")
        val = (f.value or "")[:18]
        seen.append((period, tuple(dims), val))
    # 최근 기간 1개만 추려 차원 분포 보기
    if not seen:
        continue
    last_period = sorted({p for p, _, _ in seen})[-1]
    rows = [s for s in seen if s[0] == last_period]
    print(f"  기간 {last_period}: {len(rows)} facts")
    for period, dims, val in rows[:14]:
        dimstr = " | ".join(dims) if dims else "(차원없음=전체/연결별도)"
        print(f"     {val:>18}  ←  {dimstr}")
cntlr.modelManager.close()
