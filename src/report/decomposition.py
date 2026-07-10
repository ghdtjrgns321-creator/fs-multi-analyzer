"""변동 분해 엔진 (PLAN §6.5) — 소계 항등식으로 카드의 "왜"를 결정론 계산.

부모 소계(예: 영업이익)의 YoY 변동을 구성 계정(매출총이익·판관비...) 기여로 쪼갠다.
항등식은 config/decomposition.yaml(닫힌 표준 집합), 회사별 변형 선택은 |잔차| 최소
(손 정의 금지). 구성 합이 부모 변동과 다르면 미설명 잔차를 숨기지 않고 행으로 반환한다.
"""

from __future__ import annotations

from pathlib import Path

import yaml

DECOMPOSITION_PATH = Path("config/decomposition.yaml")


def load_bridges(path: Path = DECOMPOSITION_PATH) -> dict[str, dict]:
    """{parent_canonical: {variants: [...]}} 로드. 파일 부재는 빈 dict(분해 생략 graceful)."""

    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload.get("decomposition_bridges", {}) or {}


def _amounts_by_year(rows: list[dict], series_key: str) -> dict[int, float]:
    out: dict[int, float] = {}
    for r in rows or []:
        if str(r.get("series_key")) == series_key and r.get("amount") is not None:
            out[int(r["year"])] = float(r["amount"])
    return out


def decompose_change(
    series_rows: list[dict],
    parent_series_key: str,
    target_year: int,
    bridges: dict[str, dict] | None = None,
    _visited: frozenset[str] = frozenset(),
) -> dict | None:
    """부모 계정의 target_year YoY 변동을 구성 기여로 분해(브리지 구성은 재귀 펼침).

    반환 None: 브리지 없는 계정 / 부모·전기 데이터 없음 / 변동 0.
    반환 dict: {parent, variant, year, prior_year, delta,
                rows: [{account, prior, current, delta(부호 반영 기여), contribution_pct,
                        children?, child_residual?}],
                residual, residual_pct}
    구성 라벨에 자기 브리지가 있으면(예: 매출총이익=매출-원가) 하위 분해를 children으로
    첨부한다 — 소계를 블랙박스로 두지 않는다. children의 Δ·기여율은 최상위 부모 기준으로
    부호·비율을 맞춘다(Σchildren+child_residual == 그 행 Δ). _visited는 순환 브리지 가드.
    항등식 보장: sum(row.delta) + residual == delta (부동소수 오차 내).
    """

    bridges = bridges if bridges is not None else load_bridges()
    fs_div, _, parent_name = str(parent_series_key).partition(":")
    if not parent_name or parent_name in _visited:  # 접두 없음·순환 브리지는 분해 안 함
        return None
    variants = (bridges.get(parent_name) or {}).get("variants") or []
    if not variants:
        return None

    parent_amounts = _amounts_by_year(series_rows, parent_series_key)
    years = sorted(parent_amounts)
    if target_year not in parent_amounts:
        return None
    priors = [y for y in years if y < target_year]
    if not priors:
        return None
    prior_year = priors[-1]
    delta_parent = parent_amounts[target_year] - parent_amounts[prior_year]

    best: dict | None = None
    for variant in variants:
        components: list[dict] = variant.get("components", []) or []
        rows_out: list[dict] = []
        explained = 0.0
        for slot in components:
            label = str(slot.get("label", ""))
            sign = int(slot.get("sign", 1))
            # 동의 canonical 슬롯: 후보 중 양 연도 존재 계정을 합산(표준코드 계열 갈림 흡수 —
            # 예: 판매비와관리비[dart id] / 판매 및 일반관리비[ifrs id]).
            cur_sum = prev_sum = 0.0
            found = False
            for name in slot.get("accounts", []) or []:
                amounts = _amounts_by_year(series_rows, f"{fs_div}:{name}")
                cur, prev = amounts.get(target_year), amounts.get(prior_year)
                if cur is None or prev is None:
                    continue
                found = True
                cur_sum += cur
                prev_sum += prev
            if not found:
                rows_out.append(
                    {
                        "account": label,
                        "prior": None,
                        "current": None,
                        "delta": None,
                        "contribution_pct": None,
                    }
                )
                continue
            contribution = sign * (cur_sum - prev_sum)  # 부모 방향 기여(판관비 증가 → 음수)
            explained += contribution
            rows_out.append(
                {
                    "account": label,
                    "sign": sign,
                    "prior": prev_sum,
                    "current": cur_sum,
                    "delta": contribution,
                    "contribution_pct": (
                        round(contribution / abs(delta_parent) * 100, 1) if delta_parent else None
                    ),
                }
            )
        residual = delta_parent - explained
        candidate = {
            "parent": parent_series_key,
            "variant": str(variant.get("name", "")),
            "year": target_year,
            "prior_year": prior_year,
            "parent_prior": parent_amounts[prior_year],
            "parent_current": parent_amounts[target_year],
            "change_pct": (
                round(delta_parent / abs(parent_amounts[prior_year]) * 100, 1)
                if parent_amounts[prior_year]
                else None
            ),
            "delta": delta_parent,
            "rows": rows_out,
            "residual": residual,
            "residual_pct": round(residual / abs(delta_parent) * 100, 1) if delta_parent else None,
        }
        # 구성 결측이 있는 변형은 잔차가 커져 자연 탈락한다(별도 페널티 불필요).
        if best is None or abs(residual) < abs(best["residual"]):
            best = candidate

    if best is None:
        return None
    # 재귀 펼침 — 브리지 있는 구성(매출총이익·영업이익 등)은 하위 분해를 children으로 첨부.
    # 소계 블랙박스 방지: "GP -4,162억"에서 멈추지 않고 매출/원가 기여까지 낸다.
    for row in best["rows"]:
        if row.get("delta") is None or row["account"] not in bridges:
            continue
        child = decompose_change(
            series_rows,
            f"{fs_div}:{row['account']}",
            target_year,
            bridges,
            _visited=_visited | {parent_name},
        )
        if child is None:
            continue
        sign = int(row.get("sign", 1))
        # 손자까지 최상위 부모 기준으로 부호·기여율 재귀 정렬(세전→영업이익→GP 다단 펼침).
        row["children"] = _align_child_rows(child["rows"], sign, best["delta"])
        row["child_residual"] = sign * child["residual"]
    return best


def _align_child_rows(rows: list[dict], sign: int, top_delta: float) -> list[dict]:
    """하위 분해 행들의 Δ 부호를 상위 슬롯 부호로 뒤집고 기여율을 최상위 Δ 기준으로 재계산."""

    out = []
    for c in rows:
        adj = dict(c)
        if adj.get("delta") is not None:
            adj["delta"] = sign * adj["delta"]
            adj["contribution_pct"] = (
                round(adj["delta"] / abs(top_delta) * 100, 1) if top_delta else None
            )
        if adj.get("children"):
            adj["children"] = _align_child_rows(adj["children"], sign, top_delta)
        if adj.get("child_residual") is not None:
            adj["child_residual"] = sign * adj["child_residual"]
        out.append(adj)
    return out


__all__ = ["DECOMPOSITION_PATH", "decompose_change", "load_bridges"]
