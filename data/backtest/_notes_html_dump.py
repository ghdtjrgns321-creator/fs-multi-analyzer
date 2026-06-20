"""원본/정정 rcept 주석 HTML 본문을 통째로 받아 텍스트로 저장(읽기전용).

sub_docs의 "재무제표 주석"·"연결재무제표 주석" 섹션 HTML을 받아 태그 제거 후 저장.
에이전트가 그 텍스트를 직접 통독해 부정 당시 주석인지 판단한다(값 아닌 서술·표 내용).
재현: PYTHONPATH=. uv run python data/backtest/_notes_html_dump.py <corp> <fy> <rcept> <tag>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import requests

from src.collect.opendart import DartCollector

col = DartCollector()


def strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = (
        text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    )
    return re.sub(r"[ \t]+", " ", text)


def main() -> None:
    corp, fy, rcept, tag = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    sub = col._dart.sub_docs(rcept)
    notes = sub[sub["title"].astype(str).str.contains("주석")]
    out = Path(f"data/backtest/_notes_text_{corp}_{fy}_{tag}.txt")
    total = 0
    with out.open("w", encoding="utf-8") as fh:
        for _, r in notes.iterrows():
            title = str(r["title"])
            try:
                html = requests.get(str(r["url"]), timeout=60).text
            except Exception as e:  # noqa: BLE001
                fh.write(f"\n\n===== {title} (수집실패: {e}) =====\n")
                continue
            text = strip_html(html)
            fh.write(f"\n\n===== {title} =====\n")
            fh.write(text)
            total += len(text)
            print(f"  {title}: {len(text):,}자")
    print(f"saved {out} ({total:,}자, {out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
