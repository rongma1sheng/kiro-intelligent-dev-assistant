"""弹性Redis连接池 - Resilient Redis Pool

白皮书依据: 第十二章 12.1.1 Redis连接池与重试机制

问题: Redis单点故障导致系统瘫痪
风险等级: 🔴 高

功能:
1. 连接池管理（最大50连接）
2. 指数退避重试机制
3. 健康检查（30秒间隔）
4. 自动重连装饰器

性能要求:
- 连接超时: 5秒
- 健康检查间隔: 30秒
- 最大重试次数: 3次
"""

import functools
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, cast

from loguru import logger

try:
    import redis
    from redis.backoff import ExponentialBackoff
    from redis.retry import Retry

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis库未安装，ResilientRedisPool将使用模拟模式")


class RedisPoolStatus(Enum):
    """Redis连接池状态枚举

    白皮书依据: 第十二章 12.1.1 Redis连接池与重试机制
    """

    CONNECTED = "connected"  # 已连接
    DISCONNECTED = "disconnected"  # 已断开
    RECONNECTING = "reconnecting"  # 重连中
    DEGRADED = "degraded"  # 降级模式


@dataclass
class RedisPoolConfig:
    """Redis连接池配置

    白皮书依据: 第十二章 12.1.1 Redis连接池与重试机制

    Attributes:
        host: Redis主机地址
        port: Redis端口
        max_connections: 最大连接数，默认50
        socket_timeout: 套接字超时（秒），默认5
        socket_connect_timeout: 连接超时（秒），默认5
        max_retries: 最大重试次数，默认3
        health_check_interval: 健康检查间隔（秒），默认30
        db: 数据库编号，默认0
        password: 密码，默认None
    """

    host: str = "localhost"
    port: int = 6379
    max_connections: int = 50
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    max_retries: int = 3
    health_check_interval: int = 30
    db: int = 0
    password: Optional[str] = None


