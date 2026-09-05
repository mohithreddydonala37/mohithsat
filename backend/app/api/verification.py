from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from app.models import VerificationRequest, VerificationResponse, ErrorResponse
from app.models.database import get_db, VerificationDB, AuditEventDB, LabResultDB, MedicationDB, AllergyDB, ConditionDB
from app.services import VerificationService

router = APIRouter(prefix="/verification", tags=["verification"])


def _entity_row(db: Session, entity_type: str, entity_id: int):
    models = {
        "lab_result": LabResultDB,
        "medication": MedicationDB,
        "allergy": AllergyDB,
        "condition": ConditionDB,
    }
    model = models.get(entity_type)
    return db.query(model).filter(model.id == entity_id).first() if model else None


def _sync_entity(db: Session, entity_type: str, entity_id: int, status, corrected_value=None):
    row = _entity_row(db, entity_type, entity_id)
    if row is not None:
        row.verification_status = status
        if corrected_value is not None and entity_type == "lab_result":
            row.value = corrected_value
    return row


@router.post("/edit/{entity_type}/{entity_id}", response_model=VerificationResponse)
async def edit_entity(
    entity_type: str,
    entity_id: int,
    request: VerificationRequest,
    actor_id: str = "user",
    db: Session = Depends(get_db)
):
    """
    Edit an entity while preserving the original AI extraction.
    """
    from app.models import Verification
    from app.models.enums import VerificationStatus
    
    if request.corrected_value is None:
        raise HTTPException(
            status_code=400,
            detail="corrected_value is required for edit"
        )
    
    # Try to get existing verification record from database
    verification_db = db.query(VerificationDB).filter(
        VerificationDB.entity_type == entity_type,
        VerificationDB.entity_id == entity_id
    ).first()
    
    verification = None
    if verification_db is None:
        # Editing requires an existing AI extraction so its original value is safe.
        raise HTTPException(
            status_code=404,
            detail="Verification record not found; original AI value is required"
        )
    else:
        # Check if can edit
        if verification_db.status == VerificationStatus.VERIFIED:
            raise HTTPException(
                status_code=400,
                detail="Cannot edit a verified record"
            )
        
        previous_value = verification_db.corrected_value or verification_db.original_ai_value

        # Update verification (preserve original)
        verification = Verification(
            entity_type=verification_db.entity_type,
            entity_id=verification_db.entity_id,
            status=verification_db.status,
            original_ai_value=verification_db.original_ai_value,
            corrected_value=verification_db.corrected_value,
            verified_by=verification_db.verified_by,
            notes=verification_db.notes
        )
        
        verification, _ = VerificationService.edit_value(
            verification=verification,
            new_value=request.corrected_value,
            actor_id=actor_id,
            changed_fields=["value"]
        )
        
        # Sync to database
        verification_db.status = VerificationStatus.EDITED
        verification_db.corrected_value = request.corrected_value
        _sync_entity(db, entity_type, entity_id, VerificationStatus.EDITED, request.corrected_value)
    
    # Create audit event
    audit_event = AuditEventDB(
        entity_type=entity_type,
        entity_id=entity_id,
        action="edited",
        previous_value=previous_value,
        new_value=request.corrected_value,
        actor="HUMAN",
        actor_id=actor_id,
        notes=f"Changed fields: value"
    )
    db.add(audit_event)
    db.commit()
    db.refresh(verification_db)
    
    return VerificationResponse(
        id=verification_db.id,
        entity_type=verification_db.entity_type,
        entity_id=verification_db.entity_id,
        status=verification_db.status,
        original_ai_value=verification_db.original_ai_value,
        corrected_value=verification_db.corrected_value,
        verified_by=verification_db.verified_by,
        verified_at=verification_db.verified_at,
        notes=verification_db.notes,
        created_at=verification_db.created_at
    )


@router.post("/verify/{entity_type}/{entity_id}", response_model=VerificationResponse)
async def verify_entity(
    entity_type: str,
    entity_id: int,
    request: VerificationRequest,
    actor_id: str = "user",
    db: Session = Depends(get_db)
):
    """
    Mark an entity as verified by a human.
    """
    verification_db = db.query(VerificationDB).filter(
        VerificationDB.entity_type == entity_type,
        VerificationDB.entity_id == entity_id
    ).first()
    
    if verification_db is None:
        raise HTTPException(
            status_code=404,
            detail="Verification record not found"
        )
    
    # Check if can verify
    from app.models.enums import VerificationStatus
    current_status = (
        verification_db.status.value
        if hasattr(verification_db.status, "value")
        else str(verification_db.status)
    )
    if current_status not in [VerificationStatus.PENDING.value, VerificationStatus.EDITED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot verify a record with status: {verification_db.status}"
        )
    
    previous_status = current_status

    # Update verification
    verification = VerificationService.verify(
        verification=VerificationService.create_verification(
            entity_type=verification_db.entity_type,
            entity_id=verification_db.entity_id,
            original_ai_value=verification_db.original_ai_value
        ),
        verified_by=actor_id,
        notes=request.notes
    )
    
    # Sync to database
    verification_db.status = VerificationStatus.VERIFIED
    verification_db.verified_by = actor_id
    verification_db.notes = request.notes
    _sync_entity(db, entity_type, entity_id, VerificationStatus.VERIFIED)
    
    # Create audit event
    audit_event = AuditEventDB(
        entity_type=entity_type,
        entity_id=entity_id,
        action="verified",
        previous_value=(
            previous_status
        ),
        new_value=VerificationStatus.VERIFIED,
        actor="HUMAN",
        actor_id=actor_id,
        notes=request.notes
    )
    db.add(audit_event)
    db.commit()
    db.refresh(verification_db)
    
    return VerificationResponse(
        id=verification_db.id,
        entity_type=verification_db.entity_type,
        entity_id=verification_db.entity_id,
        status=verification_db.status,
        original_ai_value=verification_db.original_ai_value,
        corrected_value=verification_db.corrected_value,
        verified_by=verification_db.verified_by,
        verified_at=verification_db.verified_at,
        notes=verification_db.notes,
        created_at=verification_db.created_at
    )


