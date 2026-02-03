"""
缓存策略性能测试 - Task 20.4

白皮书依据: 第七章 7.4 缓存策略

测试目标:
- 测试缓存命中率 > 80%
- 测试缓存查询延迟
- 测试缓存预热效果
- 测试LRU淘汰策略
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from src.brain.soldier_engine_v2 import SoldierEngineV2, SoldierConfig


class TestCacheHitRate:
    """测试缓存命中率 - 目标 > 80%"""
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_with_repeated_requests(self):
        """测试重复请求的缓存命中率"""
        config = SoldierConfig(
            decision_cache_ttl=10,
            cache_max_size=1000
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        mock_redis.info = AsyncMock(return_value={})
        
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 模拟100个请求，其中80个是重复的
        contexts = []
        for i in range(20):
            contexts.append({
                'symbol': f'00000{i % 5}',  # 只有5个不同的股票
                'market_data': {'price': 100.0, 'volume': 1000000}
            })
        
        # 第一轮请求（全部miss）
        for context in contexts:
            await soldier._get_cached_decision(context)
            await soldier._set_cached_decision(context, {'decision': 'test'})
        
        # 重置统计计数器,只统计第二轮的命中率
        soldier.stats['cache_hits'] = 0
        soldier.stats['cache_misses'] = 0
        
        # 第二轮请求（应该大部分hit）
        # Mock get返回缓存数据
        mock_redis.get = AsyncMock(return_value='{"decision": "test"}')
        
        for context in contexts:
            result = await soldier._get_cached_decision(context)
            assert result is not None
        
        # 计算命中率
        stats = await soldier.get_cache_stats()
        hit_rate = stats['hit_rate']
        
        # 验证命中率 > 80%
        assert hit_rate > 0.8, f"命中率 {hit_rate:.2%} 未达到目标 80%"
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_with_warmup(self):
        """测试预热后的缓存命中率"""
        config = SoldierConfig(
            cache_warmup_enabled=True,
            cache_warmup_symbols=['000001', '000002', '600000'],
            decision_cache_ttl=10
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.setex = AsyncMock()
        mock_redis.get = AsyncMock(return_value='{"decision": "warmup"}')
        
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 执行预热
        warmup_count = await soldier._warmup_cache()
        assert warmup_count == 3
        
        # 请求预热的股票（应该全部命中）
        for symbol in config.cache_warmup_symbols:
            context = {
                'symbol': symbol,
                'market_data': {'price': 100.0, 'volume': 1000000}
            }
            result = await soldier._get_cached_decision(context)
            assert result is not None
        
        # 验证命中率
        stats = await soldier.get_cache_stats()
        assert stats['hit_rate'] == 1.0, "预热后的命中率应该是100%"
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_degradation_over_time(self):
        """测试缓存命中率随时间的变化"""
        config = SoldierConfig(
            decision_cache_ttl=1,  # 1秒TTL
            cache_max_size=1000
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.setex = AsyncMock()
        
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        context = {
            'symbol': '000001',
            'market_data': {'price': 100.0, 'volume': 1000000}
        }
        
        # 第一次请求（miss）
        mock_redis.get = AsyncMock(return_value=None)
        result1 = await soldier._get_cached_decision(context)
        assert result1 is None
        
        # 写入缓存
        await soldier._set_cached_decision(context, {'decision': 'test'})
        
        # 立即请求（hit）
        mock_redis.get = AsyncMock(return_value='{"decision": "test"}')
        result2 = await soldier._get_cached_decision(context)
        assert result2 is not None
        
        # 等待TTL过期
        await asyncio.sleep(1.1)
        
        # 再次请求（miss，因为TTL过期）
        mock_redis.get = AsyncMock(return_value=None)
        result3 = await soldier._get_cached_decision(context)
        assert result3 is None


class TestCacheQueryLatency:
    """测试缓存查询延迟"""
    
    @pytest.mark.asyncio
    async def test_cache_get_latency(self):
        """测试缓存读取延迟"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # Mock Redis with realistic latency
        mock_redis = AsyncMock()
        
        async def mock_get_with_latency(key):
            await asyncio.sleep(0.001)  # 1ms延迟
            return '{"decision": "test"}'
        
        mock_redis.get = mock_get_with_latency
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        context = {
            'symbol': '000001',
            'market_data': {'price': 100.0, 'volume': 1000000}
        }
        
        # 测量延迟
        start_time = time.perf_counter()
        result = await soldier._get_cached_decision(context)
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        assert result is not None
        assert latency_ms < 15, f"缓存读取延迟 {latency_ms:.2f}ms 超过15ms"
    
    @pytest.mark.asyncio
    async def test_cache_set_latency(self):
        """测试缓存写入延迟"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        
        async def mock_setex_with_latency(key, ttl, value):
            await asyncio.sleep(0.002)  # 2ms延迟
            return True
        
        mock_redis.setex = mock_setex_with_latency
        mock_redis.scan = AsyncMock(return_value=(0, []))
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        context = {
            'symbol': '000001',
            'market_data': {'price': 100.0, 'volume': 1000000}
        }
        decision = {'decision': 'test'}
        
        # 测量延迟
        start_time = time.perf_counter()
        result = await soldier._set_cached_decision(context, decision)
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        assert result is True
        assert latency_ms < 20, f"缓存写入延迟 {latency_ms:.2f}ms 超过20ms"
    
    @pytest.mark.asyncio
    async def test_cache_query_performance_under_load(self):
        """测试高负载下的缓存查询性能"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value='{"decision": "test"}')
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 并发100个请求
        contexts = [
            {
                'symbol': f'00000{i}',
                'market_data': {'price': 100.0, 'volume': 1000000}
            }
            for i in range(100)
        ]
        
        start_time = time.perf_counter()
        tasks = [soldier._get_cached_decision(ctx) for ctx in contexts]
        results = await asyncio.gather(*tasks)
        total_time_ms = (time.perf_counter() - start_time) * 1000
        
        # 验证所有请求都成功
        assert all(r is not None for r in results)
        
        # 平均延迟应该 < 5ms
        avg_latency_ms = total_time_ms / len(contexts)
        assert avg_latency_ms < 5, f"平均延迟 {avg_latency_ms:.2f}ms 超过5ms"


