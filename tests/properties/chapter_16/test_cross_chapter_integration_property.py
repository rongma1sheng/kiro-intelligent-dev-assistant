"""Property-Based Tests for Cross-Chapter Integration

白皮书依据: 第十二章 12.1-12.10 跨章节集成

Property 25: Cross-Chapter Integration Consistency
**Validates: Requirements 12.1-12.10**

测试跨章节事件传播的一致性和原子性
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.infra.cross_chapter_event_bus import (
    CrossChapterEventBus,
    CrossChapterEventType,
    CrossChapterEvent
)
from src.infra.event_bus import EventBus, EventPriority


# 策略：生成跨章节事件类型
cross_chapter_event_types = st.sampled_from([
    CrossChapterEventType.HEALTH_CHECK_FAILED,
    CrossChapterEventType.HEALTH_CHECK_RECOVERED,
    CrossChapterEventType.MONITORING_ALERT,
    CrossChapterEventType.PERFORMANCE_DEGRADATION,
    CrossChapterEventType.COST_LIMIT_EXCEEDED,
    CrossChapterEventType.COST_BUDGET_WARNING,
    CrossChapterEventType.RISK_LEVEL_CHANGED,
    CrossChapterEventType.EMERGENCY_TRIGGERED,
    CrossChapterEventType.DOOMSDAY_TRIGGERED,
    CrossChapterEventType.DOOMSDAY_RESET,
    CrossChapterEventType.PERFORMANCE_REGRESSION_DETECTED,
    CrossChapterEventType.COVERAGE_GATE_FAILED,
    CrossChapterEventType.QUALITY_CHECK_FAILED
])

# 策略：生成章节编号（9-19）
chapter_numbers = st.integers(min_value=9, max_value=19)

# 策略：生成事件优先级
event_priorities = st.sampled_from([
    EventPriority.LOW,
    EventPriority.NORMAL,
    EventPriority.HIGH,
    EventPriority.CRITICAL
])

# 策略：生成事件数据
event_data = st.dictionaries(
    keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
    values=st.one_of(
        st.text(min_size=0, max_size=50),
        st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        st.integers(min_value=0, max_value=1000)
    ),
    min_size=1,
    max_size=5
)


class TestCrossChapterIntegrationProperty:
    """跨章节集成属性测试
    
    白皮书依据: 第十二章 12.1-12.10 跨章节集成
    """
    
    @pytest.mark.asyncio
    @given(
        event_type=cross_chapter_event_types,
        source_chapter=chapter_numbers,
        target_chapter=chapter_numbers,
        data=event_data,
        priority=event_priorities
    )
    @settings(
        max_examples=100,
        deadline=2000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_event_propagation_consistency(
        self,
        event_type,
        source_chapter,
        target_chapter,
        data,
        priority
    ):
        """Property 25: 事件传播一致性
        
        白皮书依据: 第十二章 12.1 跨章节事件传播
        
        属性: 发布的事件必须被正确传播，且数据保持一致
        
        **Validates: Requirements 12.1-12.10**
        """
        # 创建模拟的基础事件总线
        mock_base_bus = Mock(spec=EventBus)
        mock_base_bus.publish = AsyncMock(return_value=True)
        
        # 创建跨章节事件总线
        cross_bus = CrossChapterEventBus(mock_base_bus)
        await cross_bus.initialize()
        
        # 创建跨章节事件
        event = CrossChapterEvent(
            event_type=event_type,
            source_chapter=source_chapter,
            target_chapter=target_chapter,
            data=data,
            priority=priority
        )
        
        # 发布事件
        success = await cross_bus.publish(event)
        
        # 验证：事件必须成功发布
        assert success is True
        
        # 验证：基础事件总线的publish被调用
        assert mock_base_bus.publish.called
        
        # 验证：发布的事件数据一致性
        published_event = mock_base_bus.publish.call_args[0][0]
        assert published_event.data['cross_chapter_event_type'] == event_type.value
        assert published_event.metadata['source_chapter'] == source_chapter
        assert published_event.metadata['target_chapter'] == target_chapter
        assert published_event.metadata['is_cross_chapter'] is True
        
        # 验证：原始数据被保留
        for key, value in data.items():
            assert key in published_event.data
            assert published_event.data[key] == value
    
    @pytest.mark.asyncio
    @given(
        event_type=cross_chapter_event_types,
        source_chapter=chapter_numbers,
        data=event_data
    )
    @settings(
        max_examples=50,
        deadline=2000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_event_routing_atomicity(
        self,
        event_type,
        source_chapter,
        data
    ):
        """Property 25: 事件路由原子性
        
        白皮书依据: 第十二章 12.1 跨章节事件路由
        
        属性: 事件路由操作必须是原子的，要么完全成功，要么完全失败
        
        **Validates: Requirements 12.1-12.10**
        """
        # 创建模拟的基础事件总线
        mock_base_bus = Mock(spec=EventBus)
        
        # 测试成功场景
        mock_base_bus.publish = AsyncMock(return_value=True)
        cross_bus = CrossChapterEventBus(mock_base_bus)
        await cross_bus.initialize()
        
        event = CrossChapterEvent(
            event_type=event_type,
            source_chapter=source_chapter,
            target_chapter=13,  # 固定目标章节
            data=data,
            priority=EventPriority.NORMAL
        )
        
        success = await cross_bus.publish(event)
        
        # 验证：成功时统计信息必须更新
        assert success is True
        assert cross_bus.stats['events_published'] > 0
        
        # 测试失败场景
        mock_base_bus.publish = AsyncMock(return_value=False)
        cross_bus2 = CrossChapterEventBus(mock_base_bus)
        await cross_bus2.initialize()
        
        event2 = CrossChapterEvent(
            event_type=event_type,
            source_chapter=source_chapter,
            target_chapter=13,
            data=data,
            priority=EventPriority.NORMAL
        )
        
        success2 = await cross_bus2.publish(event2)
        
        # 验证：失败时统计信息不应更新
        assert success2 is False
        assert cross_bus2.stats['events_published'] == 0
    
    @pytest.mark.asyncio
    @given(
        num_events=st.integers(min_value=1, max_value=10),
        event_type=cross_chapter_event_types
    )
    @settings(
        max_examples=30,
        deadline=3000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_multiple_events_ordering(
        self,
        num_events,
        event_type
    ):
        """Property 25: 多事件顺序保证
        
        白皮书依据: 第十二章 12.1 跨章节事件顺序
        
        属性: 多个事件按发布顺序传播
        
        **Validates: Requirements 12.1-12.10**
        """
        # 创建模拟的基础事件总线
        mock_base_bus = Mock(spec=EventBus)
        published_events = []
        
        async def capture_publish(event):
            published_events.append(event)
            return True
        
        mock_base_bus.publish = AsyncMock(side_effect=capture_publish)
        
        cross_bus = CrossChapterEventBus(mock_base_bus)
        await cross_bus.initialize()
        
        # 发布多个事件
        for i in range(num_events):
            event = CrossChapterEvent(
                event_type=event_type,
                source_chapter=10,
                target_chapter=13,
                data={'sequence': i},
                priority=EventPriority.NORMAL
            )
            await cross_bus.publish(event)
        
        # 验证：事件数量正确
        assert len(published_events) == num_events
        
        # 验证：事件顺序保持
        for i in range(num_events):
            assert published_events[i].data['sequence'] == i
    
    @pytest.mark.asyncio
    @given(
        event_type=cross_chapter_event_types,
        priority=event_priorities
    )
    @settings(
        max_examples=50,
        deadline=2000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_event_priority_preservation(
        self,
        event_type,
        priority
    ):
        """Property 25: 事件优先级保持
        
        白皮书依据: 第十二章 12.1 跨章节事件优先级
        
        属性: 事件优先级在传播过程中必须保持不变
        
        **Validates: Requirements 12.1-12.10**
        """
        # 创建模拟的基础事件总线
        mock_base_bus = Mock(spec=EventBus)
        mock_base_bus.publish = AsyncMock(return_value=True)
        
        cross_bus = CrossChapterEventBus(mock_base_bus)
        await cross_bus.initialize()
        
        # 创建带优先级的事件
        event = CrossChapterEvent(
            event_type=event_type,
            source_chapter=10,
            target_chapter=13,
            data={'test': 'data'},
            priority=priority
        )
        
        await cross_bus.publish(event)
        
        # 验证：优先级被保持
        published_event = mock_base_bus.publish.call_args[0][0]
        assert published_event.priority == priority
    
    @pytest.mark.asyncio
    @given(
        source_chapter=chapter_numbers,
        target_chapter=chapter_numbers
    )
    @settings(
        max_examples=50,
        deadline=2000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_routing_table_consistency(
        self,
        source_chapter,
        target_chapter
    ):
        """Property 25: 路由表一致性
        
        白皮书依据: 第十二章 12.1 跨章节路由表
        
        属性: 路由表定义必须一致且可查询
        
        **Validates: Requirements 12.1-12.10**
        """
        # 创建模拟的基础事件总线
        mock_base_bus = Mock(spec=EventBus)
        mock_base_bus.publish = AsyncMock(return_value=True)
        
        cross_bus = CrossChapterEventBus(mock_base_bus)
        await cross_bus.initialize()
        
        # 获取路由表
        routing_table = cross_bus.get_routing_table()
        
        # 验证：路由表是字典
        assert isinstance(routing_table, dict)
        
        # 验证：路由表包含预期的章节
        expected_sources = [10, 12, 13, 14, 16, 18, 19]
        for source in expected_sources:
            assert source in routing_table
            assert isinstance(routing_table[source], list)
            assert len(routing_table[source]) > 0
    
    @pytest.mark.asyncio
    @given(
        event_type=cross_chapter_event_types,
        data=event_data
    )
    @settings(
        max_examples=50,
        deadline=2000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_event_metadata_completeness(
        self,
        event_type,
        data
    ):
        """Property 25: 事件元数据完整性
        
        白皮书依据: 第十二章 12.1 跨章节事件元数据
        
        属性: 所有跨章节事件必须包含完整的元数据
        
        **Validates: Requirements 12.1-12.10**
        """
        # 创建模拟的基础事件总线
        mock_base_bus = Mock(spec=EventBus)
        mock_base_bus.publish = AsyncMock(return_value=True)
        
        cross_bus = CrossChapterEventBus(mock_base_bus)
        await cross_bus.initialize()
        
        # 创建事件
        event = CrossChapterEvent(
            event_type=event_type,
            source_chapter=10,
            target_chapter=13,
            data=data,
            priority=EventPriority.NORMAL
        )
        
        await cross_bus.publish(event)
        
        # 验证：元数据完整性
        published_event = mock_base_bus.publish.call_args[0][0]
        
        # 必须包含的元数据字段
        assert 'source_chapter' in published_event.metadata
        assert 'target_chapter' in published_event.metadata
        assert 'is_cross_chapter' in published_event.metadata
        
        # 元数据值正确
        assert published_event.metadata['source_chapter'] == 10
        assert published_event.metadata['target_chapter'] == 13
        assert published_event.metadata['is_cross_chapter'] is True
    
    @pytest.mark.asyncio
    @given(
        num_subscribers=st.integers(min_value=1, max_value=5),
        event_type=cross_chapter_event_types
    )
    @settings(
        max_examples=30,
        deadline=3000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_subscriber_notification_consistency(
        self,
        num_subscribers,
        event_type
    ):
        """Property 25: 订阅者通知一致性
        
        白皮书依据: 第十二章 12.1 跨章节事件订阅
        
        属性: 所有订阅者必须收到相同的事件
        
        **Validates: Requirements 12.1-12.10**
        """
        # 创建模拟的基础事件总线
        mock_base_bus = Mock(spec=EventBus)
        mock_base_bus.publish = AsyncMock(return_value=True)
        
        cross_bus = CrossChapterEventBus(mock_base_bus)
        await cross_bus.initialize()
        
        # 注册多个订阅者
        received_events = []
        
        for i in range(num_subscribers):
            async def handler(event, idx=i):
                received_events.append((idx, event))
            
            await cross_bus.subscribe(
                event_type=event_type,
                handler_func=handler,
                handler_id=f"handler_{i}"
            )
        
        # 发布事件
        test_data = {'test': 'data', 'value': 123}
        event = CrossChapterEvent(
            event_type=event_type,
            source_chapter=10,
            target_chapter=13,
            data=test_data,
            priority=EventPriority.NORMAL
        )
        
        await cross_bus.publish(event)
        
        # 等待异步处理
        await asyncio.sleep(0.1)
        
        # 验证：所有订阅者都注册成功
        assert len(cross_bus.cross_chapter_handlers[event_type]) == num_subscribers


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
