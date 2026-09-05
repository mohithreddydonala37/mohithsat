from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import ProvenanceResponse, Origin
from app.models.database import get_db, ProvenanceDB
from app.services import ProvenanceService

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/{entity_type}/{entity_id}", response_model=ProvenanceResponse)
async def get_evidence(entity_type: str, entity_id: int, db: Session = Depends(get_db)):
    """
    Get evidence (provenance) for an entity.
    
    Returns source document, page, source text, origin, provider, model,
    and verification state for the entity.
    """
    provenance_db = db.query(ProvenanceDB).filter(
        ProvenanceDB.entity_type == entity_type,
        ProvenanceDB.entity_id == entity_id
    ).first()
    
    if provenance_db is None:
        raise HTTPException(
            status_code=404,
            detail="Evidence not found for this entity"
        )
    
    return ProvenanceResponse(
        id=provenance_db.id,
        entity_type=provenance_db.entity_type,
        entity_id=provenance_db.entity_id,
        source_document=provenance_db.source_document,
        source_page=provenance_db.source_page,
        source_text=provenance_db.source_text,
        origin=provenance_db.origin,
        ai_provider=provenance_db.ai_provider,
        ai_model=provenance_db.ai_model,
        verification_state=provenance_db.verification_state,
        timestamp=provenance_db.timestamp
    )


@router.post("/{entity_type}/{entity_id}", response_model=ProvenanceResponse)
async def create_evidence(
    entity_type: str,
    entity_id: int,
    source_document: Optional[str] = None,
    source_page: Optional[int] = None,
    source_text: Optional[str] = None,
    origin: str = "AI_EXTRACTED",
    ai_provider: Optional[str] = None,
    ai_model: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Create evidence (provenance) for an entity.
    
    This is typically called during AI extraction to record
    the source of extracted information.
    """
    # Handle both string and enum origin
    if isinstance(origin, str):
        try:
            origin_enum = Origin(origin)
        except ValueError:
            origin_enum = Origin.AI_EXTRACTED
    else:
        origin_enum = origin
    
    provenance = ProvenanceService.create_provenance(
        entity_type=entity_type,
        entity_id=entity_id,
        source_document=source_document,
        source_page=source_page,
        source_text=source_text,
        origin=origin_enum,
        ai_provider=ai_provider,
        ai_model=ai_model,
        verification_state="PENDING"
    )
    
    # Save to database
    provenance_db = ProvenanceDB(
        entity_type=provenance.entity_type,
        entity_id=provenance.entity_id,
        source_document=provenance.source_document,
        source_page=provenance.source_page,
        source_text=provenance.source_text,
        origin=provenance.origin,
        ai_provider=provenance.ai_provider,
        ai_model=provenance.ai_model,
        verification_state=provenance.verification_state
    )
    db.add(provenance_db)
    db.commit()
    db.refresh(provenance_db)
    
    return ProvenanceResponse(
        id=provenance_db.id,
        entity_type=provenance_db.entity_type,
        entity_id=provenance_db.entity_id,
        source_document=provenance_db.source_document,
        source_page=provenance_db.source_page,
        source_text=provenance_db.source_text,
        origin=provenance_db.origin,
        ai_provider=provenance_db.ai_provider,
        ai_model=provenance_db.ai_model,
        verification_state=provenance_db.verification_state,
        timestamp=provenance_db.timestamp
    )


@router.get("/chain/{entity_type}/{entity_id}")
async def get_evidence_chain(entity_type: str, entity_id: int, db: Session = Depends(get_db)):
    """
    Get the complete evidence chain for an entity.
    
    Returns all provenance records for the entity, sorted by timestamp,
    showing the history of changes and verifications.
    """
    all_provenance = db.query(ProvenanceDB).filter(
        ProvenanceDB.entity_type == entity_type,
        ProvenanceDB.entity_id == entity_id
    ).order_by(ProvenanceDB.timestamp).all()
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "chain": [
            {
                "id": p.id,
                "source_document": p.source_document,
                "source_page": p.source_page,
                "source_text": p.source_text,
                "origin": p.origin,
                "ai_provider": p.ai_provider,
                "ai_model": p.ai_model,
                "verification_state": p.verification_state,
                "timestamp": p.timestamp
            }
            for p in all_provenance
        ],
        "count": len(all_provenance)
    }


@router.get("/validate/{entity_type}/{entity_id}")
async def validate_evidence(
    entity_type: str, 
    entity_id: int, 
    require_source: bool = True,
    db: Session = Depends(get_db)
):
    """
    Validate that evidence is complete and properly structured.
    """
    provenance_db = db.query(ProvenanceDB).filter(
        ProvenanceDB.entity_type == entity_type,
        ProvenanceDB.entity_id == entity_id
    ).first()
    
    if provenance_db is None:
        return {
            "valid": False,
            "reason": "Evidence not found"
        }
    
    # Convert to Pydantic for validation
    provenance = Provenance(
        entity_type=provenance_db.entity_type,
        entity_id=provenance_db.entity_id,
        source_document=provenance_db.source_document,
        source_page=provenance_db.source_page,
        source_text=provenance_db.source_text,
        origin=provenance_db.origin,
        ai_provider=provenance_db.ai_provider,
        ai_model=provenance_db.ai_model,
        verification_state=provenance_db.verification_state
    )
    
    is_valid = ProvenanceService.validate_provenance_completeness(
        provenance,
        require_source=require_source
    )
    
    return {
        "valid": is_valid,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "require_source": require_source
    }


# Import Provenance for validation
from app.models import Provenance
