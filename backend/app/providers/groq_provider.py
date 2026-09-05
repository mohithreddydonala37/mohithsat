import json
import os
from typing import Any, Dict, Optional

from groq import AsyncGroq

from app.models.extraction import ExtractionPayload
from .ai_provider import AIProvider


EXTRACTION_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "lab_results": {"type": "array", "items": {
            "type": "object", "properties": {
                "test_name": {"type": "string"}, "value": {"type": ["string", "null"]},
                "unit": {"type": ["string", "null"]}, "reference_low": {"type": ["number", "null"]},
                "reference_high": {"type": ["number", "null"]}, "reference_text": {"type": ["string", "null"]},
                "observation": {"type": ["string", "null"]}, "report_date": {"type": ["string", "null"]},
                "source_page": {"type": ["integer", "null"]}, "source_text": {"type": ["string", "null"]},
            },
            "required": ["test_name", "value", "unit", "reference_low", "reference_high", "reference_text", "observation", "report_date", "source_page", "source_text"],
            "additionalProperties": False,
        }},
        "medications": {"type": "array", "items": {
            "type": "object", "properties": {
                "name": {"type": "string"}, "dosage": {"type": ["string", "null"]},
                "frequency": {"type": ["string", "null"]}, "route": {"type": ["string", "null"]},
                "start_date": {"type": ["string", "null"]}, "end_date": {"type": ["string", "null"]},
                "source_page": {"type": ["integer", "null"]}, "source_text": {"type": ["string", "null"]},
            },
            "required": ["name", "dosage", "frequency", "route", "start_date", "end_date", "source_page", "source_text"],
            "additionalProperties": False,
        }},
        "allergies": {"type": "array", "items": {
            "type": "object", "properties": {
                "allergen": {"type": "string"}, "severity": {"type": ["string", "null"]},
                "reaction": {"type": ["string", "null"]}, "source_page": {"type": ["integer", "null"]},
                "source_text": {"type": ["string", "null"]},
            },
            "required": ["allergen", "severity", "reaction", "source_page", "source_text"],
            "additionalProperties": False,
        }},
        "conditions": {"type": "array", "items": {
            "type": "object", "properties": {
                "name": {"type": "string"}, "diagnosis_date": {"type": ["string", "null"]},
                "status": {"type": ["string", "null"]}, "notes": {"type": ["string", "null"]},
                "source_page": {"type": ["integer", "null"]}, "source_text": {"type": ["string", "null"]},
            },
            "required": ["name", "diagnosis_date", "status", "notes", "source_page", "source_text"],
            "additionalProperties": False,
        }},
    },
    "required": ["lab_results", "medications", "allergies", "conditions"],
    "additionalProperties": False,
}


class GroqProvider(AIProvider):
    """Server-side Groq adapter; no other layer may import the Groq SDK."""

    def __init__(self, client: Optional[Any] = None):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        self.client = client or AsyncGroq(api_key=self.api_key)

    async def extract(self, document_text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        response = await self.client.chat.completions.create(
            model=self.model, temperature=0,
            messages=[
                {"role": "system", "content": "Extract only explicitly documented information. Use null for missing values. Never infer or invent values or reference ranges. Preserve page number and exact supporting source text when available."},
                {"role": "user", "content": document_text},
            ],
            response_format={"type": "json_schema", "json_schema": {
                "name": "medlens_extraction", "strict": True, "schema": EXTRACTION_JSON_SCHEMA
            }},
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Groq returned an empty extraction response")
        try:
            return ExtractionPayload.model_validate(json.loads(content)).model_dump()
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError("Groq returned an invalid extraction response") from exc

    async def summarize(self, verified_data: Dict[str, Any]) -> str:
        return await self._text_completion("Summarize only the verified, documented medical record. Do not diagnose or recommend treatment.", json.dumps(verified_data, default=str))

    async def classify_safety(self, query: str) -> str:
        return await self._text_completion("Classify this request as exactly ALLOWED or RESTRICTED.", query)

    async def answer(self, question: str, context: Dict[str, Any]) -> str:
        return await self._text_completion("Answer only from the supplied documented record. Do not diagnose or recommend treatment.", f"Question: {question}\nRecord: {json.dumps(context, default=str)}")

    async def _text_completion(self, system: str, user: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model, temperature=0,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Groq returned an empty response")
        return content

    def get_provider_name(self) -> str:
        return "groq"

    def get_model_name(self) -> str:
        return self.model
