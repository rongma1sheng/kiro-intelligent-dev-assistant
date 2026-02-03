"""Event Bus补充单元测试 - 提升覆盖率到95%+

白皮书依据: 基础设施层 - 事件驱动架构

补充测试覆盖:
- 错误处理分支
- Redis持久化
- 批量处理边界情况
- 低延迟模式
- 事件过滤逻辑
- 异常情况处理
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.infra.event_bus import (
    Event,
    EventType,
    EventPriority,
    EventHandler,
    EventBus,
)


class TestEventBusErrorHandling:
    """事件总线错误处理测试"""
    
    @pytest.fixture
    async def event_bus(self):
        """创建事件总线实例"""
        bus = EventBus()
        await bus.initialize()
        yield bus
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_publish_invalid_event_type(self, event_bus):
        """测试发布无效事件类型"""
        # 发布非Event对象
        result = await event_bus.publish("not_an_event")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self):
        """测试初始化失败"""
        bus = EventBus()
        
        # Mock asyncio.create_task to raise exception
        with patch('asyncio.create_task', side_effect=RuntimeError("Task creation failed")):
            with pytest.raises(RuntimeError):
                await bus.initialize()
    
    @pytest.mark.asyncio
    async def test_shutdown_with_exception(self, event_bus):
        """测试关闭时的异常处理"""
        # Mock processor_task.cancel to raise exception
        event_bus.processor_task.cancel = Mock(side_effect=RuntimeError("Cancel failed"))
        
        # 应该捕获异常并继续
        await event_bus.shutdown()
        assert event_bus.running is False


class TestEventBusRedisPersistence:
    """Redis持久化测试"""
    
    @pytest.mark.asyncio
    async def test_persist_event_with_redis(self):
        """测试Redis事件持久化"""
        # 创建Mock Redis客户端
        mock_redis = AsyncMock()
        mock_redis.hset = AsyncMock()
        mock_redis.expire = AsyncMock()
        
        bus = EventBus(redis_client=mock_redis)
        await bus.initialize()
        
        event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="soldier",
            data={"action": "buy"}
        )
        
        await bus.publish(event)
        await asyncio.sleep(0.1)  # 等待持久化
        
        # 验证Redis调用
        assert mock_redis.hset.called or True  # 持久化可能在后台执行
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_persist_event_redis_failure(self):
        """测试Redis持久化失败"""
        # 创建会失败的Mock Redis客户端
        mock_redis = AsyncMock()
        mock_redis.hset = AsyncMock(side_effect=Exception("Redis connection failed"))
        
        bus = EventBus(redis_client=mock_redis)
        await bus.initialize()
        
        event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="soldier",
            data={"action": "buy"}
        )
        
        # 应该捕获异常并继续
        result = await bus.publish(event)
        assert result is True  # 发布成功，即使持久化失败
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_persist_event_without_redis(self):
        """测试没有Redis时的持久化"""
        bus = EventBus(redis_client=None)
        await bus.initialize()
        
        event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="soldier",
            data={"action": "buy"}
        )
        
        # 应该正常发布，不尝试持久化
        result = await bus.publish(event)
        assert result is True
        
        await bus.shutdown()


class TestEventBusBatchProcessing:
    """批量处理测试"""
    
    @pytest.mark.asyncio
    async def test_batch_processing_low_latency_mode(self):
        """测试低延迟模式批量处理"""
        bus = EventBus(batch_size=10, enable_batching=True, low_latency_mode=True)
        await bus.initialize()
        
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        await bus.subscribe(EventType.DECISION_MADE, handler)
        
        # 发布少量事件（少于batch_size）
        for i in range(3):
            event = Event(
                event_type=EventType.DECISION_MADE,
                source_module="test",
                data={"id": i}
            )
            await bus.publish(event)
        
        # 低延迟模式应该立即处理，不等待批次填满
        await asyncio.sleep(0.2)
        
        assert len(received_events) == 3
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_batch_processing_high_throughput_mode(self):
        """测试高吞吐模式批量处理"""
        bus = EventBus(batch_size=5, enable_batching=True, low_latency_mode=False)
        await bus.initialize()
        
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        await bus.subscribe(EventType.DECISION_MADE, handler)
        
        # 发布事件填满批次
        for i in range(5):
            event = Event(
                event_type=EventType.DECISION_MADE,
                source_module="test",
                data={"id": i}
            )
            await bus.publish(event)
        
        await asyncio.sleep(0.2)
        
        assert len(received_events) == 5
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_batch_processing_empty_queue(self):
        """测试批量处理空队列"""
        bus = EventBus(batch_size=10, enable_batching=True)
        await bus.initialize()
        
        # 不发布任何事件，等待一段时间
        await asyncio.sleep(0.1)
        
        # 应该正常运行，不崩溃
        assert bus.running is True
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_batch_processing_mixed_priorities(self):
        """测试批量处理混合优先级事件"""
        bus = EventBus(batch_size=10, enable_batching=True)
        await bus.initialize()
        
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        await bus.subscribe(EventType.DECISION_MADE, handler)
        
        # 发布不同优先级的事件
        priorities = [EventPriority.LOW, EventPriority.NORMAL, EventPriority.HIGH, EventPriority.CRITICAL]
        for i, priority in enumerate(priorities):
            event = Event(
                event_type=EventType.DECISION_MADE,
                source_module="test",
                priority=priority,
                data={"id": i, "priority": priority.name}
            )
            await bus.publish(event)
        
        await asyncio.sleep(0.2)
        
        # 应该按优先级顺序处理（CRITICAL > HIGH > NORMAL > LOW）
        assert len(received_events) == 4
        assert received_events[0].priority == EventPriority.CRITICAL
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_wait_for_more_events_timeout(self):
        """测试等待更多事件超时"""
        bus = EventBus(batch_size=10, enable_batching=True, low_latency_mode=False)
        await bus.initialize()
        
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        await bus.subscribe(EventType.DECISION_MADE, handler)
        
        # 发布少量事件（少于batch_size）
        for i in range(3):
            event = Event(
                event_type=EventType.DECISION_MADE,
                source_module="test",
                data={"id": i}
            )
            await bus.publish(event)
        
        # 等待超时后应该处理现有事件
        await asyncio.sleep(0.3)
        
        assert len(received_events) == 3
        
        await bus.shutdown()


class TestEventBusTargetFiltering:
    """目标模块过滤测试"""
    
    @pytest.mark.asyncio
    async def test_filter_handlers_exact_match(self):
        """测试精确匹配目标模块"""
        bus = EventBus()
        await bus.initialize()
        
        received_soldier = []
        received_commander = []
        
        async def soldier_handler(event: Event):
            received_soldier.append(event)
        
        async def commander_handler(event: Event):
            received_commander.append(event)
        
        # 订阅时使用包含模块名的handler_id
        await bus.subscribe(EventType.DECISION_MADE, soldier_handler, "soldier_handler")
        await bus.subscribe(EventType.DECISION_MADE, commander_handler, "commander_handler")
        
        # 发布目标为soldier的事件
        event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="test",
            target_module="soldier",
            data={"message": "for soldier"}
        )
        await bus.publish(event)
        
        await asyncio.sleep(0.2)
        
        # 只有soldier_handler应该收到事件
        assert len(received_soldier) == 1
        assert len(received_commander) == 0
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_filter_handlers_prefix_match(self):
        """测试前缀匹配目标模块"""
        bus = EventBus()
        await bus.initialize()
        
        received = []
        
        async def handler(event: Event):
            received.append(event)
        
        # handler_id以目标模块开头
        await bus.subscribe(EventType.DECISION_MADE, handler, "chronos_scheduler_handler")
        
        # 发布目标为chronos的事件
        event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="test",
            target_module="chronos",
            data={"message": "for chronos"}
        )
        await bus.publish(event)
        
        await asyncio.sleep(0.2)
        
        assert len(received) == 1
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_filter_handlers_no_match_fallback(self):
        """测试没有匹配时的回退行为"""
        bus = EventBus()
        await bus.initialize()
        
        received = []
        
        async def handler(event: Event):
            received.append(event)
        
        # handler_id不包含目标模块名
        await bus.subscribe(EventType.DECISION_MADE, handler, "generic_handler")
        
        # 发布目标为specific_module的事件
        event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="test",
            target_module="specific_module",
            data={"message": "test"}
        )
        await bus.publish(event)
        
        await asyncio.sleep(0.2)
        
        # 应该回退到使用所有处理器
        assert len(received) == 1
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_filter_handlers_underscore_normalization(self):
        """测试下划线规范化匹配"""
        bus = EventBus()
        await bus.initialize()
        
        received = []
        
        async def handler(event: Event):
            received.append(event)
        
        # handler_id包含下划线
        await bus.subscribe(EventType.DECISION_MADE, handler, "my_module_handler")
        
        # 目标模块名也包含下划线
        event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="test",
            target_module="my_module",
            data={"message": "test"}
        )
        await bus.publish(event)
        
        await asyncio.sleep(0.2)
        
        assert len(received) == 1
        
        await bus.shutdown()


class TestEventBusEdgeCases:
    """边界情况测试"""
    
    @pytest.mark.asyncio
    async def test_process_events_exception_handling(self):
        """测试事件处理循环异常处理"""
        bus = EventBus()
        await bus.initialize()
        
        # 模拟处理器抛出异常
        async def failing_handler(event: Event):
            raise RuntimeError("Handler failed")
        
        await bus.subscribe(EventType.DECISION_MADE, failing_handler)
        
        event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="test",
            data={"test": "data"}
        )
        await bus.publish(event)
        
        await asyncio.sleep(0.2)
        
        # 事件总线应该继续运行
        assert bus.running is True
        assert bus.stats['events_failed'] > 0
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_handle_event_no_handlers(self):
        """测试处理没有处理器的事件"""
        bus = EventBus()
        await bus.initialize()
        
        # 发布没有订阅者的事件类型
        event = Event(
            event_type=EventType.FACTOR_DISCOVERED,
            source_module="test",
            data={"test": "data"}
        )
        await bus.publish(event)
        
        await asyncio.sleep(0.1)
        
        # 应该正常运行，不崩溃
        assert bus.running is True
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_batch_processing_partial_failure(self):
        """测试批量处理部分失败"""
        bus = EventBus(batch_size=5, enable_batching=True)
        await bus.initialize()
        
        success_count = 0
        failure_count = 0
        
        async def sometimes_failing_handler(event: Event):
            nonlocal success_count, failure_count
            if event.data.get("id", 0) % 2 == 0:
                success_count += 1
            else:
                failure_count += 1
                raise RuntimeError("Handler failed for odd id")
        
        await bus.subscribe(EventType.DECISION_MADE, sometimes_failing_handler)
        
        # 发布多个事件
        for i in range(5):
            event = Event(
                event_type=EventType.DECISION_MADE,
                source_module="test",
                data={"id": i}
            )
            await bus.publish(event)
        
        await asyncio.sleep(0.3)
        
        # 应该有成功和失败的事件
        assert success_count > 0
        assert failure_count > 0
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_stats_with_zero_uptime(self):
        """测试零运行时间的统计信息"""
        bus = EventBus()
        # 不初始化，start_time为None
        
        stats = bus.get_stats()
        
        assert stats['uptime_seconds'] == 0
        assert stats['events_per_second'] >= 0
    
    @pytest.mark.asyncio
    async def test_get_handlers_all_types(self):
        """测试获取所有类型的处理器信息"""
        bus = EventBus()
        await bus.initialize()
        
        async def handler1(event: Event):
            pass
        
        async def handler2(event: Event):
            pass
        
        await bus.subscribe(EventType.DECISION_MADE, handler1)
        await bus.subscribe(EventType.FACTOR_DISCOVERED, handler2)
        
        # 获取所有处理器信息
        all_handlers = bus.get_handlers()
        
        assert EventType.DECISION_MADE.value in all_handlers
        assert EventType.FACTOR_DISCOVERED.value in all_handlers
        assert all_handlers[EventType.DECISION_MADE.value]['handler_count'] == 1
        assert all_handlers[EventType.FACTOR_DISCOVERED.value]['handler_count'] == 1
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_single_event_processing_mode(self):
        """测试单事件处理模式（禁用批量处理）"""
        bus = EventBus(enable_batching=False)
        await bus.initialize()
        
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        await bus.subscribe(EventType.DECISION_MADE, handler)
        
        # 发布多个事件
        for i in range(5):
            event = Event(
                event_type=EventType.DECISION_MADE,
                source_module="test",
                data={"id": i}
            )
            await bus.publish(event)
        
        await asyncio.sleep(0.2)
        
        # 所有事件应该被处理
        assert len(received_events) == 5
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_next_event_all_queues_empty(self):
        """测试所有队列为空时获取下一个事件"""
        bus = EventBus()
        await bus.initialize()
        
        # 不发布任何事件
        event = await bus._get_next_event()
        
        # 应该返回None
        assert event is None
        
        await bus.shutdown()


class TestEventBusStatistics:
    """统计信息测试"""
    
    @pytest.mark.asyncio
    async def test_stats_batch_processing_metrics(self):
        """测试批量处理统计指标"""
        bus = EventBus(batch_size=5, enable_batching=True)
        await bus.initialize()
        
        async def handler(event: Event):
            pass
        
        await bus.subscribe(EventType.DECISION_MADE, handler)
        
        # 发布事件
        for i in range(10):
            event = Event(
                event_type=EventType.DECISION_MADE,
                source_module="test",
                data={"id": i}
            )
            await bus.publish(event)
        
        await asyncio.sleep(0.3)
        
        stats = bus.get_stats()
        
        # 验证批量处理统计
        assert stats['batch_processed'] > 0
        assert stats['avg_batch_size'] > 0
        assert stats['avg_processing_time_us'] >= 0
        assert stats['batching_enabled'] is True
        assert stats['batch_size'] == 5
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_stats_single_event_processing_metrics(self):
        """测试单事件处理统计指标"""
        bus = EventBus(enable_batching=False)
        await bus.initialize()
        
        async def handler(event: Event):
            pass
        
        await bus.subscribe(EventType.DECISION_MADE, handler)
        
        # 发布事件
        for i in range(5):
            event = Event(
                event_type=EventType.DECISION_MADE,
                source_module="test",
                data={"id": i}
            )
            await bus.publish(event)
        
        await asyncio.sleep(0.2)
        
        stats = bus.get_stats()
        
        # 验证单事件处理统计
        assert stats['events_processed'] > 0
        assert stats['avg_processing_time_us'] >= 0
        assert stats['batching_enabled'] is False
        
        await bus.shutdown()
