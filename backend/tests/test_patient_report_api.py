import app.models.database as database
import app.api.patient_reports as patient_reports
from fastapi.testclient import TestClient
from io import BytesIO
from pypdf import PdfWriter
from sqlalchemy.orm import sessionmaker

import pytest

from app.main import app
from app.models.database import get_db, init_db


@pytest.fixture
def client(tmp_path):
    database._engine = None
    database.SessionLocal = None
    engine = init_db(str(tmp_path / "patient-report.db"))
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        db.close()
        database._engine = None
        database.SessionLocal = None


def create_patient(client):
    response = client.post(
        "/patients",
        json={
            "age": 45,
            "sex": "F",
            "symptoms": ["fatigue"],
            "existing_conditions": ["hypertension"],
            "allergies": ["penicillin"],
            "medications": ["lisinopril 10mg"],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_retrieve_and_update_patient(client):
    patient = create_patient(client)

    retrieved = client.get(f"/patients/{patient['id']}")
    updated = client.put(
        f"/patients/{patient['id']}",
        json={"age": 46, "symptoms": ["fatigue", "headache"]},
    )

    assert retrieved.status_code == 200
    assert retrieved.json()["medications"] == ["lisinopril 10mg"]
    assert updated.status_code == 200
    assert updated.json()["age"] == 46
    assert updated.json()["symptoms"] == ["fatigue", "headache"]


def test_patient_persists_for_report_relationship(client):
    patient = create_patient(client)

    created = client.post(
        f"/patients/{patient['id']}/reports",
        json={
            "filename": "cbc.pdf",
            "pages": 2,
            "report_metadata": {"facility": "Synthetic Lab"},
        },
    )
    listed = client.get(f"/patients/{patient['id']}/reports")
    retrieved = client.get(f"/reports/{created.json()['id']}")

    assert created.status_code == 201
    assert created.json()["patient_id"] == patient["id"]
    assert created.json()["processing_status"] == "UPLOADED"
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert retrieved.status_code == 200
    assert retrieved.json()["filename"] == "cbc.pdf"
    assert retrieved.json()["report_metadata"]["facility"] == "Synthetic Lab"


def test_nonexistent_patient_and_report_return_safe_errors(client):
    missing_patient = client.get("/patients/9999")
    missing_report = client.get("/reports/9999")
    missing_report_patient = client.post(
        "/patients/9999/reports",
        json={"filename": "cbc.pdf", "pages": 1},
    )

    assert missing_patient.status_code == 404
    assert missing_patient.json()["detail"] == "Patient not found"
    assert missing_report.status_code == 404
    assert missing_report.json()["detail"] == "Report not found"
    assert missing_report_patient.status_code == 404
    assert "Patient not found" in missing_report_patient.json()["detail"]


def test_invalid_patient_and_report_input_is_rejected(client):
    invalid_patient = client.post("/patients", json={"age": 151, "sex": "F"})
    patient = create_patient(client)
    invalid_report = client.post(
        f"/patients/{patient['id']}/reports",
        json={"filename": "", "pages": 0},
    )

    assert invalid_patient.status_code == 422
    assert invalid_report.status_code == 422


def pdf_bytes(page_count=1):
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_valid_pdf_is_stored_and_extracted_page_by_page(client, tmp_path, monkeypatch):
    patient = create_patient(client)
    monkeypatch.setattr(patient_reports, "PRIVATE_STORAGE_DIR", tmp_path)

    response = client.post(
        f"/patients/{patient['id']}/reports",
        files={"file": ("cbc.pdf", pdf_bytes(2), "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["processing_status"] == "READY_FOR_REVIEW"
    assert body["filename"] == "cbc.pdf"
    assert body["report_metadata"]["original_filename"] == "cbc.pdf"
    assert body["report_metadata"]["pages"][0]["page_number"] == 1
    assert body["report_metadata"]["pages"][1]["page_number"] == 2
    assert "file_path" not in body
    stored_files = [path for path in tmp_path.iterdir() if path.suffix == ".pdf"]
    assert len(stored_files) == 1
    assert stored_files[0].suffix == ".pdf"
    assert stored_files[0].name != "cbc.pdf"


@pytest.mark.parametrize(
    ("filename", "content_type", "payload"),
    [
        ("report.txt", "application/pdf", pdf_bytes()),
        ("report.pdf", "text/plain", pdf_bytes()),
        ("report.pdf", "application/pdf", b"not a pdf"),
        ("report.pdf", "application/pdf", b""),
        ("../report.pdf", "application/pdf", pdf_bytes()),
        (r"..\report.pdf", "application/pdf", pdf_bytes()),
        ("report.pdf", "application/pdf", b"%PDF-1.4\nmalformed"),
    ],
)
def test_invalid_pdf_uploads_are_rejected(
    client, tmp_path, monkeypatch, filename, content_type, payload
):
    patient = create_patient(client)
    monkeypatch.setattr(patient_reports, "PRIVATE_STORAGE_DIR", tmp_path)

    response = client.post(
        f"/patients/{patient['id']}/reports",
        files={"file": (filename, payload, content_type)},
    )

    assert response.status_code in {400, 413, 415, 422}
    assert [path for path in tmp_path.iterdir() if path.suffix == ".pdf"] == []


def test_oversized_pdf_upload_is_rejected(client, tmp_path, monkeypatch):
    patient = create_patient(client)
    monkeypatch.setattr(patient_reports, "PRIVATE_STORAGE_DIR", tmp_path)
    monkeypatch.setattr(patient_reports, "MAX_UPLOAD_SIZE", 32)

    response = client.post(
        f"/patients/{patient['id']}/reports",
        files={"file": ("large.pdf", b"%PDF-" + b"x" * 28, "application/pdf")},
    )

    assert response.status_code == 413
    assert [path for path in tmp_path.iterdir() if path.suffix == ".pdf"] == []


def test_windows_path_filename_cannot_control_storage_path(client, tmp_path, monkeypatch):
    patient = create_patient(client)
    monkeypatch.setattr(patient_reports, "PRIVATE_STORAGE_DIR", tmp_path)

    response = client.post(
        f"/patients/{patient['id']}/reports",
        files={"file": (r"C:\report.pdf", pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 201
    stored_files = [path for path in tmp_path.iterdir() if path.suffix == ".pdf"]
    assert len(stored_files) == 1
    assert stored_files[0].name != "report.pdf"
