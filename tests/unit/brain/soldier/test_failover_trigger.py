"""Soldier热备切换触发条件测试

白皮书依据: 第二章 2.3 热备切换触发条件
验证需求: 需求2.1, 需求2.2 (热备切换触发测试)

测试目标:
1. 验证超时触发切换 (> 200ms)
2. 验证连续失败触发切换 (3次)
3. 验证GPU故障触发切换
4. 验证切换条件的准确性
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, HealthCheck
from typing import Dict, Any

from src.brain.soldier.core import SoldierWithFailover, SoldierMode, TradingDecision


class TestFailoverTriggerConditions:
    """热备切换触发条件测试类
    
    白皮书依据: 第二章 2.3
    验证需求: 需求2.1, 需求2.2
    """
    
    @pytest.fixture
    def soldier(self):
        """创建测试用的Soldier实例"""
        soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key-12345",
            failure_threshold=3,  # 标准阈值
            local_timeout=0.2  # 200ms
        )
        
        # Mock所有外部依赖
        soldier.local_model = MagicMock()
        soldier.cloud_api = MagicMock()
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
    async def test_timeout_trigger_condition(self, soldier, sample_market_data):
        """测试超时触发条件
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.1
        
        条件: 本地推理超时 > 200ms
        """
        # 模拟本地推理超时
        async def mock_timeout_inference(*args, **kwargs):
            await asyncio.sleep(0.25)  # 250ms > 200ms
            return TradingDecision(
                action="buy", symbol="000001.SZ", quantity=100,
                confidence=0.8, reasoning="本地推理（超时）"
            )
        
        # 模拟云端推理成功
        async def mock_cloud_inference(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms云端推理
            return TradingDecision(
                action="hold", symbol="000001.SZ", quantity=0,
                confidence=0.75, reasoning="云端推理（超时切换）"
            )
        
        soldier._local_inference = mock_timeout_inference
        soldier._cloud_inference = mock_cloud_inference
        soldier._update_redis_status = AsyncMock()
        soldier._send_alert = AsyncMock()
        
        # 确保初始状态为NORMAL
        soldier.mode = SoldierMode.NORMAL
        
        # 执行决策
        start_time = time.perf_counter()
        decision = await soldier.make_decision(sample_market_data)
        total_time = (time.perf_counter() - start_time) * 1000
        
        # 验证超时触发切换
        assert soldier.mode == SoldierMode.DEGRADED, "超时应该触发切换到DEGRADED模式"
        assert decision.reasoning == "云端推理（超时切换）", "应该使用云端推理结果"
        assert total_time > 200, f"总时间应该 > 200ms，实际: {total_time:.2f}ms"
        
        # 验证告警发送
        soldier._send_alert.assert_called()
        alert_call = soldier._send_alert.call_args[0][0]
        assert "推理超时" in alert_call, "告警消息应包含超时信息"
        
        print(f"✅ 超时触发测试通过: {total_time:.2f}ms, 模式: {soldier.mode.value}")
    
    @pytest.mark.asyncio
    async def test_consecutive_failure_trigger_condition(self, soldier, sample_market_data):
        """测试连续失败触发条件
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.2
        
        条件: 连续失败 >= 3次
        """
        # 模拟本地推理连续失败
        async def mock_failing_inference(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms快速失败
            raise RuntimeError("模拟推理失败")
        
        # 模拟云端推理成功
        async def mock_cloud_inference(*args, **kwargs):
            await asyncio.sleep(0.03)  # 30ms云端推理
            return TradingDecision(
                action="hold", symbol="000001.SZ", quantity=0,
                confidence=0.8, reasoning="云端推理（连续失败切换）"
            )
        
        soldier._local_inference = mock_failing_inference
        soldier._cloud_inference = mock_cloud_inference
        soldier._update_redis_status = AsyncMock()
        soldier._send_alert = AsyncMock()
        
        # 确保初始状态
        soldier.mode = SoldierMode.NORMAL
        soldier.failure_count = 0
        
        # 执行连续失败
        for i in range(3):
            try:
                decision = await soldier.make_decision(sample_market_data)
                # 第3次失败后应该切换并返回云端结果
                if i == 2:  # 第3次（索引2）
                    assert soldier.mode == SoldierMode.DEGRADED, f"第{i+1}次失败后应该切换模式"
                    assert decision.reasoning == "云端推理（连续失败切换）", "应该使用云端推理结果"
                    break
            except Exception:
                # 前两次可能抛出异常，这是正常的
                pass
        
        # 验证最终状态
        assert soldier.failure_count >= 3, f"失败计数应该 >= 3，实际: {soldier.failure_count}"
        assert soldier.mode == SoldierMode.DEGRADED, "连续失败应该触发切换"
        
        # 验证告警发送
        soldier._send_alert.assert_called()
        alert_call = soldier._send_alert.call_args[0][0]
        assert "连续失败" in alert_call, "告警消息应包含连续失败信息"
        
        print(f"✅ 连续失败触发测试通过: 失败{soldier.failure_count}次, 模式: {soldier.mode.value}")
    
    @pytest.mark.asyncio
    async def test_gpu_failure_trigger_condition(self, soldier, sample_market_data):
        """测试GPU故障触发条件
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.1, 需求2.2
        
        条件: GPU驱动故障
        """
        # Mock GPU健康检查返回故障
        async def mock_gpu_failure(*args, **kwargs):
            return False  # GPU不健康
        
        # 模拟云端推理成功
        async def mock_cloud_inference(*args, **kwargs):
            await asyncio.sleep(0.04)  # 40ms云端推理
            return TradingDecision(
                action="hold", symbol="000001.SZ", quantity=0,
                confidence=0.85, reasoning="云端推理（GPU故障切换）"
            )
        
        soldier._check_gpu_health = mock_gpu_failure
        soldier._cloud_inference = mock_cloud_inference
        soldier._update_redis_status = AsyncMock()
        soldier._send_alert = AsyncMock()
        
        # 确保初始状态为NORMAL
        soldier.mode = SoldierMode.NORMAL
        
        # 执行决策
        decision = await soldier.make_decision(sample_market_data)
        
        # 验证GPU故障触发切换
        assert soldier.mode == SoldierMode.DEGRADED, "GPU故障应该触发切换到DEGRADED模式"
        assert decision.reasoning == "云端推理（GPU故障切换）", "应该使用云端推理结果"
        
        # 验证告警发送
        soldier._send_alert.assert_called()
        alert_call = soldier._send_alert.call_args[0][0]
        assert "GPU故障" in alert_call, "告警消息应包含GPU故障信息"
        
        print(f"✅ GPU故障触发测试通过: 模式: {soldier.mode.value}")
    
    @pytest.mark.asyncio
    async def test_trigger_condition_detection_accuracy(self, soldier, sample_market_data):
        """测试触发条件检测准确性
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.1, 需求2.2
        """
        # 测试超时检测准确性
        assert await soldier._detect_timeout_condition(250.0, 200.0) == True, "250ms > 200ms应该检测为超时"
        assert await soldier._detect_timeout_condition(150.0, 200.0) == False, "150ms < 200ms不应该检测为超时"
        assert await soldier._detect_timeout_condition(200.0, 200.0) == False, "200ms = 200ms不应该检测为超时"
        
        # 测试连续失败检测准确性
        soldier.failure_count = 3
        soldier.failure_threshold = 3
        assert await soldier._detect_consecutive_failure_condition() == True, "失败3次达到阈值应该检测为连续失败"
        
        soldier.failure_count = 2
        assert await soldier._detect_consecutive_failure_condition() == False, "失败2次未达到阈值不应该检测为连续失败"
        
        soldier.failure_count = 5
        assert await soldier._detect_consecutive_failure_condition() == True, "失败5次超过阈值应该检测为连续失败"
        
        print("✅ 触发条件检测准确性测试通过")
    
    @pytest.mark.asyncio
    async def test_multiple_trigger_conditions_priority(self, soldier, sample_market_data):
        """测试多个触发条件的优先级
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.1, 需求2.2
        
        当多个条件同时满足时，应该按优先级处理
        """
        # Mock GPU故障（最高优先级）
        async def mock_gpu_failure(*args, **kwargs):
            return False
        
        # 模拟本地推理也会超时
        async def mock_timeout_inference(*args, **kwargs):
            await asyncio.sleep(0.3)  # 300ms超时
            return TradingDecision(
                action="buy", symbol="000001.SZ", quantity=100,
                confidence=0.8, reasoning="本地推理（不应该执行到这里）"
            )
        
        # 模拟云端推理
        async def mock_cloud_inference(*args, **kwargs):
            await asyncio.sleep(0.02)  # 20ms云端推理
            return TradingDecision(
                action="hold", symbol="000001.SZ", quantity=0,
                confidence=0.9, reasoning="云端推理（优先级测试）"
            )
        
        soldier._check_gpu_health = mock_gpu_failure
        soldier._local_inference = mock_timeout_inference
        soldier._cloud_inference = mock_cloud_inference
        soldier._update_redis_status = AsyncMock()
        soldier._send_alert = AsyncMock()
        
        # 设置连续失败状态
        soldier.failure_count = 2  # 接近阈值
        soldier.mode = SoldierMode.NORMAL
        
        # 执行决策
        start_time = time.perf_counter()
        decision = await soldier.make_decision(sample_market_data)
        elapsed_time = (time.perf_counter() - start_time) * 1000
        
        # 验证GPU故障优先触发（不应该等待超时）
        assert soldier.mode == SoldierMode.DEGRADED, "应该切换到DEGRADED模式"
        assert decision.reasoning == "云端推理（优先级测试）", "应该使用云端推理结果"
        assert elapsed_time < 100, f"GPU故障应该立即触发，不应该等待超时: {elapsed_time:.2f}ms"
        
        # 验证告警包含GPU故障信息
        soldier._send_alert.assert_called()
        alert_call = soldier._send_alert.call_args[0][0]
        assert "GPU故障" in alert_call, "告警应该是GPU故障而不是超时"
        
        print(f"✅ 多条件优先级测试通过: {elapsed_time:.2f}ms, 原因: GPU故障")
    
    @pytest.mark.asyncio
    async def test_trigger_condition_edge_cases(self, soldier, sample_market_data):
        """测试触发条件边界情况
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.1, 需求2.2
        """
        # 边界情况1: 恰好200ms不应该触发超时
        assert await soldier._detect_timeout_condition(200.0, 200.0) == False, "恰好200ms不应该触发超时"
        assert await soldier._detect_timeout_condition(200.1, 200.0) == True, "200.1ms应该触发超时"
        
        # 边界情况2: 恰好达到失败阈值应该触发
        soldier.failure_count = 3
        soldier.failure_threshold = 3
        assert await soldier._detect_consecutive_failure_condition() == True, "恰好达到阈值应该触发"
        
        soldier.failure_count = 2
        assert await soldier._detect_consecutive_failure_condition() == False, "未达到阈值不应该触发"
        
        # 边界情况3: 已经在DEGRADED模式时不应该重复切换
        soldier.mode = SoldierMode.DEGRADED
        original_switch_time = soldier.last_switch_time
        
        await soldier._trigger_failover("测试重复切换")
        
        # 验证没有重复切换
        assert soldier.mode == SoldierMode.DEGRADED, "应该保持DEGRADED模式"
        assert soldier.last_switch_time == original_switch_time, "切换时间不应该更新"
        
        print("✅ 触发条件边界情况测试通过")


# Property-Based Testing for Trigger Conditions
class TestFailoverTriggerProperties:
    """热备切换触发条件属性测试
    
    使用Property-Based Testing验证触发条件的正确性
    """
    
    @given(
        timeout_ms=st.floats(min_value=201.0, max_value=500.0),  # 超时情况
        failure_count=st.integers(min_value=3, max_value=10)     # 失败次数
    )
    @settings(
        max_examples=5,
        deadline=1500,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
    )
    @pytest.mark.asyncio
    async def test_trigger_condition_property(
        self,
        timeout_ms: float,
        failure_count: int
    ):
        """属性测试: 触发条件正确性
        
        Property: 对于任何超时或失败次数达到阈值的情况，都应该触发切换
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.1, 需求2.2
        """
        # 创建新的Soldier实例
        soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key-12345",
            failure_threshold=3,
            local_timeout=0.2
        )
        
        # Mock外部依赖
        soldier.local_model = MagicMock()
        soldier.cloud_api = MagicMock()
        soldier.redis_client = MagicMock()
        soldier._update_redis_status = AsyncMock()
        soldier._send_alert = AsyncMock()
        
        # 测试超时条件
        timeout_detected = await soldier._detect_timeout_condition(timeout_ms, 200.0)
        assert timeout_detected == True, f"超时{timeout_ms}ms > 200ms应该被检测"
        
        # 测试失败条件
        soldier.failure_count = failure_count
        failure_detected = await soldier._detect_consecutive_failure_condition()
        assert failure_detected == True, f"失败{failure_count}次 >= 3次应该被检测"
    
    @given(
        normal_timeout_ms=st.floats(min_value=10.0, max_value=199.9),  # 正常情况
        normal_failure_count=st.integers(min_value=0, max_value=2)     # 正常失败次数
    )
    @settings(
        max_examples=5,
        deadline=1000,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
    )
    @pytest.mark.asyncio
    async def test_no_trigger_condition_property(
        self,
        normal_timeout_ms: float,
        normal_failure_count: int
    ):
        """属性测试: 正常情况不触发
        
        Property: 对于任何未达到阈值的情况，都不应该触发切换
        
        白皮书依据: 第二章 2.3
        验证需求: 需求2.1, 需求2.2
        """
        # 创建新的Soldier实例
        soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key-12345",
            failure_threshold=3,
            local_timeout=0.2
        )
        
        # 测试正常超时不触发
        timeout_detected = await soldier._detect_timeout_condition(normal_timeout_ms, 200.0)
        assert timeout_detected == False, f"正常延迟{normal_timeout_ms}ms < 200ms不应该被检测"
        
        # 测试正常失败次数不触发
        soldier.failure_count = normal_failure_count
        failure_detected = await soldier._detect_consecutive_failure_condition()
        assert failure_detected == False, f"正常失败{normal_failure_count}次 < 3次不应该被检测"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])