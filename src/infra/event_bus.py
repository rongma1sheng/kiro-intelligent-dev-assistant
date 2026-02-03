"""
MIA系统事件总线 (Event Bus)

白皮书依据: 基础设施层 - 解耦模块间直接依赖
版本: v1.6.0
作者: MIA Team
日期: 2026-01-18

核心理念: 通过事件驱动架构解决模块间的循环依赖问题，
实现松耦合的系统架构。

主要功能:
1. 事件发布/订阅机制
2. 异步事件处理
3. 事件路由和过滤
4. 事件持久化和重放
5. 跨模块通信解耦
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import redis
from loguru import logger

from src.utils.logger import get_logger

logger = get_logger(__name__)


class EventType(Enum):
    """事件类型"""

    # Brain层事件
    DECISION_REQUEST = "decision_request"  # 决策请求（新增）
    DECISION_MADE = "decision_made"  # 决策完成
    ANALYSIS_COMPLETED = "analysis_completed"  # 分析完成
    MEMORY_UPDATED = "memory_updated"  # 记忆更新

    # Evolution层事件
    FACTOR_DISCOVERED = "factor_discovered"  # 因子发现
    ARENA_TEST_COMPLETED = "arena_test_completed"  # Arena测试完成
    STRATEGY_GENERATED = "strategy_generated"  # 策略生成
    Z2H_CERTIFIED = "z2h_certified"  # Z2H认证
    Z2H_REVOKED = "z2h_revoked"  # Z2H认证撤销
    SECURITY_ALERT = "security_alert"  # 安全警报

    # Chapter 4 - Sparta Evolution事件
    FACTOR_ARENA_COMPLETED = "factor_arena_completed"  # 因子Arena测试完成
    STRATEGY_ARENA_COMPLETED = "strategy_arena_completed"  # 策略Arena测试完成
    SIMULATION_COMPLETED = "simulation_completed"  # 模拟验证完成
    FACTOR_DECAY_DETECTED = "factor_decay_detected"  # 因子衰减检测
    STRATEGY_RETIRED = "strategy_retired"  # 策略退役

    # Infrastructure层事件
    DATA_UPDATED = "data_updated"  # 数据更新
    SYSTEM_ALERT = "system_alert"  # 系统告警
    CONFIG_CHANGED = "config_changed"  # 配置变更

    # Services层事件
    MARKET_DATA_RECEIVED = "market_data_received"  # 市场数据接收
    PORTFOLIO_UPDATED = "portfolio_updated"  # 投资组合更新
    TRADE_EXECUTED = "trade_executed"  # 交易执行

    # Chronos层事件
    SCHEDULE_TRIGGERED = "schedule_triggered"  # 调度触发
    TIMER_EXPIRED = "timer_expired"  # 定时器到期
    HEARTBEAT = "heartbeat"  # 心跳

    # 跨脑通信事件
    RESEARCH_REQUEST = "research_request"  # 研究请求
    MARKET_DATA_REQUEST = "market_data_request"  # 市场数据请求
    STRATEGY_REQUEST = "strategy_request"  # 策略请求

    # 进化-验证通信事件
    AUDIT_COMPLETED = "audit_completed"  # 审计完成
    AUDIT_REQUEST = "audit_request"  # 审计请求

    # 系统查询通信事件（内存-调度解耦）
    SYSTEM_QUERY = "system_query"  # 系统查询
    SYSTEM_RESPONSE = "system_response"  # 系统响应
    MEMORY_QUERY = "memory_query"  # 内存查询
    SCHEDULE_QUERY = "schedule_query"  # 调度查询


class EventPriority(Enum):
    """事件优先级"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Event:
    """事件对象"""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.HEARTBEAT
    source_module: str = "unknown"
    target_module: Optional[str] = None  # None表示广播
    priority: EventPriority = EventPriority.NORMAL

    # 事件数据
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    # 处理信息
    retry_count: int = 0
    max_retries: int = 3
    processed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source_module": self.source_module,
            "target_module": self.target_module,
            "priority": self.priority.value,
            "data": self.data,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "processed": self.processed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """从字典创建事件对象"""
        event = cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            source_module=data["source_module"],
            target_module=data.get("target_module"),
            priority=EventPriority(data["priority"]),
            data=data.get("data", {}),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            processed=data.get("processed", False),
        )
        return event


