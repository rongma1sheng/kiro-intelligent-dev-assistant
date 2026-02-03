"""
Kiro记忆系统 - 基于DeepSeek-Engram启发的轻量级记忆架构

提供O(1)查找的代码模式存储和智能检索功能，专门为开发场景优化。
"""

from .models import MemoryPattern, ProjectContext, TeamKnowledge, MemoryType, Priority
from .storage import MemoryStorage
from .retrieval import HashRetrieval, ContextAwareRetrieval
from .learning import UsageLearning, ErrorPatternDetector
from .core import KiroMemorySystem

__version__ = "1.0.0"
__author__ = "Kiro Development Team"

__all__ = [
    "KiroMemorySystem",
    "MemoryPattern",
    "ProjectContext", 
    "TeamKnowledge",
    "MemoryType",
    "Priority",
    "MemoryStorage",
    "HashRetrieval",
    "ContextAwareRetrieval",
    "UsageLearning",
    "ErrorPatternDetector"
]