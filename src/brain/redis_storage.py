# pylint: disable=too-many-lines
"""Redis存储管理器

白皮书依据: 第五章 5.5 Redis数据结构

本模块实现了Redis存储管理器和TTL管理器，负责：
- 分析结果存储（策略本质、风险评估、过拟合检测等）
- 知识库存储（基因胶囊、演化树、精英策略、反向黑名单等）
- TTL自动管理
- 批量操作和事务操作

性能要求:
- Redis连接池: 50个连接
- 支持10个并发分析请求
"""

import asyncio
import json
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from loguru import logger

try:
    import redis.asyncio as aioredis
    from redis.asyncio import ConnectionPool

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis库未安装，将使用内存模拟存储")


class TTLManager:
    """TTL管理器

    白皮书依据: 第五章 5.5 Redis数据结构

    管理数据的TTL策略。

    TTL配置:
    - 市场数据: 1小时 (3600秒)
    - 历史数据: 30天 (2592000秒)
    - 知识库数据: 永久 (-1)

    Attributes:
        redis_client: Redis客户端
    """

    # TTL常量
    TTL_MARKET = 3600  # 1小时
    TTL_HISTORY = 2592000  # 30天
    TTL_PERMANENT = -1  # 永久

    # 键模式到TTL的映射
    _TTL_PATTERNS: List[Tuple[str, int]] = [
        (r"^mia:market:limit_up:", TTL_HISTORY),  # 涨停板数据: 30天
        (r"^mia:market:", TTL_MARKET),  # 市场数据: 1小时
        (r"^mia:smart_money:", TTL_MARKET),  # 主力资金: 1小时
        (r"^mia:recommendation:", TTL_MARKET),  # 个股建议: 1小时
        (r"^mia:knowledge:", TTL_PERMANENT),  # 知识库: 永久
        (r"^mia:analysis:", TTL_PERMANENT),  # 分析结果: 永久
    ]

    def __init__(self, redis_client: Optional[Any] = None) -> None:
        """初始化TTL管理器

        Args:
            redis_client: Redis客户端实例
        """
        self._redis_client = redis_client
        self._compiled_patterns: List[Tuple[re.Pattern, int]] = [
            (re.compile(pattern), ttl) for pattern, ttl in self._TTL_PATTERNS
        ]
        logger.info("TTLManager初始化完成")

    def get_ttl_for_key(self, key: str) -> int:
        """根据键名获取TTL

        白皮书依据: 第五章 5.5 Redis数据结构

        规则:
        - mia:market:limit_up:* -> 30天
        - mia:market:* -> 1小时
        - mia:smart_money:* -> 1小时
        - mia:recommendation:* -> 1小时
        - mia:knowledge:* -> 永久
        - mia:analysis:* -> 永久

        Args:
            key: Redis键名

        Returns:
            TTL秒数，-1表示永久

        Raises:
            ValueError: 当键名为空时
        """
        if not key:
            raise ValueError("键名不能为空")

        for pattern, ttl in self._compiled_patterns:
            if pattern.match(key):
                return ttl

        # 默认返回永久
        return self.TTL_PERMANENT

    async def set_ttl(self, key: str, ttl: Optional[int] = None) -> None:
        """设置TTL

        Args:
            key: Redis键
            ttl: TTL秒数，None则自动判断

        Raises:
            ValueError: 当键名为空时
            RuntimeError: 当Redis客户端未初始化时
        """
        if not key:
            raise ValueError("键名不能为空")

        if self._redis_client is None:
            logger.warning(f"Redis客户端未初始化，跳过设置TTL: {key}")
            return

        actual_ttl = ttl if ttl is not None else self.get_ttl_for_key(key)

        if actual_ttl == self.TTL_PERMANENT:
            # 永久存储，移除过期时间
            await self._redis_client.persist(key)
            logger.debug(f"设置键为永久存储: {key}")
        else:
            await self._redis_client.expire(key, actual_ttl)
            logger.debug(f"设置键TTL: {key} -> {actual_ttl}秒")

    async def refresh_ttl(self, key: str) -> None:
        """刷新TTL（重置过期时间）

        Args:
            key: Redis键

        Raises:
            ValueError: 当键名为空时
        """
        if not key:
            raise ValueError("键名不能为空")

        if self._redis_client is None:
            logger.warning(f"Redis客户端未初始化，跳过刷新TTL: {key}")
            return

        ttl = self.get_ttl_for_key(key)
        if ttl != self.TTL_PERMANENT:
            await self._redis_client.expire(key, ttl)
            logger.debug(f"刷新键TTL: {key} -> {ttl}秒")

    async def invalidate(self, key: str) -> None:
        """主动失效（删除键）

        Args:
            key: Redis键

        Raises:
            ValueError: 当键名为空时
        """
        if not key:
            raise ValueError("键名不能为空")

        if self._redis_client is None:
            logger.warning(f"Redis客户端未初始化，跳过删除键: {key}")
            return

        await self._redis_client.delete(key)
        logger.debug(f"删除键: {key}")

    async def invalidate_pattern(self, pattern: str) -> int:
        """按模式批量失效

        Args:
            pattern: 键模式（支持*通配符）

        Returns:
            删除的键数量

        Raises:
            ValueError: 当模式为空时
        """
        if not pattern:
            raise ValueError("模式不能为空")

        if self._redis_client is None:
            logger.warning(f"Redis客户端未初始化，跳过批量删除: {pattern}")
            return 0

        deleted_count = 0
        cursor = 0

        while True:
            cursor, keys = await self._redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                deleted_count += await self._redis_client.delete(*keys)
            if cursor == 0:
                break

        logger.info(f"批量删除键: {pattern} -> 删除{deleted_count}个")
        return deleted_count

    async def get_ttl_stats(self) -> Dict[str, Any]:
        """获取TTL统计信息

        Returns:
            {
                'total_keys': int,
                'permanent_keys': int,
                'expiring_soon': int,  # 1小时内过期
                'by_prefix': Dict[str, int]
            }
        """
        if self._redis_client is None:
            logger.warning("Redis客户端未初始化，返回空统计")
            return {
                "total_keys": 0,
                "permanent_keys": 0,
                "expiring_soon": 0,
                "by_prefix": {},
            }

        stats = {
            "total_keys": 0,
            "permanent_keys": 0,
            "expiring_soon": 0,
            "by_prefix": {},
        }

        cursor = 0
        while True:
            cursor, keys = await self._redis_client.scan(cursor, match="mia:*", count=100)
            for key in keys:
                stats["total_keys"] += 1

                # 获取TTL
                ttl = await self._redis_client.ttl(key)
                if ttl == -1:
                    stats["permanent_keys"] += 1
                elif 0 < ttl <= 3600:
                    stats["expiring_soon"] += 1

                # 按前缀统计
                key_str = key.decode() if isinstance(key, bytes) else key
                parts = key_str.split(":")
                if len(parts) >= 2:
                    prefix = f"{parts[0]}:{parts[1]}"
                    stats["by_prefix"][prefix] = stats["by_prefix"].get(prefix, 0) + 1

            if cursor == 0:
                break

        return stats


