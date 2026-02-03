"""风格轮动因子挖掘器模块

白皮书依据: 第四章 4.1.14 风格轮动因子挖掘器
"""

from .style_rotation_miner import StyleRotationFactorMiner
from .style_rotation_operators import (
    StyleRotationConfig,
    dividend_yield_cycle,
    factor_crowding_index,
    low_volatility_anomaly,
    momentum_reversal_switch,
    quality_junk_rotation,
    sector_rotation_signal,
    size_premium_cycle,
    value_growth_spread,
)

__all__ = [
    "StyleRotationFactorMiner",
    "StyleRotationConfig",
    "value_growth_spread",
    "size_premium_cycle",
    "momentum_reversal_switch",
    "quality_junk_rotation",
    "low_volatility_anomaly",
    "dividend_yield_cycle",
    "sector_rotation_signal",
    "factor_crowding_index",
]
