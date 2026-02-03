"""
策略性能计算器 (Strategy Performance Calculator)

白皮书依据: 第四章 4.2.2 策略Arena - 性能指标计算
"""

from typing import List

import numpy as np
import pandas as pd
from loguru import logger

from src.evolution.arena.strategy_data_models import PerformanceMetrics


class StrategyPerformanceCalculator:
    """策略性能计算器

    白皮书依据: 第四章 4.2.2 策略Arena - 性能指标计算

    计算策略的各项性能指标，包括夏普比率、最大回撤、年化收益率、胜率等。

    Attributes:
        risk_free_rate: 无风险利率，默认3%
        trading_days_per_year: 每年交易日数，默认252天
    """

    def __init__(self, risk_free_rate: float = 0.03, trading_days_per_year: int = 252):
        """初始化策略性能计算器

        Args:
            risk_free_rate: 无风险利率，范围 [0, 1]
            trading_days_per_year: 每年交易日数，必须 > 0

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if not 0 <= risk_free_rate <= 1:
            raise ValueError(f"无风险利率必须在[0, 1]范围内，当前值: {risk_free_rate}")
        if trading_days_per_year <= 0:
            raise ValueError(f"每年交易日数必须大于0，当前值: {trading_days_per_year}")

        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = trading_days_per_year

        logger.info(
            f"初始化StrategyPerformanceCalculator: "
            f"risk_free_rate={risk_free_rate}, "
            f"trading_days_per_year={trading_days_per_year}"
        )

    def calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """计算夏普比率

        白皮书依据: 第四章 4.2.2 - 夏普比率 (Sharpe Ratio)

        夏普比率 = (年化收益率 - 无风险利率) / 年化波动率

        Args:
            returns: 日收益率序列

        Returns:
            夏普比率

        Raises:
            ValueError: 当收益率序列为空时
        """
        if returns.empty:
            raise ValueError("收益率序列不能为空")

        # 计算超额收益
        excess_returns = returns - self.risk_free_rate / self.trading_days_per_year

        # 计算年化夏普比率
        if excess_returns.std() == 0:
            return 0.0

        sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(self.trading_days_per_year)

        return float(sharpe)

    def calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """计算索提诺比率

        白皮书依据: 第四章 4.2.2 - 索提诺比率 (Sortino Ratio)

        索提诺比率只考虑下行波动率，更关注负收益的风险。

        Args:
            returns: 日收益率序列

        Returns:
            索提诺比率

        Raises:
            ValueError: 当收益率序列为空时
        """
        if returns.empty:
            raise ValueError("收益率序列不能为空")

        # 计算超额收益
        excess_returns = returns - self.risk_free_rate / self.trading_days_per_year

        # 计算下行波动率 (只考虑负收益)
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0

        downside_std = downside_returns.std()

        # 计算年化索提诺比率
        sortino = excess_returns.mean() / downside_std * np.sqrt(self.trading_days_per_year)

        return float(sortino)

    def calculate_max_drawdown(self, equity_curve: pd.Series) -> float:
        """计算最大回撤

        白皮书依据: 第四章 4.2.2 - 最大回撤 (Maximum Drawdown)

        最大回撤 = (谷值 - 峰值) / 峰值

        Args:
            equity_curve: 权益曲线序列

        Returns:
            最大回撤 (正数表示回撤幅度)

        Raises:
            ValueError: 当权益曲线为空时
        """
        if equity_curve.empty:
            raise ValueError("权益曲线不能为空")

        # 计算累计最大值
        running_max = equity_curve.expanding().max()

        # 计算回撤
        drawdown = (equity_curve - running_max) / running_max

        # 返回最大回撤的绝对值
        max_dd = abs(drawdown.min())

        return float(max_dd)

    def calculate_annual_return(self, returns: pd.Series) -> float:
        """计算年化收益率

        白皮书依据: 第四章 4.2.2 - 年化收益率 (Annual Return)

        Args:
            returns: 日收益率序列

        Returns:
            年化收益率

        Raises:
            ValueError: 当收益率序列为空时
        """
        if returns.empty:
            raise ValueError("收益率序列不能为空")

        # 计算累计收益
        cumulative_return = (1 + returns).prod() - 1

        # 计算年化收益率
        num_years = len(returns) / self.trading_days_per_year
        if num_years == 0:
            return 0.0

        annual_return = (1 + cumulative_return) ** (1 / num_years) - 1

        return float(annual_return)

    def calculate_annual_volatility(self, returns: pd.Series) -> float:
        """计算年化波动率

        白皮书依据: 第四章 4.2.2 - 年化波动率 (Annual Volatility)

        Args:
            returns: 日收益率序列

        Returns:
            年化波动率

        Raises:
            ValueError: 当收益率序列为空时
        """
        if returns.empty:
            raise ValueError("收益率序列不能为空")

        # 计算年化波动率
        annual_vol = returns.std() * np.sqrt(self.trading_days_per_year)

        return float(annual_vol)

    def calculate_calmar_ratio(self, returns: pd.Series, equity_curve: pd.Series) -> float:
        """计算卡玛比率

        白皮书依据: 第四章 4.2.2 - 卡玛比率 (Calmar Ratio)

        卡玛比率 = 年化收益率 / 最大回撤

        Args:
            returns: 日收益率序列
            equity_curve: 权益曲线序列

        Returns:
            卡玛比率

        Raises:
            ValueError: 当序列为空时
        """
        if returns.empty or equity_curve.empty:
            raise ValueError("收益率序列和权益曲线不能为空")

        annual_return = self.calculate_annual_return(returns)
        max_dd = self.calculate_max_drawdown(equity_curve)

        if max_dd == 0:
            return 0.0

        calmar = annual_return / max_dd

        return float(calmar)

    def calculate_win_rate(self, trade_returns: List[float]) -> float:
        """计算胜率

        白皮书依据: 第四章 4.2.2 - 胜率 (Win Rate)

        胜率 = 盈利交易次数 / 总交易次数

        Args:
            trade_returns: 每笔交易的收益率列表

        Returns:
            胜率 [0, 1]

        Raises:
            ValueError: 当交易列表为空时
        """
        if not trade_returns:
            raise ValueError("交易收益率列表不能为空")

        winning_trades = sum(1 for ret in trade_returns if ret > 0)
        total_trades = len(trade_returns)

        win_rate = winning_trades / total_trades

        return float(win_rate)

    def calculate_profit_factor(self, trade_returns: List[float]) -> float:
        """计算盈亏比

        白皮书依据: 第四章 4.2.2 - 盈亏比 (Profit Factor)

        盈亏比 = 总盈利 / 总亏损

        Args:
            trade_returns: 每笔交易的收益率列表

        Returns:
            盈亏比

        Raises:
            ValueError: 当交易列表为空时
        """
        if not trade_returns:
            raise ValueError("交易收益率列表不能为空")

        gross_profit = sum(ret for ret in trade_returns if ret > 0)
        gross_loss = abs(sum(ret for ret in trade_returns if ret < 0))

        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0

        profit_factor = gross_profit / gross_loss

        return float(profit_factor)

    def calculate_all_metrics(
        self, returns: pd.Series, equity_curve: pd.Series, trade_returns: List[float]
    ) -> PerformanceMetrics:
        """计算所有性能指标

        白皮书依据: 第四章 4.2.2 - 综合性能评估

        Args:
            returns: 日收益率序列
            equity_curve: 权益曲线序列
            trade_returns: 每笔交易的收益率列表

        Returns:
            完整的性能指标对象

        Raises:
            ValueError: 当输入数据无效时
        """
        if returns.empty or equity_curve.empty or not trade_returns:
            raise ValueError("输入数据不能为空")

        logger.info(f"开始计算所有性能指标，数据点数: {len(returns)}")

        try:
            sharpe = self.calculate_sharpe_ratio(returns)
            sortino = self.calculate_sortino_ratio(returns)
            max_dd = self.calculate_max_drawdown(equity_curve)
            annual_return = self.calculate_annual_return(returns)
            annual_vol = self.calculate_annual_volatility(returns)
            calmar = self.calculate_calmar_ratio(returns, equity_curve)
            win_rate = self.calculate_win_rate(trade_returns)
            profit_factor = self.calculate_profit_factor(trade_returns)

            avg_trade_return = float(np.mean(trade_returns))

            metrics = PerformanceMetrics(
                sharpe_ratio=sharpe,
                sortino_ratio=sortino,
                calmar_ratio=calmar,
                max_drawdown=max_dd,
                annual_return=annual_return,
                annual_volatility=annual_vol,
                win_rate=win_rate,
                profit_factor=profit_factor,
                total_trades=len(trade_returns),
                avg_trade_return=avg_trade_return,
            )

            logger.info(
                f"性能指标计算完成 - "
                f"Sharpe: {sharpe:.2f}, "
                f"MaxDD: {max_dd:.2%}, "
                f"年化收益: {annual_return:.2%}, "
                f"胜率: {win_rate:.2%}"
            )

            return metrics

        except Exception as e:
            logger.error(f"计算性能指标失败: {e}")
            raise
