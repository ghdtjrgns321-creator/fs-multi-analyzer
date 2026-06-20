"""Canonical account mapping loader."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class CanonicalAccount:
    name: str
    statement: str
    account_ids: tuple[str, ...]
    aliases: tuple[str, ...]
    is_subtotal: bool = False
    category: str = ""
    # 이 canonical의 account_id 중 '라벨이 id보다 신뢰성 높은' id 목록. 회사가 같은 영문 id를
    # 서로 다른 실질에 쓰는 모호 id(예: ifrs-full_IssuedCapital을 자본금·납입자본 양쪽에 사용)에서,
    # id-label 충돌 시 id를 고집하지 않고 한글 라벨의 canonical을 채택한다. 충돌 행에만 작용한다
    # (라벨이 이 canonical과 같으면 충돌이 아니라 무영향 — 정상 행은 그대로).
    label_priority_ids: tuple[str, ...] = ()
    # 이 canonical이 '다른 표(statement)'에서 같은 IFRS 개념으로 출현하는 id 목록. 같은 id가
    # 등록 statement(예: SCE 자본변동) 밖(예: CIS 포괄손익 OCI)에서 나와 강등될 때, 행 sj_div와
    # 호환되는 이 canonical로 구제한다(가산적 — 강등 행만, 기존 매핑 무영향). 근본원인: id→canonical
    # 1:1이라 다중표 개념을 못 담던 것. 상세: data/backtest/_FINMAP_ROOTCAUSE.md.
    cross_statement_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class SceComponentMap:
    """SCE 자본구성요소(열) 표준화 룩업. account_detail leaf → 표준·role."""

    alias_to_std: dict[str, str]  # normalize_label(alias) → 표준 구성요소명
    alias_to_role: dict[str, str]  # normalize_label(alias) → role(leaf/subtotal/total/composite)
    markers: frozenset[str]  # normalize_label(표 총계 마커)
    deductions: frozenset[str] = frozenset()  # 자본 차감변동 canonical(부호 음수 정규화 대상)
    deduction_ids: frozenset[str] = frozenset()  # 자본 차감변동 account_id(부호 음수 정규화 대상)
    change_begin: frozenset[str] = frozenset()  # 개시 자본 change_canonical
    change_total: frozenset[str] = frozenset()  # 기말 자본 change_canonical
    change_subtotals: frozenset[str] = frozenset()  # 소계 change_canonical(leaf 합 — 검산서 제외)
    subtotal_label_markers: tuple[str, ...] = ()  # 소계 label marker(canonical 미등록 변형 흡수)
    restated_begin_markers: tuple[str, ...] = ()  # 조정후 개시 식별 label marker(정규화)
    restated_delta_label_markers: tuple[str, ...] = ()  # 재작성 델타형 label marker(정규화)
    stock_balance_label_markers: tuple[str, ...] = ()  # bare 누적 잔액행 label marker(정규화)
    parent_subtotal_label_markers: tuple[str, ...] = ()  # 부모=자식합 변동소계 label marker(정규화)
    # 통합 canonical(양방향) → {minus: [키워드], plus: [키워드]} label 부호 분기 사전
    combined_deductions: dict[str, dict[str, tuple[str, ...]]] = field(default_factory=dict)
    subtotal_children: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def classify(self, leaf: str) -> tuple[str, str]:
        """leaf bare 라벨 → (component_std, role). 미매칭은 raw 보존·role=unmatched."""

        key = normalize_label(leaf)
        if not key:
            return ("", "unmatched")
        if key in self.markers:
            # 표 총계열(연결/별도재무제표 마커)은 구성요소가 아니라 bare 합계열 → component_std='-'.
            # 검산(§F)이 이 행으로 기초+Σ변동=기말을 맞춘다. raw 라벨은 component_raw에 보존.
            return ("-", "marker")
        if key in self.alias_to_std:
            return (self.alias_to_std[key], self.alias_to_role[key])
        return (leaf, "unmatched")

    def classify_change_role(self, change_canonical: str, change_label: str) -> str:
        """SCE 변동행 role → begin/total/subtotal/restated_begin/leaf.

        검산(기초+Σleaf=기말)은 leaf만 합산한다. begin/total은 검산의 양 끝, subtotal(소계)은
        leaf의 합이라 합산 시 이중계상, restated_begin(조정후 개시)은 스톡이라 변동이 아니다.
        조정후 개시는 canonical이 '기타 중요 계정'으로 흩어지므로 label marker로 식별한다
        (label에 '기초자본'을 포함하되 canonical이 begin이 아닌 행 = 조정후/재작성 개시).

        체크 순서가 의미 있다: 결정적 canonical 판정(begin/total/subtotal)을 fuzzy label marker
        판정(restated_begin)보다 먼저 한다. 소계 canonical 행의 label에 marker 부분문자열이
        섞여도 subtotal로 올바르게 분류된다(둘 다 검산 제외라 수치 영향은 없으나 분류 정확).
        """

        if change_canonical in self.change_begin:
            return "begin"
        if change_canonical in self.change_total:
            return "total"
        if change_canonical in self.change_subtotals:
            return "subtotal"
        key = normalize_label(change_label)
        # R1(라운드2): canonical 미등록 소계 변형은 label marker로 흡수('소유주와의 거래' 계열 등).
        if key and any(marker in key for marker in self.subtotal_label_markers):
            return "subtotal"
        if key and any(marker in key for marker in self.restated_begin_markers):
            return "restated_begin"
        return "leaf"

    def is_stock_balance_label(self, change_label: str) -> bool:
        """Config-driven label check for subtotal/balance-looking SCE stock rows."""

        key = normalize_label(change_label)
        return bool(key and any(marker in key for marker in self.stock_balance_label_markers))

    def is_restated_delta_label(self, change_label: str) -> bool:
        """Config-driven label check for restatement rows that are deltas, not stock."""

        key = normalize_label(change_label)
        return bool(key and any(marker in key for marker in self.restated_delta_label_markers))

    def deduction_sign(
        self,
        change_canonical: str,
        change_label: str,
        account_id: str = "",
    ) -> str:
        """변동행 부호 처리 → 'minus'(-abs)/'plus'(+abs)/'none'(원본 유지).

        R2(라운드2): 통합 canonical(자기주식변동 등)은 취득·처분 양방향이라 무조건 -abs가 처분(+)을
        뒤집는 역버그다. label 키워드로 분기한다. 단일방향 차감(배당 등)은 sce_deduction_changes로
        항상 minus. 둘 다 아니면 none(섣부른 부호 강제 금지).
        """

        if change_canonical in self.combined_deductions:
            key = normalize_label(change_label)
            spec = self.combined_deductions[change_canonical]
            is_plus = any(kw in key for kw in spec.get("plus", ()))
            is_minus = any(kw in key for kw in spec.get("minus", ()))
            # 취득·처분 키워드가 한 라벨에 모두 있으면(예 '자기주식 취득 및 처분') 방향 모호 →
            # 원본 부호 보존(섣부른 강제 금지). 한쪽만 매칭이면 그 방향, 둘 다 없으면 none.
            if is_plus and is_minus:
                return "none"
            if is_plus:
                return "plus"
            if is_minus:
                return "minus"
            return "none"
        if change_canonical in self.deductions:
            return "minus"
        if account_id in self.deduction_ids:
            return "minus"
        return "none"


def load_canonical_accounts(path: Path) -> list[CanonicalAccount]:
    """Load canonical account mapping from YAML."""

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    accounts = payload.get("canonical_accounts", {})
    result: list[CanonicalAccount] = []
    for name, values in accounts.items():
        result.append(
            CanonicalAccount(
                name=str(name),
                statement=str(values["statement"]),
                account_ids=tuple(str(x) for x in values.get("account_ids", [])),
                aliases=tuple(str(x) for x in values.get("aliases", [])),
                is_subtotal=bool(values.get("is_subtotal", False)),
                category=str(values.get("category", "")),
                label_priority_ids=tuple(str(x) for x in values.get("label_priority_ids", [])),
                cross_statement_ids=tuple(str(x) for x in values.get("cross_statement_ids", [])),
            )
        )
    return result


def load_company_quirks(path: Path | None = None) -> dict[str, dict[str, dict[str, list]]]:
    """회사 고유 정규화 이탈 교정(quirk)을 YAML에서 로드한다.

    반환 구조: {corp_code: {year: {"alias_additions": [...], "account_overrides": [...]}}}.
    corp_code/year는 데이터 키일 뿐 코드 분기가 아니다. 파일 미존재·빈 파일은 빈 dict로
    안전 반환한다(quirk가 없는 정상 경로에서 정규화가 깨지지 않게 한다).
    """

    if path is None or not Path(path).exists():
        return {}
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    quirks = payload.get("company_quirks", {}) or {}
    result: dict[str, dict[str, dict[str, list]]] = {}
    for corp_code, years in quirks.items():
        corp_key = str(corp_code)
        result[corp_key] = {}
        for year, spec in (years or {}).items():
            spec = spec or {}
            result[corp_key][str(year)] = {
                "alias_additions": list(spec.get("alias_additions", []) or []),
                "account_overrides": list(spec.get("account_overrides", []) or []),
            }
    return result


def load_sce_components(path: Path) -> SceComponentMap:
    """Load SCE equity-component standardization map from YAML (data-externalized)."""

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    components = payload.get("sce_equity_components", {})
    alias_to_std: dict[str, str] = {}
    alias_to_role: dict[str, str] = {}
    for std_name, values in components.items():
        role = str(values.get("role", "leaf"))
        for alias in values.get("aliases", []):
            key = normalize_label(alias)
            alias_to_std[key] = str(std_name)
            alias_to_role[key] = role
    markers = frozenset(
        normalize_label(marker) for marker in payload.get("sce_fs_total_markers", [])
    )
    deductions = frozenset(str(x) for x in payload.get("sce_deduction_changes", []))
    deduction_ids = frozenset(str(x) for x in payload.get("sce_deduction_ids", []))
    roles = payload.get("sce_change_roles", {})
    change_begin = frozenset(str(x) for x in roles.get("begin", []))
    change_total = frozenset(str(x) for x in roles.get("total", []))
    change_subtotals = frozenset(str(x) for x in roles.get("subtotal", []))
    subtotal_markers = tuple(normalize_label(x) for x in roles.get("subtotal_label_markers", []))
    restated_markers = tuple(normalize_label(x) for x in roles.get("restated_begin_markers", []))
    restated_delta_markers = tuple(
        normalize_label(x) for x in roles.get("restated_delta_label_markers", [])
    )
    stock_balance_markers = tuple(
        normalize_label(x) for x in roles.get("stock_balance_label_markers", [])
    )
    parent_subtotal_markers = tuple(
        normalize_label(x) for x in roles.get("parent_subtotal_label_markers", [])
    )
    subtotal_children = {
        str(parent): tuple(str(child) for child in children)
        for parent, children in roles.get("subtotal_children", {}).items()
    }
    combined = {
        str(canon): {
            "minus": tuple(normalize_label(x) for x in spec.get("minus", [])),
            "plus": tuple(normalize_label(x) for x in spec.get("plus", [])),
        }
        for canon, spec in payload.get("sce_combined_deductions", {}).items()
    }
    return SceComponentMap(
        alias_to_std=alias_to_std,
        alias_to_role=alias_to_role,
        markers=markers,
        deductions=deductions,
        deduction_ids=deduction_ids,
        change_begin=change_begin,
        change_total=change_total,
        change_subtotals=change_subtotals,
        subtotal_label_markers=subtotal_markers,
        restated_begin_markers=restated_markers,
        restated_delta_label_markers=restated_delta_markers,
        stock_balance_label_markers=stock_balance_markers,
        parent_subtotal_label_markers=parent_subtotal_markers,
        combined_deductions=combined,
        subtotal_children=subtotal_children,
    )


def subtotal_account_names(path: Path) -> set[str]:
    """Load canonical accounts marked as subtotal/identity rows."""

    return {account.name for account in load_canonical_accounts(path) if account.is_subtotal}


def normalize_label(label: object) -> str:
    """Normalize labels for alias lookup without embedding domain labels in code."""

    normalized = str(label or "").replace(" ", "").strip()
    return re.sub(r"\((손실|이익|손익)\)$", "", normalized)


def normalize_sce_change_label(label: object) -> str:
    """Normalize SCE change labels with presentation-only current-period prefixes removed."""

    normalized = normalize_label(label)
    if normalized.startswith("당기") and len(normalized) > len("당기"):
        return normalized[len("당기") :]
    return normalized
