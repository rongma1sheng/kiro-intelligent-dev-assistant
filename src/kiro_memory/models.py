"""
Kiro记忆系统数据模型

定义记忆系统中使用的核心数据结构和类型。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
import numpy as np


class MemoryType(Enum):
    """记忆类型枚举"""
    CODE_PATTERN = "code_pattern"
    ERROR_SOLUTION = "error_solution"
    BEST_PRACTICE = "best_practice"
    PROJECT_CONTEXT = "project_context"
    TEAM_KNOWLEDGE = "team_knowledge"
    CONFIGURATION = "configuration"
    DEBUGGING_TIP = "debugging_tip"


class Priority(Enum):
    """优先级枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class MemoryPattern:
    """记忆模式数据结构"""
    id: str
    type: MemoryType
    content: Dict[str, Any]
    hash_key: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embeddings: Optional[np.ndarray] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    success_rate: float = 0.0
    priority: Priority = Priority.MEDIUM
    tags: List[str] = field(default_factory=list)
    source: str = "user"
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "hash_key": self.hash_key,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat(),
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "priority": self.priority.value,
            "tags": self.tags,
            "source": self.source,
            "confidence": self.confidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryPattern':
        """从字典创建实例"""
        return cls(
            id=data["id"],
            type=MemoryType(data["type"]),
            content=data["content"],
            hash_key=data["hash_key"],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used=datetime.fromisoformat(data["last_used"]),
            usage_count=data.get("usage_count", 0),
            success_rate=data.get("success_rate", 0.0),
            priority=Priority(data.get("priority", Priority.MEDIUM.value)),
            tags=data.get("tags", []),
            source=data.get("source", "user"),
            confidence=data.get("confidence", 1.0)
        )


@dataclass
class ProjectContext:
    """项目上下文信息"""
    file_path: str
    file_type: str
    dependencies: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    complexity_score: float = 0.0
    coverage_percentage: float = 0.0
    last_modified: datetime = field(default_factory=datetime.now)
    change_frequency: float = 0.0
    error_count: int = 0
    success_count: int = 0
    related_files: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "file_path": self.file_path,
            "file_type": self.file_type,
            "dependencies": self.dependencies,
            "imports": self.imports,
            "functions": self.functions,
            "classes": self.classes,
            "test_files": self.test_files,
            "complexity_score": self.complexity_score,
            "coverage_percentage": self.coverage_percentage,
            "last_modified": self.last_modified.isoformat(),
            "change_frequency": self.change_frequency,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "related_files": self.related_files
        }


@dataclass
class TeamKnowledge:
    """团队知识数据结构"""
    id: str
    topic: str
    role: str
    content: str
    confidence: float
    source: str
    tags: List[str] = field(default_factory=list)
    related_patterns: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    effectiveness_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "topic": self.topic,
            "role": self.role,
            "content": self.content,
            "confidence": self.confidence,
            "source": self.source,
            "tags": self.tags,
            "related_patterns": self.related_patterns,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "usage_count": self.usage_count,
            "effectiveness_score": self.effectiveness_score
        }


@dataclass
class QueryContext:
    """查询上下文"""
    query: str
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    current_task: Optional[str] = None
    user_role: Optional[str] = None
    recent_patterns: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    max_results: int = 10
    min_confidence: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "query": self.query,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "current_task": self.current_task,
            "user_role": self.user_role,
            "recent_patterns": self.recent_patterns,
            "preferences": self.preferences,
            "max_results": self.max_results,
            "min_confidence": self.min_confidence
        }


@dataclass
class LearningEvent:
    """学习事件数据结构"""
    pattern_id: str
    event_type: str  # "usage", "success", "failure", "feedback"
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "pattern_id": self.pattern_id,
            "event_type": self.event_type,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class MemoryStats:
    """记忆系统统计信息"""
    total_patterns: int = 0
    patterns_by_type: Dict[str, int] = field(default_factory=dict)
    total_queries: int = 0
    cache_hit_rate: float = 0.0
    average_query_time: float = 0.0
    storage_size_mb: float = 0.0
    learning_accuracy: float = 0.0
    most_used_patterns: List[str] = field(default_factory=list)
    recent_activity: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_patterns": self.total_patterns,
            "patterns_by_type": self.patterns_by_type,
            "total_queries": self.total_queries,
            "cache_hit_rate": self.cache_hit_rate,
            "average_query_time": self.average_query_time,
            "storage_size_mb": self.storage_size_mb,
            "learning_accuracy": self.learning_accuracy,
            "most_used_patterns": self.most_used_patterns,
            "recent_activity": self.recent_activity
        }