class ResilientRedisPool:
    """弹性Redis连接池

    白皮书依据: 第十二章 12.1.1 Redis连接池与重试机制

    提供高可用的Redis连接池，支持自动重连和指数退避重试。

    Attributes:
        config: 连接池配置
        status: 当前连接状态
        pool: Redis连接池
        client: Redis客户端
        _running: 健康检查线程运行标志
        _health_thread: 健康检查线程
        _lock: 线程锁
        _failure_count: 连续失败计数
    """

    def __init__(self, config: Optional[RedisPoolConfig] = None):
        """初始化弹性Redis连接池

        Args:
            config: 连接池配置，默认使用默认配置

        Raises:
            ValueError: 当配置参数无效时
        """
        self.config: RedisPoolConfig = config or RedisPoolConfig()

        # 验证配置
        if self.config.max_connections <= 0:
            raise ValueError(f"最大连接数必须 > 0，当前: {self.config.max_connections}")

        if self.config.socket_timeout <= 0:
            raise ValueError(f"套接字超时必须 > 0，当前: {self.config.socket_timeout}")

        if self.config.max_retries < 0:
            raise ValueError(f"最大重试次数必须 >= 0，当前: {self.config.max_retries}")

        self.status: RedisPoolStatus = RedisPoolStatus.DISCONNECTED
        self.pool: Optional[Any] = None
        self.client: Optional[Any] = None

        self._running: bool = False
        self._health_thread: Optional[threading.Thread] = None
        self._lock: threading.RLock = threading.RLock()
        self._failure_count: int = 0

        logger.info(
            f"初始化ResilientRedisPool: "
            f"host={self.config.host}:{self.config.port}, "
            f"max_connections={self.config.max_connections}, "
            f"health_check_interval={self.config.health_check_interval}s"
        )

    def connect(self) -> bool:
        """建立Redis连接

        白皮书依据: 第十二章 12.1.1 Redis连接池与重试机制

        Returns:
            连接是否成功
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis库不可用，使用模拟模式")
            with self._lock:
                self.status = RedisPoolStatus.DEGRADED
            return False

        try:
            with self._lock:
                self.status = RedisPoolStatus.RECONNECTING

            # 创建重试策略
            retry = Retry(ExponentialBackoff(), retries=self.config.max_retries)

            # 创建连接池
            self.pool = redis.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry=retry,
                retry_on_timeout=True,
                health_check_interval=self.config.health_check_interval,
            )

            # 创建客户端
            self.client = redis.Redis(connection_pool=self.pool)

            # 测试连接
            self.client.ping()

            with self._lock:
                self.status = RedisPoolStatus.CONNECTED
                self._failure_count = 0

            logger.info(f"Redis连接成功: {self.config.host}:{self.config.port}")
            return True

        except redis.ConnectionError as e:
            logger.error(f"Redis连接失败: {e}")
            with self._lock:
                self.status = RedisPoolStatus.DISCONNECTED
                self._failure_count += 1
            return False

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Redis连接异常: {e}")
            with self._lock:
                self.status = RedisPoolStatus.DISCONNECTED
                self._failure_count += 1
            return False

    def disconnect(self) -> None:
        """断开Redis连接

        白皮书依据: 第十二章 12.1.1 Redis连接池与重试机制
        """
        self.stop_health_check()

        with self._lock:
            if self.pool is not None:
                try:
                    self.pool.disconnect()
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning(f"断开连接时出错: {e}")

            self.pool = None
            self.client = None
            self.status = RedisPoolStatus.DISCONNECTED

        logger.info("Redis连接已断开")

    def get_client(self) -> Optional[Any]:
        """获取Redis客户端

        白皮书依据: 第十二章 12.1.1 Redis连接池与重试机制

        Returns:
            Redis客户端，如果未连接则返回None
        """
        with self._lock:
            if self.status != RedisPoolStatus.CONNECTED:
                logger.warning(f"Redis未连接，当前状态: {self.status}")
                return None
            return self.client

    def get_status(self) -> RedisPoolStatus:
        """获取连接池状态

        Returns:
            当前连接池状态
        """
        with self._lock:
            return self.status

    def get_failure_count(self) -> int:
        """获取连续失败计数

        Returns:
            连续失败次数
        """
        with self._lock:
            return self._failure_count

    def health_check(self) -> bool:
        """执行健康检查

        白皮书依据: 第十二章 12.1.1 Redis连接池与重试机制

        Returns:
            健康检查是否通过
        """
        if not REDIS_AVAILABLE or self.client is None:
            return False

        try:
            self.client.ping()

            with self._lock:
                if self.status != RedisPoolStatus.CONNECTED:
                    self.status = RedisPoolStatus.CONNECTED
                    logger.info("Redis健康检查通过，状态恢复为CONNECTED")
                self._failure_count = 0

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"Redis健康检查失败: {e}")

            with self._lock:
                self._failure_count += 1

                if self._failure_count >= self.config.max_retries:
                    self.status = RedisPoolStatus.DISCONNECTED
                    logger.error(f"Redis连续失败{self._failure_count}次，标记为DISCONNECTED")
                else:
                    self.status = RedisPoolStatus.DEGRADED

            return False

    def start_health_check(self) -> None:
        """启动健康检查线程

        白皮书依据: 第十二章 12.1.1 Redis连接池与重试机制

        Raises:
            RuntimeError: 当健康检查已在运行时
        """
        with self._lock:
            if self._running:
                raise RuntimeError("健康检查已在运行")

            self._running = True
            self._health_thread = threading.Thread(target=self._health_check_loop, name="RedisHealthCheck", daemon=True)
            self._health_thread.start()

        logger.info("Redis健康检查线程已启动")

    def stop_health_check(self) -> None:
        """停止健康检查线程

        白皮书依据: 第十二章 12.1.1 Redis连接池与重试机制
        """
        with self._lock:
            if not self._running:
                return
            self._running = False

        if self._health_thread and self._health_thread.is_alive():
            self._health_thread.join(timeout=5.0)

        logger.info("Redis健康检查线程已停止")

    def _health_check_loop(self) -> None:
        """健康检查主循环（内部方法）

        白皮书依据: 第十二章 12.1.1 Redis连接池与重试机制
        """
        logger.info("Redis健康检查主循环已启动")

        while self._running:
            try:
                # 执行健康检查
                is_healthy = self.health_check()

                # 如果不健康，尝试重连
                if not is_healthy:
                    logger.info("尝试重新连接Redis...")
                    self.connect()

                # 等待下一次检查
                time.sleep(self.config.health_check_interval)

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"健康检查循环异常: {e}")
                time.sleep(self.config.health_check_interval)

        logger.info("Redis健康检查主循环已退出")

    def execute_with_retry(self, operation: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """带重试的操作执行

        白皮书依据: 第十二章 12.1.1 Redis连接池与重试机制

        Args:
            operation: 要执行的操作
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            操作结果

        Raises:
            redis.ConnectionError: 当重试次数用尽后仍失败时
        """
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis库不可用")

        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return operation(*args, **kwargs)

            except redis.ConnectionError as e:
                last_error = e

                if attempt < self.config.max_retries:
                    wait_time = 2**attempt  # 指数退避: 1s, 2s, 4s
                    logger.warning(
                        f"Redis操作失败，重试 {attempt + 1}/{self.config.max_retries}，" f"等待 {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Redis操作失败，已达最大重试次数 {self.config.max_retries}: {e}")

        if last_error:
            raise last_error

        raise RuntimeError("未知错误")


# 类型变量用于装饰器
F = TypeVar("F", bound=Callable[..., Any])


def redis_retry(max_retries: int = 3, backoff_factor: int = 2) -> Callable[[F], F]:
    """Redis操作重试装饰器

    白皮书依据: 第十二章 12.1.1 Redis连接池与重试机制

    Args:
        max_retries: 最大重试次数，默认3
        backoff_factor: 退避因子，默认2

    Returns:
        装饰器函数

    Example:
        >>> @redis_retry(max_retries=3)
        ... def get_portfolio_value():
        ...     return redis_client.get('portfolio:total_value')
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except Exception as e:  # pylint: disable=broad-exception-caught
                    # 检查是否是Redis连接错误
                    if REDIS_AVAILABLE and isinstance(e, redis.ConnectionError):
                        last_error = e

                        if attempt < max_retries:
                            wait_time = backoff_factor**attempt
                            logger.warning(f"[Redis] 重试 {attempt + 1}/{max_retries}，" f"等待 {wait_time}s: {e}")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"[Redis] 重试次数用尽 ({max_retries}次): {e}")
                    else:
                        # 非Redis连接错误，直接抛出
                        raise

            if last_error:
                raise last_error

            raise RuntimeError("未知错误")

        return cast(F, wrapper)

    return decorator


# 全局单例实例
_global_pool: Optional[ResilientRedisPool] = None
_global_lock: threading.Lock = threading.Lock()


def get_redis_pool(config: Optional[RedisPoolConfig] = None) -> ResilientRedisPool:
    """获取全局Redis连接池实例

    白皮书依据: 第十二章 12.1.1 Redis连接池与重试机制

    Args:
        config: 连接池配置，仅在首次调用时有效

    Returns:
        全局Redis连接池实例
    """
    global _global_pool  # pylint: disable=w0603

    with _global_lock:
        if _global_pool is None:
            _global_pool = ResilientRedisPool(config)
        return _global_pool


def reset_redis_pool() -> None:
    """重置全局Redis连接池

    主要用于测试目的。
    """
    global _global_pool  # pylint: disable=w0603

    with _global_lock:
        if _global_pool is not None:
            _global_pool.disconnect()
            _global_pool = None
