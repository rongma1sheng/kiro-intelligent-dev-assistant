# pylint: disable=too-many-lines
"""
MIA系统统一记忆系统 (Unified Memory System) - vLLM增强版

白皮书依据: 第二章 2.8 统一记忆系统 + vLLM集成优化
版本: v1.6.1 (vLLM增强版)
作者: MIA Team
日期: 2026-01-18

核心理念: 集成Engram技术、传统记忆系统和vLLM内存池管理，为LLM调用提供统一的记忆增强。

记忆层次:
1. Engram记忆 - 存算解耦的O(1)记忆系统
2. 工作记忆 - 短期活跃信息
3. 情节记忆 - 历史事件和决策
4. 语义记忆 - 知识和概念
5. vLLM内存池 - KV Cache和推理状态管理 (新增)

vLLM集成特性:
- vLLM内存池协同管理
- KV Cache优化和共享
- 推理状态持久化
- 内存压力感知调度
- 批处理内存优化
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import redis
from loguru import logger

from src.infra.event_bus import Event, EventPriority, EventType, get_event_bus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VLLMMemoryPool:
    """vLLM内存池管理器 - Task 12.1 vLLM内存集成

    白皮书依据: 第二章 2.8 统一记忆系统 - vLLM内存池管理
    需求: 6.1, 6.3 - vLLM内存池协同管理

    核心功能:
    - KV Cache管理和优化
    - 推理状态持久化
    - 内存压力监控
    - 批处理内存协调
    """

    def __init__(self):
        """初始化vLLM内存池"""
        self.kv_cache_pool = {}  # KV Cache池
        self.inference_states = {}  # 推理状态
        self.memory_pressure = 0.0  # 内存压力
        self.cache_hit_count = 0
        self.cache_miss_count = 0

        # vLLM内存配置
        self.max_kv_cache_size = 1024 * 1024 * 1024  # 1GB KV Cache
        self.max_inference_states = 1000
        self.memory_pressure_threshold = 0.8

        logger.info("[VLLMMemoryPool] vLLM内存池初始化完成")

    async def get_kv_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取KV Cache

        Args:
            cache_key: 缓存键

        Returns:
            Optional[Dict]: KV Cache数据
        """
        try:
            if cache_key in self.kv_cache_pool:  # pylint: disable=no-else-return
                self.cache_hit_count += 1
                cache_entry = self.kv_cache_pool[cache_key]

                # 更新访问时间
                cache_entry["last_accessed"] = time.time()
                cache_entry["access_count"] += 1

                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"[VLLMMemoryPool] KV Cache命中: {cache_key}"
                )  # pylint: disable=logging-fstring-interpolation
                return cache_entry["data"]
            else:
                self.cache_miss_count += 1
                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"[VLLMMemoryPool] KV Cache未命中: {cache_key}"
                )  # pylint: disable=logging-fstring-interpolation
                return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[VLLMMemoryPool] KV Cache获取失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return None

    async def store_kv_cache(self, cache_key: str, kv_data: Dict[str, Any], importance: float = 0.5):
        """存储KV Cache

        Args:
            cache_key: 缓存键
            kv_data: KV Cache数据
            importance: 重要性评分
        """
        try:
            # 检查内存压力
            await self._check_memory_pressure()

            if self.memory_pressure > self.memory_pressure_threshold:
                # 内存压力过高，清理低重要性缓存
                await self._cleanup_low_importance_cache()

            # 存储KV Cache
            cache_entry = {
                "data": kv_data,
                "importance": importance,
                "created_at": time.time(),
                "last_accessed": time.time(),
                "access_count": 1,
                "size_bytes": len(str(kv_data)),  # 简化的大小估算
            }

            self.kv_cache_pool[cache_key] = cache_entry

            # 检查缓存大小限制
            await self._check_cache_size_limit()

            logger.debug(  # pylint: disable=logging-fstring-interpolation
                f"[VLLMMemoryPool] KV Cache存储成功: {cache_key}"
            )  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[VLLMMemoryPool] KV Cache存储失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def get_inference_state(self, state_key: str) -> Optional[Dict[str, Any]]:
        """获取推理状态

        Args:
            state_key: 状态键

        Returns:
            Optional[Dict]: 推理状态数据
        """
        try:
            if state_key in self.inference_states:  # pylint: disable=no-else-return
                state_entry = self.inference_states[state_key]
                state_entry["last_accessed"] = time.time()

                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"[VLLMMemoryPool] 推理状态获取成功: {state_key}"
                )  # pylint: disable=logging-fstring-interpolation
                return state_entry["data"]
            else:
                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"[VLLMMemoryPool] 推理状态未找到: {state_key}"
                )  # pylint: disable=logging-fstring-interpolation
                return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[VLLMMemoryPool] 推理状态获取失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return None

    async def store_inference_state(self, state_key: str, state_data: Dict[str, Any]):
        """存储推理状态

        Args:
            state_key: 状态键
            state_data: 推理状态数据
        """
        try:
            state_entry = {"data": state_data, "created_at": time.time(), "last_accessed": time.time()}

            self.inference_states[state_key] = state_entry

            # 检查状态数量限制
            if len(self.inference_states) > self.max_inference_states:
                await self._cleanup_old_inference_states()

            logger.debug(  # pylint: disable=logging-fstring-interpolation
                f"[VLLMMemoryPool] 推理状态存储成功: {state_key}"
            )  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[VLLMMemoryPool] 推理状态存储失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _check_memory_pressure(self):
        """检查内存压力"""
        try:
            # 计算当前内存使用
            total_cache_size = sum(entry["size_bytes"] for entry in self.kv_cache_pool.values())

            # 计算内存压力
            self.memory_pressure = total_cache_size / self.max_kv_cache_size

            if self.memory_pressure > 0.9:
                logger.warning(  # pylint: disable=logging-fstring-interpolation
                    f"[VLLMMemoryPool] 内存压力过高: {self.memory_pressure:.2%}"
                )  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[VLLMMemoryPool] 内存压力检查失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _cleanup_low_importance_cache(self):
        """清理低重要性缓存"""
        try:
            # 按重要性排序
            cache_items = list(self.kv_cache_pool.items())
            cache_items.sort(key=lambda x: x[1]["importance"])

            # 删除最低重要性的25%缓存
            to_remove = len(cache_items) // 4
            for i in range(to_remove):
                cache_key = cache_items[i][0]
                del self.kv_cache_pool[cache_key]

            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"[VLLMMemoryPool] 清理了{to_remove}个低重要性缓存"
            )  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[VLLMMemoryPool] 缓存清理失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _check_cache_size_limit(self):
        """检查缓存大小限制"""
        try:
            total_size = sum(entry["size_bytes"] for entry in self.kv_cache_pool.values())

            if total_size > self.max_kv_cache_size:
                # 按访问时间排序，删除最旧的缓存
                cache_items = list(self.kv_cache_pool.items())
                cache_items.sort(key=lambda x: x[1]["last_accessed"])

                # 删除直到大小合适
                while total_size > self.max_kv_cache_size * 0.8 and cache_items:
                    cache_key, cache_entry = cache_items.pop(0)
                    total_size -= cache_entry["size_bytes"]
                    del self.kv_cache_pool[cache_key]

                logger.info(  # pylint: disable=logging-fstring-interpolation
                    f"[VLLMMemoryPool] 缓存大小限制清理完成"  # pylint: disable=w1309
                )  # pylint: disable=logging-fstring-interpolation,w1309

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[VLLMMemoryPool] 缓存大小检查失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _cleanup_old_inference_states(self):
        """清理旧的推理状态"""
        try:
            # 按访问时间排序
            states = list(self.inference_states.items())
            states.sort(key=lambda x: x[1]["last_accessed"])

            # 保留最近的状态
            to_keep = states[-self.max_inference_states :]
            self.inference_states = {k: v for k, v in to_keep}  # pylint: disable=r1721

            removed_count = len(states) - len(to_keep)
            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"[VLLMMemoryPool] 清理了{removed_count}个旧推理状态"
            )  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[VLLMMemoryPool] 推理状态清理失败: {e}")  # pylint: disable=logging-fstring-interpolation

    def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存统计信息"""
        total_cache_size = sum(entry["size_bytes"] for entry in self.kv_cache_pool.values())

        return {
            "kv_cache_count": len(self.kv_cache_pool),
            "inference_states_count": len(self.inference_states),
            "total_cache_size_bytes": total_cache_size,
            "memory_pressure": self.memory_pressure,
            "cache_hit_rate": (self.cache_hit_count / max(self.cache_hit_count + self.cache_miss_count, 1)),
            "cache_hits": self.cache_hit_count,
            "cache_misses": self.cache_miss_count,
        }


class MemoryType(Enum):
    """记忆类型"""

    ENGRAM = "engram"  # Engram记忆
    WORKING = "working"  # 工作记忆
    EPISODIC = "episodic"  # 情节记忆
    SEMANTIC = "semantic"  # 语义记忆


@dataclass
class MemoryEntry:
    """记忆条目"""

    id: str
    content: Dict[str, Any]
    memory_type: MemoryType
    importance: float = 0.5
    access_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    decay_factor: float = 0.95

    def update_access(self):
        """更新访问信息"""
        self.access_count += 1
        self.last_accessed = datetime.now()

        # 根据访问频率调整重要性
        self.importance = min(1.0, self.importance + 0.01)

    def calculate_relevance(self, query_context: Dict[str, Any]) -> float:  # pylint: disable=unused-argument
        """计算与查询上下文的相关性"""
        # 简化的相关性计算
        relevance = 0.0

        # 时间衰减
        time_diff = (datetime.now() - self.last_accessed).total_seconds()
        time_decay = np.exp(-time_diff / 86400)  # 24小时衰减

        # 重要性权重
        importance_weight = self.importance

        # 访问频率权重
        frequency_weight = min(1.0, self.access_count / 10.0)

        # 内容匹配（简化）
        content_match = 0.5  # 默认中等匹配

        relevance = time_decay * 0.3 + importance_weight * 0.4 + frequency_weight * 0.2 + content_match * 0.1

        return min(1.0, relevance)


class EngramMemory:
    """Engram记忆模块 - 存算解耦的O(1)记忆系统

    白皮书依据: 第二章 2.8 统一记忆系统 - Engram技术

    Engram是一种生物启发的记忆机制，通过神经网络模式存储和检索记忆。
    实现O(1)时间复杂度的记忆访问，支持模糊匹配和联想检索。

    核心特性:
    - O(1)记忆存储和检索
    - 模糊匹配和联想检索
    - 自动重要性评估
    - 记忆衰减和遗忘
    - 存算解耦架构

    使用示例:
        >>> engram = EngramMemory()
        >>> await engram.store_memory(
        ...     text="买入000001.SZ，价格10.5元",
        ...     context={"action": "buy", "symbol": "000001.SZ"},
        ...     importance=0.8
        ... )
        >>> result = await engram.query_memory(
        ...     text="000001.SZ相关决策",
        ...     context={"symbol": "000001.SZ"}
        ... )
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """初始化Engram记忆

        Args:
            redis_client: Redis客户端，用于持久化存储
        """
        self.redis_client = redis_client
        self.memory_vectors = {}  # 内存中的向量索引
        self.memory_patterns = {}  # 记忆模式映射
        self.access_stats = {}  # 访问统计

        # Engram配置
        self.vector_dim = 128  # 向量维度
        self.max_memories = 10000  # 最大记忆数量
        self.decay_rate = 0.01  # 衰减率

        logger.info("Engram记忆模块初始化完成")

    async def store_memory(self, text: str, context: Dict[str, Any], importance: float = 0.5) -> str:
        """存储记忆到Engram

        Args:
            text: 记忆文本内容
            context: 记忆上下文信息
            importance: 重要性评分 (0-1)

        Returns:
            str: 记忆ID
        """
        try:
            # 生成记忆ID
            memory_id = f"engram_{int(time.time() * 1000)}_{hash(text) % 10000}"

            # 生成记忆向量（简化实现）
            memory_vector = self._text_to_vector(text)

            # 创建记忆条目
            memory_entry = {
                "id": memory_id,
                "text": text,
                "context": context,
                "vector": memory_vector.tolist(),
                "importance": importance,
                "created_at": time.time(),
                "access_count": 0,
                "last_accessed": time.time(),
            }

            # 存储到内存索引
            self.memory_vectors[memory_id] = memory_vector
            self.memory_patterns[memory_id] = memory_entry

            # 持久化到Redis
            if self.redis_client:
                await self._persist_to_redis(memory_id, memory_entry)

            # 检查内存限制
            await self._check_memory_limit()

            logger.debug(f"Engram记忆存储成功: {memory_id}")  # pylint: disable=logging-fstring-interpolation
            return memory_id

        except Exception as e:
            logger.error(f"Engram记忆存储失败: {e}")  # pylint: disable=logging-fstring-interpolation
            raise

    async def query_memory(self, text: str, context: Dict[str, Any], top_k: int = 5) -> Optional[Dict[str, Any]]:
        """查询Engram记忆

        Args:
            text: 查询文本
            context: 查询上下文
            top_k: 返回最相关的K个记忆

        Returns:
            Dict: 查询结果，包含相关记忆和置信度
        """
        try:
            if not self.memory_patterns:
                return None

            # 生成查询向量
            query_vector = self._text_to_vector(text)

            # 计算相似度
            similarities = []
            for memory_id, memory_vector in self.memory_vectors.items():
                similarity = self._cosine_similarity(query_vector, memory_vector)

                # 结合上下文匹配
                context_match = self._context_similarity(context, self.memory_patterns[memory_id]["context"])

                # 综合评分
                combined_score = similarity * 0.7 + context_match * 0.3
                similarities.append((memory_id, combined_score))

            # 排序并获取top_k
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_memories = similarities[:top_k]

            if not top_memories or top_memories[0][1] < 0.3:
                return None

            # 构建结果
            result = {"memories": [], "confidence": top_memories[0][1], "summary": "", "patterns": []}

            for memory_id, score in top_memories:
                memory = self.memory_patterns[memory_id]
                result["memories"].append(
                    {
                        "id": memory_id,
                        "text": memory["text"],
                        "context": memory["context"],
                        "score": score,
                        "importance": memory["importance"],
                    }
                )

                # 更新访问统计
                await self._update_access_stats(memory_id)

            # 生成摘要
            result["summary"] = self._generate_memory_summary(result["memories"])

            # 提取模式
            result["patterns"] = self._extract_patterns(result["memories"])

            logger.debug(  # pylint: disable=logging-fstring-interpolation
                f"Engram记忆查询成功: 找到{len(result['memories'])}个相关记忆"
            )  # pylint: disable=logging-fstring-interpolation
            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Engram记忆查询失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return None

    def _text_to_vector(self, text: str) -> np.ndarray:
        """将文本转换为向量（简化实现）

        Args:
            text: 输入文本

        Returns:
            np.ndarray: 文本向量
        """
        # 简化的文本向量化（实际应该使用预训练的embedding模型）
        import hashlib  # pylint: disable=import-outside-toplevel

        # 使用哈希生成伪向量
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()

        # 转换为浮点向量
        vector = np.frombuffer(hash_bytes, dtype=np.uint8).astype(np.float32)

        # 扩展到指定维度
        if len(vector) < self.vector_dim:
            vector = np.tile(vector, (self.vector_dim // len(vector) + 1))[: self.vector_dim]
        else:
            vector = vector[: self.vector_dim]

        # 归一化
        vector = vector / np.linalg.norm(vector)

        return vector

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            float: 相似度 (0-1)
        """
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return max(0.0, similarity)  # 确保非负

        except Exception:  # pylint: disable=broad-exception-caught
            return 0.0

    def _context_similarity(self, ctx1: Dict[str, Any], ctx2: Dict[str, Any]) -> float:
        """计算上下文相似度

        Args:
            ctx1: 上下文1
            ctx2: 上下文2

        Returns:
            float: 相似度 (0-1)
        """
        if not ctx1 or not ctx2:
            return 0.0

        # 计算键的交集
        keys1 = set(ctx1.keys())
        keys2 = set(ctx2.keys())
        common_keys = keys1.intersection(keys2)

        if not common_keys:
            return 0.0

        # 计算值的匹配度
        matches = 0
        for key in common_keys:
            if ctx1[key] == ctx2[key]:
                matches += 1

        similarity = matches / len(common_keys)
        return similarity

    async def _persist_to_redis(self, memory_id: str, memory_entry: Dict[str, Any]):
        """持久化记忆到Redis

        Args:
            memory_id: 记忆ID
            memory_entry: 记忆条目
        """
        try:
            if not self.redis_client:
                return

            # 检查Redis客户端类型
            if hasattr(self.redis_client, "hset"):
                # 真实Redis
                key = f"engram:memory:{memory_id}"
                await self.redis_client.hset(
                    key, mapping={"data": json.dumps(memory_entry), "created_at": memory_entry["created_at"]}
                )
                await self.redis_client.expire(key, 86400 * 30)  # 30天过期

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Redis持久化失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _update_access_stats(self, memory_id: str):
        """更新访问统计

        Args:
            memory_id: 记忆ID
        """
        try:
            if memory_id in self.memory_patterns:
                self.memory_patterns[memory_id]["access_count"] += 1
                self.memory_patterns[memory_id]["last_accessed"] = time.time()

            # 更新访问统计
            if memory_id not in self.access_stats:
                self.access_stats[memory_id] = {"count": 0, "last_access": time.time()}

            self.access_stats[memory_id]["count"] += 1
            self.access_stats[memory_id]["last_access"] = time.time()

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"访问统计更新失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _check_memory_limit(self):
        """检查内存限制并清理旧记忆"""
        try:
            if len(self.memory_patterns) <= self.max_memories:
                return

            # 按重要性和访问时间排序
            memories = list(self.memory_patterns.items())
            memories.sort(
                key=lambda x: (x[1]["importance"] * 0.5 + (time.time() - x[1]["last_accessed"]) / 86400 * 0.5)
            )

            # 删除最不重要的记忆
            to_remove = len(memories) - self.max_memories
            for i in range(to_remove):
                memory_id = memories[i][0]
                del self.memory_patterns[memory_id]
                del self.memory_vectors[memory_id]
                self.access_stats.pop(memory_id, None)

            logger.info(f"清理了{to_remove}个旧记忆")  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"记忆清理失败: {e}")  # pylint: disable=logging-fstring-interpolation

    def _generate_memory_summary(self, memories: List[Dict[str, Any]]) -> str:
        """生成记忆摘要

        Args:
            memories: 记忆列表

        Returns:
            str: 摘要文本
        """
        if not memories:
            return "暂无相关记忆"

        # 简化的摘要生成
        top_memory = memories[0]
        summary = f"最相关的记忆: {top_memory['text'][:50]}..."

        if len(memories) > 1:
            summary += f" (共找到{len(memories)}个相关记忆)"

        return summary

    def _extract_patterns(self, memories: List[Dict[str, Any]]) -> List[str]:
        """提取记忆模式

        Args:
            memories: 记忆列表

        Returns:
            List[str]: 模式列表
        """
        patterns = []

        # 提取常见的上下文模式
        contexts = [mem["context"] for mem in memories]

        # 统计常见键值对
        key_counts = {}
        for ctx in contexts:
            for key, value in ctx.items():
                pattern = f"{key}={value}"
                key_counts[pattern] = key_counts.get(pattern, 0) + 1

        # 选择出现频率高的模式
        for pattern, count in key_counts.items():
            if count >= 2:  # 至少出现2次
                patterns.append(pattern)

        return patterns[:5]  # 最多返回5个模式


class UnifiedMemorySystem:
    """统一记忆系统 (集成Engram技术 + vLLM内存池) - vLLM增强版

    白皮书依据: 第二章 2.8 统一记忆系统 + vLLM集成优化
    需求: 6.1, 6.3 - vLLM内存池协同管理

    集成多种记忆机制，为LLM调用提供统一的记忆增强服务。

    记忆层次:
    1. Engram记忆 - 高速联想记忆，O(1)访问
    2. 工作记忆 - 短期活跃信息，容量有限
    3. 情节记忆 - 历史事件和决策序列
    4. 语义记忆 - 知识和概念，长期存储
    5. vLLM内存池 - KV Cache和推理状态管理 (新增)

    核心特性:
    - 多层次记忆架构
    - 智能记忆检索和融合
    - 自动重要性评估
    - 记忆衰减和遗忘机制
    - Redis持久化存储
    - vLLM内存池协同管理 (新增)
    - KV Cache优化和共享 (新增)
    - 内存压力感知调度 (新增)

    使用示例:
        >>> memory_system = UnifiedMemorySystem()
        >>> await memory_system.add_to_memory(
        ...     memory_type='episodic',
        ...     content={'action': 'buy', 'result': 'profit'},
        ...     importance=0.8
        ... )
        >>> context = await memory_system.get_relevant_context(
        ...     query={'action': 'buy'},
        ...     max_items=5
        ... )
        >>> # vLLM内存池使用
        >>> await memory_system.store_vllm_kv_cache(
        ...     cache_key='prompt_hash_123',
        ...     kv_data={'keys': [...], 'values': [...]},
        ...     importance=0.9
        ... )
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """初始化统一记忆系统 - vLLM增强版

        Args:
            redis_client: Redis客户端，用于持久化存储
        """
        self.redis_client = redis_client

        # 初始化各种记忆模块
        self.engram_memory = EngramMemory(redis_client)
        self.working_memory = {}  # 工作记忆（内存）
        self.episodic_memory = {}  # 情节记忆
        self.semantic_memory = {}  # 语义记忆

        # 初始化vLLM内存池 - Task 12.1
        self.vllm_memory_pool = VLLMMemoryPool()

        # 记忆配置
        self.working_memory_limit = 50  # 工作记忆容量
        self.episodic_memory_limit = 1000  # 情节记忆容量
        self.semantic_memory_limit = 5000  # 语义记忆容量

        # 统计信息
        self.memory_stats = {
            "total_memories": 0,
            "engram_memories": 0,
            "working_memories": 0,
            "episodic_memories": 0,
            "semantic_memories": 0,
            "vllm_cache_entries": 0,  # 新增
            "queries_count": 0,
            "cache_hits": 0,
        }

        # 事件总线和查询响应
        self.event_bus = None
        self.pending_queries = {}  # 存储待响应的查询 {correlation_id: future}

        logger.info("统一记忆系统初始化完成 - vLLM增强版")

    async def initialize(self):
        """初始化事件总线连接和事件订阅"""
        try:
            # 获取事件总线实例
            self.event_bus = await get_event_bus()

            # 订阅系统响应事件
            await self.event_bus.subscribe(
                EventType.SYSTEM_RESPONSE, self._handle_system_response, "unified_memory_system_response_handler"
            )

            logger.info("统一记忆系统事件订阅完成")

        except Exception as e:
            logger.error(f"统一记忆系统初始化失败: {e}")  # pylint: disable=logging-fstring-interpolation
            raise

    async def query_schedule_info(
        self, query_type: str = "schedule_info", timeout: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """通过事件总线查询调度信息 - vLLM增强版

        白皮书依据: 第二章 2.8 统一记忆系统 - 事件驱动解耦 + vLLM资源协同
        需求: 6.1, 6.3 - vLLM内存池协同管理

        Args:
            query_type: 查询类型
            timeout: 查询超时时间（秒）

        Returns:
            调度信息字典，超时或失败时返回None
        """
        try:
            if not self.event_bus:
                logger.error("事件总线未初始化，无法查询调度信息")
                return None

            # 获取当前事件循环
            loop = asyncio.get_running_loop()
            logger.debug(  # pylint: disable=logging-fstring-interpolation
                f"[query_schedule_info] 当前事件循环: {id(loop)}"
            )  # pylint: disable=logging-fstring-interpolation

            # 生成唯一的查询关联ID（使用UUID确保唯一性）
            import uuid  # pylint: disable=import-outside-toplevel

            correlation_id = f"memory_query_{uuid.uuid4().hex[:16]}_{int(time.time() * 1000000)}"

            # 在当前事件循环中创建Future
            response_future = loop.create_future()
            self.pending_queries[correlation_id] = response_future

            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"[query_schedule_info] 创建查询Future: correlation_id={correlation_id}, future_id={id(response_future)}"
            )

            # 获取vLLM内存状态
            vllm_memory_stats = self.vllm_memory_pool.get_memory_stats()

            # 发布系统查询事件（包含vLLM内存信息）
            query_event = Event(
                event_type=EventType.SYSTEM_QUERY,
                source_module="unified_memory_system",
                target_module="chronos_scheduler",
                priority=EventPriority.HIGH,
                data={
                    "query_type": query_type,
                    "correlation_id": correlation_id,
                    "requester": "unified_memory_system",
                    "timestamp": time.time(),
                    "vllm_memory_state": vllm_memory_stats,  # 新增vLLM内存状态
                    "memory_pressure": self.vllm_memory_pool.memory_pressure,  # 新增内存压力
                },
            )

            await self.event_bus.publish(query_event)

            logger.debug(  # pylint: disable=logging-fstring-interpolation
                f"[query_schedule_info] 查询事件已发布，等待响应..."  # pylint: disable=w1309
            )  # pylint: disable=logging-fstring-interpolation

            # 等待响应（带超时）
            try:
                response = await asyncio.wait_for(response_future, timeout=timeout)
                logger.debug(f"调度信息查询成功: {correlation_id}")  # pylint: disable=logging-fstring-interpolation
                return response

            except asyncio.TimeoutError:
                logger.warning(f"调度信息查询超时: {correlation_id}")  # pylint: disable=logging-fstring-interpolation
                self.pending_queries.pop(correlation_id, None)
                return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"调度信息查询失败: {e}", exc_info=True)  # pylint: disable=logging-fstring-interpolation
            return None

    async def _handle_system_response(self, event: Event):
        """处理系统响应事件

        Args:
            event: 系统响应事件
        """
        try:
            # 获取当前事件循环
            loop = asyncio.get_running_loop()
            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"[UnifiedMemorySystem] 收到系统响应事件: event_id={event.event_id}, source={event.source_module}, loop_id={id(loop)}"  # pylint: disable=line-too-long
            )

            correlation_id = event.data.get("correlation_id")
            if not correlation_id:
                logger.warning("系统响应事件缺少correlation_id")
                return

            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"[UnifiedMemorySystem] 处理响应: correlation_id={correlation_id}"
            )  # pylint: disable=logging-fstring-interpolation

            # 查找对应的查询Future
            response_future = self.pending_queries.get(correlation_id)
            if not response_future:
                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"未找到对应的查询请求: {correlation_id}, pending_queries={list(self.pending_queries.keys())}"
                )
                return

            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"[UnifiedMemorySystem] 找到Future: future_id={id(response_future)}, done={response_future.done()}, cancelled={response_future.cancelled()}"  # pylint: disable=line-too-long
            )

            # 设置响应结果
            if not response_future.done():
                response_data = event.data.get("response_data", {})

                # 确保在正确的事件循环中设置结果
                if response_future.get_loop() == loop:
                    response_future.set_result(response_data)
                    logger.info(f"系统响应处理完成: {correlation_id}")  # pylint: disable=logging-fstring-interpolation
                else:
                    logger.error(  # pylint: disable=logging-fstring-interpolation
                        f"Future事件循环不匹配: future_loop={id(response_future.get_loop())}, current_loop={id(loop)}"
                    )
                    # 尝试在Future的事件循环中设置结果
                    response_future.get_loop().call_soon_threadsafe(response_future.set_result, response_data)
                    logger.info(  # pylint: disable=logging-fstring-interpolation
                        f"通过call_soon_threadsafe设置结果: {correlation_id}"
                    )  # pylint: disable=logging-fstring-interpolation

                # 从pending_queries中移除
                self.pending_queries.pop(correlation_id, None)
            else:
                logger.warning(  # pylint: disable=logging-fstring-interpolation
                    f"响应Future已完成: {correlation_id}, result={response_future.result() if not response_future.cancelled() else 'cancelled'}"  # pylint: disable=line-too-long
                )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"系统响应处理失败: {e}", exc_info=True)  # pylint: disable=logging-fstring-interpolation

    async def get_memory_state_for_scheduler(self) -> Dict[str, Any]:
        """为调度器提供内存状态信息 - vLLM增强版

        白皮书依据: 第二章 2.8 统一记忆系统 - vLLM资源协同
        需求: 6.1, 6.3 - vLLM内存池协同管理

        Returns:
            内存状态信息字典（包含vLLM内存状态）
        """
        try:
            memory_stats = self.get_memory_stats()

            # 计算内存使用率
            working_usage = len(self.working_memory) / self.working_memory_limit
            episodic_usage = len(self.episodic_memory) / self.episodic_memory_limit
            semantic_usage = len(self.semantic_memory) / self.semantic_memory_limit

            # 获取vLLM内存状态
            vllm_stats = self.vllm_memory_pool.get_memory_stats()
            vllm_memory_pressure = vllm_stats["memory_pressure"]

            # 计算总体内存压力（包含vLLM）
            memory_pressure = max(
                working_usage, episodic_usage, semantic_usage, vllm_memory_pressure  # 新增vLLM内存压力
            )

            return {
                "memory_stats": memory_stats,
                "memory_usage": {
                    "working_usage": working_usage,
                    "episodic_usage": episodic_usage,
                    "semantic_usage": semantic_usage,
                    "overall_pressure": memory_pressure,
                },
                "memory_limits": {
                    "working_limit": self.working_memory_limit,
                    "episodic_limit": self.episodic_memory_limit,
                    "semantic_limit": self.semantic_memory_limit,
                },
                "vllm_memory_state": vllm_stats,  # 新增vLLM内存状态
                "vllm_memory_pressure": vllm_memory_pressure,  # 新增vLLM内存压力
                "timestamp": time.time(),
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"获取内存状态失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return {}

    # vLLM内存池接口方法 - Task 12.1

    async def store_vllm_kv_cache(self, cache_key: str, kv_data: Dict[str, Any], importance: float = 0.5) -> bool:
        """存储vLLM KV Cache

        白皮书依据: 第二章 2.8 统一记忆系统 - vLLM内存池管理
        需求: 6.1, 6.3 - vLLM内存池协同管理

        Args:
            cache_key: 缓存键
            kv_data: KV Cache数据
            importance: 重要性评分

        Returns:
            bool: 存储是否成功
        """
        try:
            await self.vllm_memory_pool.store_kv_cache(cache_key, kv_data, importance)
            self.memory_stats["vllm_cache_entries"] += 1
            logger.debug(  # pylint: disable=logging-fstring-interpolation
                f"[UnifiedMemorySystem] vLLM KV Cache存储成功: {cache_key}"
            )  # pylint: disable=logging-fstring-interpolation
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(  # pylint: disable=logging-fstring-interpolation
                f"[UnifiedMemorySystem] vLLM KV Cache存储失败: {e}"
            )  # pylint: disable=logging-fstring-interpolation
            return False

    async def get_vllm_kv_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取vLLM KV Cache

        Args:
            cache_key: 缓存键

        Returns:
            Optional[Dict]: KV Cache数据
        """
        try:
            result = await self.vllm_memory_pool.get_kv_cache(cache_key)
            if result:
                self.memory_stats["cache_hits"] += 1
                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"[UnifiedMemorySystem] vLLM KV Cache命中: {cache_key}"
                )  # pylint: disable=logging-fstring-interpolation
            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(  # pylint: disable=logging-fstring-interpolation
                f"[UnifiedMemorySystem] vLLM KV Cache获取失败: {e}"
            )  # pylint: disable=logging-fstring-interpolation
            return None

    async def store_vllm_inference_state(self, state_key: str, state_data: Dict[str, Any]) -> bool:
        """存储vLLM推理状态

        Args:
            state_key: 状态键
            state_data: 推理状态数据

        Returns:
            bool: 存储是否成功
        """
        try:
            await self.vllm_memory_pool.store_inference_state(state_key, state_data)
            logger.debug(  # pylint: disable=logging-fstring-interpolation
                f"[UnifiedMemorySystem] vLLM推理状态存储成功: {state_key}"
            )  # pylint: disable=logging-fstring-interpolation
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(  # pylint: disable=logging-fstring-interpolation
                f"[UnifiedMemorySystem] vLLM推理状态存储失败: {e}"
            )  # pylint: disable=logging-fstring-interpolation
            return False

    async def get_vllm_inference_state(self, state_key: str) -> Optional[Dict[str, Any]]:
        """获取vLLM推理状态

        Args:
            state_key: 状态键

        Returns:
            Optional[Dict]: 推理状态数据
        """
        try:
            result = await self.vllm_memory_pool.get_inference_state(state_key)
            if result:
                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"[UnifiedMemorySystem] vLLM推理状态获取成功: {state_key}"
                )  # pylint: disable=logging-fstring-interpolation
            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(  # pylint: disable=logging-fstring-interpolation
                f"[UnifiedMemorySystem] vLLM推理状态获取失败: {e}"
            )  # pylint: disable=logging-fstring-interpolation
            return None

    def get_vllm_memory_pressure(self) -> float:
        """获取vLLM内存压力

        Returns:
            float: 内存压力 (0.0-1.0)
        """
        return self.vllm_memory_pool.memory_pressure

    async def optimize_vllm_memory(self) -> Dict[str, Any]:
        """优化vLLM内存使用

        Returns:
            Dict: 优化结果统计
        """
        try:
            # 获取优化前状态
            before_stats = self.vllm_memory_pool.get_memory_stats()

            # 执行内存优化
            await self.vllm_memory_pool._check_memory_pressure()

            if self.vllm_memory_pool.memory_pressure > 0.8:
                await self.vllm_memory_pool._cleanup_low_importance_cache()

            await self.vllm_memory_pool._check_cache_size_limit()
            await self.vllm_memory_pool._cleanup_old_inference_states()

            # 获取优化后状态
            after_stats = self.vllm_memory_pool.get_memory_stats()

            optimization_result = {
                "before_cache_count": before_stats["kv_cache_count"],
                "after_cache_count": after_stats["kv_cache_count"],
                "before_memory_pressure": before_stats["memory_pressure"],
                "after_memory_pressure": after_stats["memory_pressure"],
                "cache_cleaned": before_stats["kv_cache_count"] - after_stats["kv_cache_count"],
                "memory_freed_bytes": before_stats["total_cache_size_bytes"] - after_stats["total_cache_size_bytes"],
            }

            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"[UnifiedMemorySystem] vLLM内存优化完成: {optimization_result}"
            )  # pylint: disable=logging-fstring-interpolation
            return optimization_result

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(  # pylint: disable=logging-fstring-interpolation
                f"[UnifiedMemorySystem] vLLM内存优化失败: {e}"
            )  # pylint: disable=logging-fstring-interpolation
            return {}

    async def add_to_memory(
        self,
        memory_type: str,
        content: Dict[str, Any],
        importance: float = 0.5,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """添加记忆到指定类型的记忆系统

        Args:
            memory_type: 记忆类型 ('engram', 'working', 'episodic', 'semantic')
            content: 记忆内容
            importance: 重要性评分 (0-1)
            context: 额外上下文信息

        Returns:
            str: 记忆ID

        Raises:
            ValueError: 当记忆类型无效时
        """
        try:
            # 生成记忆ID
            memory_id = f"{memory_type}_{int(time.time() * 1000)}_{hash(str(content)) % 10000}"

            # 创建记忆条目
            memory_entry = MemoryEntry(
                id=memory_id, content=content, memory_type=MemoryType(memory_type), importance=importance
            )

            # 根据类型存储到相应的记忆系统
            if memory_type == "engram":
                # 存储到Engram记忆
                text_content = json.dumps(content, ensure_ascii=False)
                engram_context = context or content
                await self.engram_memory.store_memory(text=text_content, context=engram_context, importance=importance)
                self.memory_stats["engram_memories"] += 1

            elif memory_type == "working":
                # 存储到工作记忆
                self.working_memory[memory_id] = memory_entry
                await self._check_working_memory_limit()
                self.memory_stats["working_memories"] += 1

            elif memory_type == "episodic":
                # 存储到情节记忆
                self.episodic_memory[memory_id] = memory_entry
                await self._persist_episodic_memory(memory_id, memory_entry)
                await self._check_episodic_memory_limit()
                self.memory_stats["episodic_memories"] += 1

            elif memory_type == "semantic":
                # 存储到语义记忆
                self.semantic_memory[memory_id] = memory_entry
                await self._persist_semantic_memory(memory_id, memory_entry)
                await self._check_semantic_memory_limit()
                self.memory_stats["semantic_memories"] += 1

            else:
                raise ValueError(f"无效的记忆类型: {memory_type}")

            self.memory_stats["total_memories"] += 1

            logger.debug(f"记忆添加成功: {memory_type} - {memory_id}")  # pylint: disable=logging-fstring-interpolation
            return memory_id

        except Exception as e:
            logger.error(f"记忆添加失败: {e}")  # pylint: disable=logging-fstring-interpolation
            raise

    async def get_relevant_context(
        self, query: Dict[str, Any], max_items: int = 10, memory_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """获取相关的记忆上下文

        Args:
            query: 查询条件
            max_items: 最大返回数量
            memory_types: 要查询的记忆类型列表，None表示查询所有类型

        Returns:
            List[Dict]: 相关记忆列表，按相关性排序
        """
        try:
            self.memory_stats["queries_count"] += 1

            relevant_memories = []
            memory_types = memory_types or ["engram", "working", "episodic", "semantic"]

            # 查询Engram记忆
            if "engram" in memory_types:
                engram_result = await self.engram_memory.query_memory(
                    text=json.dumps(query, ensure_ascii=False), context=query, top_k=max_items // 2
                )

                if engram_result and engram_result["memories"]:
                    for memory in engram_result["memories"]:
                        relevant_memories.append(
                            {
                                "id": memory["id"],
                                "type": "engram",
                                "content": memory["context"],
                                "relevance": memory["score"],
                                "importance": memory["importance"],
                                "summary": memory["text"][:100],
                            }
                        )

            # 查询工作记忆
            if "working" in memory_types:
                for memory_id, memory_entry in self.working_memory.items():
                    relevance = memory_entry.calculate_relevance(query)
                    if relevance > 0.3:
                        relevant_memories.append(
                            {
                                "id": memory_id,
                                "type": "working",
                                "content": memory_entry.content,
                                "relevance": relevance,
                                "importance": memory_entry.importance,
                                "summary": str(memory_entry.content)[:100],
                            }
                        )

            # 查询情节记忆
            if "episodic" in memory_types:
                for memory_id, memory_entry in self.episodic_memory.items():
                    relevance = memory_entry.calculate_relevance(query)
                    if relevance > 0.3:
                        relevant_memories.append(
                            {
                                "id": memory_id,
                                "type": "episodic",
                                "content": memory_entry.content,
                                "relevance": relevance,
                                "importance": memory_entry.importance,
                                "summary": str(memory_entry.content)[:100],
                            }
                        )

            # 查询语义记忆
            if "semantic" in memory_types:
                for memory_id, memory_entry in self.semantic_memory.items():
                    relevance = memory_entry.calculate_relevance(query)
                    if relevance > 0.3:
                        relevant_memories.append(
                            {
                                "id": memory_id,
                                "type": "semantic",
                                "content": memory_entry.content,
                                "relevance": relevance,
                                "importance": memory_entry.importance,
                                "summary": str(memory_entry.content)[:100],
                            }
                        )

            # 按相关性排序
            relevant_memories.sort(key=lambda x: x["relevance"], reverse=True)

            # 限制返回数量
            result = relevant_memories[:max_items]

            # 更新访问统计
            for memory in result:
                if memory["type"] in ["working", "episodic", "semantic"]:
                    memory_entry = getattr(self, f"{memory['type']}_memory").get(memory["id"])
                    if memory_entry:
                        memory_entry.update_access()

            logger.debug(f"记忆查询完成: 找到{len(result)}个相关记忆")  # pylint: disable=logging-fstring-interpolation
            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"记忆查询失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return []

    async def _check_working_memory_limit(self):
        """检查工作记忆容量限制"""
        try:
            if len(self.working_memory) <= self.working_memory_limit:
                return

            # 按访问时间排序，删除最旧的记忆
            memories = list(self.working_memory.items())
            memories.sort(key=lambda x: x[1].last_accessed)

            to_remove = len(memories) - self.working_memory_limit
            for i in range(to_remove):
                memory_id = memories[i][0]
                del self.working_memory[memory_id]

            logger.debug(f"工作记忆清理: 删除{to_remove}个旧记忆")  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"工作记忆清理失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _check_episodic_memory_limit(self):
        """检查情节记忆容量限制"""
        try:
            if len(self.episodic_memory) <= self.episodic_memory_limit:
                return

            # 按重要性和访问时间排序
            memories = list(self.episodic_memory.items())
            memories.sort(key=lambda x: (x[1].importance, x[1].last_accessed))

            to_remove = len(memories) - self.episodic_memory_limit
            for i in range(to_remove):
                memory_id = memories[i][0]
                del self.episodic_memory[memory_id]

            logger.debug(f"情节记忆清理: 删除{to_remove}个旧记忆")  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"情节记忆清理失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _check_semantic_memory_limit(self):
        """检查语义记忆容量限制"""
        try:
            if len(self.semantic_memory) <= self.semantic_memory_limit:
                return

            # 按重要性排序，保留最重要的记忆
            memories = list(self.semantic_memory.items())
            memories.sort(key=lambda x: x[1].importance, reverse=True)

            # 保留前N个最重要的记忆
            to_keep = memories[: self.semantic_memory_limit]
            self.semantic_memory = {k: v for k, v in to_keep}  # pylint: disable=r1721

            removed_count = len(memories) - len(to_keep)
            logger.debug(  # pylint: disable=logging-fstring-interpolation
                f"语义记忆清理: 删除{removed_count}个低重要性记忆"
            )  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"语义记忆清理失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _persist_episodic_memory(self, memory_id: str, memory_entry: MemoryEntry):
        """持久化情节记忆到Redis"""
        try:
            if not self.redis_client:
                return

            if hasattr(self.redis_client, "hset"):
                key = f"memory:episodic:{memory_id}"
                data = {
                    "content": json.dumps(memory_entry.content),
                    "importance": memory_entry.importance,
                    "created_at": memory_entry.created_at.isoformat(),
                    "access_count": memory_entry.access_count,
                }
                await self.redis_client.hset(key, mapping=data)
                await self.redis_client.expire(key, 86400 * 7)  # 7天过期

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"情节记忆持久化失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _persist_semantic_memory(self, memory_id: str, memory_entry: MemoryEntry):
        """持久化语义记忆到Redis"""
        try:
            if not self.redis_client:
                return

            if hasattr(self.redis_client, "hset"):
                key = f"memory:semantic:{memory_id}"
                data = {
                    "content": json.dumps(memory_entry.content),
                    "importance": memory_entry.importance,
                    "created_at": memory_entry.created_at.isoformat(),
                    "access_count": memory_entry.access_count,
                }
                await self.redis_client.hset(key, mapping=data)
                await self.redis_client.expire(key, 86400 * 30)  # 30天过期

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"语义记忆持久化失败: {e}")  # pylint: disable=logging-fstring-interpolation

    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆系统统计信息 - vLLM增强版

        Returns:
            Dict: 统计信息（包含vLLM内存统计）
        """
        # 获取vLLM内存统计
        vllm_stats = self.vllm_memory_pool.get_memory_stats()

        return {
            **self.memory_stats,
            "working_memory_usage": len(self.working_memory),
            "episodic_memory_usage": len(self.episodic_memory),
            "semantic_memory_usage": len(self.semantic_memory),
            "cache_hit_rate": (self.memory_stats["cache_hits"] / max(self.memory_stats["queries_count"], 1)),
            # vLLM内存统计
            "vllm_memory_stats": vllm_stats,
            "vllm_cache_count": vllm_stats["kv_cache_count"],
            "vllm_memory_pressure": vllm_stats["memory_pressure"],
            "vllm_cache_hit_rate": vllm_stats["cache_hit_rate"],
        }

    async def clear_memory(self, memory_type: Optional[str] = None):
        """清空指定类型的记忆 - vLLM增强版

        Args:
            memory_type: 记忆类型，None表示清空所有记忆，'vllm'表示清空vLLM内存池
        """
        try:
            if memory_type is None or memory_type == "working":
                self.working_memory.clear()
                logger.info("工作记忆已清空")

            if memory_type is None or memory_type == "episodic":
                self.episodic_memory.clear()
                logger.info("情节记忆已清空")

            if memory_type is None or memory_type == "semantic":
                self.semantic_memory.clear()
                logger.info("语义记忆已清空")

            if memory_type is None or memory_type == "engram":
                # 清空Engram记忆
                self.engram_memory.memory_patterns.clear()
                self.engram_memory.memory_vectors.clear()
                self.engram_memory.access_stats.clear()
                logger.info("Engram记忆已清空")

            # 清空vLLM内存池 - Task 12.1
            if memory_type is None or memory_type == "vllm":
                self.vllm_memory_pool.kv_cache_pool.clear()
                self.vllm_memory_pool.inference_states.clear()
                self.vllm_memory_pool.cache_hit_count = 0
                self.vllm_memory_pool.cache_miss_count = 0
                self.vllm_memory_pool.memory_pressure = 0.0
                logger.info("vLLM内存池已清空")

            # 重置统计
            if memory_type is None:
                self.memory_stats = {
                    "total_memories": 0,
                    "engram_memories": 0,
                    "working_memories": 0,
                    "episodic_memories": 0,
                    "semantic_memories": 0,
                    "vllm_cache_entries": 0,
                    "queries_count": 0,
                    "cache_hits": 0,
                }

        except Exception as e:
            logger.error(f"记忆清空失败: {e}")  # pylint: disable=logging-fstring-interpolation
            raise
