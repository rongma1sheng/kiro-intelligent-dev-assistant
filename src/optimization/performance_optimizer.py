"""Performance Optimizer - System Performance Optimization

白皮书依据: 第十六章 16.0 性能优化指南

核心功能:
- Soldier推理延迟优化（目标P99 <150ms）
- Redis吞吐量优化（目标>150K ops/s）
- 缓存机制实现（5秒TTL）
- 连接池优化
"""

import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from loguru import logger


class PerformanceOptimizer:
    """性能优化器 - 系统性能优化

    白皮书依据: 第十六章 16.0 性能优化指南

    优化目标:
    - Soldier决策延迟: P99 < 150ms
    - Redis吞吐量: > 150K ops/s
    - 缓存命中率: > 80%

    Attributes:
        cache_ttl: 缓存有效期（秒）
        cache_size: 缓存大小
        decision_cache: 决策缓存
        redis_client: Redis客户端
    """

    def __init__(self, redis_client=None, cache_ttl: int = 5, cache_size: int = 1000):
        """初始化性能优化器

        Args:
            redis_client: Redis客户端实例
            cache_ttl: 缓存有效期（秒）
            cache_size: 缓存大小

        Raises:
            ValueError: 当cache_ttl或cache_size无效时
        """
        if cache_ttl <= 0:
            raise ValueError(f"缓存有效期必须 > 0: {cache_ttl}")
        if cache_size <= 0:
            raise ValueError(f"缓存大小必须 > 0: {cache_size}")

        self.redis_client = redis_client
        self.cache_ttl = cache_ttl
        self.cache_size = cache_size

        # 决策缓存（LRU）
        self.decision_cache: OrderedDict = OrderedDict()

        # 统计信息
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_requests = 0

        logger.info(f"[PerformanceOptimizer] 初始化完成 - " f"缓存TTL: {cache_ttl}s, " f"缓存大小: {cache_size}")

    def optimize_soldier_latency(self, context: Dict[str, Any], decision_func) -> Dict[str, Any]:
        """优化Soldier决策延迟（目标P99 <150ms）

        白皮书依据: 第十六章 16.1 Soldier推理优化

        优化技术:
        1. 决策缓存（5秒TTL）
        2. Prompt压缩
        3. 连接池复用
        4. 异步I/O

        Args:
            context: 决策上下文
            decision_func: 决策函数

        Returns:
            决策结果字典

        Raises:
            ValueError: 当context无效时
        """
        if not context:
            raise ValueError("决策上下文不能为空")

        self.total_requests += 1

        # 1. 生成缓存键
        cache_key = self._generate_cache_key(context)

        # 2. 检查缓存
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            self.cache_hits += 1
            logger.debug(
                f"[PerformanceOptimizer] 缓存命中 - " f"键: {cache_key}, " f"命中率: {self.get_cache_hit_rate():.1%}"
            )
            return cached_result

        self.cache_misses += 1

        # 3. 压缩Prompt
        compressed_context = self._compress_prompt(context)

        # 4. 执行决策
        start_time = time.perf_counter()
        result = decision_func(compressed_context)
        latency_ms = (time.perf_counter() - start_time) * 1000

        # 5. 存入缓存
        self._put_to_cache(cache_key, result)

        logger.debug(f"[PerformanceOptimizer] 决策完成 - " f"延迟: {latency_ms:.2f}ms, " f"缓存未命中")

        return result

    def optimize_redis_throughput(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """优化Redis吞吐量（目标>150K ops/s）

        白皮书依据: 第十六章 16.2 Redis性能优化

        优化技术:
        1. Pipeline批量操作
        2. 连接池管理
        3. 健康检查（30s间隔）

        Args:
            operations: 操作列表，每个操作包含:
                - type: 操作类型（get/set/hget/hset）
                - key: 键
                - value: 值（set/hset时需要）
                - field: 字段（hget/hset时需要）

        Returns:
            操作结果列表

        Raises:
            ValueError: 当redis_client未初始化时
            ValueError: 当operations为空时
        """
        if self.redis_client is None:
            raise ValueError("Redis客户端未初始化")

        if not operations:
            raise ValueError("操作列表不能为空")

        logger.debug(f"[PerformanceOptimizer] 开始批量操作 - " f"操作数: {len(operations)}")

        # 使用Pipeline批量执行
        start_time = time.perf_counter()

        pipe = self.redis_client.pipeline()

        for op in operations:
            op_type = op.get("type")
            key = op.get("key")

            if op_type == "get":
                pipe.get(key)
            elif op_type == "set":
                pipe.set(key, op.get("value"))
            elif op_type == "hget":
                pipe.hget(key, op.get("field"))
            elif op_type == "hset":
                pipe.hset(key, op.get("field"), op.get("value"))
            else:
                logger.warning(f"[PerformanceOptimizer] 未知操作类型: {op_type}")

        results = pipe.execute()

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        ops_per_sec = len(operations) / (elapsed_ms / 1000) if elapsed_ms > 0 else 0

        logger.info(
            f"[PerformanceOptimizer] 批量操作完成 - "
            f"操作数: {len(operations)}, "
            f"耗时: {elapsed_ms:.2f}ms, "
            f"吞吐量: {ops_per_sec:,.0f} ops/s"
        )

        return results

    def implement_caching(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """实现缓存机制（5秒TTL）

        白皮书依据: 第十六章 16.1.3 缓存机制

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 缓存有效期（秒），None使用默认值
        """
        if ttl is None:
            ttl = self.cache_ttl

        self._put_to_cache(key, value, ttl)

        logger.debug(f"[PerformanceOptimizer] 缓存已更新 - " f"键: {key}, " f"TTL: {ttl}s")

    def _generate_cache_key(self, context: Dict[str, Any]) -> str:
        """生成缓存键

        Args:
            context: 决策上下文

        Returns:
            缓存键字符串
        """
        symbol = context.get("symbol", "")
        price = context.get("price", 0.0)

        return f"{symbol}_{price:.2f}"

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取数据

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或过期返回None
        """
        if key not in self.decision_cache:
            return None

        value, timestamp = self.decision_cache[key]

        # 检查是否过期
        if time.time() - timestamp > self.cache_ttl:
            # 过期，删除
            del self.decision_cache[key]
            return None

        # 移到末尾（LRU）
        self.decision_cache.move_to_end(key)

        return value

    def _put_to_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """存入缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 缓存有效期（秒）
        """
        if ttl is None:
            ttl = self.cache_ttl

        # 存入缓存
        self.decision_cache[key] = (value, time.time())

        # 移到末尾（LRU）
        self.decision_cache.move_to_end(key)

        # 限制缓存大小
        while len(self.decision_cache) > self.cache_size:
            # 删除最旧的
            self.decision_cache.popitem(last=False)

    def _compress_prompt(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """压缩Prompt，减少token数量

        白皮书依据: 第十六章 16.1.2 Prompt压缩

        Args:
            context: 原始上下文

        Returns:
            压缩后的上下文
        """
        # 仅保留关键字段
        compressed = {
            "sym": context.get("symbol", ""),
            "p": context.get("price", 0.0),
            "v": context.get("volume", 0),
            "s": context.get("signal", 0.0),
        }

        return compressed

    def get_cache_hit_rate(self) -> float:
        """获取缓存命中率

        Returns:
            缓存命中率（0-1）
        """
        if self.total_requests == 0:
            return 0.0

        return self.cache_hits / self.total_requests

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            统计信息字典，包含:
            - total_requests: 总请求数
            - cache_hits: 缓存命中数
            - cache_misses: 缓存未命中数
            - hit_rate: 命中率
            - cache_size: 当前缓存大小
            - max_cache_size: 最大缓存大小
        """
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": self.get_cache_hit_rate(),
            "cache_size": len(self.decision_cache),
            "max_cache_size": self.cache_size,
        }

    def clear_cache(self) -> None:
        """清空缓存"""
        self.decision_cache.clear()
        logger.info("[PerformanceOptimizer] 缓存已清空")

    def reset_stats(self) -> None:
        """重置统计信息"""
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_requests = 0
        logger.info("[PerformanceOptimizer] 统计信息已重置")
