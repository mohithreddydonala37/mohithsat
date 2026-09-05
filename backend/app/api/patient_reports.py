import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from pydantic import ValidationError
from pypdf import PdfReader
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.models import PatientCreateRequest, PatientResponse, PatientUpdateRequest
from app.models import ReportCreateRequest, ReportResponse
from app.models.database import PatientDB, ReportDB, ConflictDB, ProvenanceDB, VerificationDB, get_db
from app.services.extraction_pipeline import extract_report
from app.config import get_settings


router = APIRouter(tags=["patients", "reports"])
MAX_UPLOAD_SIZE = get_settings().max_upload_size
PRIVATE_STORAGE_DIR = Path(__file__).resolve().parents[2] / "data" / "private_reports"


def _decode_list(value: str) -> list[str]:
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return decoded if isinstance(decoded, list) else []


def _patient_response(patient: PatientDB) -> PatientResponse:
    return PatientResponse(
        id=patient.id,
        age=patient.age,
        sex=patient.sex,
        symptoms=_decode_list(patient.symptoms),
        existing_conditions=_decode_list(patient.existing_conditions),
        allergies=_decode_list(patient.allergies),
        medications=_decode_list(patient.medications),
        other_info=patient.other_info,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )


def _report_response(report: ReportDB) -> ReportResponse:
    metadata = {}
    if report.report_metadata:
        try:
            decoded = json.loads(report.report_metadata)
            if isinstance(decoded, dict):
                metadata = decoded
        except json.JSONDecodeError:
            metadata = {}

    return ReportResponse(
        id=report.id,
        patient_id=report.patient_id,
        filename=report.filename,
        upload_date=report.upload_date,
        pages=report.pages,
        report_metadata=metadata or None,
        processing_status=metadata.get("processing_status", "UPLOADED"),
    )


def _reject_unsafe_filename(filename: str | None) -> None:
    if not filename or not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="A PDF filename is required")
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Unsafe filename")


async def _read_pdf(upload: UploadFile) -> tuple[str, bytes, list[dict[str, object]]]:
    _reject_unsafe_filename(upload.filename)
    if upload.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Only application/pdf is accepted")

    content = await upload.read(MAX_UPLOAD_SIZE + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty")
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Uploaded PDF is too large")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a PDF")

    try:
        reader = PdfReader(BytesIO(content), strict=True)
        pages = [
            {"page_number": page_number, "page_text": page.extract_text() or ""}
            for page_number, page in enumerate(reader.pages, start=1)
        ]
    except Exception:
        raise HTTPException(status_code=400, detail="PDF could not be parsed")

    if not pages:
        raise HTTPException(status_code=400, detail="PDF contains no pages")
    return upload.filename, content, pages


def _save_private_pdf(content: bytes) -> Path:
    try:
        PRIVATE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        path = PRIVATE_STORAGE_DIR / f"{uuid4()}.pdf"
        path.write_bytes(content)
        return path
    except OSError:
        raise HTTPException(status_code=500, detail="Report could not be stored")


def _persist_report(
    db: Session,
    patient_id: int,
    filename: str,
    file_path: str,
    pages: int,
    metadata: dict,
) -> ReportDB:
    report = ReportDB(
        patient_id=patient_id,
        filename=filename,
        file_path=file_path,
        pages=pages,
        report_metadata=json.dumps(metadata),
    )
    db.add(report)
    try:
        db.commit()
        db.refresh(report)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Report could not be saved")
    return report


