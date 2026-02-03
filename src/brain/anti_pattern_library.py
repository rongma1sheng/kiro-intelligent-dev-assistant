"""反向黑名单库

白皮书依据: 第五章 5.3.4 反向黑名单

本模块实现了反向黑名单库，负责：
- 记录失败模式
- 检查因子是否匹配已知失败模式
- 生成避免建议
- 模式匹配和相似度计算

定义: 失败模式库
内容:
- 失败模式描述
- 失败次数统计
- 失败案例列表
- 避免建议

作用:
- 避免重复错误
- 指导因子挖掘
- 提高进化效率

存储: Redis
Key: mia:knowledge:anti_patterns
TTL: 永久
"""

import re
import uuid
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from loguru import logger

from src.brain.darwin_data_models import (
    AntiPattern,
    FailureCase,
    FailureStep,
)
from src.brain.redis_storage import RedisStorageManager


class AntiPatternLibrary:
    """反向黑名单库

    白皮书依据: 第五章 5.3.4 反向黑名单

    记录和管理失败模式，避免重复错误，提高进化效率。

    Attributes:
        redis_storage: Redis存储管理器
        patterns: 模式列表
    """

    # 相似度阈值
    SIMILARITY_THRESHOLD = 0.7

    def __init__(self, redis_storage: RedisStorageManager) -> None:
        """初始化反向黑名单库

        Args:
            redis_storage: Redis存储管理器实例

        Raises:
            ValueError: 当redis_storage为None时
        """
        if redis_storage is None:
            raise ValueError("Redis存储管理器不能为None")

        self._redis_storage = redis_storage
        self._patterns: List[AntiPattern] = []
        self._loaded = False

        logger.info("AntiPatternLibrary初始化完成")

    async def _ensure_loaded(self) -> None:
        """确保已从Redis加载数据"""
        if not self._loaded:
            await self._load_from_redis()
            self._loaded = True

    async def record_failure(
        self,
        factor_expression: str,
        failure_reason: str,
        failure_step: FailureStep,
    ) -> AntiPattern:
        """记录失败模式

        白皮书依据: 第五章 5.3.4 反向黑名单 - 需求4.1-4.4

        如果已存在相似模式，更新失败次数和案例列表；
        否则创建新的反向模式。

        Args:
            factor_expression: 因子表达式
            failure_reason: 失败原因
            failure_step: 失败步骤

        Returns:
            AntiPattern: 记录的反向模式

        Raises:
            ValueError: 当参数为空时
        """
        if not factor_expression:
            raise ValueError("因子表达式不能为空")
        if not failure_reason:
            raise ValueError("失败原因不能为空")

        await self._ensure_loaded()

        # 创建失败案例
        case = FailureCase(
            case_id=str(uuid.uuid4()),
            factor_expression=factor_expression,
            failure_reason=failure_reason,
            failure_step=failure_step,
            timestamp=datetime.now(),
        )

        # 提取模式签名
        signature = self.extract_pattern_signature(factor_expression)

        # 查找相似模式
        existing_pattern = await self._find_similar_pattern(factor_expression)

        if existing_pattern:
            # 更新现有模式
            existing_pattern.failure_count += 1
            existing_pattern.failure_cases.append(case)
            existing_pattern.updated_at = datetime.now()

            # 更新避免建议
            existing_pattern.avoidance_suggestions = await self.generate_avoidance_suggestions(existing_pattern)

            pattern = existing_pattern
            logger.info(f"更新反向模式: {pattern.pattern_id}, 失败次数: {pattern.failure_count}")
        else:
            # 创建新模式
            pattern = AntiPattern(
                pattern_id=str(uuid.uuid4()),
                description=self._generate_description(factor_expression, failure_reason),
                failure_count=1,
                failure_cases=[case],
                avoidance_suggestions=[],
                pattern_signature=signature,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            # 生成避免建议
            pattern.avoidance_suggestions = await self.generate_avoidance_suggestions(pattern)

            self._patterns.append(pattern)
            logger.info(f"创建新反向模式: {pattern.pattern_id}")

        # 保存到Redis
        await self._save_to_redis()

        return pattern

    def _generate_description(
        self,
        factor_expression: str,
        failure_reason: str,
    ) -> str:
        """生成模式描述"""
        # 提取表达式的关键特征
        features = self._extract_features(factor_expression)

        if features:
            return f"包含{', '.join(features)}的因子: {failure_reason}"
        return f"因子模式: {failure_reason}"

    def _extract_features(self, expression: str) -> List[str]:
        """提取表达式特征"""
        features = []

        # 检测常见模式
        if "delay" in expression.lower():
            features.append("延迟函数")
        if "rank" in expression.lower():
            features.append("排名函数")
        if "ts_" in expression.lower():
            features.append("时序函数")
        if "/" in expression:
            features.append("除法运算")
        if "**" in expression or "pow" in expression.lower():
            features.append("幂运算")

        return features

    async def _find_similar_pattern(
        self,
        factor_expression: str,
    ) -> Optional[AntiPattern]:
        """查找相似模式"""
        signature = self.extract_pattern_signature(factor_expression)

        for pattern in self._patterns:
            similarity = self.calculate_similarity(signature, pattern.pattern_signature)
            if similarity >= self.SIMILARITY_THRESHOLD:
                return pattern

        return None

    async def check_pattern(
        self,
        factor_expression: str,
    ) -> Optional[AntiPattern]:
        """检查因子是否匹配已知失败模式

        白皮书依据: 第五章 5.3.4 反向黑名单 - 需求4.5, 4.6

        Args:
            factor_expression: 因子表达式

        Returns:
            AntiPattern: 匹配的失败模式，不存在返回None

        Raises:
            ValueError: 当factor_expression为空时
        """
        if not factor_expression:
            raise ValueError("因子表达式不能为空")

        await self._ensure_loaded()

        signature = self.extract_pattern_signature(factor_expression)

        best_match: Optional[AntiPattern] = None
        best_similarity = 0.0

        for pattern in self._patterns:
            similarity = self.calculate_similarity(signature, pattern.pattern_signature)
            if similarity >= self.SIMILARITY_THRESHOLD and similarity > best_similarity:
                best_match = pattern
                best_similarity = similarity

        if best_match:
            logger.debug(f"匹配到失败模式: {best_match.pattern_id}, 相似度: {best_similarity:.4f}")

        return best_match

    async def get_all_patterns(self) -> List[AntiPattern]:
        """获取所有反向模式

        Returns:
            List[AntiPattern]: 所有反向模式列表
        """
        await self._ensure_loaded()
        return self._patterns.copy()

    async def get_top_failures(self, limit: int = 10) -> List[AntiPattern]:
        """获取失败次数最多的模式

        Args:
            limit: 返回数量限制

        Returns:
            List[AntiPattern]: 失败次数最多的模式列表
        """
        await self._ensure_loaded()

        sorted_patterns = sorted(
            self._patterns,
            key=lambda p: p.failure_count,
            reverse=True,
        )

        return sorted_patterns[:limit]

    async def generate_avoidance_suggestions(
        self,
        pattern: AntiPattern,
    ) -> List[str]:
        """生成避免建议

        白皮书依据: 第五章 5.3.4 反向黑名单 - 需求4.4

        Args:
            pattern: 反向模式

        Returns:
            List[str]: 避免建议列表
        """
        suggestions = []

        # 基于失败次数生成建议
        if pattern.failure_count >= 5:
            suggestions.append(f"该模式已失败{pattern.failure_count}次，强烈建议避免")
        elif pattern.failure_count >= 3:
            suggestions.append(f"该模式已失败{pattern.failure_count}次，建议谨慎使用")

        # 基于失败步骤生成建议
        failure_steps = set()
        for case in pattern.failure_cases:
            failure_steps.add(case.failure_step)

        if FailureStep.FUTURE_FUNCTION_DETECTION in failure_steps:
            suggestions.append("检查是否存在未来函数，避免使用未来数据")

        if FailureStep.ARENA_TEST in failure_steps:
            suggestions.append("该模式在Arena测试中表现不佳，考虑调整参数或结构")

        if FailureStep.FACTOR_ANALYSIS in failure_steps:
            suggestions.append("因子意义分析失败，考虑简化因子表达式")

        # 基于模式特征生成建议
        features = self._extract_features(pattern.pattern_signature)
        for feature in features:
            if feature == "除法运算":
                suggestions.append("注意除法运算可能导致除零错误")
            elif feature == "幂运算":
                suggestions.append("幂运算可能导致数值溢出")

        if not suggestions:
            suggestions.append("建议尝试不同的因子结构")

        return suggestions

    def calculate_similarity(
        self,
        expr1: str,
        expr2: str,
    ) -> float:
        """计算两个表达式的相似度

        白皮书依据: 第五章 5.3.4 反向黑名单 - 需求4.9

        Args:
            expr1: 表达式1
            expr2: 表达式2

        Returns:
            float: 相似度，范围[0, 1]
        """
        if not expr1 or not expr2:
            return 0.0

        if expr1 == expr2:
            return 1.0

        # 使用SequenceMatcher计算相似度
        return SequenceMatcher(None, expr1, expr2).ratio()

    def extract_pattern_signature(self, expression: str) -> str:
        """提取模式签名

        白皮书依据: 第五章 5.3.4 反向黑名单 - 需求4.9

        Args:
            expression: 因子表达式

        Returns:
            str: 模式签名
        """
        if not expression:
            return ""

        # 标准化表达式
        normalized = expression.lower().strip()

        # 移除空白字符
        normalized = re.sub(r"\s+", "", normalized)

        # 替换具体数字为占位符
        normalized = re.sub(r"\d+\.?\d*", "N", normalized)

        # 替换变量名为占位符
        normalized = re.sub(r"\b[a-z_][a-z0-9_]*\b", "V", normalized)

        return normalized

    async def _load_from_redis(self) -> None:
        """从Redis加载数据"""
        pattern_dicts = await self._redis_storage.get_anti_patterns()

        self._patterns = []
        for data in pattern_dicts:
            try:
                pattern = AntiPattern.from_dict(data)
                self._patterns.append(pattern)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"加载反向模式失败: {e}")

        logger.info(f"从Redis加载{len(self._patterns)}个反向模式")

    async def _save_to_redis(self) -> None:
        """保存数据到Redis

        白皮书依据: 第五章 5.3.4 反向黑名单 - 需求4.7, 4.8

        Key: mia:knowledge:anti_patterns
        TTL: 永久
        """
        pattern_dicts = [p.to_dict() for p in self._patterns]
        await self._redis_storage.store_anti_patterns(pattern_dicts)
        logger.debug(f"保存{len(self._patterns)}个反向模式到Redis")

    async def delete_pattern(self, pattern_id: str) -> bool:
        """删除反向模式

        Args:
            pattern_id: 模式ID

        Returns:
            bool: 是否删除成功
        """
        await self._ensure_loaded()

        for i, pattern in enumerate(self._patterns):
            if pattern.pattern_id == pattern_id:
                del self._patterns[i]
                await self._save_to_redis()
                logger.info(f"删除反向模式: {pattern_id}")
                return True

        return False

    async def clear_all(self) -> None:
        """清空所有反向模式"""
        self._patterns = []
        await self._save_to_redis()
        logger.info("清空所有反向模式")

    def pattern_count(self) -> int:
        """获取模式数量"""
        return len(self._patterns)

    async def get_pattern_by_id(self, pattern_id: str) -> Optional[AntiPattern]:
        """按ID获取模式

        Args:
            pattern_id: 模式ID

        Returns:
            AntiPattern: 模式，不存在返回None
        """
        await self._ensure_loaded()

        for pattern in self._patterns:
            if pattern.pattern_id == pattern_id:
                return pattern

        return None

    async def get_patterns_by_failure_step(
        self,
        failure_step: FailureStep,
    ) -> List[AntiPattern]:
        """按失败步骤获取模式

        Args:
            failure_step: 失败步骤

        Returns:
            List[AntiPattern]: 匹配的模式列表
        """
        await self._ensure_loaded()

        result = []
        for pattern in self._patterns:
            for case in pattern.failure_cases:
                if case.failure_step == failure_step:
                    result.append(pattern)
                    break

        return result

    async def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict: 统计信息
        """
        await self._ensure_loaded()

        total_failures = sum(p.failure_count for p in self._patterns)

        # 按失败步骤统计
        step_counts: Dict[str, int] = {}
        for pattern in self._patterns:
            for case in pattern.failure_cases:
                step_name = case.failure_step.value
                step_counts[step_name] = step_counts.get(step_name, 0) + 1

        return {
            "total_patterns": len(self._patterns),
            "total_failures": total_failures,
            "avg_failures_per_pattern": total_failures / len(self._patterns) if self._patterns else 0,
            "failures_by_step": step_counts,
        }
