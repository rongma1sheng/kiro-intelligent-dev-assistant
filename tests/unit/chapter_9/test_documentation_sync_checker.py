"""Unit Tests for Documentation Sync Checker

白皮书依据: 第九章 9.0 工程铁律 - Law 31 (Documentation Sync Law)

These tests achieve 100% coverage of the DocumentationSyncChecker module,
testing all methods, edge cases, and error handling.

Coverage Target: 100% (user requirement)
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from src.compliance.documentation_sync_checker import (
    DocumentationSyncChecker,
    SyncStatus,
    DocumentType
)


class TestDocumentationSyncChecker:
    """Unit tests for DocumentationSyncChecker
    
    Coverage target: 100%
    """
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create directory structure
            (workspace / "00_核心文档").mkdir(parents=True)
            (workspace / ".kiro" / "specs" / "test-spec").mkdir(parents=True)
            
            yield workspace
    
    def test_initialization_success(self, temp_workspace):
        """Test successful initialization"""
        checker = DocumentationSyncChecker(str(temp_workspace))
        
        assert checker is not None
        assert checker.workspace_root == temp_workspace
    
    def test_initialization_with_none_workspace(self):
        """Test initialization with None workspace (uses current directory)"""
        checker = DocumentationSyncChecker(None)
        
        assert checker is not None
        assert checker.workspace_root == Path(os.getcwd())
    
    def test_initialization_with_nonexistent_workspace(self):
        """Test initialization with non-existent workspace"""
        with pytest.raises(ValueError, match="Workspace root does not exist"):
            DocumentationSyncChecker("/non/existent/path/12345")
    
    def test_check_sync_status_all_missing(self, temp_workspace):
        """Test sync status when all documents are missing"""
        checker = DocumentationSyncChecker(str(temp_workspace))
        status_map = checker.check_sync_status()
        
        # Should have entries for all document types
        assert "whitepaper" in status_map
        assert "tasks" in status_map
        assert "todo" in status_map
        assert "checklist" in status_map
        assert "architecture" in status_map
        assert "project_structure" in status_map
        
        # All should be not synced
        for key, status in status_map.items():
            assert isinstance(status, SyncStatus)
            assert not status.is_synced
            assert status.error_message is not None
    
    def test_check_sync_status_whitepaper_exists(self, temp_workspace):
        """Test sync status when whitepaper exists"""
        # Create whitepaper
        whitepaper_path = temp_workspace / "00_核心文档" / "mia.md"
        whitepaper_path.write_text("# MIA Whitepaper\n\nContent here.")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        status_map = checker.check_sync_status()
        
        # Whitepaper should be synced
        assert status_map["whitepaper"].is_synced
        assert status_map["whitepaper"].error_message is None
        assert status_map["whitepaper"].hash_value
        assert len(status_map["whitepaper"].hash_value) == 64  # SHA-256
    
    def test_check_sync_status_all_exist(self, temp_workspace):
        """Test sync status when all documents exist"""
        # Create all documents
        (temp_workspace / "00_核心文档" / "mia.md").write_text("# Whitepaper")
        # Create directory structure for tasks.md
        (temp_workspace / ".kiro" / "specs" / "test").mkdir(parents=True, exist_ok=True)
        (temp_workspace / ".kiro" / "specs" / "test" / "tasks.md").write_text("# Tasks")
        (temp_workspace / "00_核心文档" / "TEST_TODO.md").write_text("# TODO")
        (temp_workspace / "00_核心文档" / "IMPLEMENTATION_CHECKLIST.md").write_text("# Checklist")
        (temp_workspace / "ARCHITECTURE_TEST.md").write_text("# Architecture")
        (temp_workspace / "00_核心文档" / "PROJECT_STRUCTURE.md").write_text("# Structure")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        status_map = checker.check_sync_status()
        
        # All should be synced
        for key, status in status_map.items():
            assert status.is_synced, f"{key} should be synced"
            assert status.error_message is None
            assert status.hash_value
    
    def test_compute_document_hash_success(self, temp_workspace):
        """Test successful hash computation"""
        test_file = temp_workspace / "test.md"
        test_file.write_text("Test content")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        hash_value = checker.compute_document_hash(str(test_file))
        
        assert hash_value
        assert len(hash_value) == 64  # SHA-256 hex string
        assert all(c in '0123456789abcdef' for c in hash_value)
    
    def test_compute_document_hash_nonexistent_file(self, temp_workspace):
        """Test hash computation with non-existent file"""
        checker = DocumentationSyncChecker(str(temp_workspace))
        
        with pytest.raises(FileNotFoundError):
            checker.compute_document_hash(str(temp_workspace / "nonexistent.md"))
    
    def test_compute_document_hash_consistency(self, temp_workspace):
        """Test hash consistency for same content"""
        test_file = temp_workspace / "test.md"
        test_file.write_text("Consistent content")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        
        hash1 = checker.compute_document_hash(str(test_file))
        hash2 = checker.compute_document_hash(str(test_file))
        hash3 = checker.compute_document_hash(str(test_file))
        
        assert hash1 == hash2 == hash3
    
    def test_compute_document_hash_different_content(self, temp_workspace):
        """Test hash changes with different content"""
        test_file = temp_workspace / "test.md"
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        
        test_file.write_text("Content 1")
        hash1 = checker.compute_document_hash(str(test_file))
        
        test_file.write_text("Content 2")
        hash2 = checker.compute_document_hash(str(test_file))
        
        assert hash1 != hash2

    def test_block_deployment_no_critical_docs(self, temp_workspace):
        """Test deployment blocking when critical documents missing"""
        checker = DocumentationSyncChecker(str(temp_workspace))
        
        should_block = checker.block_deployment_if_out_of_sync()
        
        assert should_block, "Should block when critical documents missing"
    
    def test_block_deployment_only_whitepaper(self, temp_workspace):
        """Test deployment blocking when only whitepaper exists"""
        (temp_workspace / "00_核心文档" / "mia.md").write_text("# Whitepaper")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        should_block = checker.block_deployment_if_out_of_sync()
        
        assert should_block, "Should block when checklist missing"
    
    def test_block_deployment_all_critical_docs(self, temp_workspace):
        """Test deployment not blocked when critical documents exist"""
        (temp_workspace / "00_核心文档" / "mia.md").write_text("# Whitepaper")
        (temp_workspace / "00_核心文档" / "IMPLEMENTATION_CHECKLIST.md").write_text("# Checklist")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        should_block = checker.block_deployment_if_out_of_sync()
        
        assert not should_block, "Should not block when critical documents exist"
    
    def test_get_out_of_sync_documents_all_missing(self, temp_workspace):
        """Test getting out-of-sync documents when all missing"""
        checker = DocumentationSyncChecker(str(temp_workspace))
        out_of_sync = checker.get_out_of_sync_documents()
        
        assert len(out_of_sync) > 0
        
        for doc in out_of_sync:
            assert isinstance(doc, SyncStatus)
            assert not doc.is_synced
            assert doc.error_message
    
    def test_get_out_of_sync_documents_some_exist(self, temp_workspace):
        """Test getting out-of-sync documents when some exist"""
        (temp_workspace / "00_核心文档" / "mia.md").write_text("# Whitepaper")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        out_of_sync = checker.get_out_of_sync_documents()
        
        # Should have some out-of-sync documents
        assert len(out_of_sync) > 0
        
        # Whitepaper should not be in out-of-sync list
        out_of_sync_types = [doc.document_type for doc in out_of_sync]
        assert DocumentType.WHITEPAPER not in out_of_sync_types
    
    def test_get_out_of_sync_documents_all_exist(self, temp_workspace):
        """Test getting out-of-sync documents when all exist"""
        # Create all documents
        (temp_workspace / "00_核心文档" / "mia.md").write_text("# Whitepaper")
        # Create directory structure for tasks.md
        (temp_workspace / ".kiro" / "specs" / "test").mkdir(parents=True, exist_ok=True)
        (temp_workspace / ".kiro" / "specs" / "test" / "tasks.md").write_text("# Tasks")
        (temp_workspace / "00_核心文档" / "TEST_TODO.md").write_text("# TODO")
        (temp_workspace / "00_核心文档" / "IMPLEMENTATION_CHECKLIST.md").write_text("# Checklist")
        (temp_workspace / "ARCHITECTURE_TEST.md").write_text("# Architecture")
        (temp_workspace / "00_核心文档" / "PROJECT_STRUCTURE.md").write_text("# Structure")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        out_of_sync = checker.get_out_of_sync_documents()
        
        # Should have no out-of-sync documents
        assert len(out_of_sync) == 0
    
    def test_validate_documentation_completeness_missing(self, temp_workspace):
        """Test completeness validation when documents missing"""
        checker = DocumentationSyncChecker(str(temp_workspace))
        
        is_complete = checker.validate_documentation_completeness()
        
        assert not is_complete
    
    def test_validate_documentation_completeness_partial(self, temp_workspace):
        """Test completeness validation with partial documents"""
        (temp_workspace / "00_核心文档" / "mia.md").write_text("# Whitepaper")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        is_complete = checker.validate_documentation_completeness()
        
        assert not is_complete
    
    def test_validate_documentation_completeness_complete(self, temp_workspace):
        """Test completeness validation when all required documents exist"""
        # Create required documents
        (temp_workspace / "00_核心文档" / "mia.md").write_text("# Whitepaper")
        # Create directory structure for tasks.md
        (temp_workspace / ".kiro" / "specs" / "test").mkdir(parents=True, exist_ok=True)
        (temp_workspace / ".kiro" / "specs" / "test" / "tasks.md").write_text("# Tasks")
        (temp_workspace / "00_核心文档" / "IMPLEMENTATION_CHECKLIST.md").write_text("# Checklist")
        (temp_workspace / "00_核心文档" / "PROJECT_STRUCTURE.md").write_text("# Structure")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        is_complete = checker.validate_documentation_completeness()
        
        assert is_complete
    
    def test_check_file_status_exists(self, temp_workspace):
        """Test _check_file_status with existing file"""
        test_file = temp_workspace / "test.md"
        test_file.write_text("Test content")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        status = checker._check_file_status(DocumentType.WHITEPAPER, test_file)
        
        assert status.is_synced
        assert status.error_message is None
        assert status.hash_value
        assert status.last_modified
        assert isinstance(status.last_modified, datetime)
    
    def test_check_file_status_not_exists(self, temp_workspace):
        """Test _check_file_status with non-existent file"""
        test_file = temp_workspace / "nonexistent.md"
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        status = checker._check_file_status(DocumentType.WHITEPAPER, test_file)
        
        assert not status.is_synced
        assert status.error_message
        assert "does not exist" in status.error_message
        assert status.hash_value == ""
    
    def test_check_file_status_exception_handling(self, temp_workspace, monkeypatch):
        """Test _check_file_status exception handling"""
        test_file = temp_workspace / "test.md"
        test_file.write_text("Test content")
        
        # Mock compute_document_hash to raise exception
        def mock_hash_error(file_path):
            raise IOError("Test error")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        monkeypatch.setattr(checker, 'compute_document_hash', mock_hash_error)
        
        status = checker._check_file_status(DocumentType.WHITEPAPER, test_file)
        
        assert not status.is_synced
        assert status.error_message
        assert "Test error" in status.error_message
    
    def test_sync_status_dataclass(self, temp_workspace):
        """Test SyncStatus dataclass structure"""
        status = SyncStatus(
            document_type=DocumentType.WHITEPAPER,
            file_path="/path/to/file.md",
            is_synced=True,
            last_modified=datetime.now(),
            hash_value="abc123",
            error_message=None
        )
        
        assert status.document_type == DocumentType.WHITEPAPER
        assert status.file_path == "/path/to/file.md"
        assert status.is_synced
        assert status.hash_value == "abc123"
        assert status.error_message is None
    
    def test_document_type_enum(self):
        """Test DocumentType enum values"""
        assert DocumentType.WHITEPAPER.value == "whitepaper"
        assert DocumentType.TASKS.value == "tasks"
        assert DocumentType.TODO.value == "todo"
        assert DocumentType.CHECKLIST.value == "checklist"
        assert DocumentType.ARCHITECTURE.value == "architecture"
        assert DocumentType.PROJECT_STRUCTURE.value == "project_structure"
    
    def test_edge_case_empty_file(self, temp_workspace):
        """Test hash computation with empty file"""
        test_file = temp_workspace / "empty.md"
        test_file.write_text("")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        hash_value = checker.compute_document_hash(str(test_file))
        
        assert hash_value
        assert len(hash_value) == 64
    
    def test_edge_case_large_file(self, temp_workspace):
        """Test hash computation with large file"""
        test_file = temp_workspace / "large.md"
        test_file.write_text("x" * 1000000)  # 1MB file
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        hash_value = checker.compute_document_hash(str(test_file))
        
        assert hash_value
        assert len(hash_value) == 64
    
    def test_edge_case_unicode_content(self, temp_workspace):
        """Test hash computation with Unicode content"""
        test_file = temp_workspace / "unicode.md"
        test_file.write_text("中文内容 🚀 Special chars: ñ, é, ü", encoding='utf-8')
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        hash_value = checker.compute_document_hash(str(test_file))
        
        assert hash_value
        assert len(hash_value) == 64
    
    def test_multiple_tasks_files(self, temp_workspace):
        """Test handling multiple tasks.md files"""
        # Create multiple tasks files
        (temp_workspace / ".kiro" / "specs" / "spec1").mkdir(parents=True)
        (temp_workspace / ".kiro" / "specs" / "spec2").mkdir(parents=True)
        (temp_workspace / ".kiro" / "specs" / "spec1" / "tasks.md").write_text("# Tasks 1")
        (temp_workspace / ".kiro" / "specs" / "spec2" / "tasks.md").write_text("# Tasks 2")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        status_map = checker.check_sync_status()
        
        # Should use first tasks file found
        assert status_map["tasks"].is_synced
    
    def test_multiple_todo_files(self, temp_workspace):
        """Test handling multiple TODO files"""
        # Create multiple TODO files
        (temp_workspace / "00_核心文档" / "CHAPTER1_TODO.md").write_text("# TODO 1")
        (temp_workspace / "00_核心文档" / "CHAPTER2_TODO.md").write_text("# TODO 2")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        status_map = checker.check_sync_status()
        
        # Should use first TODO file found
        assert status_map["todo"].is_synced
    
    def test_multiple_architecture_files(self, temp_workspace):
        """Test handling multiple architecture files"""
        # Create multiple architecture files
        (temp_workspace / "ARCHITECTURE_V1.md").write_text("# Arch 1")
        (temp_workspace / "ARCHITECTURE_V2.md").write_text("# Arch 2")
        
        checker = DocumentationSyncChecker(str(temp_workspace))
        status_map = checker.check_sync_status()
        
        # Should use first architecture file found
        assert status_map["architecture"].is_synced