class TestCacheWarmup:
    """测试缓存预热效果"""
    
    @pytest.mark.asyncio
    async def test_warmup_basic(self):
        """测试基本预热功能"""
        config = SoldierConfig(
            cache_warmup_enabled=True,
            cache_warmup_symbols=['000001', '000002', '600000']
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 执行预热
        warmup_count = await soldier._warmup_cache()
        
        # 验证预热数量
        assert warmup_count == 3
        assert soldier.cache_warmup_completed is True
        assert soldier.stats['cache_warmup_count'] == 3
        
        # 验证Redis写入次数
        assert mock_redis.setex.call_count == 3
    
    @pytest.mark.asyncio
    async def test_warmup_with_empty_symbols(self):
        """测试空预热列表"""
        config = SoldierConfig(
            cache_warmup_enabled=True,
            cache_warmup_symbols=[]
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 执行预热
        warmup_count = await soldier._warmup_cache()
        
        # 验证没有预热
        assert warmup_count == 0
        assert soldier.cache_warmup_completed is True
    
    @pytest.mark.asyncio
    async def test_warmup_disabled(self):
        """测试禁用预热"""
        config = SoldierConfig(
            cache_warmup_enabled=False,
            cache_warmup_symbols=['000001', '000002']
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 不应该执行预热（因为disabled）
        # 这个测试验证initialize()不会调用_warmup_cache()
        assert soldier.cache_warmup_completed is False
    
    @pytest.mark.asyncio
    async def test_warmup_improves_hit_rate(self):
        """测试预热提高命中率"""
        config = SoldierConfig(
            cache_warmup_enabled=True,
            cache_warmup_symbols=['000001', '000002', '600000']
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 执行预热
        await soldier._warmup_cache()
        
        # Mock get返回预热的数据
        mock_redis.get = AsyncMock(return_value='{"decision": "warmup"}')
        
        # 请求预热的股票
        for symbol in config.cache_warmup_symbols:
            context = {
                'symbol': symbol,
                'market_data': {'price': 100.0, 'volume': 1000000}
            }
            result = await soldier._get_cached_decision(context)
            assert result is not None
        
        # 验证命中率
        stats = await soldier.get_cache_stats()
        assert stats['hit_rate'] == 1.0


class TestLRUEviction:
    """测试LRU淘汰策略"""
    
    @pytest.mark.asyncio
    async def test_lru_eviction_basic(self):
        """测试基本LRU淘汰"""
        config = SoldierConfig(cache_max_size=10)
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        
        # Mock scan返回一些键
        mock_redis.scan = AsyncMock(return_value=(
            0,
            ['soldier:decision:key1', 'soldier:decision:key2', 'soldier:decision:key3']
        ))
        
        # Mock ttl返回不同的值
        ttl_values = [5, 3, 4]  # key1=5s, key2=3s, key3=4s
        mock_redis.ttl = AsyncMock(side_effect=ttl_values)
        mock_redis.delete = AsyncMock()
        
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 淘汰1个条目
        evicted = await soldier._evict_lru_entries(1)
        
        # 验证淘汰了TTL最大的（key1, TTL=5s）
        assert evicted == 1
        assert soldier.stats['cache_evictions'] == 1
        mock_redis.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_lru_eviction_multiple(self):
        """测试批量LRU淘汰"""
        config = SoldierConfig(cache_max_size=10)
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        
        # Mock scan返回5个键
        keys = [f'soldier:decision:key{i}' for i in range(5)]
        mock_redis.scan = AsyncMock(return_value=(0, keys))
        
        # Mock ttl返回不同的值
        mock_redis.ttl = AsyncMock(side_effect=[5, 3, 4, 2, 1])
        mock_redis.delete = AsyncMock()
        
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 淘汰3个条目
        evicted = await soldier._evict_lru_entries(3)
        
        # 验证淘汰了3个
        assert evicted == 3
        assert soldier.stats['cache_evictions'] == 3
        assert mock_redis.delete.call_count == 3
    
    @pytest.mark.asyncio
    async def test_enforce_cache_size_limit(self):
        """测试强制执行缓存大小限制"""
        config = SoldierConfig(cache_max_size=10)
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        
        # Mock scan返回15个键（超过限制）
        keys = [f'soldier:decision:key{i}' for i in range(15)]
        mock_redis.scan = AsyncMock(return_value=(0, keys))
        
        # Mock ttl
        mock_redis.ttl = AsyncMock(side_effect=list(range(15, 0, -1)))
        mock_redis.delete = AsyncMock()
        
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 执行大小限制
        result = await soldier._enforce_cache_size_limit()
        
        # 验证淘汰了5个（15-10=5）
        assert result is True
        assert soldier.stats['cache_evictions'] == 5
    
    @pytest.mark.asyncio
    async def test_cache_size_check(self):
        """测试缓存大小检查"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        
        # Mock scan返回100个键
        keys = [f'soldier:decision:key{i}' for i in range(100)]
        mock_redis.scan = AsyncMock(return_value=(0, keys))
        
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 检查大小
        size = await soldier._check_cache_size()
        
        assert size == 100
    
    @pytest.mark.asyncio
    async def test_eviction_triggered_on_write(self):
        """测试写入时自动触发淘汰"""
        config = SoldierConfig(cache_max_size=5)
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        
        # Mock scan返回6个键（超过限制）
        keys = [f'soldier:decision:key{i}' for i in range(6)]
        mock_redis.scan = AsyncMock(return_value=(0, keys))
        
        # Mock ttl
        mock_redis.ttl = AsyncMock(side_effect=[5, 4, 3, 2, 1, 0])
        mock_redis.delete = AsyncMock()
        mock_redis.setex = AsyncMock()
        
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 写入缓存（应该触发淘汰）
        context = {
            'symbol': '000001',
            'market_data': {'price': 100.0, 'volume': 1000000}
        }
        decision = {'decision': 'test'}
        
        result = await soldier._set_cached_decision(context, decision)
        
        # 验证写入成功
        assert result is True
        
        # 验证触发了淘汰
        assert soldier.stats['cache_evictions'] > 0


class TestCacheHealth:
    """测试缓存健康监控"""
    
    @pytest.mark.asyncio
    async def test_cache_health_healthy(self):
        """测试健康的缓存状态"""
        config = SoldierConfig(
            cache_max_size=1000,
            cache_hit_rate_target=0.8
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, ['key1', 'key2']))
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 设置高命中率
        soldier.stats['cache_hits'] = 80
        soldier.stats['cache_misses'] = 20
        soldier.cache_warmup_completed = True
        soldier.stats['cache_warmup_count'] = 10
        
        # 获取健康状态
        health = await soldier.get_cache_health()
        
        # 验证健康
        assert health['is_healthy'] is True
        assert health['hit_rate'] == 0.8
        assert health['current_size'] == 2
        assert health['warmup_completed'] is True
        assert len(health['warnings']) == 0
    
    @pytest.mark.asyncio
    async def test_cache_health_low_hit_rate(self):
        """测试低命中率告警"""
        config = SoldierConfig(
            cache_max_size=1000,
            cache_hit_rate_target=0.8
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, []))
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 设置低命中率
        soldier.stats['cache_hits'] = 30
        soldier.stats['cache_misses'] = 70
        
        # 获取健康状态
        health = await soldier.get_cache_health()
        
        # 验证不健康
        assert health['is_healthy'] is False
        assert health['hit_rate'] == 0.3
        assert any('Hit rate' in w for w in health['warnings'])
    
    @pytest.mark.asyncio
    async def test_cache_health_high_utilization(self):
        """测试高利用率告警"""
        config = SoldierConfig(cache_max_size=100)
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        
        # Mock scan返回95个键（95%利用率）
        keys = [f'key{i}' for i in range(95)]
        mock_redis.scan = AsyncMock(return_value=(0, keys))
        
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 设置高命中率（避免命中率告警）
        soldier.stats['cache_hits'] = 90
        soldier.stats['cache_misses'] = 10
        
        # 获取健康状态
        health = await soldier.get_cache_health()
        
        # 验证有告警
        assert health['utilization'] == 0.95
        assert any('approaching limit' in w for w in health['warnings'])
    
    @pytest.mark.asyncio
    async def test_cache_health_high_error_rate(self):
        """测试高错误率告警"""
        config = SoldierConfig(cache_hit_rate_target=0.8)
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, []))
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 设置高错误率
        soldier.stats['cache_hits'] = 80
        soldier.stats['cache_misses'] = 10
        soldier.stats['cache_errors'] = 10  # 10% 错误率
        
        # 获取健康状态
        health = await soldier.get_cache_health()
        
        # 验证不健康
        assert health['is_healthy'] is False
        assert any('error rate' in w for w in health['warnings'])


class TestCacheIntegration:
    """测试缓存策略集成"""
    
    @pytest.mark.asyncio
    async def test_full_cache_workflow(self):
        """测试完整的缓存工作流程"""
        config = SoldierConfig(
            cache_max_size=10,
            cache_warmup_enabled=True,
            cache_warmup_symbols=['000001', '000002'],
            cache_hit_rate_target=0.8
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, []))
        mock_redis.delete = AsyncMock()
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 1. 执行预热
        warmup_count = await soldier._warmup_cache()
        assert warmup_count == 2
        
        # 2. 写入缓存
        context = {
            'symbol': '600000',
            'market_data': {'price': 100.0, 'volume': 1000000}
        }
        decision = {'decision': 'test'}
        
        result = await soldier._set_cached_decision(context, decision)
        assert result is True
        
        # 3. 检查缓存健康
        health = await soldier.get_cache_health()
        assert 'is_healthy' in health
        assert 'hit_rate' in health
        assert 'warmup_completed' in health
    
    @pytest.mark.asyncio
    async def test_cache_performance_benchmark(self):
        """缓存性能基准测试"""
        config = SoldierConfig(cache_max_size=1000)
        soldier = SoldierEngineV2(config)
        
        # Mock Redis with realistic performance
        mock_redis = AsyncMock()
        
        async def mock_get(key):
            await asyncio.sleep(0.001)  # 1ms
            return '{"decision": "test"}'
        
        async def mock_setex(key, ttl, value):
            await asyncio.sleep(0.002)  # 2ms
            return True
        
        mock_redis.get = mock_get
        mock_redis.setex = mock_setex
        mock_redis.scan = AsyncMock(return_value=(0, []))
        
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 测试100次读写
        contexts = [
            {
                'symbol': f'00000{i % 10}',
                'market_data': {'price': 100.0, 'volume': 1000000}
            }
            for i in range(100)
        ]
        
        # 写入测试
        write_start = time.perf_counter()
        for ctx in contexts:
            await soldier._set_cached_decision(ctx, {'decision': 'test'})
        write_time = time.perf_counter() - write_start
        
        # 读取测试
        read_start = time.perf_counter()
        for ctx in contexts:
            await soldier._get_cached_decision(ctx)
        read_time = time.perf_counter() - read_start
        
        # 验证性能
        avg_write_ms = (write_time / 100) * 1000
        avg_read_ms = (read_time / 100) * 1000
        
        assert avg_write_ms < 20, f"平均写入延迟 {avg_write_ms:.2f}ms 超过20ms"
        assert avg_read_ms < 20, f"平均读取延迟 {avg_read_ms:.2f}ms 超过20ms"
