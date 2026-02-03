"""资本分配模块

白皮书依据: 第一章 1.3 资本分配
核心哲学: 资本物理 (Capital Physics)

本模块实现MIA系统的资本分配功能，根据AUM动态选择策略并调整权重。
"""

from src.capital.aum_sensor import AUMSensor
from src.capital.capital_allocator import CapitalAllocator
from src.capital.strategy_selector import StrategySelector
from src.capital.weight_adjuster import WeightAdjuster

__all__ = [
    "CapitalAllocator",
    "AUMSensor",
    "StrategySelector",
    "WeightAdjuster",
]
