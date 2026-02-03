"""Meta-MeanReversion策略模块

白皮书依据: 第六章 5.2 模块化军火库 - Meta-MeanReversion系

回归策略系列：
- S01 Retracement (回马枪): 强势股缩量回调至关键均线的潜伏策略
- S05 Dynamic Grid (网格): 震荡市AI预测支撑压力位高抛低吸
- S11 Fallen Angel (堕落天使): 基本面良好但情绪错杀的超跌反弹
"""

from src.strategies.meta_mean_reversion.s01_retracement import S01RetracementStrategy
from src.strategies.meta_mean_reversion.s05_dynamic_grid import S05DynamicGridStrategy
from src.strategies.meta_mean_reversion.s11_fallen_angel import S11FallenAngelStrategy

__all__ = [
    "S01RetracementStrategy",
    "S05DynamicGridStrategy",
    "S11FallenAngelStrategy",
]
