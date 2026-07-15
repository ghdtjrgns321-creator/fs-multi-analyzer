"""Phase1 LLM 감사 — 한 회사연도의 전 차원 데이터를 읽기좋게 dump(에이전트가 읽고 판단).

목적: 딱딱한 pass/fail이 아니라, 에이전트(Claude)가 LLM으로서 회사 데이터를 감사관처럼 읽고
이상(분식단서·정규화오류·소실·스케일)을 직접 판단하게 데이터를 풍부히 노출한다. 임계검사는 floor.

**전수 조사 원칙 (고정)**: 이 하니스는 검사 대상(분식 회사연도 등)을 **전수로** 돌린다.
"대표"·"표본" 1~2개로 끝내지 않는다(그건 §9 hollow-PASS·§10 다운스코프). 전수는 배치
러너 `_p1_review_all.py`로 강제하고, 본 스크립트는 각 회사연도 dump + **데이터 완결성
기계검사(필수 테이블 MISSING이면 FAIL)**를 바닥에 깐다. LLM 판단은 그 바닥 위에서 한다.
dump엔 본문(A~G)뿐 아니라 **주석(H)·병합(I)**도 포함한다.

**원문 대조 원칙 (D·I)**: "P1이 정보를 누락/혼합하는가"는 P1 자신의 매퍼를 거쳐 비교하면 순환이라
영원히 안 보인다. §D는 DART raw 원문(account_nm·금액)을 **매퍼 미경유로** 정규화 산출물과 직접
대조해 미출현(소실 후보)을 센다(스케일 오류도 미출현으로 잡힘). §I는 한 canonical로 collapse된
서로 다른 raw label들을 그대로 보여 LLM이 이질 병합을 판정한다.

사용: PYTHONPATH=. uv run python data/backtest/_p1_company_review.py <corp> [year]
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import duckdb
import pandas as pd

from data.backtest._p1_review_all import sce_raw_conflict_count
from src.collect.storage import read_absence
from src.normalize.config import load_canonical_accounts
from src.normalize.mapper import OTHER_CANONICAL, AccountMapper

BASE = Path("data/companies")
M = 1_000_000  # 표시 단위 백만
EOK = 100_000_000  # 억(원) — 병기 환산 기준. 1억 = 100백만이므로 백만표시→억은 ÷100.
EOK_MIN = 100_000_000  # 1억 미만은 병기 생략(소액 노이즈 억제, amounts.ANNOTATE_THRESHOLD와 동일)
KNOWN_FS_ABSENCE = {"no_report", "dart_no_data"}
KNOWN_XBRL_ABSENCE = {"no_report", "dart_no_xbrl"}


def eok(x: object) -> str:
    """백만원 표시 옆에 억 환산을 병기한다 — 읽는 쪽에 나눗셈을 시키지 않는다.

    Why: 이 덤프는 G6 LLM 통독(onboarding_gate.run_g6)과 감사 통독의 **입력 경계**다.
    경계에서 환산을 읽는 쪽에 떠넘기면 스케일 오독이 난다. 실제로 백만→억 환산에 ÷1,000을
    오적용해(정답 ÷100) `golden/hit/_effect_ranking.md` 금액 9건이 전수 1/10로 기재됐다
    (2026-07-15 적발·교정). 섹션 헤더에 "(백만원)"이라 적혀 있었는데도 9/9가 틀렸다 —
    라벨은 방어가 아니다.

    해법은 프로덕션이 이미 쓰는 것과 같다: 환산은 코드가 하고 원값 옆에 병기한다
    (src/report/amounts.py annotate_amounts — "원값(1조 2,534.7억)"). 표시 기준은 백만으로
    통일한 채(단위 혼재 금지, show() 주석 참조) 병기만 얹는다.

    주의: 게이트가 파싱하는 라인(§B '차이 N' 줄 끝, [기계요약])에는 붙이지 않는다 —
    onboarding_gate._parse_g1의 정규식 `차이\\s+(-?[\\d,]+)\\s*$`가 깨진다.
    """
    n = pd.to_numeric(x, errors="coerce")
    if pd.isna(n) or abs(float(n)) < EOK_MIN:
        return ""
    return f"({float(n) / EOK:,.1f}억)"


def _missing_db_status(corp_code: str, year_value: str) -> str:
    reason = read_absence(BASE, corp_code, year_value).get("fs")
    if reason in KNOWN_FS_ABSENCE:
        return f"미제공({reason})"
    return "FAIL(DB없음·사유미상)"


def _missing_note_status(corp_code: str, year_value: str) -> str | None:
    reason = read_absence(BASE, corp_code, year_value).get("xbrl_zip")
    if reason in KNOWN_XBRL_ABSENCE:
        return f"미제공({reason})"
    return None


corp = sys.argv[1] if len(sys.argv) > 1 else "00126380"
cdir = BASE / corp
years = (
    sorted(y.name for y in cdir.iterdir() if y.is_dir() and y.name.isdigit())
    if cdir.exists()
    else []
)
year = sys.argv[2] if len(sys.argv) > 2 else (years[-1] if years else "")
db = cdir / year / "analysis.duckdb"
print(f"{'=' * 78}\nPhase1 감사 dump — {corp}/{year}\n{'=' * 78}")
if not db.exists():
    completeness = _missing_db_status(corp, year)
    print(f"정규화 DB 없음 — {completeness}")
    print(
        f"\n[기계요약] 완결성={completeness} 소실후보=0 전기소실=0 부호반전=0 "
        f"병합다중라벨=0 SCE표준화={completeness} SCE검산={completeness} 주석행=0/?"
    )
    sys.exit(1 if completeness.startswith("FAIL") else 0)

con = duckdb.connect(str(db), read_only=True)
tabs = {r[0] for r in con.execute("SHOW TABLES").fetchall()}

# ── 데이터 완결성 기계검사 (바닥). 필수 테이블 MISSING이면 명시적 FAIL ──
# Why: 하니스가 본문만 dump하고 주석 테이블 부재를 조용히 넘기면, 누락이 "정상"처럼 보여
# LLM이 못 본다(주석 재적재 누락 사고의 원인). 여기서 못 박는다.
REQUIRED = {
    "normalized_financials": "본문 정규화",
    "sce_equity_components": "SCE 2D",
    "note_facts_classified": "주석 분류적재",
}
print("\n## 0. 데이터 완결성 (필수 테이블 — MISSING이면 FAIL)")
fails = []
known_note_missing = None
for tbl, desc in REQUIRED.items():
    if tbl in tabs:
        cnt = con.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]  # noqa: S608 (고정 식별자)
        status = "OK" if cnt > 0 else "FAIL(빈 테이블)"
        if cnt == 0:
            if tbl == "note_facts_classified":
                known_note_missing = _missing_note_status(corp, year)
            if known_note_missing is None:
                fails.append(tbl)
            else:
                status = known_note_missing
        print(f"  [{status:14}] {tbl} ({desc}) 행={cnt}")
    else:
        if tbl == "note_facts_classified":
            known_note_missing = _missing_note_status(corp, year)
        if known_note_missing is None:
            fails.append(tbl)
            status = "FAIL(MISSING)"
        else:
            status = known_note_missing
        print(f"  [{status:14}] {tbl} ({desc}) — 테이블 없음")
if fails:
    print(f"  ⛔ 완결성 FAIL: {fails} — 이 회사연도는 감사 데이터 불완전(재적재/재정규화 필요)")

nf = con.execute("SELECT * FROM normalized_financials").fetchdf()
sce = (
    con.execute("SELECT * FROM sce_equity_components").fetchdf()
    if "sce_equity_components" in tabs
    else pd.DataFrame()
)
notes = (
    con.execute("SELECT * FROM note_facts_classified").fetchdf()
    if "note_facts_classified" in tabs
    else pd.DataFrame()
)
con.close()
nf["amt"] = pd.to_numeric(nf["amount"], errors="coerce")

# 0b. SCE 구성요소 표준화 상태 — 전 행 unmatched면 표준화 사망(빈 검산이 통과로 둔갑하는 원인).
# Why: 2026-06-10 발견 — 원본 교체 컨버터가 account_detail에 XBRL member 코드를 기록해
# 한글 alias 분류기가 전멸했는데, 어떤 검사도 비명을 안 질렀다. LLM이 매번 발견하길 기대하지
# 않고 기계로 못 박는다(발견 즉시 기계화 원칙).
sce_dead = (
    not sce.empty
    and "component_role" in sce.columns
    and bool((sce["component_role"] == "unmatched").all())
)
print("\n## 0b. SCE 구성요소 표준화 상태")
if sce.empty:
    print("  (sce 테이블 없음/빈 — §0 FAIL 참조)")
elif sce_dead:
    print(
        "  ⛔ FAIL — 전 행 role=unmatched(표준화 사망). account_detail 형식 vs config alias"
        " 불일치 의심(_P1_LOSS_FIX_PROMPT.md T1)"
    )
else:
    print("  role 분포:", dict(sce["component_role"].value_counts()))


def show(df, cols, n=200):
    pd.set_option("display.width", 200)
    pd.set_option("display.max_rows", n)
    # 항상 백만(÷M) 단위로 표시한다. 과거엔 abs<1백만 행을 원 단위로 표기해, 89만원 같은 미세값이
    # "900,000"처럼 큰 백만 숫자로 둔갑하는 표시 착시가 있었다(LLM이 거짓 스케일결함으로 오판).
    # sj_div·금액 무관 일괄 ÷M로 통일해 착시를 제거한다(데이터 무변경, 표시층만).
    # 여기에 억 병기를 얹는다(eok) — 기준 단위는 백만 그대로 두되(단위 혼재 금지) 읽는 쪽이
    # ÷100을 직접 하지 않게 한다. float_format은 amt 컬럼(유일한 float)에만 적용된다.
    pd.set_option("display.float_format", lambda x: f"{x / M:,.2f}{eok(x)}")
    return df[cols].to_string(index=False)


def trunc_note(total: int, shown: int) -> None:
    """silent truncation 금지 — 잘린 건수를 LLM이 알게 명시."""
    if total > shown:
        print(f"  … (외 {total - shown}건 생략 — 전수는 DB/raw에서 확인)")


# A. 본문 전과목(분류됨) — 표별, 금액순. LLM이 모든 과목을 읽음(단위: 백만)
# CFS 우선, 없으면 OFS(별도전용 회사가 빈 dump 되는 것 방지)
fs_main = "CFS" if (nf["fs_div"] == "CFS").any() else "OFS"
print(f"\n## A. 본문 분류 과목 전체 (백만원 + 억 병기, {fs_main}) — 표(sj_div)별")
if fs_main == "OFS":
    print("  (CFS 없음 — 별도재무제표 전용 회사. OFS로 dump)")
body = nf[nf["fs_div"] == fs_main]
for sj in ["BS", "IS", "CIS", "CF", "SCE"]:
    sub = body[(body["sj_div"] == sj) & (body["canonical"] != OTHER_CANONICAL)].copy()
    if sub.empty:
        continue
    sub = sub.reindex(sub["amt"].abs().sort_values(ascending=False).index)
    print(f"\n[{sj}] {len(sub)}과목")
    print(show(sub.head(40), ["canonical", "label", "amt", "mapping_status"]))
    trunc_note(len(sub), 40)

# B. 회계 항등식 + 검산
print("\n## B. 항등식·검산")


def v(canon, fs):
    s = nf[(nf["canonical"] == canon) & (nf["fs_div"] == fs)]
    a = pd.to_numeric(s["amount"], errors="coerce").dropna()
    if len(a) > 1:
        print(
            f"  ⚠ {canon}/{fs} 중복 {len(a)}행 (값들: {[f'{x / M:,.0f}' for x in a]}) — 첫 행 사용"
        )
    return None if a.empty else float(a.iloc[0])


for fs in ["CFS", "OFS"]:
    a, li, eq = v("자산총계", fs), v("부채총계", fs), v("자본총계", fs)
    cur_a, ncur_a = v("유동자산", fs), v("비유동자산", fs)
    if None not in (a, li, eq):  # 0도 정당한 값 — truthiness로 건너뛰지 않는다
        diff = a - li - eq
        print(
            f"  [{fs}] 자산 {a / M:,.0f} = 부채 {li / M:,.0f}+자본 {eq / M:,.0f}? "
            f"차이 {diff / M:,.0f}"
        )
    if None not in (a, cur_a, ncur_a):
        # 금융지주·복합기업 2부문 BS는 자산총계=유동+비유동+금융업자산. 금융업자산이 있으면 합산해
        # 항등식 오탐(금융업 규모만큼 차이)을 막는다.
        fin_a = v("금융업자산", fs) or 0
        asset_sum = cur_a + ncur_a + fin_a
        fin_note = f"+금융업 {fin_a / M:,.0f}" if fin_a else ""
        print(
            f"        유동 {cur_a / M:,.0f}+비유동 {ncur_a / M:,.0f}{fin_note}="
            f"{asset_sum / M:,.0f} vs 자산 {a / M:,.0f} "
            f"차이 {(asset_sum - a) / M:,.0f}"
        )

# C. 미분류(기타) 상위 — LLM이 "이 큰게 왜 미분류?" 판단
print("\n## C. 미분류(기타 중요 계정) 금액 상위 20 — LLM 판단: 진짜 미등록 표준인가/소계인가")
other = nf[nf["canonical"] == OTHER_CANONICAL].copy()
other = other.reindex(other["amt"].abs().sort_values(ascending=False).index)
print(show(other.head(20), ["sj_div", "fs_div", "label", "account_id", "amt"]))
trunc_note(len(other), 20)

# D. raw 원문 전수 대조 (매퍼 미경유) — 보존 funnel + 미출현(소실 후보) + 부호반전
# Why: P1 매퍼로 raw를 다시 매핑해 비교하면 매퍼 버그가 양쪽에 똑같이 들어가 순환(미탐).
# raw 금액 원문이 정규화 산출물(본문+SCE) 어디에도 안 나타나면 소실/스케일 버그 후보.
# 비교는 |절대값| 기준 — SCE 차감변동 -abs 정규화(의도된 부호 반전)가 거짓 소실로 뜨던 것 제거
# (2026-06-10: 소실 9건 중 7건이 이 거짓 경보였음). 부호만 반전된 생존은 별도 카운트로 노출해
# 부호 정보를 조용히 버리지 않는다(차감 외 계정의 부호 반전은 그 자체가 버그 단서 → LLM 판단).
# 동일금액 우연 일치는 미탐 가능 → 이 검사는 필요조건 floor, 최종 판단은 LLM(§A·§I와 교차).
print("\n## D. raw 원문 전수 대조 (DART CSV vs 정규화, 매퍼 미경유) — 미출현=소실/스케일 후보")
print("  (참고: CIS 행수 격차는 IS 재분류 포함 가능 — 미출현 0이면 손실 아님. SCE는 2D테이블로 셈)")
loss_total = 0
prior_loss_total = 0
flip_total = 0
for fs in ["CFS", "OFS"]:
    p = cdir / year / "raw" / f"finstate_all_{fs}.csv"
    nf_fs = nf[nf["fs_div"] == fs]
    if not p.exists():
        if not nf_fs.empty:
            print(
                f"  ⚠ [{fs}] raw CSV 없음 — 정규화 {len(nf_fs)}행의 원천 대조 불가"
                "(수집 산출물 확인)"
            )
        continue
    # 미분류(기타) 행도 포함 — unmapped는 "기타 중요 계정"으로 게시되어 보존된 것(프로젝트 규칙).
    # 미분류로 살아남은 금액은 소실이 아니라 §C(미분류 상위)에서 따로 판단한다.
    norm_signed = {int(round(x)) for x in nf_fs["amt"].dropna()}
    if not sce.empty:
        sce_fs = pd.to_numeric(sce[sce["fs_div"] == fs]["amount"], errors="coerce").dropna()
        norm_signed |= {int(round(x)) for x in sce_fs}
    norm_abs = {abs(v) for v in norm_signed}
    norm_prior_signed = {
        int(round(x)) for x in pd.to_numeric(nf_fs["prior_amount"], errors="coerce").dropna()
    }
    if not sce.empty:
        sce_prior_fs = pd.to_numeric(
            sce[sce["fs_div"] == fs]["prior_amount"], errors="coerce"
        ).dropna()
        norm_prior_signed |= {int(round(x)) for x in sce_prior_fs}
    norm_prior_abs = {abs(v) for v in norm_prior_signed}
    raw_rows = list(csv.DictReader(p.open(encoding="utf-8-sig")))
    raw_by_sj: dict[str, int] = {}
    lost, prior_lost, unparsed, flipped = [], [], 0, 0
    for r in raw_rows:
        sj = r.get("sj_div") or "?"
        raw_by_sj[sj] = raw_by_sj.get(sj, 0) + 1
        prior_s = (r.get("frmtrm_amount") or "").strip()
        if prior_s and prior_s != "-":
            try:
                prior_amt = int(round(float(prior_s.replace(",", ""))))
            except ValueError:
                prior_amt = 0
            if prior_amt != 0 and abs(prior_amt) not in norm_prior_abs:
                prior_lost.append((sj, r.get("account_nm", ""), r.get("account_id", ""), prior_amt))
        s = (r.get("thstrm_amount") or "").strip()
        if not s or s == "-":
            continue
        try:
            # round 통일 — 파이프라인은 반올림 저장하므로 절사(int)는 소수 .5+에서 거짓 소실
            # (라운드3 H1: EPS -145.6 → 절사 -145 vs DB -146으로 8건 거짓 경보)
            amt = int(round(float(s.replace(",", ""))))
        except ValueError:
            unparsed += 1
            continue
        if amt == 0:
            continue
        if abs(amt) not in norm_abs:
            lost.append((sj, r.get("account_nm", ""), r.get("account_id", ""), amt))
        elif amt not in norm_signed:
            flipped += 1
    sce_fs_cnt = 0 if sce.empty else int((sce["fs_div"] == fs).sum())
    nf_by_sj = nf_fs["sj_div"].value_counts().to_dict()
    funnel = "  ".join(
        f"{sj}:{raw_by_sj.get(sj, 0)}→{(sce_fs_cnt if sj == 'SCE' else nf_by_sj.get(sj, 0))}"
        for sj in ["BS", "IS", "CIS", "CF", "SCE"]
    )
    print(f"  [{fs}] 행수 funnel(raw→norm, SCE는 2D테이블): {funnel}")
    if unparsed:
        print(f"  ⚠ [{fs}] 금액 파싱불가 raw {unparsed}행 — 대조 제외됨(원문 형식 확인)")
    if flipped:
        flip_total += flipped
        print(
            f"  ⚠ [{fs}] 부호반전 생존 {flipped}건 — 절대값은 보존, 부호만 반전(차감 -abs 정규화"
            " 의도 포함. 차감 목록 밖 계정이면 부호 버그 — LLM이 §F·config 차감목록과 대조)"
        )
    if lost:
        loss_total += len(lost)
        lost.sort(key=lambda t: abs(t[3]), reverse=True)
        print(
            f"  ⛔ [{fs}] 미출현(소실 후보) {len(lost)}건 — "
            "raw 금액(|절대값|)이 정규화 어디에도 없음:"
        )
        for sj, nm, aid, amt in lost[:15]:
            print(f"    {sj:3} {nm[:28]:28} {aid[:34]:34} {amt / M:>14,.0f}")
        trunc_note(len(lost), 15)
    else:
        print(f"  [{fs}] 미출현 0건 — raw 금액 전수가 정규화에 생존(절대값 기준)")
    if prior_lost:
        prior_loss_total += len(prior_lost)
        prior_lost.sort(key=lambda t: abs(t[3]), reverse=True)
        print(
            f"  ⛔ [{fs}] 전기 미출현(전기소실 후보) {len(prior_lost)}건 — "
            "raw 전기 금액(|절대값|)이 정규화 prior 어디에도 없음:"
        )
        for sj, nm, aid, amt in prior_lost[:15]:
            print(f"    {sj:3} {nm[:28]:28} {aid[:34]:34} {amt / M:>14,.0f}")
        trunc_note(len(prior_lost), 15)
    else:
        print(f"  [{fs}] 전기 미출현 0건 — raw 전기 금액 전수가 prior에 생존(절대값 기준)")

# E. 시계열 — 당기/전기/전전기 (주요계정) LLM이 급변 판단 + 전기 보존율
print(f"\n## E. 시계열 (당기·전기·전전기, 백만 + 억 병기, {fs_main}) — 급변·역전 판단")
pri_null = nf["prior_amount"].isna().mean() * 100
pri2_null = nf["prior2_amount"].isna().mean() * 100
print(
    f"  전기 결측 {pri_null:.0f}% · 전전기 결측 {pri2_null:.0f}% "
    "(광범위 결측=시계열 정보 소실 의심)"
)
ts = nf[
    (nf["fs_div"] == fs_main)
    & nf["canonical"].isin(
        ["자산총계", "부채총계", "자본총계", "매출", "당기순이익", "재고자산", "매출채권"]
    )
]


def _fm(x: object) -> str:
    # 백만 표시 + 억 병기(eok). 시계열은 급변 판단에 가장 많이 인용되는 구간이라 병기 필수.
    n = pd.to_numeric(x, errors="coerce")
    return "—" if pd.isna(n) else f"{float(n) / M:,.0f}{eok(n)}"


for _, r in ts.iterrows():
    p0, p1, p2 = r["amount"], r.get("prior_amount"), r.get("prior2_amount")
    print(f"  {str(r['canonical']):12s} 당기 {_fm(p0):>24} 전기 {_fm(p1):>24} 전전기 {_fm(p2):>24}")

# F-1. SCE 원공시 자기모순 — raw bare 합계행과 구성요소 컬럼 합 비교.
raw_conflict_count = sce_raw_conflict_count(sce)
print("\n## F-1. SCE 원공시모순 (bare 합계행 vs 구성요소 컬럼합)")
if raw_conflict_count:
    print(f"  ⚠ 원공시모순 {raw_conflict_count}건 — raw bare 값과 구성요소 합 불일치")
else:
    print("  원공시모순 0건")

# F. SCE 검산 + 변동 — bare 합계행(component_std='-')의 change_role 기준(leaf만 합산).
# Why: 소계(총포괄손익·기타포괄손익)·조정후개시(스톡)를 변동으로 합산하면 이중계상이라 검산이
# 깨진다(N1/D5 라운드1). change_role로 leaf만 합산하고 begin/total을 양 끝으로 쓴다. 검산 입력이
# 비면(begin/total 부재·role 컬럼 없음) 명시적 FAIL — 불능을 정상처럼 두지 않는다(hollow 차단).
print("\n## F. SCE 검산 (기초+Σleaf변동=기말, change_role 기준)")
sce_check = "불가"
if sce.empty:
    print("  ⛔ 검산 불가 — sce_equity_components 없음/빈(§0 FAIL). 통과 아님")
elif "change_role" not in sce.columns:
    print("  ⛔ 검산 불가 — change_role 컬럼 없음(구버전 정규화). 재정규화(--force) 필요")
else:
    from src.normalize.sce import sce_balance

    res = sce_balance(sce, fs_main)
    if not res["computable"]:
        print(
            f"  ⛔ 검산 불가 — bare 합계행 {res.get('n_bare', '?')}개, 기초자본/자본총계 부재. "
            "빈 검산을 통과로 두지 않는다(§0b SCE 표준화부터 수선)"
        )
    else:
        beg, leaf_sum, end, diff = res["begin"], res["leaf_sum"], res["end"], res["diff"]
        sce_check = "OK" if res["ok"] else f"FAIL({diff / M:,.0f})"
        print(
            f"  기초 {beg / M:,.0f} + Σleaf {leaf_sum / M:,.0f} = {(beg + leaf_sum) / M:,.0f} "
            f"vs 기말 {end / M:,.0f} 차이 {diff / M:,.0f} → {sce_check}"
            f"  (leaf {res['n_leaf']}행, 소계·조정후개시 {res['n_excluded']}행 제외)"
        )
        bare = sce[(sce["fs_div"] == fs_main) & (sce["component_std"] == "-")].copy()
        bare["a"] = pd.to_numeric(bare["amount"], errors="coerce")
        leaf = bare[bare["change_role"] == "leaf"]
        mv = leaf.groupby("change_canonical")["a"].sum()
        mv_sorted = mv.sort_values(key=lambda s: s.abs(), ascending=False)
        print("  leaf변동:", {k: f"{x / M:,.0f}" for k, x in mv_sorted.head(20).items()})

    # 가로 항등(총계=지배+비지배) — 세로 검산이 못 보는 축. 위반=원공시 내부 부호·금액 모순(우리
    # 정규화 결함 아님, raw 충실). 부정 확정 아니라 감사 리스크 후보로 노출.
    from src.normalize.sce import sce_horizontal_identity

    hviol = sce_horizontal_identity(sce, fs_main)
    if hviol:
        print(f"  ⚠ 가로항등 위반 {len(hviol)}건 (총계≠지배+비지배 = 원공시 내부 모순, 감사 후보):")
        for v in hviol:
            print(
                f"    [{v['change_label']}] 총계 {v['grand'] / M:,.0f} vs "
                f"지배+비지배 {v['expected'] / M:,.0f} 차이 {v['diff'] / M:,.0f}"
            )
    else:
        print("  가로항등(총계=지배+비지배): 위반 없음")

# G. 통화·스케일·부호 이상 신호
print("\n## G. 이상 신호")
print(f"  통화: {sorted(set(nf['currency'].dropna()))}")
neg_assets = nf[
    (nf["sj_div"] == "BS")
    & (nf["canonical"].astype(str).str.contains("자산|현금|재고|채권", na=False))
    & (nf["amt"] < 0)
]
if not neg_assets.empty:
    print(f"  ⚠ 음수 자산계정 {len(neg_assets)}: {list(neg_assets['canonical'].head())}")
big = nf[nf["amt"].abs() > 1e15]
if not big.empty:
    big_values = list(zip(big["canonical"].head(), (big["amt"].head() / M).round(), strict=False))
    print(f"  ⚠ 비정상 거대값(>1000조) {len(big)}: {big_values}")
# H. 주석 (note_facts_classified) — 분식 고가치 차원을 LLM이 읽고 판단
print("\n## H. 주석 분류 (note_facts_classified) — 특수관계자·차입·만기·약정·보증 등")
note_raw_cnt = None
tsv = cdir / year / "raw" / "notes_xbrl" / "note_facts.tsv"
if tsv.exists():
    with tsv.open(encoding="utf-8") as f:
        note_raw_cnt = max(sum(1 for _ in f) - 1, 0)  # 헤더 제외
if notes.empty:
    print(
        "  ⛔ 주석 없음 — 완결성 FAIL(§0 참조). 본문만으론 주석분식(특수관계자·약정 등) 감사 불가"
    )
    if note_raw_cnt:
        print(f"  (raw TSV엔 {note_raw_cnt}행 존재 — 분류적재 단계에서 전량 소실)")
else:
    if note_raw_cnt is not None:
        rate = len(notes) / note_raw_cnt * 100 if note_raw_cnt else 0
        print(f"  적재율 {len(notes)}/{note_raw_cnt}행 ({rate:.0f}%) — 분모는 raw XBRL TSV")
        if note_raw_cnt and rate < 50:
            print("  ⚠ 적재율 50% 미만 — 분류기가 다수 fact를 떨굼(의도된 흡수인지 LLM 판단)")
    else:
        print(f"  총 {len(notes)}행 (⚠ raw TSV 없음 — 적재율 분모 확인 불가)")
    if "bucket" in notes:
        print("  bucket:", dict(notes["bucket"].value_counts()))
    if "category" in notes:
        cats = notes["category"].dropna()
        print(
            "  category 상위:",
            dict(cats.value_counts().head(10)) if not cats.empty else "없음(흡수/기타주석뿐)",
        )
    if "dimensions" in notes:
        import re
        from collections import Counter

        axes: Counter = Counter()
        for d in notes["dimensions"].dropna().astype(str):
            for m in re.findall(r"([A-Za-z]+Axis)", d):
                axes[m] += 1
        # 회사별 주석 풍부도(자본구성요소만=빈약 vs 차입·특수관계자=풍부)를 LLM이 판단
        print("  주석 차원축 분포:", dict(axes.most_common(12)))
        pat = "RelatedPart|Borrowing|Maturity|Commitment|Guarantee|Collateral|Segment"
        hot = notes[notes["dimensions"].astype(str).str.contains(pat, na=False)]
        print(f"  분식 고가치축 fact {len(hot)}건 (샘플):")
        for _, r in hot.head(10).iterrows():
            lab = str(r.get("label_ko", ""))[:22]
            dim = str(r.get("dimensions", ""))[:46]
            print(f"    {lab:22} | {dim:46} | {str(r.get('value', ''))[:18]}")
        trunc_note(len(hot), 10)

# I. 병합 가시화 — 한 canonical로 collapse된 서로 다른 raw label 전시(LLM이 이질 병합 판정)
# Why: 하류(신호엔진)는 canonical 단위로 집계하므로, 이질 계정이 한 canonical에 묶이면
# 그 시점부터 구분이 소멸한다. R5(라운드2): DB만 보면 dedup으로 사라진 label은 안 보인다
# (01675421/2023 보통주자본금→자본금 collapse). raw를 매퍼로 매핑(dedup 이전)해 canonical별
# distinct raw label을 세고, DB 생존 label과 대조해 "병합으로 사라진 label"까지 노출한다.
# (§D의 매퍼-미경유 원칙은 '값 대조'에 한정 — 병합 '가시화'는 매퍼 사용이 목적 그 자체라 정당.)
print("\n## I. 병합 가시화 — 1 canonical ← 2+ raw label (dedup 이전 매퍼 매핑 기준)")
_mapper = AccountMapper(load_canonical_accounts(Path("config/canonical_accounts.yaml")))
raw_groups: dict[tuple[str, str, str], dict[str, object]] = {}
for fs in ["CFS", "OFS"]:
    p = cdir / year / "raw" / f"finstate_all_{fs}.csv"
    if not p.exists() or p.stat().st_size <= 5:
        continue
    for r in csv.DictReader(p.open(encoding="utf-8-sig")):
        res = _mapper.map_row(
            {"account_id": r.get("account_id", ""), "account_nm": r.get("account_nm", "")}
        )
        if res.canonical == OTHER_CANONICAL:
            continue
        key = (fs, r.get("sj_div", "") or "?", res.canonical)
        g = raw_groups.setdefault(key, {"labels": {}})
        amt = (r.get("thstrm_amount") or "").replace(",", "").strip()
        g["labels"].setdefault(r.get("account_nm", ""), amt)  # type: ignore[union-attr]
# 생존 label(DB) — '기타 중요 계정' 강등·SCE 2D 보존도 생존이다(라운드3 H2: 강등/SCE 생존을
# ✗소실로 거짓 표기). 소실 판정은 fs 내 전 테이블 기준, canonical별 set은 ✓표시용으로만 유지.
db_labels: dict[tuple[str, str, str], set] = {}
for _, r in nf[nf["canonical"] != OTHER_CANONICAL].iterrows():
    db_labels.setdefault((r["fs_div"], r["sj_div"], r["canonical"]), set()).add(str(r["label"]))
db_label_any: set[tuple[str, str]] = {(r["fs_div"], str(r["label"])) for _, r in nf.iterrows()}
if not sce.empty:
    db_label_any |= {(r["fs_div"], str(r["change_label"])) for _, r in sce.iterrows()}
multi = {k: v for k, v in raw_groups.items() if len(v["labels"]) > 1}  # type: ignore[arg-type]
merge_groups = len(multi)
if merge_groups == 0:
    print("  다중 label canonical 없음 — 본문 병합 collapse 없음(raw 기준)")
else:
    print(f"  {merge_groups}그룹 (raw에서 canonical 하나에 distinct label 2개 이상):")
    for (fs, sj, canon), g in sorted(
        multi.items(),
        key=lambda kv: -len(kv[1]["labels"]),  # type: ignore[arg-type]
    )[:12]:
        survived = db_labels.get((fs, sj, canon), set())
        labels = g["labels"]  # type: ignore[index]
        # 병합으로 사라진 label = fs 내 어느 테이블(본문 OTHER 강등·SCE 포함)에도 없는 것
        lost = [lab for lab in labels if (fs, lab) not in db_label_any]
        tag = f" ⚠병합소실 {len(lost)}" if lost else ""
        print(f"  [{fs}/{sj}] {canon} ← raw {len(labels)}개 label{tag}:")
        for lab, amt in list(labels.items())[:8]:
            mark = "✗소실" if lab in lost else "✓생존"
            try:
                amt_s = f"{int(float(amt)) / M:,.0f}" if amt and amt != "-" else "—"
            except ValueError:
                amt_s = "—"
            print(f"      {mark} {str(lab)[:34]:34} {amt_s:>14}")
    trunc_note(merge_groups, 12)

# 배치 러너(_p1_review_all.py)가 파싱하는 기계 요약 — 포맷 변경 시 러너 정규식 동기화
print(
    f"\n[기계요약] 완결성={'OK' if not fails else 'FAIL'} 소실후보={loss_total} "
    f"전기소실={prior_loss_total} 부호반전={flip_total} "
    f"병합다중라벨={merge_groups} 원공시모순={raw_conflict_count} "
    f"SCE표준화={'FAIL' if sce_dead or sce.empty else 'OK'} SCE검산={sce_check} "
    f"주석행={len(notes)}/{note_raw_cnt if note_raw_cnt is not None else '?'}"
)
print(
    "[감사 안내] 위 dump를 LLM이 읽고: 분식단서(급변·역전·미분류 큰계정)·소실(§D 미출현)·"
    "이질병합(§I label 묶음)·검산불일치·이상부호·주석분식(특수관계자·약정)을 감사관처럼 판단한다. "
    "§0 완결성 FAIL이면 데이터부터 고친다. PHASE1_VERIFICATION_PROTOCOL.md 참조."
)
