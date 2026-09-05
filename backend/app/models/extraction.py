from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class _ExtractionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_page: Optional[int]
    source_text: Optional[str]


class ExtractedLabResult(_ExtractionItem):
    test_name: str
    value: Optional[str]
    unit: Optional[str]
    reference_low: Optional[float]
    reference_high: Optional[float]
    reference_text: Optional[str]
    observation: Optional[str]
    report_date: Optional[str]


class ExtractedMedication(_ExtractionItem):
    name: str
    dosage: Optional[str]
    frequency: Optional[str]
    route: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]


class ExtractedAllergy(_ExtractionItem):
    allergen: str
    severity: Optional[str]
    reaction: Optional[str]


class ExtractedCondition(_ExtractionItem):
    name: str
    diagnosis_date: Optional[str]
    status: Optional[str]
    notes: Optional[str]


class ExtractionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lab_results: List[ExtractedLabResult]
    medications: List[ExtractedMedication]
    allergies: List[ExtractedAllergy]
    conditions: List[ExtractedCondition]
