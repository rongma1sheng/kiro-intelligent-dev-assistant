"""认证性能监控器

白皮书依据: 第四章 4.3.2 Z2H认证系统 - 性能监控

本模块实现认证流程的性能监控，确保认证过程高效可靠。

核心功能：
- 监控每个认证阶段的执行时间
- 监控Arena四层验证的总耗时
- 监控模拟盘验证的资源使用
- 记录性能告警
- 统计认证流程的成功率和失败率
- 统计各认证等级的分布情况
- 生成性能分析报告

Author: MIA System
Version: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from src.evolution.z2h_data_models import CertificationLevel


class PerformanceAlertLevel(Enum):
    """性能告警级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class StagePerformanceMetrics:
    """阶段性能指标"""

    stage_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    success: bool = False
    error_message: Optional[str] = None


@dataclass
class ArenaPerformanceMetrics:
    """Arena验证性能指标"""

    total_duration_seconds: float
    layer1_duration_seconds: float
    layer2_duration_seconds: float
    layer3_duration_seconds: float
    layer4_duration_seconds: float
    overall_score: float


@dataclass
class SimulationResourceMetrics:
    """模拟盘资源使用指标"""

    cpu_usage_percent: float
    memory_usage_mb: float
    disk_io_mb: float
    network_io_mb: float
    peak_cpu_percent: float
    peak_memory_mb: float


@dataclass
class PerformanceAlert:
    """性能告警"""

    alert_id: str
    alert_level: PerformanceAlertLevel
    alert_time: datetime
    stage_name: str
    metric_name: str
    actual_value: float
    threshold_value: float
    message: str


@dataclass
class CertificationStatistics:
    """认证统计信息"""

    total_certifications: int
    successful_certifications: int
    failed_certifications: int
    success_rate: float
    failure_rate: float
    avg_duration_seconds: float
    level_distribution: Dict[str, int]


@dataclass
class PerformanceAnalysisReport:
    """性能分析报告

    白皮书依据: 第四章 4.3.2 认证性能分析报告
    """

    report_id: str
    report_date: datetime
    time_range_start: datetime
    time_range_end: datetime

    # 统计信息
    statistics: CertificationStatistics

    # 性能指标
    stage_metrics: List[StagePerformanceMetrics]
    arena_metrics: List[ArenaPerformanceMetrics]
    simulation_metrics: List[SimulationResourceMetrics]

    # 告警信息
    alerts: List[PerformanceAlert]

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


