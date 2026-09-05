from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from typing import Optional
from .enums import RangeStatus, Origin, VerificationStatus


class LabResult(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "report_id": 1,
                "test_name": "Hemoglobin",
                "value": "13.5",
                "unit": "g/dL",
                "reference_low": 12.0,
                "reference_high": 16.0,
                "reference_text": "12.0-16.0 g/dL",
                "observation": "Within normal limits",
                "report_date": "2024-01-15T00:00:00",
                "source_page": 1,
                "source_text": "Hemoglobin: 13.5 g/dL (Ref: 12.0-16.0)",
                "confidence": 0.95,
                "range_status": "WITHIN_SOURCE_RANGE",
                "origin": "AI_EXTRACTED",
                "verification_status": "PENDING",
                "provider": "groq",
                "model": "llama3-70b-8192"
            }
        }
    )
    
    id: Optional[int] = None
    report_id: int
    test_name: str = Field(..., min_length=1)
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    reference_text: Optional[str] = None
    observation: Optional[str] = None
    report_date: Optional[datetime] = None
    source_page: Optional[int] = None
    source_text: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    range_status: RangeStatus = RangeStatus.NOT_DETERMINED
    origin: Origin = Origin.AI_EXTRACTED
    verification_status: VerificationStatus = VerificationStatus.PENDING
    provider: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
