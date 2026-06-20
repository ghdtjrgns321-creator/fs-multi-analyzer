"""quirk 승격 스캐너 — 반복되는 회사 quirk를 전사 패턴 승격 후보로 검출.

배경: company_quirks.yaml은 회사 고유 정규화 이탈(alias_additions/account_overrides)을 임시·
예외로만 보유한다. 같은 quirk가 여러 회사에서 반복되면 그건 더 이상 "예외"가 아니라 일반
패턴이므로 canonical_accounts.yaml(전사 적용)로 승격하고 quirk에서 제거해야 한다(quirk 남용
방지). 이 스캐너가 회사 수를 세어 3개+ 반복 후보를 제시하고, 1~2회는 quirk 유지로 표기한다
(YAGNI — 소수 반복까지 일반화하지 않는다). 실제 승격(yaml 이관) 결정은 사람이 한다.

승격 임계: 같은 (canonical, alias) 또는 (account_id, force_canonical)이 **3개+ distinct 회사**.
corp_code는 데이터 키로 흐른다(코드 분기 하드코딩 아님 — load_company_quirks가 키로 순회).

실행: PYTHONPATH=. uv run python data/backtest/_quirk_promote_scan.py
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from src.normalize.config import load_company_quirks

ROOT = Path(__file__).resolve().parents[2]
QUIRKS = ROOT / "config" / "company_quirks.yaml"
PROMOTE_THRESHOLD = 3  # 3개+ distinct 회사에서 반복되면 전사 승격 후보(YAGNI: 1~2회는 quirk 유지)


def scan() -> dict:
    """company_quirks.yaml 전수 → alias_additions·account_overrides의 회사 반복도 집계."""
    quirks = load_company_quirks(QUIRKS)

    # 같은 quirk가 등장한 distinct corp_code 집합을 키별로 모은다(회사 수 기준 승격).
    alias_corps: dict[tuple[str, str], set[str]] = defaultdict(set)
    override_corps: dict[tuple[str, str], set[str]] = defaultdict(set)

    for corp_code, years in quirks.items():
        for _year, spec in years.items():
            for add in spec.get("alias_additions", []):
                key = (str(add.get("canonical", "")), str(add.get("alias", "")))
                alias_corps[key].add(corp_code)
            for ov in spec.get("account_overrides", []):
                key = (str(ov.get("account_id", "")), str(ov.get("force_canonical", "")))
                override_corps[key].add(corp_code)

    return {
        "n_companies": len(quirks),
        "alias_corps": alias_corps,
        "override_corps": override_corps,
    }


def _report(result: dict) -> None:
    alias_corps = result["alias_corps"]
    override_corps = result["override_corps"]

    print(f"[quirk 승격 스캔] company_quirks.yaml — quirk 보유 회사 {result['n_companies']}개")
    print(f"  승격 임계: {PROMOTE_THRESHOLD}개+ distinct 회사 반복 (1~2회는 quirk 유지)")
    print()

    # alias_additions 승격 후보
    alias_promote = sorted(
        ((k, c) for k, c in alias_corps.items() if len(c) >= PROMOTE_THRESHOLD),
        key=lambda kc: -len(kc[1]),
    )
    print(f"[alias_additions 승격 후보] {len(alias_promote)}건")
    for (canon, alias), corps in alias_promote:
        print(f"  ⮕ canonical={canon!r} alias={alias!r}  ({len(corps)}개사: {sorted(corps)})")
        print(
            f"     → 편집 지시: canonical_accounts.yaml의 {canon!r} aliases에 {alias!r} 추가"
            " 후 quirk 제거"
        )
    if not alias_promote:
        print("  (없음)")
    print()

    # account_overrides 승격 후보
    ov_promote = sorted(
        ((k, c) for k, c in override_corps.items() if len(c) >= PROMOTE_THRESHOLD),
        key=lambda kc: -len(kc[1]),
    )
    print(f"[account_overrides 승격 후보] {len(ov_promote)}건")
    for (aid, force), corps in ov_promote:
        print(
            f"  ⮕ account_id={aid!r} force_canonical={force!r}  ({len(corps)}개사: {sorted(corps)})"
        )
        print(
            "     → 편집 지시: _arbitrate_conflicts 일반 규칙 또는 canonical_accounts.yaml "
            f"{force!r} account_ids에 {aid!r} 흡수 검토 후 quirk 제거"
        )
    if not ov_promote:
        print("  (없음)")
    print()

    # quirk 유지(미달) 표기
    alias_keep = [(k, c) for k, c in alias_corps.items() if 0 < len(c) < PROMOTE_THRESHOLD]
    ov_keep = [(k, c) for k, c in override_corps.items() if 0 < len(c) < PROMOTE_THRESHOLD]
    print(f"[quirk 유지(1~{PROMOTE_THRESHOLD - 1}회 반복 — 승격 미달)]")
    if not alias_keep and not ov_keep:
        print("  (없음 — 현재 등록된 quirk 없음 또는 전부 승격 임계 초과)")
    for (canon, alias), corps in alias_keep:
        print(f"  · alias {canon!r}←{alias!r}: {len(corps)}개사 (유지)")
    for (aid, force), corps in ov_keep:
        print(f"  · override {aid!r}→{force!r}: {len(corps)}개사 (유지)")
    print()

    total_promote = len(alias_promote) + len(ov_promote)
    print("=" * 60)
    print(
        f"판정: 승격 후보 {total_promote}건"
        f"{' — 현재 빈 quirk라 후보 0(정상)' if result['n_companies'] == 0 else ''}"
    )


def main() -> None:
    _report(scan())


if __name__ == "__main__":
    main()
