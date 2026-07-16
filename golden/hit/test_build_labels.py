"""검사2 정답지 빌더 단위 테스트 — 재표시 추출 + 등록조건 게이트."""

from __future__ import annotations

from golden.hit.build_labels import (
    build_label_set,
    extract_restated_labels,
    gate_asfiled,
)


def _changes():
    return [
        {
            "kind": "restated_later",
            "year": 2020,
            "series": "CFS:IS:매출채권",
            "reported": 100.0,
            "restated": 150.0,
            "restated_report": 2021,
        },
        {  # 단순 표기변경 — 정답 아님(값 안 바뀜)
            "kind": "sign_normalized",
            "year": 2020,
            "series": "CFS:CF:투자활동현금흐름",
            "reported": -50.0,
            "restated": 50.0,
            "restated_report": 2021,
        },
    ]


def test_extract_only_restated_not_sign_normalized():
    labels = extract_restated_labels("00117212", _changes())
    assert len(labels) == 1  # sign_normalized 제외
    assert labels[0].account_key == "CFS:매출채권"
    assert labels[0].source == "restated_later"


def test_materiality_filter_drops_rounding_noise():
    # 22.9조 → 22.9조(차이 0.0005%)는 반올림 잡음 → 기본 임계(1%)에서 제외.
    noise = [
        {
            "kind": "restated_later",
            "year": 2022,
            "series": "CFS:BS:자산총계",
            "reported": 22_963_651_561_449.0,
            "restated": 22_963_544_024_389.0,
            "restated_report": 2023,
        }
    ]
    assert extract_restated_labels("00258801", noise) == []
    # 임계를 0으로 낮추면 잡음도 포함(파라미터 동작 확인).
    assert len(extract_restated_labels("00258801", noise, min_rel_change=0.0)) == 1


def test_gate_passes_on_matching_asfiled_value():
    labels = extract_restated_labels("00117212", _changes())
    label = labels[0]  # reported=100
    assert gate_asfiled(label, 100.0) is True  # DB값==원본값
    assert gate_asfiled(label, 999.0) is False  # DB값≠원본값(정정본 의심)
    assert gate_asfiled(label, None) is False  # 원본 미조회 → 보류


def test_build_label_set_registers_only_gate_passed():
    changes = _changes()
    # 원본값 일치 → 등록.
    passed = build_label_set("00117212", 2020, changes, asfiled_lookup={"CFS:매출채권": 100.0})
    assert len(passed.labels) == 1
    assert len(passed.excluded) == 0
    assert passed.labels[0].asfiled_verified is True

    # 원본값 불일치 → 제외(전후꼬임 방지).
    failed = build_label_set("00117212", 2020, changes, asfiled_lookup={"CFS:매출채권": 999.0})
    assert len(failed.labels) == 0
    assert len(failed.excluded) == 1

    # 원본 미조회(lookup 없음) → 전부 보류(excluded).
    pending = build_label_set("00117212", 2020, changes)
    assert len(pending.labels) == 0
    assert len(pending.excluded) == 1


def test_build_label_set_filters_by_year():
    changes = _changes()
    # 2019년 정답지 요청 → 2020 재표시는 대상 아님.
    result = build_label_set("00117212", 2019, changes, asfiled_lookup={"CFS:매출채권": 100.0})
    assert len(result.labels) == 0
    assert len(result.excluded) == 0
