"""분식사 정정본 삭제 + 정정 전 원본 수집(본문 CSV + 주석 TSV). 백업 후 교체.

각 분식 회사연도: 원본 rcept 확보 → 컨버터로 finstate_all CSV + extract_note_facts로 주석 →
정정본 백업(_backup_corrected) → 정정본 raw/duckdb/주석 삭제 → 원본 저장. 재정규화는 다음 단계.
확인 가능(원본 XBRL 가용)한 것만 처리, 나머지 skip. **기본 dry-run, --apply로 실제 실행.**

재현: PYTHONPATH=. uv run python data/backtest/_migrate_to_original.py [--apply] [corp_code]
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from _orig_vs_corr_compare import original_rcept
from _xbrl_to_finstate_csv import load_label_map, xbrl_to_frames

from src.collect.notes_xbrl import extract_note_facts, save_note_facts
from src.collect.opendart import DartCollector

col = DartCollector()
BACKUP = Path("data/_backup_corrected")

# 2015+ 분식 6사 (corp_code, 회사, 분식연도들) — 원본 가용한 것만 자동 처리
TARGETS = [
    ("00159616", "두산에너빌리티", [2017, 2018, 2019]),
    ("00409681", "아스트", [2018, 2019, 2020, 2021]),
    ("00118345", "디아이동일", [2016, 2017, 2018, 2019]),
    ("00657783", "모델솔루션", [2022, 2023]),
    ("00413046", "셀트리온", [2016, 2017, 2018, 2019, 2020]),
    ("01091382", "세토피아", [2018, 2019]),
]
M = 100_000_000  # 억원


def _orig_ni(frames: dict) -> str:
    """원본 변환 frames에서 당기순이익(CFS·IS·차원없음) 억원 표시."""
    cfs = frames.get("CFS")
    if cfs is None or cfs.empty:
        return "—"
    # 손익을 단일 포괄손익계산서(CIS)로만 신고하는 회사도 있어 IS·CIS 둘 다 본다.
    r = cfs[
        (cfs["account_id"].str.endswith("_ProfitLoss"))  # ifrs_/ifrs-full_ 둘 다(2019+ 택사노미)
        & (cfs["account_detail"] == "-")
        & (cfs["sj_div"].isin(["IS", "CIS"]))
    ]
    if r.empty:
        return "—"
    try:
        return f"{int(r.iloc[0]['thstrm_amount']) / M:,.0f}억"
    except (ValueError, TypeError):
        return "?"


def migrate(corp: str, fy: int, apply: bool) -> tuple[str, str]:
    cdir = Path(f"data/companies/{corp}/{fy}")
    if not cdir.exists():
        return ("skip", "디스크 없음")
    orig = original_rcept(corp, fy)
    if not orig:
        return ("skip", "원본 rcept 없음")
    label_map = load_label_map(corp, fy)  # 정정본 회사라벨(삭제 전)
    frames = xbrl_to_frames(orig, corp, fy, label_map)
    if frames is None or all(df.empty for df in frames.values()):
        return ("skip", "원본 XBRL 빈/변환실패")
    ni = _orig_ni(frames)
    cfs_n = len(frames.get("CFS", []))
    ofs_n = len(frames.get("OFS", []))
    if not apply:
        return ("dry", f"원본rcept={orig} 순이익={ni} CFS행={cfs_n} OFS행={ofs_n}")

    # 1) 백업(정정본 전체 보존)
    bdir = BACKUP / corp / str(fy)
    if bdir.exists():
        shutil.rmtree(bdir)
    shutil.copytree(cdir, bdir)

    # 2) 원본 주석 추출(원본 rcept finstate_xml zip)
    zp = Path(tempfile.gettempdir()) / f"mig_{orig}.zip"
    try:
        col._dart.finstate_xml(orig, save_as=str(zp))
        notes = extract_note_facts(zp)
    except Exception:
        notes = []

    # 3) 정정본 삭제(raw 재무 CSV·정규화 DB·주석)
    for rel in ("raw/finstate_all_CFS.csv", "raw/finstate_all_OFS.csv", "analysis.duckdb"):
        p = cdir / rel
        if p.exists():
            p.unlink()
    ntsv = cdir / "raw" / "notes_xbrl" / "note_facts.tsv"
    if ntsv.exists():
        ntsv.unlink()

    # 4) 원본 저장(finstate_all CSV + 주석 TSV)
    for fs, df in frames.items():
        if not df.empty:
            df.to_csv(cdir / "raw" / f"finstate_all_{fs}.csv", index=False, encoding="utf-8-sig")
    if notes:
        save_note_facts(notes, cdir / "raw" / "notes_xbrl")
    return ("done", f"순이익={ni} CFS={cfs_n} OFS={ofs_n} 주석={len(notes)} 백업={bdir}")


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
    args = [a for a in args if a != "--apply"]
    corp_filter = args[0] if args else None
    mode = "APPLY(실제 교체)" if apply else "DRY-RUN(계획만)"
    print(f"=== 분식사 원본 교체 {mode} ===")
    counts = {"done": 0, "dry": 0, "skip": 0}
    for corp, name, years in TARGETS:
        if corp_filter and corp != corp_filter:
            continue
        for fy in years:
            status, msg = migrate(corp, fy, apply)
            counts[status] = counts.get(status, 0) + 1
            print(f"  [{status:4}] {name}/{fy}: {msg}")
    print(f"\n합계: {counts}")
    if not apply:
        print("실제 교체하려면 --apply 추가")


if __name__ == "__main__":
    main()
