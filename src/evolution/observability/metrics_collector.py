"""Metrics Collector

白皮书依据: 第四章 4.10 日志和可观测性

This module provides metrics collection for Arena pass rates, simulation success rates,
and decay detection rates.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class MetricPoint:
    """指标数据点

    Attributes:
        timestamp: 时间戳
        value: 值
        labels: 标签
    """

    timestamp: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """指标摘要

    Attributes:
        name: 指标名称
        count: 数据点数量
        total: 总和
        average: 平均值
        min_value: 最小值
        max_value: 最大值
        last_value: 最新值
    """

    name: str
    count: int
    total: float
    average: float
    min_value: float
    max_value: float
    last_value: float


class MetricsCollector:
    """指标收集器

    白皮书依据: 第四章 4.10 日志和可观测性

    收集Arena通过率、模拟成功率、衰减检测率等指标。

    Attributes:
        _metrics: 指标数据
        _counters: 计数器
        _lock: 线程锁
    """

    def __init__(self):
        """初始化指标收集器"""
        self._metrics: Dict[str, List[MetricPoint]] = {}
        self._counters: Dict[str, int] = {}
        self._lock: threading.RLock = threading.RLock()

        logger.info("MetricsCollector初始化完成")

    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """记录指标

        Args:
            name: 指标名称
            value: 值
            labels: 标签
        """
        point = MetricPoint(timestamp=datetime.now().isoformat(), value=value, labels=labels or {})

        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
            self._metrics[name].append(point)

    def increment_counter(self, name: str, amount: int = 1) -> int:
        """增加计数器

        Args:
            name: 计数器名称
            amount: 增加量

        Returns:
            新的计数值
        """
        with self._lock:
            if name not in self._counters:
                self._counters[name] = 0
            self._counters[name] += amount
            return self._counters[name]

    def get_counter(self, name: str) -> int:
        """获取计数器值

        Args:
            name: 计数器名称

        Returns:
            计数值
        """
        with self._lock:
            return self._counters.get(name, 0)

    def get_metric_summary(self, name: str) -> Optional[MetricSummary]:
        """获取指标摘要

        Args:
            name: 指标名称

        Returns:
            指标摘要，如果不存在则返回None
        """
        with self._lock:
            if name not in self._metrics or not self._metrics[name]:
                return None

            points = self._metrics[name]
            values = [p.value for p in points]

            return MetricSummary(
                name=name,
                count=len(values),
                total=sum(values),
                average=sum(values) / len(values),
                min_value=min(values),
                max_value=max(values),
                last_value=values[-1],
            )

    def get_all_metrics(self) -> Dict[str, MetricSummary]:
        """获取所有指标摘要

        Returns:
            指标名称到摘要的字典
        """
        with self._lock:
            result = {}
            for name in self._metrics:
                summary = self.get_metric_summary(name)
                if summary:
                    result[name] = summary
            return result

    def get_all_counters(self) -> Dict[str, int]:
        """获取所有计数器

        Returns:
            计数器名称到值的字典
        """
        with self._lock:
            return self._counters.copy()

    def clear(self) -> None:
        """清空所有指标和计数器"""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()

    # ========================================================================
    # Sparta Evolution 特定指标方法
    # ========================================================================

    def record_arena_result(self, arena_type: str, passed: bool, score: float) -> None:
        """记录Arena测试结果

        白皮书依据: 第四章 4.10 Arena指标

        Args:
            arena_type: Arena类型（factor/strategy）
            passed: 是否通过
            score: 得分
        """
        # 记录得分
        self.record_metric(f"arena_{arena_type}_score", score, {"arena_type": arena_type})

        # 更新计数器
        self.increment_counter(f"arena_{arena_type}_total")
        if passed:
            self.increment_counter(f"arena_{arena_type}_passed")

    def record_simulation_result(self, passed: bool, sharpe_ratio: float, total_return: float) -> None:
        """记录模拟结果

        白皮书依据: 第四章 4.10 模拟指标

        Args:
            passed: 是否通过
            sharpe_ratio: 夏普比率
            total_return: 总收益率
        """
        # 记录指标
        self.record_metric("simulation_sharpe_ratio", sharpe_ratio)
        self.record_metric("simulation_total_return", total_return)

        # 更新计数器
        self.increment_counter("simulation_total")
        if passed:
            self.increment_counter("simulation_passed")

    def record_decay_detection(self, severity: str, ic_value: float) -> None:
        """记录衰减检测

        白皮书依据: 第四章 4.10 衰减指标

        Args:
            severity: 严重程度
            ic_value: IC值
        """
        # 记录IC值
        self.record_metric("decay_ic_value", ic_value, {"severity": severity})

        # 更新计数器
        self.increment_counter("decay_detection_total")
        self.increment_counter(f"decay_{severity}")

    def get_arena_pass_rate(self, arena_type: str) -> float:
        """获取Arena通过率

        Args:
            arena_type: Arena类型

        Returns:
            通过率（0-1）
        """
        total = self.get_counter(f"arena_{arena_type}_total")
        passed = self.get_counter(f"arena_{arena_type}_passed")

        if total == 0:
            return 0.0

        return passed / total

    def get_simulation_success_rate(self) -> float:
        """获取模拟成功率

        Returns:
            成功率（0-1）
        """
        total = self.get_counter("simulation_total")
        passed = self.get_counter("simulation_passed")

        if total == 0:
            return 0.0

        return passed / total

    def get_decay_detection_rate(self) -> Dict[str, float]:
        """获取衰减检测率

        Returns:
            各严重程度的检测率
        """
        total = self.get_counter("decay_detection_total")

        if total == 0:
            return {"mild": 0.0, "moderate": 0.0, "severe": 0.0}

        return {
            "mild": self.get_counter("decay_mild") / total,
            "moderate": self.get_counter("decay_moderate") / total,
            "severe": self.get_counter("decay_severe") / total,
        }

    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态

        白皮书依据: 第四章 4.10 健康检查

        Returns:
            健康状态字典
        """
        factor_pass_rate = self.get_arena_pass_rate("factor")
        strategy_pass_rate = self.get_arena_pass_rate("strategy")
        simulation_success_rate = self.get_simulation_success_rate()

        # 判断健康状态
        is_healthy = (
            (factor_pass_rate >= 0.1 or self.get_counter("arena_factor_total") == 0)
            and (strategy_pass_rate >= 0.1 or self.get_counter("arena_strategy_total") == 0)
            and (simulation_success_rate >= 0.1 or self.get_counter("simulation_total") == 0)
        )

        return {
            "status": "healthy" if is_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "factor_arena_pass_rate": factor_pass_rate,
                "strategy_arena_pass_rate": strategy_pass_rate,
                "simulation_success_rate": simulation_success_rate,
                "decay_detection_rates": self.get_decay_detection_rate(),
            },
            "counters": self.get_all_counters(),
        }
