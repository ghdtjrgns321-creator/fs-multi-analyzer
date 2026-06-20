"""_da_merge_map.json의 account_id를 기존 canonical account_ids 블록에 삽입(영문 id, 한글 무수정).

각 canonical의 'account_ids:' 다음 첫 '- ' 라인 뒤에 누락 id를 삽입. LF·utf-8 보존.
"""

from __future__ import annotations

import json
from pathlib import Path

CFG = Path("config/canonical_accounts.yaml")
merge = json.loads(Path("data/backtest/_da_merge_map.json").read_text(encoding="utf-8"))

text = CFG.read_text(encoding="utf-8")
lines = text.split("\n")

added = 0
for canon, ids in merge.items():
    # canonical 헤더 라인 찾기
    hdr = None
    for i, ln in enumerate(lines):
        if ln == f"  {canon}:":
            hdr = i
            break
    if hdr is None:
        print(f"  [SKIP] '{canon}' 헤더 못 찾음")
        continue
    # account_ids: 라인 찾기(헤더 이후 가까운)
    aidx = None
    for i in range(hdr, min(hdr + 8, len(lines))):
        if lines[i].strip() == "account_ids:":
            aidx = i
            break
    if aidx is None:
        print(f"  [SKIP] '{canon}' account_ids 없음")
        continue
    # 이미 있는 id 모음(블록 끝까지 '- ' 라인)
    existing = set()
    end = aidx + 1
    while end < len(lines) and lines[end].lstrip().startswith("- "):
        existing.add(lines[end].strip()[2:])
        end += 1
    new_id_lines = [f"      - {i}" for i in ids if i not in existing]
    if not new_id_lines:
        continue
    lines[end:end] = new_id_lines
    added += len(new_id_lines)
    print(f"  [OK] {canon} += {[i for i in ids if i not in existing]}")

CFG.write_text("\n".join(lines), encoding="utf-8", newline="")
print(f"총 {added}개 account_id 삽입")
