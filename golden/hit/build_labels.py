"""검사2 정답지 빌더 — 재작성 정정에서 정답 계정 자동 추출 + 등록조건 게이트(설계 §3.1).

정답 신호는 현실이 만든다. t년 값이 t+1·t+2 보고서에서 실제로 바뀐 계정(series_normalize의
restated_later)은 "그 시점에 검토할 가치가 있었다"는 현실의 증명이다. 사람 라벨링 0으로 생성한다.

전후꼬임 방지 게이트: 우리 DB의 t년 값이 원본 접수분(as-filed) t년 값과 일치해야 등록한다.
불일치 = 우리 데이터가 이미 정정본 → 제외(입력에 미래정보 누수). 게이트 로직은 순수함수.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from golden.hit.check_hit import normalize_account_key
from src.report.grounding import _sig


@dataclass(frozen=True)
class Label:
    """정답지 1건 — 재표시된 계정·연도 + 등록조건 검증 상태."""

    corp_code: str
    year: int
    account_key: str  # 정규화 키(fs_div:계정명)
    source: str  # restated_later | sanction | injected
    reported: float | None = None  # 우리 DB의 t년 값
    restated: float | None = None  # 이후 보고서가 재표시한 값
    asfiled_verified: bool = False  # 등록조건(DB값==as-filed값) 통과 여부
    note: str = ""


@dataclass(frozen=True)
class LabelSet:
    """한 회사-연도의 정답지 묶음 + 미등록(게이트 탈락) 내역."""

    corp_code: str
    year: int
    labels: list[Label] = field(default_factory=list)
    excluded: list[Label] = field(default_factory=list)


def _identity_to_key(identity: str) -> str:
    """series_normalize identity(fs:sj:name)를 채점 정규화 키(fs:name)로."""

    return normalize_account_key(identity)


# 재표시 유의성 기본 임계 — 리터럴이 아니라 파라미터 기본값(호출·config로 조정). 실측 근거:
# 대형사(00117212)는 재표시 576건 중 대부분이 22.9조→22.9조 같은 0.0005% 반올림 노이즈다.
# 정답 계정은 "값이 유의하게 바뀐" 것 — 상대변화 임계로 반올림·재분류 잡음을 배제한다.
DEFAULT_MIN_REL_CHANGE = 0.01  # |restated-reported|/|reported| ≥ 1%
DEFAULT_MIN_ABS_CHANGE = 0.0  # 절대 하한(기본 미적용, 초소형 계정 과민 시 상향)


def _restatement_magnitude(reported: float | None, restated: float | None) -> tuple[float, float]:
    """(절대변화, 상대변화). reported=0이면 상대변화는 절대변화 자체 크기로 대체(0나눗셈 회피)."""

    if reported is None or restated is None:
        return 0.0, 0.0
    abs_change = abs(restated - reported)
    rel_change = abs_change / abs(reported) if reported else abs_change
    return abs_change, rel_change


def extract_restated_labels(
    corp_code: str,
    changes: list[dict],
    min_rel_change: float = DEFAULT_MIN_REL_CHANGE,
    min_abs_change: float = DEFAULT_MIN_ABS_CHANGE,
) -> list[Label]:
    """normalize_presentation의 changes에서 재표시(restated_later) 계정을 정답 후보로.

    sign_normalized(단순 표기변경)는 정답이 아니다 — 값이 실제로 바뀐 restated_later만.
    유의성 필터: 상대변화 ≥ min_rel_change **그리고** 절대변화 ≥ min_abs_change인 것만 등록
    (반올림·재분류 잡음 배제). 임계는 파라미터 — DESIGN §3.4 baseline 고정과 함께 조정한다.
    """

    out: list[Label] = []
    for change in changes or []:
        if change.get("kind") != "restated_later":
            continue
        year = change.get("year")
        if not isinstance(year, int):
            continue
        reported = _as_float(change.get("reported"))
        restated = _as_float(change.get("restated"))
        abs_change, rel_change = _restatement_magnitude(reported, restated)
        if rel_change < min_rel_change or abs_change < min_abs_change:
            continue  # 유의성 미달(반올림·재분류 잡음) — 정답 아님
        out.append(
            Label(
                corp_code=corp_code,
                year=year,
                account_key=_identity_to_key(str(change.get("series", ""))),
                source="restated_later",
                reported=reported,
                restated=restated,
                note=(
                    f"t+{int(change.get('restated_report', year)) - year} 보고서가 재표시"
                    f"(Δ{rel_change * 100:.1f}%)"
                ),
            )
        )
    return out


def _as_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def gate_asfiled(label: Label, asfiled_value: float | None) -> bool:
    """등록조건: 우리 DB의 t년 값(label.reported)이 원본 접수분 값과 유효숫자 일치.

    asfiled_value=None(원본 미조회)이면 미검증 → False(등록 보류). 값이 있으면 유효숫자 대조.
    """

    if label.reported is None or asfiled_value is None:
        return False
    return _sig(str(int(round(label.reported)))) == _sig(str(int(round(asfiled_value))))


def build_label_set(
    corp_code: str,
    year: int,
    changes: list[dict],
    asfiled_lookup: dict[str, float] | None = None,
) -> LabelSet:
    """정답 후보 추출 → 등록조건 게이트 적용 → LabelSet(등록/제외 분리).

    asfiled_lookup: {account_key: as-filed t년 값}. 없으면 전부 미검증(excluded, 보류).
    실제 as-filed 값 수집은 오케스트레이터가 하고(네트워크), 이 함수는 순수 게이트만.
    """

    candidates = [lbl for lbl in extract_restated_labels(corp_code, changes) if lbl.year == year]
    labels: list[Label] = []
    excluded: list[Label] = []
    for lbl in candidates:
        asfiled = (asfiled_lookup or {}).get(lbl.account_key)
        if gate_asfiled(lbl, asfiled):
            labels.append(
                Label(
                    **{
                        **lbl.__dict__,
                        "asfiled_verified": True,
                        "note": lbl.note + " · 원본대조 통과",
                    }
                )
            )
        else:
            reason = "원본 미조회(보류)" if asfiled is None else "DB값≠원본값(정정본 의심)"
            excluded.append(Label(**{**lbl.__dict__, "note": lbl.note + f" · 제외: {reason}"}))
    return LabelSet(corp_code=corp_code, year=year, labels=labels, excluded=excluded)


__all__ = [
    "Label",
    "LabelSet",
    "build_label_set",
    "extract_restated_labels",
    "gate_asfiled",
]
