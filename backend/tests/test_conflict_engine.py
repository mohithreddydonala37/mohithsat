import pytest
from datetime import datetime
from app.services.conflict_engine import ConflictEngine
from app.models import LabResult, Medication, Allergy, Condition


class TestConflictEngine:
    """Test deterministic conflict detection."""
    
    def test_no_conflicts_empty_list(self):
        """Test with empty lists - no conflicts."""
        conflicts = ConflictEngine.detect_all_conflicts([], [], [], [])
        assert len(conflicts) == 0
    
    def test_medication_conflict_different_dosages(self):
        """Test detection of medication dosage conflicts."""
        medications = [
            Medication(id=1, name="Lisinopril", dosage="10mg"),
            Medication(id=2, name="Lisinopril", dosage="20mg")
        ]
        
        conflicts = ConflictEngine.detect_medication_conflict(medications)
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "medication_conflict"
        assert conflicts[0].entity_id_1 == 1
        assert conflicts[0].entity_id_2 == 2
        assert "conflicting dosages" in conflicts[0].description.lower()
    
    def test_medication_no_conflict_same_dosage(self):
        """Test that same dosage does not create conflict."""
        medications = [
            Medication(id=1, name="Lisinopril", dosage="10mg"),
            Medication(id=2, name="Lisinopril", dosage="10mg")
        ]
        
        conflicts = ConflictEngine.detect_medication_conflict(medications)
        assert len(conflicts) == 0
    
    def test_medication_no_conflict_different_names(self):
        """Test that different medications don't conflict."""
        medications = [
            Medication(id=1, name="Lisinopril", dosage="10mg"),
            Medication(id=2, name="Metformin", dosage="500mg")
        ]
        
        conflicts = ConflictEngine.detect_medication_conflict(medications)
        assert len(conflicts) == 0
    
    def test_allergy_conflict_different_severity(self):
        """Test detection of allergy severity conflicts."""
        allergies = [
            Allergy(id=1, allergen="Penicillin", severity="Mild"),
            Allergy(id=2, allergen="Penicillin", severity="Severe")
        ]
        
        conflicts = ConflictEngine.detect_allergy_conflict(allergies)
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "allergy_conflict"
        assert "conflicting severity" in conflicts[0].description.lower()
    
    def test_allergy_no_conflict_same_severity(self):
        """Test that same severity does not create conflict."""
        allergies = [
            Allergy(id=1, allergen="Penicillin", severity="Severe"),
            Allergy(id=2, allergen="Penicillin", severity="Severe")
        ]
        
        conflicts = ConflictEngine.detect_allergy_conflict(allergies)
        assert len(conflicts) == 0
    
    def test_condition_conflict_different_status(self):
        """Test detection of condition status conflicts."""
        conditions = [
            Condition(id=1, name="Hypertension", status="Active"),
            Condition(id=2, name="Hypertension", status="Resolved")
        ]
        
        conflicts = ConflictEngine.detect_condition_conflict(conditions)
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "condition_conflict"
        assert "conflicting status" in conflicts[0].description.lower()
    
    def test_duplicate_lab_result_different_values(self):
        """Test detection of duplicate lab results with different values."""
        lab_results = [
            LabResult(
                id=1,
                report_id=1,
                test_name="Hemoglobin",
                value="13.5",
                report_date=datetime(2024, 1, 15)
            ),
            LabResult(
                id=2,
                report_id=1,
                test_name="Hemoglobin",
                value="14.0",
                report_date=datetime(2024, 1, 15)
            )
        ]
        
        conflicts = ConflictEngine.detect_duplicate_lab_results(lab_results)
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "duplicate_lab_result"
        assert "conflicting values" in conflicts[0].description.lower()
    
    def test_duplicate_lab_result_same_value(self):
        """Test that same values don't create conflict."""
        lab_results = [
            LabResult(
                id=1,
                report_id=1,
                test_name="Hemoglobin",
                value="13.5",
                report_date=datetime(2024, 1, 15)
            ),
            LabResult(
                id=2,
                report_id=1,
                test_name="Hemoglobin",
                value="13.5",
                report_date=datetime(2024, 1, 15)
            )
        ]
        
        conflicts = ConflictEngine.detect_duplicate_lab_results(lab_results)
        assert len(conflicts) == 0
    
    def test_duplicate_lab_result_different_dates(self):
        """Test that different dates don't create conflict."""
        lab_results = [
            LabResult(
                id=1,
                report_id=1,
                test_name="Hemoglobin",
                value="13.5",
                report_date=datetime(2024, 1, 15)
            ),
            LabResult(
                id=2,
                report_id=1,
                test_name="Hemoglobin",
                value="14.0",
                report_date=datetime(2024, 2, 15)
            )
        ]
        
        conflicts = ConflictEngine.detect_duplicate_lab_results(lab_results)
        assert len(conflicts) == 0
    
    def test_conflicting_dates_medication(self):
        """Test detection of conflicting medication dates."""
        medications = [
            Medication(
                id=1,
                name="Lisinopril",
                start_date=datetime(2024, 1, 1)
            ),
            Medication(
                id=2,
                name="Lisinopril",
                start_date=datetime(2024, 2, 1)
            )
        ]
        
        conflicts = ConflictEngine.detect_conflicting_dates("medication", medications, "start_date")
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "conflicting_dates"
    
    def test_conflicting_dates_condition(self):
        """Test detection of conflicting condition dates."""
        conditions = [
            Condition(
                id=1,
                name="Diabetes",
                diagnosis_date=datetime(2023, 1, 1)
            ),
            Condition(
                id=2,
                name="Diabetes",
                diagnosis_date=datetime(2023, 6, 1)
            )
        ]
        
        conflicts = ConflictEngine.detect_conflicting_dates("condition", conditions, "diagnosis_date")
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "conflicting_dates"
    
    def test_multiple_conflicts_same_type(self):
        """Test detection of multiple conflicts of same type."""
        medications = [
            Medication(id=1, name="Lisinopril", dosage="10mg"),
            Medication(id=2, name="Lisinopril", dosage="20mg"),
            Medication(id=3, name="Metformin", dosage="500mg"),
            Medication(id=4, name="Metformin", dosage="1000mg")
        ]
        
        conflicts = ConflictEngine.detect_medication_conflict(medications)
        assert len(conflicts) == 2
    
    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        medications = [
            Medication(id=1, name="lisinopril", dosage="10mg"),
            Medication(id=2, name="LISINOPRIL", dosage="20mg")
        ]
        
        conflicts = ConflictEngine.detect_medication_conflict(medications)
        assert len(conflicts) == 1
    
    def test_all_conflicts_combined(self):
        """Test detection of all conflict types combined."""
        lab_results = [
            LabResult(
                id=1,
                report_id=1,
                test_name="Hemoglobin",
                value="13.5",
                report_date=datetime(2024, 1, 15)
            ),
            LabResult(
                id=2,
                report_id=1,
                test_name="Hemoglobin",
                value="14.0",
                report_date=datetime(2024, 1, 15)
            )
        ]
        
        medications = [
            Medication(id=3, name="Lisinopril", dosage="10mg"),
            Medication(id=4, name="Lisinopril", dosage="20mg")
        ]
        
        allergies = [
            Allergy(id=5, allergen="Penicillin", severity="Mild"),
            Allergy(id=6, allergen="Penicillin", severity="Severe")
        ]
        
        conditions = [
            Condition(id=7, name="Hypertension", status="Active"),
            Condition(id=8, name="Hypertension", status="Resolved")
        ]
        
        conflicts = ConflictEngine.detect_all_conflicts(lab_results, medications, allergies, conditions)
        assert len(conflicts) == 4  # One of each type
    
    def test_no_auto_resolution(self):
        """Test that conflicts are flagged but not resolved."""
        medications = [
            Medication(id=1, name="Lisinopril", dosage="10mg"),
            Medication(id=2, name="Lisinopril", dosage="20mg")
        ]
        
        conflicts = ConflictEngine.detect_medication_conflict(medications)
        assert len(conflicts) == 1
        assert conflicts[0].resolved is False
        # Conflict does not select which value is correct
        assert conflicts[0].entity_id_1 == 1
        assert conflicts[0].entity_id_2 == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
