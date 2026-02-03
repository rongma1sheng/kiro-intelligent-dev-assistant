"""Property-Based Tests for Event-Driven Communication

白皮书依据: 第四章 4.7 事件驱动通信

Properties tested:
- Property 43: Event Publication Completeness
- Property 44: Event Context Completeness
"""

import pytest
import asyncio
from datetime import datetime
from hypothesis import given, strategies as st, settings, HealthCheck
from typing import Dict, Any, List

from src.infra.event_bus import EventBus, Event, EventType
from src.evolution.events.event_publisher import EventPublisher


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def factor_id_strategy(draw):
    """生成因子ID"""
    return f"FACTOR_{draw(st.integers(min_value=1, max_value=1000))}"


@st.composite
def strategy_id_strategy(draw):
    """生成策略ID"""
    return f"STRATEGY_{draw(st.integers(min_value=1, max_value=1000))}"


@st.composite
def arena_score_strategy(draw):
    """生成Arena评分"""
    return draw(st.floats(min_value=0.0, max_value=1.0))


@st.composite
def metrics_strategy(draw):
    """生成指标字典"""
    return {
        'ic': draw(st.floats(min_value=-1.0, max_value=1.0)),
        'ir': draw(st.floats(min_value=-10.0, max_value=10.0)),
        'sharpe_ratio': draw(st.floats(min_value=-5.0, max_value=5.0))
    }


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
async def event_bus():
    """创建事件总线实例"""
    bus = EventBus()
    await bus.initialize()
    yield bus
    await bus.shutdown()


@pytest.fixture
async def event_publisher(event_bus):
    """创建事件发布器实例"""
    return EventPublisher(event_bus, source_module="test_module")


# ============================================================================
# Property 43: Event Publication Completeness
# ============================================================================

