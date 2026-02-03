"""
Soldier降级和恢复机制测试 - Task 19.3, 19.4

白皮书依据: 第十二章 12.1.3 Soldier热备切换

测试内容:
- 降级触发机制
- 自动恢复机制
- 切换延迟监控
- 事件发布验证
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.brain.soldier_engine_v2 import (
    SoldierEngineV2,
    SoldierMode,
    SoldierConfig
)
from src.brain.llm_local_inference import InferenceResult, ModelStatus
from src.infra.event_bus import Event, EventType, EventPriority


@pytest.fixture
def soldier_config():
    """测试配置"""
    return SoldierConfig(
        local_inference_timeout=0.02,  # 20ms
        failure_threshold=3,
        recovery_check_interval=0.1  # 100ms for faster testing
    )


@pytest.fixture
def soldier_engine(soldier_config):
    """Soldier引擎fixture"""
    engine = SoldierEngineV2(config=soldier_config)
    
    # Mock事件总线
    engine.event_bus = AsyncMock()
    
    # Mock LLM推理引擎
    engine.llm_inference = AsyncMock()
    engine.llm_inference.status = ModelStatus.READY
    
    return engine


class TestDegradationTrigger:
    """降级触发机制测试"""
    
    @pytest.mark.asyncio
    async def test_trigger_degradation_from_normal_mode(self, soldier_engine):
        """测试从正常模式触发降级"""
        # 初始状态
        assert soldier_engine.mode == SoldierMode.NORMAL
        assert soldier_engine.failure_count == 0
        
        # 设置连续失败次数
        soldier_engine.consecutive_failures = 3
        
        # 触发降级
        await soldier_engine._trigger_degradation()
        
        # 验证模式切换
        assert soldier_engine.mode == SoldierMode.DEGRADED
        assert soldier_engine.failure_count == 1
        
        # 验证事件发布
        soldier_engine.event_bus.publish.assert_called_once()
        event = soldier_engine.event_bus.publish.call_args[0][0]
        assert event.event_type == EventType.SYSTEM_ALERT
        assert event.priority == EventPriority.CRITICAL
        assert event.data['alert_type'] == 'soldier_degradation'
        assert event.data['reason'] == 'local_model_health_check_failed'
        assert event.data['consecutive_failures'] == 3
    
    @pytest.mark.asyncio
    async def test_trigger_degradation_already_degraded(self, soldier_engine):
        """测试已经是降级模式时不重复触发"""
        # 设置为降级模式
        soldier_engine.mode = SoldierMode.DEGRADED
        soldier_engine.failure_count = 1
        
        # 尝试再次触发降级
        await soldier_engine._trigger_degradation()
        
        # 验证状态不变
        assert soldier_engine.mode == SoldierMode.DEGRADED
        assert soldier_engine.failure_count == 1
        
        # 验证没有发布事件
        soldier_engine.event_bus.publish.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_degradation_trigger_timing(self, soldier_engine):
        """测试降级触发延迟 - 性能目标: < 200ms"""
        soldier_engine.consecutive_failures = 3
        
        # 测量降级触发时间
        start_time = time.perf_counter()
        await soldier_engine._trigger_degradation()
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        # 验证延迟 < 200ms
        assert elapsed_ms < 200, f"降级触发延迟 {elapsed_ms:.2f}ms 超过200ms阈值"
        
        # 验证模式已切换
        assert soldier_engine.mode == SoldierMode.DEGRADED
    
    @pytest.mark.asyncio
    async def test_degradation_without_event_bus(self, soldier_engine):
        """测试没有事件总线时的降级"""
        soldier_engine.event_bus = None
        soldier_engine.consecutive_failures = 3
        
        # 触发降级（不应该抛出异常）
        await soldier_engine._trigger_degradation()
        
        # 验证模式切换成功
        assert soldier_engine.mode == SoldierMode.DEGRADED


class TestAutoRecovery:
    """自动恢复机制测试"""
    
    @pytest.mark.asyncio
    async def test_attempt_recovery_success(self, soldier_engine):
        """测试成功恢复到正常模式"""
        # 设置为降级模式
        soldier_engine.mode = SoldierMode.DEGRADED
        soldier_engine.consecutive_failures = 3
        
        # Mock健康检查通过
        soldier_engine.llm_inference.infer.return_value = InferenceResult(
            text="test",
            tokens=10,
            latency_ms=15.0,  # < 20ms
            cached=False,
            metadata={}
        )
        
        # 尝试恢复
        await soldier_engine._attempt_recovery()
        
        # 验证恢复成功
        assert soldier_engine.mode == SoldierMode.NORMAL
        assert soldier_engine.consecutive_failures == 0
        
        # 验证事件发布
        soldier_engine.event_bus.publish.assert_called_once()
        event = soldier_engine.event_bus.publish.call_args[0][0]
        assert event.event_type == EventType.SYSTEM_ALERT
        assert event.priority == EventPriority.HIGH
        assert event.data['alert_type'] == 'soldier_recovery'
        assert event.data['reason'] == 'local_model_health_restored'
    
    @pytest.mark.asyncio
    async def test_attempt_recovery_failure(self, soldier_engine):
        """测试恢复失败，保持降级模式"""
        # 设置为降级模式
        soldier_engine.mode = SoldierMode.DEGRADED
        
        # Mock健康检查失败
        soldier_engine.llm_inference.infer.return_value = None
        
        # 尝试恢复
        await soldier_engine._attempt_recovery()
        
        # 验证仍然是降级模式
        assert soldier_engine.mode == SoldierMode.DEGRADED
        
        # 验证没有发布恢复事件
        soldier_engine.event_bus.publish.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_attempt_recovery_already_normal(self, soldier_engine):
        """测试已经是正常模式时不尝试恢复"""
        # 初始状态为正常模式
        assert soldier_engine.mode == SoldierMode.NORMAL
        
        # 尝试恢复
        await soldier_engine._attempt_recovery()
        
        # 验证状态不变
        assert soldier_engine.mode == SoldierMode.NORMAL
        
        # 验证没有调用健康检查
        soldier_engine.llm_inference.infer.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_recovery_timing(self, soldier_engine):
        """测试恢复延迟 - 性能目标: < 200ms"""
        soldier_engine.mode = SoldierMode.DEGRADED
        
        # Mock健康检查通过
        soldier_engine.llm_inference.infer.return_value = InferenceResult(
            text="test",
            tokens=10,
            latency_ms=15.0,
            cached=False,
            metadata={}
        )
        
        # 测量恢复时间
        start_time = time.perf_counter()
        await soldier_engine._attempt_recovery()
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        # 验证延迟 < 200ms
        assert elapsed_ms < 200, f"恢复延迟 {elapsed_ms:.2f}ms 超过200ms阈值"
        
        # 验证恢复成功
        assert soldier_engine.mode == SoldierMode.NORMAL


class TestHealthCheckIntegration:
    """健康检查与降级/恢复集成测试"""
    
    @pytest.mark.asyncio
    async def test_health_check_triggers_degradation(self, soldier_engine):
        """测试健康检查失败触发降级"""
        # Mock健康检查失败
        soldier_engine.llm_inference.infer.return_value = None
        
        # 启动健康检查
        await soldier_engine._start_health_check()
        
        # 等待健康检查执行
        await asyncio.sleep(0.15)  # 等待一次检查
        
        # 验证失败计数增加
        assert soldier_engine.consecutive_failures > 0
        assert soldier_engine.stats['health_check_failures'] > 0
        
        # 清理
        await soldier_engine.stop_health_check()
    
    @pytest.mark.asyncio
    async def test_health_check_triggers_recovery(self, soldier_engine):
        """测试健康检查成功触发恢复"""
        # 设置为降级模式
        soldier_engine.mode = SoldierMode.DEGRADED
        
        # Mock健康检查通过
        soldier_engine.llm_inference.infer.return_value = InferenceResult(
            text="test",
            tokens=10,
            latency_ms=15.0,
            cached=False,
            metadata={}
        )
        
        # 启动健康检查
        await soldier_engine._start_health_check()
        
        # 等待健康检查执行和恢复
        await asyncio.sleep(0.15)
        
        # 验证恢复到正常模式
        assert soldier_engine.mode == SoldierMode.NORMAL
        assert soldier_engine.consecutive_failures == 0
        
        # 清理
        await soldier_engine.stop_health_check()
    
    @pytest.mark.asyncio
    async def test_consecutive_failures_trigger_degradation(self, soldier_engine):
        """测试连续失败达到阈值触发降级"""
        # Mock健康检查失败
        soldier_engine.llm_inference.infer.return_value = None
        
        # 启动健康检查
        await soldier_engine._start_health_check()
        
        # 等待多次健康检查（3次失败触发降级）
        await asyncio.sleep(0.35)  # 等待3次检查
        
        # 验证触发降级
        assert soldier_engine.consecutive_failures >= soldier_engine.config.failure_threshold
        assert soldier_engine.mode == SoldierMode.DEGRADED
        
        # 清理
        await soldier_engine.stop_health_check()


class TestEventPublishing:
    """事件发布验证测试"""
    
    @pytest.mark.asyncio
    async def test_degradation_event_content(self, soldier_engine):
        """测试降级事件内容"""
        soldier_engine.consecutive_failures = 5
        
        await soldier_engine._trigger_degradation()
        
        # 获取发布的事件
        event = soldier_engine.event_bus.publish.call_args[0][0]
        
        # 验证事件内容
        assert event.source_module == "soldier"
        assert event.target_module == "system"
        assert 'consecutive_failures' in event.data
        assert event.data['consecutive_failures'] == 5
        assert 'timestamp' in event.data
    
    @pytest.mark.asyncio
    async def test_recovery_event_content(self, soldier_engine):
        """测试恢复事件内容"""
        soldier_engine.mode = SoldierMode.DEGRADED
        
        # Mock健康检查通过
        soldier_engine.llm_inference.infer.return_value = InferenceResult(
            text="test",
            tokens=10,
            latency_ms=15.0,
            cached=False,
            metadata={}
        )
        
        await soldier_engine._attempt_recovery()
        
        # 获取发布的事件
        event = soldier_engine.event_bus.publish.call_args[0][0]
        
        # 验证事件内容
        assert event.source_module == "soldier"
        assert event.target_module == "system"
        assert event.data['alert_type'] == 'soldier_recovery'
        assert 'timestamp' in event.data


class TestPerformanceRequirements:
    """性能要求验证测试"""
    
    @pytest.mark.asyncio
    async def test_degradation_latency_requirement(self, soldier_engine):
        """测试降级延迟要求 < 200ms"""
        soldier_engine.consecutive_failures = 3
        
        # 执行多次测试
        latencies = []
        for _ in range(10):
            soldier_engine.mode = SoldierMode.NORMAL
            
            start_time = time.perf_counter()
            await soldier_engine._trigger_degradation()
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            latencies.append(elapsed_ms)
        
        # 验证所有延迟都 < 200ms
        max_latency = max(latencies)
        avg_latency = sum(latencies) / len(latencies)
        
        assert max_latency < 200, f"最大降级延迟 {max_latency:.2f}ms 超过200ms"
        assert avg_latency < 100, f"平均降级延迟 {avg_latency:.2f}ms 过高"
    
    @pytest.mark.asyncio
    async def test_recovery_latency_requirement(self, soldier_engine):
        """测试恢复延迟要求 < 200ms"""
        # Mock健康检查通过
        soldier_engine.llm_inference.infer.return_value = InferenceResult(
            text="test",
            tokens=10,
            latency_ms=15.0,
            cached=False,
            metadata={}
        )
        
        # 执行多次测试
        latencies = []
        for _ in range(10):
            soldier_engine.mode = SoldierMode.DEGRADED
            
            start_time = time.perf_counter()
            await soldier_engine._attempt_recovery()
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            latencies.append(elapsed_ms)
        
        # 验证所有延迟都 < 200ms
        max_latency = max(latencies)
        avg_latency = sum(latencies) / len(latencies)
        
        assert max_latency < 200, f"最大恢复延迟 {max_latency:.2f}ms 超过200ms"
        assert avg_latency < 100, f"平均恢复延迟 {avg_latency:.2f}ms 过高"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
