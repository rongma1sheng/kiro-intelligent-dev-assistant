"""Data models for Factor-to-Strategy Conversion System

白皮书依据: 第四章 4.2.2 因子组合策略生成与斯巴达考核
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

import numpy as np


class StrategyType(Enum):
    """Strategy types

    白皮书依据: 第四章 4.2.2 策略类型
    """

    PURE_FACTOR = "pure_factor"  # 纯因子策略
    FACTOR_COMBO = "factor_combo"  # 因子组合策略
    MARKET_NEUTRAL = "market_neutral"  # 市场中性策略
    DYNAMIC_WEIGHT = "dynamic_weight"  # 动态权重策略


@dataclass
class FactorCharacteristics:
    """Factor characteristics for parameter optimization

    白皮书依据: 第四章 4.1 因子特征分析

    Attributes:
        factor_id: Factor identifier
        ic: Information coefficient
        ir: Information ratio
        turnover: Factor turnover rate
        stability: Factor stability score
        arena_score: Overall Arena score
        hell_survival_rate: Hell Track survival rate
        cross_market_adaptability: Cross-market adaptability score
        category: Factor category (technical, fundamental, etc.)
    """

    factor_id: str
    ic: float
    ir: float
    turnover: float
    stability: float
    arena_score: float
    hell_survival_rate: float
    cross_market_adaptability: float
    category: str

    def __post_init__(self):
        """Validate factor characteristics"""
        if not -1.0 <= self.ic <= 1.0:
            raise ValueError(f"IC must be in [-1, 1], got {self.ic}")

        if self.ir < 0:
            raise ValueError(f"IR must be non-negative, got {self.ir}")

        if not 0.0 <= self.turnover <= 1.0:
            raise ValueError(f"Turnover must be in [0, 1], got {self.turnover}")

        if not 0.0 <= self.stability <= 1.0:
            raise ValueError(f"Stability must be in [0, 1], got {self.stability}")

        if not 0.0 <= self.arena_score <= 1.0:
            raise ValueError(f"Arena score must be in [0, 1], got {self.arena_score}")

        if not 0.0 <= self.hell_survival_rate <= 1.0:
            raise ValueError(f"Hell survival rate must be in [0, 1], got {self.hell_survival_rate}")

        if not 0.0 <= self.cross_market_adaptability <= 1.0:
            raise ValueError(f"Cross-market adaptability must be in [0, 1], got {self.cross_market_adaptability}")


@dataclass
class StrategyParameters:
    """Strategy parameters optimized based on factor characteristics

    白皮书依据: 第四章 4.2.2 策略参数设置

    Attributes:
        rebalance_frequency: Rebalance frequency in days
        position_limit: Maximum position size per stock (0-1)
        max_positions: Maximum number of positions
        entry_threshold: Factor quantile threshold for entry (0-1)
        exit_threshold: Factor quantile threshold for exit (0-1)
        stop_loss: Stop loss percentage (0-1)
        take_profit: Take profit percentage (0-1)
        leverage: Leverage multiplier (>= 1.0)
    """

    rebalance_frequency: int
    position_limit: float
    max_positions: int
    entry_threshold: float
    exit_threshold: float
    stop_loss: float
    take_profit: float
    leverage: float = 1.0

    def __post_init__(self):
        """Validate strategy parameters"""
        if self.rebalance_frequency < 1:
            raise ValueError(f"Rebalance frequency must be >= 1, got {self.rebalance_frequency}")

        if not 0.0 < self.position_limit <= 1.0:
            raise ValueError(f"Position limit must be in (0, 1], got {self.position_limit}")

        if self.max_positions < 1:
            raise ValueError(f"Max positions must be >= 1, got {self.max_positions}")

        if not 0.0 <= self.entry_threshold <= 1.0:
            raise ValueError(f"Entry threshold must be in [0, 1], got {self.entry_threshold}")

        if not 0.0 <= self.exit_threshold <= 1.0:
            raise ValueError(f"Exit threshold must be in [0, 1], got {self.exit_threshold}")

        if not 0.0 < self.stop_loss <= 1.0:
            raise ValueError(f"Stop loss must be in (0, 1], got {self.stop_loss}")

        if not 0.0 < self.take_profit <= 1.0:
            raise ValueError(f"Take profit must be in (0, 1], got {self.take_profit}")

        if self.leverage < 1.0:
            raise ValueError(f"Leverage must be >= 1.0, got {self.leverage}")


@dataclass
class StrategyTemplate:
    """Strategy code template

    白皮书依据: 第四章 4.2.2 策略模板

    Attributes:
        strategy_type: Type of strategy
        template_code: Python code template with placeholders
        required_factors: Number of factors required
        description: Template description
    """

    strategy_type: StrategyType
    template_code: str
    required_factors: int
    description: str

    def __post_init__(self):
        """Validate strategy template"""
        if self.required_factors < 1:
            raise ValueError(f"Required factors must be >= 1, got {self.required_factors}")

        if not self.template_code:
            raise ValueError("Template code cannot be empty")


@dataclass
class GeneratedStrategy:
    """Generated strategy from factors

    白皮书依据: 第四章 4.2.2 生成的策略

    Attributes:
        strategy_id: Unique strategy identifier
        strategy_name: Human-readable strategy name
        strategy_type: Type of strategy
        source_factors: List of source factor IDs
        strategy_code: Complete Python strategy code
        parameters: Strategy parameters
        expected_sharpe: Expected Sharpe ratio
        expected_return: Expected annual return
        expected_drawdown: Expected maximum drawdown
        arena_metadata: Metadata from Arena testing of source factors
        created_at: Creation timestamp
        status: Strategy status (candidate, arena_testing, etc.)
    """

    strategy_id: str
    strategy_name: str
    strategy_type: StrategyType
    source_factors: List[str]
    strategy_code: str
    parameters: StrategyParameters
    expected_sharpe: float
    expected_return: float
    expected_drawdown: float
    arena_metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "candidate"

    def __post_init__(self):
        """Validate generated strategy"""
        if not self.strategy_id:
            raise ValueError("Strategy ID cannot be empty")

        if not self.strategy_name:
            raise ValueError("Strategy name cannot be empty")

        if not self.source_factors:
            raise ValueError("Source factors cannot be empty")

        if not self.strategy_code:
            raise ValueError("Strategy code cannot be empty")

        if self.expected_sharpe < 0:
            raise ValueError(f"Expected Sharpe must be non-negative, got {self.expected_sharpe}")

        if not 0.0 <= self.expected_drawdown <= 1.0:
            raise ValueError(f"Expected drawdown must be in [0, 1], got {self.expected_drawdown}")

        if self.status not in ["candidate", "arena_testing", "simulation", "certified", "retired"]:
            raise ValueError(f"Invalid status: {self.status}")


@dataclass
class FactorCorrelationMatrix:
    """Factor correlation matrix for redundancy detection

    白皮书依据: 第四章 4.2.2 因子相关性分析

    Attributes:
        factor_ids: List of factor IDs
        correlation_matrix: Correlation matrix (numpy array)
        timestamp: Calculation timestamp
    """

    factor_ids: List[str]
    correlation_matrix: np.ndarray
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate correlation matrix"""
        if not self.factor_ids:
            raise ValueError("Factor IDs cannot be empty")

        n = len(self.factor_ids)
        if self.correlation_matrix.shape != (n, n):
            raise ValueError(
                f"Correlation matrix shape {self.correlation_matrix.shape} " f"does not match factor count {n}"
            )

        # Check if matrix is symmetric
        if not np.allclose(self.correlation_matrix, self.correlation_matrix.T):
            raise ValueError("Correlation matrix must be symmetric")

        # Check if diagonal is all 1s
        if not np.allclose(np.diag(self.correlation_matrix), 1.0):
            raise ValueError("Correlation matrix diagonal must be all 1s")

        # Check if values are in [-1, 1]
        if not np.all((-1.0 <= self.correlation_matrix) & (self.correlation_matrix <= 1.0)):
            raise ValueError("Correlation values must be in [-1, 1]")

    def get_correlation(self, factor_id1: str, factor_id2: str) -> float:
        """Get correlation between two factors

        Args:
            factor_id1: First factor ID
            factor_id2: Second factor ID

        Returns:
            Correlation coefficient

        Raises:
            ValueError: If factor IDs not found
        """
        try:
            idx1 = self.factor_ids.index(factor_id1)
            idx2 = self.factor_ids.index(factor_id2)
            return float(self.correlation_matrix[idx1, idx2])
        except ValueError as e:
            raise ValueError(f"Factor ID not found: {e}")  # pylint: disable=w0707

    def get_highly_correlated_pairs(self, threshold: float = 0.7) -> List[tuple]:
        """Get pairs of highly correlated factors

        Args:
            threshold: Correlation threshold (default 0.7)

        Returns:
            List of (factor_id1, factor_id2, correlation) tuples
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be in [0, 1], got {threshold}")

        pairs = []
        n = len(self.factor_ids)

        for i in range(n):
            for j in range(i + 1, n):
                corr = abs(self.correlation_matrix[i, j])
                if corr >= threshold:
                    pairs.append((self.factor_ids[i], self.factor_ids[j], float(self.correlation_matrix[i, j])))

        return pairs
