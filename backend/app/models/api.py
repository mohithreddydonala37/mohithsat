from pydantic import BaseModel, Field
from typing import Annotated, Optional, List
from datetime import datetime, timezone
from .enums import RangeStatus, Origin, VerificationStatus


# Request Models

PatientText = Annotated[str, Field(min_length=1, max_length=200)]


class PatientCreateRequest(BaseModel):
    age: int = Field(..., ge=0, le=150)
    sex: str = Field(..., min_length=1, max_length=50)
    symptoms: List[PatientText] = Field(default_factory=list)
    existing_conditions: List[PatientText] = Field(default_factory=list)
    allergies: List[PatientText] = Field(default_factory=list)
    medications: List[PatientText] = Field(default_factory=list)
    other_info: Optional[str] = Field(None, max_length=2000)


class PatientUpdateRequest(BaseModel):
    age: Optional[int] = Field(None, ge=0, le=150)
    sex: Optional[str] = Field(None, min_length=1, max_length=50)
    symptoms: Optional[List[PatientText]] = None
    existing_conditions: Optional[List[PatientText]] = None
    allergies: Optional[List[PatientText]] = None
    medications: Optional[List[PatientText]] = None
    other_info: Optional[str] = Field(None, max_length=2000)


class ReportUploadRequest(BaseModel):
    patient_id: int


class ReportCreateRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    pages: int = Field(default=1, ge=1, le=10000)
    report_metadata: Optional[dict] = None


class LabResultUpdateRequest(BaseModel):
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    reference_text: Optional[str] = None
    observation: Optional[str] = None
    verification_status: Optional[VerificationStatus] = None
    notes: Optional[str] = None


class MedicationUpdateRequest(BaseModel):
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    verification_status: Optional[VerificationStatus] = None
    notes: Optional[str] = None


class AllergyUpdateRequest(BaseModel):
    severity: Optional[str] = None
    reaction: Optional[str] = None
    verification_status: Optional[VerificationStatus] = None
    notes: Optional[str] = None


class ConditionUpdateRequest(BaseModel):
    diagnosis_date: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    verification_status: Optional[VerificationStatus] = None


class VerificationRequest(BaseModel):
    corrected_value: Optional[str] = None
    notes: Optional[str] = None


class ConflictResolutionRequest(BaseModel):
    conflict_id: int
    resolved: bool
    resolution_notes: Optional[str] = None


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1)
    patient_id: Optional[int] = None


# Response Models


class PatientResponse(BaseModel):
    id: int
    age: int
    sex: str
    symptoms: List[str]
    existing_conditions: List[str]
    allergies: List[str]
    medications: List[str]
    other_info: Optional[str]
    created_at: datetime
    updated_at: datetime


class ReportResponse(BaseModel):
    id: int
    patient_id: int
    filename: str
    upload_date: datetime
    pages: int
    report_metadata: Optional[dict]
    processing_status: str = "UPLOADED"


class LabResultResponse(BaseModel):
    id: int
    report_id: int
    test_name: str
    value: Optional[str]
    unit: Optional[str]
    reference_low: Optional[float]
    reference_high: Optional[float]
    reference_text: Optional[str]
    observation: Optional[str]
    report_date: Optional[datetime]
    source_page: Optional[int]
    source_text: Optional[str]
    confidence: Optional[float]
    range_status: RangeStatus
    origin: Origin
    verification_status: VerificationStatus
    provider: Optional[str]
    model: Optional[str]
    created_at: datetime


class MedicationResponse(BaseModel):
    id: int
    report_id: Optional[int]
    patient_id: Optional[int]
    name: str
    dosage: Optional[str]
    frequency: Optional[str]
    route: Optional[str]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    source_page: Optional[int]
    source_text: Optional[str]
    confidence: Optional[float]
    origin: Origin
    verification_status: VerificationStatus
    provider: Optional[str]
    model: Optional[str]
    created_at: datetime


class AllergyResponse(BaseModel):
    id: int
    report_id: Optional[int]
    patient_id: Optional[int]
    allergen: str
    severity: Optional[str]
    reaction: Optional[str]
    source_page: Optional[int]
    source_text: Optional[str]
    confidence: Optional[float]
    origin: Origin
    verification_status: VerificationStatus
    provider: Optional[str]
    model: Optional[str]
    created_at: datetime


class ConditionResponse(BaseModel):
    id: int
    report_id: Optional[int]
    patient_id: Optional[int]
    name: str
    diagnosis_date: Optional[datetime]
    status: Optional[str]
    notes: Optional[str]
    source_page: Optional[int]
    source_text: Optional[str]
    confidence: Optional[float]
    origin: Origin
    verification_status: VerificationStatus
    provider: Optional[str]
    model: Optional[str]
    created_at: datetime


class ObservationResponse(BaseModel):
    id: int
    report_id: int
    category: str
    text: str
    source_page: Optional[int]
    source_text: Optional[str]
    confidence: Optional[float]
    origin: Origin
    verification_status: VerificationStatus
    provider: Optional[str]
    model: Optional[str]
    created_at: datetime


class ConflictResponse(BaseModel):
    id: int
    conflict_type: str
    entity_type: str
    entity_id_1: int
    entity_id_2: int
    description: str
    severity: str
    resolved: bool
    resolution_notes: Optional[str]
    created_at: datetime


class ProvenanceResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    source_document: Optional[str]
    source_page: Optional[int]
    source_text: Optional[str]
    origin: Origin
    ai_provider: Optional[str]
    ai_model: Optional[str]
    verification_state: str
    timestamp: datetime


class VerificationResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    status: VerificationStatus
    original_ai_value: Optional[str]
    corrected_value: Optional[str]
    verified_by: Optional[str]
    verified_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime


class AuditEventResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    action: str
    previous_value: Optional[str]
    new_value: Optional[str]
    actor: str
    actor_id: Optional[str]
    timestamp: datetime
    notes: Optional[str]


class SummaryResponse(BaseModel):
    patient_id: int
    summary: str
    generated_at: datetime
    sources: List[str]


class QuestionResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: Optional[float]
    timestamp: datetime


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
