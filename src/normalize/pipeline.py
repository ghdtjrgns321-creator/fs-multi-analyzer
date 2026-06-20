"""L1 normalization pipeline for raw OpenDART financial statements."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from config.settings import settings
from src.normalize.config import (
    load_canonical_accounts,
    load_company_quirks,
    load_sce_components,
    normalize_label,
)
from src.normalize.mapper import (
    ALIAS,
    EXACT,
    ID_LABEL_CONFLICT,
    OTHER_CANONICAL,
    UNMAPPED,
    AccountMapper,
)
from src.normalize.sce import SCE_COMPONENT_COLUMNS, extract_sce_components
from src.normalize.schema import parse_amount, validate_raw_frame

# id-first로 매핑된 권위 등급(표준 id). N5 모순 플래그(id_label_conflict)도 id-first 매핑이므로
# 점수·dedup에서 EXACT와 동일 취급한다 — 플래그는 흔적일 뿐 매핑 거동을 바꾸지 않는다(무회귀).
_EXACT_GRADE = frozenset({EXACT, ID_LABEL_CONFLICT})

# IS↔CIS는 손익·포괄손익 통합신고(이자비용·지분법이익·당기순이익 등이 CIS로 신고)라 상호 호환.
# 나머지 재무제표 교차는 흐름조정·자본변동 행이 잔액/손익 칸으로 흡수되는 오매핑이므로 차단.
_STATEMENT_COMPATIBLE = {("IS", "CIS"), ("CIS", "IS")}

# account_id가 표준코드를 안 쓴 placeholder. 식별자가 아니므로 dedup 키로 쓰면 동명 유동/비유동
# 같은 서로 다른 line item이 한 키로 충돌해 소실된다(세토피아 CFS 파생상품부채·리스부채 사례).
_PLACEHOLDER_ACCOUNT_IDS = {"-표준계정코드 미사용-", "", "nan", "none", "None"}
# 자본금 분해 사니티(변종2): 회사가 납입자본 소계(=자본금+주식발행초과금)를 label='자본금' +
# id=ifrs-full_IssuedCapital로 위장 신고하면 라벨·id 신호가 없어 값으로만 잡힌다. "자본금 ≈
# 보통주자본금 + 주식발행초과금"이 정확히 성립할 때만 소계로 판정한다(자본잠식·우선주는 성립 안 해
# 무영향 — 단순 '자본금>자본총계' 가드의 오판 회피). 식별 id는 자본금 account_ids 중 두 종.
_ISSUED_CAPITAL_AGG_ID = "ifrs-full_IssuedCapital"  # 모호 집계 id(자본금/납입자본 양용)
_COMMON_STOCK_LEAF_ID = "dart_IssuedCapitalOfCommonStock"  # 보통주자본금 leaf
_CAPITAL_CANONICAL = "자본금"
_PAIDIN_CANONICAL = "납입자본"
_SHARE_PREMIUM_CANONICAL = "주식발행초과금"

OUTPUT_COLUMNS = [
    "corp_code",
    "year",
    "fs_div",
    "sj_div",
    "canonical",
    "account_id",
    "label",
    "amount",
    "prior_amount",
    "prior2_amount",
    "mapping_status",
    "currency",
]


def normalize_raw_file(path: Path, fs_div: str, mapper: AccountMapper) -> pd.DataFrame:
    """Normalize one raw finstate_all CSV file to long format."""

    raw = pd.read_csv(path, dtype=str)
    frame = validate_raw_frame(raw, fs_div)
    mapped = frame.apply(mapper.map_row, axis=1)
    output = pd.DataFrame(
        {
            "corp_code": frame["corp_code"],
            "year": frame["bsns_year"],
            "fs_div": frame["fs_div"],
            "sj_div": frame["sj_div"],
            "canonical": [item.canonical for item in mapped],
            "canonical_statement": [item.statement for item in mapped],
            "label_canonical": [item.label_canonical for item in mapped],
            "label_statement": [item.label_statement for item in mapped],
            "account_id": frame["account_id"],
            "label": frame["account_nm"],
            "amount": [
                parse_amount(value, settings.amount_round_digits)
                for value in frame["thstrm_amount"]
            ],
            "prior_amount": [
                parse_amount(value, settings.amount_round_digits)
                for value in _optional_amount_column(frame, "frmtrm_amount")
            ],
            "prior2_amount": [
                parse_amount(value, settings.amount_round_digits)
                for value in _optional_amount_column(frame, "bfefrmtrm_amount")
            ],
            "mapping_status": [item.mapping_status for item in mapped],
            "account_detail": frame.get("account_detail", ""),
            "currency": frame["currency"] if "currency" in frame else "KRW",
        }
    )
    arbitrated = _rescue_cross_statement(_arbitrate_conflicts(output), mapper)
    return _dedupe_canonical_rows(_dedupe_statement_rows(arbitrated))[OUTPUT_COLUMNS]


def _rescue_cross_statement(frame: pd.DataFrame, mapper: AccountMapper) -> pd.DataFrame:
    """다중표 구제(가산적): 강등(기타)된 행 중 account_id가 다른 표 canonical에 cross 등록돼
    있고 sj_div 호환이면 그 canonical로 remap. 기존 매핑(비-기타) 행은 절대 건드리지 않는다.

    근본원인: id→canonical 1:1이라 OCI 등 다중표 개념이 등록 statement 밖에서 강등되던 것.
    """

    if frame.empty:
        return frame
    aid = frame["account_id"].astype(str).str.strip()
    mask = (frame["canonical"] == OTHER_CANONICAL) & (aid != "")
    for idx in frame.index[mask]:
        result = mapper.cross_statement_match(frame.at[idx, "account_id"], frame.at[idx, "sj_div"])
        if result is not None:
            frame.at[idx, "canonical"] = result.canonical
            frame.at[idx, "canonical_statement"] = result.statement
            frame.at[idx, "mapping_status"] = result.mapping_status
    return frame


def _statement_compatible(sj_div: pd.Series, statement: pd.Series) -> pd.Series:
    """행의 sj_div와 canonical statement가 같은 표인지(또는 IS↔CIS 통합신고 호환쌍인지).

    빈 statement는 호환 판정 대상이 아니다(여기서는 False로 두고 호출부에서 빈값을 별도 처리).
    """

    sj = sj_div.astype(str)
    st = statement.astype(str)
    return pd.Series(
        [
            (s == c and c != "") or (s, c) in _STATEMENT_COMPATIBLE
            for s, c in zip(sj, st, strict=True)
        ],
        index=sj_div.index,
    )


def _arbitrate_conflicts(frame: pd.DataFrame) -> pd.DataFrame:
    """충돌(id_label_conflict) 행을 표 호환성(sj_div)으로 1단 중재하고, 비충돌 행은 기존
    statement_guard(표 불일치 강등)를 그대로 수행한다(_apply_statement_guard 흡수·확장).

    1단 표 호환성 (충돌 행 = label_canonical 비어있지 않음):
      - id_ok = compatible(sj_div, canonical_statement)
      - label_ok = compatible(sj_div, label_statement)
      - label_ok & not id_ok  → label 채택(canonical←label_canonical, 사유 id_label_conflict:table_label)
      - id_ok & not label_ok  → id 유지(현 동작)
      - not id_ok & not label_ok → 기타 중요 계정 강등(기존 statement_guard 드롭과 동일)
      - id_ok & label_ok      → id 유지(2단 범주 중재는 다음 단계 — 이번엔 변경 없음)

    비충돌 행: canonical.statement != sj_div이고 호환쌍도 아니면 기타 중요 계정으로 강등(흡수).

    Why: 공시자가 영문 id 슬롯에 다른 실질을 신고해 id-canonical이 행 sj_div와 다른 표를 가리킬 때,
    드롭만 하던 기존 statement_guard를 확장해 label 후보가 sj_div와 호환이면 그쪽을 채택한다.
    """

    if frame.empty:
        return frame
    scoped = frame.copy()
    canonical_statement = scoped["canonical_statement"].astype(str)
    label_statement = scoped["label_statement"].astype(str)
    label_canonical = scoped["label_canonical"].astype(str)
    sj_div = scoped["sj_div"].astype(str)

    is_mapped = scoped["canonical"] != OTHER_CANONICAL
    is_conflict = label_canonical != ""  # 충돌 행만 label 후보가 채워져 있다
    id_ok = _statement_compatible(sj_div, canonical_statement)
    label_ok = _statement_compatible(sj_div, label_statement)

    # 충돌 행: label만 표 호환 → label 채택
    take_label = is_mapped & is_conflict & label_ok & ~id_ok
    scoped.loc[take_label, "canonical"] = label_canonical[take_label]
    scoped.loc[take_label, "canonical_statement"] = label_statement[take_label]
    scoped.loc[take_label, "mapping_status"] = f"{ID_LABEL_CONFLICT}:table_label"

    # 충돌 행: 둘 다 비호환 → 강등(기존 statement_guard 드롭 동작 보존)
    conflict_both_bad = is_mapped & is_conflict & ~id_ok & ~label_ok

    # 비충돌 행: canonical statement가 sj_div와 불일치(빈값 아님)이고 호환쌍도 아니면 강등
    nonconflict_mismatch = is_mapped & ~is_conflict & (canonical_statement != "") & ~id_ok

    demote = conflict_both_bad | nonconflict_mismatch
    scoped.loc[demote, "canonical"] = OTHER_CANONICAL
    scoped.loc[demote, "mapping_status"] = UNMAPPED
    scoped.loc[demote, "canonical_statement"] = ""
    return scoped


def _apply_company_quirks(
    frame: pd.DataFrame,
    corp_code: str,
    year: int | str,
    quirks: dict[str, dict[str, dict[str, list]]],
) -> pd.DataFrame:
    """회사 고유 이탈 교정(quirk)을 corp_code/year에 매칭되는 행에만 적용한다.

    corp_code/year는 데이터 키다(코드 분기 하드코딩 아님). 매칭 quirk가 없으면 frame을
    그대로 반환한다(quirk 없는 회사·연도는 무변경 — 무회귀 보장).

    - account_overrides: (account_id, label) 매칭 행의 canonical을 force_canonical로 덮고
      mapping_status에 company_quirk:override 흔적을 남긴다.
    - alias_additions: label이 alias와 맞는 행을 canonical로 매핑하고
      mapping_status에 company_quirk:alias 흔적을 남긴다.
    """

    spec = quirks.get(str(corp_code), {}).get(str(year))
    if not spec or frame.empty:
        return frame
    scoped = frame.copy()
    aid = scoped["account_id"].astype(str)
    label_norm = scoped["label"].map(normalize_label)

    for override in spec.get("account_overrides", []):
        target_id = str(override.get("account_id", ""))
        target_label = normalize_label(override.get("label", ""))
        force_canonical = str(override.get("force_canonical", ""))
        if not force_canonical:
            continue
        match = (aid == target_id) & (label_norm == target_label)
        scoped.loc[match, "canonical"] = force_canonical
        scoped.loc[match, "mapping_status"] = "company_quirk:override"

    for addition in spec.get("alias_additions", []):
        target_canonical = str(addition.get("canonical", ""))
        target_alias = normalize_label(addition.get("alias", ""))
        if not target_canonical:
            continue
        match = label_norm == target_alias
        scoped.loc[match, "canonical"] = target_canonical
        scoped.loc[match, "mapping_status"] = "company_quirk:alias"

    return scoped


def _optional_amount_column(frame: pd.DataFrame, column: str) -> pd.Series:
    if column in frame:
        return frame[column]
    return pd.Series([None] * len(frame), index=frame.index)


def _dedup_identity(frame: pd.DataFrame) -> pd.Series:
    """dedup 식별자 컬럼. 실표준 account_id는 그대로 쓰고, placeholder(표준코드 미사용)는
    식별자가 아니므로 금액을 덧붙여 동명 유동/비유동 등 서로 다른 line item을 분별한다.

    정확중복(동일 금액)은 같은 키라 그대로 1행으로 합쳐지고, distinct account_id를 쓰는 표
    (OFS 등)는 영향이 없다. 금액 결측 placeholder는 모두 같은 키(금액축 정보 없음)로 합쳐진다.
    """

    aid = frame["account_id"].astype(str)
    is_placeholder = aid.str.strip().isin(_PLACEHOLDER_ACCOUNT_IDS)
    amount_num = pd.to_numeric(frame["amount"], errors="coerce").round()
    suffix = amount_num.astype("Int64").astype(str)  # 결측은 <NA> 문자열
    return aid.where(~is_placeholder, aid + "#" + suffix)


def _dedupe_statement_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep one representative row for an account within one statement/year."""

    if frame.empty:
        return frame
    key = ["_dedup_id", "label", "year", "fs_div", "sj_div", "_prior_key", "_prior2_key"]
    scoped = frame.copy()
    scoped["_dedup_id"] = _dedup_identity(scoped)
    for source, target in [("prior_amount", "_prior_key"), ("prior2_amount", "_prior2_key")]:
        scoped[target] = (
            pd.to_numeric(scoped[source], errors="coerce").round().astype("Int64").astype(str)
        )
    scoped["_detail_score"] = scoped.apply(_detail_score, axis=1)
    # amount에 None/비numeric이 섞이면 object dtype → .abs() 크래시(선진). numeric 변환.
    amount_num = pd.to_numeric(scoped["amount"], errors="coerce")
    scoped["_has_amount"] = amount_num.notna()
    scoped["_abs_amount"] = amount_num.abs().fillna(-1)
    return (
        scoped.sort_values(
            ["_detail_score", "_has_amount", "_abs_amount"],
            ascending=[False, False, False],
            kind="mergesort",
        )
        .drop_duplicates(key, keep="first")
        .drop(
            columns=[
                "_dedup_id",
                "_prior_key",
                "_prior2_key",
                "_detail_score",
                "_has_amount",
                "_abs_amount",
                "account_detail",
            ]
        )
        .reset_index(drop=True)
    )


