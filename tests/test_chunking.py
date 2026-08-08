"""청킹·중복제거 — 긴 PART 분할과 '연결/별도는 중복이 아니다' 보장."""

from __future__ import annotations

from src.notes.report_parts import ReportPart
from src.report.chunking import chunk_part, dedupe_items
from src.schemas.extract import ExtractedItem


def _item(fs_div: str, label: str, statement: str) -> ExtractedItem:
    return ExtractedItem(
        part="III",
        fs_div=fs_div,
        label=label,
        statement=statement,
        evidence="주석",
        why_relevant="검토",
    )


def test_short_part_is_not_chunked():
    part = ReportPart(numeral="XI", title="XI. 우발", text="짧은 본문")
    assert chunk_part(part) == [part]


def test_long_part_splits_with_overlap_and_covers_all_text():
    body = "\n".join(f"{i}행 내용" for i in range(20_000))  # 12만 자 이상
    part = ReportPart(numeral="III", title="III. 재무에 관한 사항", text=body)
    pieces = chunk_part(part, chunk_chars=40_000)

    assert len(pieces) > 1
    assert all(p.numeral == "III" for p in pieces)
    # 첫 조각의 시작과 마지막 조각의 끝이 원문 양끝을 덮는다(구간 누락 없음).
    assert body.startswith(pieces[0].text[:200])
    assert body.endswith(pieces[-1].text[-200:])
    # 오버랩이 있으므로 조각 길이 합은 원문보다 길다.
    assert sum(len(p.text) for p in pieces) > len(body)


def test_chunk_titles_carry_position():
    part = ReportPart(numeral="III", title="III. 재무에 관한 사항", text="가" * 130_000)
    pieces = chunk_part(part, chunk_chars=60_000)
    assert "(1/" in pieces[0].title and f"/{len(pieces)})" in pieces[0].title


def test_dedupe_keeps_consolidated_and_separate_apart():
    # 삼성 2024 실측: 연결 재고자산 56.7조 vs 별도 32.3조 — 이름만 같고 다른 사실이다.
    items = [
        _item("CFS", "재고자산 평가충당금", "평가전금액 56,737,864백만원, 충당금 4,982,999백만원"),
        _item("OFS", "재고자산 평가충당금", "평가전금액 32,283,948백만원, 충당금 3,129,833백만원"),
    ]
    assert len(dedupe_items(items)) == 2


def test_dedupe_removes_same_axis_same_amounts():
    # 청크 경계가 만든 진짜 중복 — 같은 축, 같은 인용 금액.
    items = [
        _item("CFS", "콜옵션 행사 의결", "인수대가는 267,461백만원이며 394만주를 인수한다"),
        _item("CFS", "후속사건 - 콜옵션", "인수대가는 267,461백만원이며 394만주를 인수한다"),
    ]
    assert len(dedupe_items(items)) == 1


def test_dedupe_keeps_summary_and_breakdown():
    # 총괄 ↔ 품목별 상세는 자카드 50% 수준 — 병합하면 상세가 사라진다.
    items = [
        _item("CFS", "재고자산 총괄", "평가전 56,737,864백만원, 충당금 4,982,999백만원"),
        _item(
            "CFS",
            "재고자산 품목별",
            "제품 15,061,526백만원, 충당금 1,219,250백만원, 평가전 56,737,864백만원, 재공품 24,808,100백만원",
        ),
    ]
    assert len(dedupe_items(items)) == 2


def test_dedupe_never_merges_items_without_amounts():
    # 금액이 없으면 동일성 근거가 없다 — 연결·별도의 같은 문구를 지우지 않는다.
    items = [
        _item("", "소송 진행", "다수의 소송이 진행 중이며 유출 시기는 불확실하다"),
        _item("", "소송 진행", "다수의 소송이 진행 중이며 유출 시기는 불확실하다"),
    ]
    assert len(dedupe_items(items)) == 2
