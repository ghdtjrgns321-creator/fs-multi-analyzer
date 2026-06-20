"""SCE(자본변동표) 2D 구성요소 보존.

자본변동표는 (변동행 x 자본구성요소) 2차원 표다. 메인 long format(_dedupe_*)은 열 차원을
붕괴시켜 표 총계 한 줄만 남기므로, SCE는 이 모듈이 별도 2D long 프레임으로 보존한다.
account_detail 경로의 leaf를 raw 그대로 보존(component_raw)하면서 표준으로 묶고
(component_std), role(leaf/소계/총계/마커)로 합계축을 구분한다.
"""

from __future__ import annotations

import re
from functools import lru_cache
from itertools import combinations

import pandas as pd

from config.settings import settings
from src.normalize.config import SceComponentMap, load_sce_components, normalize_label
from src.normalize.mapper import AccountMapper
from src.normalize.schema import parse_amount

SCE_COMPONENT_COLUMNS = [
    "corp_code",
    "year",
    "fs_div",
    "sj_div",
    "source_order",
    "change_label",
    "change_canonical",
    "change_status",
    "change_role",
    "account_id",
    "component_raw",
    "component_std",
    "component_role",
    "detail_path",
    "amount",
    "prior_amount",
    "prior2_amount",
    "currency",
]

# account_detail 세그먼트 접미사: " [구성요소]"(신형) / " [member]"(구형).
_SUFFIX_RE = re.compile(r"\s*\[(구성요소|member)\]\s*$")
_AGGREGATE_LABEL_RE = re.compile(r"(합계|소계|계)$")


@lru_cache(maxsize=1)
def _sce_component_map() -> SceComponentMap:
    return load_sce_components(settings.config_dir / "canonical_accounts.yaml")


def _strip_component_suffix(segment: str) -> str:
    return _SUFFIX_RE.sub("", segment).strip()


def parse_component_path(detail: object) -> tuple[list[str], str]:
    """account_detail 파이프 경로 → (세그먼트 bare 라벨 리스트, leaf 라벨).

    leaf = 경로의 마지막 세그먼트(실제 귀속 구성요소). 앞 세그먼트는 소계 계층이다.
    """

    text = str(detail or "").strip()
    if not text or text.lower() == "nan":
        return ([], "")
    segments = [_strip_component_suffix(part) for part in text.split("|")]
    segments = [seg for seg in segments if seg]
    leaf = segments[-1] if segments else ""
    return (segments, leaf)


def classify_component(leaf: str, comp_map: SceComponentMap) -> tuple[str, str]:
    """leaf bare 라벨 → (component_std, role). 미매칭은 raw 보존·role=unmatched."""

    return comp_map.classify(leaf)


def _apply_sign(amount: float | None, sign: str) -> float | None:
    """변동행 부호 정규화. sign: 'minus'→-abs(차감) / 'plus'→+abs(가산) / 'none'→원본.

    차감변동은 raw 부호가 양수(배당)·음수(자기주식취득) 제각각이라 -abs로 음수 고정(단순 ×-1은
    이미 음수인 행을 뒤집어 검산이 깨짐). R2(라운드2): 통합 canonical(취득·처분 양방향)은 처분이
    +로 보존돼야 하므로 'plus'(+abs)로 분기. None은 그대로."""

    if amount is None:
        return amount
    if sign == "minus":
        return -abs(amount)
    if sign == "plus":
        return abs(amount)
    return amount


def _cell_value(value: object) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _group_vector(group: pd.DataFrame) -> tuple[tuple[str, float | None, float | None], ...]:
    cells = [
        (
            str(row["component_std"]),
            _cell_value(row.get("amount")),
            _cell_value(row.get("prior_amount")),
        )
        for _, row in group.iterrows()
    ]
    return tuple(
        sorted(
            cells,
            key=lambda cell: (
                cell[0],
                cell[1] is not None,
                -1.0 if cell[1] is None else cell[1],
                cell[2] is not None,
                -1.0 if cell[2] is None else cell[2],
            ),
        )
    )


def _disclosed_vector_matches(
    candidate: pd.DataFrame,
    reference: pd.DataFrame,
) -> bool:
    candidate_vector = _movement_vector(candidate)
    reference_vector = _movement_vector(reference)
    if not candidate_vector:
        return False
    reference_current_components = {
        component for component, cells in reference_vector.items() if cells[0] is not None
    }
    candidate_current_components = {
        component for component, cells in candidate_vector.items() if cells[0] is not None
    }
    if candidate_current_components != reference_current_components:
        return False
    compared = False
    for component in candidate_current_components:
        candidate_value = candidate_vector[component][0]
        reference_value = reference_vector[component][0]
        if candidate_value is None:
            continue
        if reference_value is None or not _amount_equal(candidate_value, reference_value):
            return False
        compared = True
    return compared


