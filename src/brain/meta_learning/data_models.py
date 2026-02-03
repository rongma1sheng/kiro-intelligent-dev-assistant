"""元学习数据模型

白皮书依据: 第二章 2.2.4 风险控制元学习架构
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class MarketContext:
    """市场上下文

    白皮书依据: 第二章 2.2.4 风险控制元学习架构

    Attributes:
        volatility: 市场波动率，范围 [0.0, 1.0]
        liquidity: 市场流动性，范围 [0.0, 1.0]
        trend_strength: 趋势强度，范围 [-1.0, 1.0]，负值表示下跌趋势
        regime: 市场状态，取值 'bull', 'bear', 'sideways'
        aum: 当前资金规模，单位：元
        portfolio_concentration: 组合集中度，范围 [0.0, 1.0]
        recent_drawdown: 近期回撤，范围 [0.0, 1.0]
    """

    volatility: float
    liquidity: float
    trend_strength: float
    regime: str
    aum: float
    portfolio_concentration: float
    recent_drawdown: float

    def __post_init__(self):
        """验证参数范围"""
        if not 0.0 <= self.volatility <= 1.0:
            raise ValueError(f"volatility必须在[0.0, 1.0]范围内，当前: {self.volatility}")

        if not 0.0 <= self.liquidity <= 1.0:
            raise ValueError(f"liquidity必须在[0.0, 1.0]范围内，当前: {self.liquidity}")

        if not -1.0 <= self.trend_strength <= 1.0:
            raise ValueError(f"trend_strength必须在[-1.0, 1.0]范围内，当前: {self.trend_strength}")

        if self.regime not in ["bull", "bear", "sideways"]:
            raise ValueError(f"regime必须是'bull', 'bear'或'sideways'，当前: {self.regime}")

        if self.aum < 0:
            raise ValueError(f"aum必须≥0，当前: {self.aum}")

        if not 0.0 <= self.portfolio_concentration <= 1.0:
            raise ValueError(f"portfolio_concentration必须在[0.0, 1.0]范围内，当前: {self.portfolio_concentration}")

        if not 0.0 <= self.recent_drawdown <= 1.0:
            raise ValueError(f"recent_drawdown必须在[0.0, 1.0]范围内，当前: {self.recent_drawdown}")


@dataclass
class PerformanceMetrics:
    """性能指标

    白皮书依据: 第二章 2.2.4 风险控制元学习架构

    Attributes:
        sharpe_ratio: 夏普比率，通常范围 [-3.0, 5.0]
        max_drawdown: 最大回撤，范围 [0.0, 1.0]
        win_rate: 胜率，范围 [0.0, 1.0]
        profit_factor: 盈亏比，通常范围 [0.0, 10.0]
        calmar_ratio: 卡玛比率，通常范围 [-5.0, 10.0]
        sortino_ratio: 索提诺比率，通常范围 [-3.0, 5.0]
        decision_latency_ms: 决策延迟，单位：毫秒
    """

    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    calmar_ratio: float
    sortino_ratio: float
    decision_latency_ms: float

    def __post_init__(self):
        """验证参数范围"""
        if not 0.0 <= self.max_drawdown <= 1.0:
            raise ValueError(f"max_drawdown必须在[0.0, 1.0]范围内，当前: {self.max_drawdown}")

        if not 0.0 <= self.win_rate <= 1.0:
            raise ValueError(f"win_rate必须在[0.0, 1.0]范围内，当前: {self.win_rate}")

        if self.profit_factor < 0:
            raise ValueError(f"profit_factor必须≥0，当前: {self.profit_factor}")

        if self.decision_latency_ms < 0:
            raise ValueError(f"decision_latency_ms必须≥0，当前: {self.decision_latency_ms}")


@dataclass
class LearningDataPoint:
    """学习数据点

    白皮书依据: 第二章 2.2.4 风险控制元学习架构

    Attributes:
        market_context: 市场上下文
        strategy_a_performance: 策略A的性能指标
        strategy_b_performance: 策略B的性能指标
        winner: 获胜策略，'A' 或 'B'
        timestamp: 记录时间戳
    """

    market_context: MarketContext
    strategy_a_performance: PerformanceMetrics
    strategy_b_performance: PerformanceMetrics
    winner: str
    timestamp: datetime

    def __post_init__(self):
        """验证参数"""
        if self.winner not in ["A", "B"]:
            raise ValueError(f"winner必须是'A'或'B'，当前: {self.winner}")
