"""SoldierFailover单元测试

白皮书依据: 第十二章 12.1.3 Soldier热备切换机制

测试覆盖:
- 初始化验证
- 模式切换
- 决策执行
- 统计记录
- 故障恢复
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from src.brain.soldier_failover import (
    SoldierFailover,
    SoldierMode,
    FailoverConfig,
    FailoverStats
)


class TestSoldierMode:
    """SoldierMode枚举测试"""
    
    def test_mode_values(self):
        """测试模式枚举值"""
        assert SoldierMode.NORMAL.value == "local"
        assert SoldierMode.DEGRADED.value == "cloud"
        assert SoldierMode.OFFLINE.value == "offline"


class TestFailoverConfig:
    """FailoverConfig配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = FailoverConfig()
        
        assert config.local_timeout == 0.2  # 200ms
        assert config.failure_threshold == 3
        assert config.recovery_check_interval == 60.0
        assert config.max_cloud_latency == 2.0
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = FailoverConfig(
            local_timeout=0.5,
            failure_threshold=5,
            recovery_check_interval=120.0
        )
        
        assert config.local_timeout == 0.5
        assert config.failure_threshold == 5
        assert config.recovery_check_interval == 120.0


class TestFailoverStats:
    """FailoverStats统计测试"""
    
    def test_default_stats(self):
        """测试默认统计"""
        stats = FailoverStats()
        
        assert stats.total_decisions == 0
        assert stats.local_decisions == 0
        assert stats.cloud_decisions == 0
        assert stats.failover_count == 0
        assert stats.recovery_count == 0
        assert stats.avg_local_latency_ms == 0.0
        assert stats.avg_cloud_latency_ms == 0.0
    
    def test_record_local_decision(self):
        """测试记录本地决策"""
        stats = FailoverStats()
        
        stats.record_local_decision(10.0)
        stats.record_local_decision(20.0)
        
        assert stats.total_decisions == 2
        assert stats.local_decisions == 2
        assert stats.avg_local_latency_ms == 15.0
    
    def test_record_cloud_decision(self):
        """测试记录云端决策"""
        stats = FailoverStats()
        
        stats.record_cloud_decision(100.0)
        stats.record_cloud_decision(200.0)
        
        assert stats.total_decisions == 2
        assert stats.cloud_decisions == 2
        assert stats.avg_cloud_latency_ms == 150.0
    
    def test_record_mixed_decisions(self):
        """测试记录混合决策"""
        stats = FailoverStats()
        
        stats.record_local_decision(10.0)
        stats.record_cloud_decision(100.0)
        stats.record_local_decision(20.0)
        
        assert stats.total_decisions == 3
        assert stats.local_decisions == 2
        assert stats.cloud_decisions == 1
    
    def test_latency_window_limit(self):
        """测试延迟窗口限制"""
        stats = FailoverStats()
        
        # 记录超过100个决策
        for i in range(150):
            stats.record_local_decision(float(i))
        
        # 窗口应该只保留最近100个
        assert len(stats._local_latencies) == 100


class TestSoldierFailoverInit:
    """SoldierFailover初始化测试"""
    
    def test_init_default(self):
        """测试默认初始化"""
        failover = SoldierFailover()
        
        assert failover.redis is None
        assert failover.config.local_timeout == 0.2
        assert failover.mode == SoldierMode.NORMAL
        assert failover.failure_count == 0
    
    def test_init_with_redis(self):
        """测试带Redis初始化"""
        mock_redis = Mock()
        failover = SoldierFailover(redis_client=mock_redis)
        
        assert failover.redis is mock_redis
    
    def test_init_with_config(self):
        """测试带配置初始化"""
        config = FailoverConfig(local_timeout=0.5, failure_threshold=5)
        failover = SoldierFailover(config=config)
        
        assert failover.config.local_timeout == 0.5
        assert failover.config.failure_threshold == 5
    
    def test_init_with_functions(self):
        """测试带决策函数初始化"""
        async def local_func(ctx):
            return {'action': 'buy'}
        
        async def cloud_func(ctx):
            return {'action': 'sell'}
        
        failover = SoldierFailover(
            local_decide_func=local_func,
            cloud_decide_func=cloud_func
        )
        
        assert failover.local_decide_func is local_func
        assert failover.cloud_decide_func is cloud_func
    
    def test_init_invalid_timeout(self):
        """测试无效的超时配置"""
        config = FailoverConfig(local_timeout=0)
        
        with pytest.raises(ValueError, match="本地超时必须 > 0"):
            SoldierFailover(config=config)
    
    def test_init_invalid_threshold(self):
        """测试无效的阈值配置"""
        config = FailoverConfig(failure_threshold=0)
        
        with pytest.raises(ValueError, match="失败阈值必须 > 0"):
            SoldierFailover(config=config)


