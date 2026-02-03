"""Data Models for Simulation Validation System

白皮书依据: 第四章 4.5 模拟验证系统
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class StrategyTier(Enum):
    """策略层级

    白皮书依据: 第四章 4.5.2 资金分配
    """

    TIER_1 = "TIER_1"  # 顶级策略，分配100万
    TIER_2 = "TIER_2"  # 优秀策略，分配50万
    TIER_3 = "TIER_3"  # 良好策略，分配20万
    TIER_4 = "TIER_4"  # 基础策略，分配10万


class SimulationState(Enum):
    """模拟状态

    白皮书依据: 第四章 4.5.1 模拟流程
    """

    PENDING = "PENDING"  # 等待开始
    RUNNING = "RUNNING"  # 运行中
    COMPLETED = "COMPLETED"  # 正常完成
    FAILED = "FAILED"  # 失败（回撤过大等）
    TERMINATED = "TERMINATED"  # 提前终止


@dataclass
class SimulationConfig:
    """模拟配置

    白皮书依据: 第四章 4.5 模拟验证系统

    Attributes:
        duration_days: 模拟天数，默认30天
        initial_capital: 初始资金
        commission_rate: 佣金费率
        slippage_rate: 滑点率
        max_drawdown_threshold: 最大回撤阈值，超过则终止
        pass_criteria: 通过标准
    """

    duration_days: int = 30
    initial_capital: float = 1000000.0
    commission_rate: float = 0.0003  # 0.03%
    slippage_rate: float = 0.0005  # 0.05%
    max_drawdown_threshold: float = -0.20  # -20%

    # 通过标准（Requirement 6.8）
    min_return: float = 0.05  # 5%
    min_sharpe: float = 1.2
    max_drawdown: float = -0.15  # -15%
    min_win_rate: float = 0.55  # 55%
    min_profit_factor: float = 1.3

    def __post_init__(self):
        """验证配置参数"""
        if self.duration_days <= 0:
            raise ValueError(f"duration_days必须>0，当前: {self.duration_days}")

        if self.initial_capital <= 0:
            raise ValueError(f"initial_capital必须>0，当前: {self.initial_capital}")

        if not 0 <= self.commission_rate <= 1:
            raise ValueError(f"commission_rate必须在[0,1]，当前: {self.commission_rate}")

        if not 0 <= self.slippage_rate <= 1:
            raise ValueError(f"slippage_rate必须在[0,1]，当前: {self.slippage_rate}")

        if not -1 <= self.max_drawdown_threshold <= 0:
            raise ValueError(f"max_drawdown_threshold必须在[-1,0]，当前: {self.max_drawdown_threshold}")


@dataclass
class DailyResult:
    """每日模拟结果

    白皮书依据: 第四章 4.5.5 每日性能监控

    Attributes:
        date: 日期
        portfolio_value: 组合价值
        daily_return: 当日收益率
        cumulative_return: 累计收益率
        drawdown: 当前回撤
        positions: 持仓信息
        trades: 交易记录
        transaction_cost: 交易成本
    """

    date: datetime
    portfolio_value: float
    daily_return: float
    cumulative_return: float
    drawdown: float
    positions: Dict[str, float] = field(default_factory=dict)
    trades: List[Dict] = field(default_factory=list)
    transaction_cost: float = 0.0

    def __post_init__(self):
        """验证每日结果"""
        if self.portfolio_value < 0:
            raise ValueError(f"portfolio_value不能为负，当前: {self.portfolio_value}")

        if not -1 <= self.drawdown <= 0:
            raise ValueError(f"drawdown必须在[-1,0]，当前: {self.drawdown}")


@dataclass
class SimulationResult:
    """模拟结果

    白皮书依据: 第四章 4.5.7 最终指标计算

    Attributes:
        strategy_id: 策略ID
        start_date: 开始日期
        end_date: 结束日期
        duration_days: 实际运行天数
        initial_capital: 初始资金
        final_capital: 最终资金
        total_return: 总收益率
        sharpe_ratio: 夏普比率
        max_drawdown: 最大回撤
        win_rate: 胜率
        profit_factor: 盈亏比
        daily_results: 每日结果列表
        state: 模拟状态
        passed: 是否通过
        failure_reason: 失败原因
    """

    strategy_id: str
    start_date: datetime
    end_date: datetime
    duration_days: int
    initial_capital: float
    final_capital: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    daily_results: List[DailyResult]
    state: SimulationState
    passed: bool
    failure_reason: Optional[str] = None

    def __post_init__(self):
        """验证模拟结果"""
        if self.duration_days <= 0:
            raise ValueError(f"duration_days必须>0，当前: {self.duration_days}")

        if self.initial_capital <= 0:
            raise ValueError(f"initial_capital必须>0，当前: {self.initial_capital}")

        if self.final_capital < 0:
            raise ValueError(f"final_capital不能为负，当前: {self.final_capital}")

        if not -1 <= self.max_drawdown <= 0:
            raise ValueError(f"max_drawdown必须在[-1,0]，当前: {self.max_drawdown}")

        if not 0 <= self.win_rate <= 1:
            raise ValueError(f"win_rate必须在[0,1]，当前: {self.win_rate}")

        if self.profit_factor < 0:
            raise ValueError(f"profit_factor不能为负，当前: {self.profit_factor}")

        if len(self.daily_results) != self.duration_days:
            raise ValueError(f"daily_results长度({len(self.daily_results)})必须等于duration_days({self.duration_days})")
