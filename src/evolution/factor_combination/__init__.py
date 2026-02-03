"""因子组合与交互因子挖掘器模块

白皮书依据: 第四章 4.1.15 因子组合与交互因子挖掘器
"""

from .factor_combination_miner import FactorCombinationInteractionMiner
from .factor_combination_operators import (
    FactorCombinationConfig,
    conditional_factor_exposure,
    factor_interaction_term,
    factor_neutralization,
    factor_timing_signal,
    multi_factor_synergy,
    nonlinear_factor_combination,
)

__all__ = [
    "FactorCombinationInteractionMiner",
    "FactorCombinationConfig",
    "factor_interaction_term",
    "nonlinear_factor_combination",
    "conditional_factor_exposure",
    "factor_timing_signal",
    "multi_factor_synergy",
    "factor_neutralization",
]
