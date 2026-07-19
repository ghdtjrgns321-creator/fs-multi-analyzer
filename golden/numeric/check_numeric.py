"""검사1 수치 골든 — 최종 카드의 표시 수치를 DART 원천값과 대조(설계: golden/DESIGN.md §2).

기존 grounding 인덱스(`build_account_index`)와 값 대조(`_matches_scaled`)를 **최종 카드**에
재적용한다. grounding은 LLM 출력을 카드 조립 *전*에 보지만, 이 하니스는 모든 변환(억/조 환산·
표기정규화) *후*의 카드를 봐서 grounding이 못 보는 변환 버그를 잡는다.

대조 기준은 grounding과 같이 **원 단위 절대값**이다(자릿수 포함). 예전 유효숫자(trailing-zero
제거) 대조는 1,961억과 1,961백만을 같은 값으로 봐서 스케일 오류를 통과시켰다.

판정(verdict) 4종:
- match          : 원값이 그 계정 원천 풀에 실재(자릿수 포함) + 환산 표기도 정합
- value_mismatch : 계정은 있으나 인용 금액이 원천에 없음(환각) — 1a 실패
- convert_fail   : 원값은 맞으나 표시 표기가 원값과 스케일 불일치(÷10 등) — 1b 실패
- unreconcilable : 계정 자체가 인덱스에 없어 대조 불가(조용히 통과 금지, 별도 버킷)
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from dashboard.card_data import fmt_krw
from src.report.grounding import _matches_scaled, _sig_amount

# 서술/지표 근거는 금액 표가 아니므로 대조 대상에서 뺀다(evidence_rows와 동일 필터).
_NON_AMOUNT_KINDS = frozenset({"metric", "narrative"})
# 주석 네임스페이스 접두 — 계정 인덱스로 못 풀면 전역 주석값 실재로 대조(라벨 형식 idiosyncratic).
_NOTE_NAMESPACES = frozenset({"note_facts", "note", "note_disclosure"})
# 환산 무결 상대 허용오차(억/조 반올림 흡수, ÷10 스케일오류는 초과).
_CONVERT_TOL_REL = 0.005


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _amount_of(raw: Any) -> float | None:
    """원값 파싱. 서술형/None → None(대조 대상 아님).

    카드는 LLM 입력 경계에서 병기된 '168,532,992,835(1,685.3억)' 포맷으로 저장될 수 있으므로
    괄호 앞 원값만 취한다(annotate_amounts 병기 — 괄호 뒤 억/조를 숫자로 오파싱하면 안 됨).
    """

    head = str(raw).split("(")[0].replace(",", "").strip()
    try:
        return float(head)
    except (TypeError, ValueError):
        return None


def _annotation_of(raw_str: Any) -> str | None:
    """병기 포맷 '원값(1,685.3억)'의 괄호 안 환산 표기. 병기 없으면 None."""

    m = re.search(r"\(([^)]*[조억][^)]*)\)", str(raw_str))
    return m.group(1) if m else None


def decode_krw(text: Any) -> float | None:
    """사람용 억/조 표기를 원 단위 float으로 역파싱. 부호 보존, 실패 시 None.

    '1조 2,534.7억' → 1.25347e12, '858억' → 8.58e10, '-85,778,983,809' → 그대로.
    """

    s = str(text).strip()
    if not s:
        return None
    body = s.replace(",", "")
    negative = body.lstrip().startswith("-")
    total = 0.0
    matched = False
    for unit, scale in (("조", 1e12), ("억", 1e8)):
        m = re.search(rf"(-?\d+(?:\.\d+)?)\s*{unit}", body)
        if m:
            total += abs(float(m.group(1))) * scale
            matched = True
    if not matched:
        try:
            return float(body)  # 단위 없는 순수 숫자(원단위 그대로)
        except ValueError:
            return None
    return -total if negative else total


def display_granularity(text: Any) -> float:
    """표기의 최소 표현 단위(반올림 granularity). '2,534.7억'→1e7, '858억'→1e8, '1.2조'→1e11."""

    s = str(text).replace(",", "")
    for unit, scale in (("억", 1e8), ("조", 1e12)):
        m = re.search(rf"\d+(?:\.(\d+))?\s*{unit}", s)
        if m:
            decimals = len(m.group(1)) if m.group(1) else 0
            return scale / (10**decimals)
    return 1.0


def convert_ok(raw: float, display: Any, tol_rel: float = _CONVERT_TOL_REL) -> bool:
    """표시 표기가 원값과 같은 크기인가(반올림 허용, ÷10 등 스케일오류 거부).

    허용오차 = max(상대오차, 표기 granularity의 절반). ÷10 오류는 이 범위를 크게 벗어난다.
    """

    decoded = decode_krw(display)
    if decoded is None:
        return False
    tol = max(tol_rel * abs(raw), 0.5 * display_granularity(display)) + 1.0
    return abs(decoded - raw) <= tol


def _has_korean(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text)


def resolve_pool(locator: str, sj_div: str | None, index: dict[str, set[str]]) -> set[str] | None:
    """카드 locator로 원천 유효숫자 풀 조회. 없으면 None(대조불가).

    LLM이 발명한 접두(acct:·canonical:·note_facts: 등)를 벗겨 나머지도 조회한다
    (grounding.classify_ref와 동일 규칙 — 한글 없는 접두는 내부 네임스페이스). 예:
    'acct:IS:CFS:당기순이익' → 'IS:CFS:당기순이익'(sj_div 한정 키로 실존).
    """

    if not locator:
        return None
    candidates = [locator]
    prefix, _, rest = locator.partition(":")
    if rest and not _has_korean(prefix):
        candidates.append(rest)
    for candidate in candidates:
        if candidate in index:
            return index[candidate]
        if sj_div and f"{sj_div}:{candidate}" in index:
            return index[f"{sj_div}:{candidate}"]
    return None


def _reconcile_amount(
    locator: str,
    raw_str: Any,
    index: dict[str, set[str]],
    formatter: Callable[[Any], str],
    sj_div: str | None = None,
    source: str = "evidence",
    year: str = "",
    global_sigs: set[str] | None = None,
) -> dict[str, Any]:
    """수치 1건 대조 → 판정 레코드. 1a(원값 실재) → 1b(환산 무결) 순.

    근거(evidence)는 계정 특정 풀로 대조(엄격 — 틀린 계정에 틀린 값 검출). 주장(claim) 인용값은
    앵커 계정 외 형제 계정을 정당하게 인용하므로 전역 유효숫자 집합으로 대조(global_sigs).
    """

    raw = _amount_of(raw_str)
    # 표시(1b 대상): 카드가 '원값(1,685.3억)' 병기로 저장하면 괄호 안 표기가 이미 환산값이므로
    # 그것을 검증 대상으로 쓴다(pipeline이 실제 만든 환산). 병기 없으면 formatter로 렌더.
    annotation = _annotation_of(raw_str)
    display = annotation if annotation else (formatter(raw) if raw is not None else "-")
    record = {
        "locator": locator,
        "source": source,
        "year": str(year or ""),
        "raw": str(raw_str),
        "display": display,
        "sig": _sig_amount(raw) if raw is not None else "",
    }
    if raw is None:
        return {**record, "verdict": "unreconcilable"}
    everything = global_sigs if global_sigs is not None else set()
    prefix = locator.partition(":")[0]
    if source == "claim" or prefix in _NOTE_NAMESPACES:
        # 주장은 형제 계정을 정당 인용, 주석 근거는 라벨 형식 제각각 + 동명 계정(SCE 등) 오매칭 위험
        # → 둘 다 전역 실재로 대조. resolve_pool보다 먼저 처리(계정 풀이 note 값 가로채기 방지).
        pool = everything
    else:
        pool = resolve_pool(locator, sj_div, index)
        if pool is None:
            return {**record, "verdict": "unreconcilable"}
    if not _matches_scaled([abs(float(raw))], pool):
        return {**record, "verdict": "value_mismatch"}
    if not convert_ok(raw, display):
        return {**record, "verdict": "convert_fail"}
    return {**record, "verdict": "match"}


def _card_amount_refs(card: Any) -> list[dict[str, Any]]:
    """카드에서 대조할 (locator, 원값, 앵커계정) 목록 — 금액형 근거 + 주장 인용값."""

    refs: list[dict[str, Any]] = []
    anchor = str(_get(card, "cluster_key") or _get(card, "account") or "")
    for ref in _get(card, "numeric_evidence") or []:
        kind = _get(ref, "resolved_kind")
        if kind in _NON_AMOUNT_KINDS:
            continue
        if _amount_of(_get(ref, "value")) is None:
            continue
        refs.append(
            {
                "locator": str(_get(ref, "locator") or anchor),
                "raw": _get(ref, "value"),
                "year": _get(ref, "year"),
                "source": "evidence",
            }
        )
    for claim in _get(card, "claims") or []:
        cited = _get(claim, "cited_value")
        if _amount_of(cited) is None:
            continue
        refs.append({"locator": anchor, "raw": cited, "year": "", "source": "claim"})
    return refs


def reconcile_cards(
    cards: list[Any],
    index: dict[str, set[str]],
    formatter: Callable[[Any], str] = fmt_krw,
) -> dict[str, Any]:
    """카드 목록 전체 대조 → {rows, summary}. summary는 판정별 건수 + 분모 n."""

    global_sigs: set[str] = set().union(*index.values()) if index else set()
    rows: list[dict[str, Any]] = []
    for card in cards or []:
        sj_div = _get(card, "sj_div")
        for ref in _card_amount_refs(card):
            rows.append(
                _reconcile_amount(
                    ref["locator"],
                    ref["raw"],
                    index,
                    formatter,
                    sj_div=sj_div,
                    source=ref["source"],
                    year=ref["year"],
                    global_sigs=global_sigs,
                )
            )
    summary = {"n": len(rows)}
    for verdict in ("match", "value_mismatch", "convert_fail", "unreconcilable"):
        summary[verdict] = sum(1 for r in rows if r["verdict"] == verdict)
    return {"rows": rows, "summary": summary}


def _leaf_deltas(rows: list[dict[str, Any]]) -> float:
    """분해 행의 leaf delta 합(children 있으면 하위로 내려가 이중계상 방지)."""

    total = 0.0
    for r in rows or []:
        if r.get("delta") is None:
            continue
        if r.get("children"):
            total += _leaf_deltas(r["children"])
            total += float(r.get("child_residual") or 0.0)
        else:
            total += float(r["delta"])
    return total


def check_decomposition_identity(decomp: dict[str, Any], tol: float = 1.0) -> bool:
    """분해 산술 항등: |Σleaves + 잔차 − 부모 delta| ≤ tol(원). 초과 시 False."""

    if not decomp:
        return True
    delta = float(decomp.get("delta") or 0.0)
    total = _leaf_deltas(decomp.get("rows") or []) + float(decomp.get("residual") or 0.0)
    return abs(total - delta) <= tol


def source_index_from_db(corp: str, years: list[int], data_dir: Any = None) -> dict[str, set[str]]:
    """정규화 DB(권위 출처)에서 계정 원천 유효숫자 인덱스 구축(설계 §2.2).

    series_key = f'{fs_div}:{canonical}'로 카드 locator와 맞춘다. grounding.build_account_index
    재사용 — 같은 유효숫자 대조 로직을 최종 카드에 적용한다.
    """

    from src.analysis_tools import load_normalized_financials
    from src.analysis_tools.data import load_notes_classified
    from src.report.grounding import build_account_index

    frame = load_normalized_financials(corp, years, data_dir=data_dir)
    rows: list[dict[str, Any]] = []
    for rec in frame.to_dict("records"):
        canonical = rec.get("canonical")
        fs_div = rec.get("fs_div")
        if canonical is None or rec.get("amount") is None:
            continue
        series_key = f"{fs_div}:{canonical}" if fs_div else str(canonical)
        rows.append(
            {
                "series_key": series_key,
                "canonical": canonical,
                "label": rec.get("label"),
                "amount": rec.get("amount"),
                "sj_div": rec.get("sj_div"),
            }
        )
    # 주석 fact 편입(설계 §2.2) — label_ko→label 매핑. 전역 대조로 주석 인용값 실재 확인.
    note_facts: list[dict[str, Any]] = []
    try:
        notes = load_notes_classified(corp, years, data_dir=data_dir)
        note_facts = [
            {"label": r.get("label_ko"), "category": r.get("category"), "value": r.get("value")}
            for r in notes.to_dict("records")
        ]
    except (FileNotFoundError, KeyError, ValueError):
        note_facts = []  # 주석 미수집 회사는 주석 없이 진행(계정 대조는 유효)
    return build_account_index(rows, note_facts=note_facts)


def run_saved_cards(corp: str, year: Any, root: Any = None) -> dict[str, Any]:
    """저장된 카드(suspicion_cards.json)를 정규화 DB 원천과 대조 → 결과 dict.

    카드가 참조하는 연도들의 DB를 모두 로드해 인덱스를 만든다(전기값 인용 대비).
    """

    from src.report.cards_store import load_cards

    payload = load_cards(corp, year, root=root)
    if payload is None:
        return {"rows": [], "summary": {"n": 0}, "error": "저장된 카드 없음"}
    cards: list[Any] = []
    for section in ("account_cards", "relationship_cards", "company_cards"):
        cards.extend(payload.get(section) or [])
    years = sorted(
        {int(r["year"]) for r in (payload.get("series_rows") or []) if str(r.get("year")).isdigit()}
    )
    if not years:
        years = [int(year)]
    index = source_index_from_db(corp, years, data_dir=root)
    result = reconcile_cards(cards, index)
    result["meta"] = {"corp": corp, "year": str(year), "years_loaded": years, "cards": len(cards)}
    return result


def build_report_md(result: dict[str, Any]) -> str:
    """대조표 마크다운 — 헤더에 분모 N·판정별 건수, 본문에 수치별 1행."""

    s = result.get("summary", {})
    meta = result.get("meta", {})
    n = s.get("n", 0)
    bad = s.get("value_mismatch", 0) + s.get("convert_fail", 0)
    scope = f"카드 {meta.get('cards', 0)}장, DB 연도 {meta.get('years_loaded', [])}"
    lines = [
        f"# 검사1 수치 골든 대조표 — {meta.get('corp', '')}/{meta.get('year', '')}",
        "",
        f"- 대조 수치 N = {n} ({scope})",
        f"- match={s.get('match', 0)} · value_mismatch={s.get('value_mismatch', 0)}"
        f" · convert_fail={s.get('convert_fail', 0)} · unreconcilable={s.get('unreconcilable', 0)}",
        f"- **판정: {'PASS' if bad == 0 else 'FAIL'}** (원값·환산 불일치 {bad}건)",
        "",
        "| 판정 | 계정(locator) | 연도 | 원값 | 표시 | 출처 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    order = {"value_mismatch": 0, "convert_fail": 1, "unreconcilable": 2, "match": 3}
    for r in sorted(result.get("rows", []), key=lambda x: order.get(x["verdict"], 9)):
        lines.append(
            f"| {r['verdict']} | {r['locator']} | {r['year']} | {r['raw']} | {r['display']} "
            f"| {r['source']} |"
        )
    return "\n".join(lines) + "\n"


__all__ = [
    "build_report_md",
    "check_decomposition_identity",
    "convert_ok",
    "decode_krw",
    "display_granularity",
    "reconcile_cards",
    "resolve_pool",
    "run_saved_cards",
    "source_index_from_db",
]
