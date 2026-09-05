from typing import List, Optional, Tuple
from datetime import datetime
from app.models import (
    LabResult,
    Medication,
    Allergy,
    Condition,
    Conflict,
    RangeStatus
)


class ConflictEngine:
    """
    Deterministic conflict detection engine.
    
    This engine detects conflicts between records but does NOT
    determine which record is medically correct. It only flags
    inconsistencies for human review.
    """
    
    @staticmethod
    def detect_medication_conflict(medications: List[Medication]) -> List[Conflict]:
        """
        Detect medication conflicts.
        
        Conflicts detected:
        - Same medication name with different dosages
        - Same medication name with different frequencies
        - Same medication name with different routes
        """
        conflicts = []
        medication_map = {}
        
        for med in medications:
            key = med.name.lower()
            if key not in medication_map:
                medication_map[key] = []
            medication_map[key].append(med)
        
        for name, med_list in medication_map.items():
            if len(med_list) > 1:
                # Check for dosage conflicts
                dosages = {m.dosage for m in med_list if m.dosage}
                if len(dosages) > 1:
                    for i in range(len(med_list)):
                        for j in range(i + 1, len(med_list)):
                            if med_list[i].dosage != med_list[j].dosage:
                                conflict = Conflict(
                                    conflict_type="medication_conflict",
                                    entity_type="medication",
                                    entity_id_1=med_list[i].id or 0,
                                    entity_id_2=med_list[j].id or 0,
                                    description=f"Medication '{name}' has conflicting dosages: {med_list[i].dosage} vs {med_list[j].dosage}",
                                    severity="high"
                                )
                                conflicts.append(conflict)
        
        return conflicts
    
    @staticmethod
    def detect_allergy_conflict(allergies: List[Allergy]) -> List[Conflict]:
        """
        Detect allergy conflicts.
        
        Conflicts detected:
        - Same allergen with different severity levels
        - Same allergen with different reactions
        """
        conflicts = []
        allergy_map = {}
        
        for allergy in allergies:
            key = allergy.allergen.lower()
            if key not in allergy_map:
                allergy_map[key] = []
            allergy_map[key].append(allergy)
        
        for allergen, allergy_list in allergy_map.items():
            if len(allergy_list) > 1:
                # Check for severity conflicts
                severities = {a.severity for a in allergy_list if a.severity}
                if len(severities) > 1:
                    for i in range(len(allergy_list)):
                        for j in range(i + 1, len(allergy_list)):
                            if allergy_list[i].severity != allergy_list[j].severity:
                                conflict = Conflict(
                                    conflict_type="allergy_conflict",
                                    entity_type="allergy",
                                    entity_id_1=allergy_list[i].id or 0,
                                    entity_id_2=allergy_list[j].id or 0,
                                    description=f"Allergy '{allergen}' has conflicting severity: {allergy_list[i].severity} vs {allergy_list[j].severity}",
                                    severity="high"
                                )
                                conflicts.append(conflict)
        
        return conflicts
    
    @staticmethod
    def detect_condition_conflict(conditions: List[Condition]) -> List[Conflict]:
        """
        Detect condition conflicts.
        
        Conflicts detected:
        - Same condition with different status
        - Same condition with conflicting diagnosis dates
        """
        conflicts = []
        condition_map = {}
        
        for condition in conditions:
            key = condition.name.lower()
            if key not in condition_map:
                condition_map[key] = []
            condition_map[key].append(condition)
        
        for name, condition_list in condition_map.items():
            if len(condition_list) > 1:
                # Check for status conflicts
                statuses = {c.status for c in condition_list if c.status}
                if len(statuses) > 1:
                    for i in range(len(condition_list)):
                        for j in range(i + 1, len(condition_list)):
                            if condition_list[i].status != condition_list[j].status:
                                conflict = Conflict(
                                    conflict_type="condition_conflict",
                                    entity_type="condition",
                                    entity_id_1=condition_list[i].id or 0,
                                    entity_id_2=condition_list[j].id or 0,
                                    description=f"Condition '{name}' has conflicting status: {condition_list[i].status} vs {condition_list[j].status}",
                                    severity="medium"
                                )
                                conflicts.append(conflict)
        
        return conflicts
    
    @staticmethod
    def detect_duplicate_lab_results(lab_results: List[LabResult]) -> List[Conflict]:
        """
        Detect duplicate laboratory results.
        
        Duplicates detected:
        - Same test name on same date with different values
        - Same test name on same date with different units
        """
        conflicts = []
        result_map = {}
        
        for result in lab_results:
            # Create key from test name and date
            date_str = result.report_date.isoformat() if result.report_date else "unknown"
            key = f"{result.test_name.lower()}_{date_str}"
            if key not in result_map:
                result_map[key] = []
            result_map[key].append(result)
        
        for key, result_list in result_map.items():
            if len(result_list) > 1:
                # Check for value conflicts
                values = {r.value for r in result_list if r.value}
                if len(values) > 1:
                    for i in range(len(result_list)):
                        for j in range(i + 1, len(result_list)):
                            if result_list[i].value != result_list[j].value:
                                conflict = Conflict(
                                    conflict_type="duplicate_lab_result",
                                    entity_type="lab_result",
                                    entity_id_1=result_list[i].id or 0,
                                    entity_id_2=result_list[j].id or 0,
                                    description=f"Duplicate lab result '{result_list[i].test_name}' with conflicting values: {result_list[i].value} vs {result_list[j].value}",
                                    severity="high"
                                )
                                conflicts.append(conflict)
        
        return conflicts
    
    @staticmethod
    def detect_conflicting_dates(
        entity_type: str,
        entities: List,
        date_field: str = "diagnosis_date"
    ) -> List[Conflict]:
        """
        Detect conflicting dates for same entity.
        
        Args:
            entity_type: Type of entity (medication, condition, etc.)
            entities: List of entities to check
            date_field: Name of the date field to check
            
        Returns:
            List of conflicts detected
        """
        conflicts = []
        
        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities):
                if i >= j:
                    continue
                
                date1 = getattr(entity1, date_field, None)
                date2 = getattr(entity2, date_field, None)
                
                if date1 and date2 and date1 != date2:
                    # Check if entities are similar (same name for medications/conditions)
                    name1 = getattr(entity1, "name", None)
                    name2 = getattr(entity2, "name", None)
                    
                    if name1 and name2 and name1.lower() == name2.lower():
                        conflict = Conflict(
                            conflict_type="conflicting_dates",
                            entity_type=entity_type,
                            entity_id_1=entity1.id or 0,
                            entity_id_2=entity2.id or 0,
                            description=f"Conflicting {date_field} for '{name1}': {date1} vs {date2}",
                            severity="medium"
                        )
                        conflicts.append(conflict)
        
        return conflicts
    
    @staticmethod
    def detect_all_conflicts(
        lab_results: List[LabResult],
        medications: List[Medication],
        allergies: List[Allergy],
        conditions: List[Condition]
    ) -> List[Conflict]:
        """
        Detect all conflicts across all entity types.
        
        Returns a combined list of all detected conflicts.
        """
        all_conflicts = []
        
        all_conflicts.extend(ConflictEngine.detect_duplicate_lab_results(lab_results))
        all_conflicts.extend(ConflictEngine.detect_medication_conflict(medications))
        all_conflicts.extend(ConflictEngine.detect_allergy_conflict(allergies))
        all_conflicts.extend(ConflictEngine.detect_condition_conflict(conditions))
        all_conflicts.extend(ConflictEngine.detect_conflicting_dates("medication", medications, "start_date"))
        all_conflicts.extend(ConflictEngine.detect_conflicting_dates("condition", conditions, "diagnosis_date"))
        
        return all_conflicts
