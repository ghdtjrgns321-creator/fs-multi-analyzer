"""Task B3 — 서술 리더 엔진(LLM 호출 외 결정론 경로·graceful)."""

from src.notes.report_parts import ReportPart
from src.report import reader as rd
from src.schemas.extract import ExtractedItem, ReaderOutput


def _part() -> ReportPart:
    return ReportPart("XI", "XI. 그 밖에 투자자 보호", "제재현황 과징금 1,012억원 부과")


def test_run_reader_graceful_skip_without_api_key(monkeypatch):
    monkeypatch.setattr(rd.settings, "openai_api_key", "")

    result = rd.run_reader(_part(), "우발·제재 초점")

    assert result["status"] == "skipped"
    assert result["output"] is None


class _FakeUsage:
    request_tokens = 1200
    response_tokens = 300
    total_tokens = 1500


class _FakeResult:
    def __init__(self, output):
        self.output = output

    def usage(self):
        return _FakeUsage()


class _FakeAgent:
    def __init__(self, output):
        self._output = output

    def run_sync(self, prompt):
        assert "우발·제재" in prompt  # focus가 프롬프트에 실림
        assert "과징금" in prompt  # 파트 본문이 실림
        return _FakeResult(self._output)


def test_run_reader_captures_output_and_usage(monkeypatch):
    monkeypatch.setattr(rd.settings, "openai_api_key", "test-key")
    fake_out = ReaderOutput(
        items=[
            ExtractedItem(
                part="XI",
                label="제재",
                statement="과징금 1,012억원",
                evidence="XI.3",
                why_relevant="고위험",
            ),
        ]
    )
    monkeypatch.setattr(rd, "build_reader_agent", lambda model_name=None: _FakeAgent(fake_out))

    result = rd.run_reader(_part(), "우발·제재 초점")

    assert result["status"] == "ok"
    assert isinstance(result["output"], ReaderOutput)
    assert len(result["output"].items) == 1
    assert result["output"].items[0].label == "제재"
    assert result["usage"]["input_tokens"] == 1200
    assert result["usage"]["output_tokens"] == 300
