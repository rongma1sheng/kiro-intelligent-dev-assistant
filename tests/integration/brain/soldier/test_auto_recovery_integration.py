"""
Soldier自动恢复机制集成测试 - Task 19.8

白皮书依据: 第二章 2.1.2 运行模式, 第十二章 12.1.3 Soldier热备切换

测试内容:
- 恢复检测
- 自动回切（Cloud → Local）
- 恢复通知
- 恢复延迟
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.brain.soldier_engine_v2 import (
    SoldierEngineV2,
    SoldierConfig,
    SoldierMode,
    SoldierDecision
)
from src.infra.event_bus import EventBus, Event, EventType


@pytest_asyncio.fixture
async def event_bus():
    """事件总线fixture"""
    bus = EventBus()
    await bus.initialize()  # 启动后台事件处理任务
    yield bus
    await bus.shutdown()  # 清理


@pytest.fixture
def soldier_config():
    """Soldier配置fixture"""
    return SoldierConfig(
        local_inference_timeout=0.02,
        cloud_timeout=2.0,
        failure_threshold=3,
        recovery_check_interval=0.1,  # 快速测试
        decision_cache_ttl=5
    )


@pytest_asyncio.fixture
async def soldier_engine(soldier_config, event_bus):
    """Soldier引擎fixture"""
    engine = SoldierEngineV2(soldier_config)
    
    # 直接设置event_bus（跳过完整初始化）
    engine.event_bus = event_bus
    engine.state = "READY"
    
    # Mock LLM推理引擎
    engine.llm_inference = AsyncMock()
    
    # Mock DeepSeek客户端
    engine.deepseek_client = AsyncMock()
    
    yield engine
    
    # 清理
    await engine.stop_health_check()


class TestRecoveryDetection:
    """恢复检测测试"""
    
    @pytest.mark.asyncio
    async def test_recovery_detection_from_degraded_mode(self, soldier_engine):
        """测试从降级模式检测恢复"""
        # 设置为降级模式
        soldier_engine.mode = SoldierMode.DEGRADED
        soldier_engine.is_healthy = False
        soldier_engine.consecutive_failures = 3
        
        # Mock健康检查通过
        mock_result = MagicMock()
        mock_result.latency_ms = 10.0
        soldier_engine.llm_inference.infer = AsyncMock(return_value=mock_result)
        
        # 尝试恢复
        await soldier_engine._attempt_recovery()
        
        # 验证恢复成功
        assert soldier_engine.mode == SoldierMode.NORMAL
        assert soldier_engine.is_healthy is True
        assert soldier_engine.consecutive_failures == 0
        assert soldier_engine.stats['successful_recoveries'] == 1
    
    @pytest.mark.asyncio
    async def test_recovery_detection_fails_on_exception(self, soldier_engine):
        """测试恢复检测在异常时失败"""
        # 设置为降级模式
        soldier_engine.mode = SoldierMode.DEGRADED
        
        # Mock健康检查失败
        soldier_engine.llm_inference.infer = AsyncMock(side_effect=RuntimeError("Check fails"))
        
        # 尝试恢复
        await soldier_engine._attempt_recovery()
        
        # 验证恢复失败（保持降级模式）
        assert soldier_engine.mode == SoldierMode.DEGRADED
    
    @pytest.mark.asyncio
    async def test_recovery_detection_success_on_healthy_check(self, soldier_engine):
        """测试健康检查通过时恢复成功"""
        # 设置为降级模式
        soldier_engine.mode = SoldierMode.DEGRADED
        
        # Mock健康检查通过
        mock_result = MagicMock()
        mock_result.latency_ms = 10.0
        soldier_engine.llm_inference.infer = AsyncMock(return_value=mock_result)
        
        # 尝试恢复
        await soldier_engine._attempt_recovery()
        
        # 验证恢复成功
        assert soldier_engine.mode == SoldierMode.NORMAL
        assert soldier_engine.stats['successful_recoveries'] == 1


class TestAutoSwitchback:
    """自动回切测试"""
    
    @pytest.mark.asyncio
    async def test_auto_switchback_cloud_to_local(self, soldier_engine):
        """测试自动回切（Cloud → Local）"""
        # 设置为降级模式
        soldier_engine.mode = SoldierMode.DEGRADED
        initial_mode = soldier_engine.mode
        
        # Mock健康检查通过
        mock_result = MagicMock()
        mock_result.latency_ms = 10.0
        soldier_engine.llm_inference.infer = AsyncMock(return_value=mock_result)
        
        # 执行恢复
        await soldier_engine._attempt_recovery()
        
        # 验证模式切换
        assert initial_mode == SoldierMode.DEGRADED
        assert soldier_engine.mode == SoldierMode.NORMAL
    
    @pytest.mark.asyncio
    async def test_switchback_resets_failure_counters(self, soldier_engine):
        """测试回切重置失败计数器"""
        # 设置为降级模式，带失败计数
        soldier_engine.mode = SoldierMode.DEGRADED
        soldier_engine.consecutive_failures = 5
        soldier_engine.is_healthy = False
        
        # Mock健康检查通过
        mock_result = MagicMock()
        mock_result.latency_ms = 10.0
        soldier_engine.llm_inference.infer = AsyncMock(return_value=mock_result)
        
        # 执行恢复
        await soldier_engine._attempt_recovery()
        
        # 验证计数器重置
        assert soldier_engine.consecutive_failures == 0
        assert soldier_engine.is_healthy is True
    
    @pytest.mark.asyncio
    async def test_no_switchback_if_already_normal(self, soldier_engine):
        """测试已经是正常模式时不执行回切"""
        # 设置为正常模式
        soldier_engine.mode = SoldierMode.NORMAL
        initial_recoveries = soldier_engine.stats.get('successful_recoveries', 0)
        
        # 尝试恢复
        await soldier_engine._attempt_recovery()
        
        # 验证没有执行恢复操作
        assert soldier_engine.mode == SoldierMode.NORMAL
        # 恢复计数不应增加
        assert soldier_engine.stats.get('successful_recoveries', 0) == initial_recoveries


class TestRecoveryNotification:
    """恢复通知测试"""
    
    @pytest.mark.asyncio
    async def test_recovery_publishes_event(self, soldier_engine, event_bus):
        """测试恢复时发布事件"""
        # 设置为降级模式
        soldier_engine.mode = SoldierMode.DEGRADED
        
        # 确认event_bus是同一个实例
        assert soldier_engine.event_bus is event_bus
        
        # Mock健康检查通过
        mock_result = MagicMock()
        mock_result.latency_ms = 10.0
        soldier_engine.llm_inference.infer = AsyncMock(return_value=mock_result)
        
        # 订阅系统告警事件
        events_received = []
        
        async def event_handler(event: Event):
            events_received.append(event)
        
        await event_bus.subscribe(EventType.SYSTEM_ALERT, event_handler)
        
        # 执行恢复
        await soldier_engine._attempt_recovery()
        
        # 等待事件处理
        for _ in range(10):
            await asyncio.sleep(0.05)
            if len(events_received) > 0:
                break
        
        # 验证事件发布
        assert len(events_received) > 0
        recovery_event = events_received[0]
        assert recovery_event.data['alert_type'] == 'soldier_recovery'
        assert recovery_event.data['reason'] == 'local_model_health_restored'
    
    @pytest.mark.asyncio
    async def test_recovery_event_has_timestamp(self, soldier_engine, event_bus):
        """测试恢复事件包含时间戳"""
        # 设置为降级模式
        soldier_engine.mode = SoldierMode.DEGRADED
        
        # Mock健康检查通过
        mock_result = MagicMock()
        mock_result.latency_ms = 10.0
        soldier_engine.llm_inference.infer = AsyncMock(return_value=mock_result)
        
        # 订阅系统告警事件
        events_received = []
        
        async def event_handler(event: Event):
            events_received.append(event)
        
        await event_bus.subscribe(EventType.SYSTEM_ALERT, event_handler)
        
        # 执行恢复
        await soldier_engine._attempt_recovery()
        
        # 等待事件处理
        for _ in range(10):
            await asyncio.sleep(0.05)
            if len(events_received) > 0:
                break
        
        # 验证时间戳
        assert len(events_received) > 0
        recovery_event = events_received[0]
        assert 'timestamp' in recovery_event.data
    
    @pytest.mark.asyncio
    async def test_no_event_on_failed_recovery(self, soldier_engine, event_bus):
        """测试恢复失败时不发布事件"""
        # 设置为降级模式
        soldier_engine.mode = SoldierMode.DEGRADED
        
        # Mock健康检查失败
        soldier_engine.llm_inference.infer = AsyncMock(side_effect=RuntimeError("Health check failed"))
        
        # 订阅系统告警事件
        events_received = []
        
        async def event_handler(event: Event):
            if event.data.get('alert_type') == 'soldier_recovery':
                events_received.append(event)
        
        await event_bus.subscribe(EventType.SYSTEM_ALERT, event_handler)
        
        # 尝试恢复
        await soldier_engine._attempt_recovery()
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        # 验证没有发布恢复事件
        assert len(events_received) == 0
        assert soldier_engine.mode == SoldierMode.DEGRADED


class TestRecoveryLatency:
    """恢复延迟测试"""
    
    @pytest.mark.asyncio
    async def test_recovery_completes_quickly(self, soldier_engine):
        """测试恢复操作快速完成"""
        # 设置为降级模式
        soldier_engine.mode = SoldierMode.DEGRADED
        
        # Mock健康检查通过
        mock_result = MagicMock()
        mock_result.latency_ms = 10.0
        soldier_engine.llm_inference.infer = AsyncMock(return_value=mock_result)
        
        # 记录开始时间
        start_time = datetime.now()
        
        # 执行恢复
        await soldier_engine._attempt_recovery()
        
        # 记录结束时间
        end_time = datetime.now()
        latency_ms = (end_time - start_time).total_seconds() * 1000
        
        # 验证恢复成功且延迟合理（小于1秒）
        assert soldier_engine.mode == SoldierMode.NORMAL
        assert latency_ms < 1000
    
    @pytest.mark.asyncio
    async def test_recovery_tracks_successful_count(self, soldier_engine):
        """测试恢复跟踪成功计数"""
        # 设置为降级模式
        soldier_engine.mode = SoldierMode.DEGRADED
        
        # Mock健康检查通过
        mock_result = MagicMock()
        mock_result.latency_ms = 10.0
        soldier_engine.llm_inference.infer = AsyncMock(return_value=mock_result)
        
        # 执行恢复
        await soldier_engine._attempt_recovery()
        
        # 验证成功计数
        assert soldier_engine.stats['successful_recoveries'] == 1


class TestRecoveryStatistics:
    """恢复统计测试"""
    
    @pytest.mark.asyncio
    async def test_successful_recoveries_counter(self, soldier_engine):
        """测试成功恢复计数"""
        # 设置为降级模式
        soldier_engine.mode = SoldierMode.DEGRADED
        
        # Mock健康检查通过
        mock_result = MagicMock()
        mock_result.latency_ms = 10.0
        soldier_engine.llm_inference.infer = AsyncMock(return_value=mock_result)
        
        # 执行多次恢复
        for _ in range(3):
            soldier_engine.mode = SoldierMode.DEGRADED
            await soldier_engine._attempt_recovery()
        
        # 验证计数
        assert soldier_engine.stats['successful_recoveries'] == 3
    
    @pytest.mark.asyncio
    async def test_recovery_resets_consecutive_failures(self, soldier_engine):
        """测试恢复重置连续失败计数"""
        # 设置为降级模式，带失败计数
        soldier_engine.mode = SoldierMode.DEGRADED
        soldier_engine.consecutive_failures = 10
        
        # Mock健康检查通过
        mock_result = MagicMock()
        mock_result.latency_ms = 10.0
        soldier_engine.llm_inference.infer = AsyncMock(return_value=mock_result)
        
        # 尝试恢复
        await soldier_engine._attempt_recovery()
        
        # 验证计数重置
        assert soldier_engine.consecutive_failures == 0
    
    @pytest.mark.asyncio
    async def test_failed_recovery_keeps_degraded_mode(self, soldier_engine):
        """测试失败恢复保持降级模式"""
        # 设置为降级模式
        soldier_engine.mode = SoldierMode.DEGRADED
        
        # Mock健康检查失败
        soldier_engine.llm_inference.infer = AsyncMock(side_effect=RuntimeError("Failed"))
        
        # 尝试恢复
        await soldier_engine._attempt_recovery()
        
        # 验证保持降级模式
        assert soldier_engine.mode == SoldierMode.DEGRADED
        assert soldier_engine.stats.get('successful_recoveries', 0) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
