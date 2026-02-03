"""Monitoring and Reliability Integration - 监控与可靠性集成

白皮书依据: 第十二章 12.1 跨章节集成 - 监控与可靠性

核心功能:
1. 连接Prometheus指标采集器与健康检查器
2. 健康检查失败时发布跨章节事件
3. 将健康检查结果暴露为Prometheus指标
4. 自动触发告警和应急响应
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

from src.core.health_checker import ComponentStatus, HealthChecker, OverallStatus
from src.infra.cross_chapter_event_bus import CrossChapterEvent, CrossChapterEventBus, CrossChapterEventType
from src.infra.event_bus import EventPriority
from src.monitoring.prometheus_collector import PrometheusMetricsCollector


class MonitoringReliabilityIntegration:
    """监控与可靠性集成器

    白皮书依据: 第十二章 12.1 监控与可靠性集成

    功能:
    1. 将健康检查结果暴露为Prometheus指标
    2. 健康检查失败时发布跨章节事件到告警系统
    3. 自动触发Redis恢复流程
    4. 协调监控和可靠性系统

    Attributes:
        prometheus_collector: Prometheus指标采集器
        health_checker: 健康检查器
        cross_chapter_bus: 跨章节事件总线
        running: 运行状态
    """

    def __init__(
        self,
        prometheus_collector: PrometheusMetricsCollector,
        health_checker: HealthChecker,
        cross_chapter_bus: CrossChapterEventBus,
    ):
        """初始化监控与可靠性集成器

        Args:
            prometheus_collector: Prometheus指标采集器实例
            health_checker: 健康检查器实例
            cross_chapter_bus: 跨章节事件总线实例
        """
        self.prometheus_collector = prometheus_collector
        self.health_checker = health_checker
        self.cross_chapter_bus = cross_chapter_bus

        self.running = False
        self._integration_task: Optional[asyncio.Task] = None

        # 统计信息
        self.stats = {
            "health_checks_performed": 0,
            "events_published": 0,
            "redis_recoveries_attempted": 0,
            "redis_recoveries_succeeded": 0,
            "start_time": None,
        }

        # 注册健康检查指标
        self._register_health_metrics()

        logger.info("监控与可靠性集成器初始化完成")

    def _register_health_metrics(self):
        """注册健康检查相关的Prometheus指标"""
        try:
            from src.monitoring.prometheus_collector import MetricType  # pylint: disable=import-outside-toplevel

            # 整体健康状态指标
            self.prometheus_collector.register_custom_metric(
                name="mia_system_health_status",
                description="Overall system health status (0=healthy, 1=degraded, 2=unhealthy, 3=critical)",
                metric_type=MetricType.GAUGE,
            )

            # 组件健康状态指标
            self.prometheus_collector.register_custom_metric(
                name="mia_component_health_status",
                description="Component health status (0=healthy, 1=degraded, 2=unhealthy)",
                metric_type=MetricType.GAUGE,
                labels=["component"],
            )

            # 健康检查执行次数
            self.prometheus_collector.register_custom_metric(
                name="mia_health_checks_total",
                description="Total number of health checks performed",
                metric_type=MetricType.COUNTER,
            )

            # Redis恢复尝试次数
            self.prometheus_collector.register_custom_metric(
                name="mia_redis_recovery_attempts_total",
                description="Total number of Redis recovery attempts",
                metric_type=MetricType.COUNTER,
            )

            # Redis恢复成功次数
            self.prometheus_collector.register_custom_metric(
                name="mia_redis_recovery_success_total",
                description="Total number of successful Redis recoveries",
                metric_type=MetricType.COUNTER,
            )

            logger.info("健康检查指标注册完成")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"注册健康检查指标失败: {e}")

    async def start(self):
        """启动集成器"""
        if self.running:
            logger.warning("集成器已经在运行")
            return

        self.running = True
        self.stats["start_time"] = datetime.now()

        # 启动集成循环
        self._integration_task = asyncio.create_task(self._integration_loop())

        logger.info("监控与可靠性集成器已启动")

    async def stop(self):
        """停止集成器"""
        if not self.running:
            logger.warning("集成器未在运行")
            return

        self.running = False

        if self._integration_task:
            self._integration_task.cancel()
            try:
                await self._integration_task
            except asyncio.CancelledError:
                pass

        logger.info("监控与可靠性集成器已停止")

    async def _integration_loop(self):
        """集成主循环

        白皮书依据: 第十二章 12.1 监控与可靠性集成

        每30秒执行一次健康检查，并将结果同步到Prometheus和事件总线
        """
        logger.info("集成循环已启动")

        while self.running:
            try:
                # 执行健康检查
                health_result = self.health_checker.run_health_check()
                self.stats["health_checks_performed"] += 1

                # 更新Prometheus指标
                await self._update_health_metrics(health_result)

                # 处理健康检查结果
                await self._handle_health_result(health_result)

                # 等待下一次检查
                await asyncio.sleep(self.health_checker.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"集成循环异常: {e}")
                await asyncio.sleep(self.health_checker.check_interval)

        logger.info("集成循环已停止")

    async def _update_health_metrics(self, health_result):
        """更新健康检查相关的Prometheus指标

        Args:
            health_result: 健康检查结果
        """
        try:
            # 更新整体健康状态
            overall_status_metric = self.prometheus_collector.get_metric("mia_system_health_status")
            if overall_status_metric:
                status_value = self._health_status_to_value(health_result.overall_status)
                overall_status_metric.set(status_value)

            # 更新组件健康状态
            component_status_metric = self.prometheus_collector.get_metric("mia_component_health_status")
            if component_status_metric:
                for component_name, component_health in health_result.components.items():
                    status_value = self._component_status_to_value(component_health.status)
                    component_status_metric.labels(component=component_name).set(status_value)

            # 更新健康检查计数
            health_checks_metric = self.prometheus_collector.get_metric("mia_health_checks_total")
            if health_checks_metric:
                health_checks_metric.inc()

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"更新健康指标失败: {e}")

    async def _handle_health_result(self, health_result):
        """处理健康检查结果

        白皮书依据: 第十二章 12.1 监控与可靠性集成

        Args:
            health_result: 健康检查结果
        """
        # 检查Redis健康状态
        redis_health = health_result.components.get("redis")
        if redis_health and redis_health.status == ComponentStatus.UNHEALTHY:
            await self._handle_redis_failure(redis_health)

        # 检查整体健康状态
        if health_result.overall_status in [OverallStatus.UNHEALTHY, OverallStatus.CRITICAL]:
            await self._publish_health_check_failed_event(health_result)
        elif health_result.overall_status == OverallStatus.DEGRADED:
            await self._publish_performance_degradation_event(health_result)

    async def _handle_redis_failure(self, redis_health):
        """处理Redis失败

        白皮书依据: 第十章 10.2 Redis恢复

        Args:
            redis_health: Redis健康状态
        """
        logger.warning(f"检测到Redis失败: {redis_health.message}")

        # 更新统计
        self.stats["redis_recoveries_attempted"] += 1

        # 更新Prometheus指标
        recovery_attempts_metric = self.prometheus_collector.get_metric("mia_redis_recovery_attempts_total")
        if recovery_attempts_metric:
            recovery_attempts_metric.inc()

        # 尝试恢复Redis
        logger.info("开始Redis恢复流程")
        recovery_success = self.health_checker.attempt_redis_recovery()

        if recovery_success:
            logger.info("Redis恢复成功")
            self.stats["redis_recoveries_succeeded"] += 1

            # 更新Prometheus指标
            recovery_success_metric = self.prometheus_collector.get_metric("mia_redis_recovery_success_total")
            if recovery_success_metric:
                recovery_success_metric.inc()

            # 发布恢复成功事件
            await self._publish_health_check_recovered_event("redis")
        else:
            logger.error("Redis恢复失败")

            # 发布Redis失败事件到告警系统
            await self.cross_chapter_bus.publish(
                CrossChapterEvent(
                    event_type=CrossChapterEventType.HEALTH_CHECK_FAILED,
                    source_chapter=10,
                    target_chapter=13,
                    data={
                        "component": "redis",
                        "status": "unhealthy",
                        "message": redis_health.message,
                        "recovery_attempted": True,
                        "recovery_success": False,
                    },
                    priority=EventPriority.HIGH,
                )
            )
            self.stats["events_published"] += 1

    async def _publish_health_check_failed_event(self, health_result):
        """发布健康检查失败事件

        白皮书依据: 第十二章 12.1 监控与可靠性集成

        Args:
            health_result: 健康检查结果
        """
        # 收集失败的组件
        failed_components = [
            name for name, health in health_result.components.items() if health.status == ComponentStatus.UNHEALTHY
        ]

        # 发布事件到告警系统（Chapter 13）
        await self.cross_chapter_bus.publish(
            CrossChapterEvent(
                event_type=CrossChapterEventType.HEALTH_CHECK_FAILED,
                source_chapter=10,
                target_chapter=13,
                data={
                    "overall_status": health_result.overall_status.value,
                    "failed_components": failed_components,
                    "timestamp": health_result.timestamp.isoformat(),
                    "components_detail": {
                        name: {"status": health.status.value, "message": health.message, "metrics": health.metrics}
                        for name, health in health_result.components.items()
                    },
                },
                priority=(
                    EventPriority.CRITICAL
                    if health_result.overall_status == OverallStatus.CRITICAL
                    else EventPriority.HIGH
                ),
            )
        )

        self.stats["events_published"] += 1

        logger.warning(
            f"已发布健康检查失败事件: " f"状态={health_result.overall_status.value}, " f"失败组件={failed_components}"
        )

    async def _publish_performance_degradation_event(self, health_result):
        """发布性能下降事件

        Args:
            health_result: 健康检查结果
        """
        # 收集降级的组件
        degraded_components = [
            name for name, health in health_result.components.items() if health.status == ComponentStatus.DEGRADED
        ]

        # 发布事件到监控系统（Chapter 13）
        await self.cross_chapter_bus.publish(
            CrossChapterEvent(
                event_type=CrossChapterEventType.PERFORMANCE_DEGRADATION,
                source_chapter=10,
                target_chapter=13,
                data={
                    "overall_status": health_result.overall_status.value,
                    "degraded_components": degraded_components,
                    "timestamp": health_result.timestamp.isoformat(),
                },
                priority=EventPriority.NORMAL,
            )
        )

        self.stats["events_published"] += 1

        logger.info(f"已发布性能下降事件: 降级组件={degraded_components}")

    async def _publish_health_check_recovered_event(self, component: str):
        """发布健康检查恢复事件

        Args:
            component: 恢复的组件名称
        """
        await self.cross_chapter_bus.publish(
            CrossChapterEvent(
                event_type=CrossChapterEventType.HEALTH_CHECK_RECOVERED,
                source_chapter=10,
                target_chapter=13,
                data={"component": component, "timestamp": datetime.now().isoformat()},
                priority=EventPriority.NORMAL,
            )
        )

        self.stats["events_published"] += 1

        logger.info(f"已发布健康检查恢复事件: 组件={component}")

    def _health_status_to_value(self, status: OverallStatus) -> float:
        """将整体健康状态转换为数值

        Args:
            status: 整体健康状态

        Returns:
            数值表示 (0=healthy, 1=degraded, 2=unhealthy, 3=critical)
        """
        mapping = {
            OverallStatus.HEALTHY: 0.0,
            OverallStatus.DEGRADED: 1.0,
            OverallStatus.UNHEALTHY: 2.0,
            OverallStatus.CRITICAL: 3.0,
        }
        return mapping.get(status, 2.0)

    def _component_status_to_value(self, status: ComponentStatus) -> float:
        """将组件健康状态转换为数值

        Args:
            status: 组件健康状态

        Returns:
            数值表示 (0=healthy, 1=degraded, 2=unhealthy)
        """
        mapping = {ComponentStatus.HEALTHY: 0.0, ComponentStatus.DEGRADED: 1.0, ComponentStatus.UNHEALTHY: 2.0}
        return mapping.get(status, 2.0)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds() if self.stats["start_time"] else 0

        return {
            **self.stats,
            "uptime_seconds": uptime,
            "redis_recovery_success_rate": (
                self.stats["redis_recoveries_succeeded"] / max(self.stats["redis_recoveries_attempted"], 1)
            ),
        }


async def create_monitoring_reliability_integration(
    prometheus_collector: PrometheusMetricsCollector,
    health_checker: HealthChecker,
    cross_chapter_bus: CrossChapterEventBus,
) -> MonitoringReliabilityIntegration:
    """创建监控与可靠性集成器

    Args:
        prometheus_collector: Prometheus指标采集器
        health_checker: 健康检查器
        cross_chapter_bus: 跨章节事件总线

    Returns:
        监控与可靠性集成器实例
    """
    integration = MonitoringReliabilityIntegration(
        prometheus_collector=prometheus_collector, health_checker=health_checker, cross_chapter_bus=cross_chapter_bus
    )

    await integration.start()

    return integration
