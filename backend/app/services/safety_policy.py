import re


class SafetyPolicy:
    """Application-level boundary for requests seeking clinical action."""

    SAFE_RESPONSE = (
        "MedLens organizes and explains documented medical information. "
        "It does not diagnose, prescribe, recommend treatment, or recommend "
        "medication/dosage changes."
    )

    _RESTRICTED_PATTERNS = (
        r"\bdo\s+i\s+have\b",
        r"\bwhat\s+(?:disease|condition)\s+do\s+i\s+have\b",
        r"\bdiagnos(?:e|is|ed|ing)\b",
        r"\b(?:prescribe|prescription)\b",
        r"\bwhat\s+(?:medicine|medication|drug)\s+should\s+i\s+(?:take|use)\b",
        r"\bshould\s+i\s+(?:take|start|use)\s+(?:a\s+)?(?:medicine|medication|drug)\b",
        r"\b(?:increase|decrease|change|adjust|reduce)\b.{0,30}\b(?:dose|dosage)\b",
        r"\b(?:dose|dosage)\b.{0,30}\b(?:increase|decrease|change|adjust|reduce)\b",
        r"\bshould\s+i\s+stop\b.{0,30}\b(?:medicine|medication|drug)\b",
        r"\bwhat\s+treatment\s+should\s+i\s+(?:start|take|use)\b",
        r"\b(?:treatment|therapy)\b.{0,30}\b(?:should\s+i|recommend|suggest)\b",
    )

    @classmethod
    def is_restricted(cls, question: str) -> bool:
        normalized = " ".join(question.casefold().split())
        return any(re.search(pattern, normalized) for pattern in cls._RESTRICTED_PATTERNS)

    @classmethod
    def safe_response(cls) -> str:
        return cls.SAFE_RESPONSE
