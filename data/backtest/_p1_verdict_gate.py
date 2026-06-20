"""판정 매트릭스 게이트 — LLM 통독이 "주장"이 아니라 "셀 수 있는 산출물"임을 기계로 강제.

Why: LLM 검사는 컨텍스트 상태에 따라 깊이가 흔들린다(2026-06-10: 기계요약만 보고 "소실 9건"
보고 → 재탐색에서 7건이 거짓으로 판명). 성실함을 기대하지 않고, 안 읽으면 들키게 만든다:
회사연도×차원 매트릭스의 ①대상 전수 존재 ②전 칸 체크 ③판정+근거 실내용을 기계로 센다.

검사 규칙 (하나라도 어기면 exit 1):
- known_cases positive·runnable 전수가 섹션으로 존재 (누락 회사연도 = 다운스코프)
- 차원 6칸 전부 `- [x]` 체크 (`- [ ]` = 안 본 차원)
- 각 칸에 판정 + "근거" 키워드 + 최소 실내용 (빈 판정·근거 없는 판정 = hollow)

재현: uv run python data/backtest/_p1_verdict_gate.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DUMP_DIR = PROJECT_ROOT / "data/backtest/_review_dumps"
KC = PROJECT_ROOT / "data/backtest/known_cases.json"
DIMS_PER_TARGET = 6  # _p1_review_all.MATRIX_DIMS와 동기 (A~F)
MIN_CONTENT = 15  # 판정+근거 최소 글자수 — "정상" 한 단어로 때우는 hollow 차단


def load_targets(targets_path: Path | None) -> tuple[str, list[str]]:
    """(이름, 회사연도 전수) — _p1_review_all.load_targets()와 동일 규칙."""
    if targets_path is not None:
        payload = json.load(targets_path.open(encoding="utf-8"))
        out = [f"{c['corp_code']}/{y}" for c in payload["cases"] for y in c.get("run_years", [])]
        return str(payload.get("name", targets_path.stem)), out
    kc = json.load(KC.open(encoding="utf-8"))
    out = []
    for c in kc["cases"]:
        if c.get("label") == "positive" and c.get("runnable"):
            out.extend(f"{c['corp_code']}/{y}" for y in c.get("run_years", []))
    return "known", out


def main() -> None:
    tpath = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    name, tgts = load_targets(tpath)
    suffix = "" if name == "known" else f"_{name}"
    matrix = DUMP_DIR / f"_VERDICT_MATRIX{suffix}.md"
    if not matrix.exists():
        print(f"⛔ FAIL — 매트릭스 없음: {matrix} (_p1_review_all.py 먼저 실행)")
        sys.exit(1)
    text = matrix.read_text(encoding="utf-8")
    problems: list[str] = []

    # 섹션 분할: "## corp/year" 단위. 중복 섹션은 첫 섹션 채택 + FAIL —
    # last-wins면 빈 템플릿이 채워진 판정을 덮어 게이트 결과가 뒤집힌다.
    sections: dict[str, str] = {}
    for m in re.finditer(r"^## (\d{8}/\d{4})\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL):
        key = m.group(1)
        if key in sections:
            problems.append(f"{key}: 중복 섹션(수동 편집 오류 의심)")
        else:
            sections[key] = m.group(2)

    for tgt in tgts:
        body = sections.get(tgt)
        if body is None:
            problems.append(f"{tgt}: 섹션 누락(전수 위반)")
            continue
        checked = re.findall(r"^- \[x\] (.+?): *(.*)$", body, re.MULTILINE)
        unchecked = re.findall(r"^- \[ \] ", body, re.MULTILINE)
        if unchecked:
            problems.append(f"{tgt}: 미체크 차원 {len(unchecked)}개(안 본 차원)")
        if len(checked) < DIMS_PER_TARGET - len(unchecked):
            problems.append(f"{tgt}: 차원 행 부족({len(checked)}/{DIMS_PER_TARGET})")
        for dim, content in checked:
            if len(content.strip()) < MIN_CONTENT:
                problems.append(f"{tgt} [{dim[:12]}…]: 판정 내용 부실({len(content.strip())}자)")
                continue
            # "근거:" 키워드만 있고 뒤가 비면 hollow — 콜론 뒤 실내용을 별도로 센다
            ref = re.search(r"근거\s*[:：]\s*(.+)", content)
            if not ref or len(ref.group(1).strip()) < 5:
                problems.append(f"{tgt} [{dim[:12]}…]: 근거 인용 없음/빈 근거(hollow)")

    if problems:
        print(f"⛔ 판정 매트릭스 게이트 FAIL — {len(problems)}건:")
        for p in problems[:40]:
            print(f"  {p}")
        if len(problems) > 40:
            print(f"  … (외 {len(problems) - 40}건)")
        sys.exit(1)
    print(
        f"판정 매트릭스 게이트 PASS[{name}] — {len(tgts)} 회사연도 × {DIMS_PER_TARGET}차원 "
        "전 칸 판정+근거 확인"
    )


if __name__ == "__main__":
    main()
