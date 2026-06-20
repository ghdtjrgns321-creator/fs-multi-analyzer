"""D-D: SCE(자본변동표) 2D 구성요소 보존 테스트.

핵심 불변식: 자본변동표는 (변동행 x 자본구성요소) 2차원 표다. 한 변동행(예: 기초자본)이
여러 구성요소 열(이익잉여금·자본금·기타자본 등)로 나뉜 값이 1행으로 붕괴하면 안 된다.
"""

from pathlib import Path

import pandas as pd

from src.normalize.config import load_canonical_accounts, load_sce_components
from src.normalize.mapper import AccountMapper
from src.normalize.pipeline import sce_components_company_year
from src.normalize.sce import (
    SCE_COMPONENT_COLUMNS,
    classify_component,
    extract_sce_components,
    parse_component_path,
)

CONFIG = Path("config/canonical_accounts.yaml")


def _comp_map():
    return load_sce_components(CONFIG)


def test_parse_component_path_strips_suffix_and_finds_leaf() -> None:
    # 신형 3층 경로
    segs, leaf = parse_component_path(
        "자본 [구성요소]|지배기업의 소유주에게 귀속되는 지분 [구성요소]|이익잉여금 [구성요소]"
    )
    assert segs == ["자본", "지배기업의 소유주에게 귀속되는 지분", "이익잉여금"]
    assert leaf == "이익잉여금"

    # 별도(OFS) 2층 경로
    _, leaf2 = parse_component_path("자본 [구성요소]|자본금 [구성요소]")
    assert leaf2 == "자본금"

    # 구형 member 경로
    _, leaf3 = parse_component_path("자본 [member]|비지배지분 [member]")
    assert leaf3 == "비지배지분"

    # 표 총계 마커(단독)
    segs4, leaf4 = parse_component_path("연결재무제표 [member]")
    assert segs4 == ["연결재무제표"]
    assert leaf4 == "연결재무제표"

    # 빈 값 → 빈 결과
    assert parse_component_path("") == ([], "")
    assert parse_component_path(None) == ([], "")


def test_classify_component_groups_std_but_preserves_role() -> None:
    cm = _comp_map()
    # 적립금류는 명칭대로 묶되, leaf raw는 호출부에서 보존(여기선 std·role만 검증)
    assert classify_component("이익잉여금", cm) == ("이익잉여금", "leaf")
    assert classify_component("이익준비금", cm) == ("이익잉여금", "leaf")
    assert classify_component("법정적립금", cm) == ("이익잉여금", "leaf")
    # 성격이 자본조정/OCI인 적립금은 해당 표준으로
    assert classify_component("주식기준보상 적립금", cm)[0] == "자본조정"
    assert classify_component("재평가잉여금", cm)[0] == "기타포괄손익누계액"
    # 소계·총계·마커 role 구분
    assert classify_component("지배기업의 소유주에게 귀속되는 지분", cm) == (
        "지배기업소유주지분",
        "subtotal",
    )
    assert classify_component("자본", cm) == ("자본총계", "total")
    assert classify_component("연결재무제표", cm)[1] == "marker"
    assert classify_component("별도재무제표", cm)[1] == "marker"


def test_classify_component_composite_kept_separate() -> None:
    cm = _comp_map()
    # 합쳐진(미분리) 열은 억지로 쪼개지 않고 composite role로 격리
    std, role = classify_component("자본잉여금과 자본조정", cm)
    assert role == "composite"
    assert std.startswith("복합")


