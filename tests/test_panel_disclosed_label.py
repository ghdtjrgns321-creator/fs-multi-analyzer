"""설계3 — 공시 원문 라벨 승격 + 설계1 플래그의 패널 표면화.

LG생건 결함③: 정준명 '이자비용'이 FinanceCosts(금융원가)에 오매핑돼 서사까지
관통. LLM이 보는 패널에 공시 원문 계정명(disclosed_label)을 실어 라벨 권위를
공시로 옮긴다 — 정준명은 내부 조인 키로 강등.
"""

from __future__ import annotations

from src.signals.metrics_panel import account_metrics_panel


def _rows() -> list[dict]:
    # 결함③ 실사례 축약: 정준명 '이자비용' ↔ 공시 라벨 '금융원가'.
    return [
        {
            "series_key": "CFS:이자비용",
            "sj_div": "IS",
            "fs_div": "CFS",
            "year": 2024,
            "amount": 21_100_000_000.0,
            "label": "금융원가",
        },
        {
            "series_key": "CFS:이자비용",
            "sj_div": "IS",
            "fs_div": "CFS",
            "year": 2025,
            "amount": 38_700_000_000.0,
            "label": "금융원가",
        },
        {
            "series_key": "CFS:투자활동현금유출",
            "sj_div": "CF",
            "fs_div": "CFS",
            "year": 2024,
            "amount": -166_561_468_949.0,
            "label": "투자활동으로부터의 현금유출",
            "presentation_change": True,
        },
        {
            "series_key": "CFS:투자활동현금유출",
            "sj_div": "CF",
            "fs_div": "CFS",
            "year": 2025,
            "amount": -190_475_674_544.0,
            "label": "투자활동으로부터의 현금유출",
        },
    ]


def _panel() -> dict[str, dict]:
    entries = account_metrics_panel(_rows(), {"CFS": 1e13}, 2025)
    return {str(e["account"]): e for e in entries}


def test_disclosed_label_is_disclosure_original_name():
    panel = _panel()
    # 정준명(이자비용)이 아니라 회사가 공시한 이름(금융원가)이 LLM용 라벨.
    assert panel["CFS:이자비용"]["disclosed_label"] == "금융원가"
    assert panel["CFS:투자활동현금유출"]["disclosed_label"] == "투자활동으로부터의 현금유출"


def test_presentation_change_surfaces_as_note():
    panel = _panel()
    note = panel["CFS:투자활동현금유출"]["presentation_change"]
    assert note is not None and "2024" in note and "표기변경" in note
    # 플래그 없는 계정은 None(불필요한 안내 없음).
    assert panel["CFS:이자비용"]["presentation_change"] is None
    assert panel["CFS:이자비용"]["restated_prior_mismatch"] is None


def test_restated_mismatch_surfaces_as_note():
    rows = _rows()
    rows[0]["restated_later"] = True
    entries = account_metrics_panel(rows, {"CFS": 1e13}, 2025)
    entry = next(e for e in entries if e["account"] == "CFS:이자비용")
    assert entry["restated_prior_mismatch"] is not None
    assert "2024" in str(entry["restated_prior_mismatch"])
