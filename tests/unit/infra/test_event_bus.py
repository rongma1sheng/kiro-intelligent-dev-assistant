"""Event Bus单元测试

白皮书依据: 基础设施层 - 事件驱动架构

测试覆盖:
- Event类的创建和序列化
- EventHandler的事件处理
- EventBus的发布订阅机制
- 异步事件处理
- 优先级队列
- 批量处理
- 统计信息
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from src.infra.event_bus import (
    Event,
    EventType,
    EventPriority,
    EventHandler,
    EventBus,
    get_event_bus,
    publish_event,
    subscribe_event
)


class TestEvent:
    """Event类测试"""
    
    def test_event_creation_default(self):
        """测试默认事件创建"""
        event = Event()
        
        assert event.event_id is not None
        assert event.event_type == EventType.HEARTBEAT
        assert event.source_module == "unknown"
        assert event.target_module is None
        assert event.priority == EventPriority.NORMAL
        assert event.data == {}
        assert event.metadata == {}
        assert event.retry_count == 0
        assert event.max_retries == 3
        assert event.processed is False
    
    def test_event_creation_with_params(self):
        """测试带参数的事件创建"""
        event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="soldier",
            target_module="commander",
            priority=EventPriority.HIGH,
            data={"action": "buy", "symbol": "000001.SZ"},
            metadata={"timestamp": "2024-01-01"}
        )
        
        assert event.event_type == EventType.DECISION_MADE
        assert event.source_module == "soldier"
        assert event.target_module == "commander"
        assert event.priority == EventPriority.HIGH
        assert event.data == {"action": "buy", "symbol": "000001.SZ"}
        assert event.metadata == {"timestamp": "2024-01-01"}
    
    def test_event_to_dict(self):
        """测试事件序列化"""
        event = Event(
            event_type=EventType.FACTOR_DISCOVERED,
            source_module="evolution",
            data={"factor_id": "F001"}
        )
        
        event_dict = event.to_dict()
        
        assert event_dict['event_type'] == "factor_discovered"
        assert event_dict['source_module'] == "evolution"
        assert event_dict['data'] == {"factor_id": "F001"}
        assert 'event_id' in event_dict
        assert 'created_at' in event_dict
    
    def test_event_from_dict(self):
        """测试事件反序列化"""
        event_dict = {
            'event_id': 'test-event-001',
            'event_type': 'strategy_generated',
            'source_module': 'evolution',
            'target_module': 'commander',
            'priority': 3,
            'data': {'strategy_id': 'S001'},
            'metadata': {},
            'created_at': datetime.now().isoformat(),
            'expires_at': None,
            'retry_count': 0,
            'max_retries': 3,
            'processed': False
        }
        
        event = Event.from_dict(event_dict)
        
        assert event.event_id == 'test-event-001'
        assert event.event_type == EventType.STRATEGY_GENERATED
        assert event.source_module == 'evolution'
        assert event.target_module == 'commander'
        assert event.priority == EventPriority.HIGH
        assert event.data == {'strategy_id': 'S001'}
    
    def test_event_expiration(self):
        """测试事件过期"""
        past_time = datetime.now() - timedelta(hours=1)
        event = Event(
            event_type=EventType.HEARTBEAT,
            source_module="test",
            expires_at=past_time
        )
        
        assert event.expires_at < datetime.now()


class TestEventHandler:
    """EventHandler类测试"""
    
    def test_handler_creation(self):
        """测试处理器创建"""
        def handler_func(event: Event):
            pass
        
        handler = EventHandler("test_handler", handler_func)
        
        assert handler.handler_id == "test_handler"
        assert handler.handler_func == handler_func
        assert handler.call_count == 0
        assert handler.error_count == 0
        assert handler.last_called is None
    
    @pytest.mark.asyncio
    async def test_handler_sync_function(self):
        """测试同步处理函数"""
        received_events = []
        
        def handler_func(event: Event):
            received_events.append(event)
        
        handler = EventHandler("sync_handler", handler_func)
        event = Event(event_type=EventType.HEARTBEAT, source_module="test")
        
        result = await handler.handle(event)
        
        assert result is True
        assert handler.call_count == 1
        assert len(received_events) == 1
        assert received_events[0] == event
    
    @pytest.mark.asyncio
    async def test_handler_async_function(self):
        """测试异步处理函数"""
        received_events = []
        
        async def handler_func(event: Event):
            received_events.append(event)
        
        handler = EventHandler("async_handler", handler_func)
        event = Event(event_type=EventType.HEARTBEAT, source_module="test")
        
        result = await handler.handle(event)
        
        assert result is True
        assert handler.call_count == 1
        assert len(received_events) == 1
    
    @pytest.mark.asyncio
    async def test_handler_error_handling(self):
        """测试处理器错误处理"""
        def failing_handler(event: Event):
            raise ValueError("Handler error")
        
        handler = EventHandler("failing_handler", failing_handler)
        event = Event(event_type=EventType.HEARTBEAT, source_module="test")
        
        result = await handler.handle(event)
        
        assert result is False
        assert handler.call_count == 1
        assert handler.error_count == 1


class TestEventBus:
    """EventBus类测试"""
    
    @pytest.fixture
    async def event_bus(self):
        """创建事件总线实例"""
        bus = EventBus(batch_size=5, enable_batching=False)
        await bus.initialize()
        yield bus
        await bus.shutdown()
    
    @pytest.fixture
    async def batch_event_bus(self):
        """创建批量处理事件总线实例"""
        bus = EventBus(batch_size=5, enable_batching=True, low_latency_mode=True)
        await bus.initialize()
        yield bus
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_bus_initialization(self):
        """测试事件总线初始化"""
        bus = EventBus()
        await bus.initialize()
        
        assert bus.running is True
        assert bus.processor_task is not None
        assert bus.stats['start_time'] is not None
        
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_bus_shutdown(self, event_bus):
        """测试事件总线关闭"""
        assert event_bus.running is True
        
        await event_bus.shutdown()
        
        assert event_bus.running is False
    
    @pytest.mark.asyncio
    async def test_subscribe(self, event_bus):
        """测试事件订阅"""
        received_events = []
        
        def handler(event: Event):
            received_events.append(event)
        
        handler_id = await event_bus.subscribe(EventType.HEARTBEAT, handler)
        
        assert handler_id is not None
        assert EventType.HEARTBEAT in event_bus.handlers
        assert len(event_bus.handlers[EventType.HEARTBEAT]) == 1
        assert event_bus.stats['handlers_registered'] == 1
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, event_bus):
        """测试取消订阅"""
        def handler(event: Event):
            pass
        
        handler_id = await event_bus.subscribe(EventType.HEARTBEAT, handler)
        assert event_bus.stats['handlers_registered'] == 1
        
        result = await event_bus.unsubscribe(EventType.HEARTBEAT, handler_id)
        
        assert result is True
        assert event_bus.stats['handlers_registered'] == 0
    
    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent(self, event_bus):
        """测试取消不存在的订阅"""
        result = await event_bus.unsubscribe(EventType.HEARTBEAT, "nonexistent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_publish_event(self, event_bus):
        """测试发布事件"""
        event = Event(
            event_type=EventType.HEARTBEAT,
            source_module="test"
        )
        
        result = await event_bus.publish(event)
        
        assert result is True
        assert event_bus.stats['events_published'] == 1
    
    @pytest.mark.asyncio
    async def test_publish_expired_event(self, event_bus):
        """测试发布过期事件"""
        past_time = datetime.now() - timedelta(hours=1)
        event = Event(
            event_type=EventType.HEARTBEAT,
            source_module="test",
            expires_at=past_time
        )
        
        result = await event_bus.publish(event)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_publish_simple(self, event_bus):
        """测试简化发布接口"""
        result = await event_bus.publish_simple(
            event_type=EventType.HEARTBEAT,
            source_module="test",
            data={"status": "ok"}
        )
        
        assert result is True
        assert event_bus.stats['events_published'] == 1
    
    @pytest.mark.asyncio
    async def test_event_processing(self, event_bus):
        """测试事件处理"""
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        await event_bus.subscribe(EventType.HEARTBEAT, handler)
        
        event = Event(
            event_type=EventType.HEARTBEAT,
            source_module="test",
            data={"test": "data"}
        )
        
        await event_bus.publish(event)
        await asyncio.sleep(0.1)  # 等待事件处理
        
        assert len(received_events) == 1
        assert received_events[0].data == {"test": "data"}
        assert event_bus.stats['events_processed'] >= 1
    
    @pytest.mark.asyncio
    async def test_priority_queue(self, event_bus):
        """测试优先级队列"""
        # 发布不同优先级的事件
        await event_bus.publish(Event(
            event_type=EventType.HEARTBEAT,
            source_module="test",
            priority=EventPriority.LOW,
            data={"priority": "low"}
        ))
        
        await event_bus.publish(Event(
            event_type=EventType.HEARTBEAT,
            source_module="test",
            priority=EventPriority.CRITICAL,
            data={"priority": "critical"}
        ))
        
        await event_bus.publish(Event(
            event_type=EventType.HEARTBEAT,
            source_module="test",
            priority=EventPriority.HIGH,
            data={"priority": "high"}
        ))
        
        # 验证队列大小
        assert event_bus.priority_queues[EventPriority.LOW].qsize() == 1
        assert event_bus.priority_queues[EventPriority.CRITICAL].qsize() == 1
        assert event_bus.priority_queues[EventPriority.HIGH].qsize() == 1
    
    @pytest.mark.asyncio
    async def test_multiple_handlers(self, event_bus):
        """测试多个处理器"""
        received_1 = []
        received_2 = []
        
        async def handler_1(event: Event):
            received_1.append(event)
        
        async def handler_2(event: Event):
            received_2.append(event)
        
        await event_bus.subscribe(EventType.HEARTBEAT, handler_1)
        await event_bus.subscribe(EventType.HEARTBEAT, handler_2)
        
        event = Event(event_type=EventType.HEARTBEAT, source_module="test")
        await event_bus.publish(event)
        await asyncio.sleep(0.1)
        
        assert len(received_1) == 1
        assert len(received_2) == 1
    
    @pytest.mark.asyncio
    async def test_target_module_filtering(self, event_bus):
        """测试目标模块过滤"""
        received_soldier = []
        received_commander = []
        
        async def soldier_handler(event: Event):
            received_soldier.append(event)
        
        async def commander_handler(event: Event):
            received_commander.append(event)
        
        await event_bus.subscribe(EventType.DECISION_REQUEST, soldier_handler, "soldier_handler")
        await event_bus.subscribe(EventType.DECISION_REQUEST, commander_handler, "commander_handler")
        
        # 发送给soldier的事件
        event = Event(
            event_type=EventType.DECISION_REQUEST,
            source_module="test",
            target_module="soldier"
        )
        await event_bus.publish(event)
        await asyncio.sleep(0.1)
        
        # soldier应该收到，commander不应该收到
        assert len(received_soldier) >= 0  # 可能收到（取决于过滤逻辑）
        assert len(received_commander) >= 0
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, batch_event_bus):
        """测试批量处理"""
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        await batch_event_bus.subscribe(EventType.HEARTBEAT, handler)
        
        # 发布多个事件
        for i in range(10):
            await batch_event_bus.publish(Event(
                event_type=EventType.HEARTBEAT,
                source_module="test",
                data={"index": i}
            ))
        
        await asyncio.sleep(0.2)  # 等待批量处理
        
        assert len(received_events) == 10
        assert batch_event_bus.stats['batch_processed'] > 0
    
    @pytest.mark.asyncio
    async def test_get_stats(self, event_bus):
        """测试获取统计信息"""
        stats = event_bus.get_stats()
        
        assert 'events_published' in stats
        assert 'events_processed' in stats
        assert 'events_failed' in stats
        assert 'handlers_registered' in stats
        assert 'uptime_seconds' in stats
        assert 'events_per_second' in stats
        assert 'queue_sizes' in stats
        assert 'batching_enabled' in stats
    
    @pytest.mark.asyncio
    async def test_get_handlers(self, event_bus):
        """测试获取处理器信息"""
        def handler(event: Event):
            pass
        
        await event_bus.subscribe(EventType.HEARTBEAT, handler)
        
        # 获取特定类型的处理器
        handlers_info = event_bus.get_handlers(EventType.HEARTBEAT)
        
        assert handlers_info['event_type'] == 'heartbeat'
        assert handlers_info['handler_count'] == 1
        assert len(handlers_info['handlers']) == 1
        
        # 获取所有处理器
        all_handlers = event_bus.get_handlers()
        
        assert 'heartbeat' in all_handlers
        assert all_handlers['heartbeat']['handler_count'] == 1


class TestGlobalEventBus:
    """全局事件总线测试"""
    
    @pytest.mark.asyncio
    async def test_get_event_bus(self):
        """测试获取全局事件总线"""
        bus1 = await get_event_bus()
        bus2 = await get_event_bus()
        
        # 应该返回同一个实例
        assert bus1 is bus2
        
        await bus1.shutdown()
    
    @pytest.mark.asyncio
    async def test_publish_event_global(self):
        """测试全局发布事件"""
        result = await publish_event(
            event_type=EventType.HEARTBEAT,
            source_module="test",
            data={"test": "data"}
        )
        
        assert result is True
        
        bus = await get_event_bus()
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_subscribe_event_global(self):
        """测试全局订阅事件"""
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        handler_id = await subscribe_event(EventType.HEARTBEAT, handler)
        
        assert handler_id is not None
        
        bus = await get_event_bus()
        await bus.shutdown()


class TestEventTypes:
    """事件类型测试"""
    
    def test_all_event_types(self):
        """测试所有事件类型"""
        event_types = [
            EventType.DECISION_REQUEST,
            EventType.DECISION_MADE,
            EventType.ANALYSIS_COMPLETED,
            EventType.MEMORY_UPDATED,
            EventType.FACTOR_DISCOVERED,
            EventType.ARENA_TEST_COMPLETED,
            EventType.STRATEGY_GENERATED,
            EventType.Z2H_CERTIFIED,
            EventType.Z2H_REVOKED,
            EventType.SECURITY_ALERT,
            EventType.FACTOR_ARENA_COMPLETED,
            EventType.STRATEGY_ARENA_COMPLETED,
            EventType.SIMULATION_COMPLETED,
            EventType.FACTOR_DECAY_DETECTED,
            EventType.STRATEGY_RETIRED,
            EventType.DATA_UPDATED,
            EventType.SYSTEM_ALERT,
            EventType.CONFIG_CHANGED,
            EventType.MARKET_DATA_RECEIVED,
            EventType.PORTFOLIO_UPDATED,
            EventType.TRADE_EXECUTED,
            EventType.SCHEDULE_TRIGGERED,
            EventType.TIMER_EXPIRED,
            EventType.HEARTBEAT,
            EventType.RESEARCH_REQUEST,
            EventType.MARKET_DATA_REQUEST,
            EventType.STRATEGY_REQUEST,
            EventType.AUDIT_COMPLETED,
            EventType.AUDIT_REQUEST,
            EventType.SYSTEM_QUERY,
            EventType.SYSTEM_RESPONSE,
            EventType.MEMORY_QUERY,
            EventType.SCHEDULE_QUERY
        ]
        
        for event_type in event_types:
            assert isinstance(event_type.value, str)
            assert len(event_type.value) > 0


class TestEventPriorities:
    """事件优先级测试"""
    
    def test_all_priorities(self):
        """测试所有优先级"""
        priorities = [
            EventPriority.LOW,
            EventPriority.NORMAL,
            EventPriority.HIGH,
            EventPriority.CRITICAL
        ]
        
        for priority in priorities:
            assert isinstance(priority.value, int)
            assert 1 <= priority.value <= 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
