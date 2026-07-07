"""Task B1 — ExtractedItem/ReaderOutput 스키마 검증."""

import pytest
from pydantic import ValidationError

from src.schemas.extract import ExtractedItem, ReaderOutput


def test_extracted_item_roundtrip():
    item = ExtractedItem(
        part="XI",
        label="제재",
        statement="과징금 1,012억원 부과",
        evidence="XI.3 제재현황",
        why_relevant="금전적 제재는 고위험 검토 대상",
    )
    assert item.part == "XI"
    assert item.label == "제재"
    assert item.statement == "과징금 1,012억원 부과"
    assert item.evidence == "XI.3 제재현황"
    assert item.why_relevant == "금전적 제재는 고위험 검토 대상"


def test_extracted_item_rejects_empty_label():
    with pytest.raises(ValidationError):
        ExtractedItem(
            part="XI",
            label="",
            statement="내용",
            evidence="근거",
            why_relevant="이유",
        )


def test_reader_output_defaults_empty():
    out = ReaderOutput()
    assert out.items == []
    out2 = ReaderOutput(
        items=[ExtractedItem(part="I", label="a", statement="b", evidence="c", why_relevant="d")]
    )
    assert len(out2.items) == 1
