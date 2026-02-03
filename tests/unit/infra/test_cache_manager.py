"""单元测试 - 缓存管理器

白皮书依据: 第三章 3.2 基础设施与数据治理
需求: requirements.md 9.1-9.7
设计: design.md - CacheManager

测试覆盖:
1. 缓存基本操作（get/set/delete）
2. TTL过期机制
3. 序列化/反序列化
4. 缓存键生成策略
5. 错误处理
6. 统计信息
"""

import pytest
import pickle
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

from src.infra.cache_manager import CacheManager


class TestCacheManagerInitialization:
    """测试缓存管理器初始化"""
    
    def test_init_with_defaults(self):
        """测试默认参数初始化"""
        with patch('src.infra.cache_manager.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            cache = CacheManager()
            
            assert cache.default_ttl == 3600
            assert cache.key_prefix == 'mia:data:'
            assert cache.enabled is True
            mock_redis.assert_called_once()
            mock_client.ping.assert_called_once()
    
    def test_init_with_custom_params(self):
        """测试自定义参数初始化"""
        with patch('src.infra.cache_manager.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            cache = CacheManager(
                redis_host='192.168.1.100',
                redis_port=6380,
                redis_db=1,
                redis_password='secret',
                default_ttl=7200,
                key_prefix='test:'
            )
            
            assert cache.default_ttl == 7200
            assert cache.key_prefix == 'test:'
            assert cache.enabled is True
    
    def test_init_connection_failure(self):
        """测试Redis连接失败"""
        with patch('src.infra.cache_manager.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.side_effect = Exception("Connection refused")
            
            with pytest.raises(ConnectionError, match="Redis连接失败"):
                CacheManager()
    
    def test_init_disabled(self):
        """测试禁用缓存"""
        cache = CacheManager(enabled=False)
        
        assert cache.enabled is False
        assert cache.redis_client is None
    
    def test_init_redis_not_available(self):
        """测试Redis未安装"""
        with patch('src.infra.cache_manager.REDIS_AVAILABLE', False):
            cache = CacheManager()
            
            assert cache.enabled is False
            assert cache.redis_client is None


class TestCacheBasicOperations:
    """测试缓存基本操作"""
    
    @pytest.fixture
    def cache(self):
        """创建缓存管理器实例"""
        with patch('src.infra.cache_manager.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            cache = CacheManager()
            cache.redis_client = mock_client
            
            yield cache
    
    def test_set_and_get_string(self, cache):
        """测试字符串缓存"""
        test_data = "test_value"
        serialized = pickle.dumps(test_data, protocol=pickle.HIGHEST_PROTOCOL)
        
        cache.redis_client.setex = Mock(return_value=True)
        cache.redis_client.get = Mock(return_value=serialized)
        
        # 设置缓存
        result = cache.set("test_key", test_data)
        assert result is True
        cache.redis_client.setex.assert_called_once()
        
        # 获取缓存
        retrieved = cache.get("test_key")
        assert retrieved == test_data
        cache.redis_client.get.assert_called_once()
    
    def test_set_and_get_dict(self, cache):
        """测试字典缓存"""
        test_data = {'symbol': 'AAPL', 'price': 150.5, 'volume': 1000000}
        serialized = pickle.dumps(test_data, protocol=pickle.HIGHEST_PROTOCOL)
        
        cache.redis_client.setex = Mock(return_value=True)
        cache.redis_client.get = Mock(return_value=serialized)
        
        result = cache.set("test_dict", test_data)
        assert result is True
        
        retrieved = cache.get("test_dict")
        assert retrieved == test_data
        assert retrieved['symbol'] == 'AAPL'
    
    def test_set_and_get_dataframe(self, cache):
        """测试DataFrame缓存"""
        test_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=5),
            'close': [100, 101, 102, 103, 104],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        serialized = pickle.dumps(test_data, protocol=pickle.HIGHEST_PROTOCOL)
        
        cache.redis_client.setex = Mock(return_value=True)
        cache.redis_client.get = Mock(return_value=serialized)
        
        result = cache.set("test_df", test_data)
        assert result is True
        
        retrieved = cache.get("test_df")
        assert isinstance(retrieved, pd.DataFrame)
        assert len(retrieved) == 5
        pd.testing.assert_frame_equal(retrieved, test_data)
    
    def test_set_and_get_numpy_array(self, cache):
        """测试NumPy数组缓存"""
        test_data = np.array([1, 2, 3, 4, 5])
        serialized = pickle.dumps(test_data, protocol=pickle.HIGHEST_PROTOCOL)
        
        cache.redis_client.setex = Mock(return_value=True)
        cache.redis_client.get = Mock(return_value=serialized)
        
        result = cache.set("test_array", test_data)
        assert result is True
        
        retrieved = cache.get("test_array")
        assert isinstance(retrieved, np.ndarray)
        np.testing.assert_array_equal(retrieved, test_data)
    
    def test_get_nonexistent_key(self, cache):
        """测试获取不存在的键"""
        cache.redis_client.get = Mock(return_value=None)
        
        result = cache.get("nonexistent_key")
        assert result is None
    
    def test_set_none_value(self, cache):
        """测试设置None值"""
        result = cache.set("test_key", None)
        assert result is False
    
    def test_delete_existing_key(self, cache):
        """测试删除存在的键"""
        cache.redis_client.delete = Mock(return_value=1)
        
        result = cache.delete("test_key")
        assert result is True
        cache.redis_client.delete.assert_called_once()
    
    def test_delete_nonexistent_key(self, cache):
        """测试删除不存在的键"""
        cache.redis_client.delete = Mock(return_value=0)
        
        result = cache.delete("nonexistent_key")
        assert result is False
    
    def test_clear_all(self, cache):
        """测试清空所有缓存"""
        cache.redis_client.flushdb = Mock(return_value=True)
        
        result = cache.clear_all()
        assert result is True
        cache.redis_client.flushdb.assert_called_once()


class TestCacheTTL:
    """测试TTL过期机制"""
    
    @pytest.fixture
    def cache(self):
        """创建缓存管理器实例"""
        with patch('src.infra.cache_manager.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            cache = CacheManager(default_ttl=3600)
            cache.redis_client = mock_client
            
            yield cache
    
    def test_set_with_default_ttl(self, cache):
        """测试使用默认TTL"""
        test_data = "test_value"
        cache.redis_client.setex = Mock(return_value=True)
        
        cache.set("test_key", test_data)
        
        # 验证使用了默认TTL
        call_args = cache.redis_client.setex.call_args
        assert call_args[0][1] == 3600  # default_ttl
    
    def test_set_with_custom_ttl(self, cache):
        """测试使用自定义TTL"""
        test_data = "test_value"
        cache.redis_client.setex = Mock(return_value=True)
        
        cache.set("test_key", test_data, ttl=7200)
        
        # 验证使用了自定义TTL
        call_args = cache.redis_client.setex.call_args
        assert call_args[0][1] == 7200
    
    def test_get_ttl(self, cache):
        """测试获取剩余TTL"""
        cache.redis_client.ttl = Mock(return_value=1800)
        
        ttl = cache.get_ttl("test_key")
        assert ttl == 1800
        cache.redis_client.ttl.assert_called_once()
    
    def test_get_ttl_nonexistent_key(self, cache):
        """测试获取不存在键的TTL"""
        cache.redis_client.ttl = Mock(return_value=-2)
        
        ttl = cache.get_ttl("nonexistent_key")
        assert ttl == -2
    
    def test_exists(self, cache):
        """测试检查键是否存在"""
        cache.redis_client.exists = Mock(return_value=1)
        
        result = cache.exists("test_key")
        assert result is True
        
        cache.redis_client.exists = Mock(return_value=0)
        result = cache.exists("nonexistent_key")
        assert result is False


class TestCacheKeyGeneration:
    """测试缓存键生成策略"""
    
    def test_generate_cache_key_basic(self):
        """测试基础缓存键生成"""
        key = CacheManager.generate_cache_key(
            data_type="market",
            symbol="AAPL"
        )
        
        assert key == "market:AAPL"
    
    def test_generate_cache_key_with_dates(self):
        """测试带日期的缓存键生成"""
        key = CacheManager.generate_cache_key(
            data_type="market",
            symbol="AAPL",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31)
        )
        
        assert key == "market:AAPL:2024-01-01:2024-12-31"
    
    def test_generate_cache_key_with_params(self):
        """测试带额外参数的缓存键生成"""
        key = CacheManager.generate_cache_key(
            data_type="market",
            symbol="AAPL",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            frequency="1d",
            adjust="qfq"
        )
        
        # 应该包含参数哈希
        parts = key.split(':')
        assert len(parts) == 5
        assert parts[0] == "market"
        assert parts[1] == "AAPL"
        assert parts[2] == "2024-01-01"
        assert parts[3] == "2024-12-31"
        assert len(parts[4]) == 8  # 哈希长度
    
    def test_generate_cache_key_consistency(self):
        """测试缓存键生成的一致性"""
        # 相同参数应生成相同的键
        key1 = CacheManager.generate_cache_key(
            data_type="market",
            symbol="AAPL",
            frequency="1d",
            adjust="qfq"
        )
        
        key2 = CacheManager.generate_cache_key(
            data_type="market",
            symbol="AAPL",
            frequency="1d",
            adjust="qfq"
        )
        
        assert key1 == key2
    
    def test_generate_cache_key_param_order_independence(self):
        """测试参数顺序不影响键生成"""
        # 参数顺序不同，但应生成相同的键（因为内部会排序）
        key1 = CacheManager.generate_cache_key(
            data_type="market",
            symbol="AAPL",
            frequency="1d",
            adjust="qfq"
        )
        
        key2 = CacheManager.generate_cache_key(
            data_type="market",
            symbol="AAPL",
            adjust="qfq",
            frequency="1d"
        )
        
        assert key1 == key2
    
    def test_make_key_with_prefix(self):
        """测试添加前缀"""
        with patch('src.infra.cache_manager.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            cache = CacheManager(key_prefix='test:')
            full_key = cache._make_key("my_key")
            
            assert full_key == "test:my_key"


class TestCacheErrorHandling:
    """测试错误处理"""
    
    @pytest.fixture
    def cache(self):
        """创建缓存管理器实例"""
        with patch('src.infra.cache_manager.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            cache = CacheManager()
            cache.redis_client = mock_client
            
            yield cache
    
    def test_get_with_redis_error(self, cache):
        """测试获取缓存时Redis错误"""
        import redis as redis_module
        cache.redis_client.get = Mock(side_effect=redis_module.RedisError("Connection lost"))
        
        result = cache.get("test_key")
        assert result is None
    
    def test_set_with_redis_error(self, cache):
        """测试设置缓存时Redis错误"""
        import redis as redis_module
        cache.redis_client.setex = Mock(side_effect=redis_module.RedisError("Connection lost"))
        
        result = cache.set("test_key", "test_value")
        assert result is False
    
    def test_delete_with_redis_error(self, cache):
        """测试删除缓存时Redis错误"""
        import redis as redis_module
        cache.redis_client.delete = Mock(side_effect=redis_module.RedisError("Connection lost"))
        
        result = cache.delete("test_key")
        assert result is False
    
    def test_get_with_unpickling_error(self, cache):
        """测试反序列化错误"""
        cache.redis_client.get = Mock(return_value=b"invalid_pickle_data")
        cache.redis_client.delete = Mock(return_value=1)
        
        result = cache.get("test_key")
        assert result is None
        # 应该删除损坏的缓存
        cache.redis_client.delete.assert_called_once()
    
    def test_set_with_unpicklable_object(self, cache):
        """测试不可序列化对象"""
        # Lambda函数不可序列化
        unpicklable = lambda x: x + 1
        
        with pytest.raises(ValueError, match="数据不可序列化"):
            cache.set("test_key", unpicklable)
    
    def test_operations_when_disabled(self):
        """测试缓存禁用时的操作"""
        cache = CacheManager(enabled=False)
        
        assert cache.get("test_key") is None
        assert cache.set("test_key", "value") is False
        assert cache.delete("test_key") is False
        assert cache.clear_all() is False
        assert cache.exists("test_key") is False
        assert cache.get_ttl("test_key") is None


class TestCacheStats:
    """测试缓存统计"""
    
    @pytest.fixture
    def cache(self):
        """创建缓存管理器实例"""
        with patch('src.infra.cache_manager.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            cache = CacheManager()
            cache.redis_client = mock_client
            
            yield cache
    
    def test_get_stats(self, cache):
        """测试获取统计信息"""
        cache.redis_client.info = Mock(return_value={
            'used_memory': 1024000,
            'used_memory_human': '1.00M',
            'connected_clients': 5,
            'total_commands_processed': 1000,
            'keyspace_hits': 800,
            'keyspace_misses': 200
        })
        
        cache.redis_client.scan_iter = Mock(return_value=iter(['key1', 'key2', 'key3']))
        
        stats = cache.get_stats()
        
        assert stats['enabled'] is True
        assert stats['keys_count'] == 3
        assert stats['used_memory'] == 1024000
        assert stats['used_memory_human'] == '1.00M'
        assert stats['connected_clients'] == 5
        assert stats['keyspace_hits'] == 800
        assert stats['keyspace_misses'] == 200
        assert stats['hit_rate'] == 0.8  # 800 / (800 + 200)
    
    def test_get_stats_when_disabled(self):
        """测试禁用时获取统计"""
        cache = CacheManager(enabled=False)
        
        stats = cache.get_stats()
        
        assert stats['enabled'] is False
        assert stats['keys_count'] == 0
        assert stats['used_memory'] == 0
    
    def test_calculate_hit_rate(self):
        """测试命中率计算"""
        assert CacheManager._calculate_hit_rate(80, 20) == 0.8
        assert CacheManager._calculate_hit_rate(100, 0) == 1.0
        assert CacheManager._calculate_hit_rate(0, 100) == 0.0
        assert CacheManager._calculate_hit_rate(0, 0) == 0.0


class TestCacheContextManager:
    """测试上下文管理器"""
    
    def test_context_manager(self):
        """测试上下文管理器用法"""
        with patch('src.infra.cache_manager.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.close = Mock()
            
            with CacheManager() as cache:
                assert cache.enabled is True
            
            # 应该自动关闭连接
            mock_client.close.assert_called_once()
    
    def test_close(self):
        """测试手动关闭连接"""
        with patch('src.infra.cache_manager.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.close = Mock()
            
            cache = CacheManager()
            cache.close()
            
            mock_client.close.assert_called_once()


class TestCacheIntegration:
    """集成测试（需要真实Redis）"""
    
    @pytest.mark.integration
    def test_real_redis_operations(self):
        """测试真实Redis操作
        
        注意：此测试需要本地运行Redis服务
        """
        try:
            cache = CacheManager()
            
            # 测试字符串
            cache.set("test:string", "hello", ttl=60)
            assert cache.get("test:string") == "hello"
            
            # 测试字典
            test_dict = {'a': 1, 'b': 2}
            cache.set("test:dict", test_dict, ttl=60)
            assert cache.get("test:dict") == test_dict
            
            # 测试DataFrame
            df = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6]})
            cache.set("test:df", df, ttl=60)
            retrieved_df = cache.get("test:df")
            pd.testing.assert_frame_equal(retrieved_df, df)
            
            # 测试删除
            cache.delete("test:string")
            assert cache.get("test:string") is None
            
            # 清理
            cache.delete("test:dict")
            cache.delete("test:df")
            cache.close()
            
        except ConnectionError:
            pytest.skip("Redis未运行，跳过集成测试")


class TestCacheEdgeCases:
    """测试边界情况"""
    
    @pytest.fixture
    def cache(self):
        """创建缓存管理器实例"""
        with patch('src.infra.cache_manager.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            cache = CacheManager()
            cache.redis_client = mock_client
            
            yield cache
    
    def test_get_with_general_exception(self, cache):
        """测试获取缓存时的一般异常"""
        cache.redis_client.get = Mock(side_effect=RuntimeError("Unexpected error"))
        
        result = cache.get("test_key")
        assert result is None
    
    def test_set_with_general_exception_after_serialization(self, cache):
        """测试序列化后设置缓存时的一般异常"""
        cache.redis_client.setex = Mock(side_effect=RuntimeError("Unexpected error"))
        
        result = cache.set("test_key", "test_value")
        assert result is False
    
    def test_delete_with_general_exception(self, cache):
        """测试删除缓存时的一般异常"""
        cache.redis_client.delete = Mock(side_effect=RuntimeError("Unexpected error"))
        
        result = cache.delete("test_key")
        assert result is False
    
    def test_clear_all_with_exception(self, cache):
        """测试清空缓存时的异常"""
        import redis as redis_module
        cache.redis_client.flushdb = Mock(side_effect=redis_module.RedisError("Flush failed"))
        
        result = cache.clear_all()
        assert result is False
    
    def test_exists_with_exception(self, cache):
        """测试检查存在性时的异常"""
        import redis as redis_module
        cache.redis_client.exists = Mock(side_effect=redis_module.RedisError("Check failed"))
        
        result = cache.exists("test_key")
        assert result is False
    
    def test_get_ttl_with_exception(self, cache):
        """测试获取TTL时的异常"""
        import redis as redis_module
        cache.redis_client.ttl = Mock(side_effect=redis_module.RedisError("TTL check failed"))
        
        result = cache.get_ttl("test_key")
        assert result is None
    
    def test_get_stats_with_exception(self, cache):
        """测试获取统计信息时的异常"""
        import redis as redis_module
        cache.redis_client.info = Mock(side_effect=redis_module.RedisError("Info failed"))
        
        stats = cache.get_stats()
        assert 'error' in stats
        assert stats['enabled'] is True
    
    def test_close_with_exception(self):
        """测试关闭连接时的异常"""
        with patch('src.infra.cache_manager.redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.close = Mock(side_effect=RuntimeError("Close failed"))
            
            cache = CacheManager()
            # 不应该抛出异常
            cache.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
