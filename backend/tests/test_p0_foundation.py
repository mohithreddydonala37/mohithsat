from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.models.database import VerificationDB, get_db, init_db
import app.models.database as database
from app.services.provenance_service import ProvenanceService
from app.services.verification_service import VerificationService
from app.models import Origin, VerificationStatus


def test_application_import_and_health_endpoint():
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.fixture
def verification_client(tmp_path):
    from app.main import app

    database._engine = None
    database.SessionLocal = None
    engine = init_db(str(tmp_path / "p0.db"))
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = test_session()
    db.add(
        VerificationDB(
            entity_type="lab_result",
            entity_id=1,
            status=VerificationStatus.PENDING,
            original_ai_value="12.2 g/dL",
            corrected_value="12.2 g/dL",
        )
    )
    db.commit()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, db
    finally:
        app.dependency_overrides.clear()
        db.close()
        database._engine = None
        database.SessionLocal = None


def test_api_edit_preserves_original_and_records_immediate_previous_value(verification_client):
    client, db = verification_client

    first = client.post(
        "/verification/edit/lab_result/1?actor_id=user-1",
        json={"corrected_value": "12.4 g/dL"},
    )
    second = client.post(
        "/verification/edit/lab_result/1?actor_id=user-2",
        json={"corrected_value": "12.5 g/dL"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["original_ai_value"] == "12.2 g/dL"
    assert second.json()["corrected_value"] == "12.5 g/dL"

    audit = client.get("/verification/audit/lab_result/1").json()["audit_events"]
    assert audit[-2]["previous_value"] == "12.2 g/dL"
    assert audit[-2]["new_value"] == "12.4 g/dL"
    assert audit[-1]["previous_value"] == "12.4 g/dL"
    assert audit[-1]["new_value"] == "12.5 g/dL"


def test_api_edit_fails_safely_without_original_verification_record(tmp_path):
    from app.main import app

    database._engine = None
    database.SessionLocal = None
    engine = init_db(str(tmp_path / "missing-original.db"))
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = test_session()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.post(
                "/verification/edit/lab_result/99",
                json={"corrected_value": "12.4 g/dL"},
            )
    finally:
        app.dependency_overrides.clear()
        db.close()
        database._engine = None
        database.SessionLocal = None

    assert response.status_code == 404


def test_api_verify_audit_records_previous_status(verification_client):
    client, _ = verification_client

    response = client.post(
        "/verification/verify/lab_result/1?actor_id=reviewer-1",
        json={"notes": "Reviewed"},
    )

    assert response.status_code == 200
    audit = client.get("/verification/audit/lab_result/1").json()["audit_events"][-1]
    assert audit["previous_value"] == "PENDING"
    assert audit["new_value"] == "VERIFIED"


def test_service_timestamps_are_aware_utc():
    provenance = ProvenanceService.create_provenance("lab_result", 1)
    verification = VerificationService.create_verification("lab_result", 1, "12.2")

    assert provenance.timestamp.tzinfo == timezone.utc
    assert verification.updated_at.tzinfo == timezone.utc
    assert datetime.now(timezone.utc) >= provenance.timestamp
