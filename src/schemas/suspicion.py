"""Phase2 의심건 스키마 (PHASE2_DESIGN §3·§4).

관점(에이전트)이 제출하는 **의심건 1건**의 양식이다. 관점은 발견만 하고, 점수·표수·
확신도·반박은 코드/반박 에이전트가 채운다(PLAN 원칙①). grounding 강제: 계정 의심건은
account_id·cited_value를 반드시 달아야 코드가 실값과 대조(환각 탈락)하고 계정별로 묶는다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from src.schemas.findings import EvidenceRef, IssueType, RebuttalVerdict, RiskLevel

# 관점은 닫힌 6집합. 내부 4관점만 카드 표수(N/4)에 카운트, 외부·동종은 참고배지(#6·D15).
PerspectiveName = Literal["numeric", "note", "flow", "trend", "external", "industry"]
INTERNAL_PERSPECTIVES: tuple[str, ...] = ("numeric", "note", "flow", "trend")

# 계정에 걸리면 account, 회사 전체 이슈(외부·동종·지배구조·소송)면 company(#3),
# 계정 간 관계(쌍·교차재무제표) 모순이면 relationship(흐름 관점 고유 단위).
SuspicionScope = Literal["account", "company", "relationship"]

# 계정 클러스터 키 규약: "acct:{sj_div}:{account_id}". 같은 키끼리 묶어 N/4를 집계한다.
ACCOUNT_LOCATOR_PREFIX = "acct"


def build_account_locator(sj_div: str, account_id: str) -> str:
    """계정 의심건의 클러스터 locator 생성(sj_div로 동명 계정 표 구분)."""

    return f"{ACCOUNT_LOCATOR_PREFIX}:{sj_div}:{account_id}"


def parse_account_locator(locator: str) -> tuple[str, str]:
    """locator → (sj_div, account_id). 규약 위반 시 ValueError."""

    parts = locator.split(":", 2)
    if len(parts) != 3 or parts[0] != ACCOUNT_LOCATOR_PREFIX:
        raise ValueError(f"잘못된 account locator: {locator}")
    return parts[1], parts[2]


class SuspicionItem(BaseModel):
    """관점이 제출하는 의심건 1건. 코드가 이걸 모아 카드로 클러스터한다."""

    perspective: PerspectiveName
    scope: SuspicionScope
    issue_type: IssueType
    # '기타'(other) 안전판 보완용 자유 부제(#14). 9종에 안 맞는 의심건의 실제 성격 보존.
    subtype: str = ""
    account_id: str | None = Field(default=None, description="계정 의심건의 클러스터 앵커")
    sj_div: str | None = Field(default=None, description="재무제표 구분(BS/IS/CF/CIS/SCE)")
    year: str
    cited_value: str | None = Field(default=None, description="인용 수치(코드 grounding 대상)")
    description: str = Field(description="이상 근거 설명(비어 있으면 거부)")
    source_url: str | None = Field(default=None, description="외부 의심건의 출처 URL")
    risk_level: RiskLevel = "Medium"
    evidence: list[EvidenceRef] = Field(default_factory=list)
    # 관점별 선택 필드(#A 보완) — 안 쓰는 관점은 빈값. 한 봉투 통일을 유지하면서
    # 흐름(관계)·변동(시간변화)이 자유텍스트로 납작해지는 것을 막는다.
    related_accounts: list[str] = Field(
        default_factory=list, description="흐름 관점: 관계로 엮인 관련 계정들"
    )
    prior_value: str | None = Field(default=None, description="변동 관점: 전기 값")
    prior_year: str | None = Field(default=None, description="변동 관점: 전기 연도")

    @model_validator(mode="after")
    def _enforce_grounding(self) -> SuspicionItem:
        # 빈 설명 제출 금지(hollow 의심건 차단).
        if not self.description or not self.description.strip():
            raise ValueError("description은 비어 있을 수 없다.")
        # 계정 의심건은 앵커·수치 필수(grounding·클러스터 키 확보).
        if self.scope == "account":
            if not self.account_id or not str(self.account_id).strip():
                raise ValueError("account scope는 account_id가 필수다.")
            if not self.cited_value or not str(self.cited_value).strip():
                raise ValueError("account scope는 cited_value가 필수다.")
        # 관계 의심건은 대표 계정(anchor)+나머지 다리(related_accounts≥1) 필수. cited_value는 선택
        # (관계는 괴리·비율이라 단일 금액이 없을 수 있음). 다리 실존은 grounding에서 대조.
        if self.scope == "relationship":
            if not self.account_id or not str(self.account_id).strip():
                raise ValueError("relationship scope는 대표 account_id가 필수다.")
            if not self.related_accounts:
                raise ValueError("relationship scope는 related_accounts(≥1)가 필수다.")
        return self


class PerspectiveOutput(BaseModel):
    """관점 agent 1회 출력 = 의심건 여러 장을 담는 봉투(PHASE2_DESIGN §9).

    빈 결과도 status로 명시(빈칸 숨김 금지). perspective 라벨은 코드가 재주입한다.
    status: completed=LLM 정상응답(0건도 정상), deferred=의도적 건너뜀(키·데이터 없음),
    failed=LLM 호출 실패(quota·타임아웃·에러). failed는 빈 결과로 둔갑시키지 않고 표면화한다.
    """

    status: Literal["completed", "deferred", "failed"] = "completed"
    suspicions: list[SuspicionItem] = Field(default_factory=list)


class RebuttalEntry(BaseModel):
    """반박 에이전트가 카드 1장에 채우는 항목(PHASE2_DESIGN §10).

    cluster_key로 카드에 매칭. 위험도 숫자는 안 건드리고 verdict 플래그만 부여(§9).
    """

    cluster_key: str
    verdict: RebuttalVerdict
    counter_evidence: list[str] = Field(default_factory=list)
    normal_explanation: list[str] = Field(default_factory=list)
    confirm_question: list[str] = Field(default_factory=list)
    next_procedure: list[str] = Field(default_factory=list)


class RebuttalOutput(BaseModel):
    """반박 에이전트 일괄 출력. 카드 전체에 대한 entries."""

    entries: list[RebuttalEntry] = Field(default_factory=list)


def relationship_legs(item: SuspicionItem) -> list[str]:
    """관계 의심건의 다리 = {대표 account_id} ∪ related_accounts, 정렬 canonical.

    정렬해 A↔B와 B↔A가 같은 키/카드로 뭉치게 한다. 교차재무제표(CFS:현금↔OFS:현금)도
    fs_div 접두가 붙은 다리 그대로라 특수분기 없이 동일 규칙으로 처리된다."""

    legs = {leg for leg in [item.account_id, *item.related_accounts] if leg and str(leg).strip()}
    return sorted(legs)


def cluster_key(item: SuspicionItem) -> str | None:
    """계정 의심건은 계정 locator, 관계 의심건은 rel: 다리조합, 회사레벨은 None(#3)."""

    if item.scope == "relationship":
        legs = relationship_legs(item)
        return "rel:" + "|".join(legs) if legs else None
    if item.scope != "account" or not item.account_id:
        return None
    return build_account_locator(item.sj_div or "?", item.account_id)
