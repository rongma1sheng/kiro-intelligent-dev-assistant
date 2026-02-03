"""Property-Based Tests for Engineering Law Validation

白皮书依据: 第九章 9.0 工程铁律 (The Constitution)

Property 1: Engineering Law Validation Completeness
**Validates: Requirements 1.1, 1.2**

For any code change, validating against all 31 engineering laws should check
every law exactly once and return violations for all violated laws.

This property ensures the validation system is comprehensive and doesn't skip
any laws or double-check laws.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from src.compliance.engineering_law_validator import (
    EngineeringLawValidator,
    ValidationResult,
    LawViolation
)


class TestEngineeringLawValidationProperties:
    """Property-based tests for engineering law validation
    
    Feature: chapters-9-19-completion
    Property 1: Engineering Law Validation Completeness
    Validates: Requirements 1.1, 1.2
    """
    
    @pytest.fixture
    def validator(self):
        """Create validator instance"""
        return EngineeringLawValidator()
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        code_diff=st.text(min_size=1, max_size=1000),
        num_files=st.integers(min_value=1, max_value=10)
    )
    def test_property_all_laws_checked_exactly_once(
        self,
        validator,
        code_diff,
        num_files
    ):
        """Property: All 31 laws are checked exactly once
        
        Feature: chapters-9-19-completion
        Property 1: Engineering Law Validation Completeness
        **Validates: Requirements 1.1, 1.2**
        
        For any code change, the validator should check all 31 laws
        exactly once, regardless of the code content.
        """
        # Generate file paths
        affected_files = [f"src/test_file_{i}.py" for i in range(num_files)]
        
        # Validate code change
        result = validator.validate_code_change(code_diff, affected_files)
        
        # Property: Exactly 31 laws should be checked
        assert result.laws_checked == 31, \
            f"Expected 31 laws checked, got {result.laws_checked}"
        
        # Property: Result should be a ValidationResult
        assert isinstance(result, ValidationResult)
        
        # Property: Violations should be a list
        assert isinstance(result.violations, list)
        
        # Property: All violations should have valid law IDs (1-31)
        for violation in result.violations:
            assert isinstance(violation, LawViolation)
            assert 1 <= violation.law_id <= 31, \
                f"Invalid law ID: {violation.law_id}"
        
        # Property: No duplicate law IDs in violations
        violation_ids = [v.law_id for v in result.violations]
        assert len(violation_ids) == len(set(violation_ids)), \
            f"Duplicate law IDs found in violations: {violation_ids}"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        num_files=st.integers(min_value=1, max_value=5)
    )
    def test_property_violations_correctly_identified(
        self,
        validator,
        num_files
    ):
        """Property: Violations are correctly identified
        
        Feature: chapters-9-19-completion
        Property 1: Engineering Law Validation Completeness
        **Validates: Requirements 1.1, 1.2**
        
        When code violates a law, the violation should be detected and reported.
        """
        # Generate file paths
        affected_files = [f"src/test_file_{i}.py" for i in range(num_files)]
        
        # Test case 1: Code with C: drive write (violates Dual-Drive Law)
        code_with_c_write = "with open('C:\\\\data\\\\file.txt', 'w') as f: f.write('data')"
        result1 = validator.validate_code_change(code_with_c_write, affected_files)
        
        # Should have at least one violation (Dual-Drive Law)
        dual_drive_violations = [v for v in result1.violations if v.law_id == 2]
        assert len(dual_drive_violations) > 0, \
            "Dual-Drive Law violation not detected for C: drive write"
        
        # Test case 2: Code with API key (violates Zero Trust Law)
        code_with_api_key = "API_KEY = 'sk-1234567890abcdef'"
        result2 = validator.validate_code_change(code_with_api_key, affected_files)
        
        # Should have at least one violation (Zero Trust Law)
        zero_trust_violations = [v for v in result2.violations if v.law_id == 12]
        assert len(zero_trust_violations) > 0, \
            "Zero Trust Law violation not detected for API key"
        
        # Property: All results should check 31 laws
        assert result1.laws_checked == 31
        assert result2.laws_checked == 31

    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        code_diff=st.text(min_size=10, max_size=500),
        num_files=st.integers(min_value=1, max_value=3)
    )
    def test_property_validation_result_consistency(
        self,
        validator,
        code_diff,
        num_files
    ):
        """Property: Validation result is consistent
        
        Feature: chapters-9-19-completion
        Property 1: Engineering Law Validation Completeness
        **Validates: Requirements 1.1, 1.2**
        
        The validation result should be consistent:
        - is_valid is False if and only if there are violations
        - recommendations are provided for violations
        """
        affected_files = [f"src/file_{i}.py" for i in range(num_files)]
        
        result = validator.validate_code_change(code_diff, affected_files)
        
        # Property: is_valid is False iff there are violations
        if result.violations:
            assert not result.is_valid, \
                "is_valid should be False when violations exist"
        else:
            assert result.is_valid, \
                "is_valid should be True when no violations exist"
        
        # Property: Number of violations <= 31 (can't violate more laws than exist)
        assert len(result.violations) <= 31, \
            f"Cannot have more than 31 violations, got {len(result.violations)}"
        
        # Property: Recommendations should be provided
        assert isinstance(result.recommendations, list)
        
        # Property: Timestamp should be set
        assert result.timestamp is not None
    
    def test_property_empty_input_handling(self, validator):
        """Property: Empty inputs are handled correctly
        
        Feature: chapters-9-19-completion
        Property 1: Engineering Law Validation Completeness
        **Validates: Requirements 1.1, 1.2**
        
        Empty code_diff or affected_files should raise ValueError.
        """
        # Empty code_diff should raise ValueError
        with pytest.raises(ValueError, match="code_diff cannot be empty"):
            validator.validate_code_change("", ["file.py"])
        
        # Empty affected_files should raise ValueError
        with pytest.raises(ValueError, match="affected_files cannot be empty"):
            validator.validate_code_change("some code", [])
    
    def test_property_all_laws_have_validators(self, validator):
        """Property: All 31 laws have validator functions
        
        Feature: chapters-9-19-completion
        Property 1: Engineering Law Validation Completeness
        **Validates: Requirements 1.1, 1.2**
        
        Each of the 31 laws should have a validator function assigned.
        """
        all_laws = validator.get_all_laws()
        
        # Property: Exactly 31 laws
        assert len(all_laws) == 31, \
            f"Expected 31 laws, got {len(all_laws)}"
        
        # Property: All law IDs from 1 to 31
        law_ids = sorted([law.law_id for law in all_laws])
        assert law_ids == list(range(1, 32)), \
            f"Law IDs should be 1-31, got {law_ids}"
        
        # Property: All laws have validators
        for law in all_laws:
            assert law.validator is not None, \
                f"Law {law.law_id} ({law.name}) has no validator"
            assert callable(law.validator), \
                f"Law {law.law_id} ({law.name}) validator is not callable"
        
        # Property: All laws have names and descriptions
        for law in all_laws:
            assert law.name, \
                f"Law {law.law_id} has no name"
            assert law.description, \
                f"Law {law.law_id} has no description"
            assert law.severity, \
                f"Law {law.law_id} has no severity"
    
    def test_property_get_law_by_id(self, validator):
        """Property: get_law_by_id returns correct law
        
        Feature: chapters-9-19-completion
        Property 1: Engineering Law Validation Completeness
        **Validates: Requirements 1.1, 1.2**
        
        get_law_by_id should return the law with the specified ID.
        """
        # Property: Valid IDs return laws
        for law_id in range(1, 32):
            law = validator.get_law_by_id(law_id)
            assert law is not None, \
                f"Law {law_id} not found"
            assert law.law_id == law_id, \
                f"Expected law ID {law_id}, got {law.law_id}"
        
        # Property: Invalid IDs raise ValueError
        with pytest.raises(ValueError, match="law_id must be between 1 and 31"):
            validator.get_law_by_id(0)
        
        with pytest.raises(ValueError, match="law_id must be between 1 and 31"):
            validator.get_law_by_id(32)
        
        with pytest.raises(ValueError, match="law_id must be between 1 and 31"):
            validator.get_law_by_id(-1)
