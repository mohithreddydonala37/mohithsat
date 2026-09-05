from typing import Optional, List
from datetime import datetime, timezone
from app.models import (
    Provenance,
    Origin,
    VerificationStatus
)


class ProvenanceService:
    """
    Provenance tracking service.
    
    This service maintains the origin and history of extracted facts,
    ensuring source traceability and auditability.
    """
    
    @staticmethod
    def create_provenance(
        entity_type: str,
        entity_id: int,
        source_document: Optional[str] = None,
        source_page: Optional[int] = None,
        source_text: Optional[str] = None,
        origin: Origin = Origin.AI_EXTRACTED,
        ai_provider: Optional[str] = None,
        ai_model: Optional[str] = None,
        verification_state: str = "PENDING"
    ) -> Provenance:
        """
        Create a provenance record for an entity.
        
        Args:
            entity_type: Type of entity (lab_result, medication, etc.)
            entity_id: ID of the entity
            source_document: Name/path of source document
            source_page: Page number in source document
            source_text: Original text from source
            origin: Origin of the data (AI_EXTRACTED, USER_PROVIDED, etc.)
            ai_provider: AI provider used for extraction
            ai_model: AI model used for extraction
            verification_state: Current verification state
            
        Returns:
            Provenance object
        """
        return Provenance(
            entity_type=entity_type,
            entity_id=entity_id,
            source_document=source_document,
            source_page=source_page,
            source_text=source_text,
            origin=origin,
            ai_provider=ai_provider,
            ai_model=ai_model,
            verification_state=verification_state,
            timestamp=datetime.now(timezone.utc)
        )
    
    @staticmethod
    def update_verification_state(
        provenance: Provenance,
        new_state: str
    ) -> Provenance:
        """
        Update the verification state of a provenance record.
        
        Args:
            provenance: Existing provenance record
            new_state: New verification state
            
        Returns:
            Updated provenance record
        """
        provenance.verification_state = new_state
        provenance.timestamp = datetime.now(timezone.utc)
        return provenance
    
    @staticmethod
    def record_ai_extraction(
        entity_type: str,
        entity_id: int,
        source_document: str,
        source_page: Optional[int],
        source_text: Optional[str],
        provider: str,
        model: str
    ) -> Provenance:
        """
        Record provenance for AI-extracted data.
        
        Args:
            entity_type: Type of entity
            entity_id: ID of the entity
            source_document: Source document name
            source_page: Page number
            source_text: Source text
            provider: AI provider name
            model: AI model name
            
        Returns:
            Provenance record
        """
        return ProvenanceService.create_provenance(
            entity_type=entity_type,
            entity_id=entity_id,
            source_document=source_document,
            source_page=source_page,
            source_text=source_text,
            origin=Origin.AI_EXTRACTED,
            ai_provider=provider,
            ai_model=model,
            verification_state="PENDING"
        )
    
    @staticmethod
    def record_user_input(
        entity_type: str,
        entity_id: int
    ) -> Provenance:
        """
        Record provenance for user-provided data.
        
        Args:
            entity_type: Type of entity
            entity_id: ID of the entity
            
        Returns:
            Provenance record
        """
        return ProvenanceService.create_provenance(
            entity_type=entity_type,
            entity_id=entity_id,
            origin=Origin.USER_PROVIDED,
            verification_state="PENDING"
        )
    
    @staticmethod
    def record_synthetic_data(
        entity_type: str,
        entity_id: int,
        source_document: Optional[str] = None
    ) -> Provenance:
        """
        Record provenance for synthetic test data.
        
        Args:
            entity_type: Type of entity
            entity_id: ID of the entity
            source_document: Source document if applicable
            
        Returns:
            Provenance record
        """
        return ProvenanceService.create_provenance(
            entity_type=entity_type,
            entity_id=entity_id,
            source_document=source_document,
            origin=Origin.SYNTHETIC_SOURCE,
            verification_state="PENDING"
        )
    
    @staticmethod
    def record_human_verification(
        provenance: Provenance,
        verified_by: str
    ) -> Provenance:
        """
        Record that a human has verified the data.
        
        Args:
            provenance: Existing provenance record
            verified_by: Identifier of the person who verified
            
        Returns:
            New provenance record for the verification event
        """
        # Create a new provenance record for the verification event
        return ProvenanceService.create_provenance(
            entity_type=provenance.entity_type,
            entity_id=provenance.entity_id,
            source_document=provenance.source_document,
            source_page=provenance.source_page,
            source_text=provenance.source_text,
            origin=Origin.HUMAN_VERIFIED,
            ai_provider=provenance.ai_provider,
            ai_model=provenance.ai_model,
            verification_state="VERIFIED"
        )
    
    @staticmethod
    def get_provenance_chain(
        provenance_records: List[Provenance],
        entity_id: int
    ) -> List[Provenance]:
        """
        Get the complete provenance chain for an entity.
        
        Args:
            provenance_records: All provenance records
            entity_id: ID of the entity
            
        Returns:
            List of provenance records for the entity, sorted by timestamp
        """
        entity_records = [p for p in provenance_records if p.entity_id == entity_id]
        return sorted(entity_records, key=lambda x: x.timestamp)
    
    @staticmethod
    def validate_provenance_completeness(
        provenance: Provenance,
        require_source: bool = True
    ) -> bool:
        """
        Validate that a provenance record has required fields.
        
        Args:
            provenance: Provenance record to validate
            require_source: Whether source fields are required
            
        Returns:
            True if valid, False otherwise
        """
        if not provenance.entity_type or not provenance.entity_id:
            return False
        
        if require_source:
            if not provenance.source_document:
                return False
        
        # If origin is AI_EXTRACTED, provider and model should be present
        if provenance.origin == Origin.AI_EXTRACTED:
            if not provenance.ai_provider or not provenance.ai_model:
                return False
        
        return True
