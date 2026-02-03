"""Meta-Arbitrage策略模块

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Arbitrage系

套利策略系列：
- S09 CB Scalper (可转债): 基于正股联动的T+0极速交易
- S14 Cross-Domain Arb (跨域): 期货/现货或产业链联动套利
- S17 Derivatives Linkage (期现联动): 期权IV/期货升贴水作为先行指标
- S18 Future Trend (期指趋势) [Shadow Mode]: IC/IM主力合约趋势跟踪
- S19 Option Sniper (期权狙击) [Shadow Mode]: 舆情驱动的Gamma Scalping
"""

from src.strategies.meta_arbitrage.s09_cb_scalper import S09CBScalperStrategy
from src.strategies.meta_arbitrage.s14_cross_domain_arb import S14CrossDomainArbStrategy
from src.strategies.meta_arbitrage.s17_derivatives_linkage import S17DerivativesLinkageStrategy
from src.strategies.meta_arbitrage.s18_future_trend import S18FutureTrendStrategy
from src.strategies.meta_arbitrage.s19_option_sniper import S19OptionSniperStrategy

__all__ = [
    "S09CBScalperStrategy",
    "S14CrossDomainArbStrategy",
    "S17DerivativesLinkageStrategy",
    "S18FutureTrendStrategy",
    "S19OptionSniperStrategy",
]