class EventHandler:
    """事件处理器基类"""

    def __init__(self, handler_id: str, handler_func: Callable[[Event], Any]):
        """初始化事件处理器

        Args:
            handler_id: 处理器唯一标识
            handler_func: 处理函数
        """
        self.handler_id = handler_id
        self.handler_func = handler_func
        self.created_at = datetime.now()
        self.call_count = 0
        self.error_count = 0
        self.last_called = None

    async def handle(self, event: Event) -> bool:
        """处理事件

        Args:
            event: 事件对象

        Returns:
            bool: 处理是否成功
        """
        try:
            self.call_count += 1
            self.last_called = datetime.now()

            # 调用处理函数
            if asyncio.iscoroutinefunction(self.handler_func):
                result = await self.handler_func(event)
                print(f"[DEBUG-EventHandler] Async handler_func completed for {self.handler_id}, result={result}")
            else:
                result = self.handler_func(event)
                print(f"[DEBUG-EventHandler] Sync handler_func completed for {self.handler_id}, result={result}")

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.error_count += 1
            logger.error(  # pylint: disable=logging-fstring-interpolation
                f"事件处理器 {self.handler_id} 处理事件 {event.event_id} 失败: {e}"
            )  # pylint: disable=logging-fstring-interpolation
            import traceback  # pylint: disable=import-outside-toplevel

            traceback.print_exc()
            return False


