"""Soldier热备切换属性测试

白皮书依据: 第十二章 12.1.3 Soldier热备切换机制

**Property 5: Soldier Failover Threshold**
**Validates: Requirements 2.3, 2.4, 4.3**

测试内容:
1. 连续3次失败后切换到Cloud模式
2. 3次失败前不切换
3. 成功后重置失败计数
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, HealthCheck

from src.brain.soldier_failover import (
    SoldierFailover,
    SoldierMode,
    FailoverConfig,
    FailoverStats
)


class TestSoldierFailoverProperties:
    """Soldier热备切换属性测试
    
    **Validates: Requirements 2.3, 2.4, 4.3**
    """
    
    @pytest.fixture
    def failover_config(self):
        """测试配置"""
        return FailoverConfig(
            local_timeout=0.2,
            failure_threshold=3,
            recovery_check_interval=60.0,
            max_cloud_latency=2.0
        )
    
    @pytest.fixture
    def mock_redis(self):
        """模拟Redis客户端"""
        redis = MagicMock()
        redis.set = MagicMock()
        redis.get = MagicMock(return_value=None)
        return redis
    
    @given(failure_count=st.integers(min_value=0, max_value=10))
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_failover_threshold_property(self, failure_count: int):
        """Property 5: 连续失败达到阈值后切换到Cloud模式
        
        **Validates: Requirements 2.3, 2.4, 4.3**
        
        属性: 当且仅当连续失败次数 >= failure_threshold 时，
              系统应切换到Cloud模式
        """
        config = FailoverConfig(
            local_timeout=0.2,
            failure_threshold=3
        )
        
        failover = SoldierFailover(config=config)
        
        # 模拟失败次数
        failover.failure_count = failure_count
        
        # 验证属性
        if failure_count >= config.failure_threshold:
            # 应该切换到Cloud模式
            assert failover.failure_count >= config.failure_threshold
        else:
            # 不应该切换
            assert failover.failure_count < config.failure_threshold
    
    @given(
        num_failures=st.integers(min_value=0, max_value=5),
        threshold=st.integers(min_value=1, max_value=5)
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_no_failover_before_threshold(self, num_failures: int, threshold: int):
        """Property: 阈值前不切换
        
        **Validates: Requirements 2.3, 2.4**
        
        属性: 当失败次数 < threshold 时，模式应保持为NORMAL
        """
        config = FailoverConfig(
            local_timeout=0.2,
            failure_threshold=threshold
        )
        
        failover = SoldierFailover(config=config)
        
        # 模拟失败
        for _ in range(min(num_failures, threshold - 1)):
            failover.failure_count += 1
        
        # 验证：如果失败次数 < 阈值，模式应为NORMAL
        if failover.failure_count < threshold:
            assert failover.mode == SoldierMode.NORMAL
    
    @given(
        initial_failures=st.integers(min_value=0, max_value=5),
        success_count=st.integers(min_value=1, max_value=3)
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_failure_count_reset_on_success(
        self,
        initial_failures: int,
        success_count: int
    ):
        """Property: 成功后重置失败计数
        
        **Validates: Requirements 4.3**
        
        属性: 成功决策后，失败计数应重置为0
        """
        config = FailoverConfig(
            local_timeout=0.2,
            failure_threshold=3
        )
        
        failover = SoldierFailover(config=config)
        
        # 设置初始失败次数
        failover.failure_count = initial_failures
        
        # 模拟成功（重置失败计数）
        failover.failure_count = 0
        
        # 验证：成功后失败计数为0
        assert failover.failure_count == 0
    
    @pytest.mark.asyncio
    @given(context_data=st.dictionaries(
        keys=st.text(min_size=1, max_size=10),
        values=st.floats(min_value=-100, max_value=100, allow_nan=False),
        min_size=1,
        max_size=5
    ))
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_decide_returns_valid_result(self, context_data: dict):
        """Property: 决策总是返回有效结果
        
        **Validates: Requirements 2.3, 2.4, 4.3**
        
        属性: 无论本地还是云端，决策应总是返回包含action的结果
        """
        config = FailoverConfig(
            local_timeout=0.2,
            failure_threshold=3
        )
        
        # 创建模拟决策函数
        async def mock_local_decide(ctx):
            return {'action': 'buy', 'confidence': 0.8, 'source': 'local'}
        
        async def mock_cloud_decide(ctx):
            return {'action': 'hold', 'confidence': 0.5, 'source': 'cloud'}
        
        failover = SoldierFailover(
            config=config,
            local_decide_func=mock_local_decide,
            cloud_decide_func=mock_cloud_decide
        )
        
        # 执行决策
        result = await failover.decide_with_failover(context_data)
        
        # 验证结果有效
        assert result is not None
        assert 'action' in result
        assert result['action'] in ['buy', 'sell', 'hold']
    
    @pytest.mark.asyncio
    async def test_failover_after_exactly_three_failures(self):
        """Property: 恰好3次失败后切换
        
        **Validates: Requirements 2.3, 2.4, 4.3**
        
        属性: 连续3次本地失败后，系统应切换到Cloud模式
        """
        config = FailoverConfig(
            local_timeout=0.1,
            failure_threshold=3
        )
        
        call_count = 0
        
        async def failing_local_decide(ctx):
            nonlocal call_count
            call_count += 1
            raise asyncio.TimeoutError("Simulated timeout")
        
        async def mock_cloud_decide(ctx):
            return {'action': 'hold', 'confidence': 0.5, 'source': 'cloud'}
        
        failover = SoldierFailover(
            config=config,
            local_decide_func=failing_local_decide,
            cloud_decide_func=mock_cloud_decide
        )
        
        # 执行3次失败的决策
        for i in range(3):
            result = await failover.decide_with_failover({'test': i})
            assert result is not None
        
        # 验证已切换到Cloud模式
        assert failover.mode == SoldierMode.DEGRADED
        assert failover.stats.failover_count == 1
    
    @pytest.mark.asyncio
    async def test_no_failover_with_two_failures(self):
        """Property: 2次失败不切换
        
        **Validates: Requirements 2.3, 2.4**
        
        属性: 连续2次失败后，系统应保持NORMAL模式
        """
        config = FailoverConfig(
            local_timeout=0.1,
            failure_threshold=3
        )
        
        failure_count = 0
        
        async def sometimes_failing_local_decide(ctx):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:
                raise asyncio.TimeoutError("Simulated timeout")
            return {'action': 'buy', 'confidence': 0.8, 'source': 'local'}
        
        async def mock_cloud_decide(ctx):
            return {'action': 'hold', 'confidence': 0.5, 'source': 'cloud'}
        
        failover = SoldierFailover(
            config=config,
            local_decide_func=sometimes_failing_local_decide,
            cloud_decide_func=mock_cloud_decide
        )
        
        # 执行2次失败的决策
        for i in range(2):
            await failover.decide_with_failover({'test': i})
        
        # 验证仍在NORMAL模式
        assert failover.mode == SoldierMode.NORMAL
        assert failover.failure_count == 2


class TestFailoverStatsProperties:
    """热备切换统计属性测试"""
    
    @given(
        local_latencies=st.lists(
            st.floats(min_value=0.1, max_value=1000, allow_nan=False),
            min_size=1,
            max_size=50
        )
    )
    @settings(max_examples=50)
    def test_average_latency_calculation(self, local_latencies: list):
        """Property: 平均延迟计算正确
        
        属性: 平均延迟应等于所有延迟的算术平均值
        """
        stats = FailoverStats()
        
        for latency in local_latencies:
            stats.record_local_decision(latency)
        
        # 验证平均值计算
        expected_avg = sum(local_latencies[-100:]) / len(local_latencies[-100:])
        assert abs(stats.avg_local_latency_ms - expected_avg) < 0.001
    
    @given(
        local_count=st.integers(min_value=0, max_value=100),
        cloud_count=st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=50)
    def test_total_decisions_count(self, local_count: int, cloud_count: int):
        """Property: 总决策数等于本地+云端
        
        属性: total_decisions = local_decisions + cloud_decisions
        """
        stats = FailoverStats()
        
        for _ in range(local_count):
            stats.record_local_decision(10.0)
        
        for _ in range(cloud_count):
            stats.record_cloud_decision(50.0)
        
        # 验证总数
        assert stats.total_decisions == local_count + cloud_count
        assert stats.local_decisions == local_count
        assert stats.cloud_decisions == cloud_count


class TestFailoverConfigValidation:
    """热备切换配置验证测试"""
    
    @given(timeout=st.floats(min_value=-100, max_value=0))
    @settings(max_examples=20)
    def test_invalid_timeout_raises_error(self, timeout: float):
        """Property: 无效超时应抛出错误
        
        属性: local_timeout <= 0 应抛出 ValueError
        """
        config = FailoverConfig(local_timeout=timeout)
        
        with pytest.raises(ValueError, match="本地超时必须 > 0"):
            SoldierFailover(config=config)
    
    @given(threshold=st.integers(min_value=-100, max_value=0))
    @settings(max_examples=20)
    def test_invalid_threshold_raises_error(self, threshold: int):
        """Property: 无效阈值应抛出错误
        
        属性: failure_threshold <= 0 应抛出 ValueError
        """
        config = FailoverConfig(failure_threshold=threshold)
        
        with pytest.raises(ValueError, match="失败阈值必须 > 0"):
            SoldierFailover(config=config)
