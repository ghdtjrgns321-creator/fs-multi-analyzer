"""Stage1 deterministic backtest runner. No LLM calls."""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from config.settings import settings
from src.analysis_tools import load_normalized_financials
from src.backtest.score import (
    false_positive_count,
    positive_discovery_rate,
    positive_hit_rate,
    positive_track_hit_rate,
    score_case,
    track_false_positive_count,
)
from src.collect.spike import collect_company_years
from src.normalize.spike import normalize_company_years
from src.signals.red_flags import extract_red_flags
from src.signals.spike import run_signal_spike
from src.signals.universal import scan_cfs_ofs_gaps, scan_universal_signals

LABELS_PATH = Path("data/backtest/labels.csv")
RESULTS_PATH = Path("data/backtest/backtest_results.jsonl")
REPORT_PATH = Path("data/backtest/BACKTEST_REPORT.md")
CONTROL_RUN_YEARS = {"00126380", "00309503"}


def main() -> None:
    args = _args()
    labels_path = args.labels
    results_path, report_path = _output_paths(labels_path)
    labels = _labels(labels_path)
    results = []
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("w", encoding="utf-8", newline="\n") as out:
        for label in labels:
            years = _window(label)
            result = _run_one(label, years)
            results.append(result)
            out.write(json.dumps(result, ensure_ascii=False) + "\n")
            print(
                f"{label['company']}\tdiscovered={result.get('discovered')}"
                f"\tstrict={result.get('hit')}\ttrack={result.get('track_hit')}"
                f"\t{result.get('miss_reason')}"
            )
    report_path.write_text(_report(results), encoding="utf-8")
    print(f"wrote {results_path} and {report_path}")


def _run_one(label: dict[str, str], years: list[int]) -> dict[str, object]:
    try:
        _ensure_raw(label["corp_code"], years)
        available = [year for year in years if _has_finstate(label["corp_code"], year)]
        if not available:
            raise RuntimeError("no available finstate_all years")
        normalize_company_years(label["corp_code"], tuple(available))
        signal_report = run_signal_spike(label["corp_code"], available)
        frame = load_normalized_financials(label["corp_code"], available)
        signals = []
        legacy_signals = []
        for year in available:
            signals.extend(extract_red_flags(signal_report, year, include_all=True))
            signals.extend(scan_universal_signals(frame, year, include_all=True))
            signals.extend(scan_cfs_ofs_gaps(frame, year))
            legacy_signals.extend(extract_red_flags(signal_report, year, include_all=True))
            legacy_signals.extend(scan_universal_signals(frame, year, legacy_unified=True))
            legacy_signals.extend(scan_cfs_ofs_gaps(frame, year))
        return score_case(label, years, signals, frame, available, legacy_signals)
    except Exception as exc:
        return _failed(label, years, exc)


def _failed(label: dict[str, str], years: list[int], exc: Exception) -> dict[str, object]:
    return {
        "corp_code": label["corp_code"],
        "company": label["company"],
        "label": label["label"],
        "window": years,
        "fraud_accounts": _split(label.get("accounts", "")),
        "mapped": [],
        "fired_signals": [],
        "discovered": False,
        "hit": False,
        "legacy_hit": False,
        "track_hit": False,
        "miss_reason": f"실행실패:{type(exc).__name__}: {exc}",
    }


def _ensure_raw(corp_code: str, years: list[int]) -> None:
    missing = [year for year in years if not _has_finstate_files(corp_code, year)]
    if not missing:
        return
    for delay in (0, 2, 4):
        if delay:
            time.sleep(delay)
        result = collect_company_years(
            corp_code,
            tuple(missing),
            include_xbrl=False,
            include_notes=False,
        )
        if result.get("status") == "ok" and all(_has_finstate(corp_code, y) for y in missing):
            return


def _has_finstate(corp_code: str, year: int) -> bool:
    raw = settings.data_dir / corp_code / str(year) / "raw"
    paths = [raw / f"finstate_all_{fs_div}.csv" for fs_div in ("CFS", "OFS")]
    return any(path.exists() and path.stat().st_size > 5 for path in paths)


def _has_finstate_files(corp_code: str, year: int) -> bool:
    raw = settings.data_dir / corp_code / str(year) / "raw"
    return any((raw / f"finstate_all_{fs_div}.csv").exists() for fs_div in ("CFS", "OFS"))


def _labels(path: Path = LABELS_PATH) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    return [
        row
        for row in rows
        if row["dart_ok"].lower() == "true" and row["runnable"].lower() == "true"
    ]


def _window(row: dict[str, str]) -> list[int]:
    if row["corp_code"] in CONTROL_RUN_YEARS or not row.get("fraud_year_start"):
        return _split_years(row["run_years"])
    start = max(2015, int(row["fraud_year_start"]) - 2)
    end = int(row["fraud_year_end"])
    return list(range(start, end + 1))


