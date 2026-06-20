"""NEW 블록을 canonical_accounts 섹션 끝(sce_equity_components 앞)에 정밀 삽입.

한글 보존: utf-8·LF 고정, 기존 줄은 한 글자도 변경하지 않고 블록만 삽입. 삽입 후 호출측에서
git diff(추가만)·mojibake·yaml 로드·canonical 수를 검증한다.
"""

from __future__ import annotations

from pathlib import Path

CFG = Path("config/canonical_accounts.yaml")
BLOCK = Path("data/backtest/_da_register_block.yaml")

text = CFG.read_text(encoding="utf-8")
lines = text.split("\n")

# canonical_accounts 섹션 끝 = D-D SCE 주석 블록 시작 직전
anchor = None
for i, ln in enumerate(lines):
    if ln.startswith("# === D-D: SCE"):
        anchor = i
        break
if anchor is None:
    raise SystemExit("앵커(# === D-D: SCE) 못 찾음 — 중단")

block = BLOCK.read_text(encoding="utf-8").rstrip("\n")
header = [
    "  # === D-A Chunk: ≥50사 보편 표준계정 일괄 등록(account_id 우선매칭) ===",
    "  # 생성: data/backtest/_da_register_gen.py(stem 구동·이질병합 차단·충돌0).",
]
insert = header + block.split("\n") + [""]
new_lines = lines[:anchor] + insert + lines[anchor:]
CFG.write_text("\n".join(new_lines), encoding="utf-8", newline="")
print(f"삽입 완료: {len(insert)}줄 @ line {anchor + 1} 앞")
