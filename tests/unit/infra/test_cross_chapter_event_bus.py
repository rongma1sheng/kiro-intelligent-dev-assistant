"""Unit Tests: Cross-Chapter Event Bus

白皮书依据: 第十二章 12.1-12.10 跨章节集成

测试目标:
- 跨章节事件发布和订阅
- 事件路由验证
- 章节间通信
- 统计信息收集
"""

import pytest
import asyncio
from datetime import datetime
from typing import List

from src.infra.event_bus import EventBus, EventPriority
from src.infra.cross_chapter_event_bus import (
    CrossChapterEventBus,
    CrossChapterEvent,
    CrossChapterEventType,
    get_cross_chapter_event_bus,
    publish_cross_chapter_event,
    subscribe_cross_chapter_event
)


class TestCrossChapterEventBus:
    """跨章节事件总线单元测试
    
    白皮书依据: 第十二章 12.1 跨章节事件总线
    """
    
    @pytest.fixture
    async def base_event_bus(self):
        """创建基础事件总线"""
        bus = EventBus()
        await bus.initialize()
        yield bus
        await bus.shutdown()
    
    @pytest.fixture
    async def cross_chapter_bus(self, base_event_bus):
        """创建跨章节事件总线"""
        bus = CrossChapterEventBus(base_event_bus)
        await bus.initialize()
        return bus
    
    @pytest.mark.asyncio
    async def test_initialization(self, cross_chapter_bus):
        """测试初始化"""
        assert cross_chapter_bus.base_event_bus is not None
        assert cross_chapter_bus.stats['start_time'] is not None
        assert len(cross_chapter_bus.routing_table) > 0
    
    @pytest.mark.asyncio
    async def test_publish_cross_chapter_event(self, cross_chapter_bus):
        """测试发布跨章节事件"""
        event = CrossChapterEvent(
            event_type=CrossChapterEventType.HEALTH_CHECK_FAILED,
            source_chapter=10,
            target_chapter=13,
            data={'component': 'redis', 'error': 'connection timeout'}
        )
        
        success = await cross_chapter_bus.publish(event)
        
        assert success is True
        assert cross_chapter_bus.stats['events_published'] == 1
    
    @pytest.mark.asyncio
    async def test_subscribe_and_receive_event(self, cross_chapter_bus):
        """测试订阅和接收跨章节事件"""
        received_events = []
        
        async def handler(event: CrossChapterEvent):
            received_events.append(event)
        
        # 订阅事件
        await cross_chapter_bus.subscribe(
            CrossChapterEventType.HEALTH_CHECK_FAILED,
            handler
        )
        
        # 发布事件
        event = CrossChapterEvent(
            event_type=CrossChapterEventType.HEALTH_CHECK_FAILED,
            source_chapter=10,
            target_chapter=13,
            data={'component': 'redis'}
        )
        
        await cross_chapter_bus.publish(event)
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        # 验证事件接收
        assert len(received_events) == 1
        assert received_events[0].event_type == CrossChapterEventType.HEALTH_CHECK_FAILED
        assert received_events[0].source_chapter == 10
        assert received_events[0].target_chapter == 13
    
    @pytest.mark.asyncio
    async def test_routing_validation(self, cross_chapter_bus):
        """测试路由验证"""
        # 有效路由
        assert cross_chapter_bus._validate_routing(10, 13) is True
        assert cross_chapter_bus._validate_routing(16, 13) is True
        
        # 无效路由
        assert cross_chapter_bus._validate_routing(10, 99) is False
        assert cross_chapter_bus._validate_routing(99, 13) is False
    
    @pytest.mark.asyncio
    async def test_event_conversion(self, cross_chapter_bus):
        """测试事件转换"""
        cross_event = CrossChapterEvent(
            event_type=CrossChapterEventType.PERFORMANCE_REGRESSION_DETECTED,
            source_chapter=16,
            target_chapter=13,
            data={'metric': 'soldier_latency', 'degradation': 0.15},
            priority=EventPriority.HIGH
        )
        
        base_event = cross_event.to_base_event()
        
        assert base_event.source_module == "chapter_16"
        assert base_event.target_module == "chapter_13"
        assert base_event.priority == EventPriority.HIGH
        assert base_event.metadata['is_cross_chapter'] is True
        assert base_event.data['cross_chapter_event_type'] == CrossChapterEventType.PERFORMANCE_REGRESSION_DETECTED.value
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, cross_chapter_bus):
        """测试多个订阅者"""
        received_count = [0, 0]
        
        async def handler1(event: CrossChapterEvent):
            received_count[0] += 1
        
        async def handler2(event: CrossChapterEvent):
            received_count[1] += 1
        
        # 订阅同一事件
        await cross_chapter_bus.subscribe(
            CrossChapterEventType.COST_LIMIT_EXCEEDED,
            handler1
        )
        await cross_chapter_bus.subscribe(
            CrossChapterEventType.COST_LIMIT_EXCEEDED,
            handler2
        )
        
        # 发布事件
        event = CrossChapterEvent(
            event_type=CrossChapterEventType.COST_LIMIT_EXCEEDED,
            source_chapter=18,
            target_chapter=13,
            data={'cost': 100.0, 'limit': 50.0}
        )
        
        await cross_chapter_bus.publish(event)
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        # 验证两个处理器都收到事件
        assert received_count[0] == 1
        assert received_count[1] == 1
    
    @pytest.mark.asyncio
    async def test_get_routing_table(self, cross_chapter_bus):
        """测试获取路由表"""
        routing_table = cross_chapter_bus.get_routing_table()
        
        assert isinstance(routing_table, dict)
        assert 10 in routing_table
        assert 13 in routing_table[10]
        assert 19 in routing_table[10]
    
    @pytest.mark.asyncio
    async def test_get_stats(self, cross_chapter_bus):
        """测试获取统计信息"""
        # 发布几个事件
        for i in range(3):
            event = CrossChapterEvent(
                event_type=CrossChapterEventType.MONITORING_ALERT,
                source_chapter=13,
                target_chapter=19,
                data={'alert_level': 'warning'}
            )
            await cross_chapter_bus.publish(event)
        
        stats = cross_chapter_bus.get_stats()
        
        assert stats['events_published'] == 3
        assert stats['uptime_seconds'] > 0
        assert 'events_per_second' in stats
        assert 'routing_success_rate' in stats


