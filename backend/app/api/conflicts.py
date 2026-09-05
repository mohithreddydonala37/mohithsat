from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from app.models import ConflictResponse, ConflictResolutionRequest, ConflictResolveRequest, ConflictFlagRequest, ConflictCenterResponse
from app.models.database import get_db, ConflictDB, LabResultDB, MedicationDB, AllergyDB, ConditionDB, ReportDB, ProvenanceDB, VerificationDB, AuditEventDB
from app.services import ConflictEngine

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


def _status(conflict: ConflictDB) -> str:
    if conflict.resolution_notes and conflict.resolution_notes.startswith("FLAGGED"):
        return "FLAGGED"
    return "RESOLVED" if conflict.resolved else "UNRESOLVED"


def _entity(db: Session, entity_type: str, entity_id: int):
    tables = {"lab_result": LabResultDB, "medication": MedicationDB, "allergy": AllergyDB, "condition": ConditionDB}
    table = tables.get(entity_type)
    return db.query(table).filter(table.id == entity_id).first() if table else None


def _side(db: Session, entity_type: str, entity_id: int):
    row = _entity(db, entity_type, entity_id)
    if row is None:
        return None
    report_id = getattr(row, "report_id", None)
    report = db.query(ReportDB).filter(ReportDB.id == report_id).first() if report_id else None
    provenance = db.query(ProvenanceDB).filter(ProvenanceDB.entity_type == entity_type, ProvenanceDB.entity_id == entity_id).order_by(ProvenanceDB.id.desc()).first()
    verification = db.query(VerificationDB).filter(VerificationDB.entity_type == entity_type, VerificationDB.entity_id == entity_id).order_by(VerificationDB.id.desc()).first()
    if entity_type == "lab_result":
        value = row.value
        details = {"test_name": row.test_name, "unit": row.unit, "reference_low": row.reference_low, "reference_high": row.reference_high, "reference_text": row.reference_text, "observation": row.observation, "report_date": row.report_date}
    elif entity_type == "medication":
        value = row.name
        details = {"name": row.name, "dosage": row.dosage, "frequency": row.frequency, "route": row.route}
    elif entity_type == "allergy":
        value = row.allergen
        details = {"allergen": row.allergen, "severity": row.severity, "reaction": row.reaction}
    else:
        value = row.name
        details = {"name": row.name, "status": row.status, "diagnosis_date": row.diagnosis_date, "notes": row.notes}
    details = {key: (item.isoformat() if hasattr(item, "isoformat") else item) for key, item in details.items()}
    return {"entity_type": entity_type, "entity_id": entity_id, "report_id": report_id,
            "source_document": report.filename if report else (provenance.source_document if provenance else None),
            "source_page": getattr(row, "source_page", None) or (provenance.source_page if provenance else None),
            "source_text": getattr(row, "source_text", None) or (provenance.source_text if provenance else None),
            "value": value, "details": details,
            "provenance": {"origin": str(provenance.origin.value if provenance and hasattr(provenance.origin, "value") else provenance.origin), "provider": provenance.ai_provider, "model": provenance.ai_model} if provenance else None,
            "verification": {"status": str(verification.status.value if verification and hasattr(verification.status, "value") else verification.status)} if verification else None}


def _center(db: Session, conflict: ConflictDB):
    data = {key: getattr(conflict, key) for key in ("id", "conflict_type", "entity_type", "entity_id_1", "entity_id_2", "description", "severity", "resolved", "resolution_notes", "created_at")}
    data["status"] = _status(conflict)
    data["source_a"] = _side(db, conflict.entity_type, conflict.entity_id_1)
    data["source_b"] = _side(db, conflict.entity_type, conflict.entity_id_2)
    return data


def _response(conflict: ConflictDB) -> ConflictResponse:
    """Serialize the canonical conflict row for legacy/list endpoints."""
    return ConflictResponse(
        id=conflict.id,
        conflict_type=conflict.conflict_type,
        entity_type=conflict.entity_type,
        entity_id_1=conflict.entity_id_1,
        entity_id_2=conflict.entity_id_2,
        description=conflict.description,
        severity=conflict.severity,
        resolved=conflict.resolved,
        resolution_notes=conflict.resolution_notes,
        created_at=conflict.created_at,
    )


@router.get("", response_model=List[ConflictCenterResponse])
async def list_conflict_center(db: Session = Depends(get_db)):
    return [_center(db, item) for item in db.query(ConflictDB).order_by(ConflictDB.created_at.desc()).all()]


@router.get("/{conflict_id}", response_model=ConflictCenterResponse)
async def get_conflict_center(conflict_id: int, db: Session = Depends(get_db)):
    conflict = db.query(ConflictDB).filter(ConflictDB.id == conflict_id).first()
    if conflict is None:
        raise HTTPException(status_code=404, detail="Conflict not found")
    return _center(db, conflict)


