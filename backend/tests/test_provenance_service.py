import pytest
from datetime import datetime, timezone
from app.services.provenance_service import ProvenanceService
from app.models import Provenance, Origin


class TestProvenanceService:
    """Test provenance tracking service."""
    
    def test_create_provenance(self):
        """Test basic provenance creation."""
        provenance = ProvenanceService.create_provenance(
            entity_type="lab_result",
            entity_id=1,
            source_document="lab_report.pdf",
            source_page=1,
            source_text="Hemoglobin: 13.5 g/dL"
        )
        
        assert provenance.entity_type == "lab_result"
        assert provenance.entity_id == 1
        assert provenance.source_document == "lab_report.pdf"
        assert provenance.source_page == 1
        assert provenance.source_text == "Hemoglobin: 13.5 g/dL"
        assert provenance.origin == Origin.AI_EXTRACTED
        assert provenance.verification_state == "PENDING"
    
    def test_create_provenance_with_ai_origin(self):
        """Test provenance creation with AI extraction origin."""
        provenance = ProvenanceService.create_provenance(
            entity_type="lab_result",
            entity_id=1,
            source_document="lab_report.pdf",
            origin=Origin.AI_EXTRACTED,
            ai_provider="groq",
            ai_model="llama3-70b-8192"
        )
        
        assert provenance.origin == Origin.AI_EXTRACTED
        assert provenance.ai_provider == "groq"
        assert provenance.ai_model == "llama3-70b-8192"
    
    def test_create_provenance_user_origin(self):
        """Test provenance creation with user input origin."""
        provenance = ProvenanceService.create_provenance(
            entity_type="patient",
            entity_id=1,
            origin=Origin.USER_PROVIDED
        )
        
        assert provenance.origin == Origin.USER_PROVIDED
        assert provenance.ai_provider is None
        assert provenance.ai_model is None
    
    def test_create_provenance_synthetic_origin(self):
        """Test provenance creation with synthetic data origin."""
        provenance = ProvenanceService.create_provenance(
            entity_type="lab_result",
            entity_id=1,
            origin=Origin.SYNTHETIC_SOURCE,
            source_document="synthetic_data.pdf"
        )
        
        assert provenance.origin == Origin.SYNTHETIC_SOURCE
    
    def test_update_verification_state(self):
        """Test updating verification state."""
        provenance = ProvenanceService.create_provenance(
            entity_type="lab_result",
            entity_id=1
        )
        
        original_timestamp = provenance.timestamp
        updated = ProvenanceService.update_verification_state(provenance, "VERIFIED")
        
        assert updated.verification_state == "VERIFIED"
        assert updated.timestamp >= original_timestamp
    
    def test_record_ai_extraction(self):
        """Test recording AI extraction provenance."""
        provenance = ProvenanceService.record_ai_extraction(
            entity_type="lab_result",
            entity_id=1,
            source_document="lab_report.pdf",
            source_page=1,
            source_text="Hemoglobin: 13.5 g/dL",
            provider="groq",
            model="llama3-70b-8192"
        )
        
        assert provenance.origin == Origin.AI_EXTRACTED
        assert provenance.ai_provider == "groq"
        assert provenance.ai_model == "llama3-70b-8192"
        assert provenance.verification_state == "PENDING"
        assert provenance.source_document == "lab_report.pdf"
    
    def test_record_user_input(self):
        """Test recording user input provenance."""
        provenance = ProvenanceService.record_user_input(
            entity_type="patient",
            entity_id=1
        )
        
        assert provenance.origin == Origin.USER_PROVIDED
        assert provenance.verification_state == "PENDING"
        assert provenance.ai_provider is None
        assert provenance.ai_model is None
    
    def test_record_synthetic_data(self):
        """Test recording synthetic data provenance."""
        provenance = ProvenanceService.record_synthetic_data(
            entity_type="lab_result",
            entity_id=1,
            source_document="test_data.pdf"
        )
        
        assert provenance.origin == Origin.SYNTHETIC_SOURCE
        assert provenance.source_document == "test_data.pdf"
    
    def test_record_human_verification(self):
        """Test recording human verification."""
        provenance = ProvenanceService.create_provenance(
            entity_type="lab_result",
            entity_id=1,
            origin=Origin.AI_EXTRACTED
        )
        
        verified = ProvenanceService.record_human_verification(provenance, "dr_smith")
        
        assert verified.origin == Origin.HUMAN_VERIFIED
        assert verified.verification_state == "VERIFIED"
    
    def test_get_provenance_chain(self):
        """Test getting provenance chain for an entity."""
        provenance_records = [
            Provenance(id=1, entity_type="lab_result", entity_id=1, origin=Origin.AI_EXTRACTED),
            Provenance(id=2, entity_type="lab_result", entity_id=1, origin=Origin.HUMAN_VERIFIED),
            Provenance(id=3, entity_type="lab_result", entity_id=2, origin=Origin.AI_EXTRACTED),
        ]
        
        chain = ProvenanceService.get_provenance_chain(provenance_records, entity_id=1)
        
        assert len(chain) == 2
        assert all(p.entity_id == 1 for p in chain)
        # Should be sorted by timestamp
        assert chain[0].id == 1
        assert chain[1].id == 2
    
    def test_get_provenance_chain_empty(self):
        """Test getting provenance chain for non-existent entity."""
        provenance_records = [
            Provenance(id=1, entity_type="lab_result", entity_id=1, origin=Origin.AI_EXTRACTED),
        ]
        
        chain = ProvenanceService.get_provenance_chain(provenance_records, entity_id=999)
        
        assert len(chain) == 0
    
    def test_validate_provenance_completeness_success(self):
        """Test validation of complete provenance."""
        provenance = ProvenanceService.create_provenance(
            entity_type="lab_result",
            entity_id=1,
            source_document="lab_report.pdf",
            ai_provider="groq",
            ai_model="llama3-70b-8192"
        )
        
        assert ProvenanceService.validate_provenance_completeness(provenance) is True
    
    def test_validate_provenance_completeness_missing_entity_type(self):
        """Test validation fails with missing entity type."""
        # Create with None and then set to empty string for testing
        provenance = ProvenanceService.create_provenance(
            entity_type="lab_result",
            entity_id=1
        )
        provenance.entity_type = ""
        
        assert ProvenanceService.validate_provenance_completeness(provenance) is False
    
    def test_validate_provenance_completeness_missing_entity_id(self):
        """Test validation fails with missing entity ID."""
        # Create with valid ID and then set to None for testing
        provenance = ProvenanceService.create_provenance(
            entity_type="lab_result",
            entity_id=1
        )
        provenance.entity_id = None
        
        assert ProvenanceService.validate_provenance_completeness(provenance) is False
    
    def test_validate_provenance_completeness_missing_source(self):
        """Test validation fails when source required but missing."""
        provenance = ProvenanceService.create_provenance(
            entity_type="lab_result",
            entity_id=1,
            source_document=None
        )
        
        assert ProvenanceService.validate_provenance_completeness(provenance, require_source=True) is False
    
    def test_validate_provenance_completeness_source_not_required(self):
        """Test validation passes when source not required."""
        provenance = ProvenanceService.create_provenance(
            entity_type="patient",
            entity_id=1,
            source_document=None,
            origin=Origin.USER_PROVIDED
        )
        
        assert ProvenanceService.validate_provenance_completeness(provenance, require_source=False) is True
    
    def test_validate_provenance_completeness_ai_missing_provider(self):
        """Test validation fails for AI extraction without provider."""
        provenance = ProvenanceService.create_provenance(
            entity_type="lab_result",
            entity_id=1,
            origin=Origin.AI_EXTRACTED,
            ai_provider=None,
            ai_model="llama3-70b-8192"
        )
        
        assert ProvenanceService.validate_provenance_completeness(provenance) is False
    
    def test_validate_provenance_completeness_ai_missing_model(self):
        """Test validation fails for AI extraction without model."""
        provenance = ProvenanceService.create_provenance(
            entity_type="lab_result",
            entity_id=1,
            origin=Origin.AI_EXTRACTED,
            ai_provider="groq",
            ai_model=None
        )
        
        assert ProvenanceService.validate_provenance_completeness(provenance) is False
    
    def test_provenance_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated."""
        before = datetime.now(timezone.utc)
        provenance = ProvenanceService.create_provenance(
            entity_type="lab_result",
            entity_id=1
        )
        after = datetime.now(timezone.utc)
        
        assert before <= provenance.timestamp <= after
    
    def test_multiple_provenance_records_same_entity(self):
        """Test handling multiple provenance records for same entity."""
        provenance_records = []
        
        # Create initial AI extraction
        p1 = ProvenanceService.record_ai_extraction(
            entity_type="lab_result",
            entity_id=1,
            source_document="report.pdf",
            source_page=1,
            source_text="Value: 13.5",
            provider="groq",
            model="llama3-70b-8192"
        )
        provenance_records.append(p1)
        
        # Record human verification (creates new record)
        p2 = ProvenanceService.record_human_verification(p1, "dr_smith")
        provenance_records.append(p2)
        
        chain = ProvenanceService.get_provenance_chain(provenance_records, entity_id=1)
        
        assert len(chain) == 2
        # Both records should be for the same entity
        assert all(p.entity_id == 1 for p in chain)
        # First should be AI extraction, second should be human verification
        assert chain[0].origin == Origin.AI_EXTRACTED
        assert chain[1].origin == Origin.HUMAN_VERIFIED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
