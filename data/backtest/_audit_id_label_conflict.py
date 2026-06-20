"""N5 전수 모순 측정 — id가 가리키는 canonical ≠ label 정확 alias canonical인 행을 수집 전체에서
스캔해 건수·금액 분포·3패턴 분류표를 md로 산출한다(2단계 결정의 입력, 매핑 변경은 별도 회차).

전수 원칙(§10): 재정규화 상태와 무관하게 raw finstate_all_{CFS,OFS}.csv에 production 매퍼를 직접
적용한다(매퍼 미경유 비교가 아니라, 매퍼 자신의 모순 플래그를 전수 집계). 패턴:
  ① 폐지 개념: account_id가 IFRS9 이후 폐지된 분류(HeldToMaturity·AvailableForSale) 토큰 보유.
  ② 유동/비유동 계열 차이: id·label canonical이 유동/비유동/장단기 접두만 다른 같은 계열.
  ③ 완전 이질: 그 외(서로 다른 계정 family).

재현: PYTHONPATH=. uv run python data/backtest/_audit_id_label_conflict.py
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from src.normalize.config import load_canonical_accounts, normalize_label
from src.normalize.mapper import ID_LABEL_CONFLICT, AccountMapper

ROOT = Path("data/companies")
CONFIG = Path("config/canonical_accounts.yaml")
OUT = Path("data/backtest/ID_LABEL_CONFLICT_AUDIT.md")
M = 1_000_000

# 폐지 개념 토큰(IFRS9 2018 이후 폐지: 만기보유·매도가능). account_id 소문자 비교.
_ABOLISHED = ("heldtomaturity", "availableforsale")
# 유동/비유동 계열 판정용 접두 토큰(제거 후 root 비교).
_SERIES_TOKENS = ["비유동", "유동성", "유동", "장기", "단기", "순", "및기타", "기타", "비"]


def _root(canonical: str) -> str:
    """canonical에서 유동/비유동·장단기 접두를 제거한 root(계열 비교용)."""
    r = canonical
    for tok in _SERIES_TOKENS:
        r = r.replace(tok, "")
    return r


def classify(account_id: str, id_canon: str, label_canon: str) -> str:
    aid = account_id.lower()
    if any(tok in aid for tok in _ABOLISHED):
        return "①폐지개념"
    ri, rl = _root(id_canon), _root(label_canon)
    # root가 서로 포함관계이고 비지 않으면 같은 계열(유동/비유동 차이)로 본다.
    if ri and rl and (ri in rl or rl in ri):
        return "②유동비유동계열"
    return "③완전이질"


def main() -> None:
    accounts = load_canonical_accounts(CONFIG)
    mapper = AccountMapper(accounts)
    # label 정확 alias → canonical (id-label 모순 시 label쪽 canonical 식별용)
    by_alias = {normalize_label(a): acc.name for acc in accounts for a in acc.aliases}

    conflicts: list[dict] = []
    n_rows = 0
    n_company_years = 0
    corps = sorted(d for d in ROOT.iterdir() if d.is_dir() and d.name.isdigit())
    for cdir in corps:
        for ydir in sorted(p for p in cdir.iterdir() if p.is_dir() and p.name.isdigit()):
            seen_year = False
            for fs in ("CFS", "OFS"):
                p = ydir / "raw" / f"finstate_all_{fs}.csv"
                if not p.exists() or p.stat().st_size <= 5:
                    continue
                seen_year = True
                with p.open(encoding="utf-8-sig") as f:
                    for r in csv.DictReader(f):
                        n_rows += 1
                        aid = str(r.get("account_id", ""))
                        label = str(r.get("account_nm", ""))
                        res = mapper.map_row({"account_id": aid, "account_nm": label})
                        if res.mapping_status != ID_LABEL_CONFLICT:
                            continue
                        label_canon = by_alias.get(normalize_label(label), "?")
                        amt = (r.get("thstrm_amount") or "").replace(",", "").strip()
                        try:
                            amount = float(amt)
                        except ValueError:
                            amount = 0.0
                        conflicts.append(
                            {
                                "corp": cdir.name,
                                "year": ydir.name,
                                "fs": fs,
                                "sj": r.get("sj_div", ""),
                                "account_id": aid,
                                "label": label,
                                "id_canon": res.canonical,
                                "label_canon": label_canon,
                                "amount": amount,
                                "pattern": classify(aid, res.canonical, label_canon),
                            }
                        )
            if seen_year:
                n_company_years += 1

    _write_report(conflicts, n_rows, n_company_years, len(corps))


def _write_report(conflicts: list[dict], n_rows: int, n_cy: int, n_corp: int) -> None:
    by_pattern: Counter = Counter(c["pattern"] for c in conflicts)
    pair_counter: Counter = Counter(
        f"{c['id_canon']} ⟸id|label⟹ {c['label_canon']}" for c in conflicts
    )
    total_abs = sum(abs(c["amount"]) for c in conflicts)

    lines = [
        "# id-label 의미 모순 전수 측정 (N5 1단계 — 측정만, 매핑 변경 없음)",
        "",
        "> production 매퍼(map_row)의 id_label_conflict 플래그를 수집 전체 raw에 직접 적용해 집계.",
        "> 매핑은 id-first 유지(무회귀). 본 측정이 2단계(규칙 결정)의 입력이다.",
        "",
        "## 요약",
        f"- 스캔: {n_corp}개 회사 / {n_cy} 회사연도(raw 보유) / 본문 행 {n_rows:,}",
        f"- 모순 행: **{len(conflicts):,}건** (금액 |합| {total_abs / M:,.0f}백만)",
        "- 패턴 분포: " + " · ".join(f"{k} {v:,}" for k, v in by_pattern.most_common()),
        f"- 고유 canonical 쌍: {len(pair_counter):,}종",
        "",
        "## 3패턴 분류표",
        "",
        "| 패턴 | 건수 | 의미 |",
        "|------|------|------|",
        f"| ①폐지개념 | {by_pattern.get('①폐지개념', 0):,} | IFRS9 폐지 분류(HTM·AFS) id에 다른 실질 신고 |",
        f"| ②유동비유동계열 | {by_pattern.get('②유동비유동계열', 0):,} | id·label이 유동/비유동·장단기 접두만 다른 같은 계열 |",
        f"| ③완전이질 | {by_pattern.get('③완전이질', 0):,} | 서로 다른 계정 family(진짜 의미 오염 후보) |",
        "",
        "## 상위 모순 canonical 쌍 (id ⟸ | label ⟹, 빈도순 30)",
        "",
        "| 빈도 | id canonical | label canonical |",
        "|------|--------------|-----------------|",
    ]
    for pair, cnt in pair_counter.most_common(30):
        idc, labc = pair.split(" ⟸id|label⟹ ")
        lines.append(f"| {cnt} | {idc} | {labc} |")

    for pat in ["①폐지개념", "②유동비유동계열", "③완전이질"]:
        sub = [c for c in conflicts if c["pattern"] == pat]
        sub = sorted(sub, key=lambda c: abs(c["amount"]), reverse=True)[:12]
        lines += ["", f"## {pat} — 금액 상위 12 예시", ""]
        lines.append(
            "| 회사/연도 | fs/sj | label | account_id | id→canonical | label→canonical | 금액(백만) |"
        )
        lines.append("|---|---|---|---|---|---|---|")
        for c in sub:
            lines.append(
                f"| {c['corp']}/{c['year']} | {c['fs']}/{c['sj']} | {c['label'][:20]} | "
                f"{c['account_id'][:40]} | {c['id_canon']} | {c['label_canon']} | {c['amount'] / M:,.0f} |"
            )

    lines += [
        "",
        "## 2단계 후보 규칙 (별도 회차 — 본 측정 보고 후 사용자 결정)",
        "- ⓐ ①폐지개념 id → label 우선(안전: 폐지 id는 낡은 태깅 증거).",
        "- ⓑ label 정확 alias 일치 시 label 우선.",
        "- ⓒ 미해결 모순 → '기타 중요 계정' 강등+플래그.",
        "- 측정 리포트 없이 선반영하지 않는다(매핑 동작 변경은 무회귀 검증 동반).",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"모순 {len(conflicts):,}건 · {OUT} 작성")
    print("패턴:", dict(by_pattern))


if __name__ == "__main__":
    main()
