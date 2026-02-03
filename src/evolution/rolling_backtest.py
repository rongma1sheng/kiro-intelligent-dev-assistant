"""滚动回测框架 - Rolling Window Backtest

白皮书依据: 第四章 4.2 斯巴达竞技场 - 稳健性测试

滚动回测通过在不同时间窗口上重复测试策略，验证策略的时间稳定性。
支持固定窗口和扩展窗口两种模式，用于检测策略是否对市场环境变化敏感。

核心功能:
- 固定窗口回测（Fixed Window）
- 扩展窗口回测（Expanding Window）
- 窗口性能指标计算
- 稳定性评估
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

from src.evolution.strategy_evaluator import MarketType, StrategyEvaluator


class WindowMode(Enum):
    """窗口模式"""

    FIXED = "fixed"  # 固定窗口：窗口大小不变，向前滚动
    EXPANDING = "expanding"  # 扩展窗口：起始点固定，终点向前移动


@dataclass
class WindowResult:
    """单个窗口的回测结果

    Attributes:
        window_id: 窗口编号
        start_date: 窗口起始日期
        end_date: 窗口结束日期
        equity_curve: 净值曲线
        metrics: 性能指标
        trades: 交易记录（可选）
    """

    window_id: int
    start_date: datetime
    end_date: datetime
    equity_curve: pd.Series
    metrics: Dict[str, Any]
    trades: Optional[pd.Series] = None


@dataclass
class RollingBacktestResult:
    """滚动回测完整结果

    Attributes:
        window_results: 所有窗口的结果列表
        stability_metrics: 稳定性指标
        aggregated_metrics: 聚合指标
        mode: 窗口模式
        window_size_days: 窗口大小（天数）
        step_size_days: 步长（天数）
    """

    window_results: List[WindowResult]
    stability_metrics: Dict[str, Any]
    aggregated_metrics: Dict[str, Any]
    mode: WindowMode
    window_size_days: int
    step_size_days: int


class RollingBacktest:
    """滚动回测框架

    白皮书依据: 第四章 4.2 斯巴达竞技场 - 稳健性测试

    通过滚动窗口回测验证策略的时间稳定性。好的策略应该在不同时间段
    都能保持稳定的表现，而不是只在某个特定时期有效。

    Attributes:
        evaluator: 策略评价器
        window_mode: 窗口模式（固定/扩展）
        window_size_days: 窗口大小（交易日）
        step_size_days: 步长（交易日）
        min_window_size_days: 最小窗口大小
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        market_type: MarketType = MarketType.A_STOCK,
        window_mode: WindowMode = WindowMode.FIXED,
        window_size_days: int = 252,
        step_size_days: int = 63,
        min_window_size_days: int = 126,
    ):
        """初始化滚动回测框架

        Args:
            market_type: 市场类型
            window_mode: 窗口模式
            window_size_days: 窗口大小（交易日），默认252天（1年）
            step_size_days: 步长（交易日），默认63天（约3个月）
            min_window_size_days: 最小窗口大小，默认126天（半年）

        Raises:
            ValueError: 当参数不合法时
        """
        if window_size_days < min_window_size_days:
            raise ValueError(f"窗口大小必须 ≥ 最小窗口大小: " f"{window_size_days} < {min_window_size_days}")

        if step_size_days <= 0:
            raise ValueError(f"步长必须 > 0: {step_size_days}")

        if step_size_days > window_size_days:
            logger.warning(f"步长({step_size_days})大于窗口大小({window_size_days})，" f"窗口之间将没有重叠")

        self.evaluator = StrategyEvaluator(market_type=market_type)
        self.window_mode = window_mode
        self.window_size_days = window_size_days
        self.step_size_days = step_size_days
        self.min_window_size_days = min_window_size_days

        # 模式中文映射
        mode_names = {WindowMode.FIXED: "固定窗口", WindowMode.EXPANDING: "扩展窗口"}

        logger.info(
            f"RollingBacktest初始化完成 - "
            f"模式: {mode_names[window_mode]}, "
            f"窗口: {window_size_days}天, "
            f"步长: {step_size_days}天"
        )

    def run_backtest(
        self,
        strategy_func: Callable[[pd.DataFrame], Tuple[pd.Series, Optional[pd.Series]]],
        data: pd.DataFrame,
        freq: int = 252,
    ) -> RollingBacktestResult:
        """运行滚动回测

        Args:
            strategy_func: 策略函数，输入数据，返回(净值曲线, 交易记录)
            data: 完整的历史数据
            freq: 年化频率

        Returns:
            滚动回测结果

        Raises:
            ValueError: 当数据不足时
        """
        if len(data) < self.min_window_size_days:
            raise ValueError(f"数据长度不足: {len(data)} < {self.min_window_size_days}")

        logger.info(
            f"开始滚动回测 - "
            f"数据长度: {len(data)}, "
            f"模式: {['固定窗口', '扩展窗口'][self.window_mode == WindowMode.EXPANDING]}"
        )

        # 生成窗口
        windows = self._generate_windows(data)
        logger.info(f"生成 {len(windows)} 个窗口")

        # 对每个窗口运行回测
        window_results = []
        for window_id, (start_idx, end_idx) in enumerate(windows):
            window_data = data.iloc[start_idx:end_idx]

            try:
                # 运行策略
                equity, trades = strategy_func(window_data)

                # 评估性能
                metrics = self.evaluator.evaluate_strategy(equity=equity, trades=trades, freq=freq)

                # 记录结果
                result = WindowResult(
                    window_id=window_id,
                    start_date=window_data.index[0],
                    end_date=window_data.index[-1],
                    equity_curve=equity,
                    metrics=metrics,
                    trades=trades,
                )
                window_results.append(result)

                logger.info(
                    f"窗口 {window_id} 完成 - "
                    f"日期: {result.start_date.date()} ~ {result.end_date.date()}, "
                    f"年化收益: {metrics['annual_return']:.2%}, "
                    f"夏普: {metrics['sharpe']:.2f}"
                )

            except Exception as e:
                logger.error(
                    f"窗口 {window_id} 回测失败: {e}, "
                    f"日期: {window_data.index[0].date()} ~ {window_data.index[-1].date()}"
                )
                raise

        # 计算稳定性指标
        stability_metrics = self._calculate_stability_metrics(window_results)

        # 计算聚合指标
        aggregated_metrics = self._calculate_aggregated_metrics(window_results)

        logger.info(
            f"滚动回测完成 - "
            f"窗口数: {len(window_results)}, "
            f"平均年化收益: {aggregated_metrics['mean_annual_return']:.2%}, "
            f"收益稳定性: {stability_metrics['return_stability']:.2f}"
        )

        return RollingBacktestResult(
            window_results=window_results,
            stability_metrics=stability_metrics,
            aggregated_metrics=aggregated_metrics,
            mode=self.window_mode,
            window_size_days=self.window_size_days,
            step_size_days=self.step_size_days,
        )

    def _generate_windows(self, data: pd.DataFrame) -> List[Tuple[int, int]]:
        """生成窗口索引列表

        Args:
            data: 完整数据

        Returns:
            窗口索引列表 [(start_idx, end_idx), ...]
        """
        windows = []

        if self.window_mode == WindowMode.FIXED:
            # 固定窗口模式
            start_idx = 0
            while start_idx + self.window_size_days <= len(data):
                end_idx = start_idx + self.window_size_days
                windows.append((start_idx, end_idx))
                start_idx += self.step_size_days

        elif self.window_mode == WindowMode.EXPANDING:
            # 扩展窗口模式
            start_idx = 0
            end_idx = self.min_window_size_days

            while end_idx <= len(data):
                windows.append((start_idx, end_idx))
                end_idx += self.step_size_days

        return windows

    def _calculate_stability_metrics(self, window_results: List[WindowResult]) -> Dict[str, Any]:
        """计算稳定性指标

        Args:
            window_results: 所有窗口的结果

        Returns:
            稳定性指标字典
        """
        # 提取关键指标序列
        annual_returns = [r.metrics["annual_return"] for r in window_results]
        sharpe_ratios = [r.metrics["sharpe"] for r in window_results]
        [r.metrics["max_drawdown"] for r in window_results]  # pylint: disable=w0104

        # 计算稳定性（变异系数的倒数）
        return_stability = (
            1.0 / (np.std(annual_returns) / np.mean(annual_returns)) if np.mean(annual_returns) != 0 else 0.0
        )
        sharpe_stability = (
            1.0 / (np.std(sharpe_ratios) / np.mean(sharpe_ratios)) if np.mean(sharpe_ratios) != 0 else 0.0
        )

        # 计算正收益窗口占比
        positive_windows = sum(1 for r in annual_returns if r > 0)
        positive_ratio = positive_windows / len(annual_returns) if len(annual_returns) > 0 else 0.0

        # 计算最差窗口
        worst_window_idx = np.argmin(annual_returns)
        worst_window = window_results[worst_window_idx]

        # 计算最佳窗口
        best_window_idx = np.argmax(annual_returns)
        best_window = window_results[best_window_idx]

        return {
            "return_stability": return_stability,
            "sharpe_stability": sharpe_stability,
            "positive_window_ratio": positive_ratio,
            "worst_window_return": annual_returns[worst_window_idx],
            "worst_window_period": f"{worst_window.start_date.date()} ~ {worst_window.end_date.date()}",
            "best_window_return": annual_returns[best_window_idx],
            "best_window_period": f"{best_window.start_date.date()} ~ {best_window.end_date.date()}",
            "return_range": max(annual_returns) - min(annual_returns),
            "sharpe_range": max(sharpe_ratios) - min(sharpe_ratios),
        }

    def _calculate_aggregated_metrics(self, window_results: List[WindowResult]) -> Dict[str, Any]:
        """计算聚合指标

        Args:
            window_results: 所有窗口的结果

        Returns:
            聚合指标字典
        """
        # 提取所有指标
        annual_returns = [r.metrics["annual_return"] for r in window_results]
        sharpe_ratios = [r.metrics["sharpe"] for r in window_results]
        sortino_ratios = [r.metrics["sortino"] for r in window_results]
        max_drawdowns = [r.metrics["max_drawdown"] for r in window_results]
        calmar_ratios = [r.metrics["calmar"] for r in window_results if not np.isnan(r.metrics["calmar"])]

        return {
            "mean_annual_return": np.mean(annual_returns),
            "median_annual_return": np.median(annual_returns),
            "std_annual_return": np.std(annual_returns),
            "min_annual_return": np.min(annual_returns),
            "max_annual_return": np.max(annual_returns),
            "mean_sharpe": np.mean(sharpe_ratios),
            "median_sharpe": np.median(sharpe_ratios),
            "std_sharpe": np.std(sharpe_ratios),
            "min_sharpe": np.min(sharpe_ratios),
            "max_sharpe": np.max(sharpe_ratios),
            "mean_sortino": np.mean(sortino_ratios),
            "mean_max_drawdown": np.mean(max_drawdowns),
            "worst_max_drawdown": np.min(max_drawdowns),
            "mean_calmar": np.mean(calmar_ratios) if len(calmar_ratios) > 0 else np.nan,
            "num_windows": len(window_results),
        }

    def check_stability(
        self,
        result: RollingBacktestResult,
        min_positive_ratio: float = 0.7,
        max_return_cv: float = 1.0,
        max_sharpe_cv: float = 0.5,
    ) -> Dict[str, Any]:
        """检查策略稳定性

        Args:
            result: 滚动回测结果
            min_positive_ratio: 最小正收益窗口占比
            max_return_cv: 最大收益变异系数
            max_sharpe_cv: 最大夏普变异系数

        Returns:
            {
                'stable': bool,
                'passed_criteria': List[str],
                'failed_criteria': List[str]
            }
        """
        logger.info("开始稳定性检查")

        passed_criteria = []
        failed_criteria = []

        # 检查正收益窗口占比
        positive_ratio = result.stability_metrics["positive_window_ratio"]
        if positive_ratio >= min_positive_ratio:
            passed_criteria.append(f"正收益窗口占比达标: {positive_ratio:.1%} ≥ {min_positive_ratio:.1%}")
        else:
            failed_criteria.append(f"正收益窗口占比不足: {positive_ratio:.1%} < {min_positive_ratio:.1%}")

        # 检查收益稳定性
        return_stability = result.stability_metrics["return_stability"]
        return_cv = 1.0 / return_stability if return_stability > 0 else np.inf
        if return_cv <= max_return_cv:
            passed_criteria.append(f"收益稳定性达标: CV={return_cv:.2f} ≤ {max_return_cv:.2f}")
        else:
            failed_criteria.append(f"收益波动过大: CV={return_cv:.2f} > {max_return_cv:.2f}")

        # 检查夏普稳定性
        sharpe_stability = result.stability_metrics["sharpe_stability"]
        sharpe_cv = 1.0 / sharpe_stability if sharpe_stability > 0 else np.inf
        if sharpe_cv <= max_sharpe_cv:
            passed_criteria.append(f"夏普稳定性达标: CV={sharpe_cv:.2f} ≤ {max_sharpe_cv:.2f}")
        else:
            failed_criteria.append(f"夏普波动过大: CV={sharpe_cv:.2f} > {max_sharpe_cv:.2f}")

        # 检查最差窗口
        worst_return = result.stability_metrics["worst_window_return"]
        if worst_return > -0.10:  # 最差窗口亏损不超过10%
            passed_criteria.append(f"最差窗口可控: {worst_return:.2%} > -10%")
        else:
            failed_criteria.append(f"最差窗口亏损过大: {worst_return:.2%} ≤ -10%")

        stable = len(failed_criteria) == 0

        logger.info(
            f"稳定性检查完成 - "
            f"稳定: {stable}, "
            f"通过: {len(passed_criteria)}/{len(passed_criteria) + len(failed_criteria)}"
        )

        return {"stable": stable, "passed_criteria": passed_criteria, "failed_criteria": failed_criteria}
