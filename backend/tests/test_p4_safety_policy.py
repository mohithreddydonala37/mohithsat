import pytest

from app.services.ai_service import AIService
from app.services.safety_policy import SafetyPolicy


RESTRICTED_QUESTIONS = [
    "Do I have diabetes?",
    "Do I have cancer?",
    "What disease do I have?",
    "What medicine should I take?",
    "Should I increase my dosage?",
    "Should I stop my medication?",
    "What treatment should I start?",
]

ALLOWED_QUESTIONS = [
    "What tests are documented?",
    "What values are listed?",
    "What reference range is shown?",
    "What medications are documented?",
    "What changed between reports?",
    "Explain this medical term.",
]


@pytest.mark.parametrize("question", RESTRICTED_QUESTIONS)
def test_restricted_questions_are_blocked(question):
    assert SafetyPolicy.is_restricted(question) is True


@pytest.mark.parametrize("question", ALLOWED_QUESTIONS)
def test_allowed_questions_are_not_blocked(question):
    assert SafetyPolicy.is_restricted(question) is False


class CountingProvider:
    def __init__(self, answer="record-grounded answer"):
        self.answer_calls = 0
        self.answer_text = answer

    async def answer(self, question, context):
        self.answer_calls += 1
        return self.answer_text

    def get_provider_name(self):
        return "test"

    def get_model_name(self):
        return "test-model"


@pytest.mark.asyncio
async def test_restricted_question_never_reaches_provider():
    provider = CountingProvider()
    service = AIService(provider)

    response = await service.answer_question("Do I have diabetes?", {})

    assert response == SafetyPolicy.SAFE_RESPONSE
    assert provider.answer_calls == 0


@pytest.mark.asyncio
async def test_allowed_question_reaches_provider():
    provider = CountingProvider()
    service = AIService(provider)

    response = await service.answer_question("What tests are documented?", {})

    assert response == "record-grounded answer"
    assert provider.answer_calls == 1
