"""记忆系统数据模型

白皮书依据: 第二章 2.8 统一记忆系统
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class MemoryQuery:
    """记忆查询请求

    白皮书依据: 第二章 2.8.1 Engram记忆模块

    Attributes:
        text: 查询文本
        context: 上下文信息列表
        max_results: 最大返回结果数
    """

    text: str
    context: Optional[List[str]] = None
    max_results: int = 1


@dataclass
class MemoryRecord:
    """记忆记录

    白皮书依据: 第二章 2.8.1 Engram记忆模块

    Attributes:
        text: 记忆文本内容
        context: 上下文信息
        embedding: 记忆向量
        metadata: 元数据（时间戳、来源等）
    """

    text: str
    context: List[str]
    embedding: np.ndarray
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MemoryStatistics:
    """记忆系统统计信息

    白皮书依据: 第二章 2.8.1 Engram记忆模块

    Attributes:
        total_queries: 总查询次数
        hit_count: 命中次数
        miss_count: 未命中次数
        hit_rate: 命中率
        memory_usage: 内存使用情况
        total_slots: 总槽位数
        occupied_slots: 已占用槽位数
        usage_rate: 使用率
        cache_hits: 缓存命中次数（可选）
        cache_misses: 缓存未命中次数（可选）
        cache_hit_rate: 缓存命中率（可选）
        cache_size: 当前缓存大小（可选）
        cache_capacity: 缓存容量（可选）
    """

    total_queries: int
    hit_count: int
    miss_count: int
    hit_rate: float
    memory_usage: Dict[str, Any]
    total_slots: int = 0
    occupied_slots: int = 0
    usage_rate: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0
    cache_size: int = 0
    cache_capacity: int = 0
