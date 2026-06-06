"""Extract machine-readable clues from parsed FSS finding texts."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

RAW_DIR = Path("data/backtest/raw_text")
OUT_PATH = Path("data/backtest/clues.jsonl")
SUMMARY_PATH = Path("data/backtest/clues_summary.json")

CASE_TITLE = re.compile(r"(?m)^(?P<title>[가-힣]\.\s+.{0,80}?사의[^\n]+)")
FSS_FILE = re.compile(r"^FSS\d{4}[-_]\d+")
YEAR = re.compile(r"(?:결정일|지적연도)\s*[:：]?\s*(\d{4})\s*년?")
PERIOD = re.compile(r"(?:회계결산일|분식 회계연도)\s*[:：]?\s*([0-9.\-~～ ]+)")
MONEY = re.compile(r"([△◇◆✡⃝0-9,\.]+\s*(?:조|억|백만|천만)?원)")
LISTING = {
    "유가": ["유가증권"],
    "코스닥": ["코스닥"],
    "비상장": ["비상장"],
    "상장": ["상장", "주권상장"],
}
ACCOUNT_WORDS = [
    "매출채권",
    "매도가능증권",
    "자산",
    "부채",
    "재고자산",
    "무형자산",
    "유형자산",
    "종속기업투자주식",
    "관계기업투자주식",
    "지분법적용투자주식",
    "대여금",
    "선급금",
    "매출",
    "매출원가",
    "충당부채",
    "파생금융부채",
    "파생금융자산",
    "영업이익",
    "당기순이익",
    "미지급금",
    "매입채무",
]
TYPE_RULES = [
    ("가공매출", ["가공", "허위매출", "허위 매출", "매출 허위"]),
    ("자산과대", ["과대계상", "허위계상", "과대평가"]),
    ("손상미인식", ["손상차손 미계상", "손상차손 과소", "손상 미인식"]),
    ("결산수정", ["결산수정", "전기오류", "오류수정"]),
]


@dataclass(frozen=True)
class CaseClue:
    case_id: str
    source_file: str
    지적연도: str | None
    분식_회계연도: str | None
    업종_사업_키워드: list[str] | None
    분식_유형: str | None
    분식_계정: list[str] | None
    분식_금액_규모: list[str] | None
    제재_내용: list[str] | None
    상장_여부: str | None
    식별단서_인용구: list[str]
    fs_detectable: bool
    fs_detectable_reason: str


def main() -> None:
    args = _args()
    files = sorted(RAW_DIR.glob("*.txt"))
    batch = files[args.start : args.start + args.limit if args.limit else None]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.append else "w"
    rows: list[CaseClue] = []
    with OUT_PATH.open(mode, encoding="utf-8", newline="\n") as out:
        for path in batch:
            for row in extract_file(path):
                rows.append(row)
                out.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")
    write_summary()
    print(f"extracted={len(rows)} output={OUT_PATH}")


def extract_file(path: Path) -> list[CaseClue]:
    text = path.read_text(encoding="utf-8", errors="replace")
    cases = split_cases(path.name, text)
    return [extract_case(path.name, idx, title, body) for idx, (title, body) in enumerate(cases, 1)]


def split_cases(name: str, text: str) -> list[tuple[str, str]]:
    clean = re.sub(r"=== CASE_BOUNDARY \d+ ===", "", text)
    matches = list(CASE_TITLE.finditer(clean))
    if FSS_FILE.match(name) or len(matches) < 2:
        return [(Path(name).stem, clean.strip())]
    cases: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(clean)
        body = clean[match.start() : end].strip()
        cases.append((match.group("title").strip(), body))
    return cases


def extract_case(source: str, idx: int, title: str, text: str) -> CaseClue:
    sentences = _sentences(text)
    accounts = _contains(ACCOUNT_WORDS, text)
    ftype = _fraud_type(text)
    detectable, reason = _fs_detectable(text, ftype, accounts)
    return CaseClue(
        case_id=f"{Path(source).stem}#{idx:03d}",
        source_file=source,
        지적연도=_first(YEAR, text) or _year_from_name(source),
        분식_회계연도=_first(PERIOD, text),
        업종_사업_키워드=_business_keywords(text),
        분식_유형=ftype,
        분식_계정=accounts or None,
        분식_금액_규모=_money_clues(text),
        제재_내용=_sanctions(text),
        상장_여부=_listing(text),
        식별단서_인용구=_quotes(sentences, accounts, ftype),
        fs_detectable=detectable,
        fs_detectable_reason=reason,
    )


def _fraud_type(text: str) -> str | None:
    for label, words in TYPE_RULES:
        if any(word in text for word in words):
            return label
    return "기타" if any(word in text for word in ["미기재", "과소계상", "위반"]) else None


def _fs_detectable(text: str, ftype: str | None, accounts: list[str]) -> tuple[bool, str]:
    if "독립성 위반" in text:
        return False, "감사인 독립성 위반은 공시 재무제표 숫자만으로 탐지하기 어렵다."
    if "특수관계자" in text and "주석미기재" in text:
        return False, "특수관계자 미공시는 전표·계약·주석 확인이 필요한 유형이다."
    if ftype in {"가공매출", "자산과대", "손상미인식", "결산수정"} or accounts:
        return True, "분식 유형 또는 계정 금액이 재무제표 숫자에 흔적을 남길 수 있다."
    return False, "원문상 재무제표 숫자 신호로 볼 계정·금액 단서가 부족하다."


def _business_keywords(text: str) -> list[str] | None:
    patterns = [
        r"(?:는|은)\s*([가-힣A-Za-z0-9· ]{2,30}?)(?:을|를) 주요 사업으로 하는",
        r"([가-힣A-Za-z0-9· ]{2,30})업을 영위",
    ]
    found: list[str] = []
    for pattern in patterns:
        found.extend(_clean_keyword(item) for item in re.findall(pattern, text))
    return _dedupe(found)[:3] or None


def _clean_keyword(value: str) -> str:
    return re.sub(r"^[는은]\s*", "", value.strip())


def _money_clues(text: str) -> list[str] | None:
    values = [match.group(1).replace(" ", "") for match in MONEY.finditer(text)]
    return _dedupe(values)[:8] or None


def _sanctions(text: str) -> list[str] | None:
    words = ["증선위", "과징금", "검찰고발", "고발", "감사인 지정", "임원 해임권고"]
    return _contains(words, text) or None


def _listing(text: str) -> str | None:
    for label, words in LISTING.items():
        if any(word in text for word in words):
            return label
    return None


def _quotes(sentences: list[str], accounts: list[str], ftype: str | None) -> list[str]:
    keys = accounts + ([ftype] if ftype else []) + ["과대계상", "과소계상", "허위계상", "미계상"]
    picked = [sentence for sentence in sentences if any(key and key in sentence for key in keys)]
    return picked[:2] or sentences[:1]


def _sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.다음함음])\s+", compact)
    return [part.strip()[:350] for part in parts if len(part.strip()) > 20]


def _contains(words: list[str], text: str) -> list[str]:
    return [word for word in words if word in text]


def _first(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _year_from_name(name: str) -> str | None:
    match = re.search(r"(20\d{2})", name)
    return match.group(1) if match else None


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def write_summary() -> None:
    if not OUT_PATH.exists():
        return
    rows = [json.loads(line) for line in OUT_PATH.read_text(encoding="utf-8").splitlines()]
    by_type = Counter(row.get("분식_유형") or "null" for row in rows)
    fs_true = sum(1 for row in rows if row.get("fs_detectable"))
    SUMMARY_PATH.write_text(
        json.dumps(
            {"total_cases": len(rows), "fs_detectable_true": fs_true, "type_distribution": by_type},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--append", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main()
