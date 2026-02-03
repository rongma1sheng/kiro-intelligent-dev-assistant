"""第四章错误处理模块

白皮书依据: 第四章 斯巴达进化系统

实现遗传算法、Arena测试、策略生成、模拟、认证、集成、监控等
各模块的错误处理和日志记录。
"""

import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

# ============================================================================
# 错误类型定义
# ============================================================================


class ErrorSeverity(Enum):
    """错误严重程度"""

    INFO = "信息"
    WARNING = "警告"
    ERROR = "错误"
    CRITICAL = "严重"


class ErrorCategory(Enum):
    """错误类别"""

    GENETIC_ALGORITHM = "遗传算法"
    ARENA_TESTING = "Arena测试"
    STRATEGY_GENERATION = "策略生成"
    SIMULATION = "模拟"
    CERTIFICATION = "认证"
    INTEGRATION = "集成"
    MONITORING = "监控"
    DATA = "数据"
    SYSTEM = "系统"


# ============================================================================
# 自定义异常类
# ============================================================================


class SpartaEvolutionError(Exception):
    """斯巴达进化系统基础异常

    白皮书依据: 第四章 错误处理
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


# 遗传算法相关异常
class InvalidFactorExpressionError(SpartaEvolutionError):
    """无效因子表达式异常"""

    def __init__(self, expression: str, reason: str):
        super().__init__(
            message=f"无效因子表达式: {expression}, 原因: {reason}",
            category=ErrorCategory.GENETIC_ALGORITHM,
            severity=ErrorSeverity.ERROR,
            details={"expression": expression, "reason": reason},
        )


class FitnessEvaluationError(SpartaEvolutionError):
    """适应度评估失败异常"""

    def __init__(self, factor_id: str, reason: str):
        super().__init__(
            message=f"因子 {factor_id} 适应度评估失败: {reason}",
            category=ErrorCategory.GENETIC_ALGORITHM,
            severity=ErrorSeverity.WARNING,
            details={"factor_id": factor_id, "reason": reason},
        )


class PopulationDiversityCollapseError(SpartaEvolutionError):
    """种群多样性崩溃异常"""

    def __init__(self, diversity_score: float, threshold: float):
        super().__init__(
            message=f"种群多样性崩溃: 当前多样性 {diversity_score:.4f} < 阈值 {threshold:.4f}",
            category=ErrorCategory.GENETIC_ALGORITHM,
            severity=ErrorSeverity.WARNING,
            details={"diversity_score": diversity_score, "threshold": threshold},
        )


# Arena测试相关异常
class InsufficientHistoricalDataError(SpartaEvolutionError):
    """历史数据不足异常"""

    def __init__(self, required_days: int, available_days: int):
        super().__init__(
            message=f"历史数据不足: 需要 {required_days} 天, 仅有 {available_days} 天",
            category=ErrorCategory.ARENA_TESTING,
            severity=ErrorSeverity.ERROR,
            details={"required_days": required_days, "available_days": available_days},
        )


class ExtremeScenarioGenerationError(SpartaEvolutionError):
    """极端场景生成失败异常"""

    def __init__(self, scenario_type: str, reason: str):
        super().__init__(
            message=f"极端场景 '{scenario_type}' 生成失败: {reason}",
            category=ErrorCategory.ARENA_TESTING,
            severity=ErrorSeverity.WARNING,
            details={"scenario_type": scenario_type, "reason": reason},
        )


class CrossMarketDataUnavailableError(SpartaEvolutionError):
    """跨市场数据不可用异常"""

    def __init__(self, market: str, reason: str):
        super().__init__(
            message=f"市场 '{market}' 数据不可用: {reason}",
            category=ErrorCategory.ARENA_TESTING,
            severity=ErrorSeverity.WARNING,
            details={"market": market, "reason": reason},
        )


# 策略生成相关异常
class FactorCombinationError(SpartaEvolutionError):
    """因子组合失败异常"""

    def __init__(self, factor_ids: List[str], reason: str):
        super().__init__(
            message=f"因子组合失败: {reason}",
            category=ErrorCategory.STRATEGY_GENERATION,
            severity=ErrorSeverity.ERROR,
            details={"factor_ids": factor_ids, "reason": reason},
        )


class CodeGenerationSyntaxError(SpartaEvolutionError):
    """代码生成语法错误异常"""

    def __init__(self, code_snippet: str, syntax_error: str):
        super().__init__(
            message=f"代码生成语法错误: {syntax_error}",
            category=ErrorCategory.STRATEGY_GENERATION,
            severity=ErrorSeverity.ERROR,
            details={"code_snippet": code_snippet[:200], "syntax_error": syntax_error},
        )


# 模拟相关异常
class MarketDataFeedInterruptionError(SpartaEvolutionError):
    """市场数据流中断异常"""

    def __init__(self, source: str, duration_seconds: float):
        super().__init__(
            message=f"市场数据源 '{source}' 中断 {duration_seconds:.1f} 秒",
            category=ErrorCategory.SIMULATION,
            severity=ErrorSeverity.WARNING,
            details={"source": source, "duration_seconds": duration_seconds},
        )


class ExcessiveDrawdownError(SpartaEvolutionError):
    """过度回撤异常"""

    def __init__(self, current_drawdown: float, threshold: float, strategy_id: str):
        super().__init__(
            message=f"策略 {strategy_id} 回撤 {current_drawdown:.2%} 超过阈值 {threshold:.2%}",
            category=ErrorCategory.SIMULATION,
            severity=ErrorSeverity.CRITICAL,
            details={"strategy_id": strategy_id, "current_drawdown": current_drawdown, "threshold": threshold},
        )


class OrderExecutionError(SpartaEvolutionError):
    """订单执行失败异常"""

    def __init__(self, order_id: str, symbol: str, reason: str):
        super().__init__(
            message=f"订单 {order_id} ({symbol}) 执行失败: {reason}",
            category=ErrorCategory.SIMULATION,
            severity=ErrorSeverity.ERROR,
            details={"order_id": order_id, "symbol": symbol, "reason": reason},
        )


# 认证相关异常
class IncompleteSimulationMetricsError(SpartaEvolutionError):
    """模拟指标不完整异常"""

    def __init__(self, missing_metrics: List[str]):
        super().__init__(
            message=f"模拟指标不完整，缺少: {', '.join(missing_metrics)}",
            category=ErrorCategory.CERTIFICATION,
            severity=ErrorSeverity.ERROR,
            details={"missing_metrics": missing_metrics},
        )


class GeneCapsuleGenerationError(SpartaEvolutionError):
    """基因胶囊生成失败异常"""

    def __init__(self, strategy_id: str, reason: str):
        super().__init__(
            message=f"策略 {strategy_id} 基因胶囊生成失败: {reason}",
            category=ErrorCategory.CERTIFICATION,
            severity=ErrorSeverity.ERROR,
            details={"strategy_id": strategy_id, "reason": reason},
        )


# 集成相关异常
class CommanderIntegrationError(SpartaEvolutionError):
    """Commander集成失败异常"""

    def __init__(self, factor_id: str, reason: str):
        super().__init__(
            message=f"因子 {factor_id} Commander集成失败: {reason}",
            category=ErrorCategory.INTEGRATION,
            severity=ErrorSeverity.ERROR,
            details={"factor_id": factor_id, "reason": reason},
        )


class StrategyLibraryConflictError(SpartaEvolutionError):
    """策略库冲突异常"""

    def __init__(self, strategy_id: str, conflict_type: str):
        super().__init__(
            message=f"策略 {strategy_id} 库冲突: {conflict_type}",
            category=ErrorCategory.INTEGRATION,
            severity=ErrorSeverity.WARNING,
            details={"strategy_id": strategy_id, "conflict_type": conflict_type},
        )


# 监控相关异常
class MetricCalculationError(SpartaEvolutionError):
    """指标计算失败异常"""

    def __init__(self, metric_name: str, reason: str):
        super().__init__(
            message=f"指标 '{metric_name}' 计算失败: {reason}",
            category=ErrorCategory.MONITORING,
            severity=ErrorSeverity.WARNING,
            details={"metric_name": metric_name, "reason": reason},
        )


class FactorDegradationDetectionError(SpartaEvolutionError):
    """因子衰减检测失败异常"""

    def __init__(self, factor_id: str, reason: str):
        super().__init__(
            message=f"因子 {factor_id} 衰减检测失败: {reason}",
            category=ErrorCategory.MONITORING,
            severity=ErrorSeverity.WARNING,
            details={"factor_id": factor_id, "reason": reason},
        )


# ============================================================================
# 错误记录和统计
# ============================================================================


@dataclass
class ErrorRecord:
    """错误记录

    白皮书依据: 第四章 错误日志
    """

    error_id: str
    error_type: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: datetime
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    resolution_notes: Optional[str] = None


class ErrorTracker:
    """错误跟踪器

    白皮书依据: 第四章 错误监控

    跟踪和统计系统中发生的错误。
    """

    def __init__(self, max_records: int = 1000):
        """初始化错误跟踪器

        Args:
            max_records: 最大记录数量
        """
        self.max_records = max_records
        self.records: List[ErrorRecord] = []
        self._error_count = 0
        self._category_counts: Dict[ErrorCategory, int] = {cat: 0 for cat in ErrorCategory}
        self._severity_counts: Dict[ErrorSeverity, int] = {sev: 0 for sev in ErrorSeverity}

        logger.info(f"错误跟踪器初始化完成，最大记录数: {max_records}")

    def record_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> str:
        """记录错误

        Args:
            error: 异常对象
            context: 上下文信息

        Returns:
            错误ID
        """
        self._error_count += 1
        error_id = f"ERR_{self._error_count:06d}"

        # 确定错误类别和严重程度
        if isinstance(error, SpartaEvolutionError):
            category = error.category
            severity = error.severity
            message = error.message
            error_context = {**error.details, **(context or {})}
        else:
            category = ErrorCategory.SYSTEM
            severity = ErrorSeverity.ERROR
            message = str(error)
            error_context = context or {}

        # 创建记录
        record = ErrorRecord(
            error_id=error_id,
            error_type=type(error).__name__,
            message=message,
            category=category,
            severity=severity,
            timestamp=datetime.now(),
            stack_trace=traceback.format_exc(),
            context=error_context,
        )

        # 添加记录
        self.records.append(record)

        # 限制记录数量
        if len(self.records) > self.max_records:
            self.records = self.records[-self.max_records :]

        # 更新统计
        self._category_counts[category] += 1
        self._severity_counts[severity] += 1

        # 记录日志
        log_method = {
            ErrorSeverity.INFO: logger.info,
            ErrorSeverity.WARNING: logger.warning,
            ErrorSeverity.ERROR: logger.error,
            ErrorSeverity.CRITICAL: logger.critical,
        }.get(severity, logger.error)

        log_method(f"[{error_id}] [{category.value}] {message}")

        return error_id

    def resolve_error(self, error_id: str, notes: Optional[str] = None) -> bool:
        """标记错误已解决

        Args:
            error_id: 错误ID
            notes: 解决备注

        Returns:
            是否成功
        """
        for record in self.records:
            if record.error_id == error_id:
                record.resolved = True
                record.resolution_time = datetime.now()
                record.resolution_notes = notes
                logger.info(f"错误 {error_id} 已标记为已解决")
                return True

        return False

    def get_recent_errors(
        self,
        count: int = 10,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        unresolved_only: bool = False,
    ) -> List[ErrorRecord]:
        """获取最近的错误

        Args:
            count: 数量
            category: 类别筛选
            severity: 严重程度筛选
            unresolved_only: 仅未解决的

        Returns:
            错误记录列表
        """
        filtered = self.records

        if category is not None:
            filtered = [r for r in filtered if r.category == category]

        if severity is not None:
            filtered = [r for r in filtered if r.severity == severity]

        if unresolved_only:
            filtered = [r for r in filtered if not r.resolved]

        return filtered[-count:]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        unresolved_count = sum(1 for r in self.records if not r.resolved)

        return {
            "total_errors": self._error_count,
            "recorded_errors": len(self.records),
            "unresolved_errors": unresolved_count,
            "by_category": {cat.value: count for cat, count in self._category_counts.items()},
            "by_severity": {sev.value: count for sev, count in self._severity_counts.items()},
        }

    def clear(self) -> None:
        """清空记录"""
        self.records.clear()
        self._error_count = 0
        self._category_counts = {cat: 0 for cat in ErrorCategory}
        self._severity_counts = {sev: 0 for sev in ErrorSeverity}
        logger.info("错误跟踪器已清空")


# ============================================================================
# 错误处理装饰器
# ============================================================================


def handle_errors(
    category: ErrorCategory = ErrorCategory.SYSTEM,
    default_return: Any = None,
    reraise: bool = False,
    tracker: Optional[ErrorTracker] = None,
):
    """错误处理装饰器

    白皮书依据: 第四章 错误处理

    Args:
        category: 错误类别
        default_return: 发生错误时的默认返回值
        reraise: 是否重新抛出异常
        tracker: 错误跟踪器
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except SpartaEvolutionError as e:
                if tracker:
                    tracker.record_error(e)
                else:
                    logger.error(f"[{category.value}] {e.message}")

                if reraise:
                    raise
                return default_return
            except Exception as e:  # pylint: disable=broad-exception-caught
                error = SpartaEvolutionError(message=str(e), category=category, severity=ErrorSeverity.ERROR)
                if tracker:
                    tracker.record_error(error)
                else:
                    logger.error(f"[{category.value}] {str(e)}")

                if reraise:
                    raise
                return default_return

        return wrapper

    return decorator


def handle_async_errors(
    category: ErrorCategory = ErrorCategory.SYSTEM,
    default_return: Any = None,
    reraise: bool = False,
    tracker: Optional[ErrorTracker] = None,
):
    """异步错误处理装饰器

    白皮书依据: 第四章 错误处理
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except SpartaEvolutionError as e:
                if tracker:
                    tracker.record_error(e)
                else:
                    logger.error(f"[{category.value}] {e.message}")

                if reraise:
                    raise
                return default_return
            except Exception as e:  # pylint: disable=broad-exception-caught
                error = SpartaEvolutionError(message=str(e), category=category, severity=ErrorSeverity.ERROR)
                if tracker:
                    tracker.record_error(error)
                else:
                    logger.error(f"[{category.value}] {str(e)}")

                if reraise:
                    raise
                return default_return

        return wrapper

    return decorator


# ============================================================================
# 全局错误跟踪器实例
# ============================================================================

# 全局错误跟踪器
global_error_tracker = ErrorTracker(max_records=1000)


def get_global_error_tracker() -> ErrorTracker:
    """获取全局错误跟踪器"""
    return global_error_tracker