def _dedupe_canonical_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep one canonical row per statement/year without summing component lines.

    placeholder account_id(표준코드 미사용) 행이 모호한 generic 라벨(예: 유동/비유동 구분 없는
    '파생상품부채')로 한 canonical에 묶이면, 대표 1행만 남기되 **금액이 다른 비대표 행은 드롭 대신
    '기타 중요 계정'으로 강등해 보존**한다. 소실(§D 미출현) 없이, 동시에 canonical 이중계상도 막는다
    (CFS는 placeholder+라벨매핑이라 묶이고, OFS는 distinct 표준 id라 본래 분리 생존).
    """

    if frame.empty:
        return frame
    scoped = frame.copy()
    mapped = scoped[scoped["canonical"] != OTHER_CANONICAL].copy()
    unmapped = scoped[scoped["canonical"] == OTHER_CANONICAL].copy()
    if mapped.empty:
        return scoped
    mapped["_canonical_score"] = mapped.apply(_canonical_score, axis=1)
    mapped["_abs_amount"] = pd.to_numeric(mapped["amount"], errors="coerce").abs().fillna(-1)
    # 동점 점수에서 금액 큰 행을 뽑기 전에 '비충돌'을 우선한다. id_label_conflict(영문 id 슬롯에
    # 다른 실질 신고 — 예: ifrs-full_IssuedCapital 슬롯에 '납입자본' 소계)는 그 canonical 귀속이
    # 불확실하므로, 같은 canonical을 깨끗이(exact/alias) 가리키는 행이 있으면 그쪽을 대표로 삼는다.
    # 그래야 진짜 자본금 leaf가 납입자본 소계(금액 큼)에 헤드라인을 뺏기지 않는다. 충돌행은 드롭이
    # 아니라 기타로 강등 보존(아래 demote)되어 소실은 없다.
    mapped["_not_conflict"] = (mapped["mapping_status"].astype(str) != ID_LABEL_CONFLICT).astype(
        int
    )
    mapped = mapped.sort_values(
        ["_canonical_score", "_not_conflict", "_abs_amount"],
        ascending=[False, False, False],
        kind="mergesort",
    )
    group = ["canonical", "year", "fs_div"]
    is_representative = ~mapped.duplicated(group, keep="first")
    rep_amount = pd.to_numeric(
        mapped.groupby(group)["amount"].transform(lambda series: series.iloc[0]),
        errors="coerce",
    )
    rep_prior = pd.to_numeric(
        mapped.groupby(group)["prior_amount"].transform(lambda series: series.iloc[0]),
        errors="coerce",
    )
    rep_prior2 = pd.to_numeric(
        mapped.groupby(group)["prior2_amount"].transform(lambda series: series.iloc[0]),
        errors="coerce",
    )
    rep_account_id = (
        mapped.groupby(group)["account_id"].transform(lambda series: series.iloc[0]).astype(str)
    )
    amount = pd.to_numeric(mapped["amount"], errors="coerce")
    prior = pd.to_numeric(mapped["prior_amount"], errors="coerce")
    prior2 = pd.to_numeric(mapped["prior2_amount"], errors="coerce")
    value_diff = (
        (amount.isna() != rep_amount.isna())
        | (amount.notna() & rep_amount.notna() & (amount != rep_amount))
        | (prior.isna() != rep_prior.isna())
        | (prior.notna() & rep_prior.notna() & (prior != rep_prior))
        | (prior2.isna() != rep_prior2.isna())
        | (prior2.notna() & rep_prior2.notna() & (prior2 != rep_prior2))
    )
    # 비대표 행이 모호한 한글 label(ALIAS)로 같은 canonical에 묶였고 대표와 금액이 다르면, 그것은
    # 중복이 아니라 distinct line item(유동/비유동 등 — 표준 id 없어 generic 라벨로 합쳐짐)이다.
    # 드롭(소실) 대신 '기타 중요 계정'으로 강등 보존. placeholder id도 label 매핑되므로 ALIAS 포함.
    alias_mapped = mapped["mapping_status"].astype(str) == ALIAS
    demote_alias = (~is_representative) & alias_mapped & value_diff
    # N4(라운드1): 서로 다른 표준 account_id가 같은 canonical로 수렴해도 distinct line item이다
    # (예: dart_장기차입금상환 + ifrs-full_유동성장기차입금상환 → '비유동차입금상환'). EXACT 비대표
    # 그냥 드롭되던 진짜 소실(00120526/2024 25.9억) — distinct id·다른 금액이면 강등 보존(ALIAS와
    # 같은 원리, 매칭 등급만 다름). 동일 id(namespace dup)·동일 금액은 기존대로 1행(이중계상 방지).
    exact_mapped = mapped["mapping_status"].astype(str).isin(_EXACT_GRADE)
    distinct_id = mapped["account_id"].astype(str) != rep_account_id
    demote_exact = (~is_representative) & exact_mapped & (distinct_id | value_diff) & value_diff
    demote = demote_alias | demote_exact
    reps = mapped[is_representative].copy()
    demoted = mapped[demote].copy()
    demoted["canonical"] = OTHER_CANONICAL
    demoted["mapping_status"] = UNMAPPED
    demoted["canonical_statement"] = ""
    return pd.concat([reps, demoted, unmapped], ignore_index=True).drop(
        columns=["_canonical_score", "_abs_amount", "_not_conflict"]
    )


def _canonical_score(row: pd.Series) -> int:
    if str(row.get("sj_div", "")) == str(row.get("canonical_statement", "")):
        return 6
    if str(row.get("mapping_status", "")) in _EXACT_GRADE:
        return 4
    canonical = str(row.get("canonical", ""))
    label = str(row.get("label", "")).replace(" ", "").strip()
    if canonical and label == canonical.replace(" ", "").strip():
        return 3
    return 2


def _detail_score(row: pd.Series) -> int:
    detail = str(row.get("account_detail", ""))
    fs_div = str(row.get("fs_div", ""))
    if fs_div == "CFS" and "연결재무제표" in detail:
        return 3
    if fs_div == "OFS" and ("별도재무제표" in detail or "재무제표" in detail):
        return 3
    if "[member]" not in detail:
        return 2
    return 1


def _empty_output() -> pd.DataFrame:
    return pd.DataFrame(columns=OUTPUT_COLUMNS)


def _normalize_if_present(path: Path, fs_div: str, mapper: AccountMapper) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size <= 5:
        return _empty_output()
    try:
        return normalize_raw_file(path, fs_div, mapper)
    except EmptyDataError:
        return _empty_output()


def normalize_company_year(
    corp_code: str,
    year: int | str,
    data_dir: Path | None = None,
    config_path: Path | None = None,
) -> pd.DataFrame:
    """Normalize CFS/OFS raw files for one company-year."""

    root = data_dir or settings.data_dir
    mapping_path = config_path or (settings.config_dir / "canonical_accounts.yaml")
    quirks_path = (
        config_path.parent if config_path else settings.config_dir
    ) / "company_quirks.yaml"
    mapper = AccountMapper(load_canonical_accounts(mapping_path))
    quirks = load_company_quirks(quirks_path)
    raw_dir = root / corp_code / str(year) / "raw"
    frames = [
        _normalize_if_present(raw_dir / f"finstate_all_{fs_div}.csv", fs_div, mapper)
        for fs_div in ("CFS", "OFS")
    ]
    nonempty = [frame for frame in frames if not frame.empty]
    if not nonempty:
        return _empty_output()
    combined = pd.concat(nonempty, ignore_index=True)
    # quirk는 _arbitrate_conflicts(파일별 normalize_raw_file 내부) 다음, corp_code/year를
    # 명시 인자로 아는 이 지점에서 적용한다(전역·하드코딩 금지). 매칭 없으면 무변경.
    quirked = _apply_company_quirks(combined, corp_code, year, quirks)
    decomposed = _enforce_capital_decomposition(quirked)
    return _flag_cross_fs_account_id_conflicts(decomposed)


def _enforce_capital_decomposition(frame: pd.DataFrame) -> pd.DataFrame:
    """납입자본 소계를 label='자본금'으로 위장 신고한 행(id=ifrs-full_IssuedCapital)을 교정한다.

    '자본금(위장 A) ≈ 보통주자본금(B) + 주식발행초과금(C)'가 fs_div 안에서 정확히 성립할 때만
    A를 납입자본으로 강등하고 B(기타로 밀려있을 수 있음)를 자본금으로 승격한다. 분해 항등식이라
    자본잠식(결손금↓로 자본금>자본총계가 정상)·우선주(자본금=보통주+우선주≠B+C) 케이스는 성립하지
    않아 무영향(단순 자본금>자본총계 가드의 오판을 구조적으로 회피).
    """

    if frame.empty or _CAPITAL_CANONICAL not in set(frame["canonical"]):
        return frame
    out = frame.copy()
    amt = pd.to_numeric(out["amount"], errors="coerce")
    for fs in out["fs_div"].unique():
        m = out["fs_div"] == fs
        a_mask = (
            m
            & (out["canonical"] == _CAPITAL_CANONICAL)
            & (out["account_id"].astype(str) == _ISSUED_CAPITAL_AGG_ID)
        )
        if not a_mask.any():
            continue
        b_mask = m & (out["account_id"].astype(str) == _COMMON_STOCK_LEAF_ID)
        c_mask = m & (out["canonical"] == _SHARE_PREMIUM_CANONICAL)
        if not b_mask.any() or not c_mask.any():
            continue
        b_val = amt[b_mask].max()
        c_val = amt[c_mask].max()
        a_val = amt[a_mask].max()
        if pd.isna(a_val) or pd.isna(b_val) or pd.isna(c_val):
            continue
        # 정확 분해(원 단위 정수)일 때만 위장 소계로 판정.
        if round(a_val) != round(b_val + c_val):
            continue
        # A(위장 자본금=실은 납입자본) → 납입자본. B(보통주자본금 leaf) → 자본금.
        out.loc[a_mask, "canonical"] = _PAIDIN_CANONICAL
        out.loc[a_mask, "mapping_status"] = "capital_decomp:paidin"
        out.loc[a_mask, "canonical_statement"] = "BS"
        out.loc[b_mask, "canonical"] = _CAPITAL_CANONICAL
        out.loc[b_mask, "mapping_status"] = "capital_decomp:capital"
        out.loc[b_mask, "canonical_statement"] = "BS"
    return out


def _flag_cross_fs_account_id_conflicts(frame: pd.DataFrame) -> pd.DataFrame:
    """Flag same-label CFS/OFS rows that carry different authoritative account IDs."""

    if frame.empty:
        return frame
    required = {"year", "sj_div", "label", "account_id", "fs_div", "mapping_status"}
    if not required.issubset(frame.columns):
        return frame
    scoped = frame.copy()
    aid = scoped["account_id"].astype(str).str.strip()
    valid_id = ~aid.isin(_PLACEHOLDER_ACCOUNT_IDS)
    fs_count = scoped.groupby(["year", "sj_div", "label"])["fs_div"].transform("nunique")
    id_count = scoped.groupby(["year", "sj_div", "label"])["account_id"].transform("nunique")
    conflict = valid_id & (fs_count > 1) & (id_count > 1)
    scoped.loc[conflict, "mapping_status"] = ID_LABEL_CONFLICT
    return scoped


def _empty_sce() -> pd.DataFrame:
    return pd.DataFrame(columns=SCE_COMPONENT_COLUMNS)


def sce_components_company_year(
    corp_code: str,
    year: int | str,
    data_dir: Path | None = None,
    config_path: Path | None = None,
) -> pd.DataFrame:
    """Extract the SCE 2D (변동행 x 자본구성요소) long frame for one company-year.

    메인 normalize_company_year와 별개의 산출물이다(메인 스키마·signals 무변경). 메인이
    붕괴시키는 SCE 구성요소 차원을 raw account_detail에서 펼쳐 보존한다.
    """

    root = data_dir or settings.data_dir
    mapping_path = config_path or (settings.config_dir / "canonical_accounts.yaml")
    mapper = AccountMapper(load_canonical_accounts(mapping_path))
    comp_map = load_sce_components(mapping_path)
    raw_dir = root / corp_code / str(year) / "raw"

    frames: list[pd.DataFrame] = []
    for fs_div in ("CFS", "OFS"):
        path = raw_dir / f"finstate_all_{fs_div}.csv"
        if not path.exists() or path.stat().st_size <= 5:
            continue
        try:
            raw = pd.read_csv(path, dtype=str)
            validated = validate_raw_frame(raw, fs_div)
        except EmptyDataError:
            continue
        frames.append(extract_sce_components(validated, mapper, comp_map))

    nonempty = [frame for frame in frames if not frame.empty]
    if not nonempty:
        return _empty_sce()
    return pd.concat(nonempty, ignore_index=True)
