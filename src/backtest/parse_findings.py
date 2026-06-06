"""Parse FSS finding HWP/PDF files into normalized UTF-8 text files."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import fitz
import olefile
import pdfplumber

SOURCE_DIR = Path(r"C:\Users\ghdtj\workspace\portfolio\local-ai-assist\data\finding")
OUT_DIR = Path("data/backtest/raw_text")
REPORT_PATH = Path("data/backtest/parse_report.jsonl")
CASE_BOUNDARY = re.compile(r"(?m)^\s*(?:사례\s*\d+|[IVX]+\.|[0-9]+\.\s|FSS\d{4}-\d+)")


@dataclass(frozen=True)
class ParseResult:
    source: str
    extension: str
    status: str
    parser: str
    output: str | None = None
    chars: int = 0
    case_markers: int = 0
    error: str | None = None


def main() -> None:
    args = _parse_args()
    files = _files(args.ext)
    batch = files[args.start : args.start + args.limit if args.limit else None]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("a", encoding="utf-8") as report:
        for path in batch:
            result = parse_file(path)
            report.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
            print(f"{result.status}\t{result.parser}\t{path.name}\t{result.chars}")


def parse_file(path: Path) -> ParseResult:
    try:
        text, parser = parse_hwp(path) if path.suffix.lower() == ".hwp" else parse_pdf(path)
        text = normalize_text(text)
        if not text.strip():
            raise ValueError("empty text")
        marked = mark_case_boundaries(text)
        out = OUT_DIR / f"{path.stem}.txt"
        out.write_text(marked, encoding="utf-8", newline="\n")
        return ParseResult(
            source=path.name,
            extension=path.suffix.lower(),
            status="ok",
            parser=parser,
            output=str(out),
            chars=len(marked),
            case_markers=marked.count("=== CASE_BOUNDARY"),
        )
    except Exception as exc:
        return ParseResult(
            source=path.name,
            extension=path.suffix.lower(),
            status="fail",
            parser="-",
            error=f"{type(exc).__name__}: {exc}",
        )


def parse_hwp(path: Path) -> tuple[str, str]:
    output = subprocess.run(
        ["hwp5txt", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if output.returncode == 0 and output.stdout.strip():
        return output.stdout, "hwp5txt"
    with olefile.OleFileIO(path) as ole:
        data = ole.openstream("PrvText").read()
    return data.decode("utf-16le", errors="replace"), "olefile.PrvText"


def parse_pdf(path: Path) -> tuple[str, str]:
    chunks: list[str] = []
    with pdfplumber.open(path) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            chunks.append(f"\n[PAGE {idx}]\n")
            chunks.append(page.extract_text(layout=True) or "")
            for table in page.extract_tables() or []:
                chunks.append(_render_table(table))
    text = "\n".join(chunks)
    if _looks_broken(text):
        doc = fitz.open(path)
        text = "\n".join(page.get_text("text") for page in doc)
        return text, "fitz"
    return text, "pdfplumber"


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def mark_case_boundaries(text: str) -> str:
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return f"\n\n=== CASE_BOUNDARY {count:03d} ===\n{match.group(0).strip()}"

    marked = CASE_BOUNDARY.sub(repl, text)
    if "=== CASE_BOUNDARY" not in marked:
        marked = "=== CASE_BOUNDARY 001 ===\n" + marked
    return marked


def _render_table(table: list[list[object]]) -> str:
    rows = ["\n[TABLE]"]
    for row in table:
        rows.append(" | ".join("" if cell is None else str(cell).strip() for cell in row))
    return "\n".join(rows)


def _looks_broken(text: str) -> bool:
    clean = text.strip()
    return len(clean) < 200 or clean.count("�") > max(5, len(clean) // 200)


def _files(ext: str) -> list[Path]:
    files = sorted(path for path in SOURCE_DIR.iterdir() if path.is_file())
    return [path for path in files if ext == "all" or path.suffix.lower() == f".{ext}"]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ext", choices=["all", "hwp", "pdf"], default="all")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
