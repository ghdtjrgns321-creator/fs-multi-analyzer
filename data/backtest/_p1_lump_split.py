"""lump canonical 8개를 stem별 개별 canonical로 분리(라인기반 config surgery·한글보존).

각 lump 블록(  name: ~ 다음 canonical 전)을 분리 블록들로 교체. 자본금은 benign이라 유지.
검증: 분리 후 재정규화→소실0 + pytest + 백테스트.
"""

from __future__ import annotations

from pathlib import Path

CFG = Path("config/canonical_accounts.yaml")

# lump_name → (statement, [(새 canonical명, [account_ids], [aliases]), ...])
SPLITS: dict[str, tuple[str, list]] = {
    "관계기업투자": (
        "BS",
        [
            (
                "관계기업투자",
                ["ifrs-full_InvestmentsInAssociates"],
                ["관계기업투자", "관계기업투자주식"],
            ),
            (
                "지분법적용투자",
                ["ifrs-full_InvestmentAccountedForUsingEquityMethod"],
                ["지분법적용 투자지분", "지분법적용투자주식"],
            ),
            (
                "종속관계공동기업투자",
                ["ifrs-full_InvestmentsInSubsidiariesJointVenturesAndAssociates"],
                ["종속기업, 관계기업 및 공동기업투자", "종속기업및관계기업투자주식"],
            ),
        ],
    ),
    "대손상각비": (
        "CF",
        [
            ("대손상각비", ["dart_AdjustmentsForBadDebtExpenses"], ["대손상각비"]),
            ("기타대손상각비", ["dart_AdjustmentsForOtherBadDebtExpenses"], ["기타의 대손상각비"]),
        ],
    ),
    "기타금융자산취득": (
        "CF",
        [
            ("기타금융자산취득", ["dart_PurchaseOfOtherFinancialAssets"], ["기타금융자산의 취득"]),
            (
                "유동기타금융자산취득",
                ["dart_PurchaseOfOtherCurrentFinancialAssets"],
                ["기타유동금융자산의 취득"],
            ),
            (
                "비유동기타금융자산취득",
                ["dart_PurchaseOfOtherNonCurrentFinancialAssets"],
                ["기타비유동금융자산의 취득"],
            ),
        ],
    ),
    "기타금융자산처분": (
        "CF",
        [
            (
                "기타금융자산처분",
                ["dart_ProceedsFromSalesOfOtherFinancialAssets"],
                ["기타금융자산의 처분"],
            ),
            (
                "유동기타금융자산처분",
                ["dart_ProceedsFromSalesOfOtherCurrentFinancialAssets"],
                ["기타유동금융자산의 처분"],
            ),
            (
                "비유동기타금융자산처분",
                ["dart_ProceedsFromSalesOfOtherNonCurrentFinancialAssets"],
                ["기타비유동금융자산의 처분"],
            ),
        ],
    ),
    "기타자본변동": (
        "SCE",
        [
            (
                "연결대상범위변동",
                ["dart_ChangesInConsolidatedCompanies"],
                ["연결실체의 변동", "연결대상범위의 변동"],
            ),
            ("내부거래취득", ["dart_IntercompanyAcquisition"], ["연결실체내 자본거래 등"]),
            (
                "회계정책변경효과",
                [
                    "ifrs-full_IncreaseDecreaseThroughChangesInAccountingPolicies",
                    "ifrs_IncreaseDecreaseThroughChangesInAccountingPolicies",
                    "dart_IncreaseDecreaseThroughChangesInAccountingPolicies",
                ],
                ["회계정책변경에 따른 증가(감소)"],
            ),
        ],
    ),
    "FVOCI평가손익": (
        "CIS",
        [
            (
                "FVOCI지분상품평가손익",
                [
                    "ifrs-full_OtherComprehensiveIncomeNetOfTaxGainsLossesFromInvestmentsInEquityInstruments"
                ],
                ["기타포괄손익-공정가치 측정 금융자산 평가손익"],
            ),
            (
                "FVOCI적립금변동",
                [
                    "dart_ChangesInReserveOfGainsAndLossesOnFinancialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome"
                ],
                ["기타포괄손익-공정가치금융자산평가손익적립금"],
            ),
        ],
    ),
    "해외사업환산손익": (
        "CIS",
        [
            (
                "해외사업환산손익",
                ["ifrs-full_GainsLossesOnExchangeDifferencesOnTranslationNetOfTax"],
                ["해외사업장환산외환차이", "해외사업환산손익"],
            ),
            ("환율변동효과", ["dart_ChangesInForeignExchangeRates"], ["환율변동"]),
        ],
    ),
    "지분법기타포괄손익": (
        "CIS",
        [
            (
                "지분법기타포괄손익재분류가능",
                [
                    "ifrs-full_ShareOfOtherComprehensiveIncomeOfAssociatesAndJointVenturesAccountedForUsingEquityMethodThatWillBeReclassifiedToProfitOrLossNetOfTax",
                    "dart_ShareOfOtherComprehensiveIncomeOfAssociatesAndJointVenturesAccountedForUsingEquityMethodThatWillBeReclassifiedToProfitOrLossNetOfTax",
                ],
                ["지분법기타포괄손익(재분류가능)"],
            ),
            (
                "지분법기타포괄손익재분류불가능",
                [
                    "ifrs-full_ShareOfOtherComprehensiveIncomeOfAssociatesAndJointVenturesAccountedForUsingEquityMethodThatWillNotBeReclassifiedToProfitOrLossNetOfTax",
                    "dart_ShareOfOtherComprehensiveIncomeOfAssociatesAndJointVenturesAccountedForUsingEquityMethodThatWillNotBeReclassifiedToProfitOrLossNetOfTax",
                ],
                ["지분법기타포괄손익(재분류불가능)"],
            ),
        ],
    ),
}


def yq(text: str) -> str:
    if any(c in text for c in ',:[]{}#&*!|>%@`"'):
        return '"' + text.replace('"', '\\"') + '"'
    return text


def build_block(name: str, statement: str, aids: list[str], aliases: list[str]) -> list[str]:
    out = [f"  {yq(name)}:", f"    statement: {statement}", "    account_ids:"]
    out += [f"      - {a}" for a in aids]
    out.append(f"    aliases: [{', '.join(yq(a) for a in aliases)}]")
    return out


lines = CFG.read_text(encoding="utf-8").split("\n")


def find_block(name: str) -> tuple[int, int]:
    """canonical 블록 [start, end) 라인 인덱스. end=다음 2칸들여쓰기 키 or 비2칸."""
    start = None
    for i, ln in enumerate(lines):
        if ln == f"  {name}:":
            start = i
            break
    if start is None:
        return (-1, -1)
    j = start + 1
    while j < len(lines):
        ln = lines[j]
        if ln.startswith("  ") and not ln.startswith("   ") and ln.rstrip().endswith(":"):
            break  # 다음 canonical
        if ln and not ln.startswith("  "):
            break  # top-level key
        j += 1
    return (start, j)


# 뒤에서부터 치환(인덱스 안정성)
ordered = sorted(SPLITS.items(), key=lambda kv: find_block(kv[0])[0], reverse=True)
for name, (stmt, parts) in ordered:
    s, e = find_block(name)
    if s < 0:
        print(f"[SKIP] {name} 블록 못찾음")
        continue
    repl: list[str] = []
    for new_name, aids, aliases in parts:
        repl += build_block(new_name, stmt, aids, aliases)
    lines[s:e] = repl
    print(f"[OK] {name} → {len(parts)}개 분리 ({s}~{e})")

CFG.write_text("\n".join(lines), encoding="utf-8", newline="")
print("분리 완료")
