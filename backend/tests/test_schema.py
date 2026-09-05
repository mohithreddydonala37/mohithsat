import pytest
from datetime import datetime
from app.models import (
    Patient,
    Report,
    LabResult,
    Medication,
    Allergy,
    Condition,
    Observation,
    Conflict,
    Provenance,
    Verification,
    AuditEvent,
    RangeStatus,
    Origin,
    VerificationStatus,
    PatientCreateRequest,
    PatientResponse,
    LabResultResponse,
    QuestionRequest,
)


class TestPatientModel:
    def test_patient_creation(self):
        patient = Patient(
            age=45,
            sex="M",
            symptoms=["headache", "fatigue"],
            existing_conditions=["hypertension"],
            allergies=["penicillin"],
            medications=["lisinopril 10mg"],
            other_info="Family history of diabetes"
        )
        assert patient.age == 45
        assert patient.sex == "M"
        assert len(patient.symptoms) == 2
        assert patient.symptoms == ["headache", "fatigue"]

    def test_patient_age_validation(self):
        with pytest.raises(ValueError):
            Patient(age=200, sex="M")

    def test_patient_age_minimum(self):
        with pytest.raises(ValueError):
            Patient(age=-1, sex="M")


class TestLabResultModel:
    def test_lab_result_creation(self):
        lab_result = LabResult(
            report_id=1,
            test_name="Hemoglobin",
            value="13.5",
            unit="g/dL",
            reference_low=12.0,
            reference_high=16.0,
            reference_text="12.0-16.0 g/dL",
            range_status=RangeStatus.WITHIN_SOURCE_RANGE,
            origin=Origin.AI_EXTRACTED,
            verification_status=VerificationStatus.PENDING
        )
        assert lab_result.test_name == "Hemoglobin"
        assert lab_result.value == "13.5"
        assert lab_result.range_status == RangeStatus.WITHIN_SOURCE_RANGE

    def test_lab_result_missing_fields(self):
        lab_result = LabResult(
            report_id=1,
            test_name="Glucose"
        )
        assert lab_result.value is None
        assert lab_result.unit is None
        assert lab_result.range_status == RangeStatus.NOT_DETERMINED


class TestMedicationModel:
    def test_medication_creation(self):
        medication = Medication(
            report_id=1,
            name="Lisinopril",
            dosage="10mg",
            frequency="Once daily",
            route="Oral"
        )
        assert medication.name == "Lisinopril"
        assert medication.dosage == "10mg"
        assert medication.origin == Origin.AI_EXTRACTED


class TestAllergyModel:
    def test_allergy_creation(self):
        allergy = Allergy(
            report_id=1,
            allergen="Penicillin",
            severity="Severe",
            reaction="Anaphylaxis"
        )
        assert allergy.allergen == "Penicillin"
        assert allergy.severity == "Severe"


class TestConditionModel:
    def test_condition_creation(self):
        condition = Condition(
            report_id=1,
            name="Hypertension",
            status="Active"
        )
        assert condition.name == "Hypertension"
        assert condition.status == "Active"


class TestObservationModel:
    def test_observation_creation(self):
        observation = Observation(
            report_id=1,
            category="clinical_note",
            text="Patient reports improvement in symptoms"
        )
        assert observation.category == "clinical_note"
        assert observation.text == "Patient reports improvement in symptoms"


class TestConflictModel:
    def test_conflict_creation(self):
        conflict = Conflict(
            conflict_type="medication_conflict",
            entity_type="medication",
            entity_id_1=1,
            entity_id_2=2,
            description="Duplicate medication entries with different dosages"
        )
        assert conflict.conflict_type == "medication_conflict"
        assert conflict.entity_type == "medication"
        assert conflict.resolved is False


class TestProvenanceModel:
    def test_provenance_creation(self):
        provenance = Provenance(
            entity_type="lab_result",
            entity_id=1,
            source_document="lab_report_2024.pdf",
            source_page=1,
            source_text="Hemoglobin: 13.5 g/dL",
            origin=Origin.AI_EXTRACTED,
            ai_provider="groq",
            ai_model="llama3-70b-8192"
        )
        assert provenance.entity_type == "lab_result"
        assert provenance.source_document == "lab_report_2024.pdf"
        assert provenance.ai_provider == "groq"


