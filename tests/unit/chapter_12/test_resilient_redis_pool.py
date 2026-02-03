"""ResilientRedisPool单元测试

白皮书依据: 第十二章 12.1.1 Redis连接池与重试机制

测试覆盖:
- 配置验证
- 连接状态管理
- 健康检查
- 重试机制
- 全局单例
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock

from src.infra.resilient_redis_pool import (
    ResilientRedisPool,
    RedisPoolConfig,
    RedisPoolStatus,
    redis_retry,
    get_redis_pool,
    reset_redis_pool,
    REDIS_AVAILABLE
)


class TestRedisPoolConfig:
    """RedisPoolConfig配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = RedisPoolConfig()
        
        assert config.host == 'localhost'
        assert config.port == 6379
        assert config.max_connections == 50
        assert config.socket_timeout == 5
        assert config.socket_connect_timeout == 5
        assert config.max_retries == 3
        assert config.health_check_interval == 30
        assert config.db == 0
        assert config.password is None
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = RedisPoolConfig(
            host='redis.example.com',
            port=6380,
            max_connections=100,
            socket_timeout=10,
            max_retries=5,
            password='secret'
        )
        
        assert config.host == 'redis.example.com'
        assert config.port == 6380
        assert config.max_connections == 100
        assert config.socket_timeout == 10
        assert config.max_retries == 5
        assert config.password == 'secret'


class TestRedisPoolStatus:
    """RedisPoolStatus枚举测试"""
    
    def test_status_values(self):
        """测试状态枚举值"""
        assert RedisPoolStatus.CONNECTED.value == "connected"
        assert RedisPoolStatus.DISCONNECTED.value == "disconnected"
        assert RedisPoolStatus.RECONNECTING.value == "reconnecting"
        assert RedisPoolStatus.DEGRADED.value == "degraded"


class TestResilientRedisPoolInit:
    """ResilientRedisPool初始化测试"""
    
    def test_init_default_config(self):
        """测试默认配置初始化"""
        pool = ResilientRedisPool()
        
        assert pool.config.max_connections == 50
        assert pool.status == RedisPoolStatus.DISCONNECTED
        assert pool.pool is None
        assert pool.client is None
        assert pool._failure_count == 0
    
    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        config = RedisPoolConfig(max_connections=100, max_retries=5)
        pool = ResilientRedisPool(config)
        
        assert pool.config.max_connections == 100
        assert pool.config.max_retries == 5
    
    def test_init_invalid_max_connections(self):
        """测试无效的最大连接数"""
        config = RedisPoolConfig(max_connections=0)
        
        with pytest.raises(ValueError, match="最大连接数必须 > 0"):
            ResilientRedisPool(config)
    
    def test_init_invalid_socket_timeout(self):
        """测试无效的套接字超时"""
        config = RedisPoolConfig(socket_timeout=0)
        
        with pytest.raises(ValueError, match="套接字超时必须 > 0"):
            ResilientRedisPool(config)
    
    def test_init_invalid_max_retries(self):
        """测试无效的最大重试次数"""
        config = RedisPoolConfig(max_retries=-1)
        
        with pytest.raises(ValueError, match="最大重试次数必须 >= 0"):
            ResilientRedisPool(config)


class TestResilientRedisPoolConnect:
    """ResilientRedisPool连接测试"""
    
    @pytest.fixture
    def pool(self):
        """创建测试用连接池"""
        return ResilientRedisPool()
    
    def test_connect_redis_not_available(self, pool):
        """测试Redis库不可用时的连接"""
        with patch('src.infra.resilient_redis_pool.REDIS_AVAILABLE', False):
            # 重新创建pool以使用patched值
            pool2 = ResilientRedisPool()
            result = pool2.connect()
            
            assert result is False
            assert pool2.status == RedisPoolStatus.DEGRADED
    
    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
    def test_connect_success(self, pool):
        """测试成功连接"""
        mock_pool = Mock()
        mock_client = Mock()
        mock_client.ping.return_value = True
        
        with patch('src.infra.resilient_redis_pool.redis.ConnectionPool', return_value=mock_pool):
            with patch('src.infra.resilient_redis_pool.redis.Redis', return_value=mock_client):
                result = pool.connect()
                
                assert result is True
                assert pool.status == RedisPoolStatus.CONNECTED
                assert pool._failure_count == 0
    
    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
    def test_connect_failure(self, pool):
        """测试连接失败"""
        import redis
        
        with patch('src.infra.resilient_redis_pool.redis.ConnectionPool') as mock_pool_cls:
            mock_pool_cls.side_effect = redis.ConnectionError("Connection refused")
            
            result = pool.connect()
            
            assert result is False
            assert pool.status == RedisPoolStatus.DISCONNECTED
            assert pool._failure_count == 1


