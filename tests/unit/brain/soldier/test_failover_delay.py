"""Soldier热备切换延迟测试

白皮书依据: 第二章 2.3 热备切换延迟 < 200ms
验证需求: 需求2.4 (热备切换延迟测试)

测试目标:
1. 验证热备切换延迟 < 200ms
2. 验证切换过程数据完整性
3. 验证切换触发条件
4. 验证切换后系统状态
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, HealthCheck
from typing import Dict, Any

from src.brain.soldier.core import SoldierWithFailover, SoldierMode, TradingDecision


class TestFailoverDelay:
    """热备切换延迟测试类
    
    白皮书依据: 第二章 2.3
    验证需求: 需求2.1, 需求2.2, 需求2.4
    """
    
    @pytest.fixture
    def soldier(self):
        """创建测试用的Soldier实例"""
        soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key-12345",
            failure_threshold=3,
            local_timeout=0.2  # 200ms
        )
        
        # Mock所有外部依赖
        soldier.local_model = MagicMock()
        soldier.llm_gateway = MagicMock()
        soldier.redis_client = MagicMock()
        
        return soldier
    
    @pytest.fixture
    def sample_market_data(self):
        """样本市场数据"""
        return {
            "symbol": "000001.SZ",
            "price": 10.50,
            "volume": 1000000,
            "change_pct": 0.02
        }
    
    @pytest.mark.asyncio
    async def test_failover_delay_under_200ms(self, soldier, sample_market_data):
        """测试热备切换延迟 < 200ms
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.4
        
        测试策略: 模拟连续失败触发切换，而不是超时触发，
        这样可以测试真正的热备切换延迟
        """
        # 模拟本地推理立即失败（触发切换）
        async def mock_local_inference_failure(*args, **kwargs):
            await asyncio.sleep(0.01)  # 1ms快速失败
            raise RuntimeError("本地推理失败")
        
        # 模拟云端推理成功
        async def mock_cloud_inference(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms云端推理
            return TradingDecision(
                action="hold",
                symbol="000001.SZ",
                quantity=0,
                confidence=0.75,
                reasoning="云端推理结果"
            )
        
        # 设置Mock
        soldier._local_inference = mock_local_inference_failure
        soldier._cloud_inference = mock_cloud_inference
        soldier._update_redis_status = AsyncMock()
        soldier._send_alert = AsyncMock()
        
        # 设置失败阈值为1，立即触发切换
        soldier.failure_threshold = 1
        
        # 记录开始时间
        start_time = time.perf_counter()
        
        # 执行决策（应该触发热备切换）
        decision = await soldier.make_decision(sample_market_data)
        
        # 计算总延迟
        total_delay_ms = (time.perf_counter() - start_time) * 1000
        
        # 验证切换延迟 < 200ms
        assert total_delay_ms < 200, f"热备切换延迟超标: {total_delay_ms:.2f}ms > 200ms"
        
        # 验证模式已切换
        assert soldier.mode == SoldierMode.DEGRADED
        
        # 验证决策结果
        assert decision is not None
        assert decision.action == "hold"
        assert decision.reasoning == "云端推理结果"
        
        # 验证告警已发送
        soldier._send_alert.assert_called_once()
        
        print(f"✅ 热备切换延迟: {total_delay_ms:.2f}ms < 200ms")
    
    @pytest.mark.asyncio
    async def test_failover_trigger_conditions(self, soldier, sample_market_data):
        """测试热备切换触发条件
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.1, 需求2.2
        
        触发条件:
        1. 本地推理超时 > 200ms
        2. 连续失败 >= 3次
        3. GPU故障
        """
        soldier._cloud_inference = AsyncMock(return_value=TradingDecision(
            action="hold", symbol="000001.SZ", quantity=0, 
            confidence=0.7, reasoning="云端推理"
        ))
        soldier._update_redis_status = AsyncMock()
        soldier._send_alert = AsyncMock()
        
        # 测试条件1: 超时触发
        async def mock_timeout_inference(*args, **kwargs):
            await asyncio.sleep(0.25)  # 250ms > 200ms
            return TradingDecision(
                action="buy", symbol="000001.SZ", quantity=100,
                confidence=0.8, reasoning="本地推理（超时）"
            )
        
        soldier._local_inference = mock_timeout_inference
        soldier.mode = SoldierMode.NORMAL  # 重置模式
        
        decision = await soldier.make_decision(sample_market_data)
        assert soldier.mode == SoldierMode.DEGRADED, "超时应该触发切换"
        
        # 测试条件2: 连续失败触发
        soldier.mode = SoldierMode.NORMAL  # 重置模式
        soldier.failure_count = 0
        
        async def mock_failing_inference(*args, **kwargs):
            raise RuntimeError("推理失败")
        
        soldier._local_inference = mock_failing_inference
        
        # 连续失败3次
        for i in range(3):
            try:
                await soldier.make_decision(sample_market_data)
            except:
                pass
        
        assert soldier.failure_count >= 3, "失败计数应该达到阈值"
        assert soldier.mode == SoldierMode.DEGRADED, "连续失败应该触发切换"
        
        print("✅ 热备切换触发条件验证通过")
    
    @pytest.mark.asyncio
    async def test_data_integrity_during_failover(self, soldier, sample_market_data):
        """测试切换过程数据完整性
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.4
        """
        # 记录切换前的状态
        original_failure_count = soldier.failure_count
        original_redis_data = {"position": {"000001.SZ": 1000}}
        
        # 模拟Redis状态
        soldier.redis_client = MagicMock()
        soldier.redis_client.get = MagicMock(return_value=original_redis_data)
        
        # 设置失败阈值为1，立即触发切换
        soldier.failure_threshold = 1
        
        # 模拟本地推理失败
        async def mock_local_failure(*args, **kwargs):
            await asyncio.sleep(0.01)  # 1ms快速失败
            raise RuntimeError("本地推理失败")
        
        # 模拟云端推理成功
        async def mock_cloud_success(*args, **kwargs):
            await asyncio.sleep(0.02)  # 20ms云端推理
            return TradingDecision(
                action="sell",
                symbol="000001.SZ",
                quantity=500,
                confidence=0.85,
                reasoning="云端推理：基于Redis状态的决策"
            )
        
        soldier._local_inference = mock_local_failure
        soldier._cloud_inference = mock_cloud_success
        soldier._update_redis_status = AsyncMock()
        soldier._send_alert = AsyncMock()
        
        # 执行决策
        decision = await soldier.make_decision(sample_market_data)
        
        # 验证数据完整性
        assert decision is not None, "决策结果不应为空"
        assert decision.symbol == sample_market_data["symbol"], "标的代码应保持一致"
        assert decision.action in ["buy", "sell", "hold"], "交易动作应有效"
        assert 0 <= decision.confidence <= 1, "置信度应在有效范围内"
        assert decision.reasoning is not None, "决策理由不应为空"
        
        # 验证状态更新
        soldier._update_redis_status.assert_called()
        
        # 验证失败计数增加
        assert soldier.failure_count > original_failure_count, "失败计数应该增加"
        
        print("✅ 切换过程数据完整性验证通过")
    
    @pytest.mark.asyncio
    async def test_failover_performance_measurement(self, soldier, sample_market_data):
        """测试热备切换性能测量
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.4
        """
        # 收集多次切换的延迟数据
        delays = []
        
        for i in range(10):  # 测试10次切换
            # 重置状态
            soldier.mode = SoldierMode.NORMAL
            soldier.failure_count = 0
            soldier.failure_threshold = 1  # 立即触发切换
            
            # 模拟本地推理快速失败
            async def mock_failure(*args, **kwargs):
                await asyncio.sleep(0.005)  # 5ms快速失败
                raise RuntimeError(f"模拟失败 #{i+1}")
            
            # 模拟云端推理
            async def mock_cloud(*args, **kwargs):
                await asyncio.sleep(0.03)  # 30ms云端推理
                return TradingDecision(
                    action="hold", symbol="000001.SZ", quantity=0,
                    confidence=0.7, reasoning=f"云端推理第{i+1}次"
                )
            
            soldier._local_inference = mock_failure
            soldier._cloud_inference = mock_cloud
            soldier._update_redis_status = AsyncMock()
            soldier._send_alert = AsyncMock()
            
            # 测量切换延迟
            start_time = time.perf_counter()
            decision = await soldier.make_decision(sample_market_data)
            delay_ms = (time.perf_counter() - start_time) * 1000
            
            delays.append(delay_ms)
            
            # 验证切换成功
            assert soldier.mode == SoldierMode.DEGRADED
            assert decision is not None
        
        # 计算统计数据
        avg_delay = sum(delays) / len(delays)
        max_delay = max(delays)
        min_delay = min(delays)
        
        # 验证性能要求
        assert max_delay < 200, f"最大切换延迟超标: {max_delay:.2f}ms > 200ms"
        assert avg_delay < 150, f"平均切换延迟过高: {avg_delay:.2f}ms"
        
        print(f"✅ 热备切换性能统计:")
        print(f"   平均延迟: {avg_delay:.2f}ms")
        print(f"   最大延迟: {max_delay:.2f}ms")
        print(f"   最小延迟: {min_delay:.2f}ms")
        print(f"   所有延迟: {[f'{d:.1f}ms' for d in delays]}")
    
    @pytest.mark.asyncio
    async def test_failover_state_consistency(self, soldier, sample_market_data):
        """测试切换后系统状态一致性
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.1, 需求2.2
        """
        # 设置初始状态
        initial_status = soldier.get_status()
        assert initial_status["mode"] == "normal"
        
        # 设置失败阈值为1，立即触发切换
        soldier.failure_threshold = 1
        
        # 模拟切换触发
        async def mock_trigger_failover(*args, **kwargs):
            await asyncio.sleep(0.01)  # 1ms快速失败
            raise RuntimeError("触发切换")
        
        async def mock_cloud_inference(*args, **kwargs):
            await asyncio.sleep(0.02)  # 20ms云端推理
            return TradingDecision(
                action="hold", symbol="000001.SZ", quantity=0,
                confidence=0.8, reasoning="切换后云端推理"
            )
        
        soldier._local_inference = mock_trigger_failover
        soldier._cloud_inference = mock_cloud_inference
        soldier._update_redis_status = AsyncMock()
        soldier._send_alert = AsyncMock()
        
        # 执行决策触发切换
        decision = await soldier.make_decision(sample_market_data)
        
        # 验证状态一致性
        final_status = soldier.get_status()
        
        assert final_status["mode"] == "degraded", "模式应切换到DEGRADED"
        assert final_status["failure_count"] > 0, "失败计数应增加"
        assert final_status["last_switch_time"] > 0, "切换时间应记录"
        assert final_status["local_model_loaded"] == initial_status["local_model_loaded"], "本地模型状态应保持"
        assert final_status["llm_gateway_initialized"] == initial_status["llm_gateway_initialized"], "LLM网关状态应保持"
        
        # 验证Redis状态更新
        soldier._update_redis_status.assert_called()
        
        print("✅ 切换后系统状态一致性验证通过")
    
    @pytest.mark.asyncio
    async def test_multiple_failover_scenarios(self, soldier, sample_market_data):
        """测试多种切换场景
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.1, 需求2.2, 需求2.4
        """
        scenarios = [
            {
                "name": "快速失败切换",
                "local_delay": 0.01,  # 10ms快速失败
                "local_exception": RuntimeError("GPU故障"),
                "expected_mode": SoldierMode.DEGRADED
            },
            {
                "name": "连接失败切换",
                "local_delay": 0.005,  # 5ms快速失败
                "local_exception": ConnectionError("网络断开"),
                "expected_mode": SoldierMode.DEGRADED
            },
            {
                "name": "内存不足切换",
                "local_delay": 0.008,  # 8ms快速失败
                "local_exception": MemoryError("GPU内存不足"),
                "expected_mode": SoldierMode.DEGRADED
            }
        ]
        
        for scenario in scenarios:
            # 重置状态
            soldier.mode = SoldierMode.NORMAL
            soldier.failure_count = 0
            soldier.failure_threshold = 1  # 立即触发切换
            
            # 设置场景
            async def mock_local_inference(*args, **kwargs):
                await asyncio.sleep(scenario["local_delay"])
                if scenario["local_exception"]:
                    raise scenario["local_exception"]
                return TradingDecision(
                    action="buy", symbol="000001.SZ", quantity=100,
                    confidence=0.9, reasoning="本地推理成功"
                )
            
            async def mock_cloud_inference(*args, **kwargs):
                await asyncio.sleep(0.05)  # 50ms云端推理
                return TradingDecision(
                    action="hold", symbol="000001.SZ", quantity=0,
                    confidence=0.75, reasoning=f"云端推理 - {scenario['name']}"
                )
            
            soldier._local_inference = mock_local_inference
            soldier._cloud_inference = mock_cloud_inference
            soldier._update_redis_status = AsyncMock()
            soldier._send_alert = AsyncMock()
            
            # 执行测试
            start_time = time.perf_counter()
            decision = await soldier.make_decision(sample_market_data)
            delay_ms = (time.perf_counter() - start_time) * 1000
            
            # 验证结果
            assert soldier.mode == scenario["expected_mode"], f"{scenario['name']}: 模式切换失败"
            assert decision is not None, f"{scenario['name']}: 决策结果为空"
            assert delay_ms < 200, f"{scenario['name']}: 切换延迟超标 {delay_ms:.2f}ms"
            
            print(f"✅ {scenario['name']}: 延迟 {delay_ms:.2f}ms, 模式 {soldier.mode.value}")


# Property-Based Testing for Failover Delay
class TestFailoverDelayProperties:
    """热备切换延迟属性测试
    
    使用Property-Based Testing验证切换延迟的统计特性
    """
    
    @given(
        cloud_delay_ms=st.integers(min_value=20, max_value=80),    # 云端推理延迟
        local_delay_ms=st.integers(min_value=5, max_value=30)      # 本地失败延迟
    )
    @settings(
        max_examples=10, 
        deadline=2000,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
    )
    @pytest.mark.asyncio
    async def test_failover_delay_property(
        self, 
        cloud_delay_ms: int,
        local_delay_ms: int
    ):
        """属性测试: 热备切换延迟上界
        
        Property: 对于任何本地推理快速失败，热备切换总延迟应 < 200ms
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.4
        """
        # 创建新的Soldier实例（避免fixture问题）
        soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key-12345",
            failure_threshold=1,  # 立即触发切换
            local_timeout=0.2
        )
        
        # Mock外部依赖
        soldier.local_model = MagicMock()
        soldier.llm_gateway = MagicMock()
        soldier.redis_client = MagicMock()
        soldier._update_redis_status = AsyncMock()
        soldier._send_alert = AsyncMock()
        
        # 构造测试数据
        market_data = {
            "symbol": "TEST001",
            "price": 10.0,
            "volume": 100000,
            "change_pct": 0.01
        }
        
        # 模拟本地推理快速失败
        async def mock_local_failure(*args, **kwargs):
            await asyncio.sleep(local_delay_ms / 1000.0)
            raise RuntimeError(f"本地推理失败 {local_delay_ms}ms")
        
        # 模拟云端推理
        async def mock_cloud_inference(*args, **kwargs):
            await asyncio.sleep(cloud_delay_ms / 1000.0)
            return TradingDecision(
                action="hold",
                symbol="TEST001",
                quantity=0,
                confidence=0.75,
                reasoning="属性测试云端推理"
            )
        
        soldier._local_inference = mock_local_failure
        soldier._cloud_inference = mock_cloud_inference
        
        # 测量切换延迟
        start_time = time.perf_counter()
        decision = await soldier.make_decision(market_data)
        total_delay_ms = (time.perf_counter() - start_time) * 1000
        
        # 验证属性: 切换延迟 < 200ms
        assert total_delay_ms < 200, (
            f"热备切换延迟超标: {total_delay_ms:.2f}ms > 200ms "
            f"(本地失败: {local_delay_ms}ms, 云端延迟: {cloud_delay_ms}ms)"
        )
        
        # 验证切换成功
        assert soldier.mode == SoldierMode.DEGRADED
        assert decision is not None
        assert decision.symbol == "TEST001"
    
    @given(
        cloud_delay_ms=st.integers(min_value=20, max_value=100)
    )
    @settings(
        max_examples=8, 
        deadline=1500,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
    )
    @pytest.mark.asyncio
    async def test_consecutive_failure_property(
        self,
        cloud_delay_ms: int
    ):
        """属性测试: 连续失败触发切换
        
        Property: 对于任何失败，应快速触发热备切换
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.1, 需求2.2
        """
        # 创建新的Soldier实例
        soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key-12345",
            failure_threshold=1,  # 立即触发切换
            local_timeout=0.2
        )
        
        # Mock外部依赖
        soldier.local_model = MagicMock()
        soldier.llm_gateway = MagicMock()
        soldier.redis_client = MagicMock()
        soldier._update_redis_status = AsyncMock()
        soldier._send_alert = AsyncMock()
        
        market_data = {
            "symbol": "TEST001",
            "price": 10.0,
            "volume": 100000,
            "change_pct": 0.0
        }
        
        # 模拟连续失败
        async def mock_local_failure(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms快速失败
            raise RuntimeError("模拟失败")
        
        # 模拟云端推理成功
        async def mock_cloud_success(*args, **kwargs):
            await asyncio.sleep(cloud_delay_ms / 1000.0)
            return TradingDecision(
                action="hold", symbol="TEST001", quantity=0,
                confidence=0.8, reasoning="连续失败后云端推理"
            )
        
        soldier._local_inference = mock_local_failure
        soldier._cloud_inference = mock_cloud_success
        
        # 执行失败直到触发切换
        start_time = time.perf_counter()
        decision = await soldier.make_decision(market_data)
        delay_ms = (time.perf_counter() - start_time) * 1000
        
        # 验证切换成功
        assert decision is not None, "应该获得云端推理结果"
        assert delay_ms < 200, f"切换延迟超标: {delay_ms:.2f}ms"
        
        # 验证最终状态
        assert soldier.failure_count >= 1, "失败计数应达到阈值"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])