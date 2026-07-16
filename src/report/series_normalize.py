"""시계열 표기변경 정규화 — cross-report 대조(설계1).

연도별 보고서의 당기값을 이어붙인 시계열은 회사의 표기 방식 변경(예: '유출액' 양수
→ '유출' 음수)을 경제적 사건처럼 보이게 한다(LG생건 결함①). 시스템은 이미 각
보고서의 재표시 전기값(prior_amount·prior2_amount)을 저장하므로, 그것을 권위로:

- 절대값 동일·부호 상이 → 표기변경. 최신 보고서 표기로 부호 정규화(presentation_change).
- 절대값 상이 → 재표시 후보(restated_later) — 값은 안 건드리고 신호로 표면화.

계정·부호 하드코딩 없음(전 계정 동일 규칙). 새 검사 규칙 발명이 아니라 보유 데이터 사용.
"""

from __future__ import annotations

import pandas as pd

# 금액 대조 허용오차(원) — accounting-precision: round 후 비교, 1원 단위 잔차 흡수.
AMOUNT_TOLERANCE = 1.0


def _series_identity(frame: pd.DataFrame) -> pd.Series:
    """계정 정체성 = fs_div:sj_div:(canonical|label) — _account_level_series와 동일 규칙."""

    base = frame["canonical"].where(
        frame["canonical"].notna() & (frame["canonical"] != ""), frame["label"]
    )
    return frame["fs_div"].astype(str) + ":" + frame["sj_div"].astype(str) + ":" + base.astype(str)


def _valid(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if number != number or number == 0.0:  # NaN·0은 대조 불가
        return None
    return number


def normalize_presentation(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """t년 당기값을 t+1·t+2년 보고서의 재표시값과 대조해 부호 정규화·재표시 플래그.

    반환: (presentation_change·restated_later 컬럼이 추가된 새 frame, 변경 내역 리스트).
    같은 계정-연도가 복수 행이면 어느 행의 재표시값인지 확정 불가 — 보수적으로 생략.
    """

    required = {"fs_div", "sj_div", "canonical", "label", "year", "amount"}
    if frame is None or frame.empty or not required.issubset(frame.columns):
        out = frame.copy() if frame is not None else frame
        return out, []
    out = frame.copy()
    out["presentation_change"] = False
    out["restated_later"] = False
    has_prior = "prior_amount" in out.columns
    has_prior2 = "prior2_amount" in out.columns
    if not has_prior and not has_prior2:
        return out, []
    changes: list[dict] = []
    identities = _series_identity(out)
    for identity in identities.unique():
        group = out[identities == identity]
        years = group["year"].astype(int)
        unique_years = {y: idx for y, idx in zip(years, group.index) if (years == y).sum() == 1}
        for year, idx in unique_years.items():
            current = _valid(out.at[idx, "amount"])
            if current is None:
                continue
            # 이 연도를 재표시한 이후 보고서들 — 최신 보고서가 권위(인접만 보면 새 아티팩트).
            candidates: list[tuple[int, float]] = []
            if has_prior and (year + 1) in unique_years:
                restated = _valid(out.at[unique_years[year + 1], "prior_amount"])
                if restated is not None:
                    candidates.append((year + 1, restated))
            if has_prior2 and (year + 2) in unique_years:
                restated = _valid(out.at[unique_years[year + 2], "prior2_amount"])
                if restated is not None:
                    candidates.append((year + 2, restated))
            if not candidates:
                continue
            report_year, restated = max(candidates)
            if abs(abs(current) - abs(restated)) <= AMOUNT_TOLERANCE:
                if (current > 0) != (restated > 0):
                    out.at[idx, "amount"] = -current
                    out.at[idx, "presentation_change"] = True
                    changes.append(
                        {
                            "series": identity,
                            "year": year,
                            "kind": "sign_normalized",
                            "reported": current,
                            "restated": restated,
                            "restated_report": report_year,
                        }
                    )
            else:
                out.at[idx, "restated_later"] = True
                changes.append(
                    {
                        "series": identity,
                        "year": year,
                        "kind": "restated_later",
                        "reported": current,
                        "restated": restated,
                        "restated_report": report_year,
                    }
                )
    return out, changes


__all__ = ["AMOUNT_TOLERANCE", "normalize_presentation"]
