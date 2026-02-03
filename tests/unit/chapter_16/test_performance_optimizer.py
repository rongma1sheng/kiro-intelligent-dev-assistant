"""Unit tests for PerformanceOptimizer

白皮书依据: 第十六章 16.0 性能优化指南
测试目标: 100% coverage
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from src.optimization.performance_optimizer import PerformanceOptimizer


class TestPerformanceOptimizerInit:
    """测试PerformanceOptimizer初始化"""
    
    def test_init_default_params(self):
        """测试默认参数初始化"""
        optimizer = PerformanceOptimizer()
        
        assert optimizer.cache_ttl == 5
        assert optimizer.cache_size == 1000
        assert optimizer.redis_client is None
        assert len(optimizer.decision_cache) == 0
        assert optimizer.cache_hits == 0
        assert optimizer.cache_misses == 0
        assert optimizer.total_requests == 0
    
    def test_init_custom_params(self):
        """测试自定义参数初始化"""
        redis_mock = Mock()
        optimizer = PerformanceOptimizer(
            redis_client=redis_mock,
            cache_ttl=10,
            cache_size=500
        )
        
        assert optimizer.cache_ttl == 10
        assert optimizer.cache_size == 500
        assert optimizer.redis_client is redis_mock
    
    def test_init_invalid_cache_ttl(self):
        """测试无效的缓存TTL"""
        with pytest.raises(ValueError, match="缓存有效期必须 > 0"):
            PerformanceOptimizer(cache_ttl=0)
        
        with pytest.raises(ValueError, match="缓存有效期必须 > 0"):
            PerformanceOptimizer(cache_ttl=-1)
    
    def test_init_invalid_cache_size(self):
        """测试无效的缓存大小"""
        with pytest.raises(ValueError, match="缓存大小必须 > 0"):
            PerformanceOptimizer(cache_size=0)
        
        with pytest.raises(ValueError, match="缓存大小必须 > 0"):
            PerformanceOptimizer(cache_size=-1)


class TestOptimizeSoldierLatency:
    """测试Soldier延迟优化"""
    
    def test_optimize_soldier_latency_cache_miss(self):
        """测试缓存未命中"""
        optimizer = PerformanceOptimizer()
        
        context = {'symbol': '000001', 'price': 10.5, 'volume': 1000}
        decision_func = Mock(return_value={'action': 'BUY', 'confidence': 0.8})
        
        result = optimizer.optimize_soldier_latency(context, decision_func)
        
        assert result == {'action': 'BUY', 'confidence': 0.8}
        assert optimizer.cache_misses == 1
        assert optimizer.cache_hits == 0
        assert optimizer.total_requests == 1
        
        # 验证决策函数被调用
        decision_func.assert_called_once()
    
    def test_optimize_soldier_latency_cache_hit(self):
        """测试缓存命中"""
        optimizer = PerformanceOptimizer()
        
        context = {'symbol': '000001', 'price': 10.5, 'volume': 1000}
        decision_func = Mock(return_value={'action': 'BUY', 'confidence': 0.8})
        
        # 第一次调用（缓存未命中）
        result1 = optimizer.optimize_soldier_latency(context, decision_func)
        
        # 第二次调用（缓存命中）
        result2 = optimizer.optimize_soldier_latency(context, decision_func)
        
        assert result1 == result2
        assert optimizer.cache_hits == 1
        assert optimizer.cache_misses == 1
        assert optimizer.total_requests == 2
        
        # 验证决策函数只被调用一次
        assert decision_func.call_count == 1
    
    def test_optimize_soldier_latency_cache_expiry(self):
        """测试缓存过期"""
        optimizer = PerformanceOptimizer(cache_ttl=1)
        
        context = {'symbol': '000001', 'price': 10.5, 'volume': 1000}
        decision_func = Mock(return_value={'action': 'BUY', 'confidence': 0.8})
        
        # 第一次调用
        result1 = optimizer.optimize_soldier_latency(context, decision_func)
        
        # 等待缓存过期
        time.sleep(1.1)
        
        # 第二次调用（缓存已过期）
        result2 = optimizer.optimize_soldier_latency(context, decision_func)
        
        assert result1 == result2
        assert optimizer.cache_hits == 0
        assert optimizer.cache_misses == 2
        
        # 验证决策函数被调用两次
        assert decision_func.call_count == 2
    
    def test_optimize_soldier_latency_empty_context(self):
        """测试空上下文"""
        optimizer = PerformanceOptimizer()
        decision_func = Mock()
        
        with pytest.raises(ValueError, match="决策上下文不能为空"):
            optimizer.optimize_soldier_latency({}, decision_func)
    
    def test_optimize_soldier_latency_different_contexts(self):
        """测试不同上下文"""
        optimizer = PerformanceOptimizer()
        
        context1 = {'symbol': '000001', 'price': 10.5}
        context2 = {'symbol': '000002', 'price': 20.5}
        
        decision_func = Mock(side_effect=[
            {'action': 'BUY', 'confidence': 0.8},
            {'action': 'SELL', 'confidence': 0.7}
        ])
        
        result1 = optimizer.optimize_soldier_latency(context1, decision_func)
        result2 = optimizer.optimize_soldier_latency(context2, decision_func)
        
        assert result1 != result2
        assert optimizer.cache_misses == 2
        assert optimizer.cache_hits == 0


class TestOptimizeRedisThroughput:
    """测试Redis吞吐量优化"""
    
    def test_optimize_redis_throughput_basic(self):
        """测试基本批量操作"""
        redis_mock = Mock()
        pipeline_mock = Mock()
        redis_mock.pipeline.return_value = pipeline_mock
        pipeline_mock.execute.return_value = [b'10.5', True, b'20.5', True]
        
        optimizer = PerformanceOptimizer(redis_client=redis_mock)
        
        operations = [
            {'type': 'get', 'key': 'price:000001'},
            {'type': 'set', 'key': 'price:000001', 'value': '10.5'},
            {'type': 'hget', 'key': 'data:000001', 'field': 'price'},
            {'type': 'hset', 'key': 'data:000001', 'field': 'price', 'value': '20.5'}
        ]
        
        results = optimizer.optimize_redis_throughput(operations)
        
        assert len(results) == 4
        assert results == [b'10.5', True, b'20.5', True]
        
        # 验证Pipeline被使用
        redis_mock.pipeline.assert_called_once()
        pipeline_mock.execute.assert_called_once()
    
    def test_optimize_redis_throughput_no_redis_client(self):
        """测试未初始化Redis客户端"""
        optimizer = PerformanceOptimizer()
        
        operations = [{'type': 'get', 'key': 'test'}]
        
        with pytest.raises(ValueError, match="Redis客户端未初始化"):
            optimizer.optimize_redis_throughput(operations)
    
    def test_optimize_redis_throughput_empty_operations(self):
        """测试空操作列表"""
        redis_mock = Mock()
        optimizer = PerformanceOptimizer(redis_client=redis_mock)
        
        with pytest.raises(ValueError, match="操作列表不能为空"):
            optimizer.optimize_redis_throughput([])
    
    def test_optimize_redis_throughput_unknown_operation(self):
        """测试未知操作类型"""
        redis_mock = Mock()
        pipeline_mock = Mock()
        redis_mock.pipeline.return_value = pipeline_mock
        pipeline_mock.execute.return_value = []
        
        optimizer = PerformanceOptimizer(redis_client=redis_mock)
        
        operations = [
            {'type': 'unknown', 'key': 'test'}
        ]
        
        # 应该记录警告但不抛出异常
        results = optimizer.optimize_redis_throughput(operations)
        
        assert results == []


class TestImplementCaching:
    """测试缓存实现"""
    
    def test_implement_caching_default_ttl(self):
        """测试默认TTL缓存"""
        optimizer = PerformanceOptimizer()
        
        optimizer.implement_caching('test_key', 'test_value')
        
        # 验证缓存已存储
        cached = optimizer._get_from_cache('test_key')
        assert cached == 'test_value'
    
    def test_implement_caching_custom_ttl(self):
        """测试自定义TTL缓存"""
        optimizer = PerformanceOptimizer()
        
        optimizer.implement_caching('test_key', 'test_value', ttl=10)
        
        cached = optimizer._get_from_cache('test_key')
        assert cached == 'test_value'


class TestCacheOperations:
    """测试缓存操作"""
    
    def test_generate_cache_key(self):
        """测试缓存键生成"""
        optimizer = PerformanceOptimizer()
        
        context = {'symbol': '000001', 'price': 10.5}
        key = optimizer._generate_cache_key(context)
        
        assert key == '000001_10.50'
    
    def test_generate_cache_key_missing_fields(self):
        """测试缺少字段的缓存键生成"""
        optimizer = PerformanceOptimizer()
        
        context = {}
        key = optimizer._generate_cache_key(context)
        
        assert key == '_0.00'
    
    def test_get_from_cache_not_exists(self):
        """测试获取不存在的缓存"""
        optimizer = PerformanceOptimizer()
        
        result = optimizer._get_from_cache('nonexistent')
        
        assert result is None
    
    def test_get_from_cache_expired(self):
        """测试获取过期缓存"""
        optimizer = PerformanceOptimizer(cache_ttl=1)
        
        optimizer._put_to_cache('test_key', 'test_value')
        
        # 等待过期
        time.sleep(1.1)
        
        result = optimizer._get_from_cache('test_key')
        
        assert result is None
        assert 'test_key' not in optimizer.decision_cache
    
    def test_put_to_cache_lru_eviction(self):
        """测试LRU缓存淘汰"""
        optimizer = PerformanceOptimizer(cache_size=3)
        
        # 添加4个缓存项
        optimizer._put_to_cache('key1', 'value1')
        optimizer._put_to_cache('key2', 'value2')
        optimizer._put_to_cache('key3', 'value3')
        optimizer._put_to_cache('key4', 'value4')
        
        # 最旧的key1应该被淘汰
        assert len(optimizer.decision_cache) == 3
        assert 'key1' not in optimizer.decision_cache
        assert 'key2' in optimizer.decision_cache
        assert 'key3' in optimizer.decision_cache
        assert 'key4' in optimizer.decision_cache
    
    def test_put_to_cache_move_to_end(self):
        """测试LRU移动到末尾"""
        optimizer = PerformanceOptimizer(cache_size=3)
        
        optimizer._put_to_cache('key1', 'value1')
        optimizer._put_to_cache('key2', 'value2')
        optimizer._put_to_cache('key3', 'value3')
        
        # 访问key1，将其移到末尾
        optimizer._get_from_cache('key1')
        
        # 添加key4，key2应该被淘汰（因为key1被移到末尾）
        optimizer._put_to_cache('key4', 'value4')
        
        assert 'key2' not in optimizer.decision_cache
        assert 'key1' in optimizer.decision_cache


class TestCompressPrompt:
    """测试Prompt压缩"""
    
    def test_compress_prompt_full_context(self):
        """测试完整上下文压缩"""
        optimizer = PerformanceOptimizer()
        
        context = {
            'symbol': '000001',
            'price': 10.5,
            'volume': 1000,
            'signal': 0.8,
            'extra': 'ignored'
        }
        
        compressed = optimizer._compress_prompt(context)
        
        assert compressed == {
            'sym': '000001',
            'p': 10.5,
            'v': 1000,
            's': 0.8
        }
    
    def test_compress_prompt_missing_fields(self):
        """测试缺少字段的压缩"""
        optimizer = PerformanceOptimizer()
        
        context = {'symbol': '000001'}
        
        compressed = optimizer._compress_prompt(context)
        
        assert compressed == {
            'sym': '000001',
            'p': 0.0,
            'v': 0,
            's': 0.0
        }


class TestCacheStats:
    """测试缓存统计"""
    
    def test_get_cache_hit_rate_no_requests(self):
        """测试无请求时的命中率"""
        optimizer = PerformanceOptimizer()
        
        hit_rate = optimizer.get_cache_hit_rate()
        
        assert hit_rate == 0.0
    
    def test_get_cache_hit_rate_with_requests(self):
        """测试有请求时的命中率"""
        optimizer = PerformanceOptimizer()
        
        optimizer.total_requests = 10
        optimizer.cache_hits = 7
        optimizer.cache_misses = 3
        
        hit_rate = optimizer.get_cache_hit_rate()
        
        assert hit_rate == 0.7
    
    def test_get_cache_stats(self):
        """测试获取缓存统计"""
        optimizer = PerformanceOptimizer(cache_size=100)
        
        optimizer.total_requests = 10
        optimizer.cache_hits = 7
        optimizer.cache_misses = 3
        optimizer._put_to_cache('key1', 'value1')
        optimizer._put_to_cache('key2', 'value2')
        
        stats = optimizer.get_cache_stats()
        
        assert stats['total_requests'] == 10
        assert stats['cache_hits'] == 7
        assert stats['cache_misses'] == 3
        assert stats['hit_rate'] == 0.7
        assert stats['cache_size'] == 2
        assert stats['max_cache_size'] == 100
    
    def test_clear_cache(self):
        """测试清空缓存"""
        optimizer = PerformanceOptimizer()
        
        optimizer._put_to_cache('key1', 'value1')
        optimizer._put_to_cache('key2', 'value2')
        
        optimizer.clear_cache()
        
        assert len(optimizer.decision_cache) == 0
    
    def test_reset_stats(self):
        """测试重置统计"""
        optimizer = PerformanceOptimizer()
        
        optimizer.total_requests = 10
        optimizer.cache_hits = 7
        optimizer.cache_misses = 3
        
        optimizer.reset_stats()
        
        assert optimizer.total_requests == 0
        assert optimizer.cache_hits == 0
        assert optimizer.cache_misses == 0
