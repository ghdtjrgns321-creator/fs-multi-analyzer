"""어휘 게이트 — LLM 출력에 백데이터 내부 식별자가 새면 코드가 반려한다(근본 해결).

원리는 grounding과 동일: 지시(프롬프트)가 아니라 강제(검사)로 막는다. 금지 목록은
손 열거가 아니라 **그 호출에 실제 들어간 재료 dict의 키들**에서 자동 추출한다
(모집단 = 입력 자체 — 새 내부 필드가 생겨도 자동 커버, 두더지잡기 방지).
'_' 또는 '.'가 든 식별자만 금지해 ROE·DSO 같은 정당한 감사 용어는 오탐하지 않는다.
"""

from __future__ import annotations

import re
from typing import Any

# 출력에서 스캔하지 않는 구조 필드 — locator·계정 앵커 등은 내부 키가 '정당하게' 들어간다.
EXCLUDED_FIELDS = frozenset(
    {
        "locator",
        "cluster_key",
        "account_id",
        "account",
        "related_accounts",
        "source",
        "source_url",
        "year",
        "prior_year",
        "year_from",
        "year_to",
        "perspective",
        "issue_type",
        "scope",
        "sj_div",
        "method",
        "status",
        "change_type",
        "target",
        "resolved_kind",
        "display_label",
    }
)

# 금지 대상 식별자 형태: '_'/'.'를 포함한 ASCII 식별자(target_value, benchmark.roa …)
# 또는 6자 이상 단일 영단어 키(decomposition, residual …) — 한글 본문에 새면 내부 어휘.
# 5자 이하(roe·dso·trend 등)는 정당한 감사 용어와 겹쳐 금지하지 않는다(오탐 방지).
_BANNABLE = re.compile(
    r"^(?:[A-Za-z_][A-Za-z0-9]*(?:[._][A-Za-z0-9_.]+)+|[A-Za-z][A-Za-z0-9]{5,})$"
)
# 본문에서 찾을 토큰: '_'/'.' 식별자 + 단일 영단어(6자+).
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9]*(?:[._][A-Za-z0-9_]+)+|\b[A-Za-z][A-Za-z0-9]{5,}\b")


def banned_identifiers(payload: Any) -> set[str]:
    """재료(dict/list 중첩)의 모든 dict 키 중 내부 식별자 형태만 수집(소문자 정규화)."""

    out: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                key_s = str(key)
                if len(key_s) >= 4 and _BANNABLE.match(key_s):
                    out.add(key_s.lower())
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)

    walk(payload)
    return out


def find_violations(
    output: Any, banned: set[str], exclude_fields: frozenset[str] = EXCLUDED_FIELDS
) -> list[str]:
    """출력(pydantic 모델/딕셔너리)의 서술 필드에서 금지 식별자 토큰을 찾는다.

    구조 필드(locator 등)는 면제 — 계정 앵커에 내부 키가 들어가는 건 정당하다."""

    data = output.model_dump() if hasattr(output, "model_dump") else output
    hits: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key) in exclude_fields:
                    continue
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            for token in _TOKEN.findall(node):
                if token.lower() in banned:
                    hits.add(token)

    walk(data)
    return sorted(hits)


def attach_vocab_guard(agent: Any, banned: set[str]) -> None:
    """PydanticAI agent에 출력 검증기 부착 — 위반 시 ModelRetry(재생성 요구).

    grounding이 숫자에 하는 일을 언어에 한다: 지시 위반을 코드가 잡아 되돌려보낸다."""

    if not banned:
        return
    from pydantic_ai import ModelRetry

    @agent.output_validator
    def _reject_internal_vocab(ctx: Any, output: Any) -> Any:  # noqa: ANN401
        violations = find_violations(output, banned)
        if violations:
            shown = ", ".join(violations[:8])
            raise ModelRetry(
                f"내부 데이터 식별자({shown})를 본문에 쓰지 마라. "
                "감사인이 읽는 회계 언어로 바꿔 다시 작성하라."
            )
        return output


__all__ = ["EXCLUDED_FIELDS", "attach_vocab_guard", "banned_identifiers", "find_violations"]
