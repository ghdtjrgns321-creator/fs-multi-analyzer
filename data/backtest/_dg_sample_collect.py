"""O4 표본 수집: finstate_xml로 분식·소형사 XBRL zip을 실제 다운로드 가능한지 +
받은 zip을 Arelle로 전개해 비금융 주석 fact가 들어있는지 표본 검증.

가용성(다운로드 됨?) × 추출(주석 있음?) 두 축을 회사연도별로 수치화.
API 키는 config.settings(.env)로만 접근 — 출력 금지.
재현: PYTHONPATH=. uv run python data/backtest/_dg_sample_collect.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

from config.settings import settings
from src.collect.opendart import DartCollector

sys.path.insert(0, str(Path(__file__).parent))
from _dg_arelle_probe import NOTE_KEYWORDS  # noqa: E402
from arelle import Cntlr  # noqa: E402

# 표본: 분식 소형사 위주(주석이 분식 탐지에 실제로 필요한 대상) + 검증용 연도.
# 회사명은 백테스트 결과에서 확인된 corp_code. 연도는 보유 raw 구간 내.
SAMPLES = [
    ("00409681", 2021, "아스트"),
    ("00409681", 2019, "아스트"),
    ("00657783", 2021, "모델솔루션"),
    ("01091382", 2020, "세토피아"),
    ("00127699", 2020, "유네코"),
    ("00480756", 2021, "이트론"),
    ("00526696", 2021, "웨이브일렉트로닉스"),
    ("00141273", 2020, "웰바이오텍"),
]


def probe_zip(zip_path: Path) -> dict:
    """다운로드된 zip을 Arelle로 전개해 fact 수·주석 카테고리 적중을 측정."""
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(tmp)
    entries = list(Path(tmp).glob("*.xbrl"))
    if not entries:
        return {"loaded": False, "reason": "no .xbrl"}
    cntlr = Cntlr.Cntlr(logFileName="logToBuffer")
    model = cntlr.modelManager.load(str(entries[0]))
    if model is None or not getattr(model, "facts", None):
        return {"loaded": False, "reason": "no facts"}
    note_hits = {k: 0 for k in NOTE_KEYWORDS}
    text_facts = 0
    for f in model.facts:
        if f.concept is None:
            continue
        local = f.concept.qname.localName if f.concept.qname else ""
        try:
            ko = f.concept.label(lang="ko") or ""
        except Exception:
            ko = ""
        hay = f"{local} {ko}"
        for cat, kws in NOTE_KEYWORDS.items():
            if any(kw in hay for kw in kws):
                note_hits[cat] += 1
        # 서술형(텍스트블록) fact 추정: 값이 길고 숫자가 아님
        v = f.value or ""
        if len(v) > 60 and not v.replace("-", "").replace(".", "").isdigit():
            text_facts += 1
    res = {
        "loaded": True,
        "fact_count": len(model.facts),
        "note_hits": note_hits,
        "note_hit_total": sum(note_hits.values()),
        "text_facts": text_facts,
    }
    cntlr.modelManager.close()
    return res


def main() -> None:
    if not settings.dart_api_key:
        print("DART_API_KEY 미설정 — 다운로드 불가")
        return
    collector = DartCollector()
    root = settings.data_dir
    results = []
    for corp, year, name in SAMPLES:
        row: dict = {"corp": corp, "name": name, "year": year}
        try:
            report = collector.annual_report(corp, year)
        except Exception as e:  # noqa: BLE001
            row.update(report_found=False, error=f"list:{type(e).__name__}")
            results.append(row)
            print(f"{name}/{year}: 사업보고서 조회 실패 {type(e).__name__}")
            continue
        if report is None:
            row.update(report_found=False)
            results.append(row)
            print(f"{name}/{year}: 사업보고서 없음")
            continue
        row["report_found"] = True
        row["rcept_no"] = report.rcept_no
        zip_path = root / corp / str(year) / "raw" / "financial_statement_xbrl.zip"
        try:
            ok = collector.save_xbrl_zip(report, zip_path)
        except Exception as e:  # noqa: BLE001
            row.update(downloaded=False, error=f"dl:{type(e).__name__}")
            results.append(row)
            print(f"{name}/{year}: 다운로드 실패 {type(e).__name__}")
            continue
        exists = zip_path.exists() and zip_path.stat().st_size > 0
        row["downloaded"] = bool(ok) and exists
        row["zip_bytes"] = zip_path.stat().st_size if exists else 0
        if not row["downloaded"]:
            results.append(row)
            print(f"{name}/{year}: zip 없음(API가 XBRL 미제공)")
            continue
        probe = probe_zip(zip_path)
        row["probe"] = probe
        results.append(row)
        if probe["loaded"]:
            print(
                f"{name}/{year}: zip {row['zip_bytes'] // 1024}KB | "
                f"facts={probe['fact_count']} 주석적중={probe['note_hit_total']} "
                f"텍스트fact={probe['text_facts']}"
            )
        else:
            print(f"{name}/{year}: zip 받았으나 추출 실패 {probe.get('reason')}")

    out = Path("data/backtest/_dg_sample_collect.json")
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    # 요약
    n = len(results)
    found = sum(1 for r in results if r.get("report_found"))
    dl = sum(1 for r in results if r.get("downloaded"))
    extracted = sum(1 for r in results if r.get("probe", {}).get("loaded"))
    notes = sum(1 for r in results if r.get("probe", {}).get("note_hit_total", 0) > 0)
    print(
        f"\n[표본 {n}사연도] 사업보고서존재={found} zip다운로드={dl} "
        f"Arelle추출={extracted} 비금융주석포함={notes}"
    )
    print(f"결과: {out}")


if __name__ == "__main__":
    main()