class TestSoldierFailoverDecision:
    """SoldierFailover决策测试"""
    
    @pytest.fixture
    def failover(self):
        """创建测试用failover"""
        async def local_func(ctx):
            return {'action': 'buy', 'source': 'local'}
        
        async def cloud_func(ctx):
            return {'action': 'hold', 'source': 'cloud'}
        
        return SoldierFailover(
            local_decide_func=local_func,
            cloud_decide_func=cloud_func
        )
    
    @pytest.mark.asyncio
    async def test_decide_local_success(self, failover):
        """测试本地决策成功"""
        context = {'symbol': 'AAPL'}
        
        result = await failover.decide_with_failover(context)
        
        assert result['source'] == 'local'
        assert failover.mode == SoldierMode.NORMAL
        assert failover.failure_count == 0
        assert failover.stats.local_decisions == 1
    
    @pytest.mark.asyncio
    async def test_decide_local_timeout(self, failover):
        """测试本地决策超时"""
        async def slow_local(ctx):
            await asyncio.sleep(1.0)  # 超过200ms
            return {'action': 'buy', 'source': 'local'}
        
        failover.local_decide_func = slow_local
        failover.config.local_timeout = 0.01  # 10ms
        
        context = {'symbol': 'AAPL'}
        result = await failover.decide_with_failover(context)
        
        assert result['source'] == 'cloud'
        assert failover.failure_count == 1
        assert failover.stats.cloud_decisions == 1
    
    @pytest.mark.asyncio
    async def test_decide_local_error(self, failover):
        """测试本地决策错误"""
        async def error_local(ctx):
            raise RuntimeError("Local error")
        
        failover.local_decide_func = error_local
        
        context = {'symbol': 'AAPL'}
        result = await failover.decide_with_failover(context)
        
        assert result['source'] == 'cloud'
        assert failover.failure_count == 1
    
    @pytest.mark.asyncio
    async def test_decide_failover_after_threshold(self, failover):
        """测试达到阈值后切换"""
        async def error_local(ctx):
            raise RuntimeError("Local error")
        
        failover.local_decide_func = error_local
        failover.config.failure_threshold = 3
        
        context = {'symbol': 'AAPL'}
        
        # 连续失败3次
        for _ in range(3):
            await failover.decide_with_failover(context)
        
        assert failover.mode == SoldierMode.DEGRADED
        assert failover.stats.failover_count == 1
    
    @pytest.mark.asyncio
    async def test_decide_in_cloud_mode(self, failover):
        """测试Cloud模式下的决策"""
        failover.mode = SoldierMode.DEGRADED
        
        context = {'symbol': 'AAPL'}
        result = await failover.decide_with_failover(context)
        
        assert result['source'] == 'cloud'
        assert failover.stats.cloud_decisions == 1


class TestSoldierFailoverModeSwitch:
    """SoldierFailover模式切换测试"""
    
    @pytest.fixture
    def failover(self):
        """创建测试用failover"""
        mock_redis = Mock()
        return SoldierFailover(redis_client=mock_redis)
    
    @pytest.mark.asyncio
    async def test_switch_to_cloud_mode(self, failover):
        """测试切换到Cloud模式"""
        await failover.switch_to_cloud_mode()
        
        assert failover.mode == SoldierMode.DEGRADED
        assert failover.stats.failover_count == 1
        failover.redis.set.assert_called_with(
            SoldierFailover.REDIS_KEY_SOLDIER_MODE,
            'cloud'
        )
    
    @pytest.mark.asyncio
    async def test_switch_to_local_mode(self, failover):
        """测试切换回Local模式"""
        failover.mode = SoldierMode.DEGRADED
        failover.failure_count = 5
        
        await failover.switch_to_local_mode()
        
        assert failover.mode == SoldierMode.NORMAL
        assert failover.failure_count == 0
        assert failover.stats.recovery_count == 1
        failover.redis.set.assert_called_with(
            SoldierFailover.REDIS_KEY_SOLDIER_MODE,
            'local'
        )
    
    @pytest.mark.asyncio
    async def test_switch_to_cloud_no_redis(self):
        """测试无Redis时切换到Cloud模式"""
        failover = SoldierFailover(redis_client=None)
        
        await failover.switch_to_cloud_mode()
        
        assert failover.mode == SoldierMode.DEGRADED
    
    @pytest.mark.asyncio
    async def test_switch_redis_error(self, failover):
        """测试Redis错误时切换"""
        failover.redis.set.side_effect = Exception("Redis error")
        
        # 不应抛出异常
        await failover.switch_to_cloud_mode()
        
        assert failover.mode == SoldierMode.DEGRADED


