from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from typing import Optional
from .enums import VerificationStatus, Origin


class Verification(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_type": "lab_result",
                "entity_id": 1,
                "status": "VERIFIED",
                "original_ai_value": "13.5",
                "corrected_value": "13.5",
                "verified_by": "dr_smith",
                "verified_at": "2024-01-16T10:30:00",
                "notes": "Value confirmed accurate"
            }
        }
    )
    
    id: Optional[int] = None
    entity_type: str = Field(..., min_length=1)
    entity_id: int
    status: VerificationStatus = VerificationStatus.PENDING
    original_ai_value: Optional[str] = None
    corrected_value: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    origin: Optional[Origin] = None