@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    factor_id=factor_id_strategy(),
    arena_score=arena_score_strategy(),
    passed=st.booleans()
)
@pytest.mark.asyncio
async def test_property_43_event_publication_completeness(
    factor_id,
    arena_score,
    passed
):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 43: Event Publication Completeness
    
    For any significant system event (Arena completion, simulation completion,
    Z2H certification, decay detection, retirement), the system should publish
    a corresponding event to EventBus.
    
    白皮书依据: 第四章 4.7 事件驱动通信 - Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
    Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
    """
    # 创建事件总线和发布器
    event_bus = EventBus()
    await event_bus.initialize()
    
    try:
        publisher = EventPublisher(event_bus, source_module="test_module")
        
        # 记录接收到的事件
        received_events: List[Event] = []
        
        async def event_handler(event: Event):
            received_events.append(event)
        
        # 订阅所有相关事件类型
        await event_bus.subscribe(EventType.FACTOR_ARENA_COMPLETED, event_handler)
        await event_bus.subscribe(EventType.STRATEGY_ARENA_COMPLETED, event_handler)
        await event_bus.subscribe(EventType.SIMULATION_COMPLETED, event_handler)
        await event_bus.subscribe(EventType.Z2H_CERTIFIED, event_handler)
        await event_bus.subscribe(EventType.FACTOR_DECAY_DETECTED, event_handler)
        await event_bus.subscribe(EventType.STRATEGY_RETIRED, event_handler)
        
        # 发布因子Arena完成事件
        result1 = await publisher.publish_factor_arena_completed(
            factor_id=factor_id,
            arena_score=arena_score,
            passed=passed,
            detailed_metrics={'ic': 0.05, 'ir': 1.2}
        )
        
        # 发布策略Arena完成事件
        strategy_id = f"STRATEGY_{factor_id}"
        result2 = await publisher.publish_strategy_arena_completed(
            strategy_id=strategy_id,
            arena_score=arena_score,
            passed=passed,
            performance_metrics={'sharpe': 1.5, 'drawdown': -0.10}
        )
        
        # 发布模拟验证完成事件
        result3 = await publisher.publish_simulation_completed(
            strategy_id=strategy_id,
            duration_days=30,
            passed=passed,
            final_metrics={'return': 0.08, 'sharpe': 1.3}
        )
        
        # 发布Z2H认证事件
        result4 = await publisher.publish_z2h_certified(
            strategy_id=strategy_id,
            certification_level='GOLD',
            capsule_id=f"CAPSULE_{strategy_id}",
            metrics={'sharpe': 2.1}
        )
        
        # 发布因子衰减检测事件
        result5 = await publisher.publish_factor_decay_detected(
            factor_id=factor_id,
            severity='MILD',
            consecutive_days=10,
            recommended_action='REDUCE_WEIGHT',
            current_ic=0.02
        )
        
        # 发布策略退役事件
        result6 = await publisher.publish_strategy_retired(
            strategy_id=strategy_id,
            reason='SEVERE_DECAY',
            final_metrics={'final_sharpe': 0.5}
        )
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        # 验证：所有事件都应该成功发布
        assert result1, "因子Arena完成事件应该成功发布"
        assert result2, "策略Arena完成事件应该成功发布"
        assert result3, "模拟验证完成事件应该成功发布"
        assert result4, "Z2H认证事件应该成功发布"
        assert result5, "因子衰减检测事件应该成功发布"
        assert result6, "策略退役事件应该成功发布"
        
        # 验证：所有事件都应该被接收
        assert len(received_events) == 6, \
            f"应该接收到6个事件，实际: {len(received_events)}"
        
        # 验证：事件类型应该正确
        event_types = [e.event_type for e in received_events]
        assert EventType.FACTOR_ARENA_COMPLETED in event_types, \
            "应该包含因子Arena完成事件"
        assert EventType.STRATEGY_ARENA_COMPLETED in event_types, \
            "应该包含策略Arena完成事件"
        assert EventType.SIMULATION_COMPLETED in event_types, \
            "应该包含模拟验证完成事件"
        assert EventType.Z2H_CERTIFIED in event_types, \
            "应该包含Z2H认证事件"
        assert EventType.FACTOR_DECAY_DETECTED in event_types, \
            "应该包含因子衰减检测事件"
        assert EventType.STRATEGY_RETIRED in event_types, \
            "应该包含策略退役事件"
    
    finally:
        await event_bus.shutdown()


# ============================================================================
# Property 44: Event Context Completeness
# ============================================================================

@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    factor_id=factor_id_strategy(),
    arena_score=arena_score_strategy(),
    metrics=metrics_strategy()
)
@pytest.mark.asyncio
async def test_property_44_event_context_completeness(
    factor_id,
    arena_score,
    metrics
):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 44: Event Context Completeness
    
    For any published event, it should include complete context data necessary
    for subscribers to process it.
    
    白皮书依据: 第四章 4.7.8 事件上下文完整性 - Requirement 9.8
    Validates: Requirements 9.8
    """
    # 创建事件总线和发布器
    event_bus = EventBus()
    await event_bus.initialize()
    
    try:
        publisher = EventPublisher(event_bus, source_module="test_module")
        
        # 记录接收到的事件
        received_event: Event = None
        
        async def event_handler(event: Event):
            nonlocal received_event
            received_event = event
        
        # 订阅因子Arena完成事件
        await event_bus.subscribe(EventType.FACTOR_ARENA_COMPLETED, event_handler)
        
        # 发布事件
        await publisher.publish_factor_arena_completed(
            factor_id=factor_id,
            arena_score=arena_score,
            passed=True,
            detailed_metrics=metrics
        )
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        # 验证：事件应该被接收
        assert received_event is not None, \
            "事件应该被接收"
        
        # 验证：事件数据应该包含所有必要字段
        assert 'factor_id' in received_event.data, \
            "事件数据应该包含factor_id"
        
        assert 'arena_score' in received_event.data, \
            "事件数据应该包含arena_score"
        
        assert 'passed' in received_event.data, \
            "事件数据应该包含passed"
        
        assert 'detailed_metrics' in received_event.data, \
            "事件数据应该包含detailed_metrics"
        
        assert 'timestamp' in received_event.data, \
            "事件数据应该包含timestamp"
        
        # 验证：数据值应该正确
        assert received_event.data['factor_id'] == factor_id, \
            f"factor_id应该为{factor_id}，实际: {received_event.data['factor_id']}"
        
        assert received_event.data['arena_score'] == arena_score, \
            f"arena_score应该为{arena_score}，实际: {received_event.data['arena_score']}"
        
        assert received_event.data['passed'] == True, \
            "passed应该为True"
        
        # 验证：详细指标应该完整
        detailed_metrics = received_event.data['detailed_metrics']
        assert 'ic' in detailed_metrics, \
            "详细指标应该包含ic"
        
        assert 'ir' in detailed_metrics, \
            "详细指标应该包含ir"
        
        # 验证：时间戳应该有效
        timestamp_str = received_event.data['timestamp']
        timestamp = datetime.fromisoformat(timestamp_str)
        assert isinstance(timestamp, datetime), \
            "时间戳应该是有效的datetime对象"
    
    finally:
        await event_bus.shutdown()
