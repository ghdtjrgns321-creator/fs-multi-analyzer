"""SCE·주석층 신호 성격 측정 — 어떤 딱지(occurrence/metrics)가 맞는지 데이터로 결정.

계정 딱지(추세·백분위 등)를 통째 복사하면 서술형에 헛계산 노이즈. 각 층의 금액형/서술형 비율·
신규발생 수를 재서 occurrence(전 층 유의)·금액변화(금액형만)·full-metrics(부적합) 적용대상을 가른다.
실행: PYTHONPATH=. uv run python data/backtest/_e2e_sce_note_signal.py
"""

from __future__ import annotations

from pathlib import Path

from src.analysis_tools.data import load_notes_classified, load_sce_equity_components

CORPS = [("00126380", "삼성"), ("00112457", "대주")]
YEARS = [2021, 2022, 2023, 2024]
OUT = Path("data/backtest/_SCE_NOTE_SIGNAL_FIT.txt")


def _is_num(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip().replace(",", "")
    if text == "" or text == "-":
        return False
    try:
        number = float(text)
    except ValueError:
        return False
    return number == number  # not NaN


def _rows(df) -> list[dict]:
    return df.to_dict("records") if hasattr(df, "to_dict") else []


def _measure(rows: list[dict], key_fn, val_key: str, amount_is_num: bool) -> dict:
    years = sorted({str(r.get("year")) for r in rows if r.get("year") is not None})
    if not years:
        return {"total": 0}
    target = years[-1]
    prior = years[-2] if len(years) > 1 else None
    target_rows = [r for r in rows if str(r.get("year")) == target]
    total = len(target_rows)
    numeric = sum(1 for r in target_rows if _is_num(r.get(val_key)))
    # 신규발생: target 키가 직전연도에 없던(또는 0) 것.
    prior_keys = {key_fn(r) for r in rows if str(r.get("year")) == prior} if prior else set()
    appeared = sum(1 for r in target_rows if key_fn(r) not in prior_keys)
    return {
        "total": total,
        "numeric": numeric,
        "numeric_pct": round(100 * numeric / total, 1) if total else 0,
        "text_pct": round(100 * (total - numeric) / total, 1) if total else 0,
        "appeared": appeared,
        "target": target,
    }


def main() -> None:
    lines: list[str] = []
    for corp, name in CORPS:
        sce = _rows(load_sce_equity_components(corp, YEARS))
        note = _rows(load_notes_classified(corp, YEARS))

        sce_m = _measure(
            sce,
            key_fn=lambda r: (
                r.get("fs_div"),
                r.get("change_canonical") or r.get("change_label"),
                r.get("component_std"),
            ),
            val_key="amount",
            amount_is_num=True,
        )
        note_m = _measure(
            note,
            key_fn=lambda r: (r.get("concept") or r.get("label_ko"), str(r.get("dimensions"))),
            val_key="value",
            amount_is_num=False,
        )
        lines.append(f"=== {name} {corp} (target {sce_m.get('target')}) ===")
        lines.append(
            f"  SCE  총{sce_m['total']:4d} | 금액형 {sce_m['numeric_pct']:5.1f}% | 서술형 {sce_m['text_pct']:5.1f}% | 신규발생 {sce_m['appeared']:3d}"
        )
        lines.append(
            f"  주석 총{note_m['total']:5d} | 금액형 {note_m['numeric_pct']:5.1f}% | 서술형 {note_m['text_pct']:5.1f}% | 신규발생 {note_m['appeared']:4d}"
        )
    txt = "\n".join(lines)
    print(txt)
    OUT.write_text(txt, encoding="utf-8")
    print(f"저장: {OUT}")


if __name__ == "__main__":
    main()
