from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from typing import Optional


class Report(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patient_id": 1,
                "filename": "lab_report_2024.pdf",
                "file_path": "/data/reports/lab_report_2024.pdf",
                "pages": 3,
                "report_metadata": {"facility": "City Lab", "report_id": "RL-2024-001"}
            }
        }
    )
    
    id: Optional[int] = None
    patient_id: int
    filename: str = Field(..., min_length=1)
    file_path: str = Field(..., min_length=1)
    upload_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pages: int = Field(..., ge=1)
    report_metadata: Optional[dict] = None
