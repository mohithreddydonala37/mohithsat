import json
from types import SimpleNamespace

import pytest

from app.models.extraction import ExtractionPayload
from app.providers.groq_provider import EXTRACTION_JSON_SCHEMA, GroqProvider
from app.providers.mock_provider import MockAIProvider
from app.services.ai_service import AIService


def _payload(**lab_overrides):
    lab = {
        "test_name": "Hemoglobin",
        "value": "12.2",
        "unit": "g/dL",
        "reference_low": 13.0,
        "reference_high": 17.0,
        "reference_text": "13.0-17.0 g/dL",
        "observation": None,
        "report_date": None,
        "source_page": 1,
        "source_text": "Hemoglobin: 12.2 g/dL",
    }
    lab.update(lab_overrides)
    return {"lab_results": [lab], "medications": [], "allergies": [], "conditions": []}


class FakeCompletions:
    def __init__(self, content):
        self.content = content
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class FakeClient:
    def __init__(self, content):
        self.chat = SimpleNamespace(completions=FakeCompletions(content))


@pytest.mark.asyncio
async def test_groq_maps_structured_response_and_uses_strict_schema(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    fake = FakeClient(json.dumps(_payload()))
    provider = GroqProvider(client=fake)

    result = await provider.extract("Hemoglobin: 12.2 g/dL", {})

    assert result["lab_results"][0]["value"] == "12.2"
    assert "range_status" not in result["lab_results"][0]
    request = fake.chat.completions.kwargs
    assert request["response_format"]["json_schema"]["strict"] is True
    assert request["response_format"]["json_schema"]["schema"] == EXTRACTION_JSON_SCHEMA
    assert EXTRACTION_JSON_SCHEMA["additionalProperties"] is False


@pytest.mark.asyncio
async def test_groq_rejects_malformed_or_extra_response(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    invalid = _payload(range_status="BELOW_SOURCE_RANGE")
    provider = GroqProvider(client=FakeClient(json.dumps(invalid)))

    with pytest.raises(ValueError, match="invalid extraction response"):
        await provider.extract("source", {})


@pytest.mark.asyncio
async def test_missing_source_fields_remain_null(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    provider = GroqProvider(client=FakeClient(json.dumps(_payload(
        value=None, unit=None, reference_low=None, reference_high=None,
        reference_text=None, report_date=None,
    ))))

    result = await provider.extract("Hemoglobin: not reported", {})

    lab = result["lab_results"][0]
    assert lab["value"] is None
    assert lab["unit"] is None
    assert lab["reference_low"] is None
    assert lab["reference_high"] is None
    assert lab["report_date"] is None


@pytest.mark.asyncio
async def test_provider_failure_is_propagated(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    class FailingCompletions:
        async def create(self, **kwargs):
            raise RuntimeError("provider unavailable")

    provider = GroqProvider(client=SimpleNamespace(
        chat=SimpleNamespace(completions=FailingCompletions())
    ))

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await provider.extract("source", {})


@pytest.mark.asyncio
async def test_mock_provider_replaces_groq_in_ai_service():
    service = AIService(MockAIProvider(_payload()))

    result = await service.extract_from_document("source", report_id=1, source_document="report.pdf")

    assert result["success"] is True
    lab = result["data"]["lab_results"][0]
    assert lab.provider == "mock"
    assert lab.model == "mock-model"
    assert lab.range_status.value == "BELOW_SOURCE_RANGE"


def test_extraction_payload_rejects_unknown_fields():
    with pytest.raises(ValueError):
        ExtractionPayload.model_validate({
            "lab_results": [], "medications": [], "allergies": [], "conditions": [],
            "range_status": "UNKNOWN",
        })
