"""Performance Monitor - System Performance Monitoring

白皮书依据: 第十六章 16.0 性能优化指南

核心功能:
- Soldier延迟跟踪（P50, P95, P99）
- Redis吞吐量跟踪
- 性能回归检测（>10%阈值）
- 性能指标统计
"""

import statistics
from collections import deque
from typing import Any, Dict, List, Optional

from loguru import logger


class PerformanceMonitor:
    """性能监控器 - 系统性能监控

    白皮书依据: 第十六章 16.0 性能优化指南

    监控指标:
    - Soldier决策延迟: P50, P95, P99
    - Redis吞吐量: ops/s
    - 性能回归: >10%阈值告警

    Attributes:
        soldier_latencies: Soldier延迟记录（毫秒）
        redis_throughputs: Redis吞吐量记录（ops/s）
        window_size: 滑动窗口大小
        regression_threshold: 回归检测阈值（默认10%）
    """

    def __init__(self, window_size: int = 1000, regression_threshold: float = 0.10):
        """初始化性能监控器

        Args:
            window_size: 滑动窗口大小（样本数）
            regression_threshold: 回归检测阈值（0-1）

        Raises:
            ValueError: 当window_size或regression_threshold无效时
        """
        if window_size <= 0:
            raise ValueError(f"窗口大小必须 > 0: {window_size}")

        if not 0 < regression_threshold < 1:
            raise ValueError(f"回归阈值必须在 (0, 1) 范围内: {regression_threshold}")

        self.window_size = window_size
        self.regression_threshold = regression_threshold

        # 延迟记录（毫秒）
        self.soldier_latencies: deque = deque(maxlen=window_size)

        # 吞吐量记录（ops/s）
        self.redis_throughputs: deque = deque(maxlen=window_size)

        # 基线性能
        self.baseline_soldier_p99: Optional[float] = None
        self.baseline_redis_throughput: Optional[float] = None

        logger.info(
            f"[PerformanceMonitor] 初始化完成 - " f"窗口大小: {window_size}, " f"回归阈值: {regression_threshold:.1%}"
        )

    def track_soldier_latency(self, latency_ms: float) -> Dict[str, float]:
        """跟踪Soldier决策延迟（P50, P95, P99）

        白皮书依据: 第十六章 16.1 Soldier推理优化

        Args:
            latency_ms: 延迟时间（毫秒）

        Returns:
            延迟统计字典，包含:
            - p50: 中位数延迟（毫秒）
            - p95: 95分位延迟（毫秒）
            - p99: 99分位延迟（毫秒）
            - mean: 平均延迟（毫秒）
            - count: 样本数

        Raises:
            ValueError: 当latency_ms无效时
        """
        if latency_ms < 0:
            raise ValueError(f"延迟时间不能为负数: {latency_ms}")

        # 记录延迟
        self.soldier_latencies.append(latency_ms)

        # 计算统计指标
        stats = self._calculate_latency_stats(list(self.soldier_latencies))

        # 检查是否超过目标（P99 < 150ms）
        if stats["p99"] > 150:
            logger.warning(f"[PerformanceMonitor] Soldier延迟超标 - " f"P99: {stats['p99']:.2f}ms > 150ms")

        logger.debug(
            f"[PerformanceMonitor] Soldier延迟 - "
            f"P50: {stats['p50']:.2f}ms, "
            f"P95: {stats['p95']:.2f}ms, "
            f"P99: {stats['p99']:.2f}ms"
        )

        return stats

    def track_redis_throughput(self, operations: int, elapsed_seconds: float) -> Dict[str, float]:
        """跟踪Redis吞吐量

        白皮书依据: 第十六章 16.2 Redis性能优化

        Args:
            operations: 操作数
            elapsed_seconds: 耗时（秒）

        Returns:
            吞吐量统计字典，包含:
            - current: 当前吞吐量（ops/s）
            - mean: 平均吞吐量（ops/s）
            - min: 最小吞吐量（ops/s）
            - max: 最大吞吐量（ops/s）
            - count: 样本数

        Raises:
            ValueError: 当operations或elapsed_seconds无效时
        """
        if operations < 0:
            raise ValueError(f"操作数不能为负数: {operations}")

        if elapsed_seconds <= 0:
            raise ValueError(f"耗时必须 > 0: {elapsed_seconds}")

        # 计算吞吐量
        throughput = operations / elapsed_seconds

        # 记录吞吐量
        self.redis_throughputs.append(throughput)

        # 计算统计指标
        stats = self._calculate_throughput_stats(list(self.redis_throughputs))

        # 检查是否低于目标（> 150K ops/s）
        if stats["current"] < 150000:
            logger.warning(
                f"[PerformanceMonitor] Redis吞吐量低于目标 - " f"当前: {stats['current']:,.0f} ops/s < 150,000 ops/s"
            )

        logger.debug(
            f"[PerformanceMonitor] Redis吞吐量 - "
            f"当前: {stats['current']:,.0f} ops/s, "
            f"平均: {stats['mean']:,.0f} ops/s"
        )

        return stats

    def detect_performance_regression(self, metric_type: str) -> Dict[str, Any]:
        """检测性能回归（>10%阈值）

        白皮书依据: 第十六章 16.T.3 性能测试要求

        Args:
            metric_type: 指标类型（'soldier_latency' 或 'redis_throughput'）

        Returns:
            回归检测结果字典，包含:
            - has_regression: 是否发生回归
            - current_value: 当前值
            - baseline_value: 基线值
            - degradation_pct: 退化百分比
            - threshold_pct: 阈值百分比

        Raises:
            ValueError: 当metric_type无效时
            ValueError: 当基线未设置时
        """
        if metric_type not in ["soldier_latency", "redis_throughput"]:
            raise ValueError(f"无效的指标类型: {metric_type}，" f"必须是 'soldier_latency' 或 'redis_throughput'")

        if metric_type == "soldier_latency":
            if not self.soldier_latencies:
                raise ValueError("Soldier延迟数据为空，无法检测回归")

            if self.baseline_soldier_p99 is None:
                raise ValueError("Soldier延迟基线未设置，请先调用 set_baseline()")

            # 计算当前P99
            current_p99 = self._calculate_percentile(list(self.soldier_latencies), 99)

            # 计算退化百分比（延迟增加是退化）
            degradation = (current_p99 - self.baseline_soldier_p99) / self.baseline_soldier_p99

            has_regression = degradation > self.regression_threshold

            if has_regression:
                logger.error(
                    f"[PerformanceMonitor] 检测到Soldier延迟回归 - "
                    f"当前P99: {current_p99:.2f}ms, "
                    f"基线P99: {self.baseline_soldier_p99:.2f}ms, "
                    f"退化: {degradation:.1%} > {self.regression_threshold:.1%}"
                )

            return {
                "has_regression": has_regression,
                "current_value": current_p99,
                "baseline_value": self.baseline_soldier_p99,
                "degradation_pct": degradation,
                "threshold_pct": self.regression_threshold,
            }

        # redis_throughput
        if not self.redis_throughputs:
            raise ValueError("Redis吞吐量数据为空，无法检测回归")

        if self.baseline_redis_throughput is None:
            raise ValueError("Redis吞吐量基线未设置，请先调用 set_baseline()")

        # 计算当前平均吞吐量
        current_throughput = statistics.mean(self.redis_throughputs)

        # 计算退化百分比（吞吐量降低是退化）
        degradation = (self.baseline_redis_throughput - current_throughput) / self.baseline_redis_throughput

        has_regression = degradation > self.regression_threshold

        if has_regression:
            logger.error(
                f"[PerformanceMonitor] 检测到Redis吞吐量回归 - "
                f"当前: {current_throughput:,.0f} ops/s, "
                f"基线: {self.baseline_redis_throughput:,.0f} ops/s, "
                f"退化: {degradation:.1%} > {self.regression_threshold:.1%}"
            )

        return {
            "has_regression": has_regression,
            "current_value": current_throughput,
            "baseline_value": self.baseline_redis_throughput,
            "degradation_pct": degradation,
            "threshold_pct": self.regression_threshold,
        }

    def set_baseline(self, soldier_p99: Optional[float] = None, redis_throughput: Optional[float] = None) -> None:
        """设置性能基线

        Args:
            soldier_p99: Soldier延迟P99基线（毫秒）
            redis_throughput: Redis吞吐量基线（ops/s）
        """
        if soldier_p99 is not None:
            if soldier_p99 <= 0:
                raise ValueError(f"Soldier延迟基线必须 > 0: {soldier_p99}")
            self.baseline_soldier_p99 = soldier_p99
            logger.info(f"[PerformanceMonitor] Soldier延迟基线已设置: {soldier_p99:.2f}ms")

        if redis_throughput is not None:
            if redis_throughput <= 0:
                raise ValueError(f"Redis吞吐量基线必须 > 0: {redis_throughput}")
            self.baseline_redis_throughput = redis_throughput
            logger.info(f"[PerformanceMonitor] Redis吞吐量基线已设置: {redis_throughput:,.0f} ops/s")

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要

        Returns:
            性能摘要字典，包含:
            - soldier_latency: Soldier延迟统计
            - redis_throughput: Redis吞吐量统计
            - baselines: 基线值
            - sample_counts: 样本数
        """
        summary = {
            "soldier_latency": None,
            "redis_throughput": None,
            "baselines": {"soldier_p99": self.baseline_soldier_p99, "redis_throughput": self.baseline_redis_throughput},
            "sample_counts": {"soldier": len(self.soldier_latencies), "redis": len(self.redis_throughputs)},
        }

        # Soldier延迟统计
        if self.soldier_latencies:
            summary["soldier_latency"] = self._calculate_latency_stats(list(self.soldier_latencies))

        # Redis吞吐量统计
        if self.redis_throughputs:
            summary["redis_throughput"] = self._calculate_throughput_stats(list(self.redis_throughputs))

        return summary

    def _calculate_latency_stats(self, latencies: List[float]) -> Dict[str, float]:
        """计算延迟统计指标

        Args:
            latencies: 延迟列表（毫秒）

        Returns:
            统计指标字典
        """
        if not latencies:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0, "count": 0}

        return {
            "p50": self._calculate_percentile(latencies, 50),
            "p95": self._calculate_percentile(latencies, 95),
            "p99": self._calculate_percentile(latencies, 99),
            "mean": statistics.mean(latencies),
            "count": len(latencies),
        }

    def _calculate_throughput_stats(self, throughputs: List[float]) -> Dict[str, float]:
        """计算吞吐量统计指标

        Args:
            throughputs: 吞吐量列表（ops/s）

        Returns:
            统计指标字典
        """
        if not throughputs:
            return {"current": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0, "count": 0}

        return {
            "current": throughputs[-1],
            "mean": statistics.mean(throughputs),
            "min": min(throughputs),
            "max": max(throughputs),
            "count": len(throughputs),
        }

    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """计算百分位数

        Args:
            values: 数值列表
            percentile: 百分位（0-100）

        Returns:
            百分位数值
        """
        if not values:
            return 0.0

        sorted_values = sorted(values)

        # 使用线性插值计算百分位数
        # 对于P50，应该返回中位数
        if percentile == 0:
            return sorted_values[0]
        if percentile == 100:
            return sorted_values[-1]

        # 计算索引（使用0-based索引）
        index = (len(sorted_values) - 1) * percentile / 100
        lower_index = int(index)
        upper_index = min(lower_index + 1, len(sorted_values) - 1)

        # 线性插值
        weight = index - lower_index
        return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight

    def reset(self) -> None:
        """重置监控数据"""
        self.soldier_latencies.clear()
        self.redis_throughputs.clear()
        logger.info("[PerformanceMonitor] 监控数据已重置")

    def clear_baselines(self) -> None:
        """清除基线值"""
        self.baseline_soldier_p99 = None
        self.baseline_redis_throughput = None
        logger.info("[PerformanceMonitor] 基线值已清除")
