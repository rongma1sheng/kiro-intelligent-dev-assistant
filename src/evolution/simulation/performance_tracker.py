"""Performance Tracker for Daily Metrics

白皮书依据: 第四章 4.5.5 每日性能监控
"""

from datetime import datetime
from typing import Dict, List

import numpy as np
from loguru import logger

from src.evolution.simulation.data_models import DailyResult


class PerformanceTracker:
    """性能跟踪器

    白皮书依据: 第四章 4.5.5 每日性能监控

    跟踪和计算每日性能指标，包括收益率、回撤、夏普比率等。

    Attributes:
        initial_capital: 初始资金
        daily_results: 每日结果列表
        peak_value: 历史最高组合价值
    """

    def __init__(self, initial_capital: float):
        """初始化性能跟踪器

        Args:
            initial_capital: 初始资金

        Raises:
            ValueError: 当initial_capital <= 0时
        """
        if initial_capital <= 0:
            raise ValueError(f"initial_capital必须>0，当前: {initial_capital}")

        self.initial_capital = initial_capital
        self.daily_results: List[DailyResult] = []
        self.peak_value = initial_capital

        logger.info(f"初始化PerformanceTracker: initial_capital={initial_capital:.2f}")

    def record_daily_result(  # pylint: disable=too-many-positional-arguments
        self,
        date: datetime,
        portfolio_value: float,
        positions: Dict[str, float],
        trades: List[Dict],
        transaction_cost: float,
    ) -> DailyResult:
        """记录每日结果

        白皮书依据: 第四章 4.5.5 每日性能监控 - Requirement 6.5

        Args:
            date: 日期
            portfolio_value: 组合价值
            positions: 持仓信息
            trades: 交易记录
            transaction_cost: 交易成本

        Returns:
            每日结果对象
        """
        # 计算当日收益率
        if len(self.daily_results) == 0:
            previous_value = self.initial_capital
        else:
            previous_value = self.daily_results[-1].portfolio_value

        daily_return = (portfolio_value - previous_value) / previous_value

        # 计算累计收益率
        cumulative_return = (portfolio_value - self.initial_capital) / self.initial_capital

        # 更新峰值
        if portfolio_value > self.peak_value:  # pylint: disable=r1731
            self.peak_value = portfolio_value

        # 计算回撤
        drawdown = (portfolio_value - self.peak_value) / self.peak_value

        # 创建每日结果
        daily_result = DailyResult(
            date=date,
            portfolio_value=portfolio_value,
            daily_return=daily_return,
            cumulative_return=cumulative_return,
            drawdown=drawdown,
            positions=positions.copy(),
            trades=trades.copy(),
            transaction_cost=transaction_cost,
        )

        self.daily_results.append(daily_result)

        logger.debug(
            f"记录每日结果: "
            f"date={date.strftime('%Y-%m-%d')}, "
            f"portfolio_value={portfolio_value:.2f}, "
            f"daily_return={daily_return:.4f}, "
            f"cumulative_return={cumulative_return:.4f}, "
            f"drawdown={drawdown:.4f}"
        )

        return daily_result

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.03) -> float:
        """计算夏普比率

        白皮书依据: 第四章 4.5.7 最终指标计算 - Requirement 6.7

        Args:
            risk_free_rate: 无风险利率，默认3%

        Returns:
            夏普比率（年化）
        """
        if len(self.daily_results) < 2:
            return 0.0

        # 提取每日收益率
        returns = [r.daily_return for r in self.daily_results]

        # 计算超额收益
        daily_rf = risk_free_rate / 252
        excess_returns = [r - daily_rf for r in returns]

        # 计算夏普比率
        mean_excess = np.mean(excess_returns)
        std_excess = np.std(excess_returns, ddof=1)

        if std_excess == 0:
            return 0.0

        sharpe = mean_excess / std_excess * np.sqrt(252)

        return sharpe

    def calculate_max_drawdown(self) -> float:
        """计算最大回撤

        白皮书依据: 第四章 4.5.7 最终指标计算 - Requirement 6.7

        Returns:
            最大回撤（负数）
        """
        if len(self.daily_results) == 0:
            return 0.0

        drawdowns = [r.drawdown for r in self.daily_results]
        max_dd = min(drawdowns)

        return max_dd

    def calculate_win_rate(self) -> float:
        """计算胜率

        白皮书依据: 第四章 4.5.7 最终指标计算 - Requirement 6.7

        Returns:
            胜率（0-1之间）
        """
        if len(self.daily_results) < 2:
            return 0.0

        # 统计盈利天数
        winning_days = sum(1 for r in self.daily_results if r.daily_return > 0)
        total_days = len(self.daily_results)

        win_rate = winning_days / total_days

        return win_rate

    def calculate_profit_factor(self) -> float:
        """计算盈亏比

        白皮书依据: 第四章 4.5.7 最终指标计算 - Requirement 6.7

        Returns:
            盈亏比（总盈利/总亏损）
        """
        if len(self.daily_results) < 2:
            return 0.0

        # 计算总盈利和总亏损
        total_profit = sum(r.daily_return * self.initial_capital for r in self.daily_results if r.daily_return > 0)

        total_loss = abs(sum(r.daily_return * self.initial_capital for r in self.daily_results if r.daily_return < 0))

        if total_loss == 0:
            return float("inf") if total_profit > 0 else 0.0

        profit_factor = total_profit / total_loss

        return profit_factor

    def get_current_drawdown(self) -> float:
        """获取当前回撤

        Returns:
            当前回撤（负数或0）
        """
        if len(self.daily_results) == 0:
            return 0.0

        return self.daily_results[-1].drawdown

    def get_total_return(self) -> float:
        """获取总收益率

        Returns:
            总收益率
        """
        if len(self.daily_results) == 0:
            return 0.0

        return self.daily_results[-1].cumulative_return

    def get_final_capital(self) -> float:
        """获取最终资金

        Returns:
            最终资金
        """
        if len(self.daily_results) == 0:
            return self.initial_capital

        return self.daily_results[-1].portfolio_value