class TestResilientRedisPoolDisconnect:
    """ResilientRedisPool断开连接测试"""
    
    def test_disconnect(self):
        """测试断开连接"""
        pool = ResilientRedisPool()
        pool.pool = Mock()
        pool.client = Mock()
        pool.status = RedisPoolStatus.CONNECTED
        
        pool.disconnect()
        
        assert pool.pool is None
        assert pool.client is None
        assert pool.status == RedisPoolStatus.DISCONNECTED
    
    def test_disconnect_with_error(self):
        """测试断开连接时出错"""
        pool = ResilientRedisPool()
        mock_pool = Mock()
        mock_pool.disconnect.side_effect = Exception("Disconnect error")
        pool.pool = mock_pool
        pool.status = RedisPoolStatus.CONNECTED
        
        # 不应抛出异常
        pool.disconnect()
        
        assert pool.pool is None
        assert pool.status == RedisPoolStatus.DISCONNECTED


class TestResilientRedisPoolGetClient:
    """ResilientRedisPool获取客户端测试"""
    
    def test_get_client_connected(self):
        """测试已连接时获取客户端"""
        pool = ResilientRedisPool()
        mock_client = Mock()
        pool.client = mock_client
        pool.status = RedisPoolStatus.CONNECTED
        
        result = pool.get_client()
        
        assert result is mock_client
    
    def test_get_client_disconnected(self):
        """测试未连接时获取客户端"""
        pool = ResilientRedisPool()
        pool.status = RedisPoolStatus.DISCONNECTED
        
        result = pool.get_client()
        
        assert result is None


class TestResilientRedisPoolHealthCheck:
    """ResilientRedisPool健康检查测试"""
    
    def test_health_check_no_client(self):
        """测试无客户端时的健康检查"""
        pool = ResilientRedisPool()
        pool.client = None
        
        result = pool.health_check()
        
        assert result is False
    
    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
    def test_health_check_success(self):
        """测试健康检查成功"""
        pool = ResilientRedisPool()
        mock_client = Mock()
        mock_client.ping.return_value = True
        pool.client = mock_client
        pool.status = RedisPoolStatus.DEGRADED
        pool._failure_count = 2
        
        with patch('src.infra.resilient_redis_pool.REDIS_AVAILABLE', True):
            result = pool.health_check()
        
        assert result is True
        assert pool.status == RedisPoolStatus.CONNECTED
        assert pool._failure_count == 0
    
    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
    def test_health_check_failure(self):
        """测试健康检查失败"""
        pool = ResilientRedisPool()
        mock_client = Mock()
        mock_client.ping.side_effect = Exception("Ping failed")
        pool.client = mock_client
        pool.status = RedisPoolStatus.CONNECTED
        pool._failure_count = 0
        
        with patch('src.infra.resilient_redis_pool.REDIS_AVAILABLE', True):
            result = pool.health_check()
        
        assert result is False
        assert pool._failure_count == 1
        assert pool.status == RedisPoolStatus.DEGRADED
    
    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
    def test_health_check_max_failures(self):
        """测试达到最大失败次数"""
        config = RedisPoolConfig(max_retries=3)
        pool = ResilientRedisPool(config)
        mock_client = Mock()
        mock_client.ping.side_effect = Exception("Ping failed")
        pool.client = mock_client
        pool._failure_count = 2  # 已经失败2次
        
        with patch('src.infra.resilient_redis_pool.REDIS_AVAILABLE', True):
            result = pool.health_check()
        
        assert result is False
        assert pool._failure_count == 3
        assert pool.status == RedisPoolStatus.DISCONNECTED