@router.post("/patients", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(request: PatientCreateRequest, db: Session = Depends(get_db)):
    patient = PatientDB(
        age=request.age,
        sex=request.sex,
        symptoms=json.dumps(request.symptoms),
        existing_conditions=json.dumps(request.existing_conditions),
        allergies=json.dumps(request.allergies),
        medications=json.dumps(request.medications),
        other_info=request.other_info,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return _patient_response(patient)


@router.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(PatientDB).filter(PatientDB.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return _patient_response(patient)


@router.put("/patients/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    request: PatientUpdateRequest,
    db: Session = Depends(get_db),
):
    patient = db.query(PatientDB).filter(PatientDB.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    updates = request.model_dump(exclude_unset=True)
    list_fields = {"symptoms", "existing_conditions", "allergies", "medications"}
    for field, value in updates.items():
        setattr(patient, field, json.dumps(value) if field in list_fields else value)
    patient.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(patient)
    return _patient_response(patient)


@router.post(
    "/patients/{patient_id}/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_report(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    patient = db.query(PatientDB).filter(PatientDB.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if not isinstance(upload, StarletteUploadFile):
            raise HTTPException(status_code=400, detail="A PDF file is required")

        filename, content, pages = await _read_pdf(upload)
        stored_path = _save_private_pdf(content)
        metadata = {
            "original_filename": filename,
            "processing_status": "READY_FOR_REVIEW",
            "pages": pages,
        }
        try:
            report = _persist_report(
                db=db,
                patient_id=patient_id,
                filename=filename,
                file_path=str(stored_path),
                pages=len(pages),
                metadata=metadata,
            )
        except HTTPException:
            stored_path.unlink(missing_ok=True)
            raise
        return _report_response(report)

    try:
        report_request = ReportCreateRequest.model_validate(await request.json())
    except (json.JSONDecodeError, ValidationError):
        raise HTTPException(status_code=422, detail="Invalid report request")

    metadata = dict(report_request.report_metadata or {})
    metadata["processing_status"] = "UPLOADED"
    report = _persist_report(
        db=db,
        patient_id=patient_id,
        filename=report_request.filename,
        file_path=f"pending/{uuid4()}",
        pages=report_request.pages,
        metadata=metadata,
    )
    return _report_response(report)


@router.get("/patients/{patient_id}/reports", response_model=List[ReportResponse])
async def list_patient_reports(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(PatientDB).filter(PatientDB.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    reports = (
        db.query(ReportDB)
        .filter(ReportDB.patient_id == patient_id)
        .order_by(ReportDB.upload_date, ReportDB.id)
        .all()
    )
    return [_report_response(report) for report in reports]


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(ReportDB).filter(ReportDB.id == report_id).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_response(report)


@router.post("/reports/{report_id}/extract")
async def extract_report_data(report_id: int, db: Session = Depends(get_db)):
    report = db.query(ReportDB).filter(ReportDB.id == report_id).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        return await extract_report(report, db)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=502, detail="Extraction could not be completed")


@router.get("/reports/{report_id}/review")
async def get_extraction_review(report_id: int, db: Session = Depends(get_db)):
    report = db.query(ReportDB).filter(ReportDB.id == report_id).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    def serialize(row):
        result = {}
        for key, value in row.__dict__.items():
            if key.startswith("_"):
                continue
            if hasattr(value, "value"):
                value = value.value
            elif isinstance(value, datetime):
                value = value.isoformat()
            result[key] = value
        return result

    entity_ids = [row.id for rows in (report.lab_results, report.medications, report.allergies, report.conditions) for row in rows]
    return {
        "report": _report_response(report),
        "lab_results": [serialize(row) for row in report.lab_results],
        "medications": [serialize(row) for row in report.medications],
        "allergies": [serialize(row) for row in report.allergies],
        "conditions": [serialize(row) for row in report.conditions],
        "conflicts": [serialize(row) for row in db.query(ConflictDB).filter((ConflictDB.entity_id_1.in_(entity_ids)) | (ConflictDB.entity_id_2.in_(entity_ids))).all()] if entity_ids else [],
        "provenance": [serialize(row) for row in db.query(ProvenanceDB).filter(ProvenanceDB.entity_id.in_(entity_ids)).all()] if entity_ids else [],
        "verification": [serialize(row) for row in db.query(VerificationDB).filter(VerificationDB.entity_id.in_(entity_ids)).all()] if entity_ids else [],
    }
