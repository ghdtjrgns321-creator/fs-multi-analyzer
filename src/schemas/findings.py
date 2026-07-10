"""Finding 리포트 스키마 (PLAN §5).

LLM 에이전트 출력을 구조화로 강제한다. 모든 주장은 EvidenceRef로 실제 수치·주석 위치에
grounding 되어야 하며, 빈칸 제출은 허용하지 않는다(PydanticAI result_validator 연계).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class IssueType(StrEnum):
    """통제된 이슈 유형 — **재무제표 영역 축**(중립·목적정렬). 집계·필터 가능하도록 enum 고정.

    분식 가설 축(receivables_quality 등)이 아니라 재무제표 구조를 따르는 중립 영역 축이다:
    도구 목적은 '분식 탐지'가 아니라 '이상 변화·감사 검토 큐'이므로, 라벨은 부정을 전제하지 않고
    "어느 재무제표 영역의 우려인가"만 표시한다. 6관점이 이 공유 목록에서 각자 고른다(관점별 배분 아님).
    구체 위험(계속기업·이익의질·매출채권부실 등)은 enum이 아니라 subtype 자유서술로 보존한다.
    영역은 재무제표 구조(표준·유한)를 따르므로 새 유형이 계속 생기지 않는다(닫힌 축, '기타'는 극소수).
    """

    REVENUE_RECEIVABLES = "revenue_receivables"  # 수익·채권
    COST_INVENTORY = "cost_inventory"  # 원가·재고
    ASSET_VALUATION = "asset_valuation"  # 자산 평가·손상·취득(유형·무형·투자자산)
    LIABILITY_LIQUIDITY = "liability_liquidity"  # 부채·차입·유동성
    EQUITY_CAPITAL = "equity_capital"  # 자본·자본거래(자기주식·배당·유증·기타자본)
    CONTINGENCY_RELATED_PARTY = "contingency_related_party"  # 우발·특수관계·보증·약정·공시
    EARNINGS_TAX = "earnings_tax"  # 손익·세무(이익 변동·법인세·이연법인세)
    CASH_FLOW = "cash_flow"  # 현금흐름(영업·투자·재무 흐름 이상)
    UNMAPPED_MATERIAL_ACCOUNT = "unmapped_material_account"  # 표준분류 못한 큰 계정(기술)
    # 위 영역 어디에도 안 맞는 극소수 안전판. 실제 성격은 subtype 자유부제로 보존.
    OTHER = "기타"


RiskLevel = Literal["High", "Medium", "Low"]
Confidence = Literal["High", "Medium", "Low"]

# Phase2 반박 에이전트 판정 (PHASE2_DESIGN #17). 반박은 위험도 숫자를 직접 바꾸지 않고
# 이 플래그만 부여한다(§9 — AI가 위험을 임의로 깎아 은폐하는 것 차단). 코드가 표시·정렬 보정.
RebuttalVerdict = Literal["normal_dominant", "mixed", "suspicion_dominant"]


class EvidenceRef(BaseModel):
    """근거 참조 — LLM 주장이 가리키는 실제 데이터 위치. grounding 단위."""

    source: Literal["financial_statement", "note", "cash_flow", "prior_year_note"]
    locator: str = Field(description="계정 ID / 주석 섹션 ID 등 추적 키")
    year: str
    value: str | None = Field(default=None, description="결정론 레이어가 계산한 실제 수치")


class Claim(BaseModel):
    """관점이 제기한 의심 주장 1건 — 카드의 '무엇이 의심스러운가' 본문.

    반박(counter_evidence 등)만 카드에 실리고 원 주장이 탈락하던 갭을 닫는다:
    질문 없이 답변만 보이면 카드를 읽을 수 없다. cited_value는 grounding 대조를 거친 인용 수치.
    """

    perspective: str = Field(description="주장을 제기한 관점(numeric/note/flow/trend/...)")
    description: str = Field(description="이상 근거 설명(관점 제출 원문)")
    cited_value: str | None = Field(default=None, description="주장이 인용한 수치")


class ExternalRef(BaseModel):
    """카드별 외부 검증 결과 1건 — 출처 있는 외부 근거(뉴스·공시·리포트).

    외부 검증 에이전트(PLAN §5 후속 검증 단계)가 카드 확정 후 타깃 검색으로 채운다.
    출처 URL 없는 주장은 만들지 않는다(환각 차단 — external 발견자 시절 원칙 계승).
    """

    summary: str = Field(description="외부 근거 요약(출처가 뒷받침하는 주장)")
    url: str = Field(description="출처 URL")
    source: str = Field(default="", description="출처 제목/매체명")


class AccountFinding(BaseModel):
    """① 수치 / ② 주석 / ③ 흐름 분석가의 수준·흐름 Finding."""

    account: str = Field(description="분석 대상 계정 (신호엔진이 동적 선정)")
    issue_type: IssueType
    # issue_type='기타'(OTHER)일 때 실제 성격을 보존하는 자유부제(#14). 코드가 의심건에서 집계.
    subtype: str = Field(default="", description="기타 유형의 자유부제(예: 설비투자급증)")
    materiality_score: float = Field(description="유의성: 절대금액 + 총계 대비 비율")
    anomaly_score: float = Field(description="이상 정도: 변동·항등식 위반 등")
    confidence: Confidence = Field(description="매핑·근거 강도 반영")
    numeric_evidence: list[EvidenceRef] = Field(default_factory=list)
    note_evidence: list[EvidenceRef] = Field(default_factory=list)
    flow_evidence: list[EvidenceRef] = Field(default_factory=list)
    note_cross_check: str | None = Field(
        default=None, description="숫자 신호와 주석 근거의 정합/괴리"
    )
    counter_evidence: list[str] = Field(default_factory=list, description="숫자상 반대 가능성")
    normal_explanation: list[str] = Field(
        default_factory=list, description="정상일 수 있는 사업적 설명"
    )
    confirm_question: list[str] = Field(default_factory=list, description="사용자 확인 질문")
    next_procedure: list[str] = Field(default_factory=list, description="다음 감사 절차")
    risk_level: RiskLevel
    # Phase2 카드 메타 (PHASE2_DESIGN §3). 코드가 클러스터 후 채운다(관점 LLM 출력 아님).
    # 전부 optional 기본값 — 기존 단일관점 Finding 생성 경로는 무영향.
    vote_count: int = Field(default=0, description="내부 4관점 중 이 카드를 지적한 수(N/4)")
    internal_total: int = Field(default=4, description="내부 관점 총수(분모)")
    reference_badges: list[str] = Field(
        default_factory=list, description="외부·동종 등 참고 신호 배지(카운트 외)"
    )
    rebuttal_verdict: RebuttalVerdict | None = Field(
        default=None, description="반박 에이전트 판정(없으면 미반박)"
    )
    cluster_key: str | None = Field(default=None, description="클러스터 키(계정 카드면 locator)")
    # 관계(relationship) 카드의 엮인 계정 다리들. 흐름 관점 관계 모순을 단일계정으로 붕괴시키지
    # 않고 카드가 다리를 보유한다(死필드 부활). 계정·회사 카드는 빈값 → 기존 경로 무회귀.
    related_accounts: list[str] = Field(default_factory=list, description="관계 카드의 엮인 계정들")
    # 추세(trend) 카드의 전기값·전기연도(死필드 부활 2탄). 카드가 "전기 X→당기 Y"를 구조로 보유해
    # 산문에만 묻히지 않게 한다. 추세 외 카드는 None → 무회귀.
    prior_value: str | None = Field(default=None, description="추세 카드: 전기 값")
    prior_year: str | None = Field(default=None, description="추세 카드: 전기 연도")
    # 카드를 만든 관점별 의심 주장(원문). 기본 빈값 — 기존 생성 경로 무회귀.
    claims: list[Claim] = Field(default_factory=list, description="관점별 의심 주장(카드 본문)")
    # 외부 검증(카드 확정 후 타깃 검색) 결과. checked=True&빈 리스트 = "검색했으나 미발견".
    external_evidence: list[ExternalRef] = Field(
        default_factory=list, description="출처 있는 외부 근거(검증 에이전트)"
    )
    external_checked: bool = Field(default=False, description="외부 검증 수행 여부")


class ChangeRef(BaseModel):
    """④ 공시 변동 전용 근거 — 전기/당기 변화 단위."""

    target: str = Field(description="계정 또는 주석 섹션")
    change_type: Literal["new_appearance", "removal", "expansion", "reduction", "value_change"]
    prior: str | None = None
    current: str | None = None
    year_from: str
    year_to: str


class DisclosureChangeFinding(BaseModel):
    """④ 공시 변동 에이전트의 Finding. cross_inconsistency가 핵심 신호."""

    target: str
    issue_type: IssueType
    change_evidence: list[ChangeRef] = Field(default_factory=list)
    cross_inconsistency: str | None = Field(
        default=None, description="수치 vs 텍스트 모순 (예: 충당부채 불변 + 우발부채 문구 확대)"
    )
    materiality_score: float
    confidence: Confidence
    counter_evidence: list[str] = Field(default_factory=list)
    next_procedure: list[str] = Field(default_factory=list)
    risk_level: RiskLevel
