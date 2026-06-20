"""옵션(a) 정밀 판별자 전수 정밀검증 — 핵심명사 비교로 진짜오매핑 vs 동의어 분리.

가설: within/cross 무관, id-canonical과 label-canonical의 **핵심명사가 다르면 진짜 오매핑**
(투자부동산↔금융상품, 사채↔주식), **같으면 동의어**(유동리스부채↔리스부채, 단기미지급금↔미지급금).
수식어(유동/비유동/단기/장기/취득/처분/증감/발행/상환…)·괄호·로마수 접두를 떼고 core 비교.

목적: flip 후보 수 + 동의어 보존 수를 전수 측정하고, flip 후보를 출력해 정밀도(거짓양성률)를
사람이 검독하게 한다. 특히 영문 약어(FVPL=당기손익-공정가치측정금융자산) 같은 lexical 거짓양성을 드러낸다.

실행: PYTHONPATH=. uv run python data/backtest/_idlabel_precision_probe.py
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter

import duckdb

from config.settings import settings
from src.normalize.config import load_canonical_accounts, normalize_label
from src.normalize.mapper import AccountMapper

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHUNKS = os.path.join(ROOT, "data", "backtest", "_holistic_chunks.json")

# 핵심명사 추출 시 떼는 수식어(계정 실질이 아니라 상태·동작·기간 한정어).
QUALIFIERS = [
    "비유동",
    "유동",
    "단기",
    "장기",
    "순",
    "총",
    "기타",
    "의 증가(감소)",
    "의 감소(증가)",
    "증가(감소)",
    "감소(증가)",
    "증감",
    "의 증가",
    "의 감소",
    "증가",
    "감소",
    "취득",
    "처분",
    "발행",
    "상환",
    "지급",
    "수취",
    "수령",
    "납부",
    "환급",
    "전입",
    "환입",
    "의",
    "및",
]


def core(name: str) -> str:
    """수식어·괄호·로마수/번호 접두를 떼고 핵심명사만 남긴다."""
    n = re.sub(r"^\s*[IVXⅠ-ⅫA-Z0-9]+\s*[.．)]\s*", "", name)  # 'VIII.' 'IV.' '1)' 접두
    n = re.sub(r"\([^)]*\)", "", n)  # (유동)(BS)(CF) 괄호
    for q in QUALIFIERS:
        n = n.replace(q, "")
    return re.sub(r"\s+", "", n).strip()


def same_core(a: str, b: str) -> bool:
    """핵심명사 동일 또는 포함관계(짧은 쪽이 긴 쪽에 포함)면 동의어로 본다."""
    ca, cb = core(a), core(b)
    if not ca or not cb:
        return True  # core 소실 시 보수적으로 동의어(보존)
    if ca == cb:
        return True
    short, long = (ca, cb) if len(ca) <= len(cb) else (cb, ca)
    return len(short) >= 2 and short in long


def corpus_targets() -> list[tuple[str, str]]:
    chunks = json.load(open(CHUNKS, encoding="utf-8"))["chunks"]
    return [(c["corp"], str(y)) for ch in chunks for c in ch["companies"] for y in c["years"]]


def main() -> None:
    accts = load_canonical_accounts(settings.config_dir / "canonical_accounts.yaml")
    m = AccountMapper(accts)
    stmt = {a.name: a.statement for a in accts}
    compatible = {("IS", "CIS"), ("CIS", "IS")}

    flip: Counter = Counter()
    keep: Counter = Counter()
    for corp, year in corpus_targets():
        db = os.path.join(ROOT, "data", "companies", corp, year, "analysis.duckdb")
        if not os.path.exists(db):
            continue
        con = duckdb.connect(db, read_only=True)
        rows = con.execute(
            "SELECT canonical, label FROM normalized_financials "
            "WHERE mapping_status='id_label_conflict'"
        ).fetchall()
        con.close()
        for canon, lab in rows:
            bya = m._by_alias.get(normalize_label(lab))
            if not bya or bya.name == canon:
                continue
            si, sl = stmt.get(canon, ""), stmt.get(bya.name, "")
            # 표 호환: 같은 statement이거나 IS↔CIS. label측이 비호환이면 표호환성 심판 영역(이미 처리) → 제외
            if not (si == sl or (si, sl) in compatible):
                continue
            pair = (canon, bya.name)
            if same_core(canon, bya.name):
                keep[pair] += 1
            else:
                flip[pair] += 1

    print("[옵션(a) 정밀 판별자 — 핵심명사 비교]")
    print(f"  flip 후보(핵심명사 상이=진짜오매핑 후보): {len(flip)}쌍 / {sum(flip.values())}행")
    print(f"  동의어 보존(핵심명사 동일/포함): {len(keep)}쌍 / {sum(keep.values())}행")
    print()
    print(f"[flip 후보 전체 {len(flip)}쌍 — 사람 정밀검독용 (id_canonical ← label_canonical)]")
    for (c, lc), n in flip.most_common():
        print(f"  {n:4}  {c}  ←  {lc}   (core: {core(c)} | {core(lc)})")


if __name__ == "__main__":
    main()