class CertificationPerformanceMonitor:
    """认证性能监控器

    白皮书依据: 第四章 4.3.2 Z2H认证系统 - 性能监控

    核心功能：
    1. 监控每个认证阶段的执行时间
    2. 监控Arena四层验证的总耗时
    3. 监控模拟盘验证的资源使用
    4. 记录性能告警
    5. 统计认证流程的成功率和失败率
    6. 统计各认证等级的分布情况
    7. 生成性能分析报告

    Attributes:
        stage_metrics_history: 阶段性能指标历史
        arena_metrics_history: Arena性能指标历史
        simulation_metrics_history: 模拟盘资源指标历史
        alerts_history: 性能告警历史
        certification_results: 认证结果历史
        performance_thresholds: 性能阈值配置
    """

    def __init__(self):
        """初始化性能监控器"""
        self.stage_metrics_history: List[StagePerformanceMetrics] = []
        self.arena_metrics_history: List[ArenaPerformanceMetrics] = []
        self.simulation_metrics_history: List[SimulationResourceMetrics] = []
        self.alerts_history: List[PerformanceAlert] = []
        self.certification_results: List[Dict[str, Any]] = []

        # 性能阈值配置（基于白皮书要求）
        self.performance_thresholds = {
            "arena_total_duration": 30.0,  # Arena总耗时 < 30秒
            "stage_duration": 60.0,  # 单阶段耗时 < 60秒
            "cpu_usage": 80.0,  # CPU使用率 < 80%
            "memory_usage": 2048.0,  # 内存使用 < 2GB
        }

        logger.info("初始化CertificationPerformanceMonitor")

    def start_stage_monitoring(self, stage_name: str) -> str:
        """开始监控认证阶段

        白皮书依据: 第四章 4.3.2 阶段执行时间监控

        Args:
            stage_name: 阶段名称

        Returns:
            str: 监控ID
        """
        metrics = StagePerformanceMetrics(stage_name=stage_name, start_time=datetime.now())

        self.stage_metrics_history.append(metrics)

        monitoring_id = f"{stage_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"开始监控阶段: {stage_name}, monitoring_id={monitoring_id}")

        return monitoring_id

    def end_stage_monitoring(self, stage_name: str, success: bool, error_message: Optional[str] = None) -> None:
        """结束阶段监控

        Args:
            stage_name: 阶段名称
            success: 是否成功
            error_message: 错误信息（如果失败）
        """
        # 查找最近的该阶段监控记录
        for metrics in reversed(self.stage_metrics_history):
            if metrics.stage_name == stage_name and metrics.end_time is None:
                metrics.end_time = datetime.now()
                metrics.duration_seconds = (metrics.end_time - metrics.start_time).total_seconds()
                metrics.success = success
                metrics.error_message = error_message

                logger.info(
                    f"结束阶段监控: {stage_name}, " f"duration={metrics.duration_seconds:.2f}s, " f"success={success}"
                )

                # 检查是否超过阈值
                self._check_stage_duration_threshold(metrics)

                break

    def record_arena_performance(
        self, total_duration: float, layer_durations: Dict[int, float], overall_score: float
    ) -> None:
        """记录Arena验证性能

        白皮书依据: 第四章 4.3.2 Arena验证耗时监控

        Args:
            total_duration: 总耗时（秒）
            layer_durations: 各层耗时字典 {layer_num: duration}
            overall_score: 综合评分
        """
        metrics = ArenaPerformanceMetrics(
            total_duration_seconds=total_duration,
            layer1_duration_seconds=layer_durations.get(1, 0.0),
            layer2_duration_seconds=layer_durations.get(2, 0.0),
            layer3_duration_seconds=layer_durations.get(3, 0.0),
            layer4_duration_seconds=layer_durations.get(4, 0.0),
            overall_score=overall_score,
        )

        self.arena_metrics_history.append(metrics)

        logger.info(f"记录Arena性能 - " f"total={total_duration:.2f}s, " f"score={overall_score:.2f}")

        # 检查Arena总耗时阈值
        self._check_arena_duration_threshold(metrics)

    def record_simulation_resources(
        self, cpu_usage: float, memory_usage: float, disk_io: float = 0.0, network_io: float = 0.0
    ) -> None:
        """记录模拟盘资源使用

        白皮书依据: 第四章 4.3.2 模拟盘资源使用监控

        Args:
            cpu_usage: CPU使用率（百分比）
            memory_usage: 内存使用量（MB）
            disk_io: 磁盘IO（MB）
            network_io: 网络IO（MB）
        """
        # 计算峰值
        peak_cpu = cpu_usage
        peak_memory = memory_usage

        if self.simulation_metrics_history:
            last_metrics = self.simulation_metrics_history[-1]
            peak_cpu = max(cpu_usage, last_metrics.peak_cpu_percent)
            peak_memory = max(memory_usage, last_metrics.peak_memory_mb)

        metrics = SimulationResourceMetrics(
            cpu_usage_percent=cpu_usage,
            memory_usage_mb=memory_usage,
            disk_io_mb=disk_io,
            network_io_mb=network_io,
            peak_cpu_percent=peak_cpu,
            peak_memory_mb=peak_memory,
        )

        self.simulation_metrics_history.append(metrics)

        logger.debug(f"记录模拟盘资源 - " f"CPU={cpu_usage:.1f}%, " f"Memory={memory_usage:.1f}MB")

        # 检查资源使用阈值
        self._check_resource_usage_threshold(metrics)

    def record_certification_result(
        self, strategy_id: str, success: bool, level: Optional[CertificationLevel] = None, duration_seconds: float = 0.0
    ) -> None:
        """记录认证结果

        Args:
            strategy_id: 策略ID
            success: 是否成功
            level: 认证等级
            duration_seconds: 总耗时
        """
        result = {
            "strategy_id": strategy_id,
            "success": success,
            "level": level.value if level else None,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now(),
        }

        self.certification_results.append(result)

        logger.info(
            f"记录认证结果 - "
            f"strategy_id={strategy_id}, "
            f"success={success}, "
            f"level={level.value if level else 'N/A'}"
        )

    def _check_stage_duration_threshold(self, metrics: StagePerformanceMetrics) -> None:
        """检查阶段耗时阈值

        Args:
            metrics: 阶段性能指标
        """
        threshold = self.performance_thresholds["stage_duration"]

        if metrics.duration_seconds > threshold:
            alert = PerformanceAlert(
                alert_id=f"stage_duration_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                alert_level=PerformanceAlertLevel.WARNING,
                alert_time=datetime.now(),
                stage_name=metrics.stage_name,
                metric_name="stage_duration",
                actual_value=metrics.duration_seconds,
                threshold_value=threshold,
                message=f"阶段 {metrics.stage_name} 耗时 {metrics.duration_seconds:.2f}s 超过阈值 {threshold}s",
            )

            self.alerts_history.append(alert)

            logger.warning(alert.message)

    def _check_arena_duration_threshold(self, metrics: ArenaPerformanceMetrics) -> None:
        """检查Arena耗时阈值

        Args:
            metrics: Arena性能指标
        """
        threshold = self.performance_thresholds["arena_total_duration"]

        if metrics.total_duration_seconds > threshold:
            alert = PerformanceAlert(
                alert_id=f"arena_duration_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                alert_level=PerformanceAlertLevel.WARNING,
                alert_time=datetime.now(),
                stage_name="Arena验证",
                metric_name="arena_total_duration",
                actual_value=metrics.total_duration_seconds,
                threshold_value=threshold,
                message=f"Arena验证耗时 {metrics.total_duration_seconds:.2f}s 超过阈值 {threshold}s",
            )

            self.alerts_history.append(alert)

            logger.warning(alert.message)

    def _check_resource_usage_threshold(self, metrics: SimulationResourceMetrics) -> None:
        """检查资源使用阈值

        Args:
            metrics: 模拟盘资源指标
        """
        # 检查CPU使用率
        cpu_threshold = self.performance_thresholds["cpu_usage"]
        if metrics.cpu_usage_percent > cpu_threshold:
            alert = PerformanceAlert(
                alert_id=f"cpu_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                alert_level=PerformanceAlertLevel.WARNING,
                alert_time=datetime.now(),
                stage_name="模拟盘验证",
                metric_name="cpu_usage",
                actual_value=metrics.cpu_usage_percent,
                threshold_value=cpu_threshold,
                message=f"CPU使用率 {metrics.cpu_usage_percent:.1f}% 超过阈值 {cpu_threshold}%",
            )

            self.alerts_history.append(alert)
            logger.warning(alert.message)

        # 检查内存使用
        memory_threshold = self.performance_thresholds["memory_usage"]
        if metrics.memory_usage_mb > memory_threshold:
            alert = PerformanceAlert(
                alert_id=f"memory_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                alert_level=PerformanceAlertLevel.WARNING,
                alert_time=datetime.now(),
                stage_name="模拟盘验证",
                metric_name="memory_usage",
                actual_value=metrics.memory_usage_mb,
                threshold_value=memory_threshold,
                message=f"内存使用 {metrics.memory_usage_mb:.1f}MB 超过阈值 {memory_threshold}MB",
            )

            self.alerts_history.append(alert)
            logger.warning(alert.message)

    def get_certification_statistics(
        self, time_range_start: Optional[datetime] = None, time_range_end: Optional[datetime] = None
    ) -> CertificationStatistics:
        """获取认证统计信息

        白皮书依据: 第四章 4.3.2 成功率/失败率统计

        Args:
            time_range_start: 时间范围开始
            time_range_end: 时间范围结束

        Returns:
            CertificationStatistics: 认证统计信息
        """
        # 过滤时间范围内的结果
        filtered_results = self.certification_results

        if time_range_start or time_range_end:
            filtered_results = [
                r
                for r in self.certification_results
                if (not time_range_start or r["timestamp"] >= time_range_start)
                and (not time_range_end or r["timestamp"] <= time_range_end)
            ]

        if not filtered_results:
            return CertificationStatistics(
                total_certifications=0,
                successful_certifications=0,
                failed_certifications=0,
                success_rate=0.0,
                failure_rate=0.0,
                avg_duration_seconds=0.0,
                level_distribution={},
            )

        total = len(filtered_results)
        successful = sum(1 for r in filtered_results if r["success"])
        failed = total - successful

        success_rate = successful / total if total > 0 else 0.0
        failure_rate = failed / total if total > 0 else 0.0

        # 计算平均耗时
        durations = [r["duration_seconds"] for r in filtered_results if r["duration_seconds"] > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # 统计等级分布
        level_distribution = {}
        for r in filtered_results:
            if r["level"]:
                level_distribution[r["level"]] = level_distribution.get(r["level"], 0) + 1

        statistics = CertificationStatistics(
            total_certifications=total,
            successful_certifications=successful,
            failed_certifications=failed,
            success_rate=success_rate,
            failure_rate=failure_rate,
            avg_duration_seconds=avg_duration,
            level_distribution=level_distribution,
        )

        logger.info(
            f"认证统计 - " f"total={total}, " f"success_rate={success_rate:.2%}, " f"avg_duration={avg_duration:.2f}s"
        )

        return statistics

    def get_level_distribution(self) -> Dict[str, int]:
        """获取认证等级分布

        白皮书依据: 第四章 4.3.2 认证等级分布统计

        Returns:
            Dict[str, int]: 等级分布字典
        """
        distribution = {}

        for result in self.certification_results:
            if result["success"] and result["level"]:
                level = result["level"]
                distribution[level] = distribution.get(level, 0) + 1

        logger.info(f"认证等级分布: {distribution}")

        return distribution

    def get_performance_alerts(
        self,
        level: Optional[PerformanceAlertLevel] = None,
        time_range_start: Optional[datetime] = None,
        time_range_end: Optional[datetime] = None,
    ) -> List[PerformanceAlert]:
        """获取性能告警

        Args:
            level: 告警级别过滤
            time_range_start: 时间范围开始
            time_range_end: 时间范围结束

        Returns:
            List[PerformanceAlert]: 告警列表
        """
        alerts = self.alerts_history

        # 按级别过滤
        if level:
            alerts = [a for a in alerts if a.alert_level == level]

        # 按时间范围过滤
        if time_range_start:
            alerts = [a for a in alerts if a.alert_time >= time_range_start]

        if time_range_end:
            alerts = [a for a in alerts if a.alert_time <= time_range_end]

        return alerts

    def generate_performance_analysis_report(
        self, time_range_start: Optional[datetime] = None, time_range_end: Optional[datetime] = None
    ) -> PerformanceAnalysisReport:
        """生成性能分析报告

        白皮书依据: 第四章 4.3.2 性能分析报告生成

        Args:
            time_range_start: 时间范围开始
            time_range_end: 时间范围结束

        Returns:
            PerformanceAnalysisReport: 性能分析报告
        """
        # 设置默认时间范围（最近7天）
        if not time_range_end:
            time_range_end = datetime.now()

        if not time_range_start:
            time_range_start = time_range_end - timedelta(days=7)

        # 获取统计信息
        statistics = self.get_certification_statistics(time_range_start, time_range_end)

        # 过滤时间范围内的指标
        stage_metrics = [m for m in self.stage_metrics_history if time_range_start <= m.start_time <= time_range_end]

        arena_metrics = self.arena_metrics_history  # 简化：使用全部
        simulation_metrics = self.simulation_metrics_history  # 简化：使用全部

        # 获取告警
        alerts = self.get_performance_alerts(time_range_start=time_range_start, time_range_end=time_range_end)

        # 生成报告
        report = PerformanceAnalysisReport(
            report_id=f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            report_date=datetime.now(),
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            statistics=statistics,
            stage_metrics=stage_metrics,
            arena_metrics=arena_metrics,
            simulation_metrics=simulation_metrics,
            alerts=alerts,
            metadata={
                "total_alerts": len(alerts),
                "warning_alerts": len([a for a in alerts if a.alert_level == PerformanceAlertLevel.WARNING]),
                "error_alerts": len([a for a in alerts if a.alert_level == PerformanceAlertLevel.ERROR]),
            },
        )

        logger.info(
            f"生成性能分析报告 - "
            f"report_id={report.report_id}, "
            f"certifications={statistics.total_certifications}, "
            f"alerts={len(alerts)}"
        )

        return report

    def export_performance_report(self, report: PerformanceAnalysisReport, output_path: str) -> None:
        """导出性能分析报告

        Args:
            report: 性能分析报告
            output_path: 输出文件路径

        Raises:
            IOError: 当文件写入失败时
        """
        import json  # pylint: disable=import-outside-toplevel

        # 转换为可序列化的字典
        report_dict = {
            "report_id": report.report_id,
            "report_date": report.report_date.isoformat(),
            "time_range_start": report.time_range_start.isoformat(),
            "time_range_end": report.time_range_end.isoformat(),
            "statistics": {
                "total_certifications": report.statistics.total_certifications,
                "successful_certifications": report.statistics.successful_certifications,
                "failed_certifications": report.statistics.failed_certifications,
                "success_rate": report.statistics.success_rate,
                "failure_rate": report.statistics.failure_rate,
                "avg_duration_seconds": report.statistics.avg_duration_seconds,
                "level_distribution": report.statistics.level_distribution,
            },
            "stage_metrics": [
                {
                    "stage_name": m.stage_name,
                    "start_time": m.start_time.isoformat(),
                    "end_time": m.end_time.isoformat() if m.end_time else None,
                    "duration_seconds": m.duration_seconds,
                    "success": m.success,
                    "error_message": m.error_message,
                }
                for m in report.stage_metrics
            ],
            "arena_metrics": [
                {
                    "total_duration_seconds": m.total_duration_seconds,
                    "layer1_duration_seconds": m.layer1_duration_seconds,
                    "layer2_duration_seconds": m.layer2_duration_seconds,
                    "layer3_duration_seconds": m.layer3_duration_seconds,
                    "layer4_duration_seconds": m.layer4_duration_seconds,
                    "overall_score": m.overall_score,
                }
                for m in report.arena_metrics
            ],
            "simulation_metrics": [
                {
                    "cpu_usage_percent": m.cpu_usage_percent,
                    "memory_usage_mb": m.memory_usage_mb,
                    "disk_io_mb": m.disk_io_mb,
                    "network_io_mb": m.network_io_mb,
                    "peak_cpu_percent": m.peak_cpu_percent,
                    "peak_memory_mb": m.peak_memory_mb,
                }
                for m in report.simulation_metrics
            ],
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "alert_level": a.alert_level.value,
                    "alert_time": a.alert_time.isoformat(),
                    "stage_name": a.stage_name,
                    "metric_name": a.metric_name,
                    "actual_value": a.actual_value,
                    "threshold_value": a.threshold_value,
                    "message": a.message,
                }
                for a in report.alerts
            ],
            "metadata": report.metadata,
        }

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report_dict, f, ensure_ascii=False, indent=2)

            logger.info(f"性能分析报告已导出: {output_path}")

        except Exception as e:
            logger.error(f"导出性能分析报告失败: {e}")
            raise IOError(f"无法写入文件: {output_path}") from e

    def clear_history(self, days_to_keep: int = 30) -> None:
        """清理历史数据

        Args:
            days_to_keep: 保留天数
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        # 清理阶段指标
        self.stage_metrics_history = [m for m in self.stage_metrics_history if m.start_time >= cutoff_date]

        # 清理告警
        self.alerts_history = [a for a in self.alerts_history if a.alert_time >= cutoff_date]

        # 清理认证结果
        self.certification_results = [r for r in self.certification_results if r["timestamp"] >= cutoff_date]

        logger.info(f"清理{days_to_keep}天前的历史数据")
