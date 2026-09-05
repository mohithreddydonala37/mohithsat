from typing import Optional, List
from datetime import datetime, timezone
from app.models import (
    Verification,
    AuditEvent,
    VerificationStatus,
    Origin
)


class VerificationService:
    """
    Human-in-the-loop verification service.
    
    Manages the verification state machine and ensures that
    original AI extractions are preserved during human edits.
    """
    
    @staticmethod
    def create_verification(
        entity_type: str,
        entity_id: int,
        original_ai_value: Optional[str] = None,
        origin: Origin = Origin.AI_EXTRACTED
    ) -> Verification:
        """
        Create a new verification record.
        
        Args:
            entity_type: Type of entity (lab_result, medication, etc.)
            entity_id: ID of the entity
            original_ai_value: Original value extracted by AI
            origin: Origin of the data
            
        Returns:
            Verification record
        """
        return Verification(
            entity_type=entity_type,
            entity_id=entity_id,
            status=VerificationStatus.PENDING,
            original_ai_value=original_ai_value,
            corrected_value=original_ai_value,  # Initially same as original
            origin=origin,
            updated_at=datetime.now(timezone.utc)
        )
    
    @staticmethod
    def edit_value(
        verification: Verification,
        new_value: str,
        actor_id: str,
        changed_fields: Optional[List[str]] = None
    ) -> tuple[Verification, AuditEvent]:
        """
        Edit a value while preserving the original AI extraction.
        
        Args:
            verification: Existing verification record
            new_value: New corrected value
            actor_id: ID of the person making the edit
            changed_fields: List of fields that were changed
            
        Returns:
            Tuple of (updated verification, audit event)
        """
        # Store the current value as previous for audit
        previous_value = verification.corrected_value or verification.original_ai_value
        
        # Update verification
        verification.status = VerificationStatus.EDITED
        verification.corrected_value = new_value
        verification.updated_at = datetime.now(timezone.utc)
        
        # Create audit event
        audit_event = AuditEvent(
            entity_type=verification.entity_type,
            entity_id=verification.entity_id,
            action="edited",
            previous_value=previous_value,
            new_value=new_value,
            actor="HUMAN",
            actor_id=actor_id,
            notes=f"Changed fields: {', '.join(changed_fields) if changed_fields else 'value'}"
        )
        
        return verification, audit_event
    
    @staticmethod
    def verify(
        verification: Verification,
        verified_by: str,
        notes: Optional[str] = None
    ) -> tuple[Verification, AuditEvent]:
        """
        Mark a record as verified by a human.
        
        Args:
            verification: Existing verification record
            verified_by: ID of the person verifying
            notes: Optional verification notes
            
        Returns:
            Tuple of (updated verification, audit event)
        """
        previous_status = verification.status
        
        verification.status = VerificationStatus.VERIFIED
        verification.verified_by = verified_by
        verification.verified_at = datetime.now(timezone.utc)
        verification.notes = notes
        
        # Create audit event
        audit_event = AuditEvent(
            entity_type=verification.entity_type,
            entity_id=verification.entity_id,
            action="verified",
            previous_value=previous_status,
            new_value=VerificationStatus.VERIFIED,
            actor="HUMAN",
            actor_id=verified_by,
            notes=notes
        )
        
        return verification, audit_event
    
    @staticmethod
    def flag(
        verification: Verification,
        flagged_by: str,
        notes: Optional[str] = None
    ) -> tuple[Verification, AuditEvent]:
        """
        Flag a record for review.
        
        Args:
            verification: Existing verification record
            flagged_by: ID of the person flagging
            notes: Optional flag notes
            
        Returns:
            Tuple of (updated verification, audit event)
        """
        previous_status = verification.status
        
        verification.status = VerificationStatus.FLAGGED
        verification.notes = notes
        
        # Create audit event
        audit_event = AuditEvent(
            entity_type=verification.entity_type,
            entity_id=verification.entity_id,
            action="flagged",
            previous_value=previous_status,
            new_value=VerificationStatus.FLAGGED,
            actor="HUMAN",
            actor_id=flagged_by,
            notes=notes
        )
        
        return verification, audit_event
    
    @staticmethod
    def get_verification_history(
        verification_records: List[Verification],
        entity_id: int
    ) -> List[Verification]:
        """
        Get verification history for an entity.
        
        Args:
            verification_records: All verification records
            entity_id: ID of the entity
            
        Returns:
            List of verification records sorted by creation time
        """
        entity_records = [v for v in verification_records if v.entity_id == entity_id]
        return sorted(entity_records, key=lambda x: x.created_at)
    
    @staticmethod
    def can_edit(verification: Verification) -> bool:
        """
        Check if a verification record can be edited.
        
        Args:
            verification: Verification record to check
            
        Returns:
            True if editable, False otherwise
        """
        # Can edit if not already verified
        return verification.status != VerificationStatus.VERIFIED
    
    @staticmethod
    def can_verify(verification: Verification) -> bool:
        """
        Check if a verification record can be verified.
        
        Args:
            verification: Verification record to check
            
        Returns:
            True if verifiable, False otherwise
        """
        # Can verify if pending or edited
        return verification.status in [VerificationStatus.PENDING, VerificationStatus.EDITED]
    
    @staticmethod
    def is_original_preserved(verification: Verification) -> bool:
        """
        Check if original AI extraction is preserved.
        
        Args:
            verification: Verification record to check
            
        Returns:
            True if original is preserved, False otherwise
        """
        return verification.original_ai_value is not None
    
    @staticmethod
    def has_corrections(verification: Verification) -> bool:
        """
        Check if the record has human corrections.
        
        Args:
            verification: Verification record to check
            
        Returns:
            True if corrections exist, False otherwise
        """
        if verification.original_ai_value is None:
            return False
        return verification.corrected_value != verification.original_ai_value
    
    @staticmethod
    def get_current_value(verification: Verification) -> Optional[str]:
        """
        Get the current value (corrected if edited, original otherwise).
        
        Args:
            verification: Verification record
            
        Returns:
            Current value
        """
        if verification.corrected_value is not None:
            return verification.corrected_value
        return verification.original_ai_value
    
    @staticmethod
    def reset_to_original(
        verification: Verification,
        reset_by: str
    ) -> tuple[Verification, AuditEvent]:
        """
        Reset a corrected value back to the original AI extraction.
        
        Args:
            verification: Existing verification record
            reset_by: ID of the person resetting
            
        Returns:
            Tuple of (updated verification, audit event)
        """
        previous_value = verification.corrected_value
        
        verification.corrected_value = verification.original_ai_value
        verification.status = VerificationStatus.PENDING
        verification.updated_at = datetime.now(timezone.utc)
        
        # Create audit event
        audit_event = AuditEvent(
            entity_type=verification.entity_type,
            entity_id=verification.entity_id,
            action="edited",
            previous_value=previous_value,
            new_value=verification.original_ai_value,
            actor="HUMAN",
            actor_id=reset_by,
            notes="Reset to original AI extraction"
        )
        
        return verification, audit_event