def _split_years(value: str) -> list[int]:
    return [int(item) for item in str(value).split(";") if item]


def _split(value: str) -> list[str]:
    return [item for item in str(value or "").split(";") if item]


def _report(results: list[dict[str, object]]) -> str:
    discovered, total = positive_discovery_rate(results)
    strict_hit, _ = positive_hit_rate(results)
    track_hit, _ = positive_track_hit_rate(results)
    samsung = next((row for row in results if row["corp_code"] == "00126380"), None)
    kai = next((row for row in results if row["corp_code"] == "00309503"), None)
    lines = ["# BACKTEST_REPORT — Stage1 결정론 백테스트", ""]
    lines.append(f"- 발굴 recall: {discovered}/{total}")
    lines.append(f"- 기존 단일 통합 top10 strict hit: {strict_hit}/{total}")
    lines.append(f"- 새 두 트랙 quota hit: {track_hit}/{total}")
    lines.append(
        "- 채점에서 `cfs_ofs_gap`은 구조적 노이즈로 제외했다. "
        "raw fired_signals에는 남긴다."
    )
    if samsung:
        samsung_excluded = sum(
            1
            for signal in samsung.get("fired_signals", [])
            if signal.get("excluded_from_scoring")
        )
        lines.append(
            f"- 삼성전자 거짓양성 변화: 기존 raw 127 → 신규 raw "
            f"{len(samsung.get('fired_signals', []))}, cfs_ofs_gap 제외 {samsung_excluded}, "
            f"legacy 채점대상 {false_positive_count(samsung)}, "
            f"track 채점대상 {track_false_positive_count(samsung)}"
        )
    if kai:
        lines.append(
            f"- KAI 반응: 분식계정 발굴 여부 {kai.get('discovered')}, "
            f"legacy strict {kai['hit']}, track {kai.get('track_hit')} "
            f"({kai['miss_reason']})"
        )
    lines.append(
        "- mvp1 Tier 1 가드: `single_account_yoy` 채점 신호에서 CF 계정을 제외하고, "
        "`growth_divergence`는 양쪽 전년 기저가 동적 floor 이상·동일 부호일 때만 발화한다."
    )
    lines.append(
        "- `%/pp` 기반 신호의 normalized_strength는 `signal_strength_cap`으로 캡한다. "
        "raw 값은 증거로 보존한다."
    )
    lines.append("- 채점 hit 규칙·신호 임계값·상위10 기준은 변경하지 않았다.")
    lines.append(
        "- 두 트랙 quota는 자산 대비 규모로 게시 칸을 나누는 보조 잣대이며, "
        "legacy top10 결과와 병기한다."
    )
    lines.extend(
        [
            "",
            "| 회사 | label | window | available | discovered | legacy_strict | "
            "track_hit | miss_reason | fired |",
        ]
    )
    lines.append("|---|---|---|---|---|---|---|---|---:|")
    for row in results:
        lines.append(
            f"| {row['company']} | {row['label']} | {row['window']} | "
            f"{row.get('available_years', [])} | {row.get('discovered')} | "
            f"{row['hit']} | {row.get('track_hit')} | {row['miss_reason']} | "
            f"{len(row.get('fired_signals', []))} |"
        )
    lines.extend(["", "## 분식계정별 최고 강도와 순위"])
    lines.append("| 회사 | 분식계정 | status | 최고강도 | 순위 |")
    lines.append("|---|---|---|---:|---:|")
    for row in results:
        for score in row.get("account_scores", []) or []:
            lines.append(
                f"| {row['company']} | {score['source']} | {score.get('status')} | "
                f"{score.get('best_strength')} | {score.get('rank')} |"
            )
    lines.extend(["", "## 두 트랙 분식계정 상태"])
    lines.append("| 회사 | 분식계정 | track_status | track | track_rank | 최고강도 |")
    lines.append("|---|---|---|---|---:|---:|")
    for row in results:
        for score in row.get("track_account_scores", []) or []:
            signal = _track_signal_for_score(row, score)
            lines.append(
                f"| {row['company']} | {score['source']} | {score.get('status')} | "
                f"{score.get('track') or (signal.get('track') if signal else None)} | "
                f"{score.get('track_rank')} | "
                f"{score.get('best_strength')} |"
            )
    guard_lines = []
    for company, account in [
        ("두산에너빌리티", "미청구공사"),
        ("아스트", "재고자산"),
        ("디아이동일", "수익"),
    ]:
        row = next((item for item in results if item["company"] == company), None)
        if not row:
            continue
        score = next(
            (item for item in row.get("account_scores", []) if item["source"] == account),
            None,
        )
        if score:
            guard_lines.append(
                f"- {company} {account}: status {score.get('status')}, "
                f"rank {score.get('rank')}, strength {score.get('best_strength')}"
            )
    if guard_lines:
        lines.extend(["", "## mvp1 가드 확인", *guard_lines])
    if samsung:
        lines.append(
            "- 아스트 `cogs-vs-inventory` 관계 신호는 material 기저라 유지되고, "
            "0 근처 기저 폭발성 divergence는 제외된다."
        )
        lines.extend(["", "## 삼성전자 거짓양성 상위 10"])
        lines.append("| 순위 | 계정 | 유형 | 강도 | 값 | 연도 |")
        lines.append("|---:|---|---|---:|---:|---:|")
        for rank, signal in enumerate(samsung.get("false_positive_profile", []), start=1):
            lines.append(
                f"| {rank} | {signal['account']} | {signal['type']} | "
                f"{signal['normalized_strength']} | {signal['value']} | {signal['year']} |"
            )
        lines.extend(["", "## 삼성전자 두 트랙 상위 신호"])
        lines.append("| 트랙 | 순위 | 계정 | 유형 | 강도 | 값 | 규모비율 |")
        lines.append("|---|---:|---|---|---:|---:|---:|")
        for signal in samsung.get("track_false_positive_profile", []):
            lines.append(
                f"| {signal.get('track')} | {signal.get('track_rank')} | "
                f"{signal['account']} | {signal['type']} | "
                f"{signal['normalized_strength']} | {signal['value']} | "
                f"{_pct(signal.get('magnitude_ratio'))} |"
            )
    _append_clean_profiles(lines, results)
    lines.extend(["", "## 한계", "- LLM·외부검색 없이 L0~L2 숫자 신호만 본다."])
    lines.append("- 새 임계값을 만들지 않고 기존 red_flags/universal 신호만 채점했다.")
    lines.append(
        "- cfs_ofs_gap은 자회사 구조가 있으면 넓게 발생하므로 "
        "발굴·strict 판정에서 제외했다."
    )
    lines.append("- 중과실·연결특화·다년분식·단일연도 데이터는 Stage1 숫자 신호만으로 한계가 있다.")
    return "\n".join(lines) + "\n"


