"""事件驱动通信集成测试

白皮书依据: 第二章 2.8 事件驱动通信
Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import pytest
import asyncio
import time
import numpy as np

from src.infra.event_bus import EventBus, EventType, EventPriority, Event
from src.brain.meta_learning.risk_control_meta_learner import RiskControlMetaLearner
from src.brain.meta_learning.data_models import MarketContext, PerformanceMetrics
from src.brain.algo_hunter.algo_hunter import AlgoHunter
from src.brain.algo_evolution.algo_evolution_sentinel import AlgoEvolutionSentinel


class TestEventDrivenCommunicationIntegration:
    """事件驱动通信集成测试
    
    **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
    """
    
    @pytest.mark.asyncio
    async def test_component_event_communication(self):
        """测试组件间事件通信
        
        **Validates: Requirements 6.1**
        
        验证多个组件通过EventBus进行通信
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
            
            hunter = AlgoHunter(
                device='cpu',
                event_bus=event_bus
            )
            
            sentinel = AlgoEvolutionSentinel(
                event_bus=event_bus,
                scan_interval=3600
            )
            
            # 订阅事件
            learner_events = []
            hunter_events = []
            sentinel_events = []
            
            async def learner_event_handler(event: Event):
                learner_events.append(event)
            
            async def hunter_event_handler(event: Event):
                hunter_events.append(event)
            
            async def sentinel_event_handler(event: Event):
                sentinel_events.append(event)
            
            await event_bus.subscribe(EventType.ANALYSIS_COMPLETED, learner_event_handler)
            await event_bus.subscribe(EventType.ANALYSIS_COMPLETED, hunter_event_handler)
            await event_bus.subscribe(EventType.STRATEGY_GENERATED, sentinel_event_handler)
            
            # 触发事件
            # 1. RiskControlMetaLearner发布事件
            market_context = MarketContext(
                volatility=0.15,
                liquidity=0.8,
                trend_strength=0.6,
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
            
            for _ in range(10):
                await learner.observe_and_learn(market_context, perf_a, perf_b)
            
            # 2. AlgoHunter发布事件
            tick_data = np.random.randn(50, 5).astype(np.float32)
            await hunter.detect_main_force(tick_data)
            
            # 等待事件处理
            await asyncio.sleep(0.3)
            
            # 验证：事件被正确分发
            assert len(learner_events) > 0, "learner应该收到ANALYSIS_COMPLETED事件"
            assert len(hunter_events) > 0, "hunter应该收到ANALYSIS_COMPLETED事件"
            
            # 验证：事件来源正确
            learner_event_sources = [e.source_module for e in learner_events]
            assert 'risk_control_meta_learner' in learner_event_sources or 'algo_hunter' in learner_event_sources
            
        finally:
            await event_bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_event_distribution_latency(self):
        """测试事件分发延迟
        
        **Validates: Requirements 6.4**
        
        验证事件分发延迟满足性能要求
        """
        # 创建EventBus
        event_bus = EventBus()
        await event_bus.initialize()
        
        try:
            # 订阅事件
            event_received_times = []
            
            async def latency_handler(event: Event):
                event_received_times.append(time.perf_counter())
            
            await event_bus.subscribe(EventType.SYSTEM_ALERT, latency_handler)
            
            # 发布多个事件并测量延迟
            num_events = 100
            publish_times = []
            
            for i in range(num_events):
                publish_start = time.perf_counter()
                await event_bus.publish_simple(
                    event_type=EventType.SYSTEM_ALERT,
                    source_module='test',
                    data={'index': i}
                )
                publish_times.append(time.perf_counter() - publish_start)
            
            # 等待所有事件处理完成
            await asyncio.sleep(1.0)
            
            # 验证：所有事件都被处理
            assert len(event_received_times) == num_events, \
                f"所有事件应该被处理。处理了 {len(event_received_times)}/{num_events} 个事件"
            
            # 验证：发布延迟低（异步发布应该很快）
            avg_publish_latency_ms = (sum(publish_times) / len(publish_times)) * 1000
            assert avg_publish_latency_ms < 10.0, \
                f"平均发布延迟应该 < 10ms，当前: {avg_publish_latency_ms:.2f}ms"
            
            # 获取EventBus统计信息
            stats = event_bus.get_stats()
            assert stats['events_published'] == num_events
            assert stats['events_processed'] == num_events
            
        finally:
            await event_bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_event_processing_failure_recovery(self):
        """测试事件处理失败恢复
        
        **Validates: Requirements 6.5**
        
        验证事件处理失败时的恢复机制
        """
        # 创建EventBus
        event_bus = EventBus()
        await event_bus.initialize()
        
        try:
            # 创建会失败的处理器
            successful_events = []
            failed_count = [0]
            
            async def failing_handler(event: Event):
                """前3次失败，之后成功"""
                if failed_count[0] < 3:
                    failed_count[0] += 1
                    raise ValueError("模拟处理失败")
                successful_events.append(event)
            
            async def backup_handler(event: Event):
                """备用处理器，总是成功"""
                successful_events.append(event)
            
            # 订阅事件
            await event_bus.subscribe(EventType.SYSTEM_ALERT, failing_handler)
            await event_bus.subscribe(EventType.SYSTEM_ALERT, backup_handler)
            
            # 发布事件
            num_events = 5
            for i in range(num_events):
                await event_bus.publish_simple(
                    event_type=EventType.SYSTEM_ALERT,
                    source_module='test',
                    data={'index': i}
                )
            
            # 等待事件处理
            await asyncio.sleep(0.5)
            
            # 验证：即使有处理器失败，备用处理器仍然处理了所有事件
            assert len(successful_events) >= num_events, \
                f"至少应该有 {num_events} 个事件被处理（备用处理器）"
            
            # 验证：EventBus记录了失败
            stats = event_bus.get_stats()
            assert stats['events_failed'] > 0, "应该记录失败的事件"
            
        finally:
            await event_bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_priority_event_processing(self):
        """测试优先级事件处理
        
        **Validates: Requirements 6.2**
        
        验证高优先级事件优先处理
        """
        # 创建EventBus
        event_bus = EventBus()
        await event_bus.initialize()
        
        try:
            # 订阅事件
            processed_events = []
            
            async def priority_handler(event: Event):
                processed_events.append(event)
            
            await event_bus.subscribe(EventType.SYSTEM_ALERT, priority_handler)
            
            # 发布不同优先级的事件
            await event_bus.publish_simple(
                event_type=EventType.SYSTEM_ALERT,
                source_module='test',
                data={'priority': 'low'},
                priority=EventPriority.LOW
            )
            
            await event_bus.publish_simple(
                event_type=EventType.SYSTEM_ALERT,
                source_module='test',
                data={'priority': 'critical'},
                priority=EventPriority.CRITICAL
            )
            
            await event_bus.publish_simple(
                event_type=EventType.SYSTEM_ALERT,
                source_module='test',
                data={'priority': 'normal'},
                priority=EventPriority.NORMAL
            )
            
            await event_bus.publish_simple(
                event_type=EventType.SYSTEM_ALERT,
                source_module='test',
                data={'priority': 'high'},
                priority=EventPriority.HIGH
            )
            
            # 等待事件处理
            await asyncio.sleep(0.5)
            
            # 验证：所有事件都被处理
            assert len(processed_events) == 4, "所有事件应该被处理"
            
            # 验证：高优先级事件先处理
            # CRITICAL应该在前面
            priorities = [e.priority for e in processed_events]
            critical_index = priorities.index(EventPriority.CRITICAL)
            low_index = priorities.index(EventPriority.LOW)
            
            assert critical_index < low_index, \
                "CRITICAL事件应该在LOW事件之前处理"
            
        finally:
            await event_bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_targeted_event_communication(self):
        """测试目标事件通信
        
        **Validates: Requirements 6.3**
        
        验证目标事件只发送给指定模块
        """
        # 创建EventBus
        event_bus = EventBus()
        await event_bus.initialize()
        
        try:
            # 创建多个模块的处理器
            module_a_events = []
            module_b_events = []
            
            async def module_a_handler(event: Event):
                module_a_events.append(event)
            
            async def module_b_handler(event: Event):
                module_b_events.append(event)
            
            # 订阅事件
            await event_bus.subscribe(
                EventType.SYSTEM_QUERY,
                module_a_handler,
                handler_id='module_a_handler'
            )
            await event_bus.subscribe(
                EventType.SYSTEM_QUERY,
                module_b_handler,
                handler_id='module_b_handler'
            )
            
            # 发布目标事件给module_a
            await event_bus.publish_simple(
                event_type=EventType.SYSTEM_QUERY,
                source_module='requester',
                target_module='module_a',
                data={'query': 'for_module_a'}
            )
            
            # 发布目标事件给module_b
            await event_bus.publish_simple(
                event_type=EventType.SYSTEM_QUERY,
                source_module='requester',
                target_module='module_b',
                data={'query': 'for_module_b'}
            )
            
            # 等待事件处理
            await asyncio.sleep(0.3)
            
            # 验证：module_a只收到给它的事件
            assert len(module_a_events) == 1, "module_a应该收到1个事件"
            assert module_a_events[0].data['query'] == 'for_module_a'
            
            # 验证：module_b只收到给它的事件
            assert len(module_b_events) == 1, "module_b应该收到1个事件"
            assert module_b_events[0].data['query'] == 'for_module_b'
            
        finally:
            await event_bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_event_bus_statistics(self):
        """测试EventBus统计信息
        
        **Validates: Requirements 6.4**
        
        验证EventBus正确记录统计信息
        """
        # 创建EventBus
        event_bus = EventBus()
        await event_bus.initialize()
        
        try:
            # 订阅事件
            async def stats_handler(event: Event):
                pass
            
            await event_bus.subscribe(EventType.SYSTEM_ALERT, stats_handler)
            
            # 发布事件
            num_events = 50
            for i in range(num_events):
                await event_bus.publish_simple(
                    event_type=EventType.SYSTEM_ALERT,
                    source_module='test',
                    data={'index': i}
                )
            
            # 等待事件处理
            await asyncio.sleep(1.0)
            
            # 获取统计信息
            stats = event_bus.get_stats()
            
            # 验证：统计信息正确
            assert stats['events_published'] == num_events, \
                f"应该发布 {num_events} 个事件，实际: {stats['events_published']}"
            
            assert stats['events_processed'] == num_events, \
                f"应该处理 {num_events} 个事件，实际: {stats['events_processed']}"
            
            assert stats['handlers_registered'] >= 1, \
                "应该至少有1个处理器注册"
            
            assert stats['uptime_seconds'] > 0, \
                "运行时间应该 > 0"
            
            assert stats['events_per_second'] > 0, \
                "事件处理速率应该 > 0"
            
        finally:
            await event_bus.shutdown()
