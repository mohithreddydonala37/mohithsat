from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from app.models import ConflictResponse, ConflictResolutionRequest
from app.models.database import get_db, ConflictDB, LabResultDB, MedicationDB, AllergyDB, ConditionDB
from app.services import ConflictEngine

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


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
        for conflict in stored_conflicts
    ]


@router.get("/", response_model=List[ConflictResponse])
async def get_conflicts(db: Session = Depends(get_db)):
    """
    Get all detected conflicts.
    """
    conflicts = db.query(ConflictDB).all()
    
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


@router.get("/unresolved", response_model=List[ConflictResponse])
async def get_unresolved_conflicts(db: Session = Depends(get_db)):
    """
    Get only unresolved conflicts.
    """
    conflicts = db.query(ConflictDB).filter(ConflictDB.resolved == False).all()
    
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


@router.get("/{entity_type}/{entity_id}", response_model=List[ConflictResponse])
async def get_entity_conflicts(entity_type: str, entity_id: int, db: Session = Depends(get_db)):
    """
    Get conflicts involving a specific entity.
    """
    conflicts = db.query(ConflictDB).filter(
        ConflictDB.entity_type == entity_type,
        (ConflictDB.entity_id_1 == entity_id) | (ConflictDB.entity_id_2 == entity_id)
    ).all()
    
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
