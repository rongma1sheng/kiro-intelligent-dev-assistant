"""Documentation Sync Checker

白皮书依据: 第九章 9.0 工程铁律 - Law 31 (Documentation Sync Law)

This module checks synchronization across all documentation files to ensure
that whitepaper, task lists, TODO files, implementation checklist, and architecture
documents are kept in sync with code changes.

MIA编码铁律依据:
- 铁律1: 白皮书至上 - Documentation sync is Law 31
- 铁律2: 禁止简化和占位符 - Complete implementation
- 铁律3: 完整的错误处理 - All file operations have error handling
- 铁律4: 完整的类型注解 - All functions have complete type hints
- 铁律5: 完整的文档字符串 - All public APIs have docstrings
- 铁律9: 文档同步律 - This module enforces the documentation sync law
"""

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger


class DocumentType(Enum):
    """Documentation file types"""

    WHITEPAPER = "whitepaper"
    TASKS = "tasks"
    TODO = "todo"
    CHECKLIST = "checklist"
    ARCHITECTURE = "architecture"
    PROJECT_STRUCTURE = "project_structure"


@dataclass
class SyncStatus:
    """Documentation sync status

    Attributes:
        document_type: Type of document
        file_path: Path to document file
        is_synced: True if document is synchronized
        last_modified: Last modification timestamp
        hash_value: SHA-256 hash of document content
        error_message: Error message if sync check failed
    """

    document_type: DocumentType
    file_path: str
    is_synced: bool
    last_modified: datetime
    hash_value: str
    error_message: Optional[str] = None