@router.post("/{conflict_id}/resolve", response_model=ConflictCenterResponse)
async def resolve_conflict_center(conflict_id: int, request: ConflictResolveRequest, db: Session = Depends(get_db)):
    conflict = db.query(ConflictDB).filter(ConflictDB.id == conflict_id).first()
    if conflict is None:
        raise HTTPException(status_code=404, detail="Conflict not found")
    before = _status(conflict)
    conflict.resolved = request.decision != "UNRESOLVED"
    note = request.notes or ""
    conflict.resolution_notes = f"DECISION={request.decision}; NOTES={note}"
    db.add(AuditEventDB(entity_type="conflict", entity_id=conflict.id, action=f"RESOLVE_{request.decision}", previous_value=before, new_value=_status(conflict), actor="HUMAN", notes=note))
    db.commit()
    db.refresh(conflict)
    return _center(db, conflict)


@router.post("/{conflict_id}/flag", response_model=ConflictCenterResponse)
async def flag_conflict_center(conflict_id: int, request: ConflictFlagRequest, db: Session = Depends(get_db)):
    conflict = db.query(ConflictDB).filter(ConflictDB.id == conflict_id).first()
    if conflict is None:
        raise HTTPException(status_code=404, detail="Conflict not found")
    before = _status(conflict)
    conflict.resolved = False
    conflict.resolution_notes = f"FLAGGED; NOTES={request.notes or ''}"
    db.add(AuditEventDB(entity_type="conflict", entity_id=conflict.id, action="FLAG", previous_value=before, new_value="FLAGGED", actor="HUMAN", notes=request.notes))
    db.commit()
    db.refresh(conflict)
    return _center(db, conflict)


@router.get("/detect", response_model=List[ConflictResponse])
async def detect_conflicts(db: Session = Depends(get_db)):
    """
    Detect all conflicts across all entity types.
    
    This runs the ConflictEngine on all stored entities and returns
    any detected conflicts.
    """
    # Get all entities from database
    lab_results = db.query(LabResultDB).all()
    medications = db.query(MedicationDB).all()
    allergies = db.query(AllergyDB).all()
    conditions = db.query(ConditionDB).all()
    
    # Convert to Pydantic models for ConflictEngine
    from app.models import LabResult, Medication, Allergy, Condition
    
    lab_result_models = [
        LabResult(
            id=lr.id,
            report_id=lr.report_id,
            test_name=lr.test_name,
            value=lr.value,
            unit=lr.unit,
            reference_low=lr.reference_low,
            reference_high=lr.reference_high,
            reference_text=lr.reference_text,
            observation=lr.observation,
            report_date=lr.report_date,
            source_page=lr.source_page,
            source_text=lr.source_text,
            confidence=lr.confidence,
            range_status=lr.range_status,
            origin=lr.origin,
            verification_status=lr.verification_status,
            provider=lr.provider,
            model=lr.model
        )
        for lr in lab_results
    ]
    
    medication_models = [
        Medication(
            id=m.id,
            report_id=m.report_id,
            patient_id=m.patient_id,
            name=m.name,
            dosage=m.dosage,
            frequency=m.frequency,
            route=m.route,
            start_date=m.start_date,
            end_date=m.end_date,
            source_page=m.source_page,
            source_text=m.source_text,
            confidence=m.confidence,
            origin=m.origin,
            verification_status=m.verification_status,
            provider=m.provider,
            model=m.model
        )
        for m in medications
    ]
    
    allergy_models = [
        Allergy(
            id=a.id,
            report_id=a.report_id,
            patient_id=a.patient_id,
            allergen=a.allergen,
            severity=a.severity,
            reaction=a.reaction,
            source_page=a.source_page,
            source_text=a.source_text,
            confidence=a.confidence,
            origin=a.origin,
            verification_status=a.verification_status,
            provider=a.provider,
            model=a.model
        )
        for a in allergies
    ]
    
    condition_models = [
        Condition(
            id=c.id,
            report_id=c.report_id,
            patient_id=c.patient_id,
            name=c.name,
            diagnosis_date=c.diagnosis_date,
            status=c.status,
            notes=c.notes,
            source_page=c.source_page,
            source_text=c.source_text,
            confidence=c.confidence,
            origin=c.origin,
            verification_status=c.verification_status,
            provider=c.provider,
            model=c.model
        )
        for c in conditions
    ]
    
    # Run conflict detection
    conflicts = ConflictEngine.detect_all_conflicts(
        lab_results=lab_result_models,
        medications=medication_models,
        allergies=allergy_models,
        conditions=condition_models
    )
    
    # Clear old conflicts and save new ones
    db.query(ConflictDB).delete()
    
    for conflict in conflicts:
        conflict_db = ConflictDB(
            conflict_type=conflict.conflict_type,
            entity_type=conflict.entity_type,
            entity_id_1=conflict.entity_id_1,
            entity_id_2=conflict.entity_id_2,
            description=conflict.description,
            severity=conflict.severity,
            resolved=conflict.resolved,
            resolution_notes=conflict.resolution_notes
        )
        db.add(conflict_db)
    
    db.commit()
    
    # Return stored conflicts
    stored_conflicts = db.query(ConflictDB).all()
    
    return [_response(conflict) for conflict in stored_conflicts]


