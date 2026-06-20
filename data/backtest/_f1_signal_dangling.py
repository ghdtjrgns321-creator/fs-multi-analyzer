"""F1 신호 dangling 글로벌 검사 — 신호엔진이 참조하는 canonical 이름이 죽지 않았는지.

배경: lump/rename으로 canonical 이름이 바뀌었는데 신호엔진(코드·playbook)이 옛 이름을
참조하면, 매칭이 0행이 되어 **분식 신호가 조용히 죽는다**(에러 없이 빈 결과). PROTOCOL F1.
per-chunk 홀리스틱으로는 못 잡는 전사(글로벌) 사각이라 일회성/회귀 스크립트로 본다.

2계층 검사:
  Layer A (정적) — 신호엔진이 참조하는 canonical 문자열 전부 추출 → config의 canonical
                   키에 존재하나? 없으면 = 즉시 사망(타이포·삭제·리네임 미반영).
  Layer B (실증) — 그 이름이 감사 corpus(101사/383cy) 정규화 산출물에서 한 번이라도
                   canonical로 생성되나? 0건이면 = 키는 있으나 정규화가 안 붙임 =
                   신호가 영원히 데이터 없음(실질 dangling). (회사 특성상 일부만 등장하는
                   계정과 구분하려 '등장 회사연도 수'를 같이 출력한다.)

참조 출처(전수):
  - config/playbooks/relationship_chains.yaml  l2_mvp1.{yoy_accounts, growth_divergences,
       direction_checks, signal_thresholds.direction_red_flags}
  - config/playbooks/financial_ratios.yaml     ratios[].accounts[]
  - 코드 하드코딩 레지스트리(아래 CODE_HARDCODED, 감사로 전수 확인 — grep 근거 주석)

실행: PYTHONPATH=. uv run python data/backtest/_f1_signal_dangling.py
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
CHUNKS = ROOT / "data" / "backtest" / "_holistic_chunks.json"

# 코드에 박힌 canonical 비교 리터럴(== "<한글>"). 근거: grep -rnoE 'canonical.*== *"[가-힣]"' src/
# 신호·분석 파이프라인 전수. "기타 중요 계정"(미매핑 버킷)·account_id 리터럴은 canonical 아님 → 제외.
CODE_HARDCODED: dict[str, str] = {
    "자산총계": "src/signals/{mvp1.py:203, universal.py:260, restatement.py:123, sanity.py:71}",
    "부채총계": "src/backtest/review_packet.py:68",
    "자본총계": "src/backtest/review_packet.py:69",
    "매출채권": "src/signals/finding_input.py:13 (select_2023_numeric_signal)",
    "영업활동현금흐름": "src/signals/finding_input.py:15 (select_2023_numeric_signal)",
}

# 의도된 미존재(가드됨) — dangling으로 세지 않되 기록. ratios.py가 roi를 _missing으로 단락.
GUARDED_ABSENT: dict[str, str] = {
    "투자원가": "financial_ratios.yaml roi.accounts[1] — ratios.py가 계산 전 _missing로 단락(deferred)",
}

# Layer B(corpus 미행사)는 FAIL 아님 — config 엔트리가 구조적으로 유효(account_ids+alias)하면
# 해당 계정을 신고한 회사가 corpus(101사 분식후보)에 없을 뿐, 신고되면 정상 매핑된다.
# 2026-06-14 전체 모집단 4,771 DB 스캔으로 입증: '공사손실충당부채'(yoy_accounts 참조)는 감사
# corpus 313cy에서 0회였으나, 모집단에서 dart_CurrentProvisionForConstructionLosses → 공사손실충당부채
# 35행+비유동 3행 정상 매핑됨(건설사 부재가 원인, 리네임 잔재 아님). 따라서 게이트는 Layer A만 본다.
# (부수 관찰: 같은 id가 모집단에서 '기타 중요 계정' 21행·'충당부채' 1행으로도 갈림 — peer DB 구버전
#  정규화 잔재 의심. F1 dangling과 별개 트랙, 본 스크립트 판정엔 영향 없음.)


def collect_references() -> dict[str, list[str]]:
    """참조된 canonical 이름 -> 출처 목록(provenance)."""
    refs: dict[str, list[str]] = {}

    def add(name: object, prov: str) -> None:
        if name is None:
            return
        refs.setdefault(str(name), []).append(prov)

    rc = yaml.safe_load((CONFIG / "playbooks" / "relationship_chains.yaml").read_text("utf-8"))
    l2 = rc.get("l2_mvp1", {})
    for a in l2.get("yoy_accounts", []):
        add(a, "relationship_chains:l2_mvp1.yoy_accounts")
    for g in l2.get("growth_divergences", []):
        add(g.get("account_a"), f"relationship_chains:growth_div[{g.get('id')}].account_a")
        add(g.get("account_b"), f"relationship_chains:growth_div[{g.get('id')}].account_b")
    for d in l2.get("direction_checks", []):
        add(d.get("growth_account"), f"relationship_chains:direction_check[{d.get('id')}].growth")
        add(d.get("flow_account"), f"relationship_chains:direction_check[{d.get('id')}].flow")
    for r in l2.get("signal_thresholds", {}).get("direction_red_flags", []):
        add(r.get("account_a"), f"relationship_chains:red_flag[{r.get('id')}].account_a")
        add(r.get("account_b"), f"relationship_chains:red_flag[{r.get('id')}].account_b")

    fr = yaml.safe_load((CONFIG / "playbooks" / "financial_ratios.yaml").read_text("utf-8"))
    for it in fr.get("ratios", []):
        for acc in it.get("accounts", []):
            add(acc, f"financial_ratios:ratios[{it.get('id')}].accounts")

    for name, prov in CODE_HARDCODED.items():
        add(name, f"code:{prov}")

    return refs


def canonical_keys() -> set[str]:
    cfg = yaml.safe_load((CONFIG / "canonical_accounts.yaml").read_text("utf-8"))
    return set(cfg["canonical_accounts"].keys())


def corpus_canonical_counts() -> dict[str, int]:
    """감사 corpus(101사/383cy)에서 각 canonical 이름이 등장한 회사연도 수."""
    chunks = json.loads(CHUNKS.read_text("utf-8"))["chunks"]
    counts: dict[str, int] = {}
    scanned = 0
    for ch in chunks:
        for comp in ch["companies"]:
            corp = comp["corp"]
            for year in comp["years"]:
                db = ROOT / "data" / "companies" / corp / str(year) / "analysis.duckdb"
                if not db.exists():
                    continue
                scanned += 1
                con = duckdb.connect(str(db), read_only=True)
                try:
                    rows = con.execute(
                        "SELECT DISTINCT canonical FROM normalized_financials "
                        "WHERE canonical IS NOT NULL"
                    ).fetchall()
                finally:
                    con.close()
                for (canon,) in rows:
                    counts[str(canon)] = counts.get(str(canon), 0) + 1
    counts["__scanned_cy__"] = scanned
    return counts


def main() -> None:
    refs = collect_references()
    keys = canonical_keys()
    counts = corpus_canonical_counts()
    scanned = counts.pop("__scanned_cy__", 0)

    layer_a_dangling = {n: p for n, p in refs.items() if n not in keys and n not in GUARDED_ABSENT}
    # Layer B: config엔 있으나 corpus 전수에서 한 번도 canonical로 안 생성된 참조
    layer_b_dangling = {
        n: p
        for n, p in refs.items()
        if n in keys and counts.get(n, 0) == 0 and n not in GUARDED_ABSENT
    }

    print("[F1] 신호엔진 canonical dangling 검사")
    print(f"  config canonical 키: {len(keys)}")
    print(f"  신호엔진 참조 고유 이름: {len(refs)}  (corpus 스캔 {scanned} 회사연도)")
    print()

    print(f"[Layer A] 참조하나 config 키에 없음(즉시 사망): {len(layer_a_dangling)}")
    for n in sorted(layer_a_dangling):
        print(f"  ✗ {n!r}")
        for p in layer_a_dangling[n]:
            print(f"      <- {p}")
    print()

    print(
        f"[Layer B] config엔 있으나 corpus 전수 0회 생성(WARN — corpus 미행사, FAIL 아님): {len(layer_b_dangling)}"
    )
    for n in sorted(layer_b_dangling):
        print(f"  ⚠ {n!r}  ({refs[n][0]})")
        print(
            "      엔트리 유효(account_ids 있음) → 해당계정 신고 회사가 corpus에 없을 뿐. 게이트 제외."
        )
    print()

    print("[참고] 가드된 의도적 미존재:")
    for n, why in GUARDED_ABSENT.items():
        in_keys = "config키있음" if n in keys else "config키없음"
        print(f"  - {n!r} [{in_keys}, corpus {counts.get(n, 0)}cy] — {why}")
    print()

    # 저빈도 경고: corpus 등장이 매우 적은 참조(회사 특성일 수 있으나 리네임 잔재 가능)
    rare = sorted(
        ((n, counts.get(n, 0)) for n in refs if n in keys and 0 < counts.get(n, 0) <= 3),
        key=lambda x: x[1],
    )
    if rare:
        print(
            f"[저빈도 참조] corpus {scanned}cy 중 ≤3회만 등장(리네임 잔재 의심 후보, 정상일 수도):"
        )
        for n, c in rare:
            print(f"  · {n!r}: {c}cy")
        print()

    # 게이트는 Layer A(즉시사망)만 본다. Layer B는 corpus 구성(특정계정 신고회사 부재)이라 WARN.
    ok = not layer_a_dangling
    print("=" * 60)
    print(f"판정: {'PASS — 진성 dangling 0' if ok else 'FAIL — dangling 존재(Layer A)'}")
    print(
        f"  Layer A(즉시사망·게이트) {len(layer_a_dangling)} / Layer B(corpus 미행사·WARN) {len(layer_b_dangling)}"
    )


if __name__ == "__main__":
    main()