class InMemoryStorage:
    """内存模拟存储（用于测试和无Redis环境）

    当Redis不可用时，使用内存字典模拟Redis操作。
    """

    def __init__(self) -> None:
        """初始化内存存储"""
        self._data: Dict[str, Any] = {}
        self._ttls: Dict[str, int] = {}
        self._sets: Dict[str, Set[str]] = {}
        self._lists: Dict[str, List[Any]] = {}
        self._hashes: Dict[str, Dict[str, Any]] = {}

    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        return self._data.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        """设置值"""
        self._data[key] = value
        if ex is not None:
            self._ttls[key] = ex

    async def delete(self, *keys: str) -> int:
        """删除键"""
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                count += 1
            if key in self._sets:
                del self._sets[key]
                count += 1
            if key in self._lists:
                del self._lists[key]
                count += 1
            if key in self._hashes:
                del self._hashes[key]
                count += 1
        return count

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self._data or key in self._sets or key in self._lists or key in self._hashes

    async def expire(self, key: str, seconds: int) -> None:
        """设置过期时间"""
        self._ttls[key] = seconds

    async def persist(self, key: str) -> None:
        """移除过期时间"""
        self._ttls.pop(key, None)

    async def ttl(self, key: str) -> int:
        """获取TTL"""
        return self._ttls.get(key, -1)

    async def scan(
        self, cursor: int, match: str = "*", count: int = 100  # pylint: disable=unused-argument
    ) -> Tuple[int, List[str]]:  # pylint: disable=unused-argument
        """扫描键"""
        pattern = match.replace("*", ".*")
        regex = re.compile(f"^{pattern}$")
        all_keys = (
            list(self._data.keys()) + list(self._sets.keys()) + list(self._lists.keys()) + list(self._hashes.keys())
        )
        matched = [k for k in all_keys if regex.match(k)]
        return 0, matched

    async def sadd(self, key: str, *values: str) -> int:
        """添加到集合"""
        if key not in self._sets:
            self._sets[key] = set()
        before = len(self._sets[key])
        self._sets[key].update(values)
        return len(self._sets[key]) - before

    async def smembers(self, key: str) -> Set[str]:
        """获取集合成员"""
        return self._sets.get(key, set())

    async def srem(self, key: str, *values: str) -> int:
        """从集合移除"""
        if key not in self._sets:
            return 0
        before = len(self._sets[key])
        self._sets[key] -= set(values)
        return before - len(self._sets[key])

    async def lpush(self, key: str, *values: Any) -> int:
        """左侧插入列表"""
        if key not in self._lists:
            self._lists[key] = []
        for v in reversed(values):
            self._lists[key].insert(0, v)
        return len(self._lists[key])

    async def lrange(self, key: str, start: int, end: int) -> List[Any]:
        """获取列表范围"""
        if key not in self._lists:
            return []
        if end == -1:
            return self._lists[key][start:]
        return self._lists[key][start : end + 1]

    async def hset(self, key: str, mapping: Dict[str, Any]) -> int:
        """设置哈希字段"""
        if key not in self._hashes:
            self._hashes[key] = {}
        self._hashes[key].update(mapping)
        return len(mapping)

    async def hgetall(self, key: str) -> Dict[str, Any]:
        """获取所有哈希字段"""
        return self._hashes.get(key, {})

    async def mget(self, *keys: str) -> List[Optional[str]]:
        """批量获取"""
        return [self._data.get(k) for k in keys]

    async def mset(self, mapping: Dict[str, str]) -> None:
        """批量设置"""
        self._data.update(mapping)

    def pipeline(self) -> "InMemoryPipeline":
        """创建管道"""
        return InMemoryPipeline(self)


