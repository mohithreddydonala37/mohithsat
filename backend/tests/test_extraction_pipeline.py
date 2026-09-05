import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.services.extraction_pipeline as pipeline
from app.models.database import Base, LabResultDB, ProvenanceDB, ReportDB, VerificationDB
from app.providers.mock_provider import MockAIProvider


@pytest.mark.asyncio
async def test_report_extraction_persists_range_provenance_and_pending_verification(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    report = ReportDB(
        patient_id=1,
        filename="synthetic-cbc.pdf",
        file_path="private/uuid.pdf",
        pages=1,
        report_metadata=json.dumps({"pages": [{"page_number": 1, "page_text": "Hemoglobin: 12.2 g/dL"}]}),
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    payload = {"lab_results": [{
        "test_name": "Hemoglobin", "value": "12.2", "unit": "g/dL",
        "reference_low": 13.0, "reference_high": 17.0,
        "reference_text": "13.0-17.0 g/dL", "observation": None,
        "report_date": None, "source_page": 1,
        "source_text": "Hemoglobin: 12.2 g/dL",
    }], "medications": [], "allergies": [], "conditions": []}
    monkeypatch.setattr(pipeline, "_provider", lambda: MockAIProvider(payload))

    result = await pipeline.extract_report(report, session)

    lab = session.query(LabResultDB).one()
    assert result["processing_status"] == "READY_FOR_REVIEW"
    assert lab.range_status.value == "BELOW_SOURCE_RANGE"
    assert session.query(ProvenanceDB).one().source_page == 1
    assert session.query(VerificationDB).one().status.value == "PENDING"
    assert "12.2" in session.query(VerificationDB).one().original_ai_value