@router.post("/flag/{entity_type}/{entity_id}", response_model=VerificationResponse)
async def flag_entity(
    entity_type: str,
    entity_id: int,
    request: VerificationRequest,
    actor_id: str = "user",
    db: Session = Depends(get_db)
):
    """
    Flag an entity for review.
    """
    verification_db = db.query(VerificationDB).filter(
        VerificationDB.entity_type == entity_type,
        VerificationDB.entity_id == entity_id
    ).first()
    
    if verification_db is None:
        raise HTTPException(
            status_code=404,
            detail="Verification record not found"
        )
    
    # Update verification status
    from app.models.enums import VerificationStatus
    verification_db.status = VerificationStatus.FLAGGED
    verification_db.notes = request.notes
    _sync_entity(db, entity_type, entity_id, VerificationStatus.FLAGGED)
    
    # Create audit event
    audit_event = AuditEventDB(
        entity_type=entity_type,
        entity_id=entity_id,
        action="flagged",
        previous_value=None,
        new_value=VerificationStatus.FLAGGED,
        actor="HUMAN",
        actor_id=actor_id,
        notes=request.notes
    )
    db.add(audit_event)
    db.commit()
    db.refresh(verification_db)
    
    return VerificationResponse(
        id=verification_db.id,
        entity_type=verification_db.entity_type,
        entity_id=verification_db.entity_id,
        status=verification_db.status,
        original_ai_value=verification_db.original_ai_value,
        corrected_value=verification_db.corrected_value,
        verified_by=verification_db.verified_by,
        verified_at=verification_db.verified_at,
        notes=verification_db.notes,
        created_at=verification_db.created_at
    )


@router.get("/{entity_type}/{entity_id}", response_model=VerificationResponse)
async def get_verification(
    entity_type: str, 
    entity_id: int, 
    db: Session = Depends(get_db)
):
    """
    Get verification status for an entity.
    """
    verification_db = db.query(VerificationDB).filter(
        VerificationDB.entity_type == entity_type,
        VerificationDB.entity_id == entity_id
    ).first()
    
    if verification_db is None:
        raise HTTPException(
            status_code=404,
            detail="Verification record not found"
        )
    
    return VerificationResponse(
        id=verification_db.id,
        entity_type=verification_db.entity_type,
        entity_id=verification_db.entity_id,
        status=verification_db.status,
        original_ai_value=verification_db.original_ai_value,
        corrected_value=verification_db.corrected_value,
        verified_by=verification_db.verified_by,
        verified_at=verification_db.verified_at,
        notes=verification_db.notes,
        created_at=verification_db.created_at
    )


@router.post("/reset/{entity_type}/{entity_id}", response_model=VerificationResponse)
async def reset_to_original(
    entity_type: str,
    entity_id: int,
    actor_id: str = "user",
    db: Session = Depends(get_db)
):
    """
    Reset a corrected value back to the original AI extraction.
    """
    verification_db = db.query(VerificationDB).filter(
        VerificationDB.entity_type == entity_type,
        VerificationDB.entity_id == entity_id
    ).first()
    
    if verification_db is None:
        raise HTTPException(
            status_code=404,
            detail="Verification record not found"
        )
    
    # Get previous value
    previous_value = verification_db.corrected_value
    
    # Reset to original
    from app.models.enums import VerificationStatus
    verification_db.corrected_value = verification_db.original_ai_value
    verification_db.status = VerificationStatus.PENDING
    
    # Create audit event
    audit_event = AuditEventDB(
        entity_type=entity_type,
        entity_id=entity_id,
        action="edited",
        previous_value=previous_value,
        new_value=verification_db.original_ai_value,
        actor="HUMAN",
        actor_id=actor_id,
        notes="Reset to original AI extraction"
    )
    db.add(audit_event)
    db.commit()
    db.refresh(verification_db)
    
    return VerificationResponse(
        id=verification_db.id,
        entity_type=verification_db.entity_type,
        entity_id=verification_db.entity_id,
        status=verification_db.status,
        original_ai_value=verification_db.original_ai_value,
        corrected_value=verification_db.corrected_value,
        verified_by=verification_db.verified_by,
        verified_at=verification_db.verified_at,
        notes=verification_db.notes,
        created_at=verification_db.created_at
    )


@router.get("/audit/{entity_type}/{entity_id}")
async def get_audit_trail(
    entity_type: str, 
    entity_id: int, 
    db: Session = Depends(get_db)
):
    """
    Get audit trail for an entity.
    """
    audit_events = db.query(AuditEventDB).filter(
        AuditEventDB.entity_type == entity_type,
        AuditEventDB.entity_id == entity_id
    ).all()
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "audit_events": [
            {
                "id": event.id,
                "action": event.action,
                "previous_value": event.previous_value,
                "new_value": event.new_value,
                "actor": event.actor,
                "actor_id": event.actor_id,
                "timestamp": event.timestamp,
                "notes": event.notes
            }
            for event in audit_events
        ],
        "count": len(audit_events)
    }