@router.get("/", response_model=List[ConflictResponse])
async def get_conflicts(db: Session = Depends(get_db)):
    """
    Get all detected conflicts.
    """
    conflicts = db.query(ConflictDB).all()
    
    return [_response(conflict) for conflict in conflicts]


@router.get("/unresolved", response_model=List[ConflictResponse])
async def get_unresolved_conflicts(db: Session = Depends(get_db)):
    """
    Get only unresolved conflicts.
    """
    conflicts = db.query(ConflictDB).filter(ConflictDB.resolved == False).all()
    
    return [_response(conflict) for conflict in conflicts]


@router.get("/{entity_type}/{entity_id}", response_model=List[ConflictResponse])
async def get_entity_conflicts(entity_type: str, entity_id: int, db: Session = Depends(get_db)):
    """
    Get conflicts involving a specific entity.
    """
    conflicts = db.query(ConflictDB).filter(
        ConflictDB.entity_type == entity_type,
        (ConflictDB.entity_id_1 == entity_id) | (ConflictDB.entity_id_2 == entity_id)
    ).all()
    
    return [_response(conflict) for conflict in conflicts]


@router.post("/resolve/{conflict_id}", response_model=ConflictResponse)
async def resolve_conflict(conflict_id: int, request: ConflictResolutionRequest, db: Session = Depends(get_db)):
    """
    Mark a conflict as resolved.
    
    Note: This does NOT automatically select which value is correct.
    It only marks that a human has reviewed and resolved the conflict.
    """
    conflict = db.query(ConflictDB).filter(ConflictDB.id == conflict_id).first()
    
    if conflict is None:
        raise HTTPException(
            status_code=404,
            detail="Conflict not found"
        )
    
    # Update conflict resolution
    conflict.resolved = request.resolved
    conflict.resolution_notes = request.resolution_notes
    db.commit()
    db.refresh(conflict)
    
    return ConflictResponse(
        id=conflict.id,
        conflict_type=conflict.conflict_type,
        entity_type=conflict.entity_type,
        entity_id_1=conflict.entity_id_1,
        entity_id_2=conflict.entity_id_2,
        description=conflict.description,
        severity=conflict.severity,
        resolved=conflict.resolved,
        resolution_notes=conflict.resolution_notes,
        created_at=conflict.created_at
    )


@router.get("/severity/{severity}", response_model=List[ConflictResponse])
async def get_conflicts_by_severity(severity: str, db: Session = Depends(get_db)):
    """
    Get conflicts filtered by severity level.
    """
    conflicts = db.query(ConflictDB).filter(ConflictDB.severity == severity).all()
    
    return [
        ConflictResponse(
            id=conflict.id,
            conflict_type=conflict.conflict_type,
            entity_type=conflict.entity_type,
            entity_id_1=conflict.entity_id_1,
            entity_id_2=conflict.entity_id_2,
            description=conflict.description,
            severity=conflict.severity,
            resolved=conflict.resolved,
            resolution_notes=conflict.resolution_notes,
            created_at=conflict.created_at
        )
        for conflict in conflicts
    ]


@router.get("/stats/summary")
async def get_conflict_summary(db: Session = Depends(get_db)):
    """
    Get a summary of conflict statistics.
    """
    all_conflicts = db.query(ConflictDB).all()
    
    total = len(all_conflicts)
    unresolved = len([c for c in all_conflicts if not c.resolved])
    high_severity = len([c for c in all_conflicts if c.severity == "high"])
    medium_severity = len([c for c in all_conflicts if c.severity == "medium"])
    low_severity = len([c for c in all_conflicts if c.severity == "low"])
    
    by_type = {}
    for conflict in all_conflicts:
        conflict_type = conflict.conflict_type
        if conflict_type not in by_type:
            by_type[conflict_type] = 0
        by_type[conflict_type] += 1
    
    return {
        "total_conflicts": total,
        "unresolved_conflicts": unresolved,
        "by_severity": {
            "high": high_severity,
            "medium": medium_severity,
            "low": low_severity
        },
        "by_type": by_type
    }