class TestResilientRedisPoolHealthCheckThread:
    """ResilientRedisPool健康检查线程测试"""
    
    def test_start_health_check(self):
        """测试启动健康检查线程"""
        pool = ResilientRedisPool()
        
        pool.start_health_check()
        
        assert pool._running is True
        assert pool._health_thread is not None
        assert pool._health_thread.is_alive()
        
        # 清理
        pool.stop_health_check()
    
    def test_start_health_check_already_running(self):
        """测试重复启动健康检查线程"""
        pool = ResilientRedisPool()
        pool.start_health_check()
        
        with pytest.raises(RuntimeError, match="健康检查已在运行"):
            pool.start_health_check()
        
        # 清理
        pool.stop_health_check()
    
    def test_stop_health_check(self):
        """测试停止健康检查线程"""
        pool = ResilientRedisPool()
        pool.start_health_check()
        
        pool.stop_health_check()
        
        assert pool._running is False
    
    def test_stop_health_check_not_running(self):
        """测试停止未运行的健康检查线程"""
        pool = ResilientRedisPool()
        
        # 不应抛出异常
        pool.stop_health_check()
        
        assert pool._running is False


class TestResilientRedisPoolExecuteWithRetry:
    """ResilientRedisPool带重试执行测试"""
    
    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
    def test_execute_with_retry_success(self):
        """测试带重试执行成功"""
        pool = ResilientRedisPool()
        
        def operation():
            return "success"
        
        with patch('src.infra.resilient_redis_pool.REDIS_AVAILABLE', True):
            result = pool.execute_with_retry(operation)
        
        assert result == "success"
    
    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
    def test_execute_with_retry_failure_then_success(self):
        """测试重试后成功"""
        pool = ResilientRedisPool()
        call_count = [0]
        
        # 创建一个模拟的ConnectionError
        class MockConnectionError(Exception):
            pass
        
        def operation():
            call_count[0] += 1
            if call_count[0] < 2:
                raise MockConnectionError("Connection failed")
            return "success"
        
        with patch('src.infra.resilient_redis_pool.REDIS_AVAILABLE', True):
            with patch('src.infra.resilient_redis_pool.redis') as mock_redis:
                mock_redis.ConnectionError = MockConnectionError
                with patch('time.sleep'):  # 跳过等待
                    result = pool.execute_with_retry(operation)
        
        assert result == "success"
        assert call_count[0] == 2
    
    def test_execute_with_retry_redis_not_available(self):
        """测试Redis不可用时执行"""
        pool = ResilientRedisPool()
        
        with patch('src.infra.resilient_redis_pool.REDIS_AVAILABLE', False):
            with pytest.raises(RuntimeError, match="Redis库不可用"):
                pool.execute_with_retry(lambda: None)


class TestRedisRetryDecorator:
    """redis_retry装饰器测试"""
    
    def test_decorator_success(self):
        """测试装饰器成功执行"""
        @redis_retry(max_retries=3)
        def test_func():
            return "success"
        
        result = test_func()
        
        assert result == "success"
    
    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
    def test_decorator_retry_on_connection_error(self):
        """测试装饰器在连接错误时重试"""
        import redis
        
        call_count = [0]
        
        @redis_retry(max_retries=3, backoff_factor=1)
        def test_func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise redis.ConnectionError("Connection failed")
            return "success"
        
        with patch('time.sleep'):  # 跳过等待
            result = test_func()
        
        assert result == "success"
        assert call_count[0] == 2
    
    def test_decorator_non_redis_error(self):
        """测试装饰器对非Redis错误不重试"""
        @redis_retry(max_retries=3)
        def test_func():
            raise ValueError("Not a Redis error")
        
        with pytest.raises(ValueError, match="Not a Redis error"):
            test_func()