def _retag_stock_vectors(out: pd.DataFrame) -> pd.DataFrame:
    """Retag change rows whose component vector is identical to begin/restated-begin stock.

    Some filings reuse a movement concept for a restated opening balance. The label/concept is not
    reliable because the same concept can be a genuine delta elsewhere; the full component
    vector is.
    """

    if out.empty:
        return out
    required = {"fs_div", "change_label", "change_role", "component_std", "amount", "prior_amount"}
    if not required.issubset(out.columns):
        return out

    retag_labels: set[tuple[str, str]] = set()
    for fs_div, fs_frame in out.groupby("fs_div", dropna=False):
        reference_groups = [
            group
            for _, group in fs_frame[
                fs_frame["change_role"].isin(["begin", "restated_begin"])
            ].groupby("change_label", dropna=False)
        ]
        if not reference_groups:
            continue
        for label, group in fs_frame.groupby("change_label", dropna=False):
            roles = set(group["change_role"].astype(str))
            if roles <= {"begin", "total", "subtotal", "restated_begin"}:
                continue
            if any(_disclosed_vector_matches(group, reference) for reference in reference_groups):
                retag_labels.add((str(fs_div), str(label)))

    if not retag_labels:
        return out
    retag_mask = out.apply(
        lambda row: (str(row["fs_div"]), str(row["change_label"])) in retag_labels,
        axis=1,
    )
    out = out.copy()
    out.loc[retag_mask, "change_role"] = "restated_begin"
    return out


def _round_optional(value: object) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), settings.amount_round_digits)


def _movement_vector(group: pd.DataFrame) -> dict[str, tuple[float | None, float | None]]:
    vector: dict[str, list[float | None]] = {}
    for _, row in group.iterrows():
        component = str(row["component_std"])
        slot = vector.setdefault(component, [None, None])
        for idx, column in enumerate(["amount", "prior_amount"]):
            value = _round_optional(row.get(column))
            if value is None:
                continue
            slot[idx] = (
                value
                if slot[idx] is None
                else round(
                    float(slot[idx]) + value,
                    settings.amount_round_digits,
                )
            )
    return {component: (values[0], values[1]) for component, values in vector.items()}


def _sum_vectors(
    vectors: list[dict[str, tuple[float | None, float | None]]],
) -> dict[str, tuple[float | None, float | None]]:
    components = sorted({component for vector in vectors for component in vector})
    result: dict[str, tuple[float | None, float | None]] = {}
    for component in components:
        cells: list[float | None] = []
        for idx in range(2):
            values = [
                vector.get(component, (None, None))[idx]
                for vector in vectors
                if vector.get(component, (None, None))[idx] is not None
            ]
            cells.append(
                None if not values else round(float(sum(values)), settings.amount_round_digits)
            )
        result[component] = (cells[0], cells[1])
    return result


def _bare_amount(group: pd.DataFrame) -> float | None:
    bare = group[group["component_std"].astype(str) == "-"]
    if bare.empty:
        return None
    amount = _sum_optional(bare["amount"])
    if amount is None:
        return None
    return round(float(amount), settings.amount_round_digits)


def _matching_bare_subset(
    target_group: pd.DataFrame,
    groups: list[tuple[int, str, str, pd.DataFrame]],
    group_roles: dict[tuple[int, str, str], set[str]],
) -> list[pd.DataFrame] | None:
    target_amount = _bare_amount(target_group)
    if target_amount is None or _amount_equal(target_amount, 0.0):
        return None
    candidates: list[tuple[float, pd.DataFrame]] = []
    for block_id, label, account_id, group in groups:
        if group is target_group:
            continue
        if group_roles[(block_id, label, account_id)] != {"leaf"}:
            continue
        amount = _bare_amount(group)
        if amount is None or _amount_equal(amount, 0.0):
            continue
        candidates.append((amount, group))
    for size in range(1, min(4, len(candidates)) + 1):
        for subset in combinations(candidates, size):
            if _amount_equal(sum(item[0] for item in subset), target_amount):
                return [item[1] for item in subset]
    return None


def _vectors_equal(
    left: dict[str, tuple[float | None, float | None]],
    right: dict[str, tuple[float | None, float | None]],
) -> bool:
    return left == right


def _vector_is_zero(vector: dict[str, tuple[float | None, float | None]]) -> bool:
    values = [value for cells in vector.values() for value in cells if value is not None]
    return bool(values) and all(_amount_equal(value, 0.0) for value in values)


