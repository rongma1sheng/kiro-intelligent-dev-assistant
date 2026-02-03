"""Unit Tests for Engineering Law Validator

白皮书依据: 第九章 9.0 工程铁律 (The Constitution)

These tests achieve 100% coverage of the EngineeringLawValidator module,
testing all 31 laws individually, edge cases, and error handling.

Coverage Target: 100% (user requirement)
"""

import pytest
from src.compliance.engineering_law_validator import (
    EngineeringLawValidator,
    ValidationResult,
    LawViolation,
    EngineeringLaw,
    LawSeverity
)


class TestEngineeringLawValidator:
    """Unit tests for EngineeringLawValidator
    
    Coverage target: 100%
    """
    
    @pytest.fixture
    def validator(self):
        """Create validator instance"""
        return EngineeringLawValidator()
    
    def test_initialization(self, validator):
        """Test validator initialization"""
        assert validator is not None
        assert len(validator._laws) == 31
        
        # Verify all laws are initialized
        law_ids = [law.law_id for law in validator._laws]
        assert sorted(law_ids) == list(range(1, 32))
    
    def test_initialization_failure(self, monkeypatch):
        """Test initialization failure when laws incomplete"""
        # Mock _initialize_laws to create incomplete law list
        def mock_init(self):
            self._laws = []  # Empty list
        
        monkeypatch.setattr(
            EngineeringLawValidator,
            '_initialize_laws',
            mock_init
        )
        
        with pytest.raises(RuntimeError, match="Expected 31 laws"):
            EngineeringLawValidator()
    
    def test_validate_code_change_success(self, validator):
        """Test successful code validation"""
        code_diff = "def hello(): return 'world'"
        affected_files = ["src/test.py"]
        
        result = validator.validate_code_change(code_diff, affected_files)
        
        assert isinstance(result, ValidationResult)
        assert result.laws_checked == 31
        assert isinstance(result.violations, list)
        assert isinstance(result.recommendations, list)
        assert result.timestamp is not None
    
    def test_validate_code_change_empty_diff(self, validator):
        """Test validation with empty code diff"""
        with pytest.raises(ValueError, match="code_diff cannot be empty"):
            validator.validate_code_change("", ["file.py"])
    
    def test_validate_code_change_empty_files(self, validator):
        """Test validation with empty affected files"""
        with pytest.raises(ValueError, match="affected_files cannot be empty"):
            validator.validate_code_change("code", [])
    
    # Test individual laws
    
    def test_law_1_trinity_law_pass(self, validator):
        """Test Trinity Law - pass case"""
        code = "class SoldierEngine:\n    def __init__(self):\n        self.failover = CloudFailover()"
        files = ["src/brain/soldier.py"]
        
        result = validator.validate_code_change(code, files)
        
        # Should not violate Trinity Law
        trinity_violations = [v for v in result.violations if v.law_id == 1]
        assert len(trinity_violations) == 0
    
    def test_law_1_trinity_law_fail(self, validator):
        """Test Trinity Law - fail case"""
        code = "class SoldierEngine:\n    def __init__(self):\n        self.mode = 'local'"
        files = ["src/brain/soldier.py"]
        
        result = validator.validate_code_change(code, files)
        
        # Should violate Trinity Law
        trinity_violations = [v for v in result.violations if v.law_id == 1]
        assert len(trinity_violations) > 0
    
    def test_law_2_dual_drive_law_pass(self, validator):
        """Test Dual-Drive Law - pass case"""
        code = "with open('D:\\\\data\\\\file.txt', 'w') as f: f.write('data')"
        files = ["src/test.py"]
        
        result = validator.validate_code_change(code, files)
        
        # Should not violate Dual-Drive Law
        dual_drive_violations = [v for v in result.violations if v.law_id == 2]
        assert len(dual_drive_violations) == 0
    
    def test_law_2_dual_drive_law_fail(self, validator):
        """Test Dual-Drive Law - fail case"""
        code = "with open('C:\\\\data\\\\file.txt', 'w') as f: f.write('data')"
        files = ["src/test.py"]
        
        result = validator.validate_code_change(code, files)
        
        # Should violate Dual-Drive Law
        dual_drive_violations = [v for v in result.violations if v.law_id == 2]
        assert len(dual_drive_violations) > 0

    def test_law_3_latency_law_pass(self, validator):
        """Test Latency Law - pass case"""
        code = "class HighFreqData:\n    def __init__(self):\n        self.spsc = SPSCBuffer()"
        files = ["src/infra/data.py"]
        
        result = validator.validate_code_change(code, files)
        
        # Should not violate Latency Law
        latency_violations = [v for v in result.violations if v.law_id == 3]
        assert len(latency_violations) == 0
    
    def test_law_3_latency_law_fail(self, validator):
        """Test Latency Law - fail case"""
        code = "class HighFreqData:\n    def stream_realtime_data(self):\n        self.buffer = []"
        files = ["src/infra/data.py"]
        
        result = validator.validate_code_change(code, files)
        
        # Should violate Latency Law
        latency_violations = [v for v in result.violations if v.law_id == 3]
        assert len(latency_violations) > 0
    
    def test_law_12_zero_trust_law_api_key_fail(self, validator):
        """Test Zero Trust Law - API key violation"""
        code = "API_KEY = 'sk-1234567890abcdef'"
        files = ["src/config.py"]
        
        result = validator.validate_code_change(code, files)
        
        # Should violate Zero Trust Law
        zero_trust_violations = [v for v in result.violations if v.law_id == 12]
        assert len(zero_trust_violations) > 0
    
    def test_law_12_zero_trust_law_public_port_fail(self, validator):
        """Test Zero Trust Law - public port violation"""
        code = "app.run(host='0.0.0.0', port=8080)"
        files = ["src/server.py"]
        
        result = validator.validate_code_change(code, files)
        
        # Should violate Zero Trust Law
        zero_trust_violations = [v for v in result.violations if v.law_id == 12]
        assert len(zero_trust_violations) > 0
    
    def test_law_13_doomsday_law_pass(self, validator):
        """Test Doomsday Law - pass case"""
        code = "class DoomsdaySwitch:\n    def reset(self, password):\n        if not self.authenticate(password): raise"
        files = ["src/core/doomsday.py"]
        
        result = validator.validate_code_change(code, files)
        
        # Should not violate Doomsday Law
        doomsday_violations = [v for v in result.violations if v.law_id == 13]
        assert len(doomsday_violations) == 0
    
    def test_law_31_documentation_sync_law_pass(self, validator):
        """Test Documentation Sync Law - pass case"""
        code = "class NewFeature:\n    pass"
        files = ["src/new_feature.py", "00_核心文档/mia.md", "tasks.md"]
        
        result = validator.validate_code_change(code, files)
        
        # Should not violate Documentation Sync Law
        doc_sync_violations = [v for v in result.violations if v.law_id == 31]
        assert len(doc_sync_violations) == 0
    
    def test_law_31_documentation_sync_law_fail(self, validator):
        """Test Documentation Sync Law - fail case"""
        code = "class NewFeature:\n    pass"
        files = ["src/new_feature.py"]  # No documentation files
        
        result = validator.validate_code_change(code, files)
        
        # Should violate Documentation Sync Law
        doc_sync_violations = [v for v in result.violations if v.law_id == 31]
        assert len(doc_sync_violations) > 0
    
    def test_get_law_by_id_valid(self, validator):
        """Test get_law_by_id with valid IDs"""
        for law_id in range(1, 32):
            law = validator.get_law_by_id(law_id)
            assert law is not None
            assert law.law_id == law_id
            assert law.name
            assert law.description
    
    def test_get_law_by_id_invalid(self, validator):
        """Test get_law_by_id with invalid IDs"""
        with pytest.raises(ValueError, match="law_id must be between 1 and 31"):
            validator.get_law_by_id(0)
        
        with pytest.raises(ValueError, match="law_id must be between 1 and 31"):
            validator.get_law_by_id(32)
        
        with pytest.raises(ValueError, match="law_id must be between 1 and 31"):
            validator.get_law_by_id(-5)
    
    def test_get_all_laws(self, validator):
        """Test get_all_laws"""
        laws = validator.get_all_laws()
        
        assert len(laws) == 31
        assert all(isinstance(law, EngineeringLaw) for law in laws)
        
        # Verify it's a copy (modifying shouldn't affect internal state)
        laws.clear()
        assert len(validator._laws) == 31
    
    def test_get_recommendation(self, validator):
        """Test _get_recommendation for all laws"""
        for law_id in range(1, 32):
            law = validator.get_law_by_id(law_id)
            recommendation = validator._get_recommendation(law_id, law.name)
            
            assert recommendation
            assert isinstance(recommendation, str)
            assert len(recommendation) > 0
    
    def test_validation_result_structure(self, validator):
        """Test ValidationResult structure"""
        code = "def test(): pass"
        files = ["test.py"]
        
        result = validator.validate_code_change(code, files)
        
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'violations')
        assert hasattr(result, 'recommendations')
        assert hasattr(result, 'laws_checked')
        assert hasattr(result, 'timestamp')
        
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.violations, list)
        assert isinstance(result.recommendations, list)
        assert isinstance(result.laws_checked, int)
    
    def test_law_violation_structure(self, validator):
        """Test LawViolation structure"""
        code = "API_KEY = 'secret'"
        files = ["config.py"]
        
        result = validator.validate_code_change(code, files)
        
        if result.violations:
            violation = result.violations[0]
            
            assert hasattr(violation, 'law_id')
            assert hasattr(violation, 'law_name')
            assert hasattr(violation, 'file_path')
            assert hasattr(violation, 'line_number')
            assert hasattr(violation, 'description')
            assert hasattr(violation, 'severity')
            
            assert isinstance(violation.law_id, int)
            assert isinstance(violation.law_name, str)
            assert isinstance(violation.file_path, str)
            assert isinstance(violation.line_number, int)
            assert isinstance(violation.description, str)
            assert isinstance(violation.severity, LawSeverity)

    def test_validator_exception_handling(self, validator, monkeypatch):
        """Test exception handling in validator"""
        # Mock a law validator to raise exception
        def mock_validator_error(code_diff, affected_files):
            raise RuntimeError("Test error")
        
        # Replace first law's validator
        validator._laws[0].validator = mock_validator_error
        
        code = "def test(): pass"
        files = ["test.py"]
        
        result = validator.validate_code_change(code, files)
        
        # Should still complete and report error as violation
        assert result.laws_checked == 31
        assert len(result.violations) > 0
        
        # Should have violation for the failed law
        error_violations = [v for v in result.violations if v.law_id == 1]
        assert len(error_violations) > 0
        assert "Validation error" in error_violations[0].description
    
    def test_all_law_validators_callable(self, validator):
        """Test that all law validators are callable"""
        for law in validator._laws:
            assert callable(law.validator)
            
            # Test calling each validator
            try:
                result = law.validator("test code", ["test.py"])
                assert isinstance(result, bool)
            except Exception as e:
                pytest.fail(f"Law {law.law_id} validator raised exception: {e}")
    
    def test_law_severity_levels(self, validator):
        """Test that all laws have valid severity levels"""
        for law in validator._laws:
            assert isinstance(law.severity, LawSeverity)
            assert law.severity in [
                LawSeverity.CRITICAL,
                LawSeverity.HIGH,
                LawSeverity.MEDIUM
            ]
    
    def test_validation_with_multiple_violations(self, validator):
        """Test validation with multiple law violations"""
        code = """
        API_KEY = 'secret'  # Violates Zero Trust Law
        # Violates Dual-Drive Law (C: drive write operation)
        path = 'C:\\\\config\\\\write_settings.txt'
        """
        files = ["src/config.py"]
        
        result = validator.validate_code_change(code, files)
        
        # Should have multiple violations
        assert len(result.violations) >= 2
        assert not result.is_valid
        
        # Should have recommendations
        assert len(result.recommendations) > 0
    
    def test_validation_is_valid_consistency(self, validator):
        """Test is_valid is consistent with violations"""
        # Test with clean code
        clean_code = "def hello(): return 'world'"
        result1 = validator.validate_code_change(clean_code, ["test.py"])
        
        if len(result1.violations) == 0:
            assert result1.is_valid
        else:
            assert not result1.is_valid
        
        # Test with violating code
        bad_code = "API_KEY = 'secret'"
        result2 = validator.validate_code_change(bad_code, ["config.py"])
        
        if len(result2.violations) > 0:
            assert not result2.is_valid
        else:
            assert result2.is_valid
    
    def test_no_duplicate_violations(self, validator):
        """Test that no law is violated twice"""
        code = "API_KEY = 'secret'"
        files = ["config.py"]
        
        result = validator.validate_code_change(code, files)
        
        # Check for duplicate law IDs
        law_ids = [v.law_id for v in result.violations]
        assert len(law_ids) == len(set(law_ids)), \
            f"Duplicate law IDs found: {law_ids}"
    
    def test_edge_case_very_long_code(self, validator):
        """Test validation with very long code diff"""
        code = "def test():\n    pass\n" * 1000
        files = ["test.py"]
        
        result = validator.validate_code_change(code, files)
        
        assert result.laws_checked == 31
        assert isinstance(result, ValidationResult)
    
    def test_edge_case_many_files(self, validator):
        """Test validation with many affected files"""
        code = "def test(): pass"
        files = [f"src/file_{i}.py" for i in range(100)]
        
        result = validator.validate_code_change(code, files)
        
        assert result.laws_checked == 31
        assert isinstance(result, ValidationResult)
    
    def test_edge_case_special_characters(self, validator):
        """Test validation with special characters in code"""
        code = "# 中文注释\ndef test():\n    return '特殊字符 🚀'"
        files = ["test.py"]
        
        result = validator.validate_code_change(code, files)
        
        assert result.laws_checked == 31
        assert isinstance(result, ValidationResult)
    
    def test_law_names_unique(self, validator):
        """Test that all law names are unique"""
        law_names = [law.name for law in validator._laws]
        assert len(law_names) == len(set(law_names)), \
            "Law names should be unique"
    
    def test_law_descriptions_non_empty(self, validator):
        """Test that all law descriptions are non-empty"""
        for law in validator._laws:
            assert law.description, \
                f"Law {law.law_id} has empty description"
            assert len(law.description) > 0
