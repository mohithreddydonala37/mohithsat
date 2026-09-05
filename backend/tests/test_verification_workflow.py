import pytest
from datetime import datetime
from app.services.verification_service import VerificationService
from app.models import Verification, AuditEvent, VerificationStatus, Origin


class TestVerificationWorkflow:
    """Test end-to-end verification workflow."""
    
    def test_full_verification_workflow(self):
        """Test complete workflow from AI extraction to human verification."""
        
        # Step 1: AI extracts a value
        verification = VerificationService.create_verification(
            entity_type="lab_result",
            entity_id=1,
            original_ai_value="13.5",
            origin=Origin.AI_EXTRACTED
        )
        
        assert verification.status == VerificationStatus.PENDING
        assert verification.original_ai_value == "13.5"
        assert verification.corrected_value == "13.5"
        assert VerificationService.is_original_preserved(verification)
        
        # Step 2: Human reviews and edits the value
        updated_verification, audit_event = VerificationService.edit_value(
            verification=verification,
            new_value="13.7",
            actor_id="dr_smith",
            changed_fields=["value"]
        )
        
        assert updated_verification.status == VerificationStatus.EDITED
        assert updated_verification.original_ai_value == "13.5"  # Original preserved
        assert updated_verification.corrected_value == "13.7"  # New value
        assert VerificationService.has_corrections(updated_verification)
        assert audit_event.action == "edited"
        assert audit_event.actor == "HUMAN"
        
        # Step 3: Human verifies the corrected value
        verified_verification, verify_audit = VerificationService.verify(
            verification=updated_verification,
            verified_by="dr_smith",
            notes="Corrected transcription error"
        )
        
        assert verified_verification.status == VerificationStatus.VERIFIED
        assert verified_verification.verified_by == "dr_smith"
        assert verified_verification.notes == "Corrected transcription error"
        assert verify_audit.action == "verified"
        
        # Step 4: Verify cannot edit after verification
        assert not VerificationService.can_edit(verified_verification)
    
    def test_edit_preserves_original(self):
        """Test that editing preserves the original AI extraction."""
        
        verification = VerificationService.create_verification(
            entity_type="lab_result",
            entity_id=1,
            original_ai_value="13.5"
        )
        
        # Edit multiple times
        verification, _ = VerificationService.edit_value(verification, "13.6", "user1")
        verification, _ = VerificationService.edit_value(verification, "13.7", "user2")
        verification, _ = VerificationService.edit_value(verification, "13.8", "user3")
        
        # Original should still be preserved
        assert verification.original_ai_value == "13.5"
        assert verification.corrected_value == "13.8"
        assert VerificationService.is_original_preserved(verification)
    
    def test_reset_to_original(self):
        """Test resetting to original AI extraction."""
        
        verification = VerificationService.create_verification(
            entity_type="lab_result",
            entity_id=1,
            original_ai_value="13.5"
        )
        
        # Edit the value
        verification, _ = VerificationService.edit_value(verification, "13.7", "user")
        
        # Reset to original
        reset_verification, audit_event = VerificationService.reset_to_original(
            verification=verification,
            reset_by="user"
        )
        
        assert reset_verification.corrected_value == "13.5"
        assert reset_verification.status == VerificationStatus.PENDING
        assert audit_event.notes == "Reset to original AI extraction"
    
    def test_flag_workflow(self):
        """Test flagging a record for review."""
        
        verification = VerificationService.create_verification(
            entity_type="medication",
            entity_id=1,
            original_ai_value="Lisinopril 10mg"
        )
        
        # Flag the record
        flagged_verification, audit_event = VerificationService.flag(
            verification=verification,
            flagged_by="dr_smith",
            notes="Dosage seems incorrect, needs review"
        )
        
        assert flagged_verification.status == VerificationStatus.FLAGGED
        assert flagged_verification.notes == "Dosage seems incorrect, needs review"
        assert audit_event.action == "flagged"
    
    def test_cannot_edit_verified_record(self):
        """Test that verified records cannot be edited."""
        
        verification = VerificationService.create_verification(
            entity_type="lab_result",
            entity_id=1,
            original_ai_value="13.5"
        )
        
        # Verify the record
        verification, _ = VerificationService.verify(verification, "dr_smith")
        
        # Try to edit (should fail)
        assert not VerificationService.can_edit(verification)
    
    def test_cannot_verify_flagged_record(self):
        """Test that flagged records cannot be directly verified."""
        
        verification = VerificationService.create_verification(
            entity_type="lab_result",
            entity_id=1,
            original_ai_value="13.5"
        )
        
        # Flag the record
        verification, _ = VerificationService.flag(verification, "user")
        
        # Try to verify (should fail)
        assert not VerificationService.can_verify(verification)
    
    def test_get_current_value(self):
        """Test getting current value (corrected or original)."""
        
        verification = VerificationService.create_verification(
            entity_type="lab_result",
            entity_id=1,
            original_ai_value="13.5"
        )
        
        # Before edit, should return original
        current = VerificationService.get_current_value(verification)
        assert current == "13.5"
        
        # After edit, should return corrected
        verification, _ = VerificationService.edit_value(verification, "13.7", "user")
        current = VerificationService.get_current_value(verification)
        assert current == "13.7"
    
    def test_audit_trail_creation(self):
        """Test that audit events are created for all operations."""
        
        verification = VerificationService.create_verification(
            entity_type="lab_result",
            entity_id=1,
            original_ai_value="13.5"
        )
        
        audit_events = []
        
        # Edit
        verification, audit = VerificationService.edit_value(verification, "13.7", "user1")
        audit_events.append(audit)
        
        # Verify
        verification, audit = VerificationService.verify(verification, "user2")
        audit_events.append(audit)
        
        # Flag
        verification, audit = VerificationService.flag(verification, "user3")
        audit_events.append(audit)
        
        # Check audit events
        assert len(audit_events) == 3
        assert audit_events[0].action == "edited"
        assert audit_events[1].action == "verified"
        assert audit_events[2].action == "flagged"
        
        # All should have HUMAN actor
        assert all(event.actor == "HUMAN" for event in audit_events)
    
    def test_state_machine_transitions(self):
        """Test valid state machine transitions."""
        
        verification = VerificationService.create_verification(
            entity_type="lab_result",
            entity_id=1,
            original_ai_value="13.5"
        )
        
        # PENDING -> EDITED
        assert verification.status == VerificationStatus.PENDING
        verification, _ = VerificationService.edit_value(verification, "13.7", "user")
        assert verification.status == VerificationStatus.EDITED
        
        # EDITED -> VERIFIED
        verification, _ = VerificationService.verify(verification, "user")
        assert verification.status == VerificationStatus.VERIFIED
        
        # PENDING -> FLAGGED
        verification2 = VerificationService.create_verification(
            entity_type="lab_result",
            entity_id=2,
            original_ai_value="14.0"
        )
        verification2, _ = VerificationService.flag(verification2, "user")
        assert verification2.status == VerificationStatus.FLAGGED
    
    def test_verification_history(self):
        """Test retrieving verification history."""
        
        verification1 = VerificationService.create_verification(
            entity_type="lab_result",
            entity_id=1,
            original_ai_value="13.5"
        )
        
        verification2 = VerificationService.create_verification(
            entity_type="lab_result",
            entity_id=1,
            original_ai_value="13.7"
        )
        
        verification3 = VerificationService.create_verification(
            entity_type="lab_result",
            entity_id=2,
            original_ai_value="14.0"
        )
        
        all_verifications = [verification1, verification2, verification3]
        
        # Get history for entity_id 1
        history = VerificationService.get_verification_history(all_verifications, entity_id=1)
        
        assert len(history) == 2
        assert all(v.entity_id == 1 for v in history)
    
    def test_no_corrections_when_same_value(self):
        """Test that has_corrections returns False when value unchanged."""
        
        verification = VerificationService.create_verification(
            entity_type="lab_result",
            entity_id=1,
            original_ai_value="13.5"
        )
        
        # Edit to same value
        verification, _ = VerificationService.edit_value(verification, "13.5", "user")
        
        # Should not count as correction
        assert not VerificationService.has_corrections(verification)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
