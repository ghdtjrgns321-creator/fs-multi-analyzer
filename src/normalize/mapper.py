"""Canonical account mapper."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.normalize.config import CanonicalAccount, normalize_label, normalize_sce_change_label

EXACT = "exact_taxonomy_match"
ALIAS = "label_alias_match"
UNMAPPED = "unmapped_extension_account"
# account_id 매핑과 label 매핑이 서로 다른 canonical을 가리킬 때(영문 id 슬롯에 다른 실질 신고).
# label(한글 공시명)을 채택하되 흔적을 남겨 하류·감사가 단정의 위험을 인지하게 한다.
ID_LABEL_CONFLICT = "id_label_conflict"
OTHER_CANONICAL = "기타 중요 계정"
CROSS_STATEMENT = "cross_statement_match"
# 같은 표로 보는 statement 쌍(IS↔CIS 통합신고). pipeline._STATEMENT_COMPATIBLE과 동일 관습.
_COMPAT_PAIRS = {("IS", "CIS"), ("CIS", "IS")}


def _statement_ok(sj_div: str, statement: str) -> bool:
    return bool(statement) and (sj_div == statement or (sj_div, statement) in _COMPAT_PAIRS)


@dataclass(frozen=True)
class MappingResult:
    canonical: str
    mapping_status: str
    statement: str = ""
    # 충돌(id_label_conflict) 행에서만 채워지는 label 후보. 후처리 중재(_arbitrate_conflicts)가
    # id 후보(canonical/statement)와 label 후보를 표 호환성으로 비교해 채택을 결정한다.
    # 비충돌 행은 빈 문자(하위호환: 기존 소비처는 이 필드를 읽지 않는다).
    label_canonical: str = ""
    label_statement: str = ""


class AccountMapper:
    """Map rows to canonical accounts using account_id first, then aliases."""

    def __init__(self, accounts: list[CanonicalAccount]) -> None:
        self._by_id = {
            account_id: account for account in accounts for account_id in account.account_ids
        }
        # ifrs_X 와 ifrs-full_X 는 동일 IFRS 택소노미 개념의 namespace 변형이다(접두사만 상이).
        # 등록된 ifrs-full_X에 대해 ifrs_X도 같은 canonical로 EXACT 매핑한다. 특정 계정 하드코딩이
        # 아니라 namespace 규칙이므로 새 계정이 늘어도 자동 적용된다.
        for account_id, account in list(self._by_id.items()):
            if account_id.startswith("ifrs-full_"):
                short_id = "ifrs_" + account_id[len("ifrs-full_") :]
                self._by_id.setdefault(short_id, account)
        self._by_alias = {
            normalize_label(alias): account for account in accounts for alias in account.aliases
        }
        # 라벨 우선 id 집합(모호 id — 회사가 자본금/납입자본 양쪽에 쓰는 ifrs-full_IssuedCapital 등).
        # id-label 충돌 시 이 id는 라벨 canonical을 채택한다(아래 map_row).
        self._label_priority_ids = {
            account_id for account in accounts for account_id in account.label_priority_ids
        }
        # 다중표 구제: 같은 id가 등록 statement 밖에서 강등될 때 호환 canonical을 찾는다.
        # {id: [canonical...]} — cross_statement_ids로 선언한 canonical만(ifrs_X 변형도 흡수).
        self._by_cross: dict[str, list[CanonicalAccount]] = {}
        for account in accounts:
            for account_id in account.cross_statement_ids:
                self._by_cross.setdefault(account_id, []).append(account)
                if account_id.startswith("ifrs-full_"):
                    short_id = "ifrs_" + account_id[len("ifrs-full_") :]
                    self._by_cross.setdefault(short_id, []).append(account)

    def map_row(self, row: pd.Series) -> MappingResult:
        account_id = str(row.get("account_id", ""))
        label = normalize_label(row.get("account_nm", ""))

        if account_id in self._by_id:
            account = self._by_id[account_id]
            # N5(라운드1): id가 가리키는 canonical과 label 정확 alias가 다르면 의미 모순(영문 id
            # 슬롯에 다른 실질 신고 — 폐지 개념 HTM id 등). 매핑은 id-first 유지(T3 결정 보존,
            # 무회귀), mapping_status에 흔적만 남겨 2단계 측정·리뷰 대상으로 노출한다. 유사 일치는
            # 모순으로 치지 않는다(label 정확 alias 일치만 — 역방향 오염 방지).
            by_alias = self._by_alias.get(label)
            if by_alias is not None and by_alias.name != account.name:
                # 라벨 우선 id(모호 id): 라벨이 id보다 신뢰성 높으므로 라벨 canonical 채택.
                # 예: ifrs-full_IssuedCapital은 회사에 따라 자본금/납입자본 양쪽에 쓰여,
                # 라벨이 '납입자본'이면 자본금 슬롯을 차지하지 않고 납입자본으로 보낸다.
                # ★단, 라벨 canonical이 id와 같은 statement일 때만 채택한다. 그래야 CF id의 행이
                # 라벨 때문에 SCE/BS canonical로 교차표 오배정되는 것을 막는다(예: CF 주식발행 id의
                # '신주발행' 라벨이 SCE 자본금변동으로 새는 것 차단 — id 유지). 같은 표 라벨교정만 허용.
                if (
                    account_id in self._label_priority_ids
                    and by_alias.statement == account.statement
                ):
                    return MappingResult(by_alias.name, ALIAS, by_alias.statement)
                # id 채택 유지(보수). 단 label 후보를 함께 기록해 후처리 표 호환성 중재가 두
                # 후보를 모두 볼 수 있게 한다(어느 쪽이 sj_div와 호환인지로 채택 결정).
                return MappingResult(
                    account.name,
                    ID_LABEL_CONFLICT,
                    account.statement,
                    label_canonical=by_alias.name,
                    label_statement=by_alias.statement,
                )
            return MappingResult(account.name, EXACT, account.statement)
        if label in self._by_alias:
            account = self._by_alias[label]
            return MappingResult(account.name, ALIAS, account.statement)
        return MappingResult(OTHER_CANONICAL, UNMAPPED)

    def cross_statement_match(self, account_id: str, sj_div: str) -> MappingResult | None:
        """강등된(기타) 행 구제용: id가 다른 표 canonical에 cross 등록돼 있고 행 sj_div와
        호환되면 그 canonical을 반환. 없으면 None. 가산적(강등 행에만 후처리로 호출).
        """

        for account in self._by_cross.get(str(account_id), []):
            if _statement_ok(str(sj_div), account.statement):
                return MappingResult(account.name, CROSS_STATEMENT, account.statement)
        return None

    def map_change_row(self, row: pd.Series) -> MappingResult:
        """SCE(자본변동표) 변동행 전용 매핑. 본문 map_row와 달리 id-label 모순 시 label 우선.

        Why: 본문 BS/IS/CF는 표준 account_id가 권위(비유동 표준ID는 통합 라벨보다 우선) → id-first.
        그러나 SCE 변동행은 회사가 영문 id 슬롯(dart_StockDividends 등)에 다른 실질(주식선택권)을
        흔히 신고해, 한글 공시명(label)이 변동의 실질이다. 모순은 일반 규칙으로 감지하고(특정 계정
        하드코딩 없음), label을 채택하되 mapping_status에 id_label_conflict 흔적을 남긴다.
        """

        account_id = str(row.get("account_id", ""))
        label = normalize_sce_change_label(row.get("account_nm", ""))
        by_id = self._by_id.get(account_id)
        by_alias = self._by_alias.get(label)
        if by_id is not None and by_alias is not None and by_alias.name != by_id.name:
            return MappingResult(by_alias.name, ID_LABEL_CONFLICT, by_alias.statement)
        if by_id is not None:
            return MappingResult(by_id.name, EXACT, by_id.statement)
        if by_alias is not None:
            return MappingResult(by_alias.name, ALIAS, by_alias.statement)
        return MappingResult(OTHER_CANONICAL, UNMAPPED)
