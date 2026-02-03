"""Simulation Engine for Daily Simulation Logic

白皮书依据: 第四章 4.5.3 模拟引擎
"""

from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from src.evolution.simulation.cost_model import CostModel
from src.evolution.simulation.data_models import (
    DailyResult,
    SimulationConfig,
    StrategyTier,
)
from src.evolution.simulation.performance_tracker import PerformanceTracker


class SimulationEngine:
    """模拟引擎

    白皮书依据: 第四章 4.5.3 模拟引擎

    执行每日模拟逻辑，包括信号生成、交易执行、成本计算等。

    Attributes:
        config: 模拟配置
        cost_model: 成本模型
        performance_tracker: 性能跟踪器
        current_date: 当前日期
        current_positions: 当前持仓
    """

    def __init__(self, config: SimulationConfig, strategy_tier: StrategyTier = StrategyTier.TIER_3):
        """初始化模拟引擎

        Args:
            config: 模拟配置
            strategy_tier: 策略层级（决定初始资金）
        """
        self.config = config

        # 根据策略层级设置初始资金（Requirement 6.2）
        tier_capital = {
            StrategyTier.TIER_1: 1000000.0,
            StrategyTier.TIER_2: 500000.0,
            StrategyTier.TIER_3: 200000.0,
            StrategyTier.TIER_4: 100000.0,
        }
        initial_capital = tier_capital.get(strategy_tier, config.initial_capital)

        self.cost_model = CostModel(commission_rate=config.commission_rate, slippage_rate=config.slippage_rate)

        self.performance_tracker = PerformanceTracker(initial_capital)

        self.current_date: Optional[datetime] = None
        self.current_positions: Dict[str, float] = {}
        self.current_cash = initial_capital

        logger.info(
            f"初始化SimulationEngine: " f"tier={strategy_tier.value}, " f"initial_capital={initial_capital:.2f}"
        )

    def run_daily_simulation(self, date: datetime, market_data: pd.DataFrame, signals: Dict[str, float]) -> DailyResult:
        """运行每日模拟

        白皮书依据: 第四章 4.5.3 模拟引擎 - Requirement 6.3, 6.4, 6.5

        Args:
            date: 当前日期
            market_data: 市场数据（包含价格信息）
            signals: 策略信号（股票代码 -> 目标权重）

        Returns:
            每日结果
        """
        self.current_date = date

        # 1. 生成交易订单
        trades = self._generate_trades(market_data, signals)

        # 2. 执行交易并计算成本（Requirement 6.4）
        transaction_cost = self.cost_model.apply_costs_to_trades(trades)

        # 3. 更新持仓和现金
        self._execute_trades(trades, market_data)

        # 4. 计算组合价值
        portfolio_value = self._calculate_portfolio_value(market_data)

        # 5. 记录每日结果（Requirement 6.5）
        daily_result = self.performance_tracker.record_daily_result(
            date=date,
            portfolio_value=portfolio_value,
            positions=self.current_positions,
            trades=trades,
            transaction_cost=transaction_cost,
        )

        logger.debug(
            f"每日模拟完成: "
            f"date={date.strftime('%Y-%m-%d')}, "
            f"portfolio_value={portfolio_value:.2f}, "
            f"trades={len(trades)}, "
            f"cost={transaction_cost:.2f}"
        )

        return daily_result

    def _generate_trades(self, market_data: pd.DataFrame, signals: Dict[str, float]) -> List[Dict]:
        """生成交易订单

        Args:
            market_data: 市场数据
            signals: 策略信号

        Returns:
            交易列表
        """
        trades = []

        # 计算目标持仓价值
        portfolio_value = self._calculate_portfolio_value(market_data)

        for symbol, target_weight in signals.items():
            if symbol not in market_data.index:
                continue

            # 获取当前价格
            current_price = market_data.loc[symbol, "close"]

            # 计算目标持仓数量
            target_value = portfolio_value * target_weight
            target_shares = target_value / current_price

            # 计算当前持仓数量
            current_shares = self.current_positions.get(symbol, 0.0)

            # 计算需要交易的数量
            trade_shares = target_shares - current_shares

            if abs(trade_shares) > 0.01:  # 忽略微小交易
                trade_value = abs(trade_shares * current_price)

                trade = {
                    "symbol": symbol,
                    "shares": trade_shares,
                    "price": current_price,
                    "value": trade_value,
                    "side": "buy" if trade_shares > 0 else "sell",
                }

                trades.append(trade)

        return trades

    def _execute_trades(self, trades: List[Dict], market_data: pd.DataFrame) -> None:  # pylint: disable=unused-argument
        """执行交易

        Args:
            trades: 交易列表
            market_data: 市场数据
        """
        for trade in trades:
            symbol = trade["symbol"]
            shares = trade["shares"]
            cost = trade.get("cost", 0.0)

            # 获取有效价格（考虑滑点）
            market_price = trade["price"]
            is_buy = trade["side"] == "buy"
            effective_price = self.cost_model.get_effective_price(market_price, is_buy)

            # 更新持仓
            current_shares = self.current_positions.get(symbol, 0.0)
            new_shares = current_shares + shares

            if abs(new_shares) < 0.01:
                # 清仓
                if symbol in self.current_positions:
                    del self.current_positions[symbol]
            else:
                self.current_positions[symbol] = new_shares

            # 更新现金
            cash_flow = -shares * effective_price - cost
            self.current_cash += cash_flow

    def _calculate_portfolio_value(self, market_data: pd.DataFrame) -> float:
        """计算组合价值

        Args:
            market_data: 市场数据

        Returns:
            组合总价值
        """
        # 持仓价值
        position_value = 0.0
        for symbol, shares in self.current_positions.items():
            if symbol in market_data.index:
                price = market_data.loc[symbol, "close"]
                position_value += shares * price

        # 总价值 = 持仓价值 + 现金
        total_value = position_value + self.current_cash

        return total_value

    def check_early_termination(self) -> bool:
        """检查是否需要提前终止

        白皮书依据: 第四章 4.5.6 提前终止逻辑 - Requirement 6.6

        Returns:
            True表示需要终止
        """
        current_drawdown = self.performance_tracker.get_current_drawdown()

        if current_drawdown < self.config.max_drawdown_threshold:
            logger.warning(
                f"回撤超过阈值，提前终止: "
                f"current_drawdown={current_drawdown:.4f}, "
                f"threshold={self.config.max_drawdown_threshold:.4f}"
            )
            return True

        return False

    def get_performance_tracker(self) -> PerformanceTracker:
        """获取性能跟踪器

        Returns:
            性能跟踪器实例
        """
        return self.performance_tracker
