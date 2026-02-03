"""事件驱动通信属性测试

白皮书依据: 第二章 2.8 事件驱动通信
Requirements: 6.1, 6.2, 6.3
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings
from unittest.mock import AsyncMock, Mock
import numpy as np

from src.infra.event_bus import EventBus, EventType, EventPriority, Event
from src.brain.meta_learning.risk_control_meta_learner import RiskControlMetaLearner
from src.brain.meta_learning.data_models import MarketContext, PerformanceMetrics
from src.brain.algo_hunter.algo_hunter import AlgoHunter
from src.brain.algo_evolution.algo_evolution_sentinel import AlgoEvolutionSentinel


class TestEventDrivenCommunicationProperties:
    """事件驱动通信属性测试
    
    **Validates: Requirements 6.1, 6.2, 6.3**
    """
    
    @pytest.mark.asyncio
    @given(
        volatility=st.floats(min_value=0.0, max_value=1.0),
        liquidity=st.floats(min_value=0.0, max_value=1.0),
        trend_strength=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=10, deadline=5000)
    async def test_property_5_components_publish_events_instead_of_direct_calls(
        self,
        volatility: float,
        liquidity: float,
        trend_strength: float
    ):
        """Property 5: Components publish events instead of direct calls
        
        **Validates: Requirements 6.1**
        
        验证组件通过EventBus发布事件，而不是直接调用其他组件的方法
        
        Property:
            ∀ component, action:
                component.perform_action() → EventBus.publish(event)
                NOT component.perform_action() → other_component.method()
        """
        # 创建EventBus
        event_bus = EventBus()
        await event_bus.initialize()
        
        try:
            # 创建组件
            learner = RiskControlMetaLearner(
                min_samples_for_training=10,
                event_bus=event_bus
            )
            
            # 订阅事件
            events_received = []
            
            async def event_handler(event: Event):
                events_received.append(event)
            
            await event_bus.subscribe(EventType.ANALYSIS_COMPLETED, event_handler)
            await event_bus.subscribe(EventType.STRATEGY_GENERATED, event_handler)
            await event_bus.subscribe(EventType.DECISION_MADE, event_handler)
            
            # 执行操作（触发事件发布）
            market_context = MarketContext(
                volatility=volatility,
                liquidity=liquidity,
                trend_strength=trend_strength,
                regime='bull',
                aum=1000000.0,
                portfolio_concentration=0.3,
                recent_drawdown=0.05
            )
            
            perf_a = PerformanceMetrics(
                sharpe_ratio=1.2,
                max_drawdown=0.12,
                win_rate=0.55,
                profit_factor=1.5,
                calmar_ratio=1.0,
                sortino_ratio=1.3,
                decision_latency_ms=30.0
            )
            
            perf_b = PerformanceMetrics(
                sharpe_ratio=1.5,
                max_drawdown=0.10,
                win_rate=0.60,
                profit_factor=1.8,
                calmar_ratio=1.2,
                sortino_ratio=1.6,
                decision_latency_ms=50.0
            )
            
            # 触发学习（应该发布事件）
            for _ in range(10):
                await learner.observe_and_learn(market_context, perf_a, perf_b)
            
            # 等待事件处理
            await asyncio.sleep(0.1)
            
            # 验证：组件发布了事件（而不是直接调用）
            assert len(events_received) > 0, "组件应该发布事件"
            
            # 验证：事件类型正确
            event_types = [e.event_type for e in events_received]
            assert EventType.ANALYSIS_COMPLETED in event_types, "应该发布ANALYSIS_COMPLETED事件"
            
        finally:
            await event_bus.shutdown()
    
    @pytest.mark.asyncio
    @given(
        num_events=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=5, deadline=5000)
    async def test_property_18_eventbus_distributes_events_asynchronously(
        self,
        num_events: int
    ):
        """Property 18: EventBus distributes events asynchronously
        
        **Validates: Requirements 6.2**
        
        验证EventBus异步分发事件，不阻塞发布者
        
        Property:
            ∀ event:
                publish(event) returns immediately
                AND event is processed asynchronously
        """
        # 创建EventBus
        event_bus = EventBus()
        await event_bus.initialize()
        
        try:
            # 订阅事件
            events_processed = []
            processing_times = []
            
            async def slow_handler(event: Event):
                """慢速处理器，模拟耗时操作"""
                start_time = asyncio.get_event_loop().time()
                await asyncio.sleep(0.01)  # 模拟10ms处理时间
                events_processed.append(event)
                processing_times.append(asyncio.get_event_loop().time() - start_time)
            
            await event_bus.subscribe(EventType.SYSTEM_ALERT, slow_handler)
            
            # 发布多个事件
            publish_start = asyncio.get_event_loop().time()
            
            for i in range(num_events):
                await event_bus.publish_simple(
                    event_type=EventType.SYSTEM_ALERT,
                    source_module='test',
                    data={'index': i}
                )
            
            publish_duration = asyncio.get_event_loop().time() - publish_start
            
            # 验证：发布操作快速完成（不等待处理）
            # 发布num_events个事件应该远快于处理它们的时间
            expected_processing_time = num_events * 0.01  # 每个事件10ms
            assert publish_duration < expected_processing_time * 0.5, \
                f"发布应该是异步的，不应该等待处理完成。发布耗时: {publish_duration:.3f}s, 预期处理时间: {expected_processing_time:.3f}s"
            
            # 等待所有事件处理完成
            await asyncio.sleep(expected_processing_time + 0.5)
            
            # 验证：所有事件最终都被处理
            assert len(events_processed) == num_events, \
                f"所有事件应该被处理。处理了 {len(events_processed)}/{num_events} 个事件"
            
        finally:
            await event_bus.shutdown()
    
    @pytest.mark.asyncio
    @given(
        target_module=st.sampled_from(['module_a', 'module_b', 'module_c'])
    )
    @settings(max_examples=5, deadline=5000)
    async def test_property_19_components_use_async_request_response_pattern(
        self,
        target_module: str
    ):
        """Property 19: Components use async request-response pattern
        
        **Validates: Requirements 6.3**
        
        验证组件使用异步请求-响应模式进行点对点通信
        
        Property:
            ∀ request_event with target_module:
                ONLY handlers from target_module receive the event
                AND other modules do NOT receive the event
        """
        # 创建EventBus
        event_bus = EventBus()
        await event_bus.initialize()
        
        try:
            # 创建多个模块的处理器
            module_a_events = []
            module_b_events = []
            module_c_events = []
            
            async def module_a_handler(event: Event):
                module_a_events.append(event)
            
            async def module_b_handler(event: Event):
                module_b_events.append(event)
            
            async def module_c_handler(event: Event):
                module_c_events.append(event)
            
            # 订阅事件（使用模块名作为handler_id前缀）
            await event_bus.subscribe(
                EventType.SYSTEM_QUERY,
                module_a_handler,
                handler_id='module_a_query_handler'
            )
            await event_bus.subscribe(
                EventType.SYSTEM_QUERY,
                module_b_handler,
                handler_id='module_b_query_handler'
            )
            await event_bus.subscribe(
                EventType.SYSTEM_QUERY,
                module_c_handler,
                handler_id='module_c_query_handler'
            )
            
            # 发布目标事件
            await event_bus.publish_simple(
                event_type=EventType.SYSTEM_QUERY,
                source_module='requester',
                target_module=target_module,
                data={'query': 'test_query'}
            )
            
            # 等待事件处理
            await asyncio.sleep(0.2)
            
            # 验证：只有目标模块收到事件
            if target_module == 'module_a':
                assert len(module_a_events) == 1, "module_a应该收到事件"
                assert len(module_b_events) == 0, "module_b不应该收到事件"
                assert len(module_c_events) == 0, "module_c不应该收到事件"
            elif target_module == 'module_b':
                assert len(module_a_events) == 0, "module_a不应该收到事件"
                assert len(module_b_events) == 1, "module_b应该收到事件"
                assert len(module_c_events) == 0, "module_c不应该收到事件"
            elif target_module == 'module_c':
                assert len(module_a_events) == 0, "module_a不应该收到事件"
                assert len(module_b_events) == 0, "module_b不应该收到事件"
                assert len(module_c_events) == 1, "module_c应该收到事件"
            
        finally:
            await event_bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_property_broadcast_events_reach_all_subscribers(self):
        """Property: Broadcast events reach all subscribers
        
        **Validates: Requirements 6.1**
        
        验证广播事件（target_module=None）到达所有订阅者
        
        Property:
            ∀ event with target_module=None:
                ALL subscribers receive the event
        """
        # 创建EventBus
        event_bus = EventBus()
        await event_bus.initialize()
        
        try:
            # 创建多个订阅者
            subscriber_1_events = []
            subscriber_2_events = []
            subscriber_3_events = []
            
            async def subscriber_1_handler(event: Event):
                subscriber_1_events.append(event)
            
            async def subscriber_2_handler(event: Event):
                subscriber_2_events.append(event)
            
            async def subscriber_3_handler(event: Event):
                subscriber_3_events.append(event)
            
            # 订阅事件
            await event_bus.subscribe(EventType.SYSTEM_ALERT, subscriber_1_handler)
            await event_bus.subscribe(EventType.SYSTEM_ALERT, subscriber_2_handler)
            await event_bus.subscribe(EventType.SYSTEM_ALERT, subscriber_3_handler)
            
            # 发布广播事件（target_module=None）
            await event_bus.publish_simple(
                event_type=EventType.SYSTEM_ALERT,
                source_module='broadcaster',
                target_module=None,  # 广播
                data={'message': 'broadcast_test'}
            )
            
            # 等待事件处理
            await asyncio.sleep(0.2)
            
            # 验证：所有订阅者都收到事件
            assert len(subscriber_1_events) == 1, "订阅者1应该收到广播事件"
            assert len(subscriber_2_events) == 1, "订阅者2应该收到广播事件"
            assert len(subscriber_3_events) == 1, "订阅者3应该收到广播事件"
            
            # 验证：事件内容一致
            assert subscriber_1_events[0].data['message'] == 'broadcast_test'
            assert subscriber_2_events[0].data['message'] == 'broadcast_test'
            assert subscriber_3_events[0].data['message'] == 'broadcast_test'
            
        finally:
            await event_bus.shutdown()
