"""
Arena测试系统 (Arena Testing System)

白皮书依据: 第四章 4.2 Arena测试系统
版本: v1.1.0
作者: MIA Team
日期: 2026-01-23

核心理念: 通过严格的Arena测试验证因子和策略的有效性,
确保只有经过残酷竞争存活的因子和策略才能进入下一阶段。

主要组件:
1. Factor Arena (因子Arena三轨测试):
   - FactorArenaSystem: 三轨测试编排器
   - FactorRealityTrack: 历史数据测试轨道
   - FactorHellTrack: 极端场景测试轨道
   - CrossMarketTrack: 跨市场测试轨道
   - FactorPerformanceMonitor: 因子性能监控器

2. Strategy Arena (策略Arena双轨测试):
   - StrategyArenaSystem: 双轨测试编排器
   - StrategyRealityTrack: 3年历史回测轨道
   - StrategyHellTrack: 极端场景压力测试轨道
   - StrategyPerformanceCalculator: 策略性能计算器
"""

from src.evolution.arena.cross_market_track import CrossMarketTrack

# Factor Arena Data Models
from src.evolution.arena.data_models import (
    CrossMarketResult,
    Factor,
    FactorTestResult,
    HellTrackResult,
    MarketType,
    RealityTrackResult,
)

# Factor Arena Components
from src.evolution.arena.factor_arena import FactorArenaSystem
from src.evolution.arena.factor_hell_track import FactorHellTrack
from src.evolution.arena.factor_performance_monitor import FactorPerformanceMonitor
from src.evolution.arena.factor_reality_track import FactorRealityTrack

# Strategy Arena Components
from src.evolution.arena.strategy_arena import StrategyArenaSystem

# Strategy Arena Data Models
from src.evolution.arena.strategy_data_models import (
    ExtremeScenarioType,
    PerformanceMetrics,
    Strategy,
    StrategyHellTrackResult,
    StrategyRealityTrackResult,
    StrategyStatus,
    StrategyTestResult,
    StrategyType,
)
from src.evolution.arena.strategy_hell_track import ExtremeScenarioGenerator, StrategyHellTrack
from src.evolution.arena.strategy_performance_calculator import StrategyPerformanceCalculator
from src.evolution.arena.strategy_reality_track import StrategyRealityTrack

__all__ = [
    # Factor Arena Data Models
    "Factor",
    "FactorTestResult",
    "RealityTrackResult",
    "HellTrackResult",
    "CrossMarketResult",
    "MarketType",
    # Strategy Arena Data Models
    "Strategy",
    "StrategyType",
    "StrategyStatus",
    "StrategyTestResult",
    "StrategyRealityTrackResult",
    "StrategyHellTrackResult",
    "PerformanceMetrics",
    "ExtremeScenarioType",
    # Factor Arena Components
    "FactorArenaSystem",
    "FactorRealityTrack",
    "FactorHellTrack",
    "CrossMarketTrack",
    "FactorPerformanceMonitor",
    # Strategy Arena Components
    "StrategyArenaSystem",
    "StrategyRealityTrack",
    "StrategyHellTrack",
    "ExtremeScenarioGenerator",
    "StrategyPerformanceCalculator",
]
