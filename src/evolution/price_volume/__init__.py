"""量价关系因子挖掘模块

白皮书依据: 第四章 4.1.11 - 量价关系因子挖掘器

本模块提供基于量价关系的因子挖掘能力，包括：
- 量价相关性分析
- OBV背离检测
- VWAP偏离度
- 成交量加权动量
- 价量趋势分析
- 累积派发指标
- 资金流量指数
- 成交量激增模式
- 价量突破检测
- 成交量剖面支撑
- Tick成交量分析
- 成交量加权RSI
"""

from .price_volume_miner import PriceVolumeConfig, PriceVolumeRelationshipFactorMiner
from .price_volume_operators import DataQualityError, OperatorError, PriceVolumeOperatorRegistry

__all__ = [
    "PriceVolumeRelationshipFactorMiner",
    "PriceVolumeConfig",
    "PriceVolumeOperatorRegistry",
    "OperatorError",
    "DataQualityError",
]
