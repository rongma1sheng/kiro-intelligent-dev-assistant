"""
Soldier Redis缓存集成单元测试 - Task 20.2

白皮书依据: 第二章 2.1.3 决策流程

测试内容:
- Redis连接和初始化
- 缓存键生成策略
- 缓存读写操作
- TTL过期机制
- 缓存统计信息
- 错误处理
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.brain.soldier_engine_v2 import (
    SoldierEngineV2,
    SoldierConfig,
    SoldierMode
)


@pytest.fixture
def soldier_config():
    """Soldier配置fixture"""
    return SoldierConfig(
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        redis_password=None,
        redis_max_connections=10,
        decision_cache_ttl=5,
        cache_key_prefix="test:soldier:decision:"
    )


@pytest_asyncio.fixture
async def soldier_engine(soldier_config):
    """Soldier引擎fixture（不初始化Redis）"""
    engine = SoldierEngineV2(soldier_config)
    engine.state = "READY"
    
    # Mock LLM推理引擎
    engine.llm_inference = AsyncMock()
    
    yield engine


class TestRedisConnection:
    """Redis连接测试"""
    
    @pytest.mark.asyncio
    async def test_redis_initialization_success(self, soldier_engine):
        """测试Redis初始化成功"""
        # Mock Redis客户端
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        
        # 创建一个async context manager mock
        async def mock_from_url(*args, **kwargs):
            return mock_redis
        
        with patch('redis.asyncio.from_url', side_effect=mock_from_url):
            await soldier_engine._initialize_redis_cache()
            
            # 验证Redis客户端已创建
            assert soldier_engine.redis_client is not None
            assert soldier_engine.cache_enabled is True
            
            # 验证ping被调用
            mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_redis_initialization_failure(self, soldier_engine):
        """测试Redis初始化失败"""
        # Mock Redis连接失败
        with patch('redis.asyncio.from_url', side_effect=ConnectionError("Connection refused")):
            await soldier_engine._initialize_redis_cache()
            
            # 验证缓存被禁用
            assert soldier_engine.redis_client is None
            assert soldier_engine.cache_enabled is False
    
    @pytest.mark.asyncio
    async def test_redis_not_available(self, soldier_config):
        """测试Redis库不可用"""
        # Mock REDIS_AVAILABLE为False
        with patch('src.brain.soldier_engine_v2.REDIS_AVAILABLE', False):
            engine = SoldierEngineV2(soldier_config)
            
            await engine._initialize_redis_cache()
            
            # 验证缓存被禁用
            assert engine.cache_enabled is False
            assert engine.redis_client is None


class TestCacheKeyGeneration:
    """缓存键生成测试"""
    
    def test_generate_cache_key_basic(self, soldier_engine):
        """测试基本缓存键生成"""
        context = {
            'symbol': '000001.SZ',
            'market_data': {
                'price': 10.5,
                'volume': 1000000
            }
        }
        
        cache_key = soldier_engine._generate_cache_key(context)
        
        # 验证键格式
        assert cache_key.startswith(soldier_engine.config.cache_key_prefix)
        assert len(cache_key) > len(soldier_engine.config.cache_key_prefix)
    
    def test_generate_cache_key_consistency(self, soldier_engine):
        """测试相同context生成相同的键"""
        context = {
            'symbol': '000001.SZ',
            'market_data': {
                'price': 10.5,
                'volume': 1000000
            }
        }
        
        key1 = soldier_engine._generate_cache_key(context)
        key2 = soldier_engine._generate_cache_key(context)
        
        # 验证一致性
        assert key1 == key2
    
    def test_generate_cache_key_different_contexts(self, soldier_engine):
        """测试不同context生成不同的键"""
        context1 = {
            'symbol': '000001.SZ',
            'market_data': {'price': 10.5, 'volume': 1000000}
        }
        
        context2 = {
            'symbol': '000002.SZ',
            'market_data': {'price': 10.5, 'volume': 1000000}
        }
        
        key1 = soldier_engine._generate_cache_key(context1)
        key2 = soldier_engine._generate_cache_key(context2)
        
        # 验证不同
        assert key1 != key2
    
    def test_generate_cache_key_missing_fields(self, soldier_engine):
        """测试缺少字段时的键生成"""
        context = {'symbol': '000001.SZ'}  # 缺少market_data
        
        cache_key = soldier_engine._generate_cache_key(context)
        
        # 验证仍能生成键
        assert cache_key.startswith(soldier_engine.config.cache_key_prefix)


class TestCacheReadWrite:
    """缓存读写测试"""
    
    @pytest.mark.asyncio
    async def test_get_cached_decision_hit(self, soldier_engine):
        """测试缓存命中"""
        context = {
            'symbol': '000001.SZ',
            'market_data': {'price': 10.5, 'volume': 1000000}
        }
        
        cached_decision = {
            'decision': {'action': 'buy', 'confidence': 0.8},
            'metadata': {'timestamp': '2026-01-19T10:00:00'}
        }
        
        # Mock Redis客户端
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value='{"decision": {"action": "buy", "confidence": 0.8}, "metadata": {"timestamp": "2026-01-19T10:00:00"}}')
        
        soldier_engine.redis_client = mock_redis
        soldier_engine.cache_enabled = True
        
        # 获取缓存
        result = await soldier_engine._get_cached_decision(context)
        
        # 验证结果
        assert result is not None
        assert result['decision']['action'] == 'buy'
        assert result['decision']['confidence'] == 0.8
        
        # 验证统计
        assert soldier_engine.stats['cache_hits'] == 1
    
    @pytest.mark.asyncio
    async def test_get_cached_decision_miss(self, soldier_engine):
        """测试缓存未命中"""
        context = {
            'symbol': '000001.SZ',
            'market_data': {'price': 10.5, 'volume': 1000000}
        }
        
        # Mock Redis客户端返回None
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        
        soldier_engine.redis_client = mock_redis
        soldier_engine.cache_enabled = True
        
        # 获取缓存
        result = await soldier_engine._get_cached_decision(context)
        
        # 验证结果
        assert result is None
        
        # 验证统计
        assert soldier_engine.stats['cache_misses'] == 1
    
    @pytest.mark.asyncio
    async def test_get_cached_decision_disabled(self, soldier_engine):
        """测试缓存禁用时的行为"""
        context = {
            'symbol': '000001.SZ',
            'market_data': {'price': 10.5, 'volume': 1000000}
        }
        
        soldier_engine.cache_enabled = False
        
        # 获取缓存
        result = await soldier_engine._get_cached_decision(context)
        
        # 验证返回None
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_cached_decision_success(self, soldier_engine):
        """测试缓存写入成功"""
        context = {
            'symbol': '000001.SZ',
            'market_data': {'price': 10.5, 'volume': 1000000}
        }
        
        decision = {
            'decision': {'action': 'buy', 'confidence': 0.8},
            'metadata': {'timestamp': '2026-01-19T10:00:00'}
        }
        
        # Mock Redis客户端
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(return_value=True)
        
        soldier_engine.redis_client = mock_redis
        soldier_engine.cache_enabled = True
        
        # 写入缓存
        result = await soldier_engine._set_cached_decision(context, decision)
        
        # 验证结果
        assert result is True
        
        # 验证setex被调用
        mock_redis.setex.assert_called_once()
        
        # 验证TTL参数
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == soldier_engine.config.decision_cache_ttl
    
    @pytest.mark.asyncio
    async def test_set_cached_decision_error(self, soldier_engine):
        """测试缓存写入错误"""
        context = {
            'symbol': '000001.SZ',
            'market_data': {'price': 10.5, 'volume': 1000000}
        }
        
        decision = {
            'decision': {'action': 'buy', 'confidence': 0.8}
        }
        
        # Mock Redis客户端抛出异常
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(side_effect=Exception("Redis error"))
        
        soldier_engine.redis_client = mock_redis
        soldier_engine.cache_enabled = True
        
        # 写入缓存
        result = await soldier_engine._set_cached_decision(context, decision)
        
        # 验证结果
        assert result is False
        
        # 验证错误统计
        assert soldier_engine.stats['cache_errors'] == 1


class TestCacheTTL:
    """缓存TTL测试"""
    
    @pytest.mark.asyncio
    async def test_cache_ttl_configuration(self, soldier_engine):
        """测试TTL配置"""
        context = {
            'symbol': '000001.SZ',
            'market_data': {'price': 10.5, 'volume': 1000000}
        }
        
        decision = {
            'decision': {'action': 'buy', 'confidence': 0.8}
        }
        
        # Mock Redis客户端
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(return_value=True)
        
        soldier_engine.redis_client = mock_redis
        soldier_engine.cache_enabled = True
        
        # 写入缓存
        await soldier_engine._set_cached_decision(context, decision)
        
        # 验证TTL参数
        call_args = mock_redis.setex.call_args
        cache_key, ttl, data = call_args[0]
        
        assert ttl == 5  # 默认TTL
    
    @pytest.mark.asyncio
    async def test_cache_ttl_custom(self):
        """测试自定义TTL"""
        config = SoldierConfig(decision_cache_ttl=10)
        engine = SoldierEngineV2(config)
        
        context = {
            'symbol': '000001.SZ',
            'market_data': {'price': 10.5, 'volume': 1000000}
        }
        
        decision = {
            'decision': {'action': 'buy', 'confidence': 0.8}
        }
        
        # Mock Redis客户端
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(return_value=True)
        
        engine.redis_client = mock_redis
        engine.cache_enabled = True
        
        # 写入缓存
        await engine._set_cached_decision(context, decision)
        
        # 验证自定义TTL
        call_args = mock_redis.setex.call_args
        cache_key, ttl, data = call_args[0]
        
        assert ttl == 10


class TestCacheStatistics:
    """缓存统计测试"""
    
    @pytest.mark.asyncio
    async def test_get_cache_stats_basic(self, soldier_engine):
        """测试获取基本缓存统计"""
        # 设置统计数据
        soldier_engine.stats['cache_hits'] = 10
        soldier_engine.stats['cache_misses'] = 5
        soldier_engine.stats['cache_errors'] = 1
        soldier_engine.cache_enabled = True
        
        # 获取统计
        stats = await soldier_engine.get_cache_stats()
        
        # 验证统计数据
        assert stats['cache_enabled'] is True
        assert stats['cache_hits'] == 10
        assert stats['cache_misses'] == 5
        assert stats['cache_errors'] == 1
        assert stats['total_requests'] == 15
        assert abs(stats['hit_rate'] - 10/15) < 0.01
        assert stats['ttl_seconds'] == 5
    
    @pytest.mark.asyncio
    async def test_get_cache_stats_with_redis_info(self, soldier_engine):
        """测试获取Redis INFO统计"""
        soldier_engine.stats['cache_hits'] = 10
        soldier_engine.stats['cache_misses'] = 5
        soldier_engine.cache_enabled = True
        
        # Mock Redis客户端
        mock_redis = AsyncMock()
        mock_redis.info = AsyncMock(return_value={
            'total_commands_processed': 1000,
            'keyspace_hits': 800,
            'keyspace_misses': 200
        })
        
        soldier_engine.redis_client = mock_redis
        
        # 获取统计
        stats = await soldier_engine.get_cache_stats()
        
        # 验证Redis统计
        assert 'redis_total_commands' in stats
        assert stats['redis_total_commands'] == 1000
        assert stats['redis_keyspace_hits'] == 800
        assert stats['redis_keyspace_misses'] == 200
    
    @pytest.mark.asyncio
    async def test_get_cache_stats_zero_requests(self, soldier_engine):
        """测试零请求时的统计"""
        soldier_engine.cache_enabled = True
        
        # 获取统计
        stats = await soldier_engine.get_cache_stats()
        
        # 验证命中率为0
        assert stats['total_requests'] == 0
        assert stats['hit_rate'] == 0.0


class TestCacheClear:
    """缓存清空测试"""
    
    @pytest.mark.asyncio
    async def test_clear_cache_success(self, soldier_engine):
        """测试清空缓存成功"""
        # Mock Redis客户端
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(side_effect=[
            (0, ['test:soldier:decision:key1', 'test:soldier:decision:key2'])
        ])
        mock_redis.delete = AsyncMock(return_value=2)
        
        soldier_engine.redis_client = mock_redis
        soldier_engine.cache_enabled = True
        
        # 清空缓存
        result = await soldier_engine.clear_cache()
        
        # 验证结果
        assert result is True
        
        # 验证scan和delete被调用
        mock_redis.scan.assert_called()
        mock_redis.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_clear_cache_disabled(self, soldier_engine):
        """测试缓存禁用时清空"""
        soldier_engine.cache_enabled = False
        
        # 清空缓存
        result = await soldier_engine.clear_cache()
        
        # 验证返回False
        assert result is False
    
    @pytest.mark.asyncio
    async def test_clear_cache_error(self, soldier_engine):
        """测试清空缓存错误"""
        # Mock Redis客户端抛出异常
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(side_effect=Exception("Redis error"))
        
        soldier_engine.redis_client = mock_redis
        soldier_engine.cache_enabled = True
        
        # 清空缓存
        result = await soldier_engine.clear_cache()
        
        # 验证返回False
        assert result is False


class TestDecisionWithCache:
    """决策流程缓存集成测试"""
    
    @pytest.mark.asyncio
    async def test_decide_with_cache_hit(self, soldier_engine):
        """测试决策缓存命中"""
        context = {
            'symbol': '000001.SZ',
            'market_data': {'price': 10.5, 'volume': 1000000}
        }
        
        cached_decision = {
            'decision': {'action': 'buy', 'confidence': 0.8},
            'metadata': {'timestamp': '2026-01-19T10:00:00', 'cached': True}
        }
        
        # Mock缓存命中
        soldier_engine._get_cached_decision = AsyncMock(return_value=cached_decision)
        soldier_engine._set_cached_decision = AsyncMock()
        
        # 执行决策
        result = await soldier_engine.decide(context)
        
        # 验证返回缓存结果
        assert result == cached_decision
        
        # 验证没有调用set_cached_decision
        soldier_engine._set_cached_decision.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_decide_with_cache_miss(self, soldier_engine):
        """测试决策缓存未命中"""
        context = {
            'symbol': '000001.SZ',
            'market_data': {'price': 10.5, 'volume': 1000000}
        }
        
        # Mock缓存未命中
        soldier_engine._get_cached_decision = AsyncMock(return_value=None)
        soldier_engine._set_cached_decision = AsyncMock(return_value=True)
        
        # Mock LLM推理
        mock_result = MagicMock()
        mock_result.latency_ms = 10.0
        soldier_engine.llm_inference.infer = AsyncMock(return_value=mock_result)
        
        # 执行决策
        result = await soldier_engine.decide(context)
        
        # 验证返回新决策
        assert result is not None
        assert 'decision' in result
        
        # 验证调用了set_cached_decision
        soldier_engine._set_cached_decision.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
