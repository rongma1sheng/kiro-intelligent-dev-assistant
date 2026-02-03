"""记忆表实现 - RAM和SSD存储后端

白皮书依据: 第二章 2.8.1 RAM/SSD记忆表
"""

import mmap
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import numpy as np
from loguru import logger


class MemoryTable(ABC):
    """记忆表抽象基类

    白皮书依据: 第二章 2.8.1 记忆表
    """

    @abstractmethod
    def get(self, address: int) -> Optional[np.ndarray]:
        """获取记忆向量"""

    @abstractmethod
    def set(self, address: int, embedding: np.ndarray) -> None:
        """设置记忆向量"""

    @abstractmethod
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""


class RAMMemoryTable(MemoryTable):
    """RAM记忆表 - 最快访问速度

    白皮书依据: 第二章 2.8.1 RAM记忆表

    核心特性:
    1. O(1)查询和写入
    2. 使用numpy数组存储，支持快速访问
    3. 内存使用统计
    4. 适合小规模记忆（<1亿条）

    Attributes:
        size: 记忆表大小
        embedding_dim: 嵌入向量维度
        memory_table: numpy数组存储记忆向量
        occupied: 标记槽位是否被占用
    """

    def __init__(self, size: int, embedding_dim: int):
        """初始化RAM记忆表

        Args:
            size: 记忆表大小，必须 > 0
            embedding_dim: 嵌入向量维度，必须 > 0

        Raises:
            ValueError: 当size或embedding_dim <= 0时
        """
        if size <= 0:
            raise ValueError(f"记忆表大小必须 > 0，当前: {size}")

        if embedding_dim <= 0:
            raise ValueError(f"嵌入向量维度必须 > 0，当前: {embedding_dim}")

        self.size = size
        self.embedding_dim = embedding_dim

        # 使用numpy数组存储，支持快速访问
        self.memory_table = np.zeros((size, embedding_dim), dtype=np.float32)
        self.occupied = np.zeros(size, dtype=bool)

        # 内存使用统计
        memory_mb = (size * embedding_dim * 4) / (1024 * 1024)  # float32 = 4字节
        logger.info(f"RAM记忆表初始化: {size:,}条记忆, {memory_mb:.1f}MB内存")

    def get(self, address: int) -> Optional[np.ndarray]:
        """获取记忆向量 - O(1)复杂度

        白皮书依据: 第二章 2.8.1 O(1)查询

        Args:
            address: 内存地址

        Returns:
            记忆向量（如果存在）或None

        Raises:
            ValueError: 当address超出范围时
        """
        if not (0 <= address < self.size):  # pylint: disable=superfluous-parens
            raise ValueError(f"地址超出范围: {address}, 有效范围: [0, {self.size})")

        if self.occupied[address]:
            return self.memory_table[address].copy()
        return None

    def set(self, address: int, embedding: np.ndarray) -> None:
        """设置记忆向量 - O(1)复杂度

        白皮书依据: 第二章 2.8.1 O(1)写入

        Args:
            address: 内存地址
            embedding: 记忆向量

        Raises:
            ValueError: 当address超出范围或embedding维度不匹配时
        """
        if not (0 <= address < self.size):  # pylint: disable=superfluous-parens
            raise ValueError(f"地址超出范围: {address}, 有效范围: [0, {self.size})")

        if embedding.shape[0] != self.embedding_dim:
            raise ValueError(f"嵌入向量维度不匹配: 期望{self.embedding_dim}, 实际{embedding.shape[0]}")

        self.memory_table[address] = embedding
        self.occupied[address] = True

    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计

        白皮书依据: 第二章 2.8.1 统计信息收集

        Returns:
            使用统计信息字典
        """
        occupied_count = np.sum(self.occupied)
        usage_rate = occupied_count / self.size
        memory_mb = (self.size * self.embedding_dim * 4) / (1024 * 1024)

        return {
            "total_slots": self.size,
            "occupied_slots": int(occupied_count),
            "usage_rate": usage_rate,
            "memory_mb": memory_mb,
            "backend": "ram",
        }


class SSDMemoryTable(MemoryTable):
    """SSD记忆表 - 更大容量

    白皮书依据: 第二章 2.8.1 SSD记忆表

    核心特性:
    1. 支持更大容量（>1亿条）
    2. 使用内存映射文件（mmap）
    3. 缓存机制提升访问速度
    4. 容量扩展逻辑

    Attributes:
        size: 记忆表大小
        embedding_dim: 嵌入向量维度
        file_path: 存储文件路径
        memory_map: 内存映射对象
        cache: LRU缓存
        cache_size: 缓存大小
    """

    def __init__(
        self, size: int, embedding_dim: int, file_path: str = "data/memory/ssd_memory.bin", cache_size: int = 10000
    ):
        """初始化SSD记忆表

        Args:
            size: 记忆表大小，必须 > 0
            embedding_dim: 嵌入向量维度，必须 > 0
            file_path: 存储文件路径
            cache_size: 缓存大小

        Raises:
            ValueError: 当size或embedding_dim <= 0时
        """
        if size <= 0:
            raise ValueError(f"记忆表大小必须 > 0，当前: {size}")

        if embedding_dim <= 0:
            raise ValueError(f"嵌入向量维度必须 > 0，当前: {embedding_dim}")

        self.size = size
        self.embedding_dim = embedding_dim
        self.file_path = file_path
        self.cache_size = cache_size

        # 创建存储目录
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # 计算文件大小
        # 每条记忆: embedding_dim * 4字节(float32) + 1字节(occupied标志)
        record_size = embedding_dim * 4 + 1
        file_size = size * record_size

        # 创建或打开文件
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            with open(file_path, "wb") as f:
                f.write(b"\x00" * file_size)

        # 打开文件并创建内存映射
        self.file = open(file_path, "r+b")  # pylint: disable=r1732
        try:
            self.memory_map = mmap.mmap(self.file.fileno(), 0)
        except ValueError as e:  # pylint: disable=unused-variable
            # Windows上可能需要显式指定长度
            self.memory_map = mmap.mmap(self.file.fileno(), file_size)

        # 初始化缓存（简单的字典缓存）
        self.cache: Dict[int, np.ndarray] = {}
        self.cache_hits = 0
        self.cache_misses = 0

        # 内存使用统计
        memory_mb = file_size / (1024 * 1024)
        logger.info(f"SSD记忆表初始化: {size:,}条记忆, {memory_mb:.1f}MB存储, 缓存{cache_size}条")

    def get(self, address: int) -> Optional[np.ndarray]:
        """获取记忆向量 - 带缓存的O(1)复杂度

        白皮书依据: 第二章 2.8.1 SSD存储后端

        Args:
            address: 内存地址

        Returns:
            记忆向量（如果存在）或None

        Raises:
            ValueError: 当address超出范围时
        """
        if not (0 <= address < self.size):  # pylint: disable=superfluous-parens
            raise ValueError(f"地址超出范围: {address}, 有效范围: [0, {self.size})")

        # 检查缓存
        if address in self.cache:
            self.cache_hits += 1
            return self.cache[address].copy()

        self.cache_misses += 1

        # 从SSD读取
        record_size = self.embedding_dim * 4 + 1
        offset = address * record_size

        # 读取occupied标志
        self.memory_map.seek(offset)
        occupied = self.memory_map.read(1)[0]

        if not occupied:
            return None

        # 读取嵌入向量
        embedding_bytes = self.memory_map.read(self.embedding_dim * 4)
        embedding = np.frombuffer(embedding_bytes, dtype=np.float32)

        # 更新缓存
        self._update_cache(address, embedding)

        return embedding.copy()

    def set(self, address: int, embedding: np.ndarray) -> None:
        """设置记忆向量 - O(1)复杂度

        白皮书依据: 第二章 2.8.1 SSD存储后端

        Args:
            address: 内存地址
            embedding: 记忆向量

        Raises:
            ValueError: 当address超出范围或embedding维度不匹配时
        """
        if not (0 <= address < self.size):  # pylint: disable=superfluous-parens
            raise ValueError(f"地址超出范围: {address}, 有效范围: [0, {self.size})")

        if embedding.shape[0] != self.embedding_dim:
            raise ValueError(f"嵌入向量维度不匹配: 期望{self.embedding_dim}, 实际{embedding.shape[0]}")

        # 写入SSD
        record_size = self.embedding_dim * 4 + 1
        offset = address * record_size

        self.memory_map.seek(offset)
        self.memory_map.write(b"\x01")  # occupied = True
        self.memory_map.write(embedding.astype(np.float32).tobytes())

        # 更新缓存
        self._update_cache(address, embedding)

    def _update_cache(self, address: int, embedding: np.ndarray) -> None:
        """更新缓存 - LRU策略

        Args:
            address: 内存地址
            embedding: 记忆向量
        """
        # 简单的LRU：如果缓存满了，删除第一个元素
        if len(self.cache) >= self.cache_size and address not in self.cache:
            # 删除第一个键（最旧的）
            first_key = next(iter(self.cache))
            del self.cache[first_key]

        self.cache[address] = embedding.copy()

    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计

        白皮书依据: 第二章 2.8.1 统计信息收集

        Returns:
            使用统计信息字典
        """
        # 扫描occupied标志（采样方式，避免全扫描）
        sample_size = min(10000, self.size)
        sample_step = max(1, self.size // sample_size)

        occupied_count = 0
        for i in range(0, self.size, sample_step):
            record_size = self.embedding_dim * 4 + 1
            offset = i * record_size
            self.memory_map.seek(offset)
            occupied = self.memory_map.read(1)[0]
            if occupied:
                occupied_count += 1

        # 估算总占用数
        estimated_occupied = occupied_count * sample_step
        usage_rate = estimated_occupied / self.size

        # 文件大小
        file_size_mb = os.path.getsize(self.file_path) / (1024 * 1024)

        # 缓存命中率
        total_cache_queries = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / max(total_cache_queries, 1)

        return {
            "total_slots": self.size,
            "occupied_slots": estimated_occupied,
            "usage_rate": usage_rate,
            "file_size_mb": file_size_mb,
            "backend": "ssd",
            "cache_size": len(self.cache),
            "cache_hit_rate": cache_hit_rate,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
        }

    def __del__(self):
        """清理资源"""
        if hasattr(self, "memory_map"):
            self.memory_map.close()
        if hasattr(self, "file"):
            self.file.close()
