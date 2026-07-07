"""관점 material 입력 규약 — 등수 힌트(review_queue) 제거, 계산값 전수 전달.

내부 관점(numeric/flow/change)은 코드가 추린 '수상한 후보 목록'을 받지 않고,
전 계정 계산값(account_metrics_panel)과 관계신호(latest_signal_snapshot)를 직접 받는다.
"""

from __future__ import annotations

from src.report.materials import flow_material, note_material, numeric_material, trend_material


def test_note_material_surfaces_all_passed_facts() -> None:
    # 주석 fact 전량 투입(흡수·메타는 호출 전 surfaced_note_facts에서 이미 제외됨).
    facts = [
        {
            "label": "특수관계자거래",
            "value": "195674381000000",
            "category": "특수관계자거래",
            "dimensions": "",
        },
        {"label": "소송", "value": "피소 진행 중", "category": "약정_우발", "dimensions": ""},
    ]
    mat = note_material(corp_code="00000000", year=2024, note_facts=facts)
    assert mat["note_facts"] == facts  # 전량 통과(누락·컷 0)
    assert "특수관계자" in str(mat["note_facts_role"])


def test_note_material_no_facts_warns() -> None:
    mat = note_material(corp_code="00000000", year=2024, note_facts=[])
    assert mat["note_facts"] == []
    assert "없음" in str(mat["note_facts_role"])


def test_note_material_includes_report_extracts(tmp_path) -> None:
    # Layer 1 추출물(report_extracts)이 note material에 실린다(S7 청크 교체).
    from src.db.normalized import write_report_extracts
    from src.schemas.extract import ExtractedItem

    items = [
        ExtractedItem(
            part="XI",
            label="제재",
            statement="과징금 1,012억 17백만원",
            evidence="XI.3",
            why_relevant="고위험",
        ),
        ExtractedItem(
            part="VIII",
            label="특수관계",
            statement="이재용 등기임원",
            evidence="VIII.1",
            why_relevant="지배구조",
        ),
        ExtractedItem(
            part="X",
            label="지급보증",
            statement="SETK 917,000천US$",
            evidence="X.1",
            why_relevant="계열 보증",
        ),
    ]
    write_report_extracts(items, "00300", 2023, data_dir=tmp_path)

    mat = note_material("00300", 2023, note_facts=[], data_dir=tmp_path)
    assert len(mat["report_extracts"]) == 3
    labels = {r["label"] for r in mat["report_extracts"]}
    assert {"제재", "특수관계", "지급보증"} == labels
    assert "Layer 1" in str(mat["report_extracts_role"])


def test_note_material_no_extracts_warns(tmp_path) -> None:
    # 리더 미실행(빈 DB) → 빈 리스트 + 경고(silent 0 금지 §9).
    mat = note_material("00999", 2015, note_facts=[], data_dir=tmp_path)
    assert mat["report_extracts"] == []
    assert "[경고]" in str(mat["report_extracts_role"])


def test_note_disclosures_indexes_report_extracts(tmp_path) -> None:
    # card_pipeline 그라운딩 색인이 report_extracts를 tokens·text로 반영.
    from src.report.card_pipeline import _note_disclosures

    note_mat = {
        "note_sections": [],
        "report_extracts": [
            {
                "part": "XI",
                "label": "제재",
                "statement": "과징금 1,012억 17백만원",
                "evidence": "XI.3",
                "why_relevant": "고위험",
            },
        ],
    }
    out = _note_disclosures(note_mat)
    assert len(out) == 1
    assert "제재" in out[0]["tokens"] and "XI" in out[0]["tokens"]
    assert "1,012억" in out[0]["text"]


def test_trend_material_includes_sce_cells() -> None:
    # SCE 2D 셀(자본변동)은 trend(추세) 관점 material에 실린다.
    sce = [{"change": "배당", "component": "이익잉여금", "amount": -98000.0}]
    report = {
        "corp_code": "",
        "target_year": "2024",
        "latest_signal_snapshot": {},
        "account_metrics_panel": [],
        "ratio_time_series": [],
        "sce_cells": sce,
    }
    mat = trend_material(report)
    assert mat["sce_cells"] == sce


# corp_code=""로 둬 _routed_events·_correction_history가 graceful 빈 리스트를 타게 한다.
_REPORT = {
    "corp_code": "",
    "target_year": "2024",
    "review_queue": [
        {"subject": "x", "key_evidence": "y", "risk_level": "Low", "materiality_score": 0.0}
    ],
    "ratio_summary": {"활동성": {}, "이익의 질": {}},
    "ratio_time_series": [],
    "account_level_series": [],
    "account_metrics_panel": [{"account": "유형자산취득"}],
    "latest_signal_snapshot": {
        "growth_divergences": [],
        "direction_checks": [],
        "cfs_ofs_gaps": [],
        "universal_scan": [],
    },
    "unmapped_material_accounts": [],
}

_QUEUE_KEYS = ("review_queue_reference", "flow_queue_reference", "change_queue_reference")


def _assert_no_queue(material: dict) -> None:
    for key in _QUEUE_KEYS:
        assert key not in material, f"{key} 가 남아있음(등수 힌트 미제거)"


def _assert_calc_preserved(material: dict) -> None:
    assert "account_metrics_panel" in material
    assert "latest_signal_snapshot" in material


def _assert_no_redundant_series(material: dict) -> None:
    # account_level_series는 panel과 중복(같은 계정·금액) → board에서 제거(프롬프트 비대 차단).
    assert "account_level_series" not in material, "중복 series 미제거"


def _assert_panel_columnar(material: dict) -> None:
    # 객체리스트가 아니라 컬럼형({columns, rows})으로 키 반복 제거.
    panel = material["account_metrics_panel"]
    assert isinstance(panel, dict) and "columns" in panel and "rows" in panel


def test_numeric_material_no_queue_keeps_calc() -> None:
    m = numeric_material(_REPORT)
    _assert_no_queue(m)
    _assert_calc_preserved(m)
    _assert_no_redundant_series(m)
    _assert_panel_columnar(m)


def test_flow_material_no_queue_keeps_calc() -> None:
    m = flow_material(_REPORT)
    _assert_no_queue(m)
    _assert_calc_preserved(m)
    _assert_no_redundant_series(m)
    _assert_panel_columnar(m)


def test_trend_material_no_queue_keeps_calc() -> None:
    m = trend_material(_REPORT)
    _assert_no_queue(m)
    _assert_calc_preserved(m)
    _assert_no_redundant_series(m)
    _assert_panel_columnar(m)