class TestGlobalRedisPool:
    """全局Redis连接池测试"""
    
    def setup_method(self):
        """每个测试前重置全局池"""
        reset_redis_pool()
    
    def teardown_method(self):
        """每个测试后重置全局池"""
        reset_redis_pool()
    
    def test_get_redis_pool_singleton(self):
        """测试全局池单例"""
        pool1 = get_redis_pool()
        pool2 = get_redis_pool()
        
        assert pool1 is pool2
    
    def test_get_redis_pool_with_config(self):
        """测试带配置的全局池"""
        config = RedisPoolConfig(max_connections=100)
        pool = get_redis_pool(config)
        
        assert pool.config.max_connections == 100
    
    def test_reset_redis_pool(self):
        """测试重置全局池"""
        pool1 = get_redis_pool()
        reset_redis_pool()
        pool2 = get_redis_pool()
        
        assert pool1 is not pool2


class TestResilientRedisPoolGetters:
    """ResilientRedisPool getter方法测试"""
    
    def test_get_status(self):
        """测试获取状态"""
        pool = ResilientRedisPool()
        pool.status = RedisPoolStatus.CONNECTED
        
        assert pool.get_status() == RedisPoolStatus.CONNECTED
    
    def test_get_failure_count(self):
        """测试获取失败计数"""
        pool = ResilientRedisPool()
        pool._failure_count = 5
        
        assert pool.get_failure_count() == 5


class TestResilientRedisPoolThreadSafety:
    """ResilientRedisPool线程安全测试"""
    
    def test_concurrent_status_updates(self):
        """测试并发状态更新"""
        pool = ResilientRedisPool()
        errors = []
        
        def update_status(status):
            try:
                for _ in range(100):
                    with pool._lock:
                        pool.status = status
                        pool._failure_count += 1
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=update_status, args=(RedisPoolStatus.CONNECTED,)),
            threading.Thread(target=update_status, args=(RedisPoolStatus.DISCONNECTED,)),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert pool._failure_count == 200



class TestResilientRedisPoolHealthCheckLoop:
    """ResilientRedisPool健康检查循环测试"""
    
    def test_health_check_loop_reconnect(self):
        """测试健康检查循环重连"""
        pool = ResilientRedisPool()
        pool._running = True
        
        call_count = [0]
        connect_called = [False]
        
        def mock_health_check():
            call_count[0] += 1
            if call_count[0] >= 2:
                pool._running = False
            return False
        
        def mock_connect():
            connect_called[0] = True
            return True
        
        with patch.object(pool, 'health_check', side_effect=mock_health_check):
            with patch.object(pool, 'connect', side_effect=mock_connect):
                with patch('time.sleep'):
                    pool._health_check_loop()
        
        assert connect_called[0] is True
    
    def test_health_check_loop_exception(self):
        """测试健康检查循环异常处理"""
        pool = ResilientRedisPool()
        pool._running = True
        
        call_count = [0]
        
        def mock_health_check():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Test error")
            pool._running = False
            return True
        
        with patch.object(pool, 'health_check', side_effect=mock_health_check):
            with patch('time.sleep'):
                pool._health_check_loop()
        
        assert call_count[0] == 2


class TestResilientRedisPoolExecuteWithRetryExhausted:
    """ResilientRedisPool重试耗尽测试"""
    
    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
    def test_execute_with_retry_exhausted(self):
        """测试重试次数耗尽"""
        import redis
        
        config = RedisPoolConfig(max_retries=2)
        pool = ResilientRedisPool(config)
        
        def always_fail():
            raise redis.ConnectionError("Always fails")
        
        with patch('time.sleep'):
            with pytest.raises(redis.ConnectionError):
                pool.execute_with_retry(always_fail)


class TestRedisRetryDecoratorExhausted:
    """redis_retry装饰器重试耗尽测试"""
    
    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
    def test_decorator_exhausted(self):
        """测试装饰器重试耗尽"""
        import redis
        
        @redis_retry(max_retries=2, backoff_factor=1)
        def always_fail():
            raise redis.ConnectionError("Always fails")
        
        with patch('time.sleep'):
            with pytest.raises(redis.ConnectionError):
                always_fail()
