"""Cross-Chapter Event Bus - 跨章节事件总线

白皮书依据: 第十二章 12.1-12.10 跨章节集成
版本: v1.0.0
作者: MIA Team
日期: 2026-01-27

核心功能:
1. 章节间事件路由
2. 监控与可靠性集成
3. 测试与CI/CD集成
4. 成本跟踪与监控集成
5. 风险管理与应急响应集成
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from src.infra.event_bus import Event, EventBus, EventPriority, EventType


class CrossChapterEventType(Enum):
    """跨章节事件类型

    白皮书依据: 第十二章 12.1-12.10 跨章节集成
    """

    # Chapter 10 -> Chapter 13: 健康检查 -> 监控告警
    HEALTH_CHECK_FAILED = "health_check_failed"
    HEALTH_CHECK_RECOVERED = "health_check_recovered"

    # Chapter 13 -> Chapter 19: 监控告警 -> 应急响应
    MONITORING_ALERT = "monitoring_alert"
    PERFORMANCE_DEGRADATION = "performance_degradation"

    # Chapter 18 -> Chapter 13: 成本限制 -> 熔断器
    COST_LIMIT_EXCEEDED = "cost_limit_exceeded"
    COST_BUDGET_WARNING = "cost_budget_warning"

    # Chapter 19 -> Chapter 13: 风险检测 -> 告警系统
    RISK_LEVEL_CHANGED = "risk_level_changed"
    EMERGENCY_TRIGGERED = "emergency_triggered"

    # Chapter 12 -> Chapter 19: 末日开关 -> 应急程序
    DOOMSDAY_TRIGGERED = "doomsday_triggered"
    DOOMSDAY_RESET = "doomsday_reset"

    # Chapter 16 -> Chapter 13: 性能回归 -> 告警
    PERFORMANCE_REGRESSION_DETECTED = "performance_regression_detected"

    # Chapter 14 -> Chapter 17: 测试覆盖率 -> CI/CD
    COVERAGE_GATE_FAILED = "coverage_gate_failed"
    QUALITY_CHECK_FAILED = "quality_check_failed"


@dataclass
class CrossChapterEvent:
    """跨章节事件

    白皮书依据: 第十二章 12.1 跨章节事件定义

    Attributes:
        event_type: 事件类型
        source_chapter: 源章节编号
        target_chapter: 目标章节编号
        data: 事件数据
        priority: 事件优先级
        created_at: 创建时间
    """

    event_type: CrossChapterEventType
    source_chapter: int
    target_chapter: int
    data: Dict[str, Any]
    priority: EventPriority = EventPriority.NORMAL
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_base_event(self) -> Event:
        """转换为基础事件对象"""
        return Event(
            event_type=EventType.SYSTEM_ALERT,  # 使用系统告警类型
            source_module=f"chapter_{self.source_chapter}",
            target_module=f"chapter_{self.target_chapter}",
            priority=self.priority,
            data={"cross_chapter_event_type": self.event_type.value, **self.data},
            metadata={
                "source_chapter": self.source_chapter,
                "target_chapter": self.target_chapter,
                "is_cross_chapter": True,
            },
        )


class CrossChapterEventBus:
    """跨章节事件总线

    白皮书依据: 第十二章 12.1-12.10 跨章节集成

    核心功能:
    1. 章节间事件路由
    2. 事件转换和适配
    3. 跨章节流程编排
    4. 事件追踪和审计

    使用示例:
        >>> bus = CrossChapterEventBus(base_event_bus)
        >>> await bus.initialize()
        >>>
        >>> # 发布跨章节事件
        >>> event = CrossChapterEvent(
        ...     event_type=CrossChapterEventType.HEALTH_CHECK_FAILED,
        ...     source_chapter=10,
        ...     target_chapter=13,
        ...     data={'component': 'redis', 'error': 'connection timeout'}
        ... )
        >>> await bus.publish(event)
    """

    def __init__(self, base_event_bus: EventBus):
        """初始化跨章节事件总线

        Args:
            base_event_bus: 基础事件总线实例
        """
        self.base_event_bus = base_event_bus

        # 跨章节事件处理器
        self.cross_chapter_handlers: Dict[CrossChapterEventType, List[Callable]] = {}

        # 事件路由表
        self.routing_table: Dict[int, List[int]] = {
            10: [13, 19],  # Chapter 10 -> 13 (监控), 19 (应急)
            12: [19],  # Chapter 12 -> 19 (末日开关 -> 应急)
            13: [19],  # Chapter 13 -> 19 (告警 -> 应急)
            14: [17],  # Chapter 14 -> 17 (测试 -> CI/CD)
            16: [13],  # Chapter 16 -> 13 (性能 -> 监控)
            18: [13],  # Chapter 18 -> 13 (成本 -> 熔断)
            19: [13],  # Chapter 19 -> 13 (风险 -> 告警)
        }

        # 统计信息
        self.stats = {"events_published": 0, "events_routed": 0, "routing_errors": 0, "start_time": None}

        logger.info("跨章节事件总线初始化完成")

    async def initialize(self):
        """初始化跨章节事件总线"""
        try:
            # 注册跨章节事件处理器
            await self._register_cross_chapter_handlers()

            self.stats["start_time"] = datetime.now()

            logger.info("跨章节事件总线启动成功")

        except Exception as e:
            logger.error(f"跨章节事件总线初始化失败: {e}")
            raise

    async def _register_cross_chapter_handlers(self):
        """注册跨章节事件处理器"""
        # 订阅系统告警事件（用于接收跨章节事件）
        await self.base_event_bus.subscribe(
            EventType.SYSTEM_ALERT, self._handle_cross_chapter_event, handler_id="cross_chapter_event_handler"
        )

        logger.info("跨章节事件处理器注册完成")

    async def publish(self, event: CrossChapterEvent) -> bool:
        """发布跨章节事件

        白皮书依据: 第十二章 12.1 事件发布

        Args:
            event: 跨章节事件对象

        Returns:
            bool: 是否成功发布

        Raises:
            ValueError: 当事件对象无效时
        """
        try:
            # 验证事件
            if not isinstance(event, CrossChapterEvent):
                raise ValueError("事件对象类型错误")

            # 验证路由
            if not self._validate_routing(event.source_chapter, event.target_chapter):
                logger.warning(f"跨章节路由未定义: Chapter {event.source_chapter} -> {event.target_chapter}")

            # 转换为基础事件
            base_event = event.to_base_event()

            # 发布到基础事件总线
            success = await self.base_event_bus.publish(base_event)

            if success:
                self.stats["events_published"] += 1
                logger.info(
                    f"跨章节事件发布成功: {event.event_type.value}, "
                    f"Chapter {event.source_chapter} -> {event.target_chapter}"
                )

            return success

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.stats["routing_errors"] += 1
            logger.error(f"跨章节事件发布失败: {e}")
            return False

    async def subscribe(
        self,
        event_type: CrossChapterEventType,
        handler_func: Callable[[CrossChapterEvent], Any],
        handler_id: Optional[str] = None,
    ) -> str:
        """订阅跨章节事件

        Args:
            event_type: 跨章节事件类型
            handler_func: 处理函数
            handler_id: 处理器ID

        Returns:
            str: 处理器ID
        """
        if event_type not in self.cross_chapter_handlers:
            self.cross_chapter_handlers[event_type] = []

        self.cross_chapter_handlers[event_type].append(handler_func)

        logger.info(f"跨章节事件订阅成功: {event_type.value}")

        return handler_id or f"{event_type.value}_handler"

    async def _handle_cross_chapter_event(self, event: Event):
        """处理跨章节事件

        Args:
            event: 基础事件对象
        """
        try:
            # 检查是否为跨章节事件
            if not event.metadata.get("is_cross_chapter"):
                return

            # 提取跨章节事件类型
            cross_event_type_str = event.data.get("cross_chapter_event_type")
            if not cross_event_type_str:
                return

            cross_event_type = CrossChapterEventType(cross_event_type_str)

            # 重构跨章节事件对象
            cross_event = CrossChapterEvent(
                event_type=cross_event_type,
                source_chapter=event.metadata["source_chapter"],
                target_chapter=event.metadata["target_chapter"],
                data={k: v for k, v in event.data.items() if k != "cross_chapter_event_type"},
                priority=event.priority,
            )

            # 调用注册的处理器
            handlers = self.cross_chapter_handlers.get(cross_event_type, [])

            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(cross_event)
                    else:
                        handler(cross_event)

                    self.stats["events_routed"] += 1

                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"跨章节事件处理器执行失败: {e}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"跨章节事件处理失败: {e}")

    def _validate_routing(self, source_chapter: int, target_chapter: int) -> bool:
        """验证章节路由

        Args:
            source_chapter: 源章节编号
            target_chapter: 目标章节编号

        Returns:
            bool: 路由是否有效
        """
        if source_chapter not in self.routing_table:
            return False

        return target_chapter in self.routing_table[source_chapter]

    def get_routing_table(self) -> Dict[int, List[int]]:
        """获取路由表

        Returns:
            路由表字典
        """
        return self.routing_table.copy()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds() if self.stats["start_time"] else 0

        return {
            **self.stats,
            "uptime_seconds": uptime,
            "events_per_second": self.stats["events_published"] / max(uptime, 1),
            "routing_success_rate": (self.stats["events_routed"] / max(self.stats["events_published"], 1)),
        }


# 全局跨章节事件总线实例
_global_cross_chapter_bus: Optional[CrossChapterEventBus] = None


async def get_cross_chapter_event_bus(base_event_bus: Optional[EventBus] = None) -> CrossChapterEventBus:
    """获取全局跨章节事件总线实例

    Args:
        base_event_bus: 基础事件总线实例，None时使用全局实例

    Returns:
        跨章节事件总线实例
    """
    global _global_cross_chapter_bus  # pylint: disable=w0603

    if _global_cross_chapter_bus is None:
        if base_event_bus is None:
            from src.infra.event_bus import get_event_bus  # pylint: disable=import-outside-toplevel

            base_event_bus = await get_event_bus()

        _global_cross_chapter_bus = CrossChapterEventBus(base_event_bus)
        await _global_cross_chapter_bus.initialize()

    return _global_cross_chapter_bus


async def publish_cross_chapter_event(
    event_type: CrossChapterEventType,
    source_chapter: int,
    target_chapter: int,
    data: Dict[str, Any],
    priority: EventPriority = EventPriority.NORMAL,
) -> bool:
    """全局跨章节事件发布函数

    Args:
        event_type: 跨章节事件类型
        source_chapter: 源章节编号
        target_chapter: 目标章节编号
        data: 事件数据
        priority: 事件优先级

    Returns:
        bool: 是否成功发布
    """
    bus = await get_cross_chapter_event_bus()

    event = CrossChapterEvent(
        event_type=event_type,
        source_chapter=source_chapter,
        target_chapter=target_chapter,
        data=data,
        priority=priority,
    )

    return await bus.publish(event)


async def subscribe_cross_chapter_event(
    event_type: CrossChapterEventType,
    handler_func: Callable[[CrossChapterEvent], Any],
    handler_id: Optional[str] = None,
) -> str:
    """全局跨章节事件订阅函数

    Args:
        event_type: 跨章节事件类型
        handler_func: 处理函数
        handler_id: 处理器ID

    Returns:
        str: 处理器ID
    """
    bus = await get_cross_chapter_event_bus()
    return await bus.subscribe(event_type, handler_func, handler_id)
