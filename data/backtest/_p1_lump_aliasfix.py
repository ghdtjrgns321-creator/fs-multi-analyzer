"""lump 분리 후 alias 복원 — 각 lump primary에 원래 alias 전부, 나머지는 account_id 전용.

label-only(account_id 공백) 행이 primary로 fallback되게 유지. account_id 행은 분리된 정밀 canonical로.
라인기반 config 수정(한글 보존).
"""

from __future__ import annotations

from pathlib import Path

CFG = Path("config/canonical_accounts.yaml")

# canonical명 → 복원할 aliases(빈 리스트면 account_id 전용)
PRIMARY = {
    "관계기업투자": [
        "관계기업투자",
        "관계기업 및 공동기업 투자",
        "관계기업및공동기업 투자",
        "관계기업및공동기업투자",
        "관계기업및공동기업투자주식",
        "종속기업, 관계기업 및 공동기업투자",
        "종속기업및관계기업투자주식",
        "관계기업투자주식",
    ],
    "대손상각비": ["대손상각비"],
    "기타금융자산취득": [
        "기타금융자산의 취득",
        "기타유동금융자산의 취득",
        "기타비유동금융자산의 취득",
    ],
    "기타금융자산처분": [
        "기타금융자산의 처분",
        "기타유동금융자산의 처분",
        "기타비유동금융자산의 처분",
    ],
    "연결대상범위변동": [
        "연결실체의 변동",
        "연결실체내 자본거래 등",
        "회계정책변경에 따른 증가(감소)",
        "전환사채 조기상환",
        "신주인수권 행사",
        "기타자본의 증가",
        "기타자본의 감소",
        "연결대상범위의 변동",
    ],
    "FVOCI지분상품평가손익": [
        "기타포괄손익-공정가치금융자산평가손익",
        "기타포괄손익-공정가치 측정 금융자산 평가손익",
        "매도가능금융상품평가손익",
    ],
    "해외사업환산손익": ["해외사업장환산외환차이", "해외사업환산손익", "해외사업환산손익(손실)"],
    "지분법기타포괄손익재분류가능": [
        "지분법자본변동",
        "지분법기타포괄손익",
        "지분법이익잉여금",
        "지분법기타포괄손익(재분류가능)",
    ],
}
# 분리 sibling: account_id 전용(alias [])
SIBLINGS = [
    "지분법적용투자",
    "종속관계공동기업투자",
    "기타대손상각비",
    "유동기타금융자산취득",
    "비유동기타금융자산취득",
    "유동기타금융자산처분",
    "비유동기타금융자산처분",
    "내부거래취득",
    "회계정책변경효과",
    "FVOCI적립금변동",
    "환율변동효과",
    "지분법기타포괄손익재분류불가능",
]


def yq(t: str) -> str:
    if any(c in t for c in ',:[]{}#&*!|>%@`"'):
        return '"' + t.replace('"', '\\"') + '"'
    return t


lines = CFG.read_text(encoding="utf-8").split("\n")


def set_aliases(name: str, aliases: list[str]) -> bool:
    # canonical 블록의 aliases: 라인 찾아 교체
    start = None
    for i, ln in enumerate(lines):
        if ln == f"  {name}:":
            start = i
            break
    if start is None:
        return False
    for j in range(start + 1, min(start + 12, len(lines))):
        if lines[j].lstrip().startswith("aliases:"):
            lines[j] = f"    aliases: [{', '.join(yq(a) for a in aliases)}]"
            return True
    return False


done = 0
for name, al in PRIMARY.items():
    if set_aliases(name, al):
        done += 1
    else:
        print(f"[MISS] {name}")
for name in SIBLINGS:
    if set_aliases(name, []):
        done += 1
    else:
        print(f"[MISS] {name}")

CFG.write_text("\n".join(lines), encoding="utf-8", newline="")
print(f"alias 복원 {done}개 canonical")
