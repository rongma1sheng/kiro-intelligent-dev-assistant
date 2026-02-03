"""Engram记忆核心实现

白皮书依据: 第二章 2.8.1 Engram记忆模块
"""

from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger

from src.brain.memory.data_models import MemoryStatistics
from src.brain.memory.hash_router import DeterministicHashRouter
from src.brain.memory.memory_table import MemoryTable, RAMMemoryTable, SSDMemoryTable


class EngramMemory:
    """Engram记忆模块 - 存算解耦的O(1)记忆系统

    白皮书依据: 第二章 2.8.1 Engram记忆模块
    技术原理: DeepSeek Engram - 哈希N-gram + 嵌入向量

    核心优势:
    1. O(1)查找复杂度 - 无论知识库多大，查找速度恒定
    2. 存算解耦 - 记忆存储在RAM/SSD，不占用GPU显存
    3. 即插即用 - 独立模块，不参与神经网络训练
    4. 无限扩展 - 知识库大小不受GPU显存限制

    Attributes:
        ngram_size: N-gram大小
        embedding_dim: 嵌入向量维度
        memory_size: 记忆表大小
        storage_backend: 存储后端（'ram'或'ssd'）
        hash_router: 确定性哈希路由器
        memory_table: 记忆表
        hit_count: 命中次数
        miss_count: 未命中次数
        total_queries: 总查询次数
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        ngram_size: int = 4,
        embedding_dim: int = 512,
        memory_size: int = 100_000_000,  # 1亿条记忆
        storage_backend: str = "ram",  # 'ram' 或 'ssd'
        enable_cache: bool = True,  # 启用查询缓存
        cache_size: int = 10000,
    ):  # 缓存大小
        """初始化Engram记忆模块

        Args:
            ngram_size: N-gram大小，必须 > 0
            embedding_dim: 嵌入向量维度，必须 > 0
            memory_size: 记忆表大小，必须 > 0
            storage_backend: 存储后端，'ram'或'ssd'
            enable_cache: 是否启用查询缓存
            cache_size: 缓存大小（LRU缓存）

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if ngram_size <= 0:
            raise ValueError(f"N-gram大小必须 > 0，当前: {ngram_size}")

        if embedding_dim <= 0:
            raise ValueError(f"嵌入向量维度必须 > 0，当前: {embedding_dim}")

        if memory_size <= 0:
            raise ValueError(f"记忆表大小必须 > 0，当前: {memory_size}")

        if storage_backend not in ["ram", "ssd"]:
            raise ValueError(f"不支持的存储后端: {storage_backend}，支持: 'ram', 'ssd'")

        if cache_size <= 0:
            raise ValueError(f"缓存大小必须 > 0，当前: {cache_size}")

        self.ngram_size = ngram_size
        self.embedding_dim = embedding_dim
        self.memory_size = memory_size
        self.storage_backend = storage_backend
        self.enable_cache = enable_cache
        self.cache_size = cache_size

        # 核心组件
        self.hash_router = DeterministicHashRouter(memory_size)
        self.memory_table = self._init_memory_table()

        # 查询缓存（LRU）
        self._query_cache: Dict[str, Optional[np.ndarray]] = {}
        self._cache_access_order: List[str] = []

        # 统计信息
        self.hit_count = 0
        self.miss_count = 0
        self.total_queries = 0
        self.cache_hits = 0
        self.cache_misses = 0

        logger.info(
            f"Engram记忆模块初始化: "
            f"ngram_size={ngram_size}, "
            f"embedding_dim={embedding_dim}, "
            f"memory_size={memory_size:,}, "
            f"storage_backend={storage_backend}, "
            f"cache_enabled={enable_cache}, "
            f"cache_size={cache_size}"
        )

    def _init_memory_table(self) -> MemoryTable:
        """初始化记忆表

        白皮书依据: 第二章 2.8.1 存储后端选择逻辑

        Returns:
            记忆表实例
        """
        if self.storage_backend == "ram":  # pylint: disable=no-else-return
            # RAM存储 - 最快访问速度
            return RAMMemoryTable(self.memory_size, self.embedding_dim)
        elif self.storage_backend == "ssd":
            # SSD存储 - 更大容量
            return SSDMemoryTable(self.memory_size, self.embedding_dim)
        else:
            raise ValueError(f"不支持的存储后端: {self.storage_backend}")

    def query_memory(self, text: str, context: Optional[List[str]] = None) -> Optional[np.ndarray]:
        """O(1)记忆查询

        白皮书依据: 第二章 2.8.1 记忆查询功能

        核心流程:
        1. 检查查询缓存 - O(1)
        2. 提取N-gram特征 - O(n)，n为文本长度
        3. 确定性哈希路由 - O(1)复杂度
        4. 并行查找记忆向量 - O(1)
        5. 融合多个记忆向量 - O(k)，k为N-gram数量

        性能优化:
        1. LRU缓存 - 避免重复查询
        2. 向量化操作 - 加速N-gram提取
        3. 批量查找 - 减少内存访问次数

        Args:
            text: 查询文本
            context: 上下文信息

        Returns:
            记忆向量（如果找到）或None

        Raises:
            ValueError: 当text为空时
        """
        if not text:
            raise ValueError("查询文本不能为空")

        self.total_queries += 1

        # 1. 检查查询缓存
        if self.enable_cache:
            cache_key = self._get_cache_key(text, context)
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                self.cache_hits += 1
                logger.debug(f"缓存命中: text='{text[:50]}...'")
                return cached_result if isinstance(cached_result, np.ndarray) else None
            self.cache_misses += 1

        # 2. 提取N-gram特征（向量化操作）
        ngrams = self._extract_ngrams_optimized(text, context)

        if not ngrams:
            logger.warning(f"未能提取N-gram特征: text='{text[:50]}...'")
            self.miss_count += 1
            if self.enable_cache:
                self._put_to_cache(cache_key, None)
            return None

        # 3. 确定性哈希路由 - O(1)复杂度（批量处理）
        memory_addresses = self._batch_hash(ngrams)

        # 4. 并行查找记忆向量（批量查找）
        memory_vectors = self._batch_lookup(memory_addresses)

        # 5. 融合多个记忆向量
        if memory_vectors:  # pylint: disable=no-else-return
            fused_memory = self._fuse_memory_vectors_optimized(memory_vectors)
            logger.debug(f"记忆查询成功: {len(memory_vectors)}/{len(ngrams)}个N-gram命中")
            if self.enable_cache:
                self._put_to_cache(cache_key, fused_memory)
            return fused_memory
        else:
            logger.debug(f"记忆查询失败: 0/{len(ngrams)}个N-gram命中")
            if self.enable_cache:
                self._put_to_cache(cache_key, None)
            return None

    def _get_cache_key(self, text: str, context: Optional[List[str]]) -> str:
        """生成缓存键

        Args:
            text: 查询文本
            context: 上下文

        Returns:
            缓存键
        """
        if context:
            return f"{text}|{'|'.join(context[-3:])}"
        return text

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取结果

        Args:
            key: 缓存键

        Returns:
            缓存的结果或None
        """
        if key in self._query_cache:
            # 更新访问顺序（LRU）
            if key in self._cache_access_order:
                self._cache_access_order.remove(key)
            self._cache_access_order.append(key)
            return self._query_cache[key]
        return None

    def _put_to_cache(self, key: str, value: Optional[np.ndarray]) -> None:
        """将结果放入缓存

        Args:
            key: 缓存键
            value: 缓存值
        """
        # LRU淘汰
        if len(self._query_cache) >= self.cache_size:
            # 移除最久未使用的项
            if self._cache_access_order:
                oldest_key = self._cache_access_order.pop(0)
                del self._query_cache[oldest_key]

        self._query_cache[key] = value
        self._cache_access_order.append(key)

    def _extract_ngrams_optimized(self, text: str, context: Optional[List[str]] = None) -> List[str]:
        """提取N-gram特征（优化版本）

        性能优化:
        1. 避免不必要的字符串拼接
        2. 使用列表推导式
        3. 预分配内存

        Args:
            text: 文本内容
            context: 上下文信息

        Returns:
            N-gram列表
        """
        # 构建完整文本
        if context:
            # 最近3句上下文
            full_text = " ".join(context[-3:] + [text])
        else:
            full_text = text

        # 分词（优化版本）
        tokens = full_text.strip().split()
        tokens = [t for t in tokens if t]  # 过滤空token

        if len(tokens) < self.ngram_size:
            # 如果token数量不足，返回整个文本作为一个N-gram
            return [" ".join(tokens)] if tokens else []

        # 生成N-gram（使用列表推导式）
        ngrams = [" ".join(tokens[i : i + self.ngram_size]) for i in range(len(tokens) - self.ngram_size + 1)]

        return ngrams

    def _batch_hash(self, ngrams: List[str]) -> List[int]:
        """批量哈希N-grams

        性能优化: 批量处理，减少函数调用开销

        Args:
            ngrams: N-gram列表

        Returns:
            哈希地址列表
        """
        return [self.hash_router.hash(ngram) for ngram in ngrams]

    def _batch_lookup(self, addresses: List[int]) -> List[np.ndarray]:
        """批量查找记忆向量

        性能优化: 批量查找，减少内存访问次数

        Args:
            addresses: 内存地址列表

        Returns:
            记忆向量列表
        """
        memory_vectors = []
        for addr in addresses:
            vector = self.memory_table.get(addr)
            if vector is not None:
                memory_vectors.append(vector)
                self.hit_count += 1
            else:
                self.miss_count += 1
        return memory_vectors

    def _fuse_memory_vectors_optimized(self, vectors: List[np.ndarray]) -> np.ndarray:
        """融合多个记忆向量（优化版本）

        性能优化: 使用numpy向量化操作

        Args:
            vectors: 记忆向量列表

        Returns:
            融合后的记忆向量
        """
        if len(vectors) == 1:
            return vectors[0]

        # 使用numpy的mean函数（向量化操作）
        fused = np.mean(vectors, axis=0)

        return fused

    def store_memory(self, text: str, context: List[str], embedding: np.ndarray) -> None:
        """存储记忆

        白皮书依据: 第二章 2.8.1 记忆存储功能

        核心流程:
        1. 提取N-gram特征
        2. 为每个N-gram计算哈希地址
        3. 存储到记忆表

        Args:
            text: 文本内容
            context: 上下文
            embedding: 记忆向量

        Raises:
            ValueError: 当text为空或embedding维度不匹配时
        """
        if not text:
            raise ValueError("文本内容不能为空")

        if embedding.shape[0] != self.embedding_dim:
            raise ValueError(f"嵌入向量维度不匹配: 期望{self.embedding_dim}, 实际{embedding.shape[0]}")

        # 1. 提取N-gram特征
        ngrams = self._extract_ngrams(text, context)

        if not ngrams:
            logger.warning(f"未能提取N-gram特征，跳过存储: text='{text[:50]}...'")
            return

        # 2. 为每个N-gram存储记忆
        stored_count = 0
        for ngram in ngrams:
            try:
                hash_value = self.hash_router.hash(ngram)

                # 3. 存储到记忆表
                self.memory_table.set(hash_value, embedding)
                stored_count += 1

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"存储记忆失败: ngram='{ngram}', 错误: {e}")

        logger.debug(
            f"存储记忆: {stored_count}/{len(ngrams)}个N-gram, "
            f"哈希地址示例: {[self.hash_router.hash(ng) for ng in ngrams[:3]]}"
        )

    def _extract_ngrams(self, text: str, context: Optional[List[str]] = None) -> List[str]:
        """提取N-gram特征

        白皮书依据: 第二章 2.8.1 N-gram特征提取

        Args:
            text: 文本内容
            context: 上下文信息

        Returns:
            N-gram列表
        """
        # 构建完整文本
        full_text = text
        if context:
            # 最近3句上下文
            full_text = " ".join(context[-3:]) + " " + text

        # 分词
        tokens = self._tokenize(full_text)

        if len(tokens) < self.ngram_size:
            # 如果token数量不足，返回整个文本作为一个N-gram
            return [" ".join(tokens)] if tokens else []

        # 生成N-gram
        ngrams = []
        for i in range(len(tokens) - self.ngram_size + 1):
            ngram = " ".join(tokens[i : i + self.ngram_size])
            ngrams.append(ngram)

        return ngrams

    def _tokenize(self, text: str) -> List[str]:
        """分词

        简单的空格分词，实际应用中可以使用更复杂的分词器

        Args:
            text: 文本内容

        Returns:
            token列表
        """
        # 简单的空格分词
        tokens = text.strip().split()

        # 过滤空token
        tokens = [t for t in tokens if t]

        return tokens

    def _fuse_memory_vectors(self, vectors: List[np.ndarray]) -> np.ndarray:
        """融合多个记忆向量

        白皮书依据: 第二章 2.8.1 记忆向量融合

        Args:
            vectors: 记忆向量列表

        Returns:
            融合后的记忆向量
        """
        if len(vectors) == 1:
            return vectors[0]

        # 加权平均（可以改为注意力机制）
        weights = np.array([1.0 / len(vectors)] * len(vectors))
        fused = np.average(vectors, axis=0, weights=weights)

        return fused

    def get_statistics(self) -> MemoryStatistics:
        """获取统计信息

        白皮书依据: 第二章 2.8.1 统计信息收集

        Returns:
            记忆系统统计信息
        """
        hit_rate = self.hit_count / max(self.total_queries, 1)
        cache_hit_rate = self.cache_hits / max(self.total_queries, 1) if self.enable_cache else 0.0
        memory_usage = self.memory_table.get_usage_stats()

        stats = MemoryStatistics(
            total_queries=self.total_queries,
            hit_count=self.hit_count,
            miss_count=self.miss_count,
            hit_rate=hit_rate,
            memory_usage=memory_usage,
            total_slots=memory_usage.get("total_slots", 0),
            occupied_slots=memory_usage.get("occupied_slots", 0),
            usage_rate=memory_usage.get("usage_rate", 0.0),
        )

        # 添加缓存统计
        if self.enable_cache:
            stats.cache_hits = self.cache_hits
            stats.cache_misses = self.cache_misses
            stats.cache_hit_rate = cache_hit_rate
            stats.cache_size = len(self._query_cache)
            stats.cache_capacity = self.cache_size

        return stats