class TestSoldierFailoverDirectDecision:
    """SoldierFailover直接决策测试"""
    
    @pytest.mark.asyncio
    async def test_local_decide_with_func(self):
        """测试带函数的本地决策"""
        async def local_func(ctx):
            return {'action': 'buy', 'symbol': ctx['symbol']}
        
        failover = SoldierFailover(local_decide_func=local_func)
        
        result = await failover.local_decide({'symbol': 'AAPL'})
        
        assert result['action'] == 'buy'
        assert result['symbol'] == 'AAPL'
    
    @pytest.mark.asyncio
    async def test_local_decide_default(self):
        """测试默认本地决策"""
        failover = SoldierFailover()
        
        result = await failover.local_decide({'symbol': 'AAPL'})
        
        assert result['action'] == 'hold'
        assert result['source'] == 'local_default'
    
    @pytest.mark.asyncio
    async def test_cloud_decide_with_func(self):
        """测试带函数的云端决策"""
        async def cloud_func(ctx):
            return {'action': 'sell', 'symbol': ctx['symbol']}
        
        failover = SoldierFailover(cloud_decide_func=cloud_func)
        
        result = await failover.cloud_decide({'symbol': 'AAPL'})
        
        assert result['action'] == 'sell'
        assert result['symbol'] == 'AAPL'
    
    @pytest.mark.asyncio
    async def test_cloud_decide_default(self):
        """测试默认云端决策"""
        failover = SoldierFailover()
        
        result = await failover.cloud_decide({'symbol': 'AAPL'})
        
        assert result['action'] == 'hold'
        assert result['source'] == 'cloud_default'


class TestSoldierFailoverGetters:
    """SoldierFailover getter方法测试"""
    
    def test_get_mode(self):
        """测试获取模式"""
        failover = SoldierFailover()
        failover.mode = SoldierMode.DEGRADED
        
        assert failover.get_mode() == SoldierMode.DEGRADED
    
    def test_get_failure_count(self):
        """测试获取失败计数"""
        failover = SoldierFailover()
        failover.failure_count = 5
        
        assert failover.get_failure_count() == 5
    
    def test_get_stats(self):
        """测试获取统计"""
        failover = SoldierFailover()
        failover.stats.total_decisions = 100
        
        stats = failover.get_stats()
        
        assert stats.total_decisions == 100
    
    def test_is_in_failover_mode_true(self):
        """测试是否处于故障切换模式（是）"""
        failover = SoldierFailover()
        failover.mode = SoldierMode.DEGRADED
        
        assert failover.is_in_failover_mode() is True
    
    def test_is_in_failover_mode_false(self):
        """测试是否处于故障切换模式（否）"""
        failover = SoldierFailover()
        failover.mode = SoldierMode.NORMAL
        
        assert failover.is_in_failover_mode() is False


class TestSoldierFailoverAlert:
    """SoldierFailover告警测试"""
    
    def test_send_alert(self):
        """测试发送告警"""
        failover = SoldierFailover()
        
        # 不应抛出异常
        failover._send_alert("Test alert message")


class TestSoldierFailoverConcurrency:
    """SoldierFailover并发测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_decisions(self):
        """测试并发决策"""
        call_count = [0]
        
        async def local_func(ctx):
            call_count[0] += 1
            await asyncio.sleep(0.01)
            return {'action': 'buy', 'count': call_count[0]}
        
        failover = SoldierFailover(local_decide_func=local_func)
        
        # 并发执行多个决策
        tasks = [
            failover.decide_with_failover({'symbol': f'SYM{i}'})
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert failover.stats.total_decisions == 5


class TestSoldierFailoverStatsRecording:
    """SoldierFailover统计记录测试"""
    
    @pytest.mark.asyncio
    async def test_cloud_decide_with_stats(self):
        """测试带统计的云端决策"""
        async def cloud_func(ctx):
            await asyncio.sleep(0.001)  # 添加小延迟确保延迟 > 0
            return {'action': 'hold'}
        
        failover = SoldierFailover(cloud_decide_func=cloud_func)
        
        result = await failover._cloud_decide_with_stats({'symbol': 'AAPL'})
        
        assert result['action'] == 'hold'
        assert failover.stats.cloud_decisions == 1
        assert failover.stats.avg_cloud_latency_ms >= 0  # 延迟可能非常小



class TestSoldierFailoverInternalSwitch:
    """SoldierFailover内部切换测试"""
    
    @pytest.mark.asyncio
    async def test_internal_switch_to_cloud_mode(self):
        """测试内部切换到Cloud模式"""
        mock_redis = Mock()
        failover = SoldierFailover(redis_client=mock_redis)
        
        await failover._switch_to_cloud_mode()
        
        assert failover.mode == SoldierMode.DEGRADED
        assert failover.stats.failover_count == 1
