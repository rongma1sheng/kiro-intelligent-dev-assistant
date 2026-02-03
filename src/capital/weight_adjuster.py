"""权重调整器

白皮书依据: 第一章 1.3 资本分配
"""

from typing import Any, Dict, List

from loguru import logger


class WeightAdjuster:
    """权重调整器

    白皮书依据: 第一章 1.3 资本分配

    职责：
    - 基于策略表现动态调整权重
    - 确保权重约束（总和=1.0，单个∈[0.05, 0.40]）
    - 记录权重调整历史
    """

    def __init__(self, min_weight: float = 0.05, max_weight: float = 0.40, adjustment_rate: float = 0.1):
        """初始化权重调整器

        Args:
            min_weight: 最小权重，默认0.05
            max_weight: 最大权重，默认0.40
            adjustment_rate: 调整速率，默认0.1（每次调整最多10%）
        """
        if not 0 < min_weight < max_weight <= 1.0:
            raise ValueError(f"权重约束无效: min_weight={min_weight}, max_weight={max_weight}")

        self.min_weight = min_weight
        self.max_weight = max_weight
        self.adjustment_rate = adjustment_rate

        # 权重调整历史
        self.weight_history: List[Dict[str, Any]] = []

        logger.info(
            f"WeightAdjuster初始化完成 - " f"权重范围: [{min_weight}, {max_weight}], " f"调整速率: {adjustment_rate}"
        )

    async def adjust_weights(self, strategies: List[Any], performance_metrics: Dict[str, float]) -> Dict[str, float]:
        """调整策略权重

        白皮书依据: Requirement 4

        基于策略表现调整权重：
        - 表现优于预期：增加权重
        - 表现低于预期：降低权重

        约束条件：
        - sum(weights) = 1.0
        - 0.05 <= weight <= 0.40

        Args:
            strategies: 策略列表
            performance_metrics: 策略表现指标 {strategy_name: performance_score}
                performance_score > 0: 表现优于预期
                performance_score < 0: 表现低于预期
                performance_score = 0: 表现符合预期

        Returns:
            策略权重字典 {strategy_name: weight}

        Raises:
            ValueError: 当策略列表为空时
            WeightConstraintViolationError: 当无法满足权重约束时
        """
        if not strategies:
            raise ValueError("策略列表不能为空")

        try:
            logger.info(f"开始调整{len(strategies)}个策略的权重")

            # 1. 初始化权重（均等分配）
            initial_weights = self._initialize_weights(strategies)

            # 2. 如果没有表现指标，返回均等权重
            if not performance_metrics:
                logger.info("无表现指标，使用均等权重")
                await self.record_weight_history(initial_weights)
                return initial_weights

            # 3. 根据表现调整权重
            adjusted_weights = self._adjust_based_on_performance(initial_weights, performance_metrics)

            # 4. 应用权重约束
            constrained_weights = self._apply_constraints(adjusted_weights)

            # 5. 归一化权重（确保总和=1.0）
            normalized_weights = self._normalize_weights(constrained_weights)

            # 6. 验证权重
            self._validate_weights(normalized_weights)

            # 7. 记录权重历史
            await self.record_weight_history(normalized_weights)

            logger.info(f"权重调整完成: {normalized_weights}")
            return normalized_weights

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"权重调整失败: {e}")
            # 返回均等权重作为后备
            fallback_weights = self._initialize_weights(strategies)
            logger.warning(f"使用均等权重作为后备: {fallback_weights}")
            return fallback_weights

    async def record_weight_history(self, weights: Dict[str, float]) -> None:
        """记录权重调整历史

        白皮书依据: Requirement 4.7

        Args:
            weights: 权重字典
        """
        from datetime import datetime  # pylint: disable=import-outside-toplevel

        record = {"weights": weights.copy(), "timestamp": datetime.now().isoformat()}

        self.weight_history.append(record)

        # 保留最近1000条记录
        if len(self.weight_history) > 1000:
            self.weight_history = self.weight_history[-1000:]

        logger.debug(f"权重历史已记录: {record}")

    def get_weight_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取权重调整历史

        Args:
            limit: 返回的记录数量

        Returns:
            权重历史列表
        """
        return self.weight_history[-limit:]

    def _initialize_weights(self, strategies: List[Any]) -> Dict[str, float]:
        """初始化权重（均等分配）（内部方法）

        Args:
            strategies: 策略列表

        Returns:
            初始权重字典
        """
        n = len(strategies)
        equal_weight = 1.0 / n

        weights = {}
        for strategy in strategies:
            strategy_name = self._get_strategy_name(strategy)
            weights[strategy_name] = equal_weight

        return weights

    def _adjust_based_on_performance(
        self, weights: Dict[str, float], performance_metrics: Dict[str, float]
    ) -> Dict[str, float]:
        """根据表现调整权重（内部方法）

        Args:
            weights: 当前权重
            performance_metrics: 表现指标

        Returns:
            调整后的权重
        """
        adjusted_weights = weights.copy()

        for strategy_name, current_weight in weights.items():
            performance = performance_metrics.get(strategy_name, 0.0)

            # 根据表现调整权重
            if performance > 0:
                # 表现优于预期，增加权重
                adjustment = current_weight * self.adjustment_rate * performance
                adjusted_weights[strategy_name] = current_weight + adjustment
            elif performance < 0:
                # 表现低于预期，降低权重
                adjustment = current_weight * self.adjustment_rate * abs(performance)
                adjusted_weights[strategy_name] = current_weight - adjustment
            # performance == 0: 保持不变

        return adjusted_weights

    def _apply_constraints(self, weights: Dict[str, float]) -> Dict[str, float]:
        """应用权重约束（内部方法）

        确保每个权重在 [min_weight, max_weight] 范围内

        Args:
            weights: 权重字典

        Returns:
            约束后的权重
        """
        constrained_weights = {}

        for strategy_name, weight in weights.items():
            # 应用最小和最大权重约束
            constrained_weight = max(self.min_weight, min(self.max_weight, weight))
            constrained_weights[strategy_name] = constrained_weight

        return constrained_weights

    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """归一化权重（内部方法）

        确保所有权重之和 = 1.0

        Args:
            weights: 权重字典

        Returns:
            归一化后的权重
        """
        total_weight = sum(weights.values())

        if total_weight == 0:
            # 如果总权重为0，返回均等权重
            n = len(weights)
            return {name: 1.0 / n for name in weights.keys()}

        # 归一化
        normalized_weights = {name: weight / total_weight for name, weight in weights.items()}

        # 再次应用约束（归一化后可能违反约束）
        # 如果归一化后某些权重低于min_weight，需要重新调整
        needs_readjustment = any(w < self.min_weight for w in normalized_weights.values())

        if needs_readjustment:
            normalized_weights = self._readjust_weights(normalized_weights)

        return normalized_weights

    def _readjust_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """重新调整权重以满足约束（内部方法）

        当归一化后的权重违反约束时，重新调整

        Args:
            weights: 权重字典

        Returns:
            重新调整后的权重
        """
        adjusted_weights = {}
        below_min = []
        above_min = []

        # 分类权重
        for name, weight in weights.items():
            if weight < self.min_weight:
                below_min.append(name)
                adjusted_weights[name] = self.min_weight
            else:
                above_min.append(name)
                adjusted_weights[name] = weight

        if not below_min:
            return adjusted_weights

        # 计算需要补偿的权重
        deficit = sum(self.min_weight - weights[name] for name in below_min)

        # 从高于最小权重的策略中扣除
        if above_min:
            total_above = sum(adjusted_weights[name] for name in above_min)
            for name in above_min:
                reduction = (adjusted_weights[name] / total_above) * deficit
                adjusted_weights[name] -= reduction

                # 确保不低于最小权重
                if adjusted_weights[name] < self.min_weight:
                    adjusted_weights[name] = self.min_weight

        # 再次归一化
        total = sum(adjusted_weights.values())
        if abs(total - 1.0) > 0.001:
            adjusted_weights = {name: weight / total for name, weight in adjusted_weights.items()}

        return adjusted_weights

    def _validate_weights(self, weights: Dict[str, float]) -> None:
        """验证权重（内部方法）

        Args:
            weights: 权重字典

        Raises:
            WeightConstraintViolationError: 当权重违反约束时
        """
        # 检查总和
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 0.001:
            raise WeightConstraintViolationError(f"权重总和不等于1.0: {total_weight}")

        # 检查范围
        for name, weight in weights.items():
            if weight < 0:
                raise WeightConstraintViolationError(f"权重不能为负: {name}={weight}")
            if weight < self.min_weight - 0.001:
                raise WeightConstraintViolationError(f"权重低于最小值: {name}={weight} < {self.min_weight}")
            if weight > self.max_weight + 0.001:
                raise WeightConstraintViolationError(f"权重超过最大值: {name}={weight} > {self.max_weight}")

    def _get_strategy_name(self, strategy: Any) -> str:
        """获取策略名称（内部方法）

        Args:
            strategy: 策略对象或字典

        Returns:
            策略名称
        """
        if isinstance(strategy, dict):  # pylint: disable=no-else-return
            return strategy.get("strategy_name", "unknown")
        elif hasattr(strategy, "name"):
            return strategy.name
        elif hasattr(strategy, "strategy_name"):
            return strategy.strategy_name
        else:
            return str(strategy)


class WeightConstraintViolationError(Exception):
    """权重约束违反异常"""
