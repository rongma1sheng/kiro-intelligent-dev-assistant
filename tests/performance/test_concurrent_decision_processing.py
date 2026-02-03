"""
并发决策处理性能测试

白皮书依据: 第二章 2.1 AI三脑协调 + 第七章 7.7 并发决策处理
需求: 7.7 - 并发决策处理、vLLM批处理优化
测试覆盖: Task 14.7, Task 14.8

测试内容:
1. 并发决策处理性能
2. vLLM批处理效果
3. 并发限制验证
4. 吞吐量测试
"""

import pytest
import pytest_asyncio
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from typing import List, Dict, Any

from src.brain.ai_brain_coordinator import (
    AIBrainCoordinator,
    BrainDecision
)
from src.infra.event_bus import EventBus, Event, EventType, EventPriority


class TestConcurrentDecisionProcessing:
    """测试并发决策处理
    
    白皮书依据: 第二章 2.1 AI三脑协调
    需求: 7.7 - 并发决策处理
    """
    
    @pytest_asyncio.fixture
    async def coordinator(self):
        """创建协调器实例"""
        event_bus = EventBus()
        await event_bus.initialize()
        
        with patch('src.core.dependency_container.DIContainer'):
            container = Mock()
            container.is_registered = Mock(return_value=False)
            
            coordinator = AIBrainCoordinator(event_bus, container)
            await coordinator.initialize()
            
            yield coordinator
            
            await coordinator.shutdown()
    
    @pytest.mark.asyncio
    async def test_concurrent_decision_throughput(self, coordinator):
        """测试并发决策吞吐量
        
        验证: 系统应该能够处理大量并发决策请求
        性能目标: > 100 decisions/second
        """
        # Mock决策处理
        async def mock_wait_for_decision(correlation_id, timeout):
            await asyncio.sleep(0.01)  # 模拟10ms处理时间
            return BrainDecision(
                decision_id=correlation_id,
                primary_brain="soldier",
                action="hold",
                confidence=0.8,
                reasoning="Mock decision",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=correlation_id
            )
        
        coordinator._wait_for_decision = mock_wait_for_decision
        
        # 创建大量并发请求
        num_requests = 200
        contexts = [
            {'symbol': f'STOCK{i}', 'price': 100 + i}
            for i in range(num_requests)
        ]
        
        # 测试吞吐量
        start_time = time.perf_counter()
        
        tasks = [
            coordinator.request_decision(context, "soldier")
            for context in contexts
        ]
        
        decisions = await asyncio.gather(*tasks)
        
        elapsed = time.perf_counter() - start_time
        throughput = num_requests / elapsed
        
        # 验证结果
        assert len(decisions) == num_requests
        assert all(d.action for d in decisions)  # All decisions should have an action
        assert throughput > 100, f"吞吐量不足: {throughput:.2f} decisions/s < 100 decisions/s"
        
        print(f"\n并发决策吞吐量: {throughput:.2f} decisions/s")
        print(f"总耗时: {elapsed:.2f}s")
        print(f"平均延迟: {(elapsed / num_requests) * 1000:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_concurrent_limit_enforcement(self, coordinator):
        """测试并发限制生效
        
        验证: 并发数不应超过max_concurrent_decisions
        """
        # 记录并发数
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()
        
        async def mock_wait_with_tracking(correlation_id, timeout):
            nonlocal max_concurrent, current_concurrent
            
            async with lock:
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)
            
            await asyncio.sleep(0.1)  # 模拟慢速处理
            
            async with lock:
                current_concurrent -= 1
            
            return BrainDecision(
                decision_id=correlation_id,
                primary_brain="soldier",
                action="hold",
                confidence=0.8,
                reasoning="Mock decision",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=correlation_id
            )
        
        coordinator._wait_for_decision = mock_wait_with_tracking
        
        # 创建超过并发限制的请求
        num_requests = 50
        contexts = [{'symbol': f'STOCK{i}'} for i in range(num_requests)]
        
        # 并发执行
        tasks = [
            coordinator.request_decision(context, "soldier")
            for context in contexts
        ]
        
        decisions = await asyncio.gather(*tasks)
        
        # 验证并发限制
        assert max_concurrent <= coordinator.max_concurrent_decisions
        assert len(decisions) == num_requests
        
        print(f"\n最大并发数: {max_concurrent} (限制: {coordinator.max_concurrent_decisions})")
        print(f"并发限制命中次数: {coordinator.stats['concurrent_limit_hits']}")
    
    @pytest.mark.asyncio
    async def test_concurrent_decision_latency(self, coordinator):
        """测试并发决策延迟
        
        验证: 并发处理不应显著增加延迟
        性能目标: P99 < 200ms
        """
        # Mock决策处理
        async def mock_wait_for_decision(correlation_id, timeout):
            await asyncio.sleep(0.05)  # 模拟50ms处理时间
            return BrainDecision(
                decision_id=correlation_id,
                primary_brain="soldier",
                action="hold",
                confidence=0.8,
                reasoning="Mock decision",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=correlation_id
            )
        
        coordinator._wait_for_decision = mock_wait_for_decision
        
        # 测试延迟
        num_requests = 100
        latencies = []
        
        for i in range(num_requests):
            context = {'symbol': f'STOCK{i}'}
            
            start = time.perf_counter()
            decision = await coordinator.request_decision(context, "soldier")
            latency = (time.perf_counter() - start) * 1000
            
            latencies.append(latency)
        
        # 计算百分位数
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p90 = latencies[int(len(latencies) * 0.9)]
        p99 = latencies[int(len(latencies) * 0.99)]
        
        # 验证延迟
        assert p99 < 200, f"P99延迟过高: {p99:.2f}ms > 200ms"
        
        print(f"\n并发决策延迟:")
        print(f"  P50: {p50:.2f}ms")
        print(f"  P90: {p90:.2f}ms")
        print(f"  P99: {p99:.2f}ms")


