from typing import Any, Dict, Optional

from .ai_provider import AIProvider


class MockAIProvider(AIProvider):
    """Deterministic provider for tests and offline development."""

    def __init__(self, extraction_response: Optional[Dict[str, Any]] = None):
        self.extraction_response = extraction_response or {
            "lab_results": [],
            "medications": [],
            "allergies": [],
            "conditions": [],
        }

    async def extract(self, document_text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        return self.extraction_response

    async def summarize(self, verified_data: Dict[str, Any]) -> str:
        return "No verified summary is available."

    async def classify_safety(self, query: str) -> str:
        return "ALLOWED"

    async def answer(self, question: str, context: Dict[str, Any]) -> str:
        return "No record-grounded answer is available."

    def get_provider_name(self) -> str:
        return "mock"

    def get_model_name(self) -> str:
        return "mock-model"