class TestCrossChapterEventTypes:
    """跨章节事件类型测试"""
    
    def test_all_event_types_defined(self):
        """测试所有事件类型已定义"""
        expected_types = [
            'HEALTH_CHECK_FAILED',
            'HEALTH_CHECK_RECOVERED',
            'MONITORING_ALERT',
            'PERFORMANCE_DEGRADATION',
            'COST_LIMIT_EXCEEDED',
            'COST_BUDGET_WARNING',
            'RISK_LEVEL_CHANGED',
            'EMERGENCY_TRIGGERED',
            'DOOMSDAY_TRIGGERED',
            'DOOMSDAY_RESET',
            'PERFORMANCE_REGRESSION_DETECTED',
            'COVERAGE_GATE_FAILED',
            'QUALITY_CHECK_FAILED'
        ]
        
        for event_type_name in expected_types:
            assert hasattr(CrossChapterEventType, event_type_name)


class TestCrossChapterEventObject:
    """跨章节事件对象测试"""
    
    def test_event_creation(self):
        """测试事件创建"""
        event = CrossChapterEvent(
            event_type=CrossChapterEventType.RISK_LEVEL_CHANGED,
            source_chapter=19,
            target_chapter=13,
            data={'risk_level': 'high', 'symbol': '000001.SZ'}
        )
        
        assert event.event_type == CrossChapterEventType.RISK_LEVEL_CHANGED
        assert event.source_chapter == 19
        assert event.target_chapter == 13
        assert event.data['risk_level'] == 'high'
        assert event.priority == EventPriority.NORMAL
        assert isinstance(event.created_at, datetime)
    
    def test_event_with_priority(self):
        """测试带优先级的事件"""
        event = CrossChapterEvent(
            event_type=CrossChapterEventType.EMERGENCY_TRIGGERED,
            source_chapter=19,
            target_chapter=13,
            data={'emergency_level': 'critical'},
            priority=EventPriority.CRITICAL
        )
        
        assert event.priority == EventPriority.CRITICAL


