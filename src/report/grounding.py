"""Phase2 근거검증 (grounding) — PHASE2_DESIGN §4 ①.

관점이 제출한 의심건의 인용 수치가 실제 데이터에 있는지 코드가 대조해 환각을 탈락시킨다.

인용에 단위(조·억·백만·원)가 붙어 있으면 **원 단위로 복원해 자릿수까지** 대조한다. 예전에는
유효숫자(trailing-zero 제거)만 봐서 '1,961억'과 '1,961백만'이 같은 값으로 통과했다 — 자릿수가
8자리 틀려도 grounded로 나가던 구멍. 단위 병기(amounts.py)가 LLM 입력 경계에서 원→억 나눗셈을
없앤 뒤로 스케일 무시의 근거가 사라져 제거했다.

단위 없는 맨숫자('1,961')는 스케일 복원이 불가능하므로 유효숫자 대조로 남기되,
value_verified=False로 내려 '존재는 확인·자릿수 미확인'을 카드에 정직하게 표시한다.
탈락 건도 reason과 함께 전부 반환한다(§9 silent drop 금지).
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from src.schemas.suspicion import INTERNAL_PERSPECTIVES, SuspicionItem

# 금액 인용으로 볼 토큰: 쉼표묶음(12,345) · 억/조/백만 단위 · 6자리+ 정수.
# 퍼센트·소액 비율(유효숫자<3)은 금액 주장으로 보지 않아 환각 탈락 대상에서 제외(false-drop 방지).
_AMOUNT_TOKEN = re.compile(r"\d{1,3}(?:,\d{3})+|\d+\s*(?:억|조|백만)|\d{6,}")

# 단위가 붙은 인용 — 원 단위 복원이 가능한 형태. figure_sheet._SCALE에 천원을 더한 환산표.
# 긴 접미사(백만원·천원)를 먼저 둬야 '원'이 가로채지 않는다.
_SCALE = {"조": 1e12, "억": 1e8, "백만원": 1e6, "백만": 1e6, "천원": 1e3, "천": 1e3, "원": 1.0}
_UNITS = "조|억|백만원|백만|천원|천|원"
_SCALED_TOKEN = re.compile(rf"(-?\d[\d,]*(?:\.\d+)?)\s*({_UNITS})")
# 단위 없는 원 단위 금액 — 자릿수(6+)가 곧 스케일이라 복원이 확정된다.
# 쉼표 묶음(22,264,200,000,000)도 포함. 뒤에 단위가 오면 위 스케일 경로가 맡으므로 제외.
_RAW_WON_TOKEN = re.compile(rf"(?<![\d,.])(\d{{1,3}}(?:,\d{{3}})+|\d{{6,}})(?!\s*(?:{_UNITS}))")

# 복원된 인용과 실값의 허용 오차. LLM이 '1조 2,534.7억'처럼 반올림해 쓰므로 상대오차를 준다.
# 절대 하한(100만원)은 소액에서 상대오차가 과하게 좁아지는 것을 막는다(BS_TOL과 같은 철학).
_REL_TOL = 0.01
_ABS_TOL = 1_000_000.0


class GroundedSuspicion(BaseModel):
    """근거검증 결과. grounded=False면 탈락(환각), value_verified는 확신도 입력."""

    item: SuspicionItem
    grounded: bool
    value_verified: bool
    reason: str


def _sig(text: str) -> str:
    """문자열에서 유효숫자만 추출(앞뒤 0 제거). 스케일 미상 인용의 fallback 대조용."""

    digits = re.sub(r"\D", "", text).lstrip("0").rstrip("0")
    return digits


def _sig_amount(amount: float) -> str:
    """금액(float) → 인덱스 저장 형태 '원단위절대값'. round 후 정수화(accounting-precision)."""

    return str(int(round(abs(float(amount)))))


def scaled_claims(cited: str) -> list[float]:
    """인용에서 **스케일이 확정되는** 금액만 원 단위 절대값으로 복원.

    '1,961억' → 1.961e11 · '532,893백만원' → 5.32893e11 · '196100000000' → 1.961e11.
    단위 없는 '1,961'은 복원 불가라 여기 안 들어온다(→ _amount_claim_sigs fallback).
    """

    out: list[float] = []
    text = cited or ""
    for num, unit in _SCALED_TOKEN.findall(text):
        try:
            out.append(abs(float(num.replace(",", "")) * _SCALE[unit]))
        except (ValueError, KeyError):
            continue
    for raw in _RAW_WON_TOKEN.findall(text):
        digits = raw.replace(",", "")
        if len(digits) < 6:  # 짧은 맨숫자(1,961)는 스케일 미상 — sig fallback으로 넘긴다
            continue
        try:
            out.append(abs(float(digits)))
        except ValueError:
            continue
    return out


def _values_of(pool: set[str]) -> list[float]:
    """인덱스 풀(원단위 절대값 문자열) → float 목록."""

    out: list[float] = []
    for entry in pool:
        try:
            out.append(float(entry))
        except ValueError:
            continue
    return out


def _matches_scaled(claims: list[float], pool: set[str]) -> bool:
    """복원된 인용이 풀의 실값과 허용오차 내에서 일치하나(자릿수 포함 대조)."""

    actuals = _values_of(pool)
    for claim in claims:
        for actual in actuals:
            if abs(claim - actual) <= max(_ABS_TOL, _REL_TOL * abs(actual)):
                return True
    return False


def _amount_claim_sigs(cited: str) -> list[str]:
    """인용 금액 토큰의 유효숫자(3자리+). 스케일 미상 인용의 fallback 대조용."""

    sigs = []
    for token in _AMOUNT_TOKEN.findall(cited or ""):
        sig = _sig(token)
        if len(sig) >= 3:
            sigs.append(sig)
    return sigs


def _matches_sig(claims: list[str], pool: set[str]) -> bool:
    """스케일 미상 인용 — 유효숫자만 대조(자릿수는 확인 못 함)."""

    pool_sigs = {_sig(entry) for entry in pool}
    return any(claim in pool_sigs for claim in claims)


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
    # 공시 원문의 '532,893백만원'도 인덱스는 원 단위 절대값으로 통일한다(대조 기준 일치).
    for disc in note_disclosures or []:
        text = str(disc.get("text", ""))
        values = {_sig_amount(v) for v in scaled_claims(text)}
        for token in disc.get("tokens", []) or []:
            token = str(token).strip()
            if token:
                index.setdefault(f"note:{token}", set()).update(values)
        if values:
            index.setdefault(_NOTE_DISCLOSURE_KEY, set()).update(values)
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
    cited = item.cited_value or ""
    scaled = scaled_claims(cited)
    claims = _amount_claim_sigs(cited)
    if pool is None:
        # 라벨 미매칭이라도 인용 금액이 실제 공시 텍스트에 있으면 grounded(허위탈락 방지).
        if scaled and _matches_scaled(scaled, disclosure):
            return GroundedSuspicion(
                item=item,
                grounded=True,
                value_verified=True,
                reason="주석 공시 텍스트에 인용 금액 실재",
            )
        if not scaled and claims and _matches_sig(claims, disclosure):
            return GroundedSuspicion(
                item=item,
                grounded=True,
                value_verified=False,
                reason="주석 공시에 유효숫자 일치(단위 미표기 — 자릿수 미확인)",
            )
        return GroundedSuspicion(
            item=item,
            grounded=False,
            value_verified=False,
            reason="주석 라벨·금액 모두 데이터에 없음(환각)",
        )
    if not claims and not scaled:
        return GroundedSuspicion(
            item=item, grounded=True, value_verified=False, reason="주석 존재·수치 비교불가(서술형)"
        )
    if scaled:
        if _matches_scaled(scaled, pool) or _matches_scaled(scaled, disclosure):
            return GroundedSuspicion(
                item=item, grounded=True, value_verified=True, reason="인용 금액이 주석 실값과 일치"
            )
        return GroundedSuspicion(
            item=item,
            grounded=False,
            value_verified=False,
            reason="인용 수치가 주석 실값과 불일치(환각 — 자릿수 포함 대조)",
        )
    if _matches_sig(claims, pool) or _matches_sig(claims, disclosure):
        return GroundedSuspicion(
            item=item,
            grounded=True,
            value_verified=False,
            reason="주석 실값과 유효숫자 일치(단위 미표기 — 자릿수 미확인)",
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
    cited = item.cited_value or ""
    scaled = scaled_claims(cited)
    claims = _amount_claim_sigs(cited)
    if not claims and not scaled:
        return GroundedSuspicion(
            item=item,
            grounded=True,
            value_verified=False,
            reason="계정 존재·수치 비교불가(추세/비율)",
        )
    if scaled:
        if _matches_scaled(scaled, pool):
            return GroundedSuspicion(
                item=item, grounded=True, value_verified=True, reason="인용 금액이 계정 실값과 일치"
            )
        return GroundedSuspicion(
            item=item,
            grounded=False,
            value_verified=False,
            reason="인용 수치가 계정 실값과 불일치(환각 — 자릿수 포함 대조)",
        )
    if _matches_sig(claims, pool):
        return GroundedSuspicion(
            item=item,
            grounded=True,
            value_verified=False,
            reason="계정 실값과 유효숫자 일치(단위 미표기 — 자릿수 미확인)",
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
    cited = item.cited_value or ""
    scaled = scaled_claims(cited)
    pools = [index.get(str(leg), set()) | index.get(f"{item.sj_div}:{leg}", set()) for leg in legs]
    # 관계는 비율·괴리라 단일 금액이 없을 수 있어 value_verified는 선택 판정이다.
    # 자릿수까지 맞아야 verified — 스케일 미상 인용은 verified로 올리지 않는다.
    verified = bool(scaled) and any(_matches_scaled(scaled, pool) for pool in pools)
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


# EvidenceRef 종류 분류 — 여기(코드가 색인을 아는 유일한 지점)서 확정해 카드에 싣는다.
# 렌더러가 locator 문자열 모양으로 역추정하던 두더지잡기의 근본 해결.
_NARRATIVE_NAMESPACES = frozenset({"note", "note_facts", "report_extracts", "sce"})
_FS_PREFIXES = frozenset({"CFS", "OFS", "BS", "IS", "CF", "CIS", "SCE"})


def _has_korean(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text)


def _evidence_label(locator: str) -> str:
    """locator → 사람용 라벨: 'ASCII접두:한글라벨'·'코드|라벨' 형태의 접두를 벗긴다.

    접두를 열거하지 않는다 — LLM이 canonical: 같은 임의 접두를 발명해도(실측) 나머지에
    한글 라벨이 있으면 그것이 사람용 라벨이다."""

    prefix, _, rest = locator.partition(":")
    base = rest if (rest and not _has_korean(prefix)) else locator
    return base.split("|")[-1].strip() or locator


def _numeric_value(value: object) -> bool:
    try:
        float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return False
    return True


def classify_ref(ref: object, sj_div: str | None, index: dict[str, set[str]]) -> None:
    """근거 참조 1건에 resolved_kind·display_label 세팅(in-place).

    규칙(형식 예상 금지 — 실측에서 LLM이 canonical:·언더스코어 변형을 발명함):
    ①서술 네임스페이스 → note/narrative ②locator 또는 '접두 뒤 나머지'가 색인에 실존 →
    account ③한글이 한 글자도 없는 미해석 참조 = 전부 metric(어떤 구분자든) ④나머지는
    값이 금액이면 account, 아니면 narrative(드롭 없음)."""

    locator = str(getattr(ref, "locator", "") or "")
    prefix, _, rest = locator.partition(":")
    label = _evidence_label(locator)
    if prefix in _NARRATIVE_NAMESPACES:
        kind = "note" if _numeric_value(getattr(ref, "value", None)) else "narrative"
    elif any(
        candidate in index or (sj_div and f"{sj_div}:{candidate}" in index)
        for candidate in (locator, rest, label)
        if candidate
    ):
        kind = "account"
    elif prefix in _FS_PREFIXES:
        kind = "account"
    elif not _has_korean(locator):
        kind = "metric"  # ASCII-only 미해석 참조(지표·내부 키) — 표시 금지
    else:
        kind = "account" if _numeric_value(getattr(ref, "value", None)) else "narrative"
    ref.resolved_kind = kind  # type: ignore[attr-defined]
    ref.display_label = label  # type: ignore[attr-defined]


def classify_evidence(item: SuspicionItem, index: dict[str, set[str]]) -> None:
    """의심건의 근거 참조 전부에 종류·라벨 세팅.

    account=계정 실측(수치 표) / note=주석 수치 / narrative=서술 공시(읽는 목록) /
    metric=지표 원시 키(표시 안 함 — 내용은 주장 서술이 이미 담음)."""

    for ref in item.evidence:
        classify_ref(ref, item.sj_div, index)


def verify_suspicions(
    items: list[SuspicionItem],
    index: dict[str, set[str]],
    peer_keys: set[str] | None = None,
) -> list[GroundedSuspicion]:
    """전 의심건 검증 + 근거 종류 분류. 탈락 건도 reason과 함께 전부 반환(§9 silent drop 금지)."""

    results = []
    for item in items:
        classify_evidence(item, index)
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