def _has_parent_subtotal_signal(
    target: pd.Series,
    children: list[pd.DataFrame],
    comp_map: SceComponentMap,
) -> bool:
    target_id = str(target.get("account_id", ""))
    child_ids = [str(child.iloc[0].get("account_id", "")) for child in children if not child.empty]
    has_dart_child = any(child_id.startswith("dart_") for child_id in child_ids)
    if target_id.startswith("ifrs-full_") and has_dart_child:
        return True
    label_key = str(target.get("change_label", ""))
    normalized = normalize_label(label_key)
    if normalized and _AGGREGATE_LABEL_RE.search(normalized):
        return True
    target_detail = str(target.get("detail_path", "") or "").strip()
    if target_detail and any(
        str(child.iloc[0].get("detail_path", "") or "").strip().startswith(f"{target_detail}|")
        for child in children
        if not child.empty
    ):
        return True
    return bool(
        normalized
        and any(marker in normalized for marker in comp_map.parent_subtotal_label_markers)
    )


def _strict_bare_balance_ok(frame: pd.DataFrame, comp_map: SceComponentMap) -> bool:
    if frame.empty or "change_role" not in frame.columns:
        return False
    bare = frame[frame["component_std"].astype(str) == "-"].copy()
    if bare.empty:
        return False
    bare["_a"] = pd.to_numeric(bare["amount"], errors="coerce")
    roles = bare["change_role"].astype(str)
    if not bool((roles == "begin").any()) or not bool((roles == "total").any()):
        return False
    begin = float(bare.loc[roles == "begin", "_a"].sum())
    end = float(bare.loc[roles == "total", "_a"].sum())
    restated_delta = (roles == "restated_begin") & bare["change_label"].astype(str).isin(
        _restated_delta_labels(frame, comp_map)
    )
    movement = (roles == "leaf") | restated_delta
    leaf_sum = float(bare.loc[movement, "_a"].sum())
    tol = max(1000.0, abs(end) * 1e-7)
    return abs(begin + leaf_sum - end) <= tol


def _retag_parent_subtotal_vectors(out: pd.DataFrame, comp_map: SceComponentMap) -> pd.DataFrame:
    """Retag leaf rows that are taxonomy parent subtotals of other leaf movement rows."""

    if out.empty:
        return out
    required = {
        "fs_div",
        "change_label",
        "change_role",
        "account_id",
        "source_order",
        "component_std",
        "amount",
        "prior_amount",
    }
    if not required.issubset(out.columns):
        return out

    retag_groups: set[tuple[str, str, str, int]] = set()
    group_cols = ["_block_id", "change_label", "account_id"]
    for fs_div, fs_frame in out.groupby("fs_div", dropna=False, sort=False):
        fs_frame = _with_adjacent_block_ids(fs_frame)
        fs_retag_groups: set[tuple[str, str, str, int]] = set()
        candidate_groups = [
            (int(block_id), str(label), str(account_id), group)
            for (block_id, label, account_id), group in fs_frame[
                fs_frame["change_role"].astype(str).isin(["leaf", "subtotal"])
            ].groupby(group_cols, dropna=False, sort=False)
        ]
        target_groups = [
            (block_id, label, account_id, group)
            for block_id, label, account_id, group in candidate_groups
            if set(group["change_role"].astype(str)) == {"leaf"}
        ]
        if len(candidate_groups) < 2 or not target_groups:
            continue
        vectors = {
            (block_id, label, account_id): _movement_vector(group)
            for block_id, label, account_id, group in candidate_groups
        }
        group_roles = {
            (block_id, label, account_id): set(group["change_role"].astype(str))
            for block_id, label, account_id, group in candidate_groups
        }
        matched_blocks: set[int] = set()
        for target_block, target_label, target_id, target_group in target_groups:
            target_key = (target_block, target_label, target_id)
            target_vector = vectors[target_key]
            if _vector_is_zero(target_vector):
                continue
            preceding_segment: list[pd.DataFrame] = []
            for block_id, label, account_id, group in reversed(candidate_groups):
                if block_id >= target_block:
                    continue
                key = (block_id, label, account_id)
                if block_id in matched_blocks or group_roles[key] == {"subtotal"}:
                    break
                preceding_segment.append(group)
            if preceding_segment and _vectors_equal(
                target_vector,
                _sum_vectors(
                    [
                        _movement_vector(group)
                        for group in reversed(preceding_segment)
                        if not _vector_is_zero(_movement_vector(group))
                    ]
                ),
            ):
                if _has_parent_subtotal_signal(target_group.iloc[0], preceding_segment, comp_map):
                    fs_retag_groups.add((str(fs_div), target_label, target_id, target_block))
                    matched_blocks.add(target_block)
                    continue
            others = [
                (block_id, label, account_id, group)
                for block_id, label, account_id, group in candidate_groups
                if (block_id, label, account_id) != target_key
            ]
            matched_children: list[pd.DataFrame] | None = None
            for child_block, child_label, child_id, child_group in others:
                if _vectors_equal(target_vector, vectors[(child_block, child_label, child_id)]):
                    single_child = [child_group]
                    if _has_parent_subtotal_signal(target_group.iloc[0], single_child, comp_map):
                        matched_children = single_child
                        break
            if matched_children is not None:
                fs_retag_groups.add((str(fs_div), target_label, target_id, target_block))
                matched_blocks.add(target_block)
                continue
            for idx, first in enumerate(others):
                for second in others[idx + 1 :]:
                    child_vectors = [
                        vectors[(first[0], first[1], first[2])],
                        vectors[(second[0], second[1], second[2])],
                    ]
                    if _vectors_equal(target_vector, _sum_vectors(child_vectors)):
                        matched_children = [first[3], second[3]]
                        break
                if matched_children is not None:
                    break
            if matched_children is None and _has_parent_subtotal_signal(
                target_group.iloc[0],
                [item[3] for item in others],
                comp_map,
            ):
                matched_children = _matching_bare_subset(target_group, others, group_roles)
            if matched_children is None:
                continue
            if _has_parent_subtotal_signal(target_group.iloc[0], matched_children, comp_map):
                fs_retag_groups.add((str(fs_div), target_label, target_id, target_block))
                matched_blocks.add(target_block)

        if not fs_retag_groups:
            continue
        trial = fs_frame.copy()
        trial_groups = fs_retag_groups.copy()
        trial_mask = trial.apply(
            lambda row, groups=trial_groups: (
                (
                    str(row["fs_div"]),
                    str(row["change_label"]),
                    str(row["account_id"]),
                    int(row["_block_id"]),
                )
                in groups
            ),
            axis=1,
        )
        trial.loc[trial_mask, "change_role"] = "subtotal"
        if _strict_bare_balance_ok(trial, comp_map):
            retag_groups.update(fs_retag_groups)

    if not retag_groups:
        return out
    out = out.copy()
    out = _with_adjacent_block_ids(out)
    retag_mask = out.apply(
        lambda row: (
            (
                str(row["fs_div"]),
                str(row["change_label"]),
                str(row["account_id"]),
                int(row["_block_id"]),
            )
            in retag_groups
        ),
        axis=1,
    )
    out.loc[retag_mask, "change_role"] = "subtotal"
    return out.drop(columns=["_block_id"]).sort_index()