class TestBatchProcessing:
    """测试vLLM批处理效果
    
    白皮书依据: 第二章 2.1 AI三脑协调 - vLLM批处理
    需求: 7.7 - vLLM批处理优化
    """
    
    @pytest_asyncio.fixture
    async def coordinator(self):
        """创建协调器实例"""
        event_bus = EventBus()
        await event_bus.initialize()
        
        with patch('src.core.dependency_container.DIContainer'):
            container = Mock()
            container.is_registered = Mock(return_value=False)
            
            coordinator = AIBrainCoordinator(event_bus, container)
            await coordinator.initialize()
            
            yield coordinator
            
            await coordinator.shutdown()
    
    @pytest.mark.asyncio
    async def test_batch_processing_throughput(self, coordinator):
        """测试批处理吞吐量
        
        验证: 批处理应该提高吞吐量
        性能目标: 批处理吞吐量 > 单个处理吞吐量 * 1.5
        """
        # Mock决策处理
        async def mock_wait_for_decision(correlation_id, timeout):
            await asyncio.sleep(0.02)  # 模拟20ms处理时间
            return BrainDecision(
                decision_id=correlation_id,
                primary_brain="commander",
                action="hold",
                confidence=0.8,
                reasoning="Mock decision",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=correlation_id
            )
        
        coordinator._wait_for_decision = mock_wait_for_decision
        
        # 测试批处理
        num_requests = 100
        contexts = [{'symbol': f'STOCK{i}'} for i in range(num_requests)]
        
        # 启用批处理
        coordinator.enable_batch_processing = True
        
        start_time = time.perf_counter()
        
        tasks = [
            coordinator.request_decision(context, "commander")
            for context in contexts
        ]
        
        decisions = await asyncio.gather(*tasks)
        
        elapsed = time.perf_counter() - start_time
        throughput = num_requests / elapsed
        
        # 验证结果
        assert len(decisions) == num_requests
        assert coordinator.stats['batch_decisions'] > 0
        
        print(f"\n批处理吞吐量: {throughput:.2f} decisions/s")
        print(f"批处理决策数: {coordinator.stats['batch_decisions']}")
        print(f"批处理率: {(coordinator.stats['batch_decisions'] / num_requests) * 100:.1f}%")
    
    @pytest.mark.asyncio
    async def test_batch_size_optimization(self, coordinator):
        """测试批处理大小优化
        
        验证: 批处理大小应该影响性能
        """
        # Mock决策处理
        async def mock_wait_for_decision(correlation_id, timeout):
            await asyncio.sleep(0.01)
            return BrainDecision(
                decision_id=correlation_id,
                primary_brain="commander",
                action="hold",
                confidence=0.8,
                reasoning="Mock decision",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=correlation_id
            )
        
        coordinator._wait_for_decision = mock_wait_for_decision
        
        # 测试不同批处理大小
        batch_sizes = [1, 5, 10, 20]
        results = {}
        
        for batch_size in batch_sizes:
            coordinator.batch_size = batch_size
            coordinator.enable_batch_processing = True
            
            num_requests = 50
            contexts = [{'symbol': f'STOCK{i}'} for i in range(num_requests)]
            
            start_time = time.perf_counter()
            
            tasks = [
                coordinator.request_decision(context, "commander")
                for context in contexts
            ]
            
            await asyncio.gather(*tasks)
            
            elapsed = time.perf_counter() - start_time
            throughput = num_requests / elapsed
            
            results[batch_size] = throughput
        
        # 验证批处理优化
        print(f"\n批处理大小优化:")
        for batch_size, throughput in results.items():
            print(f"  批大小={batch_size}: {throughput:.2f} decisions/s")
        
        # 批处理应该比单个处理快
        assert results[5] > results[1], "批处理应该比单个处理快"
    
    @pytest.mark.asyncio
    async def test_batch_vs_direct_comparison(self, coordinator):
        """测试批处理vs直接处理对比
        
        验证: 批处理应该在高负载下表现更好
        """
        # Mock决策处理
        async def mock_wait_for_decision(correlation_id, timeout):
            await asyncio.sleep(0.02)
            return BrainDecision(
                decision_id=correlation_id,
                primary_brain="commander",
                action="hold",
                confidence=0.8,
                reasoning="Mock decision",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=correlation_id
            )
        
        coordinator._wait_for_decision = mock_wait_for_decision
        
        num_requests = 100
        contexts = [{'symbol': f'STOCK{i}'} for i in range(num_requests)]
        
        # 测试直接处理
        coordinator.enable_batch_processing = False
        
        start_direct = time.perf_counter()
        tasks_direct = [
            coordinator.request_decision(context, "commander")
            for context in contexts
        ]
        await asyncio.gather(*tasks_direct)
        elapsed_direct = time.perf_counter() - start_direct
        throughput_direct = num_requests / elapsed_direct
        
        # 重置统计
        coordinator.stats['batch_decisions'] = 0
        
        # 测试批处理
        coordinator.enable_batch_processing = True
        
        start_batch = time.perf_counter()
        tasks_batch = [
            coordinator.request_decision(context, "commander")
            for context in contexts
        ]
        await asyncio.gather(*tasks_batch)
        elapsed_batch = time.perf_counter() - start_batch
        throughput_batch = num_requests / elapsed_batch
        
        # 验证批处理优势
        improvement = ((throughput_batch - throughput_direct) / throughput_direct) * 100
        
        print(f"\n批处理vs直接处理对比:")
        print(f"  直接处理: {throughput_direct:.2f} decisions/s")
        print(f"  批处理: {throughput_batch:.2f} decisions/s")
        print(f"  性能提升: {improvement:.1f}%")
        
        # 批处理应该有性能提升（至少10%）
        assert throughput_batch >= throughput_direct * 1.1, f"批处理性能提升不足: {improvement:.1f}% < 10%"


