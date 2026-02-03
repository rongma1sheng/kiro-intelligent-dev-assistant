"""
AI三脑缓存管理器 - vLLM协同版

白皮书依据: 第二章 2.1-2.3 AI三脑系统 + vLLM内存池协同
需求: 7.4 - 缓存优化（与vLLM协同）

核心功能:
- LRU缓存策略（最大1000项 for Commander, 500项 for Scholar）
- 与vLLM KV Cache协同管理
- 缓存预热机制
- 缓存统计（命中率、大小）
- 自动过期和清理
"""

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class CacheEntry:
    """缓存条目

    Attributes:
        key: 缓存键
        value: 缓存值
        created_at: 创建时间
        last_accessed: 最后访问时间
        access_count: 访问次数
        size_bytes: 估算的大小（字节）
        importance: 重要性评分（0-1）
    """

    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    size_bytes: int = 0
    importance: float = 0.5

    def update_access(self):
        """更新访问信息"""
        self.last_accessed = time.time()
        self.access_count += 1
        # 根据访问频率提升重要性
        self.importance = min(1.0, self.importance + 0.01)


class LRUCache:
    """LRU缓存实现 - vLLM协同版

    白皮书依据: 第二章 2.1-2.3 AI三脑系统 + vLLM内存池协同
    需求: 7.4 - 缓存优化

    核心特性:
    - LRU淘汰策略
    - TTL过期机制
    - 缓存统计
    - vLLM KV Cache协同
    - 缓存预热

    Performance:
        查询延迟: < 1ms
        命中率目标: > 30%
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: float = 300.0, vllm_memory_pool: Optional[Any] = None):
        """初始化LRU缓存

        Args:
            max_size: 最大缓存项数
            ttl_seconds: 缓存过期时间（秒）
            vllm_memory_pool: vLLM内存池（用于协同管理）
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.vllm_memory_pool = vllm_memory_pool

        # 使用OrderedDict实现LRU
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # 统计信息
        self.stats = {"hits": 0, "misses": 0, "evictions": 0, "expirations": 0, "total_size_bytes": 0}

        logger.info(f"LRUCache初始化: max_size={max_size}, ttl={ttl_seconds}s")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在或过期时返回None
        """
        if key not in self._cache:
            self.stats["misses"] += 1
            return None

        entry = self._cache[key]

        # 检查是否过期
        if self._is_expired(entry):
            self._remove_entry(key)
            self.stats["misses"] += 1
            self.stats["expirations"] += 1
            return None

        # 更新访问信息
        entry.update_access()

        # 移到末尾（最近使用）
        self._cache.move_to_end(key)

        self.stats["hits"] += 1
        return entry.value

    def put(self, key: str, value: Any, importance: float = 0.5):
        """存储缓存值

        Args:
            key: 缓存键
            value: 缓存值
            importance: 重要性评分（0-1）
        """
        # 估算大小
        size_bytes = self._estimate_size(value)

        # 如果键已存在，更新
        if key in self._cache:
            old_entry = self._cache[key]
            self.stats["total_size_bytes"] -= old_entry.size_bytes
            self._cache.pop(key)

        # 创建新条目
        entry = CacheEntry(key=key, value=value, size_bytes=size_bytes, importance=importance)

        # 添加到缓存
        self._cache[key] = entry
        self.stats["total_size_bytes"] += size_bytes

        # 检查大小限制
        self._enforce_size_limit()

        # 如果有vLLM内存池，同步存储KV Cache
        if self.vllm_memory_pool:
            self._sync_to_vllm(key, value, importance)

    def remove(self, key: str) -> bool:
        """移除缓存项

        Args:
            key: 缓存键

        Returns:
            是否移除成功
        """
        if key not in self._cache:
            return False

        self._remove_entry(key)
        return True

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self.stats["total_size_bytes"] = 0
        logger.info("缓存已清空")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            统计信息字典
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / max(total_requests, 1)

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": hit_rate,
            "evictions": self.stats["evictions"],
            "expirations": self.stats["expirations"],
            "total_size_bytes": self.stats["total_size_bytes"],
            "avg_size_bytes": self.stats["total_size_bytes"] / max(len(self._cache), 1),
        }

    def warmup(self, keys_values: List[Tuple[str, Any, float]]):
        """缓存预热

        Args:
            keys_values: (key, value, importance)元组列表
        """
        logger.info(f"开始缓存预热: {len(keys_values)}项")

        for key, value, importance in keys_values:
            self.put(key, value, importance)

        logger.info(f"缓存预热完成: 当前大小={len(self._cache)}")

    def _is_expired(self, entry: CacheEntry) -> bool:
        """检查缓存项是否过期

        Args:
            entry: 缓存条目

        Returns:
            是否过期
        """
        age = time.time() - entry.created_at
        return age > self.ttl_seconds

    def _remove_entry(self, key: str):
        """移除缓存条目

        Args:
            key: 缓存键
        """
        if key in self._cache:
            entry = self._cache.pop(key)
            self.stats["total_size_bytes"] -= entry.size_bytes

    def _enforce_size_limit(self):
        """强制执行大小限制（LRU淘汰）"""
        while len(self._cache) > self.max_size:
            # 移除最旧的项（OrderedDict的第一项）
            oldest_key = next(iter(self._cache))
            self._remove_entry(oldest_key)
            self.stats["evictions"] += 1

    def _estimate_size(self, value: Any) -> int:
        """估算值的大小

        Args:
            value: 缓存值

        Returns:
            估算的字节数
        """
        try:
            # 简化的大小估算
            if isinstance(value, str):  # pylint: disable=no-else-return
                return len(value.encode("utf-8"))
            elif isinstance(value, (int, float)):
                return 8
            elif isinstance(value, dict):
                return len(str(value))
            elif isinstance(value, list):
                return len(str(value))
            else:
                return len(str(value))
        except Exception:  # pylint: disable=broad-exception-caught
            return 1024  # 默认1KB

    def _sync_to_vllm(self, key: str, value: Any, importance: float):
        """同步到vLLM内存池

        Args:
            key: 缓存键
            value: 缓存值
            importance: 重要性评分
        """
        try:
            if hasattr(self.vllm_memory_pool, "store_kv_cache"):
                # 异步存储到vLLM KV Cache
                import asyncio  # pylint: disable=import-outside-toplevel

                # 如果有事件循环，使用异步
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(
                            self.vllm_memory_pool.store_kv_cache(
                                cache_key=key, kv_data={"value": value}, importance=importance
                            )
                        )
                    else:
                        # 同步执行
                        loop.run_until_complete(
                            self.vllm_memory_pool.store_kv_cache(
                                cache_key=key, kv_data={"value": value}, importance=importance
                            )
                        )
                except RuntimeError:
                    # 没有事件循环，跳过
                    pass

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"同步到vLLM失败: {e}")


class CacheManager:
    """缓存管理器 - 统一管理AI三脑的缓存

    白皮书依据: 第二章 2.1-2.3 AI三脑系统
    需求: 7.4 - 缓存优化

    为Commander、Scholar、Soldier提供统一的缓存管理服务
    """

    def __init__(self, vllm_memory_pool: Optional[Any] = None):
        """初始化缓存管理器

        Args:
            vllm_memory_pool: vLLM内存池（用于协同管理）
        """
        self.vllm_memory_pool = vllm_memory_pool

        # 为不同的AI脑创建独立的缓存
        self.commander_cache = LRUCache(max_size=1000, ttl_seconds=300.0, vllm_memory_pool=vllm_memory_pool)  # 5分钟

        self.scholar_cache = LRUCache(max_size=500, ttl_seconds=3600.0, vllm_memory_pool=vllm_memory_pool)  # 1小时

        self.soldier_cache = LRUCache(max_size=2000, ttl_seconds=5.0, vllm_memory_pool=vllm_memory_pool)  # 5秒

        logger.info("CacheManager初始化完成")

    def get_cache(self, brain_type: str) -> LRUCache:
        """获取指定AI脑的缓存

        Args:
            brain_type: AI脑类型（'commander', 'scholar', 'soldier'）

        Returns:
            对应的LRU缓存

        Raises:
            ValueError: 当brain_type无效时
        """
        if brain_type == "commander":  # pylint: disable=no-else-return
            return self.commander_cache
        elif brain_type == "scholar":
            return self.scholar_cache
        elif brain_type == "soldier":
            return self.soldier_cache
        else:
            raise ValueError(f"无效的brain_type: {brain_type}")

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有缓存的统计信息

        Returns:
            所有缓存的统计信息
        """
        return {
            "commander": self.commander_cache.get_stats(),
            "scholar": self.scholar_cache.get_stats(),
            "soldier": self.soldier_cache.get_stats(),
        }

    def clear_all(self):
        """清空所有缓存"""
        self.commander_cache.clear()
        self.scholar_cache.clear()
        self.soldier_cache.clear()
        logger.info("所有缓存已清空")
