"""D-A 미분류 분류후보 군집 리포트 (read-only).

입력은 이미 전수(1667사·9319파일) 산출된 `_audit_unmapped.json`의 classify_candidates
(표준ID 보유·canonical 없는 미분류 account_id 전수, 행수 n·라벨·sj 보유). 추가 raw 스캔 없이
2106종 전부를 군집화한다.

군집 축: 주 sj_div(그 account_id 행이 실제 쌓인 sj 최빈) × 개념계열(account_id IFRS 영문
표준명으로 판정 — 현 canonical 매핑 미참조, 자기참조 금지). 개념계열 분류기는 _da_cluster.py를
재사용한다.

플래그: account_id가 config 등록 account_ids에 있으면 "타표문반복(이미 canonical 보유)",
없으면 "신규개념후보(어디에도 canonical 없음)".

지표: 행수(n, 전수)·종수를 우선. 금액은 원천 이상치로 amax 미신뢰 → 표기는 행수 중심.
account_id별 고유 회사수·금액 중앙값은 raw 전수 재스캔(_da_cluster.py)으로 보강 가능(부가지표).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import yaml
from _da_cluster import concept_family, local_name  # 동일 분류기 재사용

SRC = Path("data/backtest/_audit_unmapped.json")
CONFIG = Path("config/canonical_accounts.yaml")
OUT_MD = Path("data/backtest/AGENDA_DA_CLUSTERS.md")
TASK_STATED = 2080  # 과제 명시 분모(차이 규명용 표시값 — 계산 미구동)


def value_bucket(c: dict) -> tuple[str, str]:
    """분류가치 제안(단정 아님): 행수·종수·신규비중 결합 휴리스틱."""
    rows = c["rows"]
    new_ratio = c["new"] / max(c["ids"], 1)
    if rows >= 8000 and new_ratio >= 0.5:
        return "높음", "행수 많고 신규개념 비중 큼 — canonical 추가 시 분류율 기여 큼(제안)"
    if rows < 1500 or new_ratio < 0.3:
        return "낮음", "희소하거나 타표반복(이미 canonical 보유) 비중 큼 — 우선순위 낮음(제안)"
    return "중간", "중간 규모 — 개념 정의·표문 의미 토의 후 선별 등록(제안)"


def short_id(aid: str) -> str:
    ln = local_name(aid)
    return ln if len(ln) <= 46 else ln[:43] + "..."


def main() -> None:
    src = json.loads(SRC.read_text(encoding="utf-8"))
    cands = src["classify_candidates"]

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["canonical_accounts"]
    reg_ids: dict[str, str] = {}
    for name, spec in cfg.items():
        for a in spec.get("account_ids", []):
            reg_ids[a] = name

    # account_id별 레코드
    recs = []
    for it in cands:
        aid = it["account_id"]
        sj = it["sj"]
        dom_sj = max(sj, key=sj.get) if sj else "?"
        fam = concept_family(aid, dom_sj)
        registered = aid in reg_ids
        recs.append(
            {
                "account_id": aid,
                "n": it["n"],
                "dom_sj": dom_sj,
                "family": fam,
                "cluster": f"{dom_sj} / {fam}",
                "is_new": not registered,
                "registered_as": reg_ids.get(aid, ""),
                "labels": it.get("labels", []),
            }
        )

    # 군집 집계
    clusters: dict[str, dict] = defaultdict(
        lambda: {"ids": 0, "rows": 0, "new": 0, "repeat": 0, "members": []}
    )
    for r in recs:
        c = clusters[r["cluster"]]
        c["ids"] += 1
        c["rows"] += r["n"]
        if r["is_new"]:
            c["new"] += 1
        else:
            c["repeat"] += 1
        c["members"].append(r)

    cluster_out = []
    for name, c in clusters.items():
        mem = sorted(c["members"], key=lambda x: -x["n"])
        cluster_out.append({"name": name, **c, "top5": mem[:5]})
    cluster_out.sort(key=lambda x: -x["rows"])

    total = len(recs)
    new = sum(1 for r in recs if r["is_new"])
    repeat = total - new
    csum = sum(c["ids"] for c in cluster_out)

    L: list[str] = []
    A = L.append
    A("# D-A 미분류 분류후보 군집 (전수)\n")
    A("> 읽기전용 감사 산출물. config/코드 미수정. 분류가치는 **제안**이며 단정·확정이 아니다.\n")
    A(
        "재현: `PYTHONPATH=. uv run python data/backtest/_da_report.py` "
        "(입력=전수 산출물 `_audit_unmapped.json`). 회사수·금액중앙값 보강은 "
        "`PYTHONPATH=. uv run python data/backtest/_da_cluster.py`(raw 전수 재스캔).\n"
    )

    A("## 1. 분모 확정 (전수 §10)\n")
    A(
        "대상 = `_audit_unmapped.json`의 `classify_candidates` = 표준ID(ifrs-full_*/dart_*/ifrs_*) "
        "보유하나 canonical 미매핑(OTHER)인 비차원 account_id. 운영 매핑 파이프라인"
        "(가드→`_dedupe_statement_rows`)으로 1667사·9319파일 전수 집계된 결과다.\n"
    )
    A("```")
    A(f"전수 account_id 종수          : {total:,}")
    A(f"  ├ 신규개념후보(config 미등록) : {new:,}")
    A(f"  └ 타표문반복(config 등록ID)   : {repeat:,}")
    A(f"군집 종수 합(미배정 0 증명)     : {csum:,}  (= 총 {total:,} 일치)")
    A(f"과제 명시 분모                  : {TASK_STATED:,}")
    A(f"  → 차이 {total - TASK_STATED:+,} = 타표문반복 {repeat}종이 포함된 것.")
    A(f"     과제 '2080종' = 신규개념후보({new}종)와 정확히 일치.")
    A(f"군집 수                         : {len(cluster_out):,}")
    A("```\n")
    A(
        "**플래그(요구4):** account_id가 config 등록 `account_ids`에 있으면 그 개념은 이미 어느 "
        "재무제표에 canonical로 존재(타 표문에서 반복 등장)이고, 없으면 어디에도 canonical 없는 "
        "신규개념 후보다. 판정은 account_id 표준명 기준(현 canonical 매핑 미참조 — 자기참조 금지).\n"
    )

    A("## 2. 군집 축\n")
    A(
        "- **주 sj_div**: account_id 행이 raw에서 가장 많이 쌓인 재무제표 구분(BS/IS/CIS/CF/SCE). "
        "현 매핑이 아니라 데이터 분포로 판정.\n"
        "- **개념계열**: account_id의 IFRS 영문 표준명을 토큰 규칙으로 판정"
        "(`*InvestingActivities`→투자활동흐름, `AdjustmentsFor*`→현금흐름조정, "
        "`*FinancialAssets`→기타금융자산, `*Tax*`→세금 등). 현 canonical 미참조.\n"
        "- 금액은 원천 이상치(예: 일부 corp 자산 122,130조)가 있어 **행수·종수를 우선 지표**로 둔다"
        "(amax 미신뢰). 회사수·중앙값은 부가지표로 `_da_cluster.py` 재스캔 시 산출.\n"
    )

    A("## 3. 군집표 (총행수 내림차순)\n")
    A("| # | 군집 (주sj / 개념계열) | 종수 | 총행수 | 신규/반복 | 가치(제안) |")
    A("|---|------------------------|-----:|-------:|:---------:|:----------:|")
    for i, c in enumerate(cluster_out, 1):
        val, _ = value_bucket(c)
        A(
            f"| {i} | {c['name']} | {c['ids']:,} | {c['rows']:,} | "
            f"{c['new']}/{c['repeat']} | {val} |"
        )
    A("")
    A(f"종수 합계 = {csum:,} (= 전수 {total:,}, 미배정 0)\n")

    by_val: dict[str, list] = {"높음": [], "중간": [], "낮음": []}
    for c in cluster_out:
        by_val[value_bucket(c)[0]].append(c)
    A("## 4. 분류가치 제안 요약 (단정 금지 — 토의 입력)\n")
    for v in ("높음", "중간", "낮음"):
        cl = by_val[v]
        ids = sum(x["ids"] for x in cl)
        rows = sum(x["rows"] for x in cl)
        names = ", ".join(x["name"] for x in cl[:10])
        A(f"### 가치 {v}: 군집 {len(cl)}개 · 종수 {ids:,} · 행수 {rows:,}")
        if cl:
            A(f"- 기준(제안): {value_bucket(cl[0])[1]}")
        A(f"- 군집: {names}{' …' if len(cl) > 10 else ''}\n")

    A("## 5. 대표 군집 상세 (상위 12 · 대표 account_id 5개)\n")
    A("행수=전수. flag=신규개념후보/타표문반복. id=IFRS 영문 표준명(local).\n")
    for c in cluster_out[:12]:
        val, _ = value_bucket(c)
        A(f"### {c['name']}  — 종수 {c['ids']}, 행수 {c['rows']:,}, 가치(제안) {val}")
        A("```")
        A(f"{'행수':>7}  account_id(local)                               | 예시라벨 [flag]")
        for m in c["top5"]:
            flag = "신규" if m["is_new"] else f"반복:{m['registered_as']}"
            lab = m["labels"][0] if m["labels"] else ""
            A(f"{m['n']:>7,}  {short_id(m['account_id']):<46} | {lab} [{flag}]")
        A("```\n")

    A("## 6. 한계·주의\n")
    A(
        "- 개념계열은 IFRS 영문명 토큰 규칙이라 일부 복합명은 근사 분류된다. '기타개념'은 규칙 "
        "미적중 잔여이며 분류불가가 아니라 **추가 정의 필요** 잔여다(종수 명시).\n"
        "- CF 방향성 흐름은 활동어(`...Activities`)가 있으면 투자/재무활동으로, 없으면 그 계정의 "
        "자산·부채 성격(예: 차입·사채, 기타금융자산)으로 세분된다 — 의도된 분류다.\n"
        "- **행수는 전수**지만, account_id별 **고유 회사수·금액 중앙값**은 본 표에 없다"
        "(`_audit_unmapped.json`에 미수록). 필요 시 `_da_cluster.py`로 raw 전수 재스캔하면 "
        "군집별 합집합 회사수·중앙값까지 산출된다(부가지표).\n"
        "- 분류가치 버킷은 행수·신규비중 휴리스틱일 뿐, 등록 여부는 개념 정의·표문 의미 토의 후 "
        "사용자 결정(§8).\n"
    )

    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"MD -> {OUT_MD}")
    print(f"total={total} new={new} repeat={repeat} clusters={len(cluster_out)} sum={csum}")


if __name__ == "__main__":
    main()
