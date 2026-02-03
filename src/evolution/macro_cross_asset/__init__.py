"""宏观与跨资产因子挖掘器模块

白皮书依据: 第四章 4.1.15 - 宏观与跨资产因子挖掘器

本模块实现基于宏观经济和跨资产视角的因子挖掘，捕捉系统性风险和资产配置机会。

Author: MIA Team
Date: 2026-01-25
"""

from src.evolution.macro_cross_asset.macro_cross_asset_miner import MacroCrossAssetConfig, MacroCrossAssetFactorMiner
from src.evolution.macro_cross_asset.macro_cross_asset_operators import (
    DataQualityError,
    MacroCrossAssetOperatorRegistry,
    OperatorError,
)

__all__ = [
    "MacroCrossAssetFactorMiner",
    "MacroCrossAssetConfig",
    "MacroCrossAssetOperatorRegistry",
    "OperatorError",
    "DataQualityError",
]
