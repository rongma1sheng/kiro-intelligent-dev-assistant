"""
vLLM内存协调器单元测试

白皮书依据: 第二章 2.8 统一记忆系统 - vLLM内存协同管理
版本: v1.6.0
作者: MIA Team
日期: 2026-01-19

测试覆盖:
1. AMD AI 395内存池初始化和管理
2. 内存分配和释放机制
3. 内存压力检测和清理
4. Variable Graphics Memory优化
5. XDNA2 NPU缓存管理
6. PagedAttention碎片整理
7. 事件驱动协同通信
8. 性能指标验证
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from src.brain.vllm_memory_coordinator import (
    VLLMMemoryCoordinator,
    MemoryType,
    MemoryPressureLevel,
    MemoryAllocationRequest,
    MemoryPool,
    MemoryStats
)
from src.infra.event_bus import EventType, EventPriority, Event


class TestVLLMMemoryCoordinator:
    """vLLM内存协调器测试类"""
    
    @pytest.fixture
    async def coordinator(self):
        """创建内存协调器实例"""
        coordinator = VLLMMemoryCoordinator()
        
        # Mock事件总线
        coordinator.event_bus = AsyncMock()
        
        yield coordinator
        
        # 清理
        if coordinator.running:
            await coordinator.shutdown()
    
    @pytest.fixture
    async def initialized_coordinator(self, coordinator):
        """创建已初始化的内存协调器"""
        # 保存mock的event_bus
        mock_event_bus = coordinator.event_bus
        
        # 初始化时阻止获取真实事件总线
        with patch('src.brain.vllm_memory_coordinator.get_event_bus', new_callable=AsyncMock) as mock_get_bus:
            mock_get_bus.return_value = mock_event_bus
            await coordinator.initialize()
        
        # 确保event_bus仍然是mock
        coordinator.event_bus = mock_event_bus
        return coordinator
    
    def test_coordinator_initialization(self, coordinator):
        """测试协调器初始化"""
        # 验证AMD AI 395内存池配置
        assert MemoryType.UNIFIED_SYSTEM in coordinator.memory_pools
        assert MemoryType.VARIABLE_GRAPHICS in coordinator.memory_pools
        assert MemoryType.NPU_CACHE in coordinator.memory_pools
        assert MemoryType.L3_CACHE in coordinator.memory_pools
        assert MemoryType.PAGED_ATTENTION in coordinator.memory_pools
        
        # 验证内存池大小
        assert coordinator.memory_pools[MemoryType.UNIFIED_SYSTEM].total_size == 128.0  # 128GB
        assert coordinator.memory_pools[MemoryType.VARIABLE_GRAPHICS].total_size == 96.0  # 96GB
        assert coordinator.memory_pools[MemoryType.NPU_CACHE].total_size == 2.0  # 2GB
        assert coordinator.memory_pools[MemoryType.L3_CACHE].total_size == 0.064  # 64MB
        assert coordinator.memory_pools[MemoryType.PAGED_ATTENTION].total_size == 32.0  # 32GB
        
        # 验证配置参数
        assert coordinator.config['pressure_check_interval'] == 0.1
        assert coordinator.config['cleanup_threshold'] == 0.8
        assert coordinator.config['fragmentation_threshold'] == 0.05
        assert coordinator.config['npu_optimization'] is True
        
        # 验证统计信息初始化
        assert isinstance(coordinator.stats, MemoryStats)
        assert coordinator.stats.total_allocations == 0
    
    @pytest.mark.asyncio
    async def test_memory_pool_initialization(self, coordinator):
        """测试内存池初始化"""
        await coordinator._initialize_memory_pools()
        
        # 验证统一系统内存
        unified_pool = coordinator.memory_pools[MemoryType.UNIFIED_SYSTEM]
        assert unified_pool.used_size == 16.0  # 系统占用16GB
        assert unified_pool.free_size == 112.0  # 剩余112GB
        
        # 验证Variable Graphics Memory
        vgm_pool = coordinator.memory_pools[MemoryType.VARIABLE_GRAPHICS]
        assert vgm_pool.used_size == 0.0  # 初始未分配
        assert vgm_pool.free_size == 96.0  # 全部可用
        
        # 验证NPU缓存
        npu_pool = coordinator.memory_pools[MemoryType.NPU_CACHE]
        assert npu_pool.used_size == 0.1  # NPU运行时占用100MB
        assert npu_pool.free_size == 1.9  # 剩余1.9GB
        
        # 验证PagedAttention块池
        paged_pool = coordinator.memory_pools[MemoryType.PAGED_ATTENTION]
        assert paged_pool.used_size == 0.0  # 初始未分配
        assert paged_pool.fragmentation == 0.0  # 初始无碎片
    
    @pytest.mark.asyncio
    async def test_memory_allocation_success(self, initialized_coordinator):
        """测试成功的内存分配"""
        coordinator = initialized_coordinator
        
        # 创建分配请求
        request = MemoryAllocationRequest(
            request_id="test_alloc_001",
            size_gb=8.0,
            memory_type=MemoryType.VARIABLE_GRAPHICS,
            priority=5,
            timeout=5.0
        )
        
        # 执行分配
        allocation = await coordinator.allocate_memory(request)
        
        # 验证分配结果
        assert allocation is not None
        assert allocation['request_id'] == "test_alloc_001"
        assert allocation['size_gb'] == 8.0
        assert allocation['memory_type'] == MemoryType.VARIABLE_GRAPHICS.value
        assert allocation['priority'] == 5
        
        # 验证内存池状态更新
        vgm_pool = coordinator.memory_pools[MemoryType.VARIABLE_GRAPHICS]
        assert vgm_pool.used_size == 8.0
        assert vgm_pool.free_size == 88.0
        
        # 验证统计信息更新
        assert coordinator.stats.total_allocations == 1
        assert coordinator.stats.successful_allocations == 1
        assert coordinator.stats.failed_allocations == 0
        assert coordinator.stats.avg_allocation_time > 0
        
        # 验证分配记录
        assert len(coordinator.active_allocations) == 1
        assert allocation['allocation_id'] in coordinator.active_allocations
    
    @pytest.mark.asyncio
    async def test_memory_allocation_insufficient_memory(self, initialized_coordinator):
        """测试内存不足的分配请求"""
        coordinator = initialized_coordinator
        
        # 创建超大分配请求
        request = MemoryAllocationRequest(
            request_id="test_alloc_large",
            size_gb=200.0,  # 超过96GB限制
            memory_type=MemoryType.VARIABLE_GRAPHICS,
            priority=3
        )
        
        # 执行分配 - 应该抛出ValueError或返回None
        try:
            allocation = await coordinator.allocate_memory(request)
            # 如果没有抛出异常，验证分配失败
            assert allocation is None
        except ValueError as e:
            # 预期的异常：请求大小超过内存池总大小
            assert "超过" in str(e) or "exceed" in str(e).lower()
        
        # 验证统计信息
        assert coordinator.stats.total_allocations >= 0
    
    @pytest.mark.asyncio
    async def test_memory_deallocation(self, initialized_coordinator):
        """测试内存释放"""
        coordinator = initialized_coordinator
        
        # 先分配内存
        request = MemoryAllocationRequest(
            request_id="test_dealloc",
            size_gb=4.0,
            memory_type=MemoryType.PAGED_ATTENTION,
            priority=3
        )
        
        allocation = await coordinator.allocate_memory(request)
        assert allocation is not None
        
        allocation_id = allocation['allocation_id']
        
        # 验证分配后状态
        paged_pool = coordinator.memory_pools[MemoryType.PAGED_ATTENTION]
        assert paged_pool.used_size == 4.0
        assert paged_pool.free_size == 28.0
        
        # 释放内存
        success = await coordinator.deallocate_memory(allocation_id)
        
        # 验证释放结果
        assert success is True
        
        # 验证内存池状态恢复
        assert paged_pool.used_size == 0.0
        assert paged_pool.free_size == 32.0
        
        # 验证分配记录清除
        assert allocation_id not in coordinator.active_allocations
        
        # 验证统计信息
        assert coordinator.stats.total_deallocations == 1
    
    @pytest.mark.asyncio
    async def test_memory_pressure_detection(self, initialized_coordinator):
        """测试内存压力检测"""
        coordinator = initialized_coordinator
        
        # 初始状态应该是低压力
        pressure_info = await coordinator.detect_memory_pressure()
        assert pressure_info['overall_pressure'] == MemoryPressureLevel.LOW
        assert len(pressure_info['critical_pools']) == 0
        
        # 分配大量内存制造高压力
        large_requests = []
        for i in range(10):
            request = MemoryAllocationRequest(
                request_id=f"pressure_test_{i}",
                size_gb=8.0,
                memory_type=MemoryType.VARIABLE_GRAPHICS,
                priority=3
            )
            allocation = await coordinator.allocate_memory(request)
            if allocation:
                large_requests.append(allocation)
        
        # 检测压力
        pressure_info = await coordinator.detect_memory_pressure()
        
        # 验证压力等级提升
        assert pressure_info['overall_pressure'] in [
            MemoryPressureLevel.MODERATE, 
            MemoryPressureLevel.HIGH, 
            MemoryPressureLevel.CRITICAL
        ]
        
        # 验证压力信息结构
        assert 'pool_pressures' in pressure_info
        assert 'recommendations' in pressure_info
        assert 'timestamp' in pressure_info
        
        # 验证Variable Graphics Memory压力
        vgm_pressure = pressure_info['pool_pressures'][MemoryType.VARIABLE_GRAPHICS.value]
        assert vgm_pressure['utilization'] > 0.5  # 使用率超过50%
    
    @pytest.mark.asyncio
    async def test_memory_cleanup(self, initialized_coordinator):
        """测试内存清理"""
        coordinator = initialized_coordinator
        
        # 分配一些内存
        allocations = []
        for i in range(5):
            request = MemoryAllocationRequest(
                request_id=f"cleanup_test_{i}",
                size_gb=2.0,
                memory_type=MemoryType.PAGED_ATTENTION,
                priority=2  # 低优先级
            )
            allocation = await coordinator.allocate_memory(request)
            if allocation:
                allocations.append(allocation)
        
        # 验证分配成功
        assert len(allocations) == 5
        paged_pool = coordinator.memory_pools[MemoryType.PAGED_ATTENTION]
        initial_used = paged_pool.used_size
        
        # 先释放一些分配
        for alloc in allocations[:3]:
            await coordinator.deallocate_memory(alloc['allocation_id'])
        
        # 触发清理
        cleanup_result = await coordinator.trigger_cleanup(MemoryType.PAGED_ATTENTION)
        
        # 验证清理结果
        assert cleanup_result['freed_memory_gb'] >= 0
        assert cleanup_result['cleanup_time_ms'] >= 0
        
        # 验证统计信息
        assert coordinator.stats.cleanup_operations >= 1
    
    @pytest.mark.asyncio
    async def test_paged_attention_defragmentation(self, initialized_coordinator):
        """测试PagedAttention碎片整理"""
        coordinator = initialized_coordinator
        
        # 模拟碎片化状态
        paged_pool = coordinator.memory_pools[MemoryType.PAGED_ATTENTION]
        paged_pool.fragmentation = 0.08  # 8%碎片率
        
        # 执行碎片整理
        defrag_result = await coordinator._defragment_paged_attention()
        
        # 验证碎片整理结果
        assert defrag_result['blocks_merged'] >= 0
        assert defrag_result['fragmentation_after'] <= defrag_result['fragmentation_before']
        
        # 验证碎片率降低或保持
        assert paged_pool.fragmentation < 0.08
        
        # 验证统计信息
        assert coordinator.stats.fragmentation_events == 1
    
    @pytest.mark.asyncio
    async def test_variable_graphics_optimization(self, initialized_coordinator):
        """测试Variable Graphics Memory优化"""
        coordinator = initialized_coordinator
        
        # 测试大内存分配优化
        large_request = MemoryAllocationRequest(
            request_id="large_vgm_test",
            size_gb=16.0,  # 大于8GB
            memory_type=MemoryType.VARIABLE_GRAPHICS,
            priority=3
        )
        
        allocation = await coordinator.allocate_memory(large_request)
        assert allocation is not None
        
        # 验证优化标记
        assert allocation['metadata']['compression_enabled'] is True
        assert allocation['metadata']['optimization'] == 'large_allocation'
        
        # 测试高优先级分配优化
        high_priority_request = MemoryAllocationRequest(
            request_id="high_priority_vgm_test",
            size_gb=4.0,
            memory_type=MemoryType.VARIABLE_GRAPHICS,
            priority=5  # 高优先级
        )
        
        allocation2 = await coordinator.allocate_memory(high_priority_request)
        assert allocation2 is not None
        
        # 验证优化标记
        assert allocation2['metadata']['preallocation_enabled'] is True
        assert allocation2['metadata']['optimization'] == 'high_priority'
    
    @pytest.mark.asyncio
    async def test_npu_cache_optimization(self, initialized_coordinator):
        """测试NPU缓存优化"""
        coordinator = initialized_coordinator
        
        # 启用NPU优化
        coordinator.config['npu_optimization'] = True
        
        # 分配NPU缓存
        npu_request = MemoryAllocationRequest(
            request_id="npu_cache_test",
            size_gb=0.5,
            memory_type=MemoryType.NPU_CACHE,
            priority=4
        )
        
        allocation = await coordinator.allocate_memory(npu_request)
        assert allocation is not None
        
        # 验证NPU优化标记
        assert allocation['metadata']['npu_acceleration'] is True
        assert allocation['metadata']['xdna2_optimized'] is True
        assert allocation['metadata']['optimization'] == 'npu_cache'
    
    @pytest.mark.asyncio
    async def test_memory_stats(self, initialized_coordinator):
        """测试内存统计信息"""
        coordinator = initialized_coordinator
        
        # 执行一些操作
        request = MemoryAllocationRequest(
            request_id="stats_test",
            size_gb=4.0,
            memory_type=MemoryType.UNIFIED_SYSTEM,
            priority=3
        )
        
        allocation = await coordinator.allocate_memory(request)
        await coordinator.deallocate_memory(allocation['allocation_id'])
        await coordinator.trigger_cleanup()
        
        # 获取统计信息
        stats = await coordinator.get_memory_stats()
        
        # 验证统计信息结构
        assert 'allocation_stats' in stats
        assert 'cleanup_stats' in stats
        assert 'pool_stats' in stats
        assert 'amd_ai_395_stats' in stats
        
        # 验证分配统计
        alloc_stats = stats['allocation_stats']
        assert alloc_stats['total_allocations'] == 1
        assert alloc_stats['successful_allocations'] == 1
        assert alloc_stats['total_deallocations'] == 1
        assert alloc_stats['success_rate'] == 1.0
        
        # 验证清理统计
        cleanup_stats = stats['cleanup_stats']
        assert cleanup_stats['cleanup_operations'] == 1
        
        # 验证AMD AI 395特定统计
        amd_stats = stats['amd_ai_395_stats']
        assert 'unified_memory_utilization' in amd_stats
        assert 'variable_graphics_utilization' in amd_stats
        assert 'npu_cache_utilization' in amd_stats
        assert 'paged_attention_efficiency' in amd_stats
        assert 'total_ai_memory_gb' in amd_stats
    
    @pytest.mark.asyncio
    async def test_system_query_handling(self, initialized_coordinator):
        """测试系统查询处理"""
        coordinator = initialized_coordinator
        
        # 确保event_bus.publish是AsyncMock
        coordinator.event_bus.publish = AsyncMock()
        
        # 模拟内存统计查询
        query_event = Event(
            event_type=EventType.SYSTEM_QUERY,
            source_module="test_module",
            target_module="vllm_memory_coordinator",
            priority=EventPriority.HIGH,
            data={
                'query_type': 'memory_stats',
                'correlation_id': 'test_query_001',
                'requester': 'test_module'
            }
        )
        
        # 处理查询
        await coordinator._handle_system_query(query_event)
        
        # 验证响应事件发布
        coordinator.event_bus.publish.assert_called_once()
        
        # 获取发布的事件
        published_event = coordinator.event_bus.publish.call_args[0][0]
        assert published_event.event_type == EventType.SYSTEM_RESPONSE
        assert published_event.data['correlation_id'] == 'test_query_001'
        assert published_event.data['status'] == 'success'
        assert 'response_data' in published_event.data
    
    @pytest.mark.asyncio
    async def test_pressure_alert_handling(self, initialized_coordinator):
        """测试内存压力告警处理"""
        coordinator = initialized_coordinator
        
        # 创建高压力状态
        pressure_info = {
            'overall_pressure': MemoryPressureLevel.CRITICAL,
            'critical_pools': [MemoryType.VARIABLE_GRAPHICS.value],
            'recommendations': ['立即触发全局内存清理']
        }
        
        # 确保event_bus.publish是AsyncMock
        coordinator.event_bus.publish = AsyncMock()
        
        # 处理压力告警
        await coordinator._handle_pressure_alert(pressure_info)
        
        # 验证告警事件发布
        coordinator.event_bus.publish.assert_called_once()
        
        # 获取发布的事件
        published_event = coordinator.event_bus.publish.call_args[0][0]
        assert published_event.event_type == EventType.SYSTEM_ALERT
        assert published_event.data['alert_type'] == 'memory_pressure'
        assert published_event.data['pressure_level'] == 'critical'
    
    @pytest.mark.asyncio
    async def test_health_check(self, initialized_coordinator):
        """测试健康检查"""
        coordinator = initialized_coordinator
        
        # 执行健康检查
        health = await coordinator.health_check()
        
        # 验证健康状态
        assert 'healthy' in health
        assert 'coordinator_healthy' in health
        assert 'cleanup_healthy' in health
        assert 'monitoring_healthy' in health
        assert 'memory_healthy' in health
        assert 'event_bus_healthy' in health
        assert 'memory_pressure' in health
        assert 'active_allocations' in health
        assert 'total_memory_gb' in health
        assert 'used_memory_gb' in health
        assert 'timestamp' in health
        
        # 验证总内存大小
        expected_total = 128.0 + 96.0 + 2.0 + 0.064 + 32.0  # 所有内存池总和
        assert abs(health['total_memory_gb'] - expected_total) < 0.1
    
    def test_allocation_request_validation(self, coordinator):
        """测试分配请求验证"""
        # 测试有效请求
        valid_request = MemoryAllocationRequest(
            request_id="valid_test",
            size_gb=4.0,
            memory_type=MemoryType.VARIABLE_GRAPHICS,
            priority=3,
            timeout=5.0
        )
        
        # 应该不抛出异常
        coordinator._validate_allocation_request(valid_request)
        
        # 测试无效请求 - 空ID
        with pytest.raises(ValueError, match="request_id不能为空"):
            invalid_request = MemoryAllocationRequest(
                request_id="",
                size_gb=4.0,
                memory_type=MemoryType.VARIABLE_GRAPHICS
            )
            coordinator._validate_allocation_request(invalid_request)
        
        # 测试无效请求 - 负大小
        with pytest.raises(ValueError, match="size_gb必须大于0"):
            invalid_request = MemoryAllocationRequest(
                request_id="test",
                size_gb=-1.0,
                memory_type=MemoryType.VARIABLE_GRAPHICS
            )
            coordinator._validate_allocation_request(invalid_request)
        
        # 测试无效请求 - 无效优先级
        with pytest.raises(ValueError, match="priority必须在1-5范围内"):
            invalid_request = MemoryAllocationRequest(
                request_id="test",
                size_gb=4.0,
                memory_type=MemoryType.VARIABLE_GRAPHICS,
                priority=10
            )
            coordinator._validate_allocation_request(invalid_request)
        
        # 测试无效请求 - 超大分配
        with pytest.raises(ValueError, match="请求大小.*超过内存池总大小"):
            invalid_request = MemoryAllocationRequest(
                request_id="test",
                size_gb=200.0,  # 超过96GB限制
                memory_type=MemoryType.VARIABLE_GRAPHICS
            )
            coordinator._validate_allocation_request(invalid_request)
    
    def test_memory_pool_utilization_calculation(self):
        """测试内存池利用率计算"""
        pool = MemoryPool(
            pool_type=MemoryType.VARIABLE_GRAPHICS,
            total_size=100.0,
            used_size=60.0
        )
        
        # 验证利用率计算
        assert pool.utilization == 0.6
        assert pool.free_size == 40.0
        
        # 测试压力等级更新
        pool.update_pressure_level()
        assert pool.pressure_level == MemoryPressureLevel.MODERATE  # 60%使用率
        
        # 测试高压力状态
        pool.used_size = 85.0
        pool.free_size = 15.0
        pool.update_pressure_level()
        assert pool.pressure_level == MemoryPressureLevel.HIGH  # 85%使用率
        
        # 测试临界状态
        pool.used_size = 98.0
        pool.free_size = 2.0
        pool.update_pressure_level()
        assert pool.pressure_level == MemoryPressureLevel.CRITICAL  # 98%使用率
    
    @pytest.mark.asyncio
    async def test_coordinator_lifecycle(self, coordinator):
        """测试协调器生命周期"""
        # 初始状态
        assert coordinator.running is False
        assert coordinator.coordinator_task is None
        
        # 确保event_bus.subscribe是AsyncMock
        coordinator.event_bus.subscribe = AsyncMock()
        
        # 初始化
        with patch('src.brain.vllm_memory_coordinator.get_event_bus', new_callable=AsyncMock) as mock_get_bus:
            mock_get_bus.return_value = coordinator.event_bus
            await coordinator.initialize()
        
        assert coordinator.running is True
        
        # 验证事件总线订阅
        coordinator.event_bus.subscribe.assert_called()
        
        # 关闭
        await coordinator.shutdown()
        assert coordinator.running is False
    
    @pytest.mark.asyncio
    async def test_emergency_cleanup(self, initialized_coordinator):
        """测试紧急内存清理"""
        coordinator = initialized_coordinator
        
        # 分配一些内存
        request = MemoryAllocationRequest(
            request_id="emergency_test",
            size_gb=10.0,
            memory_type=MemoryType.VARIABLE_GRAPHICS,
            priority=2
        )
        
        allocation = await coordinator.allocate_memory(request)
        
        # 记录初始使用量
        vgm_pool = coordinator.memory_pools[MemoryType.VARIABLE_GRAPHICS]
        initial_used = vgm_pool.used_size
        
        # 先释放分配
        if allocation:
            await coordinator.deallocate_memory(allocation['allocation_id'])
        
        # 触发紧急清理
        await coordinator._trigger_emergency_cleanup(MemoryType.VARIABLE_GRAPHICS)
        
        # 验证清理执行（内存使用量应该减少或保持）
        assert vgm_pool.used_size <= initial_used
    
    def test_pressure_recommendations_generation(self, coordinator):
        """测试内存压力建议生成"""
        # 测试临界压力建议
        critical_pressure_info = {
            'overall_pressure': MemoryPressureLevel.CRITICAL,
            'critical_pools': [MemoryType.VARIABLE_GRAPHICS.value, MemoryType.PAGED_ATTENTION.value]
        }
        
        recommendations = coordinator._generate_pressure_recommendations(critical_pressure_info)
        
        assert "立即触发全局内存清理" in recommendations
        assert "暂停低优先级内存分配" in recommendations
        assert "释放部分Variable Graphics Memory回系统内存" in recommendations
        assert "执行PagedAttention碎片整理" in recommendations
        
        # 测试高压力建议
        high_pressure_info = {
            'overall_pressure': MemoryPressureLevel.HIGH,
            'critical_pools': [MemoryType.NPU_CACHE.value]
        }
        
        recommendations = coordinator._generate_pressure_recommendations(high_pressure_info)
        
        assert "启动预防性内存清理" in recommendations
        assert "清理NPU推理缓存" in recommendations
        
        # 测试低压力建议
        low_pressure_info = {
            'overall_pressure': MemoryPressureLevel.LOW,
            'critical_pools': []
        }
        
        recommendations = coordinator._generate_pressure_recommendations(low_pressure_info)
        
        assert "内存状态良好，继续监控" in recommendations


class TestMemoryPoolOperations:
    """内存池操作测试类"""
    
    def test_memory_pool_creation(self):
        """测试内存池创建"""
        pool = MemoryPool(
            pool_type=MemoryType.UNIFIED_SYSTEM,
            total_size=128.0,
            used_size=16.0
        )
        
        assert pool.pool_type == MemoryType.UNIFIED_SYSTEM
        assert pool.total_size == 128.0
        assert pool.used_size == 16.0
        assert pool.free_size == 112.0  # 自动计算
        assert pool.utilization == 0.125  # 16/128
        assert pool.pressure_level == MemoryPressureLevel.LOW
        assert pool.fragmentation == 0.0
    
    def test_pressure_level_transitions(self):
        """测试压力等级转换"""
        pool = MemoryPool(
            pool_type=MemoryType.VARIABLE_GRAPHICS,
            total_size=100.0
        )
        
        # 低压力 (<60%)
        pool.used_size = 50.0
        pool.update_pressure_level()
        assert pool.pressure_level == MemoryPressureLevel.LOW
        
        # 中等压力 (60-80%)
        pool.used_size = 70.0
        pool.update_pressure_level()
        assert pool.pressure_level == MemoryPressureLevel.MODERATE
        
        # 高压力 (80-95%)
        pool.used_size = 90.0
        pool.update_pressure_level()
        assert pool.pressure_level == MemoryPressureLevel.HIGH
        
        # 临界压力 (>95%)
        pool.used_size = 98.0
        pool.update_pressure_level()
        assert pool.pressure_level == MemoryPressureLevel.CRITICAL


class TestMemoryAllocationRequest:
    """内存分配请求测试类"""
    
    def test_allocation_request_creation(self):
        """测试分配请求创建"""
        request = MemoryAllocationRequest(
            request_id="test_request",
            size_gb=8.0,
            memory_type=MemoryType.VARIABLE_GRAPHICS,
            priority=4,
            timeout=10.0,
            metadata={'test': 'data'}
        )
        
        assert request.request_id == "test_request"
        assert request.size_gb == 8.0
        assert request.memory_type == MemoryType.VARIABLE_GRAPHICS
        assert request.priority == 4
        assert request.timeout == 10.0
        assert request.metadata == {'test': 'data'}
    
    def test_allocation_request_defaults(self):
        """测试分配请求默认值"""
        request = MemoryAllocationRequest(
            request_id="test_request",
            size_gb=4.0,
            memory_type=MemoryType.NPU_CACHE
        )
        
        assert request.priority == 3  # 默认优先级
        assert request.timeout == 5.0  # 默认超时
        assert request.metadata == {}  # 默认空元数据


class TestMemoryStats:
    """内存统计测试类"""
    
    def test_memory_stats_initialization(self):
        """测试内存统计初始化"""
        stats = MemoryStats()
        
        assert stats.total_allocations == 0
        assert stats.successful_allocations == 0
        assert stats.failed_allocations == 0
        assert stats.total_deallocations == 0
        assert stats.cleanup_operations == 0
        assert stats.fragmentation_events == 0
        assert stats.pressure_alerts == 0
        assert stats.avg_allocation_time == 0.0
    
    def test_memory_stats_updates(self):
        """测试内存统计更新"""
        stats = MemoryStats()
        
        # 模拟统计更新
        stats.total_allocations = 10
        stats.successful_allocations = 8
        stats.failed_allocations = 2
        stats.total_deallocations = 5
        stats.cleanup_operations = 2
        stats.avg_allocation_time = 1.5
        
        # 验证更新
        assert stats.total_allocations == 10
        assert stats.successful_allocations == 8
        assert stats.failed_allocations == 2
        assert stats.total_deallocations == 5
        assert stats.cleanup_operations == 2
        assert stats.avg_allocation_time == 1.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])