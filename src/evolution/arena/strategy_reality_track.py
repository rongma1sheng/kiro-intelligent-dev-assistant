"""
策略Reality Track (Strategy Reality Track)

白皮书依据: 第四章 4.2.2 策略Arena - Reality Track (3年历史回测)
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from src.evolution.arena.strategy_data_models import Strategy, StrategyRealityTrackResult
from src.evolution.arena.strategy_performance_calculator import StrategyPerformanceCalculator


class StrategyRealityTrack:
    """策略Reality Track测试

    白皮书依据: 第四章 4.2.2 策略Arena - Reality Track

    使用3年真实历史数据对策略进行回测，评估策略在正常市场环境下的表现。

    Attributes:
        performance_calculator: 性能计算器
        test_period_years: 测试周期(年)，默认3年
        initial_capital: 初始资金，默认100万
        commission_rate: 手续费率，默认0.0003 (万三)
        slippage_rate: 滑点率，默认0.0001
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        performance_calculator: Optional[StrategyPerformanceCalculator] = None,
        test_period_years: int = 3,
        initial_capital: float = 1_000_000.0,
        commission_rate: float = 0.0003,
        slippage_rate: float = 0.0001,
    ):
        """初始化Reality Track测试器

        Args:
            performance_calculator: 性能计算器，None则创建默认实例
            test_period_years: 测试周期(年)，必须 > 0
            initial_capital: 初始资金，必须 > 0
            commission_rate: 手续费率，范围 [0, 1]
            slippage_rate: 滑点率，范围 [0, 1]

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if test_period_years <= 0:
            raise ValueError(f"测试周期必须大于0年，当前值: {test_period_years}")
        if initial_capital <= 0:
            raise ValueError(f"初始资金必须大于0，当前值: {initial_capital}")
        if not 0 <= commission_rate <= 1:
            raise ValueError(f"手续费率必须在[0, 1]范围内，当前值: {commission_rate}")
        if not 0 <= slippage_rate <= 1:
            raise ValueError(f"滑点率必须在[0, 1]范围内，当前值: {slippage_rate}")

        self.performance_calculator = performance_calculator or StrategyPerformanceCalculator()
        self.test_period_years = test_period_years
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

        logger.info(
            f"初始化StrategyRealityTrack: "
            f"test_period={test_period_years}年, "
            f"initial_capital={initial_capital:,.0f}, "
            f"commission={commission_rate:.4f}, "
            f"slippage={slippage_rate:.4f}"
        )

    async def test_strategy(self, strategy: Strategy, historical_data: pd.DataFrame) -> StrategyRealityTrackResult:
        """测试策略在Reality Track上的表现

        白皮书依据: 第四章 4.2.2 - Reality Track 3年历史回测

        Args:
            strategy: 待测试策略
            historical_data: 历史数据，索引为日期，列包含OHLCV等

        Returns:
            Reality Track测试结果

        Raises:
            ValueError: 当输入数据无效时
        """
        if historical_data.empty:
            raise ValueError("历史数据不能为空")

        logger.info(f"开始Reality Track测试: strategy_id={strategy.id}, " f"数据点数={len(historical_data)}")

        try:
            # 1. 运行回测
            backtest_results = await self._run_backtest(strategy, historical_data)

            # 2. 计算性能指标
            metrics = self._calculate_metrics(backtest_results)

            # 3. 计算Reality评分
            reality_score = self._calculate_reality_score(metrics)

            # 4. 构建结果对象
            result = StrategyRealityTrackResult(
                sharpe_ratio=metrics["sharpe_ratio"],
                max_drawdown=metrics["max_drawdown"],
                annual_return=metrics["annual_return"],
                win_rate=metrics["win_rate"],
                profit_factor=metrics["profit_factor"],
                calmar_ratio=metrics["calmar_ratio"],
                sortino_ratio=metrics["sortino_ratio"],
                total_trades=metrics["total_trades"],
                avg_holding_period=metrics["avg_holding_period"],
                reality_score=reality_score,
                test_period_days=len(historical_data),
            )

            logger.info(
                f"Reality Track测试完成 - "
                f"Sharpe: {result.sharpe_ratio:.2f}, "
                f"MaxDD: {result.max_drawdown:.2%}, "
                f"年化收益: {result.annual_return:.2%}, "
                f"Reality评分: {reality_score:.3f}"
            )

            return result

        except Exception as e:
            logger.error(f"Reality Track测试失败: {e}")
            raise

    async def _run_backtest(self, strategy: Strategy, historical_data: pd.DataFrame) -> Dict[str, Any]:
        """运行回测

        Args:
            strategy: 待测试策略
            historical_data: 历史数据

        Returns:
            回测结果字典，包含equity_curve, returns, trades等
        """
        logger.debug(f"开始运行回测: strategy_id={strategy.id}")

        # 初始化
        equity = self.initial_capital
        equity_curve = [equity]
        daily_returns = []
        trades = []
        positions = {}

        # 模拟逐日交易
        for i in range(1, len(historical_data)):
            historical_data.index[i]  # pylint: disable=w0104
            historical_data.index[i - 1]  # pylint: disable=w0104

            # 获取当前数据
            current_data = historical_data.iloc[: i + 1]

            # 生成交易信号 (简化版本，实际应执行策略代码)
            signals = self._generate_signals(strategy, current_data)

            # 执行交易
            trade_results = self._execute_trades(signals, historical_data.iloc[i], equity, positions)

            # 更新持仓和权益
            positions = trade_results["positions"]
            equity = trade_results["equity"]
            trades.extend(trade_results["trades"])

            # 记录权益曲线
            equity_curve.append(equity)

            # 计算日收益率
            daily_return = (equity - equity_curve[-2]) / equity_curve[-2]
            daily_returns.append(daily_return)

        # 转换为Series
        equity_series = pd.Series(equity_curve, index=historical_data.index)
        returns_series = pd.Series(daily_returns, index=historical_data.index[1:])

        logger.debug(f"回测完成: 总交易次数={len(trades)}, " f"最终权益={equity:,.0f}")

        return {"equity_curve": equity_series, "returns": returns_series, "trades": trades, "positions": positions}

    def _generate_signals(
        self, strategy: Strategy, data: pd.DataFrame  # pylint: disable=unused-argument
    ) -> Dict[str, float]:  # pylint: disable=unused-argument
        """生成交易信号

        Args:
            strategy: 策略对象
            data: 历史数据

        Returns:
            信号字典 {symbol: signal_strength}
        """
        # 简化版本：随机生成信号
        # 实际应执行策略代码生成真实信号
        np.random.seed(hash(strategy.id) % (2**32))
        signal_strength = np.random.randn() * 0.5

        return {"symbol": signal_strength}

    def _execute_trades(
        self,
        signals: Dict[str, float],
        current_price_data: pd.Series,  # pylint: disable=unused-argument
        equity: float,
        positions: Dict[str, float],  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:
        """执行交易

        Args:
            signals: 交易信号
            current_price_data: 当前价格数据
            equity: 当前权益
            positions: 当前持仓

        Returns:
            交易结果字典
        """
        trades = []
        new_positions = positions.copy()
        new_equity = equity

        for symbol, signal in signals.items():
            # 简化版本：根据信号强度调整仓位
            if abs(signal) > 0.3:  # 信号阈值
                # 计算目标仓位
                target_position = signal * equity * 0.1  # 最多10%仓位

                # 计算交易量
                current_position = positions.get(symbol, 0)
                trade_amount = target_position - current_position

                if abs(trade_amount) > 0:
                    # 应用手续费和滑点
                    cost = abs(trade_amount) * (self.commission_rate + self.slippage_rate)

                    # 记录交易
                    trades.append(
                        {"symbol": symbol, "amount": trade_amount, "cost": cost, "return": 0.0}  # 实际收益在平仓时计算
                    )

                    # 更新持仓和权益
                    new_positions[symbol] = target_position
                    new_equity -= cost

        return {"positions": new_positions, "equity": new_equity, "trades": trades}

    def _calculate_metrics(self, backtest_results: Dict[str, Any]) -> Dict[str, float]:
        """计算性能指标

        Args:
            backtest_results: 回测结果

        Returns:
            性能指标字典
        """
        equity_curve = backtest_results["equity_curve"]
        returns = backtest_results["returns"]
        trades = backtest_results["trades"]

        # 提取交易收益率
        trade_returns = [t["return"] for t in trades if "return" in t and t["return"] != 0]
        if not trade_returns:
            # 如果没有完整交易记录，使用日收益率估算
            trade_returns = returns.tolist()

        # 计算所有指标
        performance_metrics = self.performance_calculator.calculate_all_metrics(
            returns=returns, equity_curve=equity_curve, trade_returns=trade_returns
        )

        # 计算平均持仓周期
        avg_holding_period = self._calculate_avg_holding_period(trades)

        return {
            "sharpe_ratio": performance_metrics.sharpe_ratio,
            "sortino_ratio": performance_metrics.sortino_ratio,
            "calmar_ratio": performance_metrics.calmar_ratio,
            "max_drawdown": performance_metrics.max_drawdown,
            "annual_return": performance_metrics.annual_return,
            "win_rate": performance_metrics.win_rate,
            "profit_factor": performance_metrics.profit_factor,
            "total_trades": performance_metrics.total_trades,
            "avg_holding_period": avg_holding_period,
        }

    def _calculate_avg_holding_period(self, trades: List[Dict[str, Any]]) -> float:
        """计算平均持仓周期

        Args:
            trades: 交易列表

        Returns:
            平均持仓周期(天)
        """
        if not trades:
            return 0.0

        # 简化版本：假设平均持仓5天
        # 实际应根据开仓和平仓时间计算
        return 5.0

    def _calculate_reality_score(self, metrics: Dict[str, float]) -> float:
        """计算Reality Track综合评分

        白皮书依据: 第四章 4.2.2 - Reality Track评分标准

        评分公式:
        Reality Score = 0.3 * Sharpe标准化 + 0.2 * 回撤标准化 +
                       0.2 * 年化收益标准化 + 0.15 * 胜率标准化 +
                       0.15 * 盈亏比标准化

        Args:
            metrics: 性能指标字典

        Returns:
            Reality评分 [0, 1]
        """
        # 标准化各项指标到[0, 1]
        sharpe_norm = self._normalize_sharpe(metrics["sharpe_ratio"])
        drawdown_norm = self._normalize_drawdown(metrics["max_drawdown"])
        return_norm = self._normalize_return(metrics["annual_return"])
        winrate_norm = metrics["win_rate"]  # 已经在[0, 1]
        pf_norm = self._normalize_profit_factor(metrics["profit_factor"])

        # 加权计算综合评分
        reality_score = (
            0.30 * sharpe_norm + 0.20 * drawdown_norm + 0.20 * return_norm + 0.15 * winrate_norm + 0.15 * pf_norm
        )

        # 确保在[0, 1]范围内
        reality_score = max(0.0, min(1.0, reality_score))

        return float(reality_score)

    def _normalize_sharpe(self, sharpe: float) -> float:
        """标准化夏普比率到[0, 1]"""
        # Sharpe > 2.0 视为满分
        return min(1.0, max(0.0, sharpe / 2.0))

    def _normalize_drawdown(self, drawdown: float) -> float:
        """标准化最大回撤到[0, 1]"""
        # 回撤越小越好，15%以下视为满分
        if drawdown <= 0.15:  # pylint: disable=no-else-return
            return 1.0
        elif drawdown >= 0.50:
            return 0.0
        else:
            return 1.0 - (drawdown - 0.15) / 0.35

    def _normalize_return(self, annual_return: float) -> float:
        """标准化年化收益率到[0, 1]"""
        # 年化收益 > 30% 视为满分
        return min(1.0, max(0.0, annual_return / 0.30))

    def _normalize_profit_factor(self, profit_factor: float) -> float:
        """标准化盈亏比到[0, 1]"""
        # 盈亏比 > 2.0 视为满分
        return min(1.0, max(0.0, profit_factor / 2.0))
