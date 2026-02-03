"""缓存管理器 - 智能数据探针与桥接系统

白皮书依据: 第三章 3.2 基础设施与数据治理
需求: requirements.md 9.1-9.7 (原7.1-7.10)
设计: design.md 核心组件设计 - 缓存管理器

本模块实现了基于Redis的缓存管理器，用于：
- 减少API调用次数
- 提高数据获取速度
- 降低数据源负载
- 优化系统性能

性能要求:
- 缓存命中率 > 80%
- 缓存读写延迟 < 10ms
- 支持TTL自动过期
"""

import hashlib
import pickle
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis未安装，缓存功能将被禁用")


class CacheManager:
    """缓存管理器

    白皮书依据: 第三章 3.2 基础设施与数据治理
    需求: 9.1-9.7
    设计: design.md - CacheManager

    使用Redis管理数据缓存，支持：
    1. 键值对存储（get/set）
    2. TTL自动过期
    3. 序列化/反序列化（pickle）
    4. 缓存键生成策略
    5. 批量操作

    缓存策略：
    - 日线数据缓存24小时（需求9.2）
    - 分钟线数据缓存1小时（需求9.3）
    - 宏观数据缓存7天（需求9.4）

    Attributes:
        redis_client: Redis客户端实例
        default_ttl: 默认过期时间（秒），默认3600秒（1小时）
        key_prefix: 缓存键前缀，用于命名空间隔离
        enabled: 缓存是否启用

    Example:
        >>> cache = CacheManager()
        >>> cache.set("market:AAPL:2024-01-01", data, ttl=86400)
        >>> data = cache.get("market:AAPL:2024-01-01")
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        default_ttl: int = 3600,
        key_prefix: str = "mia:data:",
        enabled: bool = True,
    ):
        """初始化缓存管理器

        Args:
            redis_host: Redis主机地址，默认localhost
            redis_port: Redis端口，默认6379
            redis_db: Redis数据库编号，默认0
            redis_password: Redis密码，可选
            default_ttl: 默认过期时间（秒），默认3600秒（1小时）
            key_prefix: 缓存键前缀，默认'mia:data:'
            enabled: 是否启用缓存，默认True

        Raises:
            ConnectionError: 当Redis连接失败时
        """
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.enabled = enabled and REDIS_AVAILABLE

        if not self.enabled:
            logger.warning("缓存管理器已禁用")
            self.redis_client = None
            return

        try:
            # 初始化Redis客户端
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=False,  # 不自动解码，使用pickle
                socket_connect_timeout=5,
                socket_timeout=5,
            )

            # 测试连接
            self.redis_client.ping()

            logger.info(f"缓存管理器初始化成功: {redis_host}:{redis_port}, " f"db={redis_db}, ttl={default_ttl}s")

        except (redis.ConnectionError, ConnectionRefusedError, OSError) as e:
            logger.error(f"Redis连接失败: {e}")
            self.enabled = False
            self.redis_client = None
            raise ConnectionError(f"Redis连接失败: {e}") from e

        except Exception as e:
            logger.error(f"缓存管理器初始化失败: {e}")
            self.enabled = False
            self.redis_client = None
            raise ConnectionError(f"Redis连接失败: {e}") from e

    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据

        需求: 9.1

        Args:
            key: 缓存键（不含前缀）

        Returns:
            缓存的数据，如果不存在或缓存禁用返回None

        Example:
            >>> data = cache.get("market:AAPL:2024-01-01")
        """
        if not self.enabled or self.redis_client is None:
            return None

        try:
            # 添加前缀
            full_key = self._make_key(key)

            # 获取数据
            data = self.redis_client.get(full_key)

            if data is None:
                logger.debug(f"缓存未命中: {key}")
                return None

            # 反序列化
            result = pickle.loads(data)
            logger.debug(f"缓存命中: {key}")

            return result

        except pickle.UnpicklingError as e:
            logger.error(f"反序列化失败: {key}, 错误: {e}")
            # 删除损坏的缓存
            self.delete(key)
            return None

        except redis.RedisError as e:
            logger.warning(f"获取缓存失败: {key}, 错误: {e}")
            return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"获取缓存异常: {key}, 错误: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存数据

        需求: 9.1, 9.2, 9.3, 9.4

        Args:
            key: 缓存键（不含前缀）
            value: 要缓存的数据（必须可序列化）
            ttl: 过期时间（秒），None使用默认值

        Returns:
            是否设置成功

        Raises:
            ValueError: 当value不可序列化时

        Example:
            >>> cache.set("market:AAPL:2024-01-01", data, ttl=86400)
        """
        if not self.enabled or self.redis_client is None:
            return False

        if value is None:
            logger.warning(f"尝试缓存None值: {key}")
            return False

        try:
            # 序列化
            data = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

        except (pickle.PicklingError, TypeError, AttributeError) as e:
            logger.error(f"序列化失败: {key}, 错误: {e}")
            raise ValueError(f"数据不可序列化: {e}") from e

        try:
            # 添加前缀
            full_key = self._make_key(key)

            # 设置缓存
            ttl = ttl or self.default_ttl
            self.redis_client.setex(full_key, ttl, data)

            logger.debug(f"缓存设置成功: {key}, ttl={ttl}s")
            return True

        except redis.RedisError as e:
            logger.error(f"设置缓存失败: {key}, 错误: {e}")
            return False

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"设置缓存异常: {key}, 错误: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存

        需求: 9.6

        Args:
            key: 缓存键（不含前缀）

        Returns:
            是否删除成功

        Example:
            >>> cache.delete("market:AAPL:2024-01-01")
        """
        if not self.enabled or self.redis_client is None:
            return False

        try:
            # 添加前缀
            full_key = self._make_key(key)

            # 删除缓存
            result = self.redis_client.delete(full_key)

            if result > 0:  # pylint: disable=no-else-return
                logger.debug(f"缓存删除成功: {key}")
                return True
            else:
                logger.debug(f"缓存不存在: {key}")
                return False

        except redis.RedisError as e:
            logger.error(f"删除缓存失败: {key}, 错误: {e}")
            return False

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"删除缓存异常: {key}, 错误: {e}")
            return False

    def clear_all(self) -> bool:
        """清空所有缓存

        需求: 9.7

        警告：此操作会清空当前Redis数据库的所有数据！

        Returns:
            是否清空成功

        Example:
            >>> cache.clear_all()
        """
        if not self.enabled or self.redis_client is None:
            return False

        try:
            # 清空当前数据库
            self.redis_client.flushdb()
            logger.info("已清空所有缓存")
            return True

        except redis.RedisError as e:
            logger.error(f"清空缓存失败: {e}")
            return False

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"清空缓存异常: {e}")
            return False

    def exists(self, key: str) -> bool:
        """检查缓存是否存在

        Args:
            key: 缓存键（不含前缀）

        Returns:
            缓存是否存在

        Example:
            >>> if cache.exists("market:AAPL:2024-01-01"):
            ...     data = cache.get("market:AAPL:2024-01-01")
        """
        if not self.enabled or self.redis_client is None:
            return False

        try:
            full_key = self._make_key(key)
            return self.redis_client.exists(full_key) > 0

        except redis.RedisError as e:
            logger.warning(f"检查缓存存在性失败: {key}, 错误: {e}")
            return False

    def get_ttl(self, key: str) -> Optional[int]:
        """获取缓存剩余过期时间

        Args:
            key: 缓存键（不含前缀）

        Returns:
            剩余过期时间（秒），-1表示永不过期，-2表示不存在，None表示查询失败

        Example:
            >>> ttl = cache.get_ttl("market:AAPL:2024-01-01")
            >>> print(f"剩余时间: {ttl}秒")
        """
        if not self.enabled or self.redis_client is None:
            return None

        try:
            full_key = self._make_key(key)
            return self.redis_client.ttl(full_key)

        except redis.RedisError as e:
            logger.warning(f"获取TTL失败: {key}, 错误: {e}")
            return None

    def _make_key(self, key: str) -> str:
        """生成完整的缓存键

        添加前缀，用于命名空间隔离。

        Args:
            key: 原始键

        Returns:
            完整的缓存键
        """
        return f"{self.key_prefix}{key}"

    @staticmethod
    def generate_cache_key(
        data_type: str,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs,
    ) -> str:
        """生成标准化的缓存键

        需求: 9.1 - 缓存键生成策略

        使用标准化格式生成缓存键，支持参数哈希。

        Args:
            data_type: 数据类型（market, sentiment, news等）
            symbol: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            **kwargs: 其他参数（会被哈希）

        Returns:
            标准化的缓存键

        Example:
            >>> key = CacheManager.generate_cache_key(
            ...     data_type="market",
            ...     symbol="AAPL",
            ...     start_date=datetime(2024, 1, 1),
            ...     end_date=datetime(2024, 12, 31),
            ...     frequency="1d"
            ... )
            >>> print(key)
            'market:AAPL:2024-01-01:2024-12-31:a1b2c3d4'
        """
        # 基础键
        parts = [data_type, symbol]

        # 添加日期
        if start_date:
            parts.append(start_date.strftime("%Y-%m-%d"))
        if end_date:
            parts.append(end_date.strftime("%Y-%m-%d"))

        # 处理额外参数
        if kwargs:
            # 对参数进行排序，确保一致性
            sorted_params = sorted(kwargs.items())
            param_str = str(sorted_params)

            # 生成参数哈希（前8位）
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            parts.append(param_hash)

        return ":".join(parts)

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            缓存统计信息字典

        Example:
            >>> stats = cache.get_stats()
            >>> print(f"缓存键数量: {stats['keys_count']}")
            >>> print(f"内存使用: {stats['used_memory_human']}")
        """
        if not self.enabled or self.redis_client is None:
            return {"enabled": False, "keys_count": 0, "used_memory": 0}

        try:
            info = self.redis_client.info()

            # 统计当前前缀的键数量
            pattern = f"{self.key_prefix}*"
            keys_count = len(list(self.redis_client.scan_iter(match=pattern, count=100)))

            return {
                "enabled": True,
                "keys_count": keys_count,
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info.get("keyspace_hits", 0), info.get("keyspace_misses", 0)),
            }

        except redis.RedisError as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {"enabled": True, "error": str(e)}

    @staticmethod
    def _calculate_hit_rate(hits: int, misses: int) -> float:
        """计算缓存命中率

        Args:
            hits: 命中次数
            misses: 未命中次数

        Returns:
            命中率（0-1）
        """
        total = hits + misses
        if total == 0:
            return 0.0
        return hits / total

    def close(self):
        """关闭Redis连接

        Example:
            >>> cache.close()
        """
        if self.redis_client is not None:
            try:
                self.redis_client.close()
                logger.info("Redis连接已关闭")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"关闭Redis连接失败: {e}")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
        return False
