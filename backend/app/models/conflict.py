from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from typing import Optional, Literal


class Conflict(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conflict_type": "medication_conflict",
                "entity_type": "medication",
                "entity_id_1": 1,
                "entity_id_2": 2,
                "description": "Duplicate medication entries with different dosages",
                "severity": "high",
                "resolved": False
            }
        }
    )
    
    id: Optional[int] = None
    conflict_type: Literal[
        "medication_conflict",
        "allergy_conflict",
        "condition_conflict",
        "duplicate_lab_result",
        "conflicting_dates",
        "value_conflict"
    ] = Field(..., min_length=1)
    entity_type: Literal[
        "lab_result",
        "medication",
        "allergy",
        "condition"
    ] = Field(..., min_length=1)
    entity_id_1: int
    entity_id_2: int
    description: str = Field(..., min_length=1)
    severity: Literal["low", "medium", "high"] = Field(default="medium")
    resolved: bool = False
    resolution_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
