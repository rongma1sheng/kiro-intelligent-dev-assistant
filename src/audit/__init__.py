"""审计模块

白皮书依据: 第七章 7.2 审计体系

本模块实现MIA系统的审计体系，包括：
- 独立审计进程
- 审计日志系统
- 完整性验证
"""

from src.audit.audit_logger import AuditLogger, IntegrityError
from src.audit.auditor import AuditError, Auditor, InsufficientPositionError, ReconciliationError
from src.audit.data_models import (
    AuditEntry,
    AuditEventType,
    ReconciliationDiscrepancy,
    ShadowPosition,
)

__all__ = [
    "AuditLogger",
    "IntegrityError",
    "Auditor",
    "AuditError",
    "InsufficientPositionError",
    "ReconciliationError",
    "AuditEventType",
    "AuditEntry",
    "ShadowPosition",
    "ReconciliationDiscrepancy",
]