def _with_adjacent_block_ids(frame: pd.DataFrame) -> pd.DataFrame:
    """Assign block ids to adjacent runs of the same SCE change label/account within each fs."""

    out = frame.sort_values(["fs_div", "source_order"], kind="stable").copy()
    block_ids = pd.Series(index=out.index, dtype="int64")
    for _fs_div, fs_frame in out.groupby("fs_div", dropna=False, sort=False):
        group_key = fs_frame["change_label"].astype(str) + "\0" + fs_frame["account_id"].astype(str)
        block_ids.loc[fs_frame.index] = group_key.ne(group_key.shift()).cumsum().astype("int64")
    out["_block_id"] = block_ids.astype("int64")
    return out


def _amount_equal(left: float, right: float) -> bool:
    digits = settings.amount_round_digits
    return round(float(left), digits) == round(float(right), digits)


def _restated_delta_labels(fs_frame: pd.DataFrame, comp_map: SceComponentMap) -> set[str]:
    begin_vectors = {
        _group_vector(group)
        for _, group in fs_frame[fs_frame["change_role"].astype(str) == "begin"].groupby(
            "change_label", dropna=False
        )
    }
    if not begin_vectors:
        return set()
    labels: set[str] = set()
    restated = fs_frame[fs_frame["change_role"].astype(str) == "restated_begin"]
    for label, group in restated.groupby("change_label", dropna=False):
        label_text = str(label)
        if comp_map.is_stock_balance_label(label_text):
            continue
        if (
            comp_map.is_restated_delta_label(label_text)
            and _group_vector(group) not in begin_vectors
        ):
            labels.add(label_text)
    return labels


