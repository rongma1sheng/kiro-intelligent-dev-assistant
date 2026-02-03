"""确定性哈希路由器

白皮书依据: 第二章 2.8.1 确定性哈希路由
"""

import hashlib
from typing import List

from loguru import logger


class DeterministicHashRouter:
    """确定性哈希路由器

    白皮书依据: 第二章 2.8.1 确定性哈希路由
    技术特点: 无需训练的路由网络，O(1)定位

    核心功能:
    1. 使用SHA256哈希函数确保分布均匀
    2. 确定性映射：相同输入总是得到相同地址
    3. O(1)时间复杂度
    4. 支持哈希分布均匀性验证

    Attributes:
        memory_size: 记忆表大小
        hash_function: 哈希函数（默认SHA256）
    """

    def __init__(self, memory_size: int):
        """初始化哈希路由器

        Args:
            memory_size: 记忆表大小，必须 > 0

        Raises:
            ValueError: 当memory_size <= 0时
        """
        if memory_size <= 0:
            raise ValueError(f"记忆表大小必须 > 0，当前: {memory_size}")

        self.memory_size = memory_size
        self.hash_function = hashlib.sha256

        logger.info(f"初始化DeterministicHashRouter: memory_size={memory_size:,}")

    def hash(self, ngram: str) -> int:
        """确定性哈希函数

        白皮书依据: 第二章 2.8.1 确定性哈希路由

        使用SHA256确保分布均匀，O(1)时间复杂度

        Args:
            ngram: N-gram字符串

        Returns:
            内存地址 (0 到 memory_size-1)

        Raises:
            ValueError: 当ngram为空时
        """
        if not ngram:
            raise ValueError("N-gram不能为空")

        # 使用SHA256确保分布均匀
        hash_bytes = self.hash_function(ngram.encode("utf-8")).digest()

        # 转换为整数并取模
        hash_int = int.from_bytes(hash_bytes[:8], byteorder="big")
        memory_address = hash_int % self.memory_size

        return memory_address

    def hash_batch(self, ngrams: List[str]) -> List[int]:
        """批量哈希

        Args:
            ngrams: N-gram字符串列表

        Returns:
            内存地址列表
        """
        return [self.hash(ngram) for ngram in ngrams]

    def verify_distribution(self, sample_ngrams: List[str]) -> dict:
        """验证哈希分布均匀性

        白皮书依据: 第二章 2.8.1 哈希分布均匀性验证

        Args:
            sample_ngrams: 样本N-gram列表

        Returns:
            分布统计信息
        """
        if not sample_ngrams:
            raise ValueError("样本N-gram列表不能为空")

        # 计算所有哈希值
        hash_values = self.hash_batch(sample_ngrams)

        # 统计分布
        bucket_size = max(1, self.memory_size // 100)  # 分成100个桶
        buckets = [0] * 100

        for hash_val in hash_values:
            bucket_idx = min(99, hash_val // bucket_size)
            buckets[bucket_idx] += 1

        # 计算统计指标
        avg_count = len(sample_ngrams) / 100
        variance = sum((count - avg_count) ** 2 for count in buckets) / 100
        std_dev = variance**0.5

        # 计算均匀性系数（0-1，越接近1越均匀）
        uniformity = 1.0 - (std_dev / avg_count) if avg_count > 0 else 0.0

        return {
            "sample_size": len(sample_ngrams),
            "unique_addresses": len(set(hash_values)),
            "collision_rate": 1.0 - len(set(hash_values)) / len(sample_ngrams),
            "uniformity": uniformity,
            "avg_per_bucket": avg_count,
            "std_dev": std_dev,
        }