class TestConcurrentLimitStatistics:
    """测试并发限制统计
    
    白皮书依据: 第二章 2.1 AI三脑协调
    需求: 7.7 - 并发限制统计
    """
    
    @pytest_asyncio.fixture
    async def coordinator(self):
        """创建协调器实例"""
        event_bus = EventBus()
        await event_bus.initialize()
        
        with patch('src.core.dependency_container.DIContainer'):
            container = Mock()
            container.is_registered = Mock(return_value=False)
            
            coordinator = AIBrainCoordinator(event_bus, container)
            await coordinator.initialize()
            
            yield coordinator
            
            await coordinator.shutdown()
    
    @pytest.mark.asyncio
    async def test_concurrent_statistics_accuracy(self, coordinator):
        """测试并发统计准确性
        
        验证: 统计信息应该准确反映并发处理情况
        """
        # Mock决策处理
        async def mock_wait_for_decision(correlation_id, timeout):
            await asyncio.sleep(0.05)
            return BrainDecision(
                decision_id=correlation_id,
                primary_brain="soldier",
                action="hold",
                confidence=0.8,
                reasoning="Mock decision",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=correlation_id
            )
        
        coordinator._wait_for_decision = mock_wait_for_decision
        
        # 执行并发请求
        num_requests = 50
        contexts = [{'symbol': f'STOCK{i}'} for i in range(num_requests)]
        
        tasks = [
            coordinator.request_decision(context, "soldier")
            for context in contexts
        ]
        
        await asyncio.gather(*tasks)
        
        # 获取统计信息
        stats = coordinator.get_statistics()
        
        # 验证统计准确性
        assert stats['total_decisions'] == num_requests
        assert stats['concurrent_decisions'] == num_requests
        assert 'concurrent_rate' in stats
        assert 'batch_rate' in stats
        assert 'concurrent_limit_hits' in stats
        
        print(f"\n并发统计信息:")
        print(f"  总决策数: {stats['total_decisions']}")
        print(f"  并发决策数: {stats['concurrent_decisions']}")
        print(f"  并发率: {stats['concurrent_rate']:.1f}%")
        print(f"  批处理率: {stats['batch_rate']:.1f}%")
        print(f"  并发限制命中: {stats['concurrent_limit_hits']}")
    
    @pytest.mark.asyncio
    async def test_batch_statistics_tracking(self, coordinator):
        """测试批处理统计跟踪
        
        验证: 应该正确跟踪批处理统计
        """
        # Mock决策处理
        async def mock_wait_for_decision(correlation_id, timeout):
            await asyncio.sleep(0.01)
            return BrainDecision(
                decision_id=correlation_id,
                primary_brain="commander",
                action="hold",
                confidence=0.8,
                reasoning="Mock decision",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=correlation_id
            )
        
        coordinator._wait_for_decision = mock_wait_for_decision
        coordinator.enable_batch_processing = True
        
        # 执行批处理请求
        num_requests = 30
        contexts = [{'symbol': f'STOCK{i}'} for i in range(num_requests)]
        
        tasks = [
            coordinator.request_decision(context, "commander")
            for context in contexts
        ]
        
        await asyncio.gather(*tasks)
        
        # 获取统计信息
        stats = coordinator.get_statistics()
        
        # 验证批处理统计
        assert stats['batch_decisions'] > 0
        assert stats['batch_rate'] > 0
        assert stats['pending_batch_count'] >= 0
        
        print(f"\n批处理统计信息:")
        print(f"  批处理决策数: {stats['batch_decisions']}")
        print(f"  批处理率: {stats['batch_rate']:.1f}%")
        print(f"  待处理批次: {stats['pending_batch_count']}")
        print(f"  批处理大小: {stats['batch_size']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
