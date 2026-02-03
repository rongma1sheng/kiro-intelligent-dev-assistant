"""策略模块

白皮书依据: 第四章 4.2 斯巴达竞技场
白皮书依据: 第六章 5.2 模块化军火库

包含5大元策略系列，共15个具体战术模式：
- Meta-Momentum (动量系): S02, S07, S13
- Meta-MeanReversion (回归系): S01, S05, S11
- Meta-Following (跟随系): S06, S10, S15
- Meta-Arbitrage (套利系): S09, S14, S17, S18, S19
- Meta-Event (事件系): S16
"""

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import ArenaTestResult, Position, Signal, StrategyConfig, StrategyMetadata

# Meta-Arbitrage策略
from src.strategies.meta_arbitrage import (
    S09CBScalperStrategy,
    S14CrossDomainArbStrategy,
    S17DerivativesLinkageStrategy,
    S18FutureTrendStrategy,
    S19OptionSniperStrategy,
)

# Meta-Event策略
from src.strategies.meta_event import (
    S16ThemeHunterStrategy,
)

# Meta-Following策略
from src.strategies.meta_following import (
    S06DragonTigerStrategy,
    S10NorthboundStrategy,
    S15AlgoHunterStrategy,
)

# Meta-MeanReversion策略
from src.strategies.meta_mean_reversion import (
    S01RetracementStrategy,
    S05DynamicGridStrategy,
    S11FallenAngelStrategy,
)

# Meta-Momentum策略
from src.strategies.meta_momentum import (
    S02AggressiveStrategy,
    S07MorningSniperStrategy,
    S13LimitDownReversalStrategy,
)

__all__ = [
    # 基础类
    "Strategy",
    "Signal",
    "Position",
    "StrategyConfig",
    "ArenaTestResult",
    "StrategyMetadata",
    # Meta-Momentum
    "S02AggressiveStrategy",
    "S07MorningSniperStrategy",
    "S13LimitDownReversalStrategy",
    # Meta-MeanReversion
    "S01RetracementStrategy",
    "S05DynamicGridStrategy",
    "S11FallenAngelStrategy",
    # Meta-Following
    "S06DragonTigerStrategy",
    "S10NorthboundStrategy",
    "S15AlgoHunterStrategy",
    # Meta-Arbitrage
    "S09CBScalperStrategy",
    "S14CrossDomainArbStrategy",
    "S17DerivativesLinkageStrategy",
    "S18FutureTrendStrategy",
    "S19OptionSniperStrategy",
    # Meta-Event
    "S16ThemeHunterStrategy",
]
