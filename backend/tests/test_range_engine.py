import pytest
from app.services.range_engine import RangeEngine
from app.models.enums import RangeStatus


class TestRangeEngine:
    """Test deterministic range classification."""
    
    def test_within_source_range(self):
        """Test value within reference range."""
        result = RangeEngine.classify_range(
            value="13.5",
            reference_low=12.0,
            reference_high=16.0
        )
        assert result == RangeStatus.WITHIN_SOURCE_RANGE
    
    def test_below_source_range(self):
        """Test value below reference range."""
        result = RangeEngine.classify_range(
            value="11.0",
            reference_low=12.0,
            reference_high=16.0
        )
        assert result == RangeStatus.BELOW_SOURCE_RANGE
    
    def test_above_source_range(self):
        """Test value above reference range."""
        result = RangeEngine.classify_range(
            value="17.0",
            reference_low=12.0,
            reference_high=16.0
        )
        assert result == RangeStatus.ABOVE_SOURCE_RANGE
    
    def test_missing_low_range(self):
        """Test with missing low reference range."""
        result = RangeEngine.classify_range(
            value="13.5",
            reference_low=None,
            reference_high=16.0
        )
        assert result == RangeStatus.NOT_DETERMINED
    
    def test_missing_high_range(self):
        """Test with missing high reference range."""
        result = RangeEngine.classify_range(
            value="13.5",
            reference_low=12.0,
            reference_high=None
        )
        assert result == RangeStatus.NOT_DETERMINED
    
    def test_missing_both_ranges(self):
        """Test with both reference ranges missing."""
        result = RangeEngine.classify_range(
            value="13.5",
            reference_low=None,
            reference_high=None
        )
        assert result == RangeStatus.NOT_DETERMINED
    
    def test_missing_value(self):
        """Test with missing value."""
        result = RangeEngine.classify_range(
            value=None,
            reference_low=12.0,
            reference_high=16.0
        )
        assert result == RangeStatus.NOT_DETERMINED
    
    def test_invalid_value_string(self):
        """Test with non-numeric value string."""
        result = RangeEngine.classify_range(
            value="high",
            reference_low=12.0,
            reference_high=16.0
        )
        assert result == RangeStatus.NOT_DETERMINED
    
    def test_boundary_low(self):
        """Test value exactly at low boundary."""
        result = RangeEngine.classify_range(
            value="12.0",
            reference_low=12.0,
            reference_high=16.0
        )
        assert result == RangeStatus.WITHIN_SOURCE_RANGE
    
    def test_boundary_high(self):
        """Test value exactly at high boundary."""
        result = RangeEngine.classify_range(
            value="16.0",
            reference_low=12.0,
            reference_high=16.0
        )
        assert result == RangeStatus.WITHIN_SOURCE_RANGE
    
    def test_negative_value(self):
        """Test with negative value."""
        result = RangeEngine.classify_range(
            value="-5.0",
            reference_low=0.0,
            reference_high=10.0
        )
        assert result == RangeStatus.BELOW_SOURCE_RANGE
    
    def test_zero_value(self):
        """Test with zero value."""
        result = RangeEngine.classify_range(
            value="0.0",
            reference_low=0.0,
            reference_high=10.0
        )
        assert result == RangeStatus.WITHIN_SOURCE_RANGE
    
    def test_very_small_range(self):
        """Test with very small reference range."""
        result = RangeEngine.classify_range(
            value="0.51",
            reference_low=0.5,
            reference_high=0.52
        )
        assert result == RangeStatus.WITHIN_SOURCE_RANGE
    
    def test_classify_range_with_unit(self):
        """Test range classification with unit parameter."""
        result = RangeEngine.classify_range_with_unit(
            value="13.5",
            unit="g/dL",
            reference_low=12.0,
            reference_high=16.0
        )
        assert result == RangeStatus.WITHIN_SOURCE_RANGE
    
    def test_classify_range_with_unit_missing(self):
        """Test range classification with missing unit."""
        result = RangeEngine.classify_range_with_unit(
            value="13.5",
            unit=None,
            reference_low=12.0,
            reference_high=16.0
        )
        assert result == RangeStatus.WITHIN_SOURCE_RANGE
    
    def test_deterministic_behavior(self):
        """Test that classification is deterministic."""
        # Same inputs should always produce same output
        result1 = RangeEngine.classify_range("13.5", 12.0, 16.0)
        result2 = RangeEngine.classify_range("13.5", 12.0, 16.0)
        result3 = RangeEngine.classify_range("13.5", 12.0, 16.0)
        
        assert result1 == result2 == result3
        assert result1 == RangeStatus.WITHIN_SOURCE_RANGE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
