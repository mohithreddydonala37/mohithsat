import pytest
import os
from sqlalchemy.orm import Session
from app.models.database import init_db, get_db, Base, get_engine
from app.models.database import (
    PatientDB, ReportDB, LabResultDB, MedicationDB, AllergyDB, 
    ConditionDB, ObservationDB, ConflictDB, ProvenanceDB, 
    VerificationDB, AuditEventDB, RangeStatusEnum, OriginEnum, VerificationStatusEnum
)
from datetime import datetime


# Test database path
TEST_DB_PATH = "test_medlens.db"


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test."""
    # Remove test database if it exists
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass
    
    # Reset global state
    from app.models import database
    database._engine = None
    database.SessionLocal = None
    
    # Initialize test database
    engine = init_db(TEST_DB_PATH)
    
    # Get a session
    db_gen = get_db()
    db = next(db_gen)
    
    yield db
    
    # Cleanup
    db.close()
    engine.dispose()
    
    # Reset global state again
    database._engine = None
    database.SessionLocal = None
    
    # Try to remove test database
    try:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
    except PermissionError:
        pass  # File may still be locked on Windows


class TestDatabasePersistence:
    """Test that data persists across sessions."""
    
    def test_patient_persistence(self, test_db: Session):
        """Test patient data persists to database."""
        # Create patient
        patient = PatientDB(
            age=45,
            sex="M",
            symptoms="headache,fatigue",
            existing_conditions="hypertension",
            allergies="penicillin",
            medications="lisinopril 10mg",
            other_info="Family history of diabetes"
        )
        test_db.add(patient)
        test_db.commit()
        patient_id = patient.id
        
        # Close and reopen session
        test_db.close()
        db_gen = get_db()
        test_db = next(db_gen)
        
        # Retrieve patient
        retrieved = test_db.query(PatientDB).filter(PatientDB.id == patient_id).first()
        assert retrieved is not None
        assert retrieved.age == 45
        assert retrieved.sex == "M"
    
    def test_lab_result_persistence(self, test_db: Session):
        """Test lab result data persists."""
        # Create patient and report first
        patient = PatientDB(age=30, sex="F", symptoms="", existing_conditions="", allergies="", medications="")
        test_db.add(patient)
        test_db.commit()
        
        report = ReportDB(
            patient_id=patient.id,
            filename="test.pdf",
            file_path="/test/test.pdf",
            pages=1
        )
        test_db.add(report)
        test_db.commit()
        
        # Create lab result
        lab_result = LabResultDB(
            report_id=report.id,
            test_name="Hemoglobin",
            value="13.5",
            unit="g/dL",
            reference_low=12.0,
            reference_high=16.0,
            reference_text="12.0-16.0 g/dL",
            range_status=RangeStatusEnum.WITHIN_SOURCE_RANGE,
            origin=OriginEnum.AI_EXTRACTED,
            verification_status=VerificationStatusEnum.PENDING
        )
        test_db.add(lab_result)
        test_db.commit()
        lab_result_id = lab_result.id
        
        # Close and reopen
        test_db.close()
        db_gen = get_db()
        test_db = next(db_gen)
        
        # Retrieve
        retrieved = test_db.query(LabResultDB).filter(LabResultDB.id == lab_result_id).first()
        assert retrieved is not None
        assert retrieved.test_name == "Hemoglobin"
        assert retrieved.value == "13.5"
        assert retrieved.range_status == RangeStatusEnum.WITHIN_SOURCE_RANGE
    
    def test_verification_persistence(self, test_db: Session):
        """Test verification data persists."""
        verification = VerificationDB(
            entity_type="lab_result",
            entity_id=1,
            status=VerificationStatusEnum.PENDING,
            original_ai_value="13.5",
            corrected_value="13.5"
        )
        test_db.add(verification)
        test_db.commit()
        verification_id = verification.id
        
        # Close and reopen
        test_db.close()
        db_gen = get_db()
        test_db = next(db_gen)
        
        # Retrieve
        retrieved = test_db.query(VerificationDB).filter(VerificationDB.id == verification_id).first()
        assert retrieved is not None
        assert retrieved.entity_type == "lab_result"
        assert retrieved.status == VerificationStatusEnum.PENDING
    
    def test_provenance_persistence(self, test_db: Session):
        """Test provenance data persists."""
        provenance = ProvenanceDB(
            entity_type="lab_result",
            entity_id=1,
            source_document="test.pdf",
            source_page=1,
            source_text="Hemoglobin: 13.5 g/dL",
            origin=OriginEnum.AI_EXTRACTED,
            ai_provider="groq",
            ai_model="llama3-70b-8192",
            verification_state="PENDING"
        )
        test_db.add(provenance)
        test_db.commit()
        provenance_id = provenance.id
        
        # Close and reopen
        test_db.close()
        db_gen = get_db()
        test_db = next(db_gen)
        
        # Retrieve
        retrieved = test_db.query(ProvenanceDB).filter(ProvenanceDB.id == provenance_id).first()
        assert retrieved is not None
        assert retrieved.entity_type == "lab_result"
        assert retrieved.ai_provider == "groq"
    
    def test_conflict_persistence(self, test_db: Session):
        """Test conflict data persists."""
        conflict = ConflictDB(
            conflict_type="medication_conflict",
            entity_type="medication",
            entity_id_1=1,
            entity_id_2=2,
            description="Conflicting dosages",
            severity="high",
            resolved=False
        )
        test_db.add(conflict)
        test_db.commit()
        conflict_id = conflict.id
        
        # Close and reopen
        test_db.close()
        db_gen = get_db()
        test_db = next(db_gen)
        
        # Retrieve
        retrieved = test_db.query(ConflictDB).filter(ConflictDB.id == conflict_id).first()
        assert retrieved is not None
        assert retrieved.conflict_type == "medication_conflict"
        assert retrieved.resolved is False
    
    def test_audit_event_persistence(self, test_db: Session):
        """Test audit event data persists."""
        audit = AuditEventDB(
            entity_type="lab_result",
            entity_id=1,
            action="edited",
            previous_value="13.5",
            new_value="13.7",
            actor="HUMAN",
            actor_id="dr_smith"
        )
        test_db.add(audit)
        test_db.commit()
        audit_id = audit.id
        
        # Close and reopen
        test_db.close()
        db_gen = get_db()
        test_db = next(db_gen)
        
        # Retrieve
        retrieved = test_db.query(AuditEventDB).filter(AuditEventDB.id == audit_id).first()
        assert retrieved is not None
        assert retrieved.action == "edited"
        assert retrieved.actor == "HUMAN"


class TestDatabaseCRUD:
    """Test CRUD operations."""
    
    def test_create_patient(self, test_db: Session):
        """Test creating a patient."""
        patient = PatientDB(
            age=50,
            sex="F",
            symptoms="chest pain",
            existing_conditions="diabetes",
            allergies="none",
            medications="metformin 500mg"
        )
        test_db.add(patient)
        test_db.commit()
        
        assert patient.id is not None
        assert patient.age == 50
    
    def test_read_patient(self, test_db: Session):
        """Test reading a patient."""
        patient = PatientDB(age=40, sex="M", symptoms="", existing_conditions="", allergies="", medications="")
        test_db.add(patient)
        test_db.commit()
        
        retrieved = test_db.query(PatientDB).filter(PatientDB.id == patient.id).first()
        assert retrieved is not None
        assert retrieved.id == patient.id
    
    def test_update_patient(self, test_db: Session):
        """Test updating a patient."""
        patient = PatientDB(age=35, sex="M", symptoms="", existing_conditions="", allergies="", medications="")
        test_db.add(patient)
        test_db.commit()
        
        # Update
        patient.age = 36
        test_db.commit()
        
        # Verify
        retrieved = test_db.query(PatientDB).filter(PatientDB.id == patient.id).first()
        assert retrieved.age == 36
    
    def test_delete_patient(self, test_db: Session):
        """Test deleting a patient."""
        patient = PatientDB(age=25, sex="F", symptoms="", existing_conditions="", allergies="", medications="")
        test_db.add(patient)
        test_db.commit()
        patient_id = patient.id
        
        # Delete
        test_db.delete(patient)
        test_db.commit()
        
        # Verify
        retrieved = test_db.query(PatientDB).filter(PatientDB.id == patient_id).first()
        assert retrieved is None
    
    def test_medication_crud(self, test_db: Session):
        """Test medication CRUD."""
        # Create patient and report
        patient = PatientDB(age=30, sex="F", symptoms="", existing_conditions="", allergies="", medications="")
        test_db.add(patient)
        test_db.commit()
        
        report = ReportDB(patient_id=patient.id, filename="test.pdf", file_path="/test.pdf", pages=1)
        test_db.add(report)
        test_db.commit()
        
        # Create medication
        medication = MedicationDB(
            report_id=report.id,
            name="Lisinopril",
            dosage="10mg",
            frequency="Once daily",
            origin=OriginEnum.AI_EXTRACTED
        )
        test_db.add(medication)
        test_db.commit()
        
        assert medication.id is not None
        
        # Read
        retrieved = test_db.query(MedicationDB).filter(MedicationDB.id == medication.id).first()
        assert retrieved.name == "Lisinopril"
        
        # Update
        medication.dosage = "20mg"
        test_db.commit()
        retrieved = test_db.query(MedicationDB).filter(MedicationDB.id == medication.id).first()
        assert retrieved.dosage == "20mg"
        
        # Delete
        test_db.delete(medication)
        test_db.commit()
        retrieved = test_db.query(MedicationDB).filter(MedicationDB.id == medication.id).first()
        assert retrieved is None


class TestDatabaseRelationships:
    """Test database relationships."""
    
    def test_patient_report_relationship(self, test_db: Session):
        """Test patient has many reports relationship."""
        patient = PatientDB(age=40, sex="M", symptoms="", existing_conditions="", allergies="", medications="")
        test_db.add(patient)
        test_db.commit()
        
        report1 = ReportDB(patient_id=patient.id, filename="report1.pdf", file_path="/report1.pdf", pages=1)
        report2 = ReportDB(patient_id=patient.id, filename="report2.pdf", file_path="/report2.pdf", pages=2)
        test_db.add(report1)
        test_db.add(report2)
        test_db.commit()
        
        # Retrieve patient with reports
        retrieved_patient = test_db.query(PatientDB).filter(PatientDB.id == patient.id).first()
        assert len(retrieved_patient.reports) == 2
    
    def test_report_lab_result_relationship(self, test_db: Session):
        """Test report has many lab results relationship."""
        patient = PatientDB(age=40, sex="M", symptoms="", existing_conditions="", allergies="", medications="")
        test_db.add(patient)
        test_db.commit()
        
        report = ReportDB(patient_id=patient.id, filename="report.pdf", file_path="/report.pdf", pages=1)
        test_db.add(report)
        test_db.commit()
        
        lab1 = LabResultDB(report_id=report.id, test_name="Hemoglobin")
        lab2 = LabResultDB(report_id=report.id, test_name="Glucose")
        test_db.add(lab1)
        test_db.add(lab2)
        test_db.commit()
        
        # Retrieve report with lab results
        retrieved_report = test_db.query(ReportDB).filter(ReportDB.id == report.id).first()
        assert len(retrieved_report.lab_results) == 2


class TestDatabaseInitialization:
    """Test database initialization."""
    
    def test_init_db_creates_tables(self):
        """Test that init_db creates all tables."""
        # Remove test database if exists
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except PermissionError:
                pass
        
        # Reset global state
        from app.models import database
        database._engine = None
        database.SessionLocal = None
        
        # Initialize
        engine = init_db(TEST_DB_PATH)
        
        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        expected_tables = [
            'patients', 'reports', 'lab_results', 'medications', 
            'allergies', 'conditions', 'observations', 'conflicts',
            'provenance', 'verifications', 'audit_events'
        ]
        
        for table in expected_tables:
            assert table in table_names
        
        # Cleanup
        engine.dispose()
        database._engine = None
        database.SessionLocal = None
        
        try:
            if os.path.exists(TEST_DB_PATH):
                os.remove(TEST_DB_PATH)
        except PermissionError:
            pass  # File may still be locked on Windows


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