def _retag_stock_balance_rows(out: pd.DataFrame, comp_map: SceComponentMap) -> pd.DataFrame:
    """Retag bare subtotal/balance-looking rows that equal the running SCE stock balance."""

    if out.empty or not comp_map.stock_balance_label_markers:
        return out
    required = {"fs_div", "source_order", "change_label", "change_role", "component_std", "amount"}
    if not required.issubset(out.columns):
        return out

    retag_labels: set[tuple[str, str]] = set()
    for fs_div, fs_frame in out.groupby("fs_div", dropna=False, sort=False):
        bare = fs_frame[fs_frame["component_std"].astype(str) == "-"].copy()
        if bare.empty:
            continue
        restated_delta_labels = _restated_delta_labels(fs_frame, comp_map)
        role_series = bare["change_role"].astype(str)
        total_amount = float(
            pd.to_numeric(bare.loc[role_series == "total", "amount"], errors="coerce").sum()
        )
        subtotal_amount = float(
            pd.to_numeric(bare.loc[role_series == "subtotal", "amount"], errors="coerce").sum()
        )
        has_subtotal_bridge = bool(
            (role_series == "subtotal").any() and (role_series == "total").any()
        )
        bare = bare.sort_values("source_order", kind="stable")
        running = 0.0
        has_begin = False
        pending_leaf = 0.0
        for _idx, row in bare.iterrows():
            amount = _cell_value(row.get("amount"))
            if amount is None:
                continue
            role = str(row.get("change_role", ""))
            if role == "begin":
                running = amount + pending_leaf
                has_begin = True
                continue
            if role == "restated_begin":
                if str(row.get("change_label", "")) in restated_delta_labels:
                    if has_begin:
                        running += amount
                    else:
                        pending_leaf += amount
                else:
                    running = amount + pending_leaf
                    has_begin = True
                continue
            if role != "leaf":
                continue
            is_balance_label = comp_map.is_stock_balance_label(str(row.get("change_label", "")))
            is_running_balance = has_begin and _amount_equal(running, amount)
            is_subtotal_bridge = has_subtotal_bridge and _amount_equal(
                total_amount - subtotal_amount, amount
            )
            if is_balance_label and (is_running_balance or is_subtotal_bridge):
                retag_labels.add((str(fs_div), str(row.get("change_label", ""))))
                running = amount
                continue
            if has_begin:
                running += amount
            else:
                pending_leaf += amount

    if not retag_labels:
        return out
    out = out.copy()
    retag_mask = out.apply(
        lambda row: (str(row["fs_div"]), str(row["change_label"])) in retag_labels,
        axis=1,
    )
    out.loc[retag_mask, "change_role"] = "stock_balance"
    return out


def _sum_optional(series: pd.Series) -> float | None:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return None
    return float(numeric.sum())


def _has_mixed_sign(series: pd.Series) -> bool:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    numeric = numeric[numeric != 0]
    return bool((numeric > 0).any() and (numeric < 0).any())


def _apply_bare_sign(amount: float | None, sign: str, mixed_component_signs: bool) -> float | None:
    if sign == "minus" and mixed_component_signs:
        return amount
    return _apply_sign(amount, sign)


