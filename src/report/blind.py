"""blind 실행 — 관점 material에서 회사 정체를 제거한다(백테스트 사전지식 오염 차단).

정답지가 실명 확정 사건이라 LLM이 사건을 이미 알고 있을 수 있다. 프롬프트의 "외부 사실 금지"는
지시일 뿐 강제가 아니므로, 입력에서 정체 자체를 지운 뒤 같은 결과가 나오는지 대조한다.

가리는 것은 정체뿐 — 계정명·금액·연도는 손대지 않는다(분석 재료가 훼손되면 대조가 무의미).
파이프라인은 수정하지 않는다. build_suspicion_cards가 materials를 주입받으므로 여기서 만든
마스킹 결과를 넘기면 된다.
"""

from __future__ import annotations

import re
from typing import Any

TARGET_TOKEN = "[대상회사]"
PEER_TOKEN = "[동종사]"

# 값이 회사 정체인 필드 — 회사형 표기가 없는 이름(동종사 등)은 패턴으로 못 잡아 키로 판별한다.
# 프로필 원본이 그대로 실리는 경로가 있어(실측: 종목코드·법인번호·대표자·영문명) 식별 필드를 넓게 잡는다.
_TARGET_KEYS = frozenset(
    {
        "company_name",
        "target_company",
        "corp_code",
        "target_corp_code",
        "corp_name",
        "corp_name_eng",
        "stock_name",
        "stock_code",
        "jurir_no",
        "bizr_no",
        "ceo_nm",
        "adres",
        "hm_url",
        "ir_url",
    }
)
_PEER_CONTAINER = "peers"

# 한국 회사 표기: 앞에 붙는 (주)·㈜·주식회사, 뒤에 붙는 (주)·㈜.
# 후치형에 공백을 허용하면 "이후 (주)오르비텍"의 '이후 (주)'가 회사명으로 잡힌다(실측) — 붙은 것만.
_COMPANY_FORMS = re.compile(
    r"(?:\(주\)|㈜|주식회사)\s*[가-힣A-Za-z0-9]+|[가-힣A-Za-z0-9]+(?:\(주\)|㈜)"
)
_DOMAIN = re.compile(r"(?:https?://)?(?:www\.)?[A-Za-z0-9-]+\.(?:co\.kr|com|kr|net)")
# 영문 사명 — 프로필 영문명이 서술에 섞여 나온다.
_ENG_COMPANY = re.compile(r"[A-Z][A-Za-z&.\- ]{2,40}?(?:Co\.,? ?Ltd\.?|Inc\.|Corp\.|Company)")
# 회사형 표기에서 사명만 떼는 패턴 — 접두어 없이 맨 이름으로도 등장하기 때문(실측: '에이에스티지').
_STRIP_FORM = re.compile(r"^(?:\(주\)|㈜|주식회사)\s*|(?:\(주\)|㈜)$")


def company_aliases(report: dict[str, Any]) -> list[str]:
    """대상 회사를 가리키는 문자열 후보 — 표기가 달라도 같은 회사임을 놓치지 않게."""

    names = [str(report.get(k, "") or "") for k in ("company_name", "corp_name", "stock_name")]
    code = str(report.get("corp_code", "") or "")
    aliases = {n for n in names if n}
    for name in list(aliases):
        aliases.update({f"주식회사{name}", f"주식회사 {name}", f"(주){name}", f"㈜{name}"})
    if code:
        aliases.add(code)
    # 긴 것부터 지워야 "주식회사아스트"가 "아스트"로 부분 치환되고 남는 일이 없다.
    return sorted(aliases, key=len, reverse=True)


def mask_text(text: str, aliases: list[str]) -> str:
    """문장 속 회사 정체를 토큰으로 치환. 같은 회사는 같은 번호를 받는다(관계 서술 보존)."""

    out = str(text)
    for alias in aliases:
        out = out.replace(alias, TARGET_TOKEN)
    out = _DOMAIN.sub("[도메인]", out)
    out = _ENG_COMPANY.sub("[회사영문]", out)

    seen: dict[str, str] = {}

    def _swap(match: re.Match[str]) -> str:
        raw = match.group(0)
        if TARGET_TOKEN in raw:
            return raw
        if raw not in seen:
            seen[raw] = f"[회사{len(seen) + 1}]"
        return seen[raw]

    out = _COMPANY_FORMS.sub(_swap, out)
    # 접두어를 뗀 맨 이름도 같은 토큰으로 — 같은 문서가 '(주)오르비텍'과 '오르비텍'을 섞어 쓴다.
    for form, token in sorted(seen.items(), key=lambda kv: -len(kv[0])):
        bare = _STRIP_FORM.sub("", form).strip()
        if len(bare) >= 2:
            out = out.replace(bare, token)
    return out


def _walk(node: Any, aliases: list[str], peer_scope: bool = False) -> Any:
    if isinstance(node, str):
        return mask_text(node, aliases)
    if isinstance(node, list):
        return [_walk(v, aliases, peer_scope) for v in node]
    if isinstance(node, dict):
        out: dict[Any, Any] = {}
        for key, value in node.items():
            in_peers = peer_scope or key == _PEER_CONTAINER
            if key in _TARGET_KEYS and isinstance(value, str | int | float):
                out[key] = PEER_TOKEN if peer_scope else TARGET_TOKEN
            else:
                out[key] = _walk(value, aliases, in_peers)
        return out
    return node


def blind_materials(materials: dict[str, dict], report: dict[str, Any]) -> dict[str, dict]:
    """관점별 material 전체를 마스킹한 사본을 낸다(원본 불변)."""

    aliases = company_aliases(report)
    return {name: _walk(material, aliases) for name, material in materials.items()}


__all__ = ["PEER_TOKEN", "TARGET_TOKEN", "blind_materials", "company_aliases", "mask_text"]
