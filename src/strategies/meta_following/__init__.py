"""Meta-Following策略模块

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Following系

跟随策略系列：
- S06 Dragon Tiger (龙虎榜): 解析龙虎榜数据跟随知名游资席位
- S10 Northbound (北向): 实时监控北向资金流向跟随外资重仓股
- S15 Algo Hunter (主力雷达): AMD本地模型识别冰山单与吸筹行为
"""

from src.strategies.meta_following.s06_dragon_tiger import S06DragonTigerStrategy
from src.strategies.meta_following.s10_northbound import S10NorthboundStrategy
from src.strategies.meta_following.s15_algo_hunter import S15AlgoHunterStrategy

__all__ = [
    "S06DragonTigerStrategy",
    "S10NorthboundStrategy",
    "S15AlgoHunterStrategy",
]
