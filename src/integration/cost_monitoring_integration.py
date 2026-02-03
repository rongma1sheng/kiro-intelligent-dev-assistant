"""Cost Monitoring Integration - 成本追踪与监控集成

白皮书依据: 第十八章 18.2 成本监控与追踪, 第十二章 12.3 成本追踪与监控集成
版本: v1.0.0
作者: MIA Team
日期: 2026-01-27

核心功能:
1. 集成成本追踪器与Prometheus指标采集
2. 发布成本指标到Prometheus
3. 发布跨章节事件通知成本问题
4. 自动化成本监控和告警
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

from src.infra.cross_chapter_event_bus import CrossChapterEvent, CrossChapterEventBus, CrossChapterEventType
from src.infra.event_bus import EventPriority
from src.monitoring.cost_predictor import CostPredictor
from src.monitoring.cost_tracker import CostTracker
from src.monitoring.prometheus_collector import MetricType, PrometheusMetricsCollector


@dataclass
class CostMonitoringStatus:
    """成本监控状态

    白皮书依据: 第十八章 18.2 成本监控与追踪

    Attributes:
        daily_cost: 今日成本
        monthly_cost: 本月成本
        predicted_monthly: 预测月成本
        daily_budget_utilization: 日预算使用率
        monthly_budget_utilization: 月预算使用率
        is_daily_exceeded: 日预算是否超限
        is_monthly_exceeded: 月预算是否超限
        timestamp: 状态时间戳
    """

    daily_cost: float
    monthly_cost: float
    predicted_monthly: float
    daily_budget_utilization: float
    monthly_budget_utilization: float
    is_daily_exceeded: bool
    is_monthly_exceeded: bool
    timestamp: datetime


class CostMonitoringIntegration:
    """成本追踪与监控集成

    白皮书依据: 第十八章 18.2 成本监控与追踪, 第十二章 12.3 成本追踪与监控集成

    核心功能:
    1. 集成成本追踪器与Prometheus
    2. 发布成本指标到Prometheus
    3. 发布跨章节事件（成本告警）
    4. 自动化成本监控

    集成流程:
    1. 成本追踪器记录API调用成本
    2. 定期同步成本数据到Prometheus
    3. 检测预算超限
    4. 发布跨章节事件通知熔断器

    使用示例:
        >>> integration = CostMonitoringIntegration(
        ...     cost_tracker=cost_tracker,
        ...     prometheus_collector=prometheus_collector,
        ...     event_bus=cross_chapter_bus
        ... )
        >>> await integration.initialize()
        >>>
        >>> # 追踪API调用并自动同步到Prometheus
        >>> await integration.track_and_publish(
        ...     service='soldier',
        ...     model='deepseek-chat',
        ...     input_tokens=1000,
        ...     output_tokens=500
        ... )
    """

    def __init__(
        self,
        cost_tracker: CostTracker,
        prometheus_collector: PrometheusMetricsCollector,
        event_bus: Optional[CrossChapterEventBus] = None,
        sync_interval: int = 60,
    ):
        """初始化成本监控集成

        Args:
            cost_tracker: 成本追踪器实例
            prometheus_collector: Prometheus指标采集器实例
            event_bus: 跨章节事件总线实例
            sync_interval: 同步间隔（秒），默认60秒

        Raises:
            ValueError: 当参数无效时
        """
        if cost_tracker is None:
            raise ValueError("cost_tracker不能为None")

        if prometheus_collector is None:
            raise ValueError("prometheus_collector不能为None")

        if sync_interval < 1:
            raise ValueError(f"同步间隔必须 >= 1秒: {sync_interval}")

        self.cost_tracker = cost_tracker
        self.prometheus_collector = prometheus_collector
        self.event_bus = event_bus
        self.sync_interval = sync_interval

        # 初始化成本预测器
        self.cost_predictor = CostPredictor(cost_tracker)

        # 统计信息
        self.stats = {
            "total_tracked": 0,
            "total_synced": 0,
            "events_published": 0,
            "budget_alerts": 0,
            "start_time": None,
        }

        # 注册成本指标到Prometheus
        self._register_cost_metrics()

        logger.info(f"成本监控集成初始化完成: sync_interval={sync_interval}s")

    def _register_cost_metrics(self):
        """注册成本指标到Prometheus

        白皮书依据: 第十三章 13.1 Prometheus指标埋点
        """
        try:
            # 成本指标
            self.prometheus_collector.register_custom_metric(
                name="mia_cost_daily_total", description="Daily total cost in CNY", metric_type=MetricType.GAUGE
            )

            self.prometheus_collector.register_custom_metric(
                name="mia_cost_monthly_total", description="Monthly total cost in CNY", metric_type=MetricType.GAUGE
            )

            self.prometheus_collector.register_custom_metric(
                name="mia_cost_predicted_monthly",
                description="Predicted monthly cost in CNY",
                metric_type=MetricType.GAUGE,
            )

            self.prometheus_collector.register_custom_metric(
                name="mia_cost_by_service",
                description="Cost by service in CNY",
                metric_type=MetricType.GAUGE,
                labels=["service"],
            )

            self.prometheus_collector.register_custom_metric(
                name="mia_cost_daily_budget_utilization",
                description="Daily budget utilization ratio",
                metric_type=MetricType.GAUGE,
            )

            self.prometheus_collector.register_custom_metric(
                name="mia_cost_monthly_budget_utilization",
                description="Monthly budget utilization ratio",
                metric_type=MetricType.GAUGE,
            )

            self.prometheus_collector.register_custom_metric(
                name="mia_cost_api_calls_total",
                description="Total API calls tracked",
                metric_type=MetricType.COUNTER,
                labels=["service", "model"],
            )

            self.prometheus_collector.register_custom_metric(
                name="mia_cost_budget_exceeded",
                description="Budget exceeded flag (0=no, 1=yes)",
                metric_type=MetricType.GAUGE,
                labels=["budget_type"],
            )

            logger.info("成本指标已注册到Prometheus")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"注册成本指标失败: {e}")

    async def initialize(self):
        """初始化集成模块"""
        try:
            # 如果没有提供事件总线，获取全局实例
            if self.event_bus is None:
                from src.infra.cross_chapter_event_bus import (  # pylint: disable=import-outside-toplevel
                    get_cross_chapter_event_bus,
                )

                self.event_bus = await get_cross_chapter_event_bus()

            self.stats["start_time"] = datetime.now()

            # 初始同步
            await self.sync_cost_metrics()

            logger.info("成本监控集成启动成功")

        except Exception as e:
            logger.error(f"成本监控集成初始化失败: {e}")
            raise

    async def track_and_publish(self, service: str, model: str, input_tokens: int, output_tokens: int) -> float:
        """追踪API调用并发布到Prometheus

        白皮书依据: 第十八章 18.2.1 实时监控

        Args:
            service: 服务名称
            model: 模型名称
            input_tokens: 输入token数
            output_tokens: 输出token数

        Returns:
            本次调用成本（CNY）
        """
        # 追踪成本
        cost = self.cost_tracker.track_api_call(
            service=service, model=model, input_tokens=input_tokens, output_tokens=output_tokens
        )

        self.stats["total_tracked"] += 1

        # 更新Prometheus指标
        api_calls_metric = self.prometheus_collector.get_metric("mia_cost_api_calls_total")
        if api_calls_metric:
            api_calls_metric.labels(service=service, model=model).inc()

        # 同步成本指标
        await self.sync_cost_metrics()

        # 检查预算超限
        await self._check_budget_limits()

        return cost

    async def sync_cost_metrics(self):
        """同步成本指标到Prometheus

        白皮书依据: 第十三章 13.1.2 指标采集器
        """
        try:
            # 获取预算状态
            budget_status = self.cost_tracker.get_budget_status()

            # 获取成本预测
            prediction = self.cost_predictor.predict_monthly_cost()

            # 获取成本分解
            cost_breakdown = self.cost_tracker.get_cost_breakdown()

            # 更新日成本
            daily_cost_metric = self.prometheus_collector.get_metric("mia_cost_daily_total")
            if daily_cost_metric:
                daily_cost_metric.set(budget_status["daily_cost"])

            # 更新月成本
            monthly_cost_metric = self.prometheus_collector.get_metric("mia_cost_monthly_total")
            if monthly_cost_metric:
                monthly_cost_metric.set(budget_status["monthly_cost"])

            # 更新预测月成本
            predicted_metric = self.prometheus_collector.get_metric("mia_cost_predicted_monthly")
            if predicted_metric:
                predicted_metric.set(prediction["predicted_monthly"])

            # 更新服务成本
            service_cost_metric = self.prometheus_collector.get_metric("mia_cost_by_service")
            if service_cost_metric:
                for service, cost in cost_breakdown.items():
                    service_cost_metric.labels(service=service).set(cost)

            # 更新预算使用率
            daily_util_metric = self.prometheus_collector.get_metric("mia_cost_daily_budget_utilization")
            if daily_util_metric:
                daily_util_metric.set(budget_status["daily_utilization"])

            monthly_util_metric = self.prometheus_collector.get_metric("mia_cost_monthly_budget_utilization")
            if monthly_util_metric:
                monthly_util_metric.set(budget_status["monthly_utilization"])

            # 更新预算超限标志
            exceeded_metric = self.prometheus_collector.get_metric("mia_cost_budget_exceeded")
            if exceeded_metric:
                exceeded_metric.labels(budget_type="daily").set(1 if budget_status["is_daily_exceeded"] else 0)
                exceeded_metric.labels(budget_type="monthly").set(1 if budget_status["is_monthly_exceeded"] else 0)

            self.stats["total_synced"] += 1

            logger.debug(
                f"成本指标已同步到Prometheus: "
                f"日成本=¥{budget_status['daily_cost']:.2f}, "
                f"月成本=¥{budget_status['monthly_cost']:.2f}"
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"同步成本指标失败: {e}")

    async def _check_budget_limits(self):
        """检查预算限制并发布事件

        白皮书依据: 第十二章 12.3 成本追踪与监控集成
        """
        try:
            budget_status = self.cost_tracker.get_budget_status()

            # 检查日预算超限
            if budget_status["is_daily_exceeded"]:
                await self._publish_cost_limit_exceeded_event(
                    limit_type="daily",
                    current_cost=budget_status["daily_cost"],
                    budget=budget_status["daily_budget"],
                    utilization=budget_status["daily_utilization"],
                )

            # 检查月预算超限
            if budget_status["is_monthly_exceeded"]:
                await self._publish_cost_limit_exceeded_event(
                    limit_type="monthly",
                    current_cost=budget_status["monthly_cost"],
                    budget=budget_status["monthly_budget"],
                    utilization=budget_status["monthly_utilization"],
                )

            # 检查预测超限
            alert = self.cost_predictor.alert_if_over_budget()
            if alert:
                await self._publish_cost_budget_warning_event(alert)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"检查预算限制失败: {e}")

    async def _publish_cost_limit_exceeded_event(
        self, limit_type: str, current_cost: float, budget: float, utilization: float
    ):
        """发布成本限制超限事件

        白皮书依据: 第十二章 12.3 成本追踪与监控集成

        事件路由: Chapter 18 (Cost) -> Chapter 13 (Monitoring)

        Args:
            limit_type: 限制类型（daily/monthly）
            current_cost: 当前成本
            budget: 预算
            utilization: 使用率
        """
        try:
            if self.event_bus is None:
                logger.warning("事件总线未初始化，跳过事件发布")
                return

            event = CrossChapterEvent(
                event_type=CrossChapterEventType.COST_LIMIT_EXCEEDED,
                source_chapter=18,
                target_chapter=13,
                data={
                    "limit_type": limit_type,
                    "current_cost": current_cost,
                    "budget": budget,
                    "utilization": utilization,
                    "excess_amount": current_cost - budget,
                    "timestamp": datetime.now().isoformat(),
                },
                priority=EventPriority.HIGH,
            )

            success = await self.event_bus.publish(event)

            if success:
                self.stats["events_published"] += 1
                self.stats["budget_alerts"] += 1
                logger.warning(
                    f"成本限制超限事件已发布 (Chapter 18 -> 13): " f"{limit_type} ¥{current_cost:.2f} > ¥{budget:.2f}"
                )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"发布成本限制超限事件失败: {e}")

    async def _publish_cost_budget_warning_event(self, alert: Dict[str, Any]):
        """发布成本预算警告事件

        白皮书依据: 第十二章 12.3 成本追踪与监控集成

        事件路由: Chapter 18 (Cost) -> Chapter 13 (Monitoring)

        Args:
            alert: 告警信息字典
        """
        try:
            if self.event_bus is None:
                logger.warning("事件总线未初始化，跳过事件发布")
                return

            event = CrossChapterEvent(
                event_type=CrossChapterEventType.COST_BUDGET_WARNING,
                source_chapter=18,
                target_chapter=13,
                data={
                    "predicted_monthly": alert["predicted_monthly"],
                    "budget_monthly": alert["budget_monthly"],
                    "excess_amount": alert["excess_amount"],
                    "budget_utilization": alert["budget_utilization"],
                    "message": alert["message"],
                    "timestamp": datetime.now().isoformat(),
                },
                priority=EventPriority.NORMAL,
            )

            success = await self.event_bus.publish(event)

            if success:
                self.stats["events_published"] += 1
                logger.warning(f"成本预算警告事件已发布 (Chapter 18 -> 13): " f"{alert['message']}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"发布成本预算警告事件失败: {e}")

    async def get_monitoring_status(self) -> CostMonitoringStatus:
        """获取成本监控状态

        Returns:
            成本监控状态
        """
        budget_status = self.cost_tracker.get_budget_status()
        prediction = self.cost_predictor.predict_monthly_cost()

        return CostMonitoringStatus(
            daily_cost=budget_status["daily_cost"],
            monthly_cost=budget_status["monthly_cost"],
            predicted_monthly=prediction["predicted_monthly"],
            daily_budget_utilization=budget_status["daily_utilization"],
            monthly_budget_utilization=budget_status["monthly_utilization"],
            is_daily_exceeded=budget_status["is_daily_exceeded"],
            is_monthly_exceeded=budget_status["is_monthly_exceeded"],
            timestamp=datetime.now(),
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds() if self.stats["start_time"] else 0

        return {
            **self.stats,
            "uptime_seconds": uptime,
            "tracking_rate": self.stats["total_tracked"] / max(uptime, 1),
            "sync_rate": self.stats["total_synced"] / max(uptime, 1),
        }


# 全局集成实例
_global_cost_monitoring_integration: Optional[CostMonitoringIntegration] = None


async def get_cost_monitoring_integration(
    cost_tracker: Optional[CostTracker] = None,
    prometheus_collector: Optional[PrometheusMetricsCollector] = None,
    event_bus: Optional[CrossChapterEventBus] = None,
) -> CostMonitoringIntegration:
    """获取全局成本监控集成实例

    Args:
        cost_tracker: 成本追踪器实例
        prometheus_collector: Prometheus指标采集器实例
        event_bus: 跨章节事件总线实例

    Returns:
        成本监控集成实例
    """
    global _global_cost_monitoring_integration  # pylint: disable=w0603

    if _global_cost_monitoring_integration is None:
        if cost_tracker is None or prometheus_collector is None:
            raise ValueError("首次调用必须提供cost_tracker和prometheus_collector")

        _global_cost_monitoring_integration = CostMonitoringIntegration(
            cost_tracker=cost_tracker, prometheus_collector=prometheus_collector, event_bus=event_bus
        )
        await _global_cost_monitoring_integration.initialize()

    return _global_cost_monitoring_integration


async def track_api_cost(service: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """全局API成本追踪函数

    Args:
        service: 服务名称
        model: 模型名称
        input_tokens: 输入token数
        output_tokens: 输出token数

    Returns:
        本次调用成本（CNY）
    """
    integration = await get_cost_monitoring_integration()
    return await integration.track_and_publish(
        service=service, model=model, input_tokens=input_tokens, output_tokens=output_tokens
    )
