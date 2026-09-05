from typing import Optional
from app.models.enums import RangeStatus


class RangeEngine:
    """
    Deterministic reference range classification engine.
    
    This engine performs only mathematical comparison of values
    against source-provided reference ranges. It does NOT use
    external medical knowledge or infer missing information.
    """
    
    @staticmethod
    def classify_range(
        value: Optional[str],
        reference_low: Optional[float],
        reference_high: Optional[float]
    ) -> RangeStatus:
        """
        Classify a value against source reference ranges.
        
        Args:
            value: The lab result value as a string
            reference_low: Lower bound of reference range from source
            reference_high: Upper bound of reference range from source
            
        Returns:
            RangeStatus: Classification based on deterministic rules
            
        Rules:
            - Missing source range → NOT_DETERMINED
            - value < low → BELOW_SOURCE_RANGE
            - value > high → ABOVE_SOURCE_RANGE
            - otherwise → WITHIN_SOURCE_RANGE
        """
        # If reference range is missing, cannot determine
        if reference_low is None or reference_high is None:
            return RangeStatus.NOT_DETERMINED
        
        # If value is missing, cannot determine
        if value is None:
            return RangeStatus.NOT_DETERMINED
        
        # Try to parse value as float
        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            # If value cannot be parsed as number, cannot determine
            return RangeStatus.NOT_DETERMINED
        
        # Apply deterministic classification rules
        if numeric_value < reference_low:
            return RangeStatus.BELOW_SOURCE_RANGE
        elif numeric_value > reference_high:
            return RangeStatus.ABOVE_SOURCE_RANGE
        else:
            return RangeStatus.WITHIN_SOURCE_RANGE
    
    @staticmethod
    def classify_range_with_unit(
        value: Optional[str],
        unit: Optional[str],
        reference_low: Optional[float],
        reference_high: Optional[float]
    ) -> RangeStatus:
        """
        Classify range with unit awareness.
        
        Note: This implementation does not perform unit conversion.
        Unit mismatches should be flagged by validation layer.
        
        Args:
            value: The lab result value as a string
            unit: The unit of measurement (for awareness, not conversion)
            reference_low: Lower bound of reference range from source
            reference_high: Upper bound of reference range from source
            
        Returns:
            RangeStatus: Classification based on deterministic rules
        """
        # Unit is recorded but not used for classification
        # Unit validation should happen separately
        return RangeEngine.classify_range(value, reference_low, reference_high)
