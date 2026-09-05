from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from typing import Optional, Literal


class AuditEvent(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_type": "lab_result",
                "entity_id": 1,
                "action": "edited",
                "previous_value": "13.5",
                "new_value": "13.7",
                "actor": "HUMAN",
                "actor_id": "dr_smith",
                "notes": "Corrected transcription error"
            }
        }
    )
    
    id: Optional[int] = None
    entity_type: str = Field(..., min_length=1)
    entity_id: int
    action: Literal[
        "created",
        "updated",
        "deleted",
        "verified",
        "flagged",
        "edited"
    ] = Field(..., min_length=1)
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    actor: Literal["AI", "HUMAN"] = Field(..., min_length=1)
    actor_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: Optional[str] = None
