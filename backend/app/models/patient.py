from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from typing import Optional


class Patient(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "age": 45,
                "sex": "M",
                "symptoms": ["headache", "fatigue"],
                "existing_conditions": ["hypertension"],
                "allergies": ["penicillin"],
                "medications": ["lisinopril 10mg"],
                "other_info": "Family history of diabetes"
            }
        }
    )
    
    id: Optional[int] = None
    age: int = Field(..., ge=0, le=150)
    sex: str = Field(..., min_length=1)
    symptoms: list[str] = Field(default_factory=list)
    existing_conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    other_info: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