def _append_clean_profiles(lines: list[str], results: list[dict[str, object]]) -> None:
    clean_rows = [row for row in results if row["label"] == "clean"]
    if not clean_rows:
        return
    lines.extend(["", "## 정상 회사 채점 신호 상위 5"])
    lines.append("| 회사 | 채점신호수 | 상위5 | 잔여 아티팩트 후보 |")
    lines.append("|---|---:|---|---|")
    for row in clean_rows:
        top5 = row.get("false_positive_profile", [])[:5]
        top_text = "<br>".join(
            f"{item['account']} / {item['type']} / {item['normalized_strength']}"
            for item in top5
        )
        artifact_text = "<br>".join(_artifact_notes(top5)) or "없음"
        lines.append(
            f"| {row['company']} | {false_positive_count(row)} | {top_text} | "
            f"{artifact_text} |"
        )


def _artifact_notes(signals: list[dict[str, object]]) -> list[str]:
    notes = []
    for signal in signals:
        value = signal.get("value")
        if not isinstance(value, int | float):
            continue
        signal_type = signal.get("type")
        account = str(signal.get("account", ""))
        if signal_type in {"single_account_yoy", "universal_yoy"} and abs(value) >= 1000:
            notes.append(f"{account} YoY {value}")
        elif signal_type == "growth_divergence" and abs(value) >= 300:
            notes.append(f"{account} divergence {value}pp")
        elif "결손금" in account and abs(value) >= 1000:
            notes.append(f"{account} {value}")
    return notes


def _track_signal_for_score(
    row: dict[str, object],
    score: dict[str, object],
) -> dict[str, object] | None:
    target = score.get("source")
    for signal in row.get("track_scoring_top", []) or []:
        if signal.get("account") == target:
            return signal
    for signal in row.get("fired_signals", []) or []:
        if signal.get("account") == target:
            return signal
    return None


def _pct(value: object) -> str:
    if not isinstance(value, int | float):
        return ""
    return f"{float(value) * 100:.2f}%"


def _output_paths(labels_path: Path) -> tuple[Path, Path]:
    stem = labels_path.stem
    suffix = "" if stem == "labels" else stem.removeprefix("labels")
    if stem != "labels" and not suffix.startswith("_"):
        suffix = f"_{suffix}"
    return (
        RESULTS_PATH.with_name(f"backtest_results{suffix}.jsonl"),
        REPORT_PATH.with_name(f"BACKTEST_REPORT{suffix}.md"),
    )


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic Stage1 backtest.")
    parser.add_argument("--labels", type=Path, default=LABELS_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    main()