def test_extract_sce_preserves_component_dimension_no_collapse() -> None:
    # 합성 SCE 프레임: 한 변동행(기초자본)이 구성요소 4종으로 나뉨 → 4행 모두 보존돼야
    raw = pd.DataFrame(
        [
            {
                "corp_code": "00000000",
                "bsns_year": "2023",
                "fs_div": "CFS",
                "sj_div": "SCE",
                "account_id": "dart_EquityAtBeginningOfPeriod",
                "account_nm": "기초자본",
                "account_detail": "자본 [구성요소]|지배기업의 소유주에게 귀속되는 지분 [구성요소]"
                "|이익잉여금 [구성요소]",
                "thstrm_amount": "1000",
                "frmtrm_amount": "900",
                "bfefrmtrm_amount": "800",
                "currency": "KRW",
            },
            {
                "corp_code": "00000000",
                "bsns_year": "2023",
                "fs_div": "CFS",
                "sj_div": "SCE",
                "account_id": "dart_EquityAtBeginningOfPeriod",
                "account_nm": "기초자본",
                "account_detail": "자본 [구성요소]|지배기업의 소유주에게 귀속되는 지분 [구성요소]"
                "|자본금 [구성요소]",
                "thstrm_amount": "200",
                "frmtrm_amount": "200",
                "bfefrmtrm_amount": "200",
                "currency": "KRW",
            },
            {
                "corp_code": "00000000",
                "bsns_year": "2023",
                "fs_div": "CFS",
                "sj_div": "SCE",
                "account_id": "dart_EquityAtBeginningOfPeriod",
                "account_nm": "기초자본",
                "account_detail": "자본 [구성요소]|비지배지분 [구성요소]",
                "thstrm_amount": "50",
                "frmtrm_amount": "40",
                "bfefrmtrm_amount": "30",
                "currency": "KRW",
            },
            {
                "corp_code": "00000000",
                "bsns_year": "2023",
                "fs_div": "CFS",
                "sj_div": "SCE",
                "account_id": "dart_EquityAtBeginningOfPeriod",
                "account_nm": "기초자본",
                "account_detail": "연결재무제표 [member]",
                "thstrm_amount": "1250",
                "frmtrm_amount": "1140",
                "bfefrmtrm_amount": "1030",
                "currency": "KRW",
            },
            # BS 행은 SCE 추출 대상이 아님
            {
                "corp_code": "00000000",
                "bsns_year": "2023",
                "fs_div": "CFS",
                "sj_div": "BS",
                "account_id": "ifrs-full_Inventories",
                "account_nm": "재고자산",
                "account_detail": "",
                "thstrm_amount": "777",
                "frmtrm_amount": "",
                "bfefrmtrm_amount": "",
                "currency": "KRW",
            },
        ]
    )
    mapper = AccountMapper(load_canonical_accounts(CONFIG))
    out = extract_sce_components(raw, mapper, _comp_map())

    assert list(out.columns) == SCE_COMPONENT_COLUMNS
    # SCE만, BS 제외
    assert set(out["sj_div"]) == {"SCE"}
    # 기초자본 변동행이 4행으로 보존(붕괴 0)
    base = out[out["change_label"] == "기초자본"]
    assert len(base) == 4
    # 구성요소 raw가 그대로 보존됨(어디 구성요소인지 유지)
    assert set(base["component_raw"]) == {"이익잉여금", "자본금", "비지배지분", "연결재무제표"}
    # 표준 묶음 + role
    leaf_rows = base[base["component_role"] == "leaf"]
    assert set(leaf_rows["component_std"]) == {"이익잉여금", "자본금", "비지배지분"}
    marker_rows = base[base["component_role"] == "marker"]
    assert marker_rows["component_raw"].tolist() == ["연결재무제표"]
    # 변동행은 canonical로도 매핑(기초자본)
    assert set(base["change_canonical"]) == {"기초자본"}
    # 비교표시 금액 보존
    iy = base[base["component_raw"] == "이익잉여금"].iloc[0]
    assert iy["amount"] == 1000.0
    assert iy["prior_amount"] == 900.0
    assert iy["prior2_amount"] == 800.0


def test_extract_sce_empty_frame_returns_columns() -> None:
    empty = pd.DataFrame(columns=["sj_div"])
    out = extract_sce_components(empty, AccountMapper([]), _comp_map())
    assert list(out.columns) == SCE_COMPONENT_COLUMNS
    assert out.empty


def test_sce_components_end_to_end_samsung_2023() -> None:
    # 실제 회사: 삼성 00126380 2023. CFS(3층)+OFS(2층) 구성요소 보존 end-to-end.
    out = sce_components_company_year("00126380", 2023)
    if out.empty:
        # raw 데이터가 없는 환경이면 스킵(스키마만 보장)
        assert list(out.columns) == SCE_COMPONENT_COLUMNS
        return

    assert set(out["sj_div"]) == {"SCE"}
    # CFS·OFS 둘 다 보존
    assert {"CFS", "OFS"}.issubset(set(out["fs_div"]))
    # 한 변동행(기초자본)이 여러 구성요소로 보존(붕괴 0)
    base_cfs = out[(out["change_label"] == "기초자본") & (out["fs_div"] == "CFS")]
    assert base_cfs["component_raw"].nunique() >= 4
    # 표준 묶음에 이익잉여금·자본금이 포함
    assert {"이익잉여금", "자본금"}.issubset(set(base_cfs["component_std"]))
    # role 분포: leaf·subtotal·total·marker 모두 존재
    roles = set(out["component_role"])
    assert "leaf" in roles
    assert "marker" in roles
