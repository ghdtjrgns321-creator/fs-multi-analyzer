"""신규 등록 블록의 alias/account_id 충돌 전수검사(읽기전용).

위험: _by_alias는 dict comprehension이라 같은 alias는 나중(=신규) 것이 기존을 덮음.
신규 alias가 기존 canonical의 alias와 충돌하면 기존 라벨매핑이 바뀌는 회귀.
account_id는 register_gen이 미등록만 골랐으나 재확인.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from src.normalize.config import normalize_label

CFG = Path("config/canonical_accounts.yaml")
BLOCK = Path("data/backtest/_da_register_block.yaml")

cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))["canonical_accounts"]
# 신규 블록을 임시로 파싱(들여쓰기가 canonical_accounts 하위와 동일하므로 래핑)
block_text = "canonical_accounts:\n" + BLOCK.read_text(encoding="utf-8")
new = yaml.safe_load(block_text)["canonical_accounts"]

existing_alias: dict[str, str] = {}
existing_id: dict[str, str] = {}
for name, body in cfg.items():
    for al in body.get("aliases", []) or []:
        existing_alias[normalize_label(al)] = name
    for aid in body.get("account_ids", []) or []:
        existing_id[aid] = name

alias_collisions = []
id_collisions = []
new_alias_seen: dict[str, str] = {}
for name, body in new.items():
    for al in body.get("aliases", []) or []:
        nl = normalize_label(al)
        if nl in existing_alias and existing_alias[nl] != name:
            alias_collisions.append((al, existing_alias[nl], name))
        if nl in new_alias_seen and new_alias_seen[nl] != name:
            alias_collisions.append((al, f"[NEW]{new_alias_seen[nl]}", name))
        new_alias_seen[nl] = name
    for aid in body.get("account_ids", []) or []:
        if aid in existing_id and existing_id[aid] != name:
            id_collisions.append((aid, existing_id[aid], name))

print(f"신규 canonical: {len(new)}개")
print(f"=== alias 충돌(기존/신규 라벨 겹침): {len(alias_collisions)}건 ===")
for al, old, newn in alias_collisions:
    print(f"  '{al}'  기존[{old}]  ←덮어씀―  신규[{newn}]")
print(f"\n=== account_id 충돌(이미 다른 canonical 보유): {len(id_collisions)}건 ===")
for aid, old, newn in id_collisions:
    print(f"  {aid}  기존[{old}]  vs  신규[{newn}]")
if not alias_collisions and not id_collisions:
    print("\n충돌 0 — 안전하게 삽입 가능.")