class EventBus:
    """事件总线

    核心功能:
    1. 事件发布/订阅
    2. 异步事件处理
    3. 事件持久化
    4. 跨模块通信解耦

    使用示例:
        >>> bus = EventBus()
        >>> await bus.initialize()
        >>>
        >>> # 订阅事件
        >>> await bus.subscribe(EventType.DECISION_MADE, handler_func)
        >>>
        >>> # 发布事件
        >>> event = Event(
        ...     event_type=EventType.DECISION_MADE,
        ...     source_module="soldier",
        ...     data={"action": "buy", "symbol": "000001.SZ"}
        ... )
        >>> await bus.publish(event)
    """

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        batch_size: int = 10,
        enable_batching: bool = True,
        low_latency_mode: bool = False,
    ):
        """初始化事件总线

        Args:
            redis_client: Redis客户端，用于事件持久化
            batch_size: 批量处理事件数量，默认10
            enable_batching: 是否启用批量处理，默认True
            low_latency_mode: 低延迟模式，不等待批次填满，立即处理，默认False
        """
        self.redis_client = redis_client
        self.batch_size = batch_size
        self.enable_batching = enable_batching
        self.low_latency_mode = low_latency_mode

        # 事件处理器注册表
        self.handlers: Dict[EventType, List[EventHandler]] = {}

        # 优化的事件队列（使用更大的maxsize以减少阻塞）
        self.event_queue = asyncio.Queue(maxsize=10000)
        self.priority_queues = {
            EventPriority.CRITICAL: asyncio.Queue(maxsize=1000),
            EventPriority.HIGH: asyncio.Queue(maxsize=5000),
            EventPriority.NORMAL: asyncio.Queue(maxsize=10000),
            EventPriority.LOW: asyncio.Queue(maxsize=5000),
        }

        # 处理器任务
        self.processor_task = None
        self.running = False

        # 统计信息
        self.stats = {
            "events_published": 0,
            "events_processed": 0,
            "events_failed": 0,
            "handlers_registered": 0,
            "start_time": None,
            "batch_processed": 0,
            "avg_batch_size": 0.0,
            "avg_processing_time_us": 0.0,  # 微秒
        }

        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"事件总线初始化完成 (batch_size={batch_size}, batching={enable_batching}, low_latency={low_latency_mode})"
        )

    async def initialize(self):
        """初始化事件总线"""
        try:
            # 启动事件处理器
            self.running = True
            self.processor_task = asyncio.create_task(self._process_events())
            self.stats["start_time"] = datetime.now()

            logger.info("事件总线启动成功")

        except Exception as e:
            logger.error(f"事件总线初始化失败: {e}")  # pylint: disable=logging-fstring-interpolation
            raise

    async def shutdown(self):
        """关闭事件总线"""
        try:
            self.running = False

            if self.processor_task:
                self.processor_task.cancel()
                try:
                    await self.processor_task
                except asyncio.CancelledError:
                    pass

            logger.info("事件总线已关闭")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"事件总线关闭失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def subscribe(
        self, event_type: EventType, handler_func: Callable[[Event], Any], handler_id: Optional[str] = None
    ) -> str:
        """订阅事件

        Args:
            event_type: 事件类型
            handler_func: 处理函数
            handler_id: 处理器ID，None时自动生成

        Returns:
            str: 处理器ID
        """
        if handler_id is None:
            handler_id = f"{event_type.value}_{int(time.time())}_{len(self.handlers.get(event_type, []))}"

        handler = EventHandler(handler_id, handler_func)

        if event_type not in self.handlers:
            self.handlers[event_type] = []

        self.handlers[event_type].append(handler)
        self.stats["handlers_registered"] += 1

        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"事件订阅成功: {event_type.value} -> {handler_id}"
        )  # pylint: disable=logging-fstring-interpolation
        return handler_id

    async def unsubscribe(self, event_type: EventType, handler_id: str) -> bool:
        """取消订阅

        Args:
            event_type: 事件类型
            handler_id: 处理器ID

        Returns:
            bool: 是否成功取消订阅
        """
        if event_type not in self.handlers:
            return False

        handlers = self.handlers[event_type]
        for i, handler in enumerate(handlers):
            if handler.handler_id == handler_id:
                del handlers[i]
                self.stats["handlers_registered"] -= 1
                logger.info(  # pylint: disable=logging-fstring-interpolation
                    f"取消事件订阅: {event_type.value} -> {handler_id}"
                )  # pylint: disable=logging-fstring-interpolation
                return True

        return False

    async def publish(self, event: Event) -> bool:
        """发布事件

        Args:
            event: 事件对象

        Returns:
            bool: 是否成功发布
        """
        try:
            # 验证事件
            if not isinstance(event, Event):
                raise ValueError("事件对象类型错误")

            # 检查事件是否过期
            if event.expires_at and datetime.now() > event.expires_at:
                logger.warning(  # pylint: disable=logging-fstring-interpolation
                    f"事件已过期，跳过发布: {event.event_id}"
                )  # pylint: disable=logging-fstring-interpolation
                return False

            # 根据优先级放入对应队列
            await self.priority_queues[event.priority].put(event)

            # 持久化事件（如果配置了Redis）
            if self.redis_client:
                await self._persist_event(event)

            self.stats["events_published"] += 1

            logger.debug(  # pylint: disable=logging-fstring-interpolation
                f"[EventBus] 事件发布成功: {event.event_type.value} ({event.event_id}), source={event.source_module}, target={event.target_module}, priority={event.priority.name}"  # pylint: disable=line-too-long
            )
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"事件发布失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return False

    async def publish_simple(  # pylint: disable=too-many-positional-arguments
        self,
        event_type: EventType,
        source_module: str,
        data: Dict[str, Any],
        target_module: Optional[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> bool:
        """简化的事件发布接口

        Args:
            event_type: 事件类型
            source_module: 源模块
            data: 事件数据
            target_module: 目标模块，None表示广播
            priority: 事件优先级

        Returns:
            bool: 是否成功发布
        """
        event = Event(
            event_type=event_type,
            source_module=source_module,
            target_module=target_module,
            priority=priority,
            data=data,
        )

        return await self.publish(event)

    async def _process_events(self):
        """事件处理主循环（优化版 - 支持批量处理）"""
        logger.info("事件处理器启动")

        while self.running:
            try:
                if self.enable_batching:
                    # 批量处理模式
                    events = await self._get_event_batch()

                    if events:
                        start_time = time.perf_counter()
                        await self._handle_event_batch(events)
                        elapsed_us = (time.perf_counter() - start_time) * 1_000_000

                        # 更新统计信息
                        self.stats["batch_processed"] += 1
                        batch_count = self.stats["batch_processed"]
                        self.stats["avg_batch_size"] = (
                            self.stats["avg_batch_size"] * (batch_count - 1) + len(events)
                        ) / batch_count
                        self.stats["avg_processing_time_us"] = (
                            self.stats["avg_processing_time_us"] * (batch_count - 1) + elapsed_us
                        ) / batch_count
                    else:
                        # 没有事件时短暂休眠（减少CPU占用）
                        await asyncio.sleep(0.001)  # 1ms
                else:
                    # 单事件处理模式（向后兼容）
                    event = await self._get_next_event()

                    if event:
                        start_time = time.perf_counter()
                        logger.debug(  # pylint: disable=logging-fstring-interpolation
                            f"[EventBus] 从队列获取事件: {event.event_type.value}, event_id={event.event_id}"
                        )  # pylint: disable=logging-fstring-interpolation
                        await self._handle_event(event)
                        elapsed_us = (time.perf_counter() - start_time) * 1_000_000

                        # 更新统计信息
                        self.stats["avg_processing_time_us"] = (
                            self.stats["avg_processing_time_us"] * self.stats["events_processed"] + elapsed_us
                        ) / (self.stats["events_processed"] + 1)
                    else:
                        # 没有事件时短暂休眠
                        await asyncio.sleep(0.001)  # 1ms

            except asyncio.CancelledError:
                break
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"事件处理循环异常: {e}")  # pylint: disable=logging-fstring-interpolation
                await asyncio.sleep(0.1)

        logger.info("事件处理器已停止")

    async def _get_next_event(self) -> Optional[Event]:
        """获取下一个待处理事件（按优先级）"""
        # 按优先级顺序检查队列
        for priority in [EventPriority.CRITICAL, EventPriority.HIGH, EventPriority.NORMAL, EventPriority.LOW]:
            queue = self.priority_queues[priority]

            try:
                # 非阻塞获取事件
                event = queue.get_nowait()
                return event
            except asyncio.QueueEmpty:
                continue

        return None

    async def _get_event_batch(self) -> List[Event]:
        """批量获取待处理事件（按优先级，自适应延迟优化）

        性能优化:
        1. 批量处理可以减少上下文切换，提高吞吐量
        2. 低延迟模式: 立即处理现有事件，不等待批次填满
        3. 高吞吐模式: 短暂等待以填满批次

        Returns:
            事件列表，最多batch_size个事件
        """
        events = []

        # 按优先级顺序收集事件
        for priority in [EventPriority.CRITICAL, EventPriority.HIGH, EventPriority.NORMAL, EventPriority.LOW]:
            queue = self.priority_queues[priority]

            # 从当前优先级队列收集事件
            while len(events) < self.batch_size:
                try:
                    event = queue.get_nowait()
                    events.append(event)
                except asyncio.QueueEmpty:
                    break

            # 如果已经收集到足够的事件，停止收集
            if len(events) >= self.batch_size:
                break

        # 自适应延迟优化
        if not self.low_latency_mode and 0 < len(events) < self.batch_size:
            # 高吞吐模式: 等待最多1ms，看是否有更多事件到达
            try:
                await asyncio.wait_for(self._wait_for_more_events(events), timeout=0.001)  # 1ms超时
            except asyncio.TimeoutError:
                pass  # 超时就直接处理现有事件

        # 低延迟模式: 立即返回，不等待
        return events

    async def _wait_for_more_events(self, events: List[Event]):
        """等待更多事件到达（用于延迟优化）"""
        # 尝试从队列中获取更多事件，直到达到batch_size
        for priority in [EventPriority.CRITICAL, EventPriority.HIGH, EventPriority.NORMAL, EventPriority.LOW]:
            queue = self.priority_queues[priority]

            while len(events) < self.batch_size:
                try:
                    # 使用短超时的get，而不是get_nowait
                    event = await asyncio.wait_for(queue.get(), timeout=0.0001)
                    events.append(event)
                except asyncio.TimeoutError:
                    break
                except asyncio.QueueEmpty:
                    break

            if len(events) >= self.batch_size:
                break

    async def _handle_event_batch(self, events: List[Event]):
        """批量处理事件（并发优化版）

        性能优化:
        1. 批量处理减少日志开销和上下文切换
        2. 并发执行所有处理器，提高吞吐量
        3. 使用asyncio.gather实现真正的并发

        Args:
            events: 事件列表
        """
        if not events:
            return

        logger.debug(f"[EventBus] 批量处理 {len(events)} 个事件")  # pylint: disable=logging-fstring-interpolation

        # 按事件类型分组（相同类型的事件可以共享处理器查找）
        events_by_type: Dict[EventType, List[Event]] = {}
        for event in events:
            if event.event_type not in events_by_type:
                events_by_type[event.event_type] = []
            events_by_type[event.event_type].append(event)

        # 批量处理每种类型的事件
        for event_type, type_events in events_by_type.items():
            handlers = self.handlers.get(event_type, [])

            if not handlers:
                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"没有找到事件处理器: {event_type.value}, 跳过 {len(type_events)} 个事件"
                )  # pylint: disable=logging-fstring-interpolation
                continue

            # 为每个事件创建处理任务（并发执行）
            tasks = []
            event_task_map = []  # 记录事件和任务的映射

            for event in type_events:
                # 过滤目标模块
                filtered_handlers = self._filter_handlers_by_target(handlers, event)

                # 为每个处理器创建任务
                for handler in filtered_handlers:
                    task = handler.handle(event)
                    tasks.append(task)
                    event_task_map.append(event)

            # 并发执行所有任务（关键优化点）
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 统计处理结果
            for i, result in enumerate(results):
                event = event_task_map[i]
                if isinstance(result, Exception):
                    self.stats["events_failed"] += 1
                    logger.error(  # pylint: disable=logging-fstring-interpolation
                        f"批量处理事件失败: {event.event_id}, 错误: {result}"
                    )  # pylint: disable=logging-fstring-interpolation
                elif result:
                    self.stats["events_processed"] += 1
                else:
                    self.stats["events_failed"] += 1

    def _filter_handlers_by_target(self, handlers: List[EventHandler], event: Event) -> List[EventHandler]:
        """根据目标模块过滤处理器

        Args:
            handlers: 处理器列表
            event: 事件对象

        Returns:
            过滤后的处理器列表
        """
        if not event.target_module:
            return handlers

        # 根据handler_id过滤目标模块的处理器
        filtered_handlers = [
            h
            for h in handlers
            if event.target_module in h.handler_id
            or h.handler_id.startswith(event.target_module)
            or event.target_module.replace("_", "") in h.handler_id.replace("_", "")
        ]

        # 如果没有匹配的处理器，使用所有处理器（向后兼容）
        if not filtered_handlers:
            return handlers

        return filtered_handlers

    async def _handle_event(self, event: Event):
        """处理单个事件"""
        try:
            # 获取事件处理器
            handlers = self.handlers.get(event.event_type, [])

            if not handlers:
                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"没有找到事件处理器: {event.event_type.value}, event_id={event.event_id}"
                )  # pylint: disable=logging-fstring-interpolation
                return

            logger.debug(  # pylint: disable=logging-fstring-interpolation
                f"处理事件: {event.event_type.value}, event_id={event.event_id}, source={event.source_module}, target={event.target_module}, handlers_count={len(handlers)}"  # pylint: disable=line-too-long
            )

            # 过滤目标模块（如果指定了target_module）
            filtered_handlers = handlers
            if event.target_module:
                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"所有handler_ids: {[h.handler_id for h in handlers]}"
                )  # pylint: disable=logging-fstring-interpolation

                # 根据handler_id过滤目标模块的处理器
                # handler_id格式通常包含模块名，如 "chronos_scheduler_query_handler"
                filtered_handlers = [
                    h
                    for h in handlers
                    if event.target_module in h.handler_id
                    or h.handler_id.startswith(event.target_module)
                    or event.target_module.replace("_", "") in h.handler_id.replace("_", "")
                ]

                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"过滤后的handler_ids: {[h.handler_id for h in filtered_handlers]}"
                )  # pylint: disable=logging-fstring-interpolation

                # 如果没有匹配的处理器，使用所有处理器（向后兼容）
                if not filtered_handlers:
                    logger.debug(  # pylint: disable=logging-fstring-interpolation
                        f"未找到目标模块 {event.target_module} 的处理器，使用所有处理器"
                    )  # pylint: disable=logging-fstring-interpolation
                    filtered_handlers = handlers
                else:
                    logger.debug(  # pylint: disable=logging-fstring-interpolation
                        f"事件 {event.event_id} 过滤到 {len(filtered_handlers)} 个目标处理器（目标: {event.target_module}）, handler_ids={[h.handler_id for h in filtered_handlers]}"  # pylint: disable=line-too-long
                    )

            # 并发处理所有处理器
            tasks = []
            for handler in filtered_handlers:
                logger.info(  # pylint: disable=logging-fstring-interpolation
                    f"[EventBus] 准备调用处理器: {handler.handler_id} for event {event.event_id}"
                )  # pylint: disable=logging-fstring-interpolation
                task = asyncio.create_task(handler.handle(event))
                tasks.append(task)

            # 等待所有处理器完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 统计处理结果
            success_count = sum(1 for result in results if result is True)
            error_count = len(results) - success_count

            if error_count > 0:
                self.stats["events_failed"] += 1
                logger.warning(  # pylint: disable=logging-fstring-interpolation
                    f"事件处理部分失败: {event.event_id}, 成功: {success_count}, 失败: {error_count}"
                )  # pylint: disable=logging-fstring-interpolation
            else:
                self.stats["events_processed"] += 1
                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"事件处理成功: {event.event_id}, 处理器数量: {len(filtered_handlers)}"
                )  # pylint: disable=logging-fstring-interpolation

            # 标记事件为已处理
            event.processed = True

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.stats["events_failed"] += 1
            logger.error(f"事件处理异常: {event.event_id}, 错误: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _persist_event(self, event: Event):
        """持久化事件到Redis"""
        try:
            if not self.redis_client:
                return

            # 检查Redis客户端类型
            if hasattr(self.redis_client, "hset"):
                # 真实Redis
                key = f"event:{event.event_id}"
                await self.redis_client.hset(
                    key, mapping={"data": json.dumps(event.to_dict()), "created_at": event.created_at.isoformat()}
                )
                await self.redis_client.expire(key, 86400)  # 24小时过期

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"事件持久化失败: {e}")  # pylint: disable=logging-fstring-interpolation

    def get_stats(self) -> Dict[str, Any]:
        """获取事件总线统计信息"""
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds() if self.stats["start_time"] else 0

        return {
            **self.stats,
            "uptime_seconds": uptime,
            "events_per_second": self.stats["events_processed"] / max(uptime, 1),
            "queue_sizes": {priority.name: queue.qsize() for priority, queue in self.priority_queues.items()},
            "handler_count_by_type": {
                event_type.value: len(handlers) for event_type, handlers in self.handlers.items()
            },
            "batching_enabled": self.enable_batching,
            "batch_size": self.batch_size,
        }

    def get_handlers(self, event_type: Optional[EventType] = None) -> Dict[str, Any]:
        """获取处理器信息"""
        if event_type:  # pylint: disable=no-else-return
            handlers = self.handlers.get(event_type, [])
            return {
                "event_type": event_type.value,
                "handler_count": len(handlers),
                "handlers": [
                    {
                        "handler_id": h.handler_id,
                        "call_count": h.call_count,
                        "error_count": h.error_count,
                        "last_called": h.last_called.isoformat() if h.last_called else None,
                    }
                    for h in handlers
                ],
            }
        else:
            return {
                event_type.value: {
                    "handler_count": len(handlers),
                    "total_calls": sum(h.call_count for h in handlers),
                    "total_errors": sum(h.error_count for h in handlers),
                }
                for event_type, handlers in self.handlers.items()
            }


# 全局事件总线实例
_global_event_bus: Optional[EventBus] = None


async def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    global _global_event_bus  # pylint: disable=w0603

    if _global_event_bus is None:
        _global_event_bus = EventBus()
        await _global_event_bus.initialize()

    return _global_event_bus


async def publish_event(
    event_type: EventType,
    source_module: str,
    data: Dict[str, Any],
    target_module: Optional[str] = None,
    priority: EventPriority = EventPriority.NORMAL,
) -> bool:
    """全局事件发布函数"""
    bus = await get_event_bus()
    return await bus.publish_simple(
        event_type=event_type, source_module=source_module, data=data, target_module=target_module, priority=priority
    )


async def subscribe_event(
    event_type: EventType, handler_func: Callable[[Event], Any], handler_id: Optional[str] = None
) -> str:
    """全局事件订阅函数"""
    bus = await get_event_bus()
    return await bus.subscribe(event_type, handler_func, handler_id)