class TestVerificationModel:
    def test_verification_creation(self):
        verification = Verification(
            entity_type="lab_result",
            entity_id=1,
            status=VerificationStatus.VERIFIED,
            original_ai_value="13.5",
            corrected_value="13.5",
            verified_by="dr_smith"
        )
        assert verification.status == VerificationStatus.VERIFIED
        assert verification.original_ai_value == "13.5"
        assert verification.verified_by == "dr_smith"


class TestAuditEventModel:
    def test_audit_event_creation(self):
        audit_event = AuditEvent(
            entity_type="lab_result",
            entity_id=1,
            action="edited",
            previous_value="13.5",
            new_value="13.7",
            actor="HUMAN",
            actor_id="dr_smith"
        )
        assert audit_event.action == "edited"
        assert audit_event.actor == "HUMAN"
        assert audit_event.previous_value == "13.5"


class TestAPIRequestModels:
    def test_patient_create_request(self):
        request = PatientCreateRequest(
            age=45,
            sex="M",
            symptoms=["headache"],
            medications=["lisinopril"]
        )
        assert request.age == 45
        assert len(request.symptoms) == 1

    def test_question_request(self):
        request = QuestionRequest(
            question="What tests are listed?",
            patient_id=1
        )
        assert request.question == "What tests are listed?"
        assert request.patient_id == 1


class TestEnumValues:
    def test_range_status_enum(self):
        assert RangeStatus.WITHIN_SOURCE_RANGE == "WITHIN_SOURCE_RANGE"
        assert RangeStatus.BELOW_SOURCE_RANGE == "BELOW_SOURCE_RANGE"
        assert RangeStatus.ABOVE_SOURCE_RANGE == "ABOVE_SOURCE_RANGE"
        assert RangeStatus.NOT_DETERMINED == "NOT_DETERMINED"

    def test_origin_enum(self):
        assert Origin.USER_PROVIDED == "USER_PROVIDED"
        assert Origin.SYNTHETIC_SOURCE == "SYNTHETIC_SOURCE"
        assert Origin.AI_EXTRACTED == "AI_EXTRACTED"
        assert Origin.HUMAN_VERIFIED == "HUMAN_VERIFIED"

    def test_verification_status_enum(self):
        assert VerificationStatus.PENDING == "PENDING"
        assert VerificationStatus.EDITED == "EDITED"
        assert VerificationStatus.VERIFIED == "VERIFIED"
        assert VerificationStatus.FLAGGED == "FLAGGED"


class TestProviderPortability:
    def test_lab_result_groq_provider(self):
        """Test that LabResult can be created with Groq provider"""
        lab_result = LabResult(
            report_id=1,
            test_name="Hemoglobin",
            value="13.5",
            provider="groq",
            model="llama3-70b-8192",
            origin=Origin.AI_EXTRACTED
        )
        assert lab_result.provider == "groq"
        assert lab_result.model == "llama3-70b-8192"

    def test_lab_result_openai_provider(self):
        """Test that LabResult can be created with OpenAI provider (portability)"""
        lab_result = LabResult(
            report_id=1,
            test_name="Hemoglobin",
            value="13.5",
            provider="openai",
            model="gpt-4",
            origin=Origin.AI_EXTRACTED
        )
        assert lab_result.provider == "openai"
        assert lab_result.model == "gpt-4"

    def test_lab_result_anthropic_provider(self):
        """Test that LabResult can be created with Anthropic provider (portability)"""
        lab_result = LabResult(
            report_id=1,
            test_name="Hemoglobin",
            value="13.5",
            provider="anthropic",
            model="claude-3-opus",
            origin=Origin.AI_EXTRACTED
        )
        assert lab_result.provider == "anthropic"
        assert lab_result.model == "claude-3-opus"

    def test_canonical_schema_provider_agnostic(self):
        """Test that canonical schema does not have provider-specific fields"""
        lab_result = LabResult(
            report_id=1,
            test_name="Hemoglobin",
            value="13.5"
        )
        # Canonical fields should be provider-agnostic
        assert hasattr(lab_result, 'test_name')
        assert hasattr(lab_result, 'value')
        assert hasattr(lab_result, 'unit')
        assert hasattr(lab_result, 'range_status')
        # Provider fields are optional and generic
        assert lab_result.provider is None
        assert lab_result.model is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