class InMemoryPipeline:
    """内存管道（模拟Redis管道）"""

    def __init__(self, storage: InMemoryStorage) -> None:
        """初始化管道"""
        self._storage = storage
        self._commands: List[Tuple[str, tuple, dict]] = []

    def set(self, key: str, value: str, ex: Optional[int] = None) -> "InMemoryPipeline":
        """添加set命令"""
        self._commands.append(("set", (key, value), {"ex": ex}))
        return self

    def delete(self, *keys: str) -> "InMemoryPipeline":
        """添加delete命令"""
        self._commands.append(("delete", keys, {}))
        return self

    def expire(self, key: str, seconds: int) -> "InMemoryPipeline":
        """添加expire命令"""
        self._commands.append(("expire", (key, seconds), {}))
        return self

    async def execute(self) -> List[Any]:
        """执行所有命令"""
        results = []
        for cmd, args, kwargs in self._commands:
            method = getattr(self._storage, cmd)
            result = await method(*args, **kwargs)
            results.append(result)
        self._commands.clear()
        return results


class RedisStorageManager:  # pylint: disable=too-many-public-methods
    """Redis存储管理器

    白皮书依据: 第五章 5.5 Redis数据结构

    管理分析结果和知识库的Redis存储。

    Attributes:
        redis_pool: Redis连接池（50个连接）
        ttl_manager: TTL管理器
    """

    # 键前缀常量
    KEY_ANALYSIS_ESSENCE = "mia:analysis:essence"
    KEY_ANALYSIS_RISK = "mia:analysis:risk"
    KEY_ANALYSIS_OVERFITTING = "mia:analysis:overfitting"
    KEY_MARKET_MACRO = "mia:market:macro"
    KEY_MARKET_LIMIT_UP = "mia:market:limit_up"
    KEY_SMART_MONEY = "mia:smart_money:deep_analysis"
    KEY_RECOMMENDATION = "mia:recommendation"
    KEY_KNOWLEDGE_GENE_CAPSULE = "mia:knowledge:gene_capsule"
    KEY_KNOWLEDGE_EVOLUTION_TREE = "mia:knowledge:evolution_tree"
    KEY_KNOWLEDGE_ELITE_STRATEGIES = "mia:knowledge:elite_strategies"
    KEY_KNOWLEDGE_FAILED_STRATEGIES = "mia:knowledge:failed_strategies"
    KEY_KNOWLEDGE_ANTI_PATTERNS = "mia:knowledge:anti_patterns"

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        pool_size: int = 50,
        use_memory_fallback: bool = True,
    ) -> None:
        """初始化Redis存储管理器

        Args:
            redis_url: Redis连接URL
            pool_size: 连接池大小，默认50
            use_memory_fallback: 当Redis不可用时是否使用内存存储

        Raises:
            RuntimeError: 当Redis不可用且不允许内存回退时
        """
        self._redis_url = redis_url
        self._pool_size = pool_size
        self._use_memory_fallback = use_memory_fallback
        self._redis_client: Optional[Any] = None
        self._ttl_manager: Optional[TTLManager] = None
        self._initialized = False

        logger.info(f"RedisStorageManager初始化: url={redis_url}, pool_size={pool_size}")

    async def initialize(self) -> None:
        """初始化Redis连接

        Raises:
            RuntimeError: 当Redis连接失败且不允许内存回退时
        """
        if self._initialized:
            return

        if REDIS_AVAILABLE:
            try:
                pool = ConnectionPool.from_url(
                    self._redis_url,
                    max_connections=self._pool_size,
                    decode_responses=True,
                )
                self._redis_client = aioredis.Redis(connection_pool=pool)
                # 测试连接
                await self._redis_client.ping()
                logger.info("Redis连接成功")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"Redis连接失败: {e}")
                if self._use_memory_fallback:
                    logger.info("使用内存存储作为回退")
                    self._redis_client = InMemoryStorage()
                else:
                    raise RuntimeError(f"Redis连接失败: {e}") from e
        else:
            if self._use_memory_fallback:
                logger.info("Redis库未安装，使用内存存储")
                self._redis_client = InMemoryStorage()
            else:
                raise RuntimeError("Redis库未安装且不允许内存回退")

        self._ttl_manager = TTLManager(self._redis_client)
        self._initialized = True

    async def close(self) -> None:
        """关闭Redis连接"""
        if self._redis_client is not None and REDIS_AVAILABLE:
            if hasattr(self._redis_client, "aclose"):
                await self._redis_client.aclose()
            elif hasattr(self._redis_client, "close"):
                # 对于旧版本Redis或内存存储
                if asyncio.iscoroutinefunction(self._redis_client.close):
                    await self._redis_client.close()
                else:
                    self._redis_client.close()
        self._initialized = False
        logger.info("Redis连接已关闭")

    @property
    def ttl_manager(self) -> TTLManager:
        """获取TTL管理器"""
        if self._ttl_manager is None:
            raise RuntimeError("RedisStorageManager未初始化，请先调用initialize()")
        return self._ttl_manager

    async def _ensure_initialized(self) -> None:
        """确保已初始化"""
        if not self._initialized:
            await self.initialize()

    # ===== 分析结果存储 =====

    async def store_essence_analysis(
        self,
        strategy_id: str,
        data: Dict[str, Any],
    ) -> None:
        """存储策略本质分析

        白皮书依据: 第五章 5.5.1 分析结果存储

        Key: mia:analysis:essence:{strategy_id}
        Type: String (JSON)
        TTL: 永久

        Args:
            strategy_id: 策略ID
            data: 分析数据

        Raises:
            ValueError: 当strategy_id为空时
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")

        await self._ensure_initialized()
        key = f"{self.KEY_ANALYSIS_ESSENCE}:{strategy_id}"
        json_data = json.dumps(data, ensure_ascii=False, default=str)
        await self._redis_client.set(key, json_data)
        await self._ttl_manager.set_ttl(key)
        logger.debug(f"存储策略本质分析: {key}")

    async def store_risk_assessment(
        self,
        strategy_id: str,
        data: Dict[str, Any],
    ) -> None:
        """存储风险评估

        白皮书依据: 第五章 5.5.1 分析结果存储

        Key: mia:analysis:risk:{strategy_id}
        Type: String (JSON)
        TTL: 永久

        Args:
            strategy_id: 策略ID
            data: 风险评估数据

        Raises:
            ValueError: 当strategy_id为空时
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")

        await self._ensure_initialized()
        key = f"{self.KEY_ANALYSIS_RISK}:{strategy_id}"
        json_data = json.dumps(data, ensure_ascii=False, default=str)
        await self._redis_client.set(key, json_data)
        await self._ttl_manager.set_ttl(key)
        logger.debug(f"存储风险评估: {key}")

    async def store_overfitting_detection(
        self,
        strategy_id: str,
        data: Dict[str, Any],
    ) -> None:
        """存储过拟合检测

        白皮书依据: 第五章 5.5.1 分析结果存储

        Key: mia:analysis:overfitting:{strategy_id}
        Type: String (JSON)
        TTL: 永久

        Args:
            strategy_id: 策略ID
            data: 过拟合检测数据

        Raises:
            ValueError: 当strategy_id为空时
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")

        await self._ensure_initialized()
        key = f"{self.KEY_ANALYSIS_OVERFITTING}:{strategy_id}"
        json_data = json.dumps(data, ensure_ascii=False, default=str)
        await self._redis_client.set(key, json_data)
        await self._ttl_manager.set_ttl(key)
        logger.debug(f"存储过拟合检测: {key}")

    async def store_market_macro(self, data: Dict[str, Any]) -> None:
        """存储市场宏观分析

        白皮书依据: 第五章 5.5.1 分析结果存储

        Key: mia:market:macro
        Type: Hash
        TTL: 1小时

        Args:
            data: 市场宏观分析数据
        """
        await self._ensure_initialized()
        key = self.KEY_MARKET_MACRO
        # 将数据转换为字符串值的字典
        string_data = {k: json.dumps(v, ensure_ascii=False, default=str) for k, v in data.items()}
        await self._redis_client.hset(key, mapping=string_data)
        await self._ttl_manager.set_ttl(key)
        logger.debug(f"存储市场宏观分析: {key}")

    async def store_limit_up_data(
        self,
        date: str,
        data: Dict[str, Any],
    ) -> None:
        """存储涨停板数据

        白皮书依据: 第五章 5.5.1 分析结果存储

        Key: mia:market:limit_up:{date}
        Type: String (JSON)
        TTL: 30天

        Args:
            date: 日期（格式：YYYY-MM-DD）
            data: 涨停板数据

        Raises:
            ValueError: 当date为空时
        """
        if not date:
            raise ValueError("日期不能为空")

        await self._ensure_initialized()
        key = f"{self.KEY_MARKET_LIMIT_UP}:{date}"
        json_data = json.dumps(data, ensure_ascii=False, default=str)
        await self._redis_client.set(key, json_data)
        await self._ttl_manager.set_ttl(key)
        logger.debug(f"存储涨停板数据: {key}")

    async def store_smart_money_analysis(
        self,
        symbol: str,
        data: Dict[str, Any],
    ) -> None:
        """存储主力资金深度分析

        白皮书依据: 第五章 5.5.1 分析结果存储

        Key: mia:smart_money:deep_analysis:{symbol}
        Type: String (JSON)
        TTL: 1小时

        Args:
            symbol: 股票代码
            data: 主力资金分析数据

        Raises:
            ValueError: 当symbol为空时
        """
        if not symbol:
            raise ValueError("股票代码不能为空")

        await self._ensure_initialized()
        key = f"{self.KEY_SMART_MONEY}:{symbol}"
        json_data = json.dumps(data, ensure_ascii=False, default=str)
        await self._redis_client.set(key, json_data)
        await self._ttl_manager.set_ttl(key)
        logger.debug(f"存储主力资金分析: {key}")

    async def store_recommendation(
        self,
        symbol: str,
        data: Dict[str, Any],
    ) -> None:
        """存储个股建议

        白皮书依据: 第五章 5.5.1 分析结果存储

        Key: mia:recommendation:{symbol}
        Type: String (JSON)
        TTL: 1小时

        Args:
            symbol: 股票代码
            data: 个股建议数据

        Raises:
            ValueError: 当symbol为空时
        """
        if not symbol:
            raise ValueError("股票代码不能为空")

        await self._ensure_initialized()
        key = f"{self.KEY_RECOMMENDATION}:{symbol}"
        json_data = json.dumps(data, ensure_ascii=False, default=str)
        await self._redis_client.set(key, json_data)
        await self._ttl_manager.set_ttl(key)
        logger.debug(f"存储个股建议: {key}")

    # ===== 知识库存储 =====

    async def store_gene_capsule(
        self,
        capsule_id: str,
        data: Dict[str, Any],
    ) -> None:
        """存储基因胶囊

        白皮书依据: 第五章 5.5.2 知识库存储

        Key: mia:knowledge:gene_capsule:{capsule_id}
        Type: String (JSON)
        TTL: 永久

        Args:
            capsule_id: 胶囊ID
            data: 基因胶囊数据

        Raises:
            ValueError: 当capsule_id为空时
        """
        if not capsule_id:
            raise ValueError("胶囊ID不能为空")

        await self._ensure_initialized()
        key = f"{self.KEY_KNOWLEDGE_GENE_CAPSULE}:{capsule_id}"
        json_data = json.dumps(data, ensure_ascii=False, default=str)
        await self._redis_client.set(key, json_data)
        await self._ttl_manager.set_ttl(key)
        logger.debug(f"存储基因胶囊: {key}")

    async def store_evolution_tree(self, data: Dict[str, Any]) -> None:
        """存储演化树

        白皮书依据: 第五章 5.5.2 知识库存储

        Key: mia:knowledge:evolution_tree
        Type: String (JSON)
        TTL: 永久

        Args:
            data: 演化树数据
        """
        await self._ensure_initialized()
        key = self.KEY_KNOWLEDGE_EVOLUTION_TREE
        json_data = json.dumps(data, ensure_ascii=False, default=str)
        await self._redis_client.set(key, json_data)
        await self._ttl_manager.set_ttl(key)
        logger.debug(f"存储演化树: {key}")

    async def add_elite_strategy(self, strategy_id: str) -> None:
        """添加精英策略

        白皮书依据: 第五章 5.5.2 知识库存储

        Key: mia:knowledge:elite_strategies
        Type: Set
        TTL: 永久

        Args:
            strategy_id: 策略ID

        Raises:
            ValueError: 当strategy_id为空时
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")

        await self._ensure_initialized()
        key = self.KEY_KNOWLEDGE_ELITE_STRATEGIES
        await self._redis_client.sadd(key, strategy_id)
        await self._ttl_manager.set_ttl(key)
        logger.debug(f"添加精英策略: {strategy_id}")

    async def add_failed_strategy(self, strategy_id: str) -> None:
        """添加失败策略

        白皮书依据: 第五章 5.5.2 知识库存储

        Key: mia:knowledge:failed_strategies
        Type: Set
        TTL: 永久

        Args:
            strategy_id: 策略ID

        Raises:
            ValueError: 当strategy_id为空时
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")

        await self._ensure_initialized()
        key = self.KEY_KNOWLEDGE_FAILED_STRATEGIES
        await self._redis_client.sadd(key, strategy_id)
        await self._ttl_manager.set_ttl(key)
        logger.debug(f"添加失败策略: {strategy_id}")

    async def store_anti_patterns(
        self,
        patterns: List[Dict[str, Any]],
    ) -> None:
        """存储反向黑名单

        白皮书依据: 第五章 5.5.2 知识库存储

        Key: mia:knowledge:anti_patterns
        Type: List (JSON)
        TTL: 永久

        Args:
            patterns: 反向模式列表
        """
        await self._ensure_initialized()
        key = self.KEY_KNOWLEDGE_ANTI_PATTERNS

        # 先删除旧数据
        await self._redis_client.delete(key)

        # 添加新数据
        if patterns:
            json_patterns = [json.dumps(p, ensure_ascii=False, default=str) for p in patterns]
            await self._redis_client.lpush(key, *json_patterns)

        await self._ttl_manager.set_ttl(key)
        logger.debug(f"存储反向黑名单: {len(patterns)}个模式")

    # ===== 查询方法 =====

    async def get_essence_analysis(
        self,
        strategy_id: str,
    ) -> Optional[Dict[str, Any]]:
        """获取策略本质分析

        Args:
            strategy_id: 策略ID

        Returns:
            分析数据，不存在返回None
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")

        await self._ensure_initialized()
        key = f"{self.KEY_ANALYSIS_ESSENCE}:{strategy_id}"
        data = await self._redis_client.get(key)
        if data:
            return json.loads(data)
        return None

    async def get_risk_assessment(
        self,
        strategy_id: str,
    ) -> Optional[Dict[str, Any]]:
        """获取风险评估

        Args:
            strategy_id: 策略ID

        Returns:
            风险评估数据，不存在返回None
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")

        await self._ensure_initialized()
        key = f"{self.KEY_ANALYSIS_RISK}:{strategy_id}"
        data = await self._redis_client.get(key)
        if data:
            return json.loads(data)
        return None

    async def get_overfitting_detection(
        self,
        strategy_id: str,
    ) -> Optional[Dict[str, Any]]:
        """获取过拟合检测

        Args:
            strategy_id: 策略ID

        Returns:
            过拟合检测数据，不存在返回None
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")

        await self._ensure_initialized()
        key = f"{self.KEY_ANALYSIS_OVERFITTING}:{strategy_id}"
        data = await self._redis_client.get(key)
        if data:
            return json.loads(data)
        return None

    async def get_market_macro(self) -> Optional[Dict[str, Any]]:
        """获取市场宏观分析

        Returns:
            市场宏观分析数据，不存在返回None
        """
        await self._ensure_initialized()
        key = self.KEY_MARKET_MACRO
        data = await self._redis_client.hgetall(key)
        if data:
            return {k: json.loads(v) for k, v in data.items()}
        return None

    async def get_limit_up_data(self, date: str) -> Optional[Dict[str, Any]]:
        """获取涨停板数据

        Args:
            date: 日期（格式：YYYY-MM-DD）

        Returns:
            涨停板数据，不存在返回None
        """
        if not date:
            raise ValueError("日期不能为空")

        await self._ensure_initialized()
        key = f"{self.KEY_MARKET_LIMIT_UP}:{date}"
        data = await self._redis_client.get(key)
        if data:
            return json.loads(data)
        return None

    async def get_smart_money_analysis(
        self,
        symbol: str,
    ) -> Optional[Dict[str, Any]]:
        """获取主力资金深度分析

        Args:
            symbol: 股票代码

        Returns:
            主力资金分析数据，不存在返回None
        """
        if not symbol:
            raise ValueError("股票代码不能为空")

        await self._ensure_initialized()
        key = f"{self.KEY_SMART_MONEY}:{symbol}"
        data = await self._redis_client.get(key)
        if data:
            return json.loads(data)
        return None

    async def get_recommendation(
        self,
        symbol: str,
    ) -> Optional[Dict[str, Any]]:
        """获取个股建议

        Args:
            symbol: 股票代码

        Returns:
            个股建议数据，不存在返回None
        """
        if not symbol:
            raise ValueError("股票代码不能为空")

        await self._ensure_initialized()
        key = f"{self.KEY_RECOMMENDATION}:{symbol}"
        data = await self._redis_client.get(key)
        if data:
            return json.loads(data)
        return None

    async def get_gene_capsule(
        self,
        capsule_id: str,
    ) -> Optional[Dict[str, Any]]:
        """获取基因胶囊

        Args:
            capsule_id: 胶囊ID

        Returns:
            基因胶囊数据，不存在返回None
        """
        if not capsule_id:
            raise ValueError("胶囊ID不能为空")

        await self._ensure_initialized()
        key = f"{self.KEY_KNOWLEDGE_GENE_CAPSULE}:{capsule_id}"
        data = await self._redis_client.get(key)
        if data:
            return json.loads(data)
        return None

    async def get_evolution_tree(self) -> Optional[Dict[str, Any]]:
        """获取演化树

        Returns:
            演化树数据，不存在返回None
        """
        await self._ensure_initialized()
        key = self.KEY_KNOWLEDGE_EVOLUTION_TREE
        data = await self._redis_client.get(key)
        if data:
            return json.loads(data)
        return None

    async def get_elite_strategies(self) -> Set[str]:
        """获取精英策略集合

        Returns:
            精英策略ID集合
        """
        await self._ensure_initialized()
        key = self.KEY_KNOWLEDGE_ELITE_STRATEGIES
        return await self._redis_client.smembers(key)

    async def get_failed_strategies(self) -> Set[str]:
        """获取失败策略集合

        Returns:
            失败策略ID集合
        """
        await self._ensure_initialized()
        key = self.KEY_KNOWLEDGE_FAILED_STRATEGIES
        return await self._redis_client.smembers(key)

    async def get_anti_patterns(self) -> List[Dict[str, Any]]:
        """获取反向黑名单

        Returns:
            反向模式列表
        """
        await self._ensure_initialized()
        key = self.KEY_KNOWLEDGE_ANTI_PATTERNS
        data = await self._redis_client.lrange(key, 0, -1)
        return [json.loads(p) for p in data] if data else []

    # ===== 批量操作 =====

    async def batch_store(
        self,
        items: List[Tuple[str, Dict[str, Any], Optional[int]]],
    ) -> None:
        """批量存储

        Args:
            items: [(key, data, ttl), ...]，ttl为None则自动判断
        """
        if not items:
            return

        await self._ensure_initialized()

        pipe = self._redis_client.pipeline()
        for key, data, ttl in items:
            json_data = json.dumps(data, ensure_ascii=False, default=str)
            actual_ttl = ttl if ttl is not None else self._ttl_manager.get_ttl_for_key(key)
            if actual_ttl == TTLManager.TTL_PERMANENT:
                pipe.set(key, json_data)
            else:
                pipe.set(key, json_data, ex=actual_ttl)

        await pipe.execute()
        logger.debug(f"批量存储: {len(items)}个键")

    async def batch_get(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取

        Args:
            keys: 键列表

        Returns:
            键到数据的字典
        """
        if not keys:
            return {}

        await self._ensure_initialized()

        values = await self._redis_client.mget(*keys)
        result = {}
        for key, value in zip(keys, values):
            if value:
                result[key] = json.loads(value)

        return result

    # ===== 事务操作 =====

    async def execute_transaction(
        self,
        operations: List[Callable],
    ) -> bool:
        """执行事务操作

        Args:
            operations: 操作函数列表，每个函数接受redis客户端作为参数

        Returns:
            是否成功
        """
        if not operations:
            return True

        await self._ensure_initialized()

        try:
            pipe = self._redis_client.pipeline()
            for op in operations:
                await op(pipe)
            await pipe.execute()
            logger.debug(f"事务执行成功: {len(operations)}个操作")
            return True
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"事务执行失败: {e}")
            return False

    # ===== 辅助方法 =====

    async def key_exists(self, key: str) -> bool:
        """检查键是否存在

        Args:
            key: Redis键

        Returns:
            是否存在
        """
        await self._ensure_initialized()
        return await self._redis_client.exists(key)

    async def delete_key(self, key: str) -> bool:
        """删除键

        Args:
            key: Redis键

        Returns:
            是否删除成功
        """
        await self._ensure_initialized()
        result = await self._redis_client.delete(key)
        return result > 0

    async def get_all_gene_capsule_ids(self) -> List[str]:
        """获取所有基因胶囊ID

        Returns:
            胶囊ID列表
        """
        await self._ensure_initialized()

        capsule_ids = []
        cursor = 0
        pattern = f"{self.KEY_KNOWLEDGE_GENE_CAPSULE}:*"

        while True:
            cursor, keys = await self._redis_client.scan(cursor, match=pattern, count=100)
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                capsule_id = key_str.split(":")[-1]
                capsule_ids.append(capsule_id)
            if cursor == 0:
                break

        return capsule_ids

    async def get_gene_capsules_by_family(
        self,
        family_id: str,
    ) -> List[Dict[str, Any]]:
        """按家族ID获取基因胶囊

        Args:
            family_id: 家族ID

        Returns:
            基因胶囊列表
        """
        if not family_id:
            raise ValueError("家族ID不能为空")

        await self._ensure_initialized()

        capsules = []
        capsule_ids = await self.get_all_gene_capsule_ids()

        for capsule_id in capsule_ids:
            capsule = await self.get_gene_capsule(capsule_id)
            if capsule and capsule.get("family_id") == family_id:
                capsules.append(capsule)

        return capsules
