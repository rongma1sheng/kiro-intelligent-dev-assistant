"""Cost Optimizer - API Cost Optimization Strategies

白皮书依据: 第十八章 18.3 成本优化策略

核心功能:
- 优先使用本地模型
- 响应缓存
- 批量调用
- Prompt压缩
"""

import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class CostOptimizer:
    """成本优化器 - API成本优化策略

    白皮书依据: 第十八章 18.3 成本优化策略

    核心功能:
    - 优先使用本地模型
    - 响应缓存
    - 批量调用
    - Prompt压缩

    Attributes:
        cache_ttl: 缓存过期时间（秒）
        batch_size: 批量大小
        cache: 响应缓存
    """

    def __init__(self, cache_ttl: int = 300, batch_size: int = 10):
        """初始化成本优化器

        Args:
            cache_ttl: 缓存过期时间（秒），默认300秒（5分钟）
            batch_size: 批量大小，默认10

        Raises:
            ValueError: 当参数无效时
        """
        if cache_ttl <= 0:
            raise ValueError(f"缓存过期时间必须 > 0: {cache_ttl}")

        if batch_size <= 0:
            raise ValueError(f"批量大小必须 > 0: {batch_size}")

        self.cache_ttl = cache_ttl
        self.batch_size = batch_size

        # 响应缓存：{cache_key: (response, timestamp)}
        self.cache: Dict[str, Tuple[Any, float]] = {}

        # 统计信息
        self.cache_hits = 0
        self.cache_misses = 0
        self.local_model_uses = 0
        self.cloud_model_uses = 0
        self.batch_calls = 0

        logger.info(f"[CostOptimizer] 初始化完成 - " f"缓存TTL: {cache_ttl}s, " f"批量大小: {batch_size}")

    def prefer_local_over_cloud(self, local_available: bool, budget_exceeded: bool) -> str:
        """优先使用本地模型

        白皮书依据: 第十八章 18.3.1 模型选择优化

        Args:
            local_available: 本地模型是否可用
            budget_exceeded: 预算是否超限

        Returns:
            推荐的模型类型（local/cloud）
        """
        # 优先级1: 本地模型可用
        if local_available:
            self.local_model_uses += 1
            logger.debug("[CostOptimizer] 使用本地模型（免费）")
            return "local"

        # 优先级2: 预算超限，强制使用本地模型
        if budget_exceeded:
            logger.warning(
                "[CostOptimizer] 预算超限，但本地模型不可用，"
                "建议使用降级策略"  # pylint: disable=implicit-str-concat
            )  # pylint: disable=implicit-str-concat
            return "local"  # 即使不可用也返回local，由调用方处理

        # 优先级3: 使用云端模型
        self.cloud_model_uses += 1
        logger.debug("[CostOptimizer] 使用云端模型")
        return "cloud"

    def implement_response_caching(self, request_key: str, response: Optional[Any] = None) -> Optional[Any]:
        """实现响应缓存

        白皮书依据: 第十八章 18.3.2 缓存策略

        相同请求5分钟内返回缓存

        Args:
            request_key: 请求键（用于缓存查找）
            response: 响应内容（如果提供，则存入缓存）

        Returns:
            如果缓存命中，返回缓存的响应；否则返回None

        Raises:
            ValueError: 当请求键为空时
        """
        if not request_key:
            raise ValueError("请求键不能为空")

        # 生成缓存键
        cache_key = self._generate_cache_key(request_key)

        # 如果提供了响应，存入缓存
        if response is not None:
            self.cache[cache_key] = (response, time.time())
            logger.debug(f"[CostOptimizer] 缓存响应: {cache_key[:16]}...")
            return None

        # 检查缓存
        if cache_key in self.cache:
            cached_response, timestamp = self.cache[cache_key]

            # 检查是否过期
            if time.time() - timestamp < self.cache_ttl:  # pylint: disable=no-else-return
                self.cache_hits += 1
                logger.debug(
                    f"[CostOptimizer] 缓存命中: {cache_key[:16]}... " f"(命中率: {self.get_cache_hit_rate():.1%})"
                )
                return cached_response
            else:
                # 缓存过期，删除
                del self.cache[cache_key]

        # 缓存未命中
        self.cache_misses += 1
        logger.debug(f"[CostOptimizer] 缓存未命中: {cache_key[:16]}...")
        return None

    def batch_api_calls(self, requests: List[str], max_batch_size: Optional[int] = None) -> List[List[str]]:
        """批量API调用

        白皮书依据: 第十八章 18.3.3 批量调用

        合并多个请求为批次

        Args:
            requests: 请求列表
            max_batch_size: 最大批量大小，None表示使用默认值

        Returns:
            批次列表，每个批次是一个请求列表

        Raises:
            ValueError: 当请求列表为空时
        """
        if not requests:
            raise ValueError("请求列表不能为空")

        batch_size = max_batch_size or self.batch_size

        # 分批
        batches = []
        for i in range(0, len(requests), batch_size):
            batch = requests[i : i + batch_size]
            batches.append(batch)

        self.batch_calls += len(batches)

        logger.info(
            f"[CostOptimizer] 批量调用 - "
            f"请求数: {len(requests)}, "
            f"批次数: {len(batches)}, "
            f"批量大小: {batch_size}"
        )

        return batches

    def use_cheaper_models(self, task_complexity: str, model_prices: Dict[str, float]) -> str:
        """使用更便宜的模型

        根据任务复杂度选择合适的模型

        Args:
            task_complexity: 任务复杂度（simple/medium/complex）
            model_prices: 模型价格表 {model: price}

        Returns:
            推荐的模型名称

        Raises:
            ValueError: 当参数无效时
        """
        if task_complexity not in ["simple", "medium", "complex"]:
            raise ValueError(f"无效的任务复杂度: {task_complexity}，" f"必须是 simple/medium/complex 之一")

        if not model_prices:
            raise ValueError("模型价格表不能为空")

        # 按价格排序
        sorted_models = sorted(model_prices.items(), key=lambda x: x[1])

        # 根据任务复杂度选择模型
        if task_complexity == "simple":
            # 简单任务：使用最便宜的模型
            model = sorted_models[0][0]
        elif task_complexity == "medium":
            # 中等任务：使用中等价格的模型
            mid_index = len(sorted_models) // 2
            model = sorted_models[mid_index][0]
        else:  # complex
            # 复杂任务：使用最贵的模型（性能最好）
            model = sorted_models[-1][0]

        logger.debug(f"[CostOptimizer] 任务复杂度: {task_complexity}, " f"推荐模型: {model} (¥{model_prices[model]}/M)")

        return model

    def compress_prompt(self, prompt: str) -> str:
        """压缩Prompt

        白皮书依据: 第十八章 18.3.4 Prompt压缩

        减少token数量

        Args:
            prompt: 原始Prompt

        Returns:
            压缩后的Prompt
        """
        if not prompt:
            return prompt

        compressed = prompt

        # 移除冗余词汇
        replacements = {
            "请分析": "分析",
            "请判断": "判断",
            "请评估": "评估",
            "根据以上信息": "",
            "根据上述内容": "",
            "股票代码": "代码",
            "交易量": "量",
            "成交量": "量",
            "市盈率": "PE",
            "市净率": "PB",
            "净资产收益率": "ROE",
        }

        for old, new in replacements.items():
            compressed = compressed.replace(old, new)

        # 移除多余空格
        compressed = " ".join(compressed.split())

        # 计算压缩率
        original_len = len(prompt)
        compressed_len = len(compressed)
        compression_ratio = (original_len - compressed_len) / original_len if original_len > 0 else 0

        logger.debug(
            f"[CostOptimizer] Prompt压缩 - "
            f"原始: {original_len}字符, "
            f"压缩后: {compressed_len}字符, "
            f"压缩率: {compression_ratio:.1%}"
        )

        return compressed

    def get_cache_hit_rate(self) -> float:
        """获取缓存命中率

        Returns:
            缓存命中率（0-1）
        """
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.get_cache_hit_rate(),
            "cache_size": len(self.cache),
            "local_model_uses": self.local_model_uses,
            "cloud_model_uses": self.cloud_model_uses,
            "batch_calls": self.batch_calls,
            "cache_ttl": self.cache_ttl,
            "batch_size": self.batch_size,
        }

    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()
        logger.info("[CostOptimizer] 缓存已清空")

    def clear_expired_cache(self) -> int:
        """清理过期缓存

        Returns:
            清理的缓存数量
        """
        current_time = time.time()
        expired_keys = []

        for key, (_, timestamp) in self.cache.items():
            if current_time - timestamp >= self.cache_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.info(f"[CostOptimizer] 清理过期缓存: {len(expired_keys)}个")

        return len(expired_keys)

    def _generate_cache_key(self, request_key: str) -> str:
        """生成缓存键

        Args:
            request_key: 请求键

        Returns:
            缓存键（MD5哈希）
        """
        return hashlib.md5(request_key.encode()).hexdigest()
