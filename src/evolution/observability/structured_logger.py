"""Structured Logger

白皮书依据: 第四章 4.10 日志和可观测性

This module provides structured logging with JSON format, timestamps,
module names, and correlation IDs.
"""

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class LogLevel(Enum):
    """日志级别

    白皮书依据: 第四章 4.10.8 日志级别配置
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """日志条目

    白皮书依据: 第四章 4.10.6 结构化日志

    Attributes:
        timestamp: 时间戳
        level: 日志级别
        module: 模块名称
        correlation_id: 关联ID
        message: 日志消息
        context: 上下文数据
    """

    timestamp: str
    level: str
    module: str
    correlation_id: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """转换为JSON字符串

        Returns:
            JSON字符串
        """
        return json.dumps(
            {
                "timestamp": self.timestamp,
                "level": self.level,
                "module": self.module,
                "correlation_id": self.correlation_id,
                "message": self.message,
                "context": self.context,
            },
            ensure_ascii=False,
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            字典
        """
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "module": self.module,
            "correlation_id": self.correlation_id,
            "message": self.message,
            "context": self.context,
        }


class StructuredLogger:
    """结构化日志器

    白皮书依据: 第四章 4.10 日志和可观测性

    提供结构化日志记录，包含时间戳、模块名、关联ID等。

    Attributes:
        module_name: 模块名称
        log_level: 日志级别
        correlation_id: 当前关联ID
        _entries: 日志条目列表（用于测试）
        _handlers: 日志处理器列表
    """

    # 线程本地存储，用于关联ID
    _local = threading.local()

    def __init__(self, module_name: str, log_level: LogLevel = LogLevel.INFO, correlation_id: Optional[str] = None):
        """初始化结构化日志器

        Args:
            module_name: 模块名称
            log_level: 日志级别
            correlation_id: 关联ID，None则自动生成
        """
        self.module_name: str = module_name
        self.log_level: LogLevel = log_level
        self._correlation_id: str = correlation_id or self._generate_correlation_id()
        self._entries: List[LogEntry] = []
        self._handlers: List[Callable[[LogEntry], None]] = []
        self._lock: threading.Lock = threading.Lock()

    @property
    def correlation_id(self) -> str:
        """获取当前关联ID

        Returns:
            关联ID
        """
        return self._correlation_id

    @correlation_id.setter
    def correlation_id(self, value: str) -> None:
        """设置关联ID

        Args:
            value: 新的关联ID
        """
        self._correlation_id = value

    def _generate_correlation_id(self) -> str:
        """生成关联ID

        Returns:
            UUID格式的关联ID
        """
        return str(uuid.uuid4())[:8]

    def _should_log(self, level: LogLevel) -> bool:
        """判断是否应该记录日志

        Args:
            level: 日志级别

        Returns:
            是否应该记录
        """
        level_order = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.CRITICAL: 4,
        }
        return level_order[level] >= level_order[self.log_level]

    def _create_entry(self, level: LogLevel, message: str, context: Optional[Dict[str, Any]] = None) -> LogEntry:
        """创建日志条目

        Args:
            level: 日志级别
            message: 日志消息
            context: 上下文数据

        Returns:
            日志条目
        """
        return LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level.value,
            module=self.module_name,
            correlation_id=self._correlation_id,
            message=message,
            context=context or {},
        )

    def _log(self, level: LogLevel, message: str, context: Optional[Dict[str, Any]] = None) -> Optional[LogEntry]:
        """记录日志

        Args:
            level: 日志级别
            message: 日志消息
            context: 上下文数据

        Returns:
            日志条目，如果未记录则返回None
        """
        if not self._should_log(level):
            return None

        entry = self._create_entry(level, message, context)

        with self._lock:
            self._entries.append(entry)

        # 调用处理器
        for handler in self._handlers:
            try:
                handler(entry)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"日志处理器执行失败: {e}")

        # 同时使用loguru记录
        log_func = getattr(logger, level.value.lower())
        log_func(f"[{self.module_name}][{self._correlation_id}] {message} | {context or {}}")

        return entry

    def debug(self, message: str, **context: Any) -> Optional[LogEntry]:
        """记录DEBUG日志

        Args:
            message: 日志消息
            **context: 上下文数据

        Returns:
            日志条目
        """
        return self._log(LogLevel.DEBUG, message, context)

    def info(self, message: str, **context: Any) -> Optional[LogEntry]:
        """记录INFO日志

        Args:
            message: 日志消息
            **context: 上下文数据

        Returns:
            日志条目
        """
        return self._log(LogLevel.INFO, message, context)

    def warning(self, message: str, **context: Any) -> Optional[LogEntry]:
        """记录WARNING日志

        Args:
            message: 日志消息
            **context: 上下文数据

        Returns:
            日志条目
        """
        return self._log(LogLevel.WARNING, message, context)

    def error(self, message: str, **context: Any) -> Optional[LogEntry]:
        """记录ERROR日志

        Args:
            message: 日志消息
            **context: 上下文数据

        Returns:
            日志条目
        """
        return self._log(LogLevel.ERROR, message, context)

    def critical(self, message: str, **context: Any) -> Optional[LogEntry]:
        """记录CRITICAL日志

        Args:
            message: 日志消息
            **context: 上下文数据

        Returns:
            日志条目
        """
        return self._log(LogLevel.CRITICAL, message, context)

    def add_handler(self, handler: Callable[[LogEntry], None]) -> None:
        """添加日志处理器

        Args:
            handler: 处理器函数
        """
        self._handlers.append(handler)

    def remove_handler(self, handler: Callable[[LogEntry], None]) -> None:
        """移除日志处理器

        Args:
            handler: 处理器函数
        """
        if handler in self._handlers:
            self._handlers.remove(handler)

    def get_entries(self) -> List[LogEntry]:
        """获取所有日志条目

        Returns:
            日志条目列表
        """
        with self._lock:
            return self._entries.copy()

    def clear_entries(self) -> None:
        """清空日志条目"""
        with self._lock:
            self._entries.clear()

    # ========================================================================
    # Sparta Evolution 特定日志方法
    # ========================================================================

    def log_arena_start(self, arena_type: str, entity_id: str, parameters: Dict[str, Any]) -> LogEntry:
        """记录Arena测试开始

        白皮书依据: 第四章 4.10.1 Arena日志

        Args:
            arena_type: Arena类型（factor/strategy）
            entity_id: 因子/策略ID
            parameters: 测试参数

        Returns:
            日志条目
        """
        return self.info(
            f"Arena测试开始",  # pylint: disable=w1309
            arena_type=arena_type,
            entity_id=entity_id,
            parameters=parameters,
            event_type="ARENA_START",
        )

    def log_track_completion(self, track_name: str, entity_id: str, score: float, metrics: Dict[str, Any]) -> LogEntry:
        """记录Track完成

        白皮书依据: 第四章 4.10.2 Track日志

        Args:
            track_name: Track名称
            entity_id: 因子/策略ID
            score: 得分
            metrics: 指标

        Returns:
            日志条目
        """
        return self.info(
            f"Track测试完成: {track_name}",
            track_name=track_name,
            entity_id=entity_id,
            score=score,
            metrics=metrics,
            event_type="TRACK_COMPLETION",
        )

    def log_validation_failure(self, stage: str, entity_id: str, reason: str, details: Dict[str, Any]) -> LogEntry:
        """记录验证失败

        白皮书依据: 第四章 4.10.3 验证失败日志

        Args:
            stage: 验证阶段
            entity_id: 因子/策略ID
            reason: 失败原因
            details: 详细信息

        Returns:
            日志条目
        """
        return self.warning(
            f"验证失败: {stage}",
            stage=stage,
            entity_id=entity_id,
            reason=reason,
            details=details,
            event_type="VALIDATION_FAILURE",
        )

    def log_z2h_certification(
        self, strategy_id: str, certification_level: str, capsule_id: str, metrics: Dict[str, Any]
    ) -> LogEntry:
        """记录Z2H认证

        白皮书依据: 第四章 4.10.4 Z2H认证日志

        Args:
            strategy_id: 策略ID
            certification_level: 认证级别
            capsule_id: 胶囊ID
            metrics: 指标

        Returns:
            日志条目
        """
        return self.info(
            f"Z2H认证完成: {certification_level}",
            strategy_id=strategy_id,
            certification_level=certification_level,
            capsule_id=capsule_id,
            metrics=metrics,
            event_type="Z2H_CERTIFICATION",
        )

    def log_decay_detection(self, factor_id: str, severity: str, ic_value: float, consecutive_days: int) -> LogEntry:
        """记录衰减检测

        白皮书依据: 第四章 4.10.5 衰减检测日志

        Args:
            factor_id: 因子ID
            severity: 严重程度
            ic_value: IC值
            consecutive_days: 连续天数

        Returns:
            日志条目
        """
        return self.warning(
            f"因子衰减检测: {severity}",
            factor_id=factor_id,
            severity=severity,
            ic_value=ic_value,
            consecutive_days=consecutive_days,
            event_type="DECAY_DETECTION",
        )


# 全局日志器缓存
_loggers: Dict[str, StructuredLogger] = {}
_loggers_lock = threading.Lock()


def get_logger(module_name: str, log_level: LogLevel = LogLevel.INFO) -> StructuredLogger:
    """获取或创建日志器

    Args:
        module_name: 模块名称
        log_level: 日志级别

    Returns:
        StructuredLogger实例
    """
    with _loggers_lock:
        if module_name not in _loggers:
            _loggers[module_name] = StructuredLogger(module_name, log_level)
        return _loggers[module_name]