class TestGlobalFunctions:
    """全局函数测试"""
    
    @pytest.mark.asyncio
    async def test_get_cross_chapter_event_bus(self):
        """测试获取全局跨章节事件总线"""
        bus = await get_cross_chapter_event_bus()
        
        assert isinstance(bus, CrossChapterEventBus)
        assert bus.base_event_bus is not None
        
        # 清理
        await bus.base_event_bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_publish_cross_chapter_event_global(self):
        """测试全局发布函数"""
        success = await publish_cross_chapter_event(
            event_type=CrossChapterEventType.DOOMSDAY_TRIGGERED,
            source_chapter=12,
            target_chapter=19,
            data={'trigger_reason': 'fund_loss_exceeded'},
            priority=EventPriority.CRITICAL
        )
        
        assert success is True
        
        # 清理
        bus = await get_cross_chapter_event_bus()
        await bus.base_event_bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_subscribe_cross_chapter_event_global(self):
        """测试全局订阅函数"""
        received_events = []
        
        async def handler(event: CrossChapterEvent):
            received_events.append(event)
        
        handler_id = await subscribe_cross_chapter_event(
            CrossChapterEventType.QUALITY_CHECK_FAILED,
            handler
        )
        
        assert handler_id is not None
        
        # 清理
        bus = await get_cross_chapter_event_bus()
        await bus.base_event_bus.shutdown()


class TestEdgeCases:
    """边界情况测试"""
    
    @pytest.fixture
    async def base_event_bus(self):
        """创建基础事件总线"""
        bus = EventBus()
        await bus.initialize()
        yield bus
        await bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_invalid_event_type(self, base_event_bus):
        """测试无效事件类型"""
        bus = CrossChapterEventBus(base_event_bus)
        await bus.initialize()
        
        # 尝试发布非CrossChapterEvent对象（应该返回False）
        success = await bus.publish("invalid_event")
        assert success is False
        assert bus.stats['routing_errors'] == 1
    
    @pytest.mark.asyncio
    async def test_undefined_routing(self, base_event_bus):
        """测试未定义的路由"""
        bus = CrossChapterEventBus(base_event_bus)
        await bus.initialize()
        
        # 发布未定义路由的事件（应该成功但有警告）
        event = CrossChapterEvent(
            event_type=CrossChapterEventType.MONITORING_ALERT,
            source_chapter=99,  # 未定义的源章节
            target_chapter=13,
            data={'alert': 'test'}
        )
        
        success = await bus.publish(event)
        assert success is True  # 仍然应该成功发布
    
    @pytest.mark.asyncio
    async def test_handler_exception(self, base_event_bus):
        """测试处理器异常"""
        bus = CrossChapterEventBus(base_event_bus)
        await bus.initialize()
        
        async def failing_handler(event: CrossChapterEvent):
            raise ValueError("Handler error")
        
        await bus.subscribe(
            CrossChapterEventType.HEALTH_CHECK_FAILED,
            failing_handler
        )
        
        event = CrossChapterEvent(
            event_type=CrossChapterEventType.HEALTH_CHECK_FAILED,
            source_chapter=10,
            target_chapter=13,
            data={'test': 'data'}
        )
        
        # 应该不会抛出异常
        success = await bus.publish(event)
        assert success is True
        
        # 等待处理
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
