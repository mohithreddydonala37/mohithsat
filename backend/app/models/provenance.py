from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from typing import Optional
from .enums import Origin


class Provenance(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_type": "lab_result",
                "entity_id": 1,
                "source_document": "lab_report_2024.pdf",
                "source_page": 1,
                "source_text": "Hemoglobin: 13.5 g/dL (Ref: 12.0-16.0)",
                "origin": "AI_EXTRACTED",
                "ai_provider": "groq",
                "ai_model": "llama3-70b-8192",
                "verification_state": "PENDING"
            }
        }
    )
    
    id: Optional[int] = None
    entity_type: str = Field(..., min_length=1)
    entity_id: int
    source_document: Optional[str] = None
    source_page: Optional[int] = None
    source_text: Optional[str] = None
    origin: Origin = Origin.AI_EXTRACTED
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    verification_state: str = Field(default="PENDING")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
