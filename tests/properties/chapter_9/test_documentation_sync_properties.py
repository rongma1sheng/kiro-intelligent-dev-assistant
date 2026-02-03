"""Property-Based Tests for Documentation Sync

白皮书依据: 第九章 9.0 工程铁律 - Law 31 (Documentation Sync Law)

Property 2: Documentation Sync Consistency
**Validates: Requirements 1.3, 1.4**

For any set of documentation files, if all files have matching hash values
in the sync registry, then the sync checker should report all documents as
synchronized.

This is a consistency property ensuring the sync checker correctly identifies
synchronized states.
"""

import pytest
import tempfile
import os
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from src.compliance.documentation_sync_checker import (
    DocumentationSyncChecker,
    SyncStatus,
    DocumentType
)


class TestDocumentationSyncProperties:
    """Property-based tests for documentation sync
    
    Feature: chapters-9-19-completion
    Property 2: Documentation Sync Consistency
    Validates: Requirements 1.3, 1.4
    """
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create directory structure
            (workspace / "00_核心文档").mkdir(parents=True)
            (workspace / ".kiro" / "specs" / "test-spec").mkdir(parents=True)
            (workspace / ".kiro" / "specs" / "test").mkdir(parents=True)
            
            yield workspace
    
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        content=st.text(min_size=10, max_size=1000)
    )
    def test_property_hash_consistency(self, temp_workspace, content):
        """Property: Same content produces same hash
        
        Feature: chapters-9-19-completion
        Property 2: Documentation Sync Consistency
        **Validates: Requirements 1.3, 1.4**
        
        Computing hash of the same file multiple times should produce
        the same hash value.
        """
        # Create test file
        test_file = temp_workspace / "test_doc.md"
        test_file.write_text(content, encoding='utf-8')
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        
        # Compute hash multiple times
        hash1 = checker.compute_document_hash(str(test_file))
        hash2 = checker.compute_document_hash(str(test_file))
        hash3 = checker.compute_document_hash(str(test_file))
        
        # Property: All hashes should be identical
        assert hash1 == hash2 == hash3, \
            "Hash should be consistent for same content"
        
        # Property: Hash should be non-empty
        assert hash1, "Hash should not be empty"
        
        # Property: Hash should be hex string (SHA-256 = 64 hex chars)
        assert len(hash1) == 64, \
            f"SHA-256 hash should be 64 characters, got {len(hash1)}"
        assert all(c in '0123456789abcdef' for c in hash1), \
            "Hash should be hexadecimal"
    
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        content1=st.text(min_size=10, max_size=500),
        content2=st.text(min_size=10, max_size=500)
    )
    def test_property_hash_uniqueness(self, temp_workspace, content1, content2):
        """Property: Different content produces different hash
        
        Feature: chapters-9-19-completion
        Property 2: Documentation Sync Consistency
        **Validates: Requirements 1.3, 1.4**
        
        Different file contents should produce different hash values
        (with overwhelming probability).
        """
        assume(content1 != content2)  # Only test when contents differ
        
        # Create test files
        file1 = temp_workspace / "doc1.md"
        file2 = temp_workspace / "doc2.md"
        file1.write_text(content1, encoding='utf-8')
        file2.write_text(content2, encoding='utf-8')
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        
        # Compute hashes
        hash1 = checker.compute_document_hash(str(file1))
        hash2 = checker.compute_document_hash(str(file2))
        
        # Property: Different content should produce different hashes
        assert hash1 != hash2, \
            "Different content should produce different hashes"

    def test_property_sync_status_completeness(self, temp_workspace):
        """Property: Sync status covers all document types
        
        Feature: chapters-9-19-completion
        Property 2: Documentation Sync Consistency
        **Validates: Requirements 1.3, 1.4**
        
        check_sync_status should return status for all document types.
        """
        # Ensure test directory exists
        test_dir = temp_workspace / ".kiro" / "specs" / "test"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Create minimal required files
        (temp_workspace / "00_核心文档" / "mia.md").write_text("# Whitepaper")
        (temp_workspace / "00_核心文档" / "IMPLEMENTATION_CHECKLIST.md").write_text("# Checklist")
        (test_dir / "tasks.md").write_text("# Tasks")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        status_map = checker.check_sync_status()
        
        # Property: Status map should contain expected keys
        expected_keys = {
            "whitepaper",
            "tasks",
            "todo",
            "checklist",
            "architecture",
            "project_structure"
        }
        
        assert set(status_map.keys()) == expected_keys, \
            f"Expected keys {expected_keys}, got {set(status_map.keys())}"
        
        # Property: All values should be SyncStatus objects
        for key, status in status_map.items():
            assert isinstance(status, SyncStatus), \
                f"Status for {key} should be SyncStatus, got {type(status)}"
            assert isinstance(status.document_type, DocumentType), \
                f"document_type should be DocumentType enum"
            assert isinstance(status.is_synced, bool), \
                f"is_synced should be boolean"
            assert isinstance(status.hash_value, str), \
                f"hash_value should be string"
    
    def test_property_deployment_blocking_consistency(self, temp_workspace):
        """Property: Deployment blocking is consistent with sync status
        
        Feature: chapters-9-19-completion
        Property 2: Documentation Sync Consistency
        **Validates: Requirements 1.3, 1.4**
        
        If critical documents are synced, deployment should not be blocked.
        If critical documents are missing, deployment should be blocked.
        """
        checker = DocumentationSyncChecker(str(temp_workspace))
        
        # Test 1: No critical documents - should block
        should_block1 = checker.block_deployment_if_out_of_sync()
        assert should_block1, \
            "Deployment should be blocked when critical documents missing"
        
        # Test 2: Create whitepaper only - should still block (checklist missing)
        (temp_workspace / "00_核心文档" / "mia.md").write_text("# Whitepaper")
        should_block2 = checker.block_deployment_if_out_of_sync()
        assert should_block2, \
            "Deployment should be blocked when checklist missing"
        
        # Test 3: Create both critical documents - should not block
        (temp_workspace / "00_核心文档" / "IMPLEMENTATION_CHECKLIST.md").write_text("# Checklist")
        should_block3 = checker.block_deployment_if_out_of_sync()
        assert not should_block3, \
            "Deployment should not be blocked when critical documents exist"
    
    def test_property_out_of_sync_detection(self, temp_workspace):
        """Property: Out-of-sync documents are correctly identified
        
        Feature: chapters-9-19-completion
        Property 2: Documentation Sync Consistency
        **Validates: Requirements 1.3, 1.4**
        
        Documents that don't exist should be reported as out of sync.
        """
        # Create only whitepaper
        (temp_workspace / "00_核心文档" / "mia.md").write_text("# Whitepaper")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        out_of_sync = checker.get_out_of_sync_documents()
        
        # Property: Should have multiple out-of-sync documents
        assert len(out_of_sync) > 0, \
            "Should detect out-of-sync documents"
        
        # Property: All out-of-sync documents should have is_synced=False
        for doc in out_of_sync:
            assert not doc.is_synced, \
                f"Out-of-sync document should have is_synced=False: {doc.document_type}"
            assert doc.error_message, \
                f"Out-of-sync document should have error message: {doc.document_type}"
    
    def test_property_documentation_completeness_validation(self, temp_workspace):
        """Property: Completeness validation is consistent
        
        Feature: chapters-9-19-completion
        Property 2: Documentation Sync Consistency
        **Validates: Requirements 1.3, 1.4**
        
        Documentation is complete if and only if all required documents exist.
        """
        # Ensure test directory exists
        test_dir = temp_workspace / ".kiro" / "specs" / "test"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        
        # Test 1: No documents - not complete
        is_complete1 = checker.validate_documentation_completeness()
        assert not is_complete1, \
            "Documentation should not be complete when files missing"
        
        # Test 2: Create required documents - should be complete
        (temp_workspace / "00_核心文档" / "mia.md").write_text("# Whitepaper")
        (test_dir / "tasks.md").write_text("# Tasks")
        (temp_workspace / "00_核心文档" / "IMPLEMENTATION_CHECKLIST.md").write_text("# Checklist")
        (temp_workspace / "00_核心文档" / "PROJECT_STRUCTURE.md").write_text("# Structure")
        
        is_complete2 = checker.validate_documentation_completeness()
        assert is_complete2, \
            "Documentation should be complete when all required files exist"
    
    def test_property_file_not_found_handling(self, temp_workspace):
        """Property: Non-existent files are handled gracefully
        
        Feature: chapters-9-19-completion
        Property 2: Documentation Sync Consistency
        **Validates: Requirements 1.3, 1.4**
        
        Attempting to hash a non-existent file should raise FileNotFoundError.
        """
        checker = DocumentationSyncChecker(str(temp_workspace))
        
        non_existent_file = str(temp_workspace / "does_not_exist.md")
        
        # Property: Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            checker.compute_document_hash(non_existent_file)
    
    @settings(max_examples=30)
    @given(
        content=st.text(min_size=1, max_size=500)
    )
    def test_property_workspace_root_validation(self, content):
        """Property: Invalid workspace root is rejected
        
        Feature: chapters-9-19-completion
        Property 2: Documentation Sync Consistency
        **Validates: Requirements 1.3, 1.4**
        
        Creating checker with non-existent workspace should raise ValueError.
        """
        non_existent_path = f"/non/existent/path/{content[:20]}"
        
        # Property: Should raise ValueError for non-existent path
        with pytest.raises(ValueError, match="Workspace root does not exist"):
            DocumentationSyncChecker(non_existent_path)
