"""替代数据因子挖掘模块

白皮书依据: 第四章 4.1.3 - 替代数据因子挖掘器

本模块提供基于替代数据源的因子挖掘能力，包括：
- 卫星数据
- 社交媒体数据
- 网络流量数据
- 供应链数据
- 人流量数据
- 新闻数据
- 搜索趋势数据
- 航运数据
"""

from .alternative_data_miner import AlternativeDataConfig, AlternativeDataFactorMiner
from .alternative_data_operators import AlternativeDataOperatorRegistry, DataQualityError, OperatorError

__all__ = [
    "AlternativeDataFactorMiner",
    "AlternativeDataConfig",
    "AlternativeDataOperatorRegistry",
    "OperatorError",
    "DataQualityError",
]