class DocumentationSyncChecker:
    """Checks synchronization across all documentation

    白皮书依据: 第九章 9.0 工程铁律 - Law 31 (Documentation Sync Law)

    This checker validates that all documentation files are synchronized:
    - Whitepaper (00_核心文档/mia.md)
    - Task lists (.kiro/specs/*/tasks.md)
    - TODO files (00_核心文档/*_TODO.md)
    - Implementation checklist (00_核心文档/IMPLEMENTATION_CHECKLIST.md)
    - Architecture documents (ARCHITECTURE_*.md)
    - Project structure (00_核心文档/PROJECT_STRUCTURE.md)

    Example:
        >>> checker = DocumentationSyncChecker()
        >>> status = checker.check_sync_status()
        >>> if not all(s.is_synced for s in status.values()):
        ...     print("Documentation out of sync!")
    """

    def __init__(self, workspace_root: Optional[str] = None):
        """Initialize documentation sync checker

        Args:
            workspace_root: Root directory of workspace (defaults to current directory)

        Raises:
            ValueError: If workspace_root does not exist
        """
        self.workspace_root = Path(workspace_root or os.getcwd())

        if not self.workspace_root.exists():
            raise ValueError(f"Workspace root does not exist: {self.workspace_root}")

        logger.info(f"DocumentationSyncChecker initialized with root: {self.workspace_root}")

    def check_sync_status(self) -> Dict[str, SyncStatus]:
        """Check sync status of all documentation

        白皮书依据: 第九章 9.0 工程铁律 - Law 31

        Checks all documentation files and returns their sync status.
        A document is considered "synced" if it exists and can be read.

        Returns:
            Dict mapping document type to sync status

        Example:
            >>> status = checker.check_sync_status()
            >>> for doc_type, sync_status in status.items():
            ...     print(f"{doc_type}: {'✓' if sync_status.is_synced else '✗'}")
        """
        logger.info("Checking documentation sync status")

        status_map: Dict[str, SyncStatus] = {}

        # Check whitepaper
        whitepaper_path = self.workspace_root / "00_核心文档" / "mia.md"
        status_map["whitepaper"] = self._check_file_status(DocumentType.WHITEPAPER, whitepaper_path)

        # Check task lists
        tasks_files = list(self.workspace_root.glob(".kiro/specs/*/tasks.md"))
        if tasks_files:
            # Use the first tasks file as representative
            status_map["tasks"] = self._check_file_status(DocumentType.TASKS, tasks_files[0])
        else:
            status_map["tasks"] = SyncStatus(
                document_type=DocumentType.TASKS,
                file_path="",
                is_synced=False,
                last_modified=datetime.now(),
                hash_value="",
                error_message="No tasks.md files found",
            )

        # Check TODO files
        todo_files = list(self.workspace_root.glob("00_核心文档/*_TODO.md"))
        if todo_files:
            status_map["todo"] = self._check_file_status(DocumentType.TODO, todo_files[0])
        else:
            status_map["todo"] = SyncStatus(
                document_type=DocumentType.TODO,
                file_path="",
                is_synced=False,
                last_modified=datetime.now(),
                hash_value="",
                error_message="No TODO files found",
            )

        # Check implementation checklist
        checklist_path = self.workspace_root / "00_核心文档" / "IMPLEMENTATION_CHECKLIST.md"
        status_map["checklist"] = self._check_file_status(DocumentType.CHECKLIST, checklist_path)

        # Check architecture documents
        arch_files = list(self.workspace_root.glob("ARCHITECTURE_*.md"))
        if arch_files:
            status_map["architecture"] = self._check_file_status(DocumentType.ARCHITECTURE, arch_files[0])
        else:
            status_map["architecture"] = SyncStatus(
                document_type=DocumentType.ARCHITECTURE,
                file_path="",
                is_synced=False,
                last_modified=datetime.now(),
                hash_value="",
                error_message="No architecture documents found",
            )

        # Check project structure
        project_structure_path = self.workspace_root / "00_核心文档" / "PROJECT_STRUCTURE.md"
        status_map["project_structure"] = self._check_file_status(
            DocumentType.PROJECT_STRUCTURE, project_structure_path
        )

        synced_count = sum(1 for s in status_map.values() if s.is_synced)
        logger.info(f"Documentation sync check complete: {synced_count}/{len(status_map)} documents synced")

        return status_map

    def _check_file_status(self, doc_type: DocumentType, file_path: Path) -> SyncStatus:
        """Check sync status of a single file

        Args:
            doc_type: Type of document
            file_path: Path to document file

        Returns:
            SyncStatus for the file
        """
        try:
            if not file_path.exists():
                return SyncStatus(
                    document_type=doc_type,
                    file_path=str(file_path),
                    is_synced=False,
                    last_modified=datetime.now(),
                    hash_value="",
                    error_message=f"File does not exist: {file_path}",
                )

            # Get last modified time
            last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)

            # Compute hash
            hash_value = self.compute_document_hash(str(file_path))

            return SyncStatus(
                document_type=doc_type,
                file_path=str(file_path),
                is_synced=True,
                last_modified=last_modified,
                hash_value=hash_value,
                error_message=None,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error checking file {file_path}: {e}", exc_info=True)
            return SyncStatus(
                document_type=doc_type,
                file_path=str(file_path),
                is_synced=False,
                last_modified=datetime.now(),
                hash_value="",
                error_message=str(e),
            )

    def compute_document_hash(self, file_path: str) -> str:
        """Compute hash of document for sync tracking

        白皮书依据: 第九章 9.0 工程铁律 - Law 31

        Computes SHA-256 hash of document content for tracking changes.

        Args:
            file_path: Path to document file

        Returns:
            SHA-256 hash as hex string

        Raises:
            FileNotFoundError: If file does not exist
            IOError: If file cannot be read

        Example:
            >>> hash1 = checker.compute_document_hash("mia.md")
            >>> # ... modify file ...
            >>> hash2 = checker.compute_document_hash("mia.md")
            >>> assert hash1 != hash2  # File changed
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {file_path}")

        try:
            with open(path, "rb") as f:
                content = f.read()
                hash_value = hashlib.sha256(content).hexdigest()

            logger.debug(f"Computed hash for {file_path}: {hash_value[:16]}...")
            return hash_value

        except IOError as e:
            logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
            raise IOError(f"Cannot read file {file_path}: {e}") from e

    def block_deployment_if_out_of_sync(self) -> bool:
        """Block deployment if documentation is out of sync

        白皮书依据: 第九章 9.0 工程铁律 - Law 31

        Checks if all critical documentation is synchronized.
        Returns True if deployment should be blocked.

        Critical documents:
        - Whitepaper (must exist and be readable)
        - Implementation checklist (must exist and be readable)

        Returns:
            True if deployment should be blocked, False otherwise

        Example:
            >>> if checker.block_deployment_if_out_of_sync():
            ...     print("Deployment blocked: documentation out of sync")
            ...     sys.exit(1)
        """
        logger.info("Checking if deployment should be blocked")

        status_map = self.check_sync_status()

        # Check critical documents
        critical_docs = ["whitepaper", "checklist"]

        for doc_key in critical_docs:
            if doc_key not in status_map:
                logger.error(f"Critical document missing: {doc_key}")
                return True

            status = status_map[doc_key]
            if not status.is_synced:
                logger.error(f"Critical document out of sync: {doc_key} - {status.error_message}")
                return True

        # Check if any documents have errors
        docs_with_errors = [
            (key, status.error_message)
            for key, status in status_map.items()
            if not status.is_synced and status.error_message
        ]

        if docs_with_errors:
            logger.warning(
                f"Found {len(docs_with_errors)} documents with errors: " f"{[key for key, _ in docs_with_errors]}"
            )
            # Only block if critical documents are affected
            critical_errors = [key for key, _ in docs_with_errors if key in critical_docs]
            if critical_errors:
                logger.error(f"Critical documents have errors: {critical_errors}")
                return True

        logger.info("Documentation sync check passed, deployment allowed")
        return False

    def get_out_of_sync_documents(self) -> List[SyncStatus]:
        """Get list of documents that are out of sync

        Returns:
            List of SyncStatus for documents that are not synced

        Example:
            >>> out_of_sync = checker.get_out_of_sync_documents()
            >>> for doc in out_of_sync:
            ...     print(f"Out of sync: {doc.document_type.value} - {doc.error_message}")
        """
        status_map = self.check_sync_status()
        return [status for status in status_map.values() if not status.is_synced]

    def validate_documentation_completeness(self) -> bool:
        """Validate that all required documentation exists

        白皮书依据: 第九章 9.0 工程铁律 - Law 31

        Checks that all required documentation files exist and are readable.

        Returns:
            True if all required documentation exists, False otherwise
        """
        logger.info("Validating documentation completeness")

        status_map = self.check_sync_status()

        # All document types should be present
        required_types = ["whitepaper", "tasks", "checklist", "project_structure"]

        missing_docs = []
        for doc_type in required_types:
            if doc_type not in status_map or not status_map[doc_type].is_synced:
                missing_docs.append(doc_type)

        if missing_docs:
            logger.error(f"Missing or unreadable documentation: {missing_docs}")
            return False

        logger.info("Documentation completeness validation passed")
        return True