def _drop_nested_detail_children(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep parent component rows when parent and nested child detail paths both exist."""

    if frame.empty or "detail_path" not in frame.columns:
        return frame
    details = {idx: str(detail or "").strip() for idx, detail in frame["detail_path"].items()}
    drop: set[object] = set()
    for idx, detail in details.items():
        if not detail:
            continue
        for other_idx, other in details.items():
            if idx == other_idx or not other or len(other) <= len(detail):
                continue
            if other.startswith(f"{detail}|"):
                drop.add(other_idx)
    if not drop:
        return frame
    return frame.drop(index=list(drop))


def _add_derived_bare_totals(out: pd.DataFrame) -> pd.DataFrame:
    """Add flagged derived bare totals when a change row has component cells but no bare cell."""

    if out.empty:
        return out
    required = {
        "corp_code",
        "year",
        "fs_div",
        "sj_div",
        "source_order",
        "change_label",
        "change_canonical",
        "change_status",
        "change_role",
        "account_id",
        "component_std",
        "component_role",
        "amount",
    }
    if not required.issubset(out.columns):
        return out

    derived: list[dict[str, object]] = []
    group_cols = [
        "corp_code",
        "year",
        "fs_div",
        "sj_div",
        "change_label",
        "change_canonical",
        "change_status",
        "change_role",
        "account_id",
        "currency",
    ]
    summable_roles = {"leaf", "unmatched", "composite"}
    for _, group in out.groupby(group_cols, dropna=False, sort=False):
        if (group["component_std"].astype(str) == "-").any():
            continue
        summable = group[group["component_role"].astype(str).isin(summable_roles)]
        summable = _drop_nested_detail_children(summable)
        if summable.empty:
            continue
        amount = _sum_optional(summable["amount"])
        prior_amount = _sum_optional(summable.get("prior_amount", pd.Series(dtype=object)))
        prior2_amount = _sum_optional(summable.get("prior2_amount", pd.Series(dtype=object)))
        if amount is None and prior_amount is None and prior2_amount is None:
            continue
        first = group.iloc[0].to_dict()
        sign = str(first.pop("_deduction_sign", "none"))
        first.update(
            {
                "source_order": float(pd.to_numeric(group["source_order"], errors="coerce").min()),
                "component_raw": "",
                "component_std": "-",
                "component_role": "derived_total",
                "detail_path": "[derived:component_sum]",
                "amount": _apply_bare_sign(amount, sign, _has_mixed_sign(summable["amount"])),
                "prior_amount": _apply_bare_sign(
                    prior_amount,
                    sign,
                    _has_mixed_sign(summable.get("prior_amount", pd.Series(dtype=object))),
                ),
                "prior2_amount": _apply_bare_sign(
                    prior2_amount,
                    sign,
                    _has_mixed_sign(summable.get("prior2_amount", pd.Series(dtype=object))),
                ),
            }
        )
        derived.append(first)
    if not derived:
        return out
    return pd.concat([out, pd.DataFrame(derived, columns=SCE_COMPONENT_COLUMNS)], ignore_index=True)


def extract_sce_components(
    raw: pd.DataFrame,
    change_mapper: AccountMapper,
    comp_map: SceComponentMap,
) -> pd.DataFrame:
    """검증된 raw 프레임에서 SCE 2D long 프레임을 추출한다(열 차원 붕괴 없음).

    각 SCE 원천 행 = 표의 한 셀(변동행 x 구성요소). dedup는 정확 중복만 제거하고
    구성요소 차원은 보존한다.
    """

    if raw.empty or "sj_div" not in raw:
        return pd.DataFrame(columns=SCE_COMPONENT_COLUMNS)
    sce = raw[raw["sj_div"].astype(str) == "SCE"]
    if sce.empty:
        return pd.DataFrame(columns=SCE_COMPONENT_COLUMNS)

    rows: list[dict[str, object]] = []
    for source_order, (_, row) in enumerate(sce.iterrows()):
        detail = row.get("account_detail", "")
        _, leaf = parse_component_path(detail)
        component_std, role = classify_component(leaf, comp_map)
        # SCE 변동행은 id-label 모순 시 label(한글 공시명) 우선 — 본문 map_row(id-first)와 분리.
        # (예: dart_StockDividends 슬롯에 신고된 '주식선택권'이 배당으로 오집계되던 것 차단)
        change = change_mapper.map_change_row(row)
        # 차감/가산 부호 정규화(기초+Σ변동=기말 검산 일치). 단일방향 차감은 -abs, 통합 canonical
        # (자기주식변동 등)은 label로 취득(-)·처분(+) 분기(R2). raw 부호 혼재는 부호 고정이 흡수.
        label = str(row.get("account_nm", ""))
        sign = comp_map.deduction_sign(change.canonical, label, str(row.get("account_id", "")))
        # 변동행 role(begin/total/소계/조정후개시/leaf) — 검산(§F)은 leaf만 합산해
        # 소계·조정후개시 스톡의 이중계상을 막는다(N1/D5).
        change_role = comp_map.classify_change_role(change.canonical, label)
        rows.append(
            {
                "corp_code": row.get("corp_code", ""),
                "year": row.get("bsns_year", ""),
                "fs_div": row.get("fs_div", ""),
                "sj_div": "SCE",
                "source_order": source_order,
                "change_label": row.get("account_nm", ""),
                "change_canonical": change.canonical,
                "change_status": change.mapping_status,
                "change_role": change_role,
                "account_id": row.get("account_id", ""),
                "component_raw": leaf,
                "component_std": component_std,
                "component_role": role,
                "detail_path": str(detail or ""),
                "amount": _apply_sign(
                    parse_amount(row.get("thstrm_amount"), settings.amount_round_digits),
                    sign,
                ),
                "prior_amount": _apply_sign(
                    parse_amount(row.get("frmtrm_amount"), settings.amount_round_digits),
                    sign,
                ),
                "prior2_amount": _apply_sign(
                    parse_amount(row.get("bfefrmtrm_amount"), settings.amount_round_digits),
                    sign,
                ),
                "currency": row.get("currency", "KRW") or "KRW",
                "_deduction_sign": sign,
            }
        )

    out = pd.DataFrame(rows)
    # 셀 단위 정확 중복만 제거(붕괴 금지). 구성요소·변동행 차원은 그대로 둔다.
    out = out.drop_duplicates(
        subset=["fs_div", "change_label", "account_id", "component_raw", "detail_path", "amount"],
        keep="first",
    ).reset_index(drop=True)
    # member 부호는 raw를 충실히 보존한다. 차감변동(배당 등)은 _apply_sign이 전 셀에 -abs를 이미
    # 적용했고(grand+member 일관), 비차감 행에서 member가 grand과 부호 반대인 경우는 원공시 자체의
    # 내부 모순이다 — "grand이 진실"이라 추측해 뒤집으면 데이터 변조이고 소계를 방치해 새 불일치를
    # 만든다. 그 모순은 sce_horizontal_identity(가로항등)·sce_balance(검산)가 노출한다(48차 감사).
    out = _add_derived_bare_totals(out)
    out = _retag_stock_vectors(out)
    out = _retag_parent_subtotal_vectors(out, comp_map)
    out = _retag_stock_balance_rows(out, comp_map)
    return out.reindex(columns=SCE_COMPONENT_COLUMNS).reset_index(drop=True)


def sce_balance(sce_df: pd.DataFrame, fs_div: str) -> dict[str, object]:
    """SCE 자본 검산: 기초 + Σleaf변동 = 기말. bare 합계행(component_std='-')의 change_role 기반.

    leaf만 합산한다 — 소계(총포괄손익·기타포괄손익)·조정후개시(스톡)를 합산하면 이중계상이라
    검산이 깨진다(N1/D5 라운드1). begin/total 행이 없으면 computable=False(빈 검산을 통과로
    두지 않는다). change_role 컬럼이 없으면(구버전 정규화) 명시적 불능을 반환.
    """

    fs_frame = sce_df[sce_df["fs_div"] == fs_div].copy()
    bare = fs_frame[fs_frame["component_std"] == "-"].copy()
    if bare.empty or "change_role" not in bare.columns:
        return {"computable": False, "reason": "no_bare_or_role", "n_bare": int(len(bare))}
    bare["_a"] = pd.to_numeric(bare["amount"], errors="coerce")
    role = bare["change_role"].astype(str)
    has_begin = bool((role == "begin").any())
    has_total = bool((role == "total").any())
    begin = float(bare.loc[role == "begin", "_a"].sum())
    end = float(bare.loc[role == "total", "_a"].sum())
    comp_map = _sce_component_map()
    restated_delta = (role == "restated_begin") & bare["change_label"].astype(str).isin(
        _restated_delta_labels(fs_frame, comp_map)
    )
    movement = (role == "leaf") | restated_delta
    leaf_sum = float(bare.loc[movement, "_a"].sum())
    subtotal_rows = bare.loc[role == "subtotal"]
    subtotal_sum = float(subtotal_rows["_a"].sum())
    diff = begin + leaf_sum - end
    # 허용오차: 원 단위 공시 반올림 잔차(행별 ±1원 누적)·float 잔차는 검산 실패가 아니다.
    # 자본총계 대비 1e-7(0.00001%) 비례 + 1,000원 바닥 — 실제 결함(누락 leaf·부호오류)은 leaf
    # 규모(백만+)라 이 임계를 넘는다(00134176/2023 잔차 6원 vs 옛 소계 이중계상 38.8백만).
    tol = max(1000.0, abs(end) * 1e-7)
    # R3-b(라운드3): 소계 전체 채택을 잔여 보정으로 일반화한다. config에 선언된 소계는
    # residual = subtotal - disclosed_children_sum만 채택한다. 자식 전부 공시 시 residual≈0(D5
    # 무회귀), 자식 0개면 residual=subtotal(R3 라운드2와 동치), 일부 자식만 있으면 미공시 잔여만
    # 보정한다. config가 없는 소계는 기존 R3 fallback(소계 전체 채택)을 유지한다.
    leaf_only_diff = (
        diff  # 채택 전 leaf-only 검산값 — 채택해도 은닉하지 않고 보존(진단·이상추적용).
    )
    configured_residual = 0.0
    adopted_canonicals: list[str] = []
    unconfigured_subtotal_sum = subtotal_sum
    if "change_canonical" in bare.columns:
        leaf_rows = bare.loc[movement]
        for canonical, children in comp_map.subtotal_children.items():
            parent_rows = subtotal_rows.loc[subtotal_rows["change_canonical"] == canonical]
            if parent_rows.empty:
                continue
            subtotal_amount = float(parent_rows["_a"].sum())
            child_amount = float(
                leaf_rows.loc[leaf_rows["change_canonical"].isin(children), "_a"].sum()
            )
            residual = subtotal_amount - child_amount
            configured_residual += residual
            unconfigured_subtotal_sum -= subtotal_amount
            if abs(residual) > tol:
                adopted_canonicals.append(canonical)
    diff_residual_adopt = diff + configured_residual
    diff_adopt = diff_residual_adopt + unconfigured_subtotal_sum
    adopted_subtotal = False
    if abs(diff) > tol and abs(diff_residual_adopt) <= tol:
        diff = diff_residual_adopt
        leaf_sum = leaf_sum + configured_residual
        adopted_subtotal = True
        if not adopted_canonicals and configured_residual:
            adopted_canonicals = subtotal_rows["change_canonical"].tolist()
    elif abs(diff) > tol and abs(diff_adopt) <= tol:
        diff = diff_adopt
        leaf_sum = leaf_sum + configured_residual + unconfigured_subtotal_sum
        adopted_subtotal = True
        if not adopted_canonicals and "change_canonical" in bare.columns:
            adopted_canonicals = subtotal_rows["change_canonical"].tolist()
    return {
        "computable": has_begin and has_total,
        "begin": begin,
        "leaf_sum": leaf_sum,
        "end": end,
        "diff": diff,
        "leaf_only_diff": leaf_only_diff,
        "tol": tol,
        "ok": (has_begin and has_total and abs(diff) <= tol),
        "adopted_subtotal": adopted_subtotal,
        "adopted_canonicals": adopted_canonicals,
        "n_leaf": int(movement.sum()),
        "n_excluded": int((role.isin(["subtotal", "restated_begin", "stock_balance"])).sum()),
    }


# 가로항등 점검에서 비교할 자본 귀속 구성요소(연결 기준): 총계 = 지배지분 + 비지배지분.
_HORIZONTAL_GRAND = "-"
_HORIZONTAL_CONTROLLING = "지배기업소유주지분"
_HORIZONTAL_NCI = "비지배지분"


def sce_horizontal_identity(
    sce_df: pd.DataFrame,
    fs_div: str,
    tol_floor: float = 1_000_000.0,
    rel_tol: float = 0.005,
) -> list[dict[str, object]]:
    """SCE 가로 항등 점검: 변동행마다 총계(component_std='-') ≈ 지배기업소유주지분 + 비지배지분.

    세로 검산(sce_balance: 기초+Σleaf=기말)이 못 보는 축이다. 회사가 공시한 변동 총계가 그
    구성요소(지배+비지배) 합과 어긋나면 **원공시 자체의 내부 부호·금액 모순**이다(우리 정규화
    결함 아님 — 정규화는 raw 부호를 그대로 옮긴다, raw 대조로 확인). 부정 확정이 아니라 감사인이
    볼 리스크 후보로 노출한다. 위반 변동행 목록을 반환한다(없으면 빈 리스트).

    - 비지배지분 미공시(단일기업·NCI 없음) 변동행은 적용 불가 → skip(거짓양성 차단).
    - materiality 허용오차: tol_floor(기본 100만원, 다구성요소 백만단위 반올림 흡수)와 총계 대비
      rel_tol(기본 0.5%) 중 큰 값. 백만 미만 반올림 잔차는 모순으로 보지 않고, 실제 원공시 모순만
      노출한다(관측 사례: 비지배 부호 반대 42.5억·248억, 소계 부호 반대 800억 → 전부 임계 위).
      tol_floor/rel_tol은 sce_balance와 동일하게 함수 인자(기본값 둠, 호출부에서 조정 가능).
    """

    if sce_df.empty or "component_std" not in sce_df.columns:
        return []
    fs_frame = sce_df[sce_df["fs_div"] == fs_div]
    if fs_frame.empty or "change_role" not in fs_frame.columns:
        return []
    leaf = fs_frame[fs_frame["change_role"].astype(str) == "leaf"].copy()
    if leaf.empty:
        return []
    leaf["_a"] = pd.to_numeric(leaf["amount"], errors="coerce")
    violations: list[dict[str, object]] = []
    for label, group in leaf.groupby("change_label", dropna=False):
        components = group.dropna(subset=["_a"])

        def _sum(component_std: str, rows: pd.DataFrame = components) -> float | None:
            matched = rows[rows["component_std"].astype(str) == component_std]["_a"]
            return None if matched.empty else float(matched.sum())

        grand = _sum(_HORIZONTAL_GRAND)
        controlling = _sum(_HORIZONTAL_CONTROLLING)
        nci = _sum(_HORIZONTAL_NCI)
        if grand is None or controlling is None or nci is None:
            continue
        expected = controlling + nci
        diff = grand - expected
        tol = max(tol_floor, abs(grand) * rel_tol)
        if abs(diff) > tol:
            violations.append(
                {
                    "fs_div": fs_div,
                    "change_label": str(label),
                    "grand": grand,
                    "controlling": controlling,
                    "nci": nci,
                    "expected": expected,
                    "diff": diff,
                }
            )
    return violations
