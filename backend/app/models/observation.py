from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from typing import Optional
from .enums import Origin, VerificationStatus


class Observation(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "report_id": 1,
                "category": "clinical_note",
                "text": "Patient reports improvement in symptoms",
                "source_page": 3,
                "source_text": "Clinical Note: Patient reports improvement in symptoms",
                "confidence": 0.88,
                "origin": "AI_EXTRACTED",
                "verification_status": "PENDING",
                "provider": "groq",
                "model": "llama3-70b-8192"
            }
        }
    )
    
    id: Optional[int] = None
    report_id: int
    category: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    source_page: Optional[int] = None
    source_text: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    origin: Origin = Origin.AI_EXTRACTED
    verification_status: VerificationStatus = VerificationStatus.PENDING
    provider: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
