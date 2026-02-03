"""Event Publisher for Sparta Evolution System

白皮书依据: 第四章 4.7 事件驱动通信
"""

from datetime import datetime
from typing import Any, Dict

from loguru import logger

from src.infra.event_bus import Event, EventBus, EventPriority, EventType


class EventPublisher:
    """事件发布器

    白皮书依据: 第四章 4.7 事件驱动通信

    为Sparta Evolution系统提供统一的事件发布接口。

    Attributes:
        event_bus: 事件总线实例
        source_module: 源模块名称
    """

    def __init__(self, event_bus: EventBus, source_module: str):
        """初始化事件发布器

        Args:
            event_bus: 事件总线实例
            source_module: 源模块名称

        Raises:
            ValueError: 当参数无效时
        """
        if not isinstance(event_bus, EventBus):
            raise TypeError(f"event_bus必须是EventBus类型，当前: {type(event_bus)}")

        if not source_module:
            raise ValueError("source_module不能为空")

        self.event_bus = event_bus
        self.source_module = source_module

        logger.info(f"初始化EventPublisher: source_module={source_module}")

    async def publish_factor_arena_completed(
        self, factor_id: str, arena_score: float, passed: bool, detailed_metrics: Dict[str, Any]
    ) -> bool:
        """发布因子Arena测试完成事件

        白皮书依据: 第四章 4.7.1 因子Arena完成事件 - Requirement 9.1

        Args:
            factor_id: 因子ID
            arena_score: Arena评分
            passed: 是否通过
            detailed_metrics: 详细指标

        Returns:
            是否成功发布
        """
        event = Event(
            event_type=EventType.FACTOR_ARENA_COMPLETED,
            source_module=self.source_module,
            priority=EventPriority.HIGH,
            data={
                "factor_id": factor_id,
                "arena_score": arena_score,
                "passed": passed,
                "detailed_metrics": detailed_metrics,
                "timestamp": datetime.now().isoformat(),
            },
        )

        result = await self.event_bus.publish(event)

        if result:
            logger.info(
                f"发布因子Arena完成事件: "
                f"factor_id={factor_id}, "
                f"arena_score={arena_score:.4f}, "
                f"passed={passed}"
            )

        return result

    async def publish_strategy_arena_completed(
        self, strategy_id: str, arena_score: float, passed: bool, performance_metrics: Dict[str, Any]
    ) -> bool:
        """发布策略Arena测试完成事件

        白皮书依据: 第四章 4.7.2 策略Arena完成事件 - Requirement 9.2

        Args:
            strategy_id: 策略ID
            arena_score: Arena评分
            passed: 是否通过
            performance_metrics: 性能指标

        Returns:
            是否成功发布
        """
        event = Event(
            event_type=EventType.STRATEGY_ARENA_COMPLETED,
            source_module=self.source_module,
            priority=EventPriority.HIGH,
            data={
                "strategy_id": strategy_id,
                "arena_score": arena_score,
                "passed": passed,
                "performance_metrics": performance_metrics,
                "timestamp": datetime.now().isoformat(),
            },
        )

        result = await self.event_bus.publish(event)

        if result:
            logger.info(
                f"发布策略Arena完成事件: "
                f"strategy_id={strategy_id}, "
                f"arena_score={arena_score:.4f}, "
                f"passed={passed}"
            )

        return result

    async def publish_simulation_completed(
        self, strategy_id: str, duration_days: int, passed: bool, final_metrics: Dict[str, Any]
    ) -> bool:
        """发布模拟验证完成事件

        白皮书依据: 第四章 4.7.3 模拟验证完成事件 - Requirement 9.3

        Args:
            strategy_id: 策略ID
            duration_days: 模拟天数
            passed: 是否通过
            final_metrics: 最终指标

        Returns:
            是否成功发布
        """
        event = Event(
            event_type=EventType.SIMULATION_COMPLETED,
            source_module=self.source_module,
            priority=EventPriority.HIGH,
            data={
                "strategy_id": strategy_id,
                "duration_days": duration_days,
                "passed": passed,
                "final_metrics": final_metrics,
                "timestamp": datetime.now().isoformat(),
            },
        )

        result = await self.event_bus.publish(event)

        if result:
            logger.info(
                f"发布模拟验证完成事件: "
                f"strategy_id={strategy_id}, "
                f"duration_days={duration_days}, "
                f"passed={passed}"
            )

        return result

    async def publish_z2h_certified(
        self, strategy_id: str, certification_level: str, capsule_id: str, metrics: Dict[str, Any]
    ) -> bool:
        """发布Z2H认证事件

        白皮书依据: 第四章 4.7.4 Z2H认证事件 - Requirement 9.4

        Args:
            strategy_id: 策略ID
            certification_level: 认证级别
            capsule_id: 胶囊ID
            metrics: 指标

        Returns:
            是否成功发布
        """
        event = Event(
            event_type=EventType.Z2H_CERTIFIED,
            source_module=self.source_module,
            priority=EventPriority.CRITICAL,
            data={
                "strategy_id": strategy_id,
                "certification_level": certification_level,
                "capsule_id": capsule_id,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat(),
            },
        )

        result = await self.event_bus.publish(event)

        if result:
            logger.info(
                f"发布Z2H认证事件: "
                f"strategy_id={strategy_id}, "
                f"certification_level={certification_level}, "
                f"capsule_id={capsule_id}"
            )

        return result

    async def publish_factor_decay_detected(  # pylint: disable=too-many-positional-arguments
        self, factor_id: str, severity: str, consecutive_days: int, recommended_action: str, current_ic: float
    ) -> bool:
        """发布因子衰减检测事件

        白皮书依据: 第四章 4.7.5 因子衰减检测事件 - Requirement 9.5

        Args:
            factor_id: 因子ID
            severity: 严重程度
            consecutive_days: 连续天数
            recommended_action: 推荐动作
            current_ic: 当前IC

        Returns:
            是否成功发布
        """
        event = Event(
            event_type=EventType.FACTOR_DECAY_DETECTED,
            source_module=self.source_module,
            priority=EventPriority.HIGH,
            data={
                "factor_id": factor_id,
                "severity": severity,
                "consecutive_days": consecutive_days,
                "recommended_action": recommended_action,
                "current_ic": current_ic,
                "timestamp": datetime.now().isoformat(),
            },
        )

        result = await self.event_bus.publish(event)

        if result:
            logger.warning(
                f"发布因子衰减检测事件: "
                f"factor_id={factor_id}, "
                f"severity={severity}, "
                f"consecutive_days={consecutive_days}, "
                f"recommended_action={recommended_action}"
            )

        return result

    async def publish_strategy_retired(self, strategy_id: str, reason: str, final_metrics: Dict[str, Any]) -> bool:
        """发布策略退役事件

        白皮书依据: 第四章 4.7.6 策略退役事件 - Requirement 9.6

        Args:
            strategy_id: 策略ID
            reason: 退役原因
            final_metrics: 最终指标

        Returns:
            是否成功发布
        """
        event = Event(
            event_type=EventType.STRATEGY_RETIRED,
            source_module=self.source_module,
            priority=EventPriority.HIGH,
            data={
                "strategy_id": strategy_id,
                "reason": reason,
                "final_metrics": final_metrics,
                "timestamp": datetime.now().isoformat(),
            },
        )

        result = await self.event_bus.publish(event)

        if result:
            logger.warning(f"发布策略退役事件: " f"strategy_id={strategy_id}, " f"reason={reason}")

        return result
