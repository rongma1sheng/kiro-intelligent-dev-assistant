"""Parameter Optimizer for Strategy Generation

白皮书依据: 第四章 4.2.2 策略参数优化
"""

from typing import List

from loguru import logger

from src.evolution.converter.data_models import (
    FactorCharacteristics,
    StrategyParameters,
    StrategyType,
)


class ParameterOptimizer:
    """Optimizes strategy parameters based on factor characteristics

    白皮书依据: 第四章 4.2.2 策略参数优化

    This class determines optimal strategy parameters (rebalance frequency,
    position limits, thresholds, etc.) based on factor characteristics like
    IC, IR, turnover, stability, and Arena test results.
    """

    def __init__(self):
        """Initialize parameter optimizer"""
        logger.info("Initialized ParameterOptimizer")

    async def optimize_parameters(
        self, factor_characteristics: List[FactorCharacteristics], strategy_type: StrategyType
    ) -> StrategyParameters:
        """Optimize strategy parameters based on factor characteristics

        白皮书依据: 第四章 4.2.2 参数优化算法

        Args:
            factor_characteristics: List of factor characteristics
            strategy_type: Type of strategy being generated

        Returns:
            Optimized strategy parameters

        Raises:
            ValueError: If inputs are invalid
        """
        if not factor_characteristics:
            raise ValueError("Factor characteristics cannot be empty")

        logger.info(
            f"Optimizing parameters for {strategy_type.value} strategy " f"with {len(factor_characteristics)} factors"
        )

        # Calculate aggregate metrics
        avg_turnover = sum(fc.turnover for fc in factor_characteristics) / len(factor_characteristics)
        avg_stability = sum(fc.stability for fc in factor_characteristics) / len(factor_characteristics)
        avg_arena_score = sum(fc.arena_score for fc in factor_characteristics) / len(factor_characteristics)
        avg_hell_survival = sum(fc.hell_survival_rate for fc in factor_characteristics) / len(factor_characteristics)

        # Optimize rebalance frequency based on turnover
        rebalance_frequency = self._optimize_rebalance_frequency(avg_turnover)

        # Optimize position limit based on stability and Arena score
        position_limit = self._optimize_position_limit(avg_stability, avg_arena_score, strategy_type)

        # Optimize max positions based on strategy type
        max_positions = self._optimize_max_positions(strategy_type, len(factor_characteristics))

        # Optimize entry/exit thresholds based on IC
        entry_threshold, exit_threshold = self._optimize_thresholds(factor_characteristics, strategy_type)

        # Optimize stop loss based on Hell Track survival rate
        stop_loss = self._optimize_stop_loss(avg_hell_survival)

        # Optimize take profit based on Arena score
        take_profit = self._optimize_take_profit(avg_arena_score)

        # Leverage is always 1.0 for safety
        leverage = 1.0

        parameters = StrategyParameters(
            rebalance_frequency=rebalance_frequency,
            position_limit=position_limit,
            max_positions=max_positions,
            entry_threshold=entry_threshold,
            exit_threshold=exit_threshold,
            stop_loss=stop_loss,
            take_profit=take_profit,
            leverage=leverage,
        )

        logger.info(
            f"Optimized parameters: rebalance={rebalance_frequency}d, "
            f"position_limit={position_limit:.2%}, max_positions={max_positions}, "
            f"entry_threshold={entry_threshold:.2f}, exit_threshold={exit_threshold:.2f}"
        )

        return parameters

    def _optimize_rebalance_frequency(self, avg_turnover: float) -> int:
        """Optimize rebalance frequency based on factor turnover

        白皮书依据: 第四章 4.2.2 调仓频率优化

        High turnover factors → more frequent rebalancing
        Low turnover factors → less frequent rebalancing

        Args:
            avg_turnover: Average factor turnover (0-1)

        Returns:
            Rebalance frequency in days
        """
        if avg_turnover >= 0.8:  # pylint: disable=no-else-return
            return 1  # Daily rebalance for high turnover
        elif avg_turnover >= 0.5:
            return 3  # Every 3 days
        elif avg_turnover >= 0.3:
            return 5  # Weekly rebalance
        elif avg_turnover >= 0.1:
            return 10  # Every 2 weeks
        else:
            return 20  # Monthly rebalance for low turnover

    def _optimize_position_limit(
        self, avg_stability: float, avg_arena_score: float, strategy_type: StrategyType
    ) -> float:
        """Optimize position limit based on stability and Arena score

        白皮书依据: 第四章 4.2.2 仓位限制优化

        Higher stability + higher Arena score → larger position limit

        Args:
            avg_stability: Average factor stability (0-1)
            avg_arena_score: Average Arena score (0-1)
            strategy_type: Type of strategy

        Returns:
            Position limit (0-1)
        """
        # Base position limit
        base_limit = 0.05  # 5%

        # Adjust based on stability and Arena score
        quality_score = (avg_stability + avg_arena_score) / 2

        if quality_score >= 0.8:
            multiplier = 2.0  # Up to 10%
        elif quality_score >= 0.6:
            multiplier = 1.5  # Up to 7.5%
        else:
            multiplier = 1.0  # Stay at 5%

        # Adjust based on strategy type
        if strategy_type == StrategyType.PURE_FACTOR:
            type_multiplier = 1.0
        elif strategy_type == StrategyType.FACTOR_COMBO:
            type_multiplier = 0.8  # More conservative for combos
        elif strategy_type == StrategyType.MARKET_NEUTRAL:
            type_multiplier = 1.2  # Can be more aggressive for market neutral
        else:  # DYNAMIC_WEIGHT
            type_multiplier = 0.9

        position_limit = min(base_limit * multiplier * type_multiplier, 0.15)  # Cap at 15%

        return position_limit

    def _optimize_max_positions(self, strategy_type: StrategyType, num_factors: int) -> int:
        """Optimize maximum number of positions

        白皮书依据: 第四章 4.2.2 持仓数量优化

        Args:
            strategy_type: Type of strategy
            num_factors: Number of factors in strategy

        Returns:
            Maximum number of positions
        """
        if strategy_type == StrategyType.PURE_FACTOR:  # pylint: disable=no-else-return
            return 20  # Pure factor can hold more positions
        elif strategy_type == StrategyType.FACTOR_COMBO:
            return max(10, 15 - num_factors)  # Fewer positions for more factors
        elif strategy_type == StrategyType.MARKET_NEUTRAL:
            return 30  # Market neutral needs more positions for hedging
        else:  # DYNAMIC_WEIGHT
            return 15

    def _optimize_thresholds(
        self, factor_characteristics: List[FactorCharacteristics], strategy_type: StrategyType
    ) -> tuple:
        """Optimize entry and exit thresholds

        白皮书依据: 第四章 4.2.2 阈值优化

        Args:
            factor_characteristics: List of factor characteristics
            strategy_type: Type of strategy

        Returns:
            Tuple of (entry_threshold, exit_threshold)
        """
        # Calculate average IC
        avg_ic = sum(abs(fc.ic) for fc in factor_characteristics) / len(factor_characteristics)

        # Higher IC → more aggressive thresholds
        if avg_ic >= 0.08:
            entry_threshold = 0.7  # Top 30%
            exit_threshold = 0.3  # Bottom 30%
        elif avg_ic >= 0.05:
            entry_threshold = 0.75  # Top 25%
            exit_threshold = 0.25  # Bottom 25%
        elif avg_ic >= 0.03:
            entry_threshold = 0.8  # Top 20%
            exit_threshold = 0.2  # Bottom 20%
        else:
            entry_threshold = 0.85  # Top 15%
            exit_threshold = 0.15  # Bottom 15%

        # Adjust for strategy type
        if strategy_type == StrategyType.MARKET_NEUTRAL:
            # Market neutral needs symmetric thresholds
            entry_threshold = 0.8
            exit_threshold = 0.2

        return entry_threshold, exit_threshold

    def _optimize_stop_loss(self, avg_hell_survival: float) -> float:
        """Optimize stop loss based on Hell Track survival rate

        白皮书依据: 第四章 4.2.2 止损优化

        Higher survival rate → tighter stop loss (factor is more resilient)
        Lower survival rate → wider stop loss (give more room)

        Args:
            avg_hell_survival: Average Hell Track survival rate (0-1)

        Returns:
            Stop loss percentage (0-1)
        """
        if avg_hell_survival >= 0.8:  # pylint: disable=no-else-return
            return 0.08  # 8% stop loss
        elif avg_hell_survival >= 0.6:
            return 0.10  # 10% stop loss
        elif avg_hell_survival >= 0.4:
            return 0.12  # 12% stop loss
        else:
            return 0.15  # 15% stop loss

    def _optimize_take_profit(self, avg_arena_score: float) -> float:
        """Optimize take profit based on Arena score

        白皮书依据: 第四章 4.2.2 止盈优化

        Higher Arena score → higher take profit target

        Args:
            avg_arena_score: Average Arena score (0-1)

        Returns:
            Take profit percentage (0-1)
        """
        if avg_arena_score >= 0.8:  # pylint: disable=no-else-return
            return 0.20  # 20% take profit
        elif avg_arena_score >= 0.7:
            return 0.15  # 15% take profit
        elif avg_arena_score >= 0.6:
            return 0.12  # 12% take profit
        else:
            return 0.10  # 10% take profit
