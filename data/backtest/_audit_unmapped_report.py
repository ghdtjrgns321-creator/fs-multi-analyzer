"""_audit_unmapped.json + _audit_macro_structure.json → data/backtest/UNMAPPED_AUDIT.md.

미분류 잔여(분류 천장)와 거시 구조 인벤토리를 합쳐 '거시 분류 설계' 입력으로 제시.
분류후보는 config 등록ID와 대조해 '신규분류 가능(어디에도 canonical 없음)' vs
'기존개념 타표문(가드가 강등)'으로 가른다. 단정 금지(§8) — 설계·수정은 다음 단계.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.normalize.config import load_canonical_accounts

UN = Path("data/backtest/_audit_unmapped.json")
MAC = Path("data/backtest/_audit_macro_structure.json")
OUT = Path("data/backtest/UNMAPPED_AUDIT.md")
CONFIG = Path("config/canonical_accounts.yaml")


def won(x: float) -> str:
    return f"{x / 1e8:,.0f}억" if abs(x) >= 1e8 else f"{x / 1e8:,.2f}억"


def main() -> None:
    un = json.loads(UN.read_text(encoding="utf-8"))
    mac = json.loads(MAC.read_text(encoding="utf-8")) if MAC.exists() else None
    accounts = load_canonical_accounts(CONFIG)
    registered_ids = {aid: ac.name for ac in accounts for aid in ac.account_ids}

    cands = un["classify_candidates"]
    # 신규분류 가능 vs 기존개념 타표문(가드 강등)
    new_cand = [c for c in cands if c["account_id"] not in registered_ids]
    demoted = [c for c in cands if c["account_id"] in registered_ids]
    new_cand.sort(key=lambda c: -c["n"])
    demoted.sort(key=lambda c: -c["n"])

    cov = un["coverage"]
    L = []
    A = L.append
    A("# 미분류 잔여 + 거시구조 전수 탐색 (UNMAPPED_AUDIT)")
    A("")
    A(
        "> Phase1이 canonical로 분류 못 하고 '기타 중요 계정'으로 넘기는 잔여를 전수 측정 + 사업보고서"
    )
    A(
        "> 분해 차원 인벤토리. 운영 가드·_dedupe_statement_rows 실호출. 목적: 분류 천장·거시구조 파악."
    )
    A(
        "> 단정 금지 — canonical 신설·수정은 다음 단계(§8). 재현: `_audit_unmapped.py`·`_audit_macro_structure.py`."
    )
    A("")
    A("## 1. 미분류 잔여 전수")
    A("")
    A(f"- 회사 {cov['companies']}사·파일 {cov['files']:,}·회사연도 {cov['company_years']:,}.")
    A(
        f"- statement-dedup 후 행 {cov['rows_after_stmt_dedup']:,} 중 **미분류 {cov['unmapped_rows']:,} "
        f"({cov['unmapped_pct']}%)**, 분류 {cov['mapped_rows']:,}."
    )
    A(
        f"- 가드 후 raw {cov['raw_rows_after_guard']:,} → dedup 붕괴 {cov['collapsed_by_stmt_dedup']:,}행 "
        f"(차원행 raw {cov['dim_rows_raw']:,} — 주로 SCE 구성요소·member)."
    )
    br = un["unmapped_breakdown_rows"]
    A(
        f"- 미분류 분해: 표준ID 보유 {br.get('has_id', 0):,}행 / 공백ID(확장계정) {br.get('blank_id', 0):,}행."
    )
    A("")
    A(
        "> 금액(최대금액)은 원천 `thstrm_amount` 절대값이며 원천 스케일 이상치(corp 00204226 등)가 "
        "일부 과대계상. 분류 후보 판단 기준은 **행수·표준ID 존재**이며 금액과 무관."
    )
    A("")
    A("### sj_div별 미분류율 (어느 표가 안 잡히나)")
    A("")
    A("| sj_div | 전체 | 미분류 | 미분류율 |")
    A("|---|--:|--:|--:|")
    for sj, v in un["sj_distribution"].items():
        A(f"| {sj} | {v['total']:,} | {v['unmapped']:,} | {v['unmapped_pct']}% |")
    A("")

    A("## 2. 신규분류 가능 — 표준ID 있는데 canonical 어디에도 없음 (최우선)")
    A("")
    A(
        f"표준ID 보유·미등록 account_id **{len(new_cand)}종**. 이것이 '더 분류할 수 있는' 핵심 — "
        "canonical 신설/등록 시 EXACT 매핑으로 분류 가능."
    )
    A("")
    A("| account_id | 행수 | 최대금액 | 주 sj | 예시 라벨 |")
    A("|---|--:|--:|---|---|")
    for c in new_cand[:60]:
        sj = max(c["sj"], key=c["sj"].get) if c.get("sj") else ""
        A(
            f"| {c['account_id']} | {c['n']:,} | {won(c['amax'])} | {sj} | {', '.join(c['labels'][:2])} |"
        )
    if len(new_cand) > 60:
        A("")
        A(f"… 외 {len(new_cand) - 60}종 (전체 _audit_unmapped.json).")
    A("")

    A("## 3. 기존개념 타표문 (가드가 강등 — 동일 숫자의 CF/SCE 표현)")
    A("")
    A(
        f"이미 다른 표문에 canonical이 있는 개념 **{len(demoted)}종**이 CF/SCE 등에서 미분류로 남음 "
        "(예: ProfitLoss·Equity의 현금흐름표·자본변동표 표현). statement 가드의 의도된 분리이며, "
        "같은 숫자라 신규분류 대상 아님 — 필요 시 '표문 태깅'으로 연결만."
    )
    A("")
    A("| account_id | (소속 canonical) | 행수 | 최대금액 | 주 sj |")
    A("|---|---|--:|--:|---|")
    for c in demoted[:25]:
        sj = max(c["sj"], key=c["sj"].get) if c.get("sj") else ""
        A(
            f"| {c['account_id']} | {registered_ids.get(c['account_id'], '')} | {c['n']:,} | {won(c['amax'])} | {sj} |"
        )
    A("")

    ext = un.get("extension_accounts", [])
    A("## 4. 공백 표준ID 확장계정 (회사 자체계정 — 표준ID 없음)")
    A("")
    A(
        f"account_id 공백 + 미분류 라벨 상위 {min(len(ext), 30)} (표준ID 없어 alias로만 가능). 분모 {ext and sum(e['n'] for e in ext) or 0:,}행+."
    )
    A("")
    A("| 라벨 | 행수 | 최대금액 |")
    A("|---|--:|--:|")
    for e in ext[:30]:
        A(f"| {e['label']} | {e['n']:,} | {won(e['amax'])} |")
    A("")

    if mac:
        mc = mac["coverage"]
        A("## 5. 거시 구조 인벤토리 (사업보고서 분해 차원)")
        A("")
        A(f"전수 {mc['companies']}사·{mc['files']:,}파일·raw {mc['rows_all_raw']:,}행.")
        A("")
        A("### 5.1 재무제표 × 연결/별도 행렬")
        A("")
        A("| | " + " | ".join(sorted({k.split("/")[1] for k in mac["fs_sj_matrix"]})) + " |")
        sjs = sorted({k.split("/")[1] for k in mac["fs_sj_matrix"]})
        A("|---|" + "--:|" * len(sjs))
        for fs in ("CFS", "OFS"):
            cells = [f"{mac['fs_sj_matrix'].get(f'{fs}/{sj}', 0):,}" for sj in sjs]
            A(f"| {fs} | " + " | ".join(cells) + " |")
        A("")
        A("### 5.2 account_detail 차원종류 (분해축 규모)")
        A("")
        A("| sj_div | plain | member | 구성요소 | 기타detail |")
        A("|---|--:|--:|--:|--:|")
        for sj, c in mac["detail_kind_by_sj"].items():
            A(
                f"| {sj} | {c.get('plain', 0):,} | {c.get('member', 0):,} | {c.get('구성요소', 0):,} | {c.get('기타detail', 0):,} |"
            )
        A("")
        A(
            f"→ **SCE만 2D 매트릭스**(자본구성요소 {mac['sce_components_distinct']}종 × 자본변동 행). "
            "BS/IS/CIS/CF는 plain(1D). member는 연결/별도 등 표문 태그."
        )
        A("")
        A("### 5.3 SCE 자본구성요소 축 (상위)")
        A("")
        A(", ".join(f"{k}({v:,})" for k, v in list(mac["sce_components_top"].items())[:15]))
        A("")
        A("### 5.4 기간·단위·보고서종류")
        A("")
        pf = mac["period_fill_pct"]
        A(
            f"- 기간 충전율: 당기 {pf['thstrm']}% · 전기 {pf['frmtrm']}% · 전전기 {pf['bfefrmtrm']}% · "
            f"분기누적 {pf['thstrm_add']}%. → **비교기간 3개** 가용(전전기까지)."
        )
        A(f"- 통화: {mac['currency']}")
        A(f"- reprt_code: {mac['reprt_code']} (11011=사업보고서).")
        A("")
        nt = mac["notes"]
        A("### 5.5 주석 수집 현황")
        A("")
        A(
            f"- 주석 디렉터리 보유 회사연도: {nt['company_years_with_notes']:,} (CFS {nt['by_fs']['CFS']:,}·OFS {nt['by_fs']['OFS']:,})."
        )
        A(f"- 디렉터리당 파일수 분포: {nt['files_per_dir_bucket']}")
    else:
        A("## 5. 거시 구조 인벤토리")
        A("")
        A("_audit_macro_structure.json 미생성 — 거시 하니스 실행 후 재생성.")
    A("")

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(
        f"신규분류후보={len(new_cand)}종 · 타표문강등={len(demoted)}종 · 확장계정={len(ext)} -> {OUT}"
    )
    print("\n[신규분류 가능 상위 25]")
    for c in new_cand[:25]:
        sj = max(c["sj"], key=c["sj"].get) if c.get("sj") else ""
        print(f"  {c['n']:>6}행 {won(c['amax']):>10} [{sj}] {c['account_id']}")


if __name__ == "__main__":
    main()
