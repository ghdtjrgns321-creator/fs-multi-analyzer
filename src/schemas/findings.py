"""Finding 리포트 스키마 (PLAN §5).

LLM 에이전트 출력을 구조화로 강제한다. 모든 주장은 EvidenceRef로 실제 수치·주석 위치에
grounding 되어야 하며, 빈칸 제출은 허용하지 않는다(PydanticAI result_validator 연계).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class IssueType(StrEnum):
    """통제된 이슈 유형. 자유 문자열 금지 — 집계·필터 가능하도록 enum 고정(원칙: #1 분기 강제)."""

    RECEIVABLES_QUALITY = "receivables_quality"
    INVENTORY_OBSOLESCENCE = "inventory_obsolescence"
    GOING_CONCERN = "going_concern"
    CONTINGENT_LIABILITY_UNDERSTATEMENT = "contingent_liability_understatement"
    RELATED_PARTY_CONCENTRATION = "related_party_concentration"
    EARNINGS_QUALITY = "earnings_quality"
    LIQUIDITY_RISK = "liquidity_risk"
    DISCLOSURE_CHANGE = "disclosure_change"
    UNMAPPED_MATERIAL_ACCOUNT = "unmapped_material_account"


RiskLevel = Literal["High", "Medium", "Low"]
Confidence = Literal["High", "Medium", "Low"]


class EvidenceRef(BaseModel):
    """근거 참조 — LLM 주장이 가리키는 실제 데이터 위치. grounding 단위."""

    source: Literal["financial_statement", "note", "cash_flow", "prior_year_note"]
    locator: str = Field(description="계정 ID / 주석 섹션 ID 등 추적 키")
    year: str
    value: str | None = Field(default=None, description="결정론 레이어가 계산한 실제 수치")


class AccountFinding(BaseModel):
    """① 수치 / ② 주석 / ③ 흐름 분석가의 수준·흐름 Finding."""

    account: str = Field(description="분석 대상 계정 (신호엔진이 동적 선정)")
    issue_type: IssueType
    materiality_score: float = Field(description="유의성: 절대금액 + 총계 대비 비율")
    anomaly_score: float = Field(description="이상 정도: 변동·항등식 위반 등")
    confidence: Confidence = Field(description="매핑·근거 강도 반영")
    numeric_evidence: list[EvidenceRef] = Field(default_factory=list)
    note_evidence: list[EvidenceRef] = Field(default_factory=list)
    flow_evidence: list[EvidenceRef] = Field(default_factory=list)
    counter_evidence: list[str] = Field(default_factory=list, description="숫자상 반대 가능성")
    normal_explanation: list[str] = Field(
        default_factory=list, description="정상일 수 있는 사업적 설명"
    )
    next_procedure: list[str] = Field(default_factory=list, description="다음 감사 절차")
    risk_level: RiskLevel


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
