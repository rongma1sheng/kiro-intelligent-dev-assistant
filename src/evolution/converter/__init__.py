"""Factor-to-Strategy Conversion System

白皮书依据: 第四章 4.2.2 因子组合策略生成与斯巴达考核

This module implements the conversion of Arena-validated factors into tradeable strategies.
"""

from src.evolution.converter.correlation_analyzer import CorrelationAnalyzer
from src.evolution.converter.data_models import (
    FactorCharacteristics,
    FactorCorrelationMatrix,
    GeneratedStrategy,
    StrategyParameters,
    StrategyTemplate,
    StrategyType,
)
from src.evolution.converter.factor_to_strategy_converter import FactorToStrategyConverter
from src.evolution.converter.parameter_optimizer import ParameterOptimizer

__all__ = [
    "StrategyTemplate",
    "StrategyType",
    "FactorCharacteristics",
    "StrategyParameters",
    "GeneratedStrategy",
    "FactorCorrelationMatrix",
    "FactorToStrategyConverter",
    "CorrelationAnalyzer",
    "ParameterOptimizer",
]
