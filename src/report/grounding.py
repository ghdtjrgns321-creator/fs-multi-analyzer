"""Phase2 근거검증 (grounding) — PHASE2_DESIGN §4 ①.

관점이 제출한 의심건의 인용 수치가 실제 데이터에 있는지 코드가 대조해 환각을 탈락시킨다.
LLM은 같은 금액을 원·백만·억 등 다른 단위로 인용하므로(메모리: 원/백만 오독), 직접 float
비교 대신 **유효숫자(trailing-zero 제거) 동일성**으로 스케일·단위 무관하게 대조한다.
탈락 건도 reason과 함께 전부 반환한다(§9 silent drop 금지).
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from src.schemas.suspicion import INTERNAL_PERSPECTIVES, SuspicionItem

# 금액 인용으로 볼 토큰: 쉼표묶음(12,345) · 억/조/백만 단위 · 6자리+ 정수.
# 퍼센트·소액 비율(유효숫자<3)은 금액 주장으로 보지 않아 환각 탈락 대상에서 제외(false-drop 방지).
_AMOUNT_TOKEN = re.compile(r"\d{1,3}(?:,\d{3})+|\d+\s*(?:억|조|백만)|\d{6,}")


class GroundedSuspicion(BaseModel):
    """근거검증 결과. grounded=False면 탈락(환각), value_verified는 확신도 입력."""

    item: SuspicionItem
    grounded: bool
    value_verified: bool
    reason: str


def _sig(text: str) -> str:
    """문자열에서 유효숫자만 추출(앞뒤 0 제거). '1,961억'·'196100000000' → '1961'."""

    digits = re.sub(r"\D", "", text).lstrip("0").rstrip("0")
    return digits


def _sig_amount(amount: float) -> str:
    """금액(float) → 유효숫자. round 후 정수화(accounting-precision)."""

    return _sig(str(int(round(abs(amount)))))


def _amount_claim_sigs(cited: str) -> list[str]:
    """인용 문자열의 금액 주장 토큰들의 유효숫자(3자리+만)."""

    sigs = []
    for token in _AMOUNT_TOKEN.findall(cited or ""):
        sig = _sig(token)
        if len(sig) >= 3:
            sigs.append(sig)
    return sigs


def _note_value_sig(value: object) -> str | None:
    """주석 fact value가 순수 숫자면 유효숫자, 서술형(문장)이면 None.
    혼합('532,893백만원')도 None(존재만 grounding) — 스트레이 숫자 오매칭 방지."""

    text = str(value).strip().replace(",", "")
    try:
        number = float(text)
    except ValueError:
        return None
    if number != number:  # NaN
        return None
    return _sig_amount(number)


_NOTE_DISCLOSURE_KEY = "note:__disclosure__"


def build_account_index(
    account_series: list[dict],
    unmapped: list[dict] | None = None,
    note_facts: list[dict] | None = None,
    sce_cells: list[dict] | None = None,
    note_disclosures: list[dict] | None = None,
) -> dict[str, set[str]]:
    """계정 식별자(series_key/canonical/label/account_id) → 그 계정 금액들의 유효숫자 집합.

    note_facts는 `note:{label}`·`note:{category}` 네임스페이스로 색인(본문 키와 비충돌). 금액형은
    value 유효숫자, 서술형은 빈 풀(존재만) → note-only 우발 항목이 환각 탈락하지 않게 한다.

    note_disclosures는 서술형 공시(note_sections·report_extracts 담보·특수관계·소송 등)로,
    각 항목 {tokens, text}의 금액을 note:{token}별 + 전역 note:__disclosure__ 풀에 색인한다(사각#3).
    XBRL fact에 없는 서술형 공시가 grounding에서 허위탈락하던 것을 막는다."""

    index: dict[str, set[str]] = {}

    def _add(key: object, amount: object, sj_div: object = None) -> None:
        if key is None or str(key).strip() == "":
            return
        try:
            sig = _sig_amount(float(amount))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return
        index.setdefault(str(key), set()).add(sig)
        # sj_div 한정 키도 색인 — 동명이계(BS/IS/CF 같은 계정명)에서 타 표 금액으로
        # 환각 통과하던 경로 차단(verify는 sj_div 한정 키를 우선 조회).
        if sj_div is not None and str(sj_div).strip():
            index.setdefault(f"{sj_div}:{key}", set()).add(sig)

    for row in account_series or []:
        for field in ("series_key", "canonical", "label"):
            _add(row.get(field), row.get("amount"), row.get("sj_div"))
    for row in unmapped or []:
        for field in ("account_id", "label"):
            _add(row.get(field), row.get("amount"), row.get("sj_div"))
    # 주석 fact: note: 네임스페이스(본문 키와 비충돌). 금액형은 유효숫자, 서술형은 빈 풀(존재만).
    for fact in note_facts or []:
        label = str(fact.get("label", "")).strip()
        category = str(fact.get("category", "")).strip()
        sig = _note_value_sig(fact.get("value"))
        for token in (label, category):
            if not token:
                continue
            pool = index.setdefault(f"note:{token}", set())
            if sig is not None:
                pool.add(sig)
    # 서술형 공시(사각#3): 담보·특수관계·소송 등은 XBRL fact가 아니라 HTML 발췌·사업보고서 청크에
    # 산다. 각 공시 텍스트의 금액을 token별 + 전역(__disclosure__) 풀에 색인해 값 기반 grounding.
    for disc in note_disclosures or []:
        text = str(disc.get("text", ""))
        sigs = {sig for tok in _AMOUNT_TOKEN.findall(text) if len(sig := _sig(tok)) >= 3}
        for token in disc.get("tokens", []) or []:
            token = str(token).strip()
            if token:
                index.setdefault(f"note:{token}", set()).update(sigs)
        if sigs:
            index.setdefault(_NOTE_DISCLOSURE_KEY, set()).update(sigs)
    # SCE 2D 셀: sce:{change}·sce:{component} 네임스페이스(본문 비충돌). change 관점이 조회.
    for cell in sce_cells or []:
        sig = _note_value_sig(cell.get("amount"))
        for token in (str(cell.get("change", "")).strip(), str(cell.get("component", "")).strip()):
            if not token:
                continue
            pool = index.setdefault(f"sce:{token}", set())
            if sig is not None:
                pool.add(sig)
    return index


def _verify_note_suspicion(item: SuspicionItem, index: dict[str, set[str]]) -> GroundedSuspicion:
    """note 계정 의심건: 주석 라벨 키 + 서술형 공시 값 기반 grounding(사각#3).

    XBRL fact 라벨(note:{account_id})이 있으면 그 풀로, 없으면 note:__disclosure__(서술형 공시 전체
    금액 풀)로 값 검증한다. LLM이 담보를 다른 라벨로 앵커링해도 인용 금액이 실제 공시에 있으면
    grounded — 진짜 공시를 환각으로 죽이던 허위탈락 차단. 공시에 없는 금액은 여전히 탈락(환각가드)."""

    pool = index.get(f"note:{item.account_id}")
    if pool is None and item.related_accounts:
        pool = index.get(f"note:{item.related_accounts[0]}")
    disclosure = index.get(_NOTE_DISCLOSURE_KEY, set())
    claims = _amount_claim_sigs(item.cited_value or "")
    if pool is None:
        # 라벨 미매칭이라도 인용 금액이 실제 공시 텍스트에 있으면 grounded(허위탈락 방지).
        if claims and any(claim in disclosure for claim in claims):
            return GroundedSuspicion(
                item=item,
                grounded=True,
                value_verified=True,
                reason="주석 공시 텍스트에 인용 금액 실재",
            )
        return GroundedSuspicion(
            item=item,
            grounded=False,
            value_verified=False,
            reason="주석 라벨·금액 모두 데이터에 없음(환각)",
        )
    if not claims:
        return GroundedSuspicion(
            item=item, grounded=True, value_verified=False, reason="주석 존재·수치 비교불가(서술형)"
        )
    if any(claim in pool or claim in disclosure for claim in claims):
        return GroundedSuspicion(
            item=item, grounded=True, value_verified=True, reason="인용 금액이 주석 실값과 일치"
        )
    return GroundedSuspicion(
        item=item,
        grounded=False,
        value_verified=False,
        reason="인용 수치가 주석 실값과 불일치(환각)",
    )


def verify_account_suspicion(item: SuspicionItem, index: dict[str, set[str]]) -> GroundedSuspicion:
    """계정 의심건: 계정 존재 + 인용 금액 유효숫자 대조."""

    # note 관점은 전용 grounding(서술형 공시 값 기반 fallback 포함, 사각#3).
    if item.perspective == "note":
        return _verify_note_suspicion(item, index)
    # sj_div 한정 키 우선(동명이계 오매칭 차단), 없으면 account_id만으로 fallback.
    pool: set[str] | None = None
    # trend(추세) 관점은 본문 키 외에 sce: 네임스페이스(자본변동표)도 조회 가능.
    if pool is None and item.perspective == "trend":
        pool = index.get(f"sce:{item.account_id}")
    if pool is None and item.sj_div:
        pool = index.get(f"{item.sj_div}:{item.account_id}")
    if pool is None and item.perspective != "note":
        pool = index.get(str(item.account_id or ""))
    if pool is None:
        return GroundedSuspicion(
            item=item, grounded=False, value_verified=False, reason="계정이 데이터에 없음(환각)"
        )
    claims = _amount_claim_sigs(item.cited_value or "")
    if not claims:
        return GroundedSuspicion(
            item=item,
            grounded=True,
            value_verified=False,
            reason="계정 존재·수치 비교불가(추세/비율)",
        )
    if any(claim in pool for claim in claims):
        return GroundedSuspicion(
            item=item, grounded=True, value_verified=True, reason="인용 금액이 계정 실값과 일치"
        )
    return GroundedSuspicion(
        item=item,
        grounded=False,
        value_verified=False,
        reason="인용 수치가 계정 실값과 불일치(환각)",
    )


def _leg_in_index(leg: object, sj_div: object, index: dict[str, set[str]]) -> bool:
    """관계 다리(계정)가 index에 실존하나. 다리는 fs_div 접두(CFS:현금) 그대로거나
    sj_div 한정 키로 조회된다. 존재만 확인(금액 대조는 value_verified에서)."""

    if leg is None or not str(leg).strip():
        return False
    if str(leg) in index:
        return True
    return bool(sj_div and f"{sj_div}:{leg}" in index)


def verify_relationship_suspicion(
    item: SuspicionItem, index: dict[str, set[str]]
) -> GroundedSuspicion:
    """관계 의심건: 모든 다리(대표+related)가 실존해야 grounded(가짜 계정 간 관계 날조 차단).

    cited_value 유효숫자가 어느 다리 금액과 맞으면 value_verified(선택 — 관계는 비율·괴리라
    단일 금액이 없을 수 있음)."""

    from src.schemas.suspicion import relationship_legs

    legs = relationship_legs(item)
    missing = [leg for leg in legs if not _leg_in_index(leg, item.sj_div, index)]
    if missing:
        return GroundedSuspicion(
            item=item,
            grounded=False,
            value_verified=False,
            reason=f"관계 다리 미존재(환각): {missing}",
        )
    claims = _amount_claim_sigs(item.cited_value or "")
    verified = any(
        claim in index.get(str(leg), set()) or claim in index.get(f"{item.sj_div}:{leg}", set())
        for leg in legs
        for claim in claims
    )
    reason = "관계 다리 실존" + (" · 인용수치 일치" if verified else "")
    return GroundedSuspicion(item=item, grounded=True, value_verified=verified, reason=reason)


def verify_company_suspicion(
    item: SuspicionItem, peer_keys: set[str] | None = None
) -> GroundedSuspicion:
    """회사레벨 의심건: 외부=출처 URL 존재 / 동종=peer 대조(참고이므로 탈락 안 함, D15)."""

    if item.perspective == "external":
        has_url = bool(item.source_url and str(item.source_url).startswith("http"))
        return GroundedSuspicion(
            item=item,
            grounded=has_url,
            value_verified=False,
            reason="출처 URL 확인(내용 검증불가)" if has_url else "외부 출처 URL 없음(탈락)",
        )
    if item.perspective == "industry":
        verified = bool(peer_keys and str(item.account_id or "") in peer_keys)
        return GroundedSuspicion(
            item=item,
            grounded=True,
            value_verified=verified,
            reason="동종 peer 지표 대조" if verified else "동종 참고 신호(peer 미대조)",
        )
    # numeric 등이 회사레벨로 온 경우: 계정 앵커가 없어 수치 검증 불가, 참고로 유지.
    return GroundedSuspicion(
        item=item, grounded=True, value_verified=False, reason="회사레벨 의심건(수치 검증불가)"
    )


def verify_suspicions(
    items: list[SuspicionItem],
    index: dict[str, set[str]],
    peer_keys: set[str] | None = None,
) -> list[GroundedSuspicion]:
    """전 의심건 검증. 탈락 건도 reason과 함께 전부 반환(§9 silent drop 금지)."""

    results = []
    for item in items:
        if item.scope == "account":
            results.append(verify_account_suspicion(item, index))
        elif item.scope == "relationship":
            results.append(verify_relationship_suspicion(item, index))
        else:
            results.append(verify_company_suspicion(item, peer_keys))
    return results


def grounded_only(results: list[GroundedSuspicion]) -> list[GroundedSuspicion]:
    """생존(grounded) 의심건만. 호출부 편의."""

    return [r for r in results if r.grounded]


__all__ = [
    "GroundedSuspicion",
    "INTERNAL_PERSPECTIVES",
    "build_account_index",
    "grounded_only",
    "verify_account_suspicion",
    "verify_company_suspicion",
    "verify_relationship_suspicion",
    "verify_suspicions",
]
