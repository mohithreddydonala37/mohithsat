from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime, timezone
import enum
from typing import Generator
from app.config import get_settings

Base = declarative_base()

# Default database path
DEFAULT_DATABASE_URL = get_settings().database_url

# Create session factory
SessionLocal = None
_engine = None


def get_engine(db_path: str = None) -> None:
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        db_url = f"sqlite:///{db_path}" if db_path else DEFAULT_DATABASE_URL
        # For SQLite on Windows, check_same_thread=False allows multi-threaded access
        _engine = create_engine(db_url, connect_args={"check_same_thread": False})
    return _engine


def get_db() -> Generator:
    """
    FastAPI dependency for database sessions.
    
    Yields:
        Session: SQLAlchemy session
    """
    global SessionLocal
    if SessionLocal is None:
        engine = get_engine()
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(db_path: str = None) -> None:
    """
    Initialize the database.
    Creates all tables if they don't exist.
    
    Args:
        db_path: Optional path to database file
    """
    global SessionLocal, _engine
    
    engine = get_engine(db_path)
    if SessionLocal is None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    return engine


class RangeStatusEnum(enum.Enum):
    WITHIN_SOURCE_RANGE = "WITHIN_SOURCE_RANGE"
    BELOW_SOURCE_RANGE = "BELOW_SOURCE_RANGE"
    ABOVE_SOURCE_RANGE = "ABOVE_SOURCE_RANGE"
    NOT_DETERMINED = "NOT_DETERMINED"


class OriginEnum(enum.Enum):
    USER_PROVIDED = "USER_PROVIDED"
    SYNTHETIC_SOURCE = "SYNTHETIC_SOURCE"
    AI_EXTRACTED = "AI_EXTRACTED"
    HUMAN_VERIFIED = "HUMAN_VERIFIED"


class VerificationStatusEnum(enum.Enum):
    PENDING = "PENDING"
    EDITED = "EDITED"
    VERIFIED = "VERIFIED"
    FLAGGED = "FLAGGED"


class PatientDB(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    age = Column(Integer, nullable=False)
    sex = Column(String, nullable=False)
    symptoms = Column(Text, nullable=False)
    existing_conditions = Column(Text, nullable=False)
    allergies = Column(Text, nullable=False)
    medications = Column(Text, nullable=False)
    other_info = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    reports = relationship("ReportDB", back_populates="patient")


class ReportDB(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    upload_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    pages = Column(Integer, nullable=False)
    report_metadata = Column(Text, nullable=True)

    patient = relationship("PatientDB", back_populates="reports")
    lab_results = relationship("LabResultDB", back_populates="report")
    medications = relationship("MedicationDB", back_populates="report")
    allergies = relationship("AllergyDB", back_populates="report")
    conditions = relationship("ConditionDB", back_populates="report")
    observations = relationship("ObservationDB", back_populates="report")


class LabResultDB(Base):
    __tablename__ = "lab_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    test_name = Column(String, nullable=False)
    value = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    reference_low = Column(Float, nullable=True)
    reference_high = Column(Float, nullable=True)
    reference_text = Column(String, nullable=True)
    observation = Column(String, nullable=True)
    report_date = Column(DateTime, nullable=True)
    source_page = Column(Integer, nullable=True)
    source_text = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    range_status = Column(SQLEnum(RangeStatusEnum), default=RangeStatusEnum.NOT_DETERMINED)
    origin = Column(SQLEnum(OriginEnum), default=OriginEnum.AI_EXTRACTED)
    verification_status = Column(SQLEnum(VerificationStatusEnum), default=VerificationStatusEnum.PENDING)
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    report = relationship("ReportDB", back_populates="lab_results")


class MedicationDB(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=True)
    frequency = Column(String, nullable=True)
    route = Column(String, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    source_page = Column(Integer, nullable=True)
    source_text = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    origin = Column(SQLEnum(OriginEnum), default=OriginEnum.AI_EXTRACTED)
    verification_status = Column(SQLEnum(VerificationStatusEnum), default=VerificationStatusEnum.PENDING)
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    report = relationship("ReportDB", back_populates="medications")


class AllergyDB(Base):
    __tablename__ = "allergies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    allergen = Column(String, nullable=False)
    severity = Column(String, nullable=True)
    reaction = Column(String, nullable=True)
    source_page = Column(Integer, nullable=True)
    source_text = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    origin = Column(SQLEnum(OriginEnum), default=OriginEnum.AI_EXTRACTED)
    verification_status = Column(SQLEnum(VerificationStatusEnum), default=VerificationStatusEnum.PENDING)
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    report = relationship("ReportDB", back_populates="allergies")


class ConditionDB(Base):
    __tablename__ = "conditions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    name = Column(String, nullable=False)
    diagnosis_date = Column(DateTime, nullable=True)
    status = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    source_page = Column(Integer, nullable=True)
    source_text = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    origin = Column(SQLEnum(OriginEnum), default=OriginEnum.AI_EXTRACTED)
    verification_status = Column(SQLEnum(VerificationStatusEnum), default=VerificationStatusEnum.PENDING)
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    report = relationship("ReportDB", back_populates="conditions")


class ObservationDB(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    category = Column(String, nullable=False)
    text = Column(String, nullable=False)
    source_page = Column(Integer, nullable=True)
    source_text = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    origin = Column(SQLEnum(OriginEnum), default=OriginEnum.AI_EXTRACTED)
    verification_status = Column(SQLEnum(VerificationStatusEnum), default=VerificationStatusEnum.PENDING)
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    report = relationship("ReportDB", back_populates="observations")


class ConflictDB(Base):
    __tablename__ = "conflicts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conflict_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id_1 = Column(Integer, nullable=False)
    entity_id_2 = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    severity = Column(String, default="medium")
    resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ProvenanceDB(Base):
    __tablename__ = "provenance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    source_document = Column(String, nullable=True)
    source_page = Column(Integer, nullable=True)
    source_text = Column(String, nullable=True)
    origin = Column(SQLEnum(OriginEnum), default=OriginEnum.AI_EXTRACTED)
    ai_provider = Column(String, nullable=True)
    ai_model = Column(String, nullable=True)
    verification_state = Column(String, default="PENDING")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class VerificationDB(Base):
    __tablename__ = "verifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    status = Column(SQLEnum(VerificationStatusEnum), default=VerificationStatusEnum.PENDING)
    original_ai_value = Column(String, nullable=True)
    corrected_value = Column(String, nullable=True)
    verified_by = Column(String, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuditEventDB(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    previous_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    actor = Column(String, nullable=False)
    actor_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text, nullable=True)


def get_database_url(db_path: str = "medlens.db") -> str:
    return f"sqlite:///{db_path}"


def create_engine_with_db(db_path: str = "medlens.db"):
    engine = create_engine(get_database_url(db_path))
    Base.metadata.create_all(engine)
    return engine
