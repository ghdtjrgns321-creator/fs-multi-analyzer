"""D-A ≥50사 → canonical 등록 생성(v3: account_id stem 구동·이질병합 차단).

설계 원칙(이질병합 재발 방지):
- canonical 정체성은 **account_id 영문 stem**(prefix 제거·소문자)으로 구동. 한글 라벨은 표시용.
  이유: 회사들이 유동/비유동/총계 파생상품을 모두 '파생상품부채'로 라벨링 → 라벨로는 구분 불가.
- stem 그룹핑: namespace 변형(ifrs-full_/ifrs_/dart_·대소문자)만 한 canonical로 병합(안전).
- 유동/비유동은 stem의 current/noncurrent 토큰으로 일반 분리(특정 계정 하드코딩 없음).
- 기존 canonical 병합은 (a) stem 일치 또는 (b) 생성이름이 기존 '이름'과 정확 일치일 때만.
  기존의 **포괄적 alias**(예: '파생상품부채')로는 병합하지 않음(이질병합 차단).
- NEW의 alias는 충돌 시 드롭(account_id 우선매칭으로 분류되므로 무해). 충돌 0 보장.

재현: PYTHONPATH=. uv run python data/backtest/_da_register_gen.py
산출: _da_register_block.yaml(NEW) + _da_merge_map.json(기존 병합).
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

import yaml

from src.normalize.config import normalize_label

CFG = Path("config/canonical_accounts.yaml")
THRESHOLD = 50
HIGH = {
    "CF / 현금흐름조정",
    "CF / 기타금융자산",
    "CF / 현금잔액·증감·환율효과",
    "SCE / 자본구성요소",
    "BS / 기타금융자산",
    "CF / 차입·사채",
    "CF / 투자활동흐름",
    "BS / 기타금융부채",
    "BS / 자본구성요소",
    "CF / 재무활동흐름",
    "BS / 기타비금융부채",
    "CF / 비금융자산(유형·무형·재고)",
    "CF / 관계·종속기업투자",
    "BS / 기타비금융자산",
}
SJ = {"CF": "CF", "BS": "BS", "SCE": "SCE", "IS": "IS", "CIS": "CIS"}
PREFIXES = ("ifrs-full_", "ifrs_", "dart_")


def stem(aid: str) -> str:
    s = aid
    for p in PREFIXES:
        if s.startswith(p):
            s = s[len(p) :]
            break
    return s.lower()


def variants(aid: str) -> list[str]:
    out = [aid]
    if aid.startswith("ifrs-full_"):
        out.append("ifrs_" + aid[len("ifrs-full_") :])
    return out


def primary_label(a: dict) -> str:
    labs = [
        " ".join(str(x).split()).strip() for x in (a.get("labels") or [a.get("label", "")]) if x
    ]
    return labs[0] if labs else ""


# 기존 등록 상태
cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))["canonical_accounts"]
existing_stem: dict[str, str] = {}  # stem -> canonical name
existing_name_norm: dict[str, str] = {}  # normalize(name) -> name
existing_alias_norm: set[str] = set()  # normalize(name|alias) 전체(충돌검사용)
existing_ids: set[str] = set()
for name, body in cfg.items():
    existing_name_norm[normalize_label(name)] = name
    existing_alias_norm.add(normalize_label(name))
    for al in body.get("aliases", []) or []:
        existing_alias_norm.add(normalize_label(al))
    for aid in body.get("account_ids", []) or []:
        existing_ids.add(aid)
        if aid.startswith("ifrs-full_"):
            existing_ids.add("ifrs_" + aid[len("ifrs-full_") :])
        existing_stem.setdefault(stem(aid), name)


def is_registered(aid: str) -> bool:
    aid2 = ("ifrs_" + aid[len("ifrs-full_") :]) if aid.startswith("ifrs-full_") else aid
    return aid in existing_ids or aid2 in existing_ids


ALL_MODE = os.environ.get("P1_ALL") == "1"  # 전수: HIGH·임계 해제, 전 표준ID 등록

d = json.load(open("data/backtest/_da_cluster.json", encoding="utf-8"))
targets = [
    a
    for a in d["accounts"]
    if a["flag"] == "신규개념후보"
    and (ALL_MODE or a["cluster"] in HIGH)
    and (ALL_MODE or a["n_companies"] >= THRESHOLD)
    and not is_registered(a["account_id"])
]
print(f"대상: {len(targets)}종 (전수모드={ALL_MODE})")

# 1) stem으로 그룹핑(namespace 변형 통합)
groups: dict[str, dict] = {}
for a in targets:
    st = stem(a["account_id"])
    sj = SJ[a["cluster"].split(" / ")[0]]
    g = groups.setdefault(
        st, {"ids": [], "rows": 0, "comps": 0, "label": primary_label(a), "sj": sj}
    )
    for v in variants(a["account_id"]):
        if v not in g["ids"]:
            g["ids"].append(v)
    g["rows"] += a["n"]
    g["comps"] = max(g["comps"], a["n_companies"])


def disambiguated_name(st: str, label: str) -> str:
    # 유동/비유동을 stem 토큰으로 일반 분리(라벨이 이미 명시하면 그대로).
    base = label or st
    if "noncurrent" in st and "비유동" not in base and "유동" not in base:
        return "비유동" + base
    if "current" in st and "noncurrent" not in st and "유동" not in base:
        return "유동" + base
    return base


# 2) 기존 병합 vs 신규 분기
merge_map: dict[str, list[str]] = defaultdict(list)
new_groups: list[dict] = []
for st, g in groups.items():
    name = disambiguated_name(st, g["label"])
    # 병합은 stem 일치(같은 개념 namespace 변형)만. 이름매칭 병합은 statement-cross(지분법
    # IS↔CF)·CF섹션-cross(배당금 영업↔투자)를 유발해 제거. 이름 겹치면 NEW로 분리(near-dup 허용).
    tgt = existing_stem.get(st)
    if tgt:
        for i in g["ids"]:
            if i not in merge_map[tgt]:
                merge_map[tgt].append(i)
    else:
        new_groups.append({**g, "stem": st, "name": name})

# 3) NEW 이름 중복 해소(같은 이름 다수 stem) + alias 충돌 드롭
new_entries = []
name_used = set(existing_name_norm.values())
new_alias_used: set[str] = set()
for g in sorted(new_groups, key=lambda x: -x["rows"]):
    name = g["name"]
    if name in name_used:
        cand = f"{name}({g['sj']})"
        k = 2
        while cand in name_used:
            cand = f"{name}({g['sj']}{k})"
            k += 1
        name = cand
    name_used.add(name)
    # alias: 원라벨이 기존/신규 alias와 충돌하면 드롭(account_id로만 분류 → 무해)
    al = g["label"]
    aln = normalize_label(al)
    aliases = []
    if (
        al
        and aln not in existing_alias_norm
        and aln not in new_alias_used
        and aln == normalize_label(name)
    ):
        aliases = [al]
        new_alias_used.add(aln)
    new_entries.append((name, g["sj"], g["ids"], aliases, g["rows"], g["comps"]))

n_merge_ids = sum(len(v) for v in merge_map.values())
print(f"→ MERGE: 기존 {len(merge_map)}개 canonical에 account_id {n_merge_ids}개 추가")
print(f"→ NEW  : 신규 canonical {len(new_entries)}개\n")

print("=== MERGE 맵 ===")
for tgt, ids in sorted(merge_map.items()):
    print(f"  [{tgt}] += {ids}")

print("\n=== NEW(statement별) ===")
bystmt = defaultdict(list)
for e in new_entries:
    bystmt[e[1]].append(e)
for sj in ("CF", "BS", "SCE", "IS", "CIS"):
    if sj in bystmt:
        print(f"\n--- {sj}: {len(bystmt[sj])}개 ---")
        for name, _sj, ids, aliases, rows, comps in bystmt[sj]:
            amark = "" if aliases else "  [alias없음:account_id매칭]"
            print(f"  [{comps}사 {rows}행] {name}  ({len(ids)}ids){amark}")


def yq(s: str) -> str:
    if any(c in s for c in ',:[]{}#&*!|>%@`"') or s != s.strip():
        return '"' + s.replace('"', '\\"') + '"'
    return s


Path("data/backtest/_da_merge_map.json").write_text(
    json.dumps(merge_map, ensure_ascii=False, indent=2), encoding="utf-8"
)
lines: list[str] = []
for name, sj, ids, aliases, _rows, _comps in new_entries:
    lines.append(f"  {yq(name)}:")
    lines.append(f"    statement: {sj}")
    lines.append("    account_ids:")
    for i in ids:
        lines.append(f"      - {i}")
    if aliases:
        lines.append(f"    aliases: [{', '.join(yq(a) for a in aliases)}]")
    else:
        lines.append("    aliases: []")
Path("data/backtest/_da_register_block.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\nNEW 블록 → _da_register_block.yaml ({len(new_entries)}개)")
print(f"MERGE 맵 → _da_merge_map.json ({len(merge_map)}개)")
