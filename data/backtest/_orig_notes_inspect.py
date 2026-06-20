"""원본 rcept 주석이 진짜 부정 당시 주석인지 직접 확인(읽기전용).

원본 rcept·정정 rcept 주석 fact를 같은 파서로 추출해, 분식 핵심계정(무형자산·특수관계자·
차입·보증)의 주석 차원 상세를 나란히 출력. 원본 주석값이 부풀린(분식) 방향이면 진짜 부정 당시 주석.
재현: PYTHONPATH=. uv run python data/backtest/_orig_notes_inspect.py <corp> <fy>
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path("data/backtest")))
from _orig_vs_corr_compare import M, corr_rcept, load_facts, original_rcept  # noqa: E402

# 분식 흔한 주석 계정 키워드(concept localName)
KEYWORDS = [
    "Intangible",
    "RelatedPart",
    "Borrowing",
    "Guarantee",
    "Commitment",
    "Receivable",
    "Inventor",
    "Provision",
    "Contingent",
]


def main() -> None:
    corp = sys.argv[1] if len(sys.argv) > 1 else "00413046"
    fy = int(sys.argv[2]) if len(sys.argv) > 2 else 2016
    ro = original_rcept(corp, fy)
    rc = corr_rcept(corp, fy)
    print(f"=== {corp} FY{fy} | 원본 rcept={ro} 정정 rcept={rc} ===")
    orig = load_facts(ro)
    corr = load_facts(rc)
    if orig is None or corr is None:
        print("로드 실패")
        return

    allk = sorted(set(orig) | set(corr), key=lambda k: ((orig.get(k) or corr.get(k))[2], k[2]))
    rows = []
    for k in allk:
        _aid, fs, detail, per = k
        if per != 0 or fs != "CFS":
            continue
        ln = (orig.get(k) or corr.get(k))[2]
        if not any(w in ln for w in KEYWORDS):
            continue
        ov = orig.get(k, (None,))[0]
        cv = corr.get(k, (None,))[0]
        rows.append((ln, detail, ov, cv))

    print(f"\n[분식계정 주석 상세] 차원보유 주석 fact, CFS·당기 (총 {len(rows)})")
    print(f"  {'주석계정':30} {'차원(detail)':40} {'원본':>13} {'정정':>13} 판정")
    changed = 0
    for ln, detail, ov, cv in rows:
        if ov is not None and cv is not None and abs(ov - cv) > 1e6:
            changed += 1
            mark = "★원본>정정(부풀림)" if abs(ov) > abs(cv) else "원본<정정"
        elif ov is None:
            mark = "정정에만"
        elif cv is None:
            mark = "원본에만"
        else:
            mark = "동일"
        os_ = f"{ov / M:,.0f}" if ov is not None else "—"
        cs = f"{cv / M:,.0f}" if cv is not None else "—"
        # 변경 또는 한쪽만 있는 것 우선 표시(동일은 생략해 노이즈 감소)
        if mark != "동일":
            print(f"  {ln[:30]:30} {detail[:40]:40} {os_:>13} {cs:>13} {mark}")
    print(f"\n변경/차이 주석 {changed}건. 원본>정정(부풀림)이면 원본 주석=부정 당시 값.")


if __name__ == "__main__":
    main()
