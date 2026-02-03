"""Walk-Forward分析框架

白皮书依据: 第四章 4.2 斯巴达竞技场 - 防过拟合测试

Walk-Forward分析是防止策略过拟合的关键方法。通过将数据分为样本内（In-Sample）
和样本外（Out-of-Sample），在样本内优化参数，在样本外验证效果，模拟真实交易场景。

核心功能:
- 样本内参数优化（In-Sample Optimization）
- 样本外性能验证（Out-of-Sample Validation）
- 锚定模式（Anchored）和滚动模式（Rolling）
- 过拟合检测
- 效率比率计算
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

from src.evolution.strategy_evaluator import MarketType, StrategyEvaluator


class WalkForwardMode(Enum):
    """Walk-Forward模式"""

    ANCHORED = "anchored"  # 锚定模式：IS起点固定，OOS向前滚动
    ROLLING = "rolling"  # 滚动模式：IS和OOS都向前滚动


@dataclass
class WalkForwardPeriod:
    """单个Walk-Forward周期

    Attributes:
        period_id: 周期编号
        is_start_date: 样本内起始日期
        is_end_date: 样本内结束日期
        oos_start_date: 样本外起始日期
        oos_end_date: 样本外结束日期
        is_data: 样本内数据
        oos_data: 样本外数据
        optimal_params: 样本内优化得到的最优参数
        is_metrics: 样本内性能指标
        oos_metrics: 样本外性能指标
        is_equity: 样本内净值曲线
        oos_equity: 样本外净值曲线
    """

    period_id: int
    is_start_date: datetime
    is_end_date: datetime
    oos_start_date: datetime
    oos_end_date: datetime
    is_data: pd.DataFrame
    oos_data: pd.DataFrame
    optimal_params: Dict[str, Any]
    is_metrics: Dict[str, Any]
    oos_metrics: Dict[str, Any]
    is_equity: pd.Series
    oos_equity: pd.Series


@dataclass
class WalkForwardResult:
    """Walk-Forward分析完整结果

    Attributes:
        periods: 所有周期的结果列表
        combined_oos_equity: 合并的样本外净值曲线
        combined_oos_metrics: 合并的样本外性能指标
        overfitting_metrics: 过拟合检测指标
        efficiency_ratio: 效率比率（OOS/IS性能比）
        mode: Walk-Forward模式
        is_ratio: 样本内占比
    """

    periods: List[WalkForwardPeriod]
    combined_oos_equity: pd.Series
    combined_oos_metrics: Dict[str, Any]
    overfitting_metrics: Dict[str, Any]
    efficiency_ratio: float
    mode: WalkForwardMode
    is_ratio: float


class WalkForwardAnalysis:
    """Walk-Forward分析框架

    白皮书依据: 第四章 4.2 斯巴达竞技场 - 防过拟合测试

    Walk-Forward分析通过样本内优化、样本外验证的方式，检测策略是否过拟合。
    好的策略应该在样本外也能保持接近样本内的表现（效率比率 > 0.5）。

    Attributes:
        evaluator: 策略评价器
        mode: Walk-Forward模式
        is_ratio: 样本内数据占比
        oos_ratio: 样本外数据占比
        min_is_days: 最小样本内天数
        min_oos_days: 最小样本外天数
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        market_type: MarketType = MarketType.A_STOCK,
        mode: WalkForwardMode = WalkForwardMode.ROLLING,
        is_ratio: float = 0.7,
        min_is_days: int = 252,
        min_oos_days: int = 63,
    ):
        """初始化Walk-Forward分析框架

        Args:
            market_type: 市场类型
            mode: Walk-Forward模式
            is_ratio: 样本内数据占比，默认0.7（70%）
            min_is_days: 最小样本内天数，默认252天（1年）
            min_oos_days: 最小样本外天数，默认63天（约3个月）

        Raises:
            ValueError: 当参数不合法时
        """
        if not 0 < is_ratio < 1:
            raise ValueError(f"样本内占比必须在(0, 1)之间: {is_ratio}")

        if min_is_days <= 0:
            raise ValueError(f"最小样本内天数必须 > 0: {min_is_days}")

        if min_oos_days <= 0:
            raise ValueError(f"最小样本外天数必须 > 0: {min_oos_days}")

        self.evaluator = StrategyEvaluator(market_type=market_type)
        self.mode = mode
        self.is_ratio = is_ratio
        self.oos_ratio = 1.0 - is_ratio
        self.min_is_days = min_is_days
        self.min_oos_days = min_oos_days

        # 市场类型中文映射
        market_names = {MarketType.A_STOCK: "A股", MarketType.FUTURES: "期货", MarketType.CRYPTO: "加密货币"}

        # 模式中文映射
        mode_names = {WalkForwardMode.ANCHORED: "锚定模式", WalkForwardMode.ROLLING: "滚动模式"}

        logger.info(
            f"WalkForwardAnalysis初始化完成 - "
            f"市场类型: {market_names.get(market_type, market_type.value)}, "
            f"模式: {mode_names[mode]}, "
            f"IS占比: {is_ratio:.1%}, "
            f"OOS占比: {self.oos_ratio:.1%}"
        )

    def run_analysis(
        self,
        optimize_func: Callable[[pd.DataFrame], Dict[str, Any]],
        backtest_func: Callable[[pd.DataFrame, Dict[str, Any]], Tuple[pd.Series, Optional[pd.Series]]],
        data: pd.DataFrame,
        freq: int = 252,
    ) -> WalkForwardResult:
        """运行Walk-Forward分析

        Args:
            optimize_func: 参数优化函数，输入IS数据，返回最优参数
            backtest_func: 回测函数，输入数据和参数，返回(净值曲线, 交易记录)
            data: 完整的历史数据
            freq: 年化频率

        Returns:
            Walk-Forward分析结果

        Raises:
            ValueError: 当数据不足时
        """
        min_total_days = self.min_is_days + self.min_oos_days
        if len(data) < min_total_days:
            raise ValueError(f"数据长度不足: {len(data)} < {min_total_days}")

        # 模式中文映射
        mode_names = {WalkForwardMode.ANCHORED: "锚定模式", WalkForwardMode.ROLLING: "滚动模式"}

        logger.info(f"开始Walk-Forward分析 - " f"数据长度: {len(data)}, " f"模式: {mode_names[self.mode]}")

        # 生成周期
        periods_data = self._generate_periods(data)
        logger.info(f"生成 {len(periods_data)} 个周期")

        # 对每个周期进行优化和验证
        periods = []
        for period_id, (is_data, oos_data) in enumerate(periods_data):
            try:
                # 样本内优化
                logger.info(
                    f"周期 {period_id} - 样本内优化 " f"({is_data.index[0].date()} ~ {is_data.index[-1].date()})"
                )
                optimal_params = optimize_func(is_data)

                # 样本内回测
                is_equity, is_trades = backtest_func(is_data, optimal_params)
                is_metrics = self.evaluator.evaluate_strategy(equity=is_equity, trades=is_trades, freq=freq)

                # 样本外验证
                logger.info(
                    f"周期 {period_id} - 样本外验证 " f"({oos_data.index[0].date()} ~ {oos_data.index[-1].date()})"
                )
                oos_equity, oos_trades = backtest_func(oos_data, optimal_params)
                oos_metrics = self.evaluator.evaluate_strategy(equity=oos_equity, trades=oos_trades, freq=freq)

                # 记录结果
                period = WalkForwardPeriod(
                    period_id=period_id,
                    is_start_date=is_data.index[0],
                    is_end_date=is_data.index[-1],
                    oos_start_date=oos_data.index[0],
                    oos_end_date=oos_data.index[-1],
                    is_data=is_data,
                    oos_data=oos_data,
                    optimal_params=optimal_params,
                    is_metrics=is_metrics,
                    oos_metrics=oos_metrics,
                    is_equity=is_equity,
                    oos_equity=oos_equity,
                )
                periods.append(period)

                logger.info(
                    f"周期 {period_id} 完成 - "
                    f"IS夏普: {is_metrics['sharpe']:.2f}, "
                    f"OOS夏普: {oos_metrics['sharpe']:.2f}, "
                    f"效率比: {oos_metrics['sharpe']/is_metrics['sharpe']:.2f}"
                )

            except Exception as e:
                logger.error(f"周期 {period_id} 分析失败: {e}")
                raise

        # 合并样本外净值曲线
        combined_oos_equity = self._combine_oos_equity(periods)

        # 计算合并的样本外性能
        combined_oos_metrics = self.evaluator.evaluate_strategy(equity=combined_oos_equity, trades=None, freq=freq)

        # 计算过拟合指标
        overfitting_metrics = self._calculate_overfitting_metrics(periods)

        # 计算效率比率
        efficiency_ratio = self._calculate_efficiency_ratio(periods)

        logger.info(
            f"Walk-Forward分析完成 - "
            f"周期数: {len(periods)}, "
            f"OOS年化收益: {combined_oos_metrics['annual_return']:.2%}, "
            f"OOS夏普: {combined_oos_metrics['sharpe']:.2f}, "
            f"效率比率: {efficiency_ratio:.2f}"
        )

        return WalkForwardResult(
            periods=periods,
            combined_oos_equity=combined_oos_equity,
            combined_oos_metrics=combined_oos_metrics,
            overfitting_metrics=overfitting_metrics,
            efficiency_ratio=efficiency_ratio,
            mode=self.mode,
            is_ratio=self.is_ratio,
        )

    def _generate_periods(self, data: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """生成Walk-Forward周期

        Args:
            data: 完整数据

        Returns:
            周期列表 [(is_data, oos_data), ...]
        """
        periods = []

        if self.mode == WalkForwardMode.ANCHORED:
            # 锚定模式：IS起点固定
            is_start_idx = 0
            is_end_idx = self.min_is_days

            while is_end_idx + self.min_oos_days <= len(data):
                oos_end_idx = min(is_end_idx + self.min_oos_days, len(data))

                is_data = data.iloc[is_start_idx:is_end_idx]
                oos_data = data.iloc[is_end_idx:oos_end_idx]

                periods.append((is_data, oos_data))

                # 下一个周期：IS扩展，OOS向前移动
                is_end_idx = oos_end_idx

        elif self.mode == WalkForwardMode.ROLLING:
            # 滚动模式：IS和OOS都向前滚动
            total_period_days = int(self.min_is_days / self.is_ratio)
            oos_days = int(total_period_days * self.oos_ratio)

            start_idx = 0
            while start_idx + total_period_days <= len(data):
                is_end_idx = start_idx + self.min_is_days
                oos_end_idx = min(is_end_idx + oos_days, len(data))

                is_data = data.iloc[start_idx:is_end_idx]
                oos_data = data.iloc[is_end_idx:oos_end_idx]

                periods.append((is_data, oos_data))

                # 下一个周期：向前滚动OOS长度
                start_idx += oos_days

        return periods

    def _combine_oos_equity(self, periods: List[WalkForwardPeriod]) -> pd.Series:
        """合并所有周期的样本外净值曲线

        Args:
            periods: 所有周期

        Returns:
            合并的样本外净值曲线
        """
        combined_equity = pd.Series(dtype=float)

        for period in periods:
            # 归一化：每个OOS周期从上一个周期的结束值开始
            if len(combined_equity) == 0:
                # 第一个周期
                combined_equity = period.oos_equity.copy()
            else:
                # 后续周期：连接到前一个周期
                last_value = combined_equity.iloc[-1]
                first_value = period.oos_equity.iloc[0]

                # 归一化
                normalized_equity = period.oos_equity * (last_value / first_value)

                # 合并（去除重复的第一个点）
                combined_equity = pd.concat([combined_equity, normalized_equity.iloc[1:]])

        return combined_equity

    def _calculate_overfitting_metrics(self, periods: List[WalkForwardPeriod]) -> Dict[str, Any]:
        """计算过拟合检测指标

        Args:
            periods: 所有周期

        Returns:
            过拟合指标字典
        """
        # 提取IS和OOS的关键指标
        is_sharpes = [p.is_metrics["sharpe"] for p in periods]
        oos_sharpes = [p.oos_metrics["sharpe"] for p in periods]

        is_returns = [p.is_metrics["annual_return"] for p in periods]
        oos_returns = [p.oos_metrics["annual_return"] for p in periods]

        # 计算性能衰减
        sharpe_degradation = np.mean(is_sharpes) - np.mean(oos_sharpes)
        return_degradation = np.mean(is_returns) - np.mean(oos_returns)

        # 计算一致性（IS和OOS都为正的周期占比）
        consistent_periods = sum(
            1 for p in periods if p.is_metrics["annual_return"] > 0 and p.oos_metrics["annual_return"] > 0
        )
        consistency_ratio = consistent_periods / len(periods) if len(periods) > 0 else 0.0

        # 计算OOS失败周期（OOS为负收益）
        failed_oos_periods = sum(1 for p in periods if p.oos_metrics["annual_return"] < 0)
        failure_ratio = failed_oos_periods / len(periods) if len(periods) > 0 else 0.0

        # 判断是否过拟合
        is_overfitted = (
            sharpe_degradation > 0.5  # 夏普衰减超过0.5
            or return_degradation > 0.10  # 收益衰减超过10%
            or consistency_ratio < 0.6  # 一致性低于60%
            or failure_ratio > 0.3  # 失败率超过30%
        )

        return {
            "sharpe_degradation": sharpe_degradation,
            "return_degradation": return_degradation,
            "consistency_ratio": consistency_ratio,
            "failure_ratio": failure_ratio,
            "is_overfitted": is_overfitted,
            "mean_is_sharpe": np.mean(is_sharpes),
            "mean_oos_sharpe": np.mean(oos_sharpes),
            "mean_is_return": np.mean(is_returns),
            "mean_oos_return": np.mean(oos_returns),
        }

    def _calculate_efficiency_ratio(self, periods: List[WalkForwardPeriod]) -> float:
        """计算效率比率（OOS/IS性能比）

        Args:
            periods: 所有周期

        Returns:
            效率比率（0-1之间，越接近1越好）
        """
        # 使用夏普比率计算效率比
        is_sharpes = [p.is_metrics["sharpe"] for p in periods]
        oos_sharpes = [p.oos_metrics["sharpe"] for p in periods]

        mean_is_sharpe = np.mean(is_sharpes)
        mean_oos_sharpe = np.mean(oos_sharpes)

        if mean_is_sharpe <= 0:
            return 0.0

        efficiency = mean_oos_sharpe / mean_is_sharpe

        # 限制在[0, 1]范围内
        return max(0.0, min(1.0, efficiency))

    def check_overfitting(
        self,
        result: WalkForwardResult,
        min_efficiency_ratio: float = 0.5,
        max_sharpe_degradation: float = 0.5,
        min_consistency_ratio: float = 0.6,
    ) -> Dict[str, Any]:
        """检查策略是否过拟合

        Args:
            result: Walk-Forward分析结果
            min_efficiency_ratio: 最小效率比率
            max_sharpe_degradation: 最大夏普衰减
            min_consistency_ratio: 最小一致性比率

        Returns:
            {
                'not_overfitted': bool,
                'passed_criteria': List[str],
                'failed_criteria': List[str]
            }
        """
        logger.info("开始过拟合检查")

        passed_criteria = []
        failed_criteria = []

        # 检查效率比率
        if result.efficiency_ratio >= min_efficiency_ratio:
            passed_criteria.append(f"效率比率达标: {result.efficiency_ratio:.2f} ≥ {min_efficiency_ratio:.2f}")
        else:
            failed_criteria.append(f"效率比率过低: {result.efficiency_ratio:.2f} < {min_efficiency_ratio:.2f}")

        # 检查夏普衰减
        sharpe_degradation = result.overfitting_metrics["sharpe_degradation"]
        if sharpe_degradation <= max_sharpe_degradation:
            passed_criteria.append(f"夏普衰减可控: {sharpe_degradation:.2f} ≤ {max_sharpe_degradation:.2f}")
        else:
            failed_criteria.append(f"夏普衰减过大: {sharpe_degradation:.2f} > {max_sharpe_degradation:.2f}")

        # 检查一致性
        consistency_ratio = result.overfitting_metrics["consistency_ratio"]
        if consistency_ratio >= min_consistency_ratio:
            passed_criteria.append(f"IS-OOS一致性达标: {consistency_ratio:.1%} ≥ {min_consistency_ratio:.1%}")
        else:
            failed_criteria.append(f"IS-OOS一致性不足: {consistency_ratio:.1%} < {min_consistency_ratio:.1%}")

        # 检查OOS失败率
        failure_ratio = result.overfitting_metrics["failure_ratio"]
        if failure_ratio <= 0.3:
            passed_criteria.append(f"OOS失败率可控: {failure_ratio:.1%} ≤ 30%")
        else:
            failed_criteria.append(f"OOS失败率过高: {failure_ratio:.1%} > 30%")

        not_overfitted = len(failed_criteria) == 0

        logger.info(
            f"过拟合检查完成 - "
            f"未过拟合: {not_overfitted}, "
            f"通过: {len(passed_criteria)}/{len(passed_criteria) + len(failed_criteria)}"
        )

        return {
            "not_overfitted": not_overfitted,
            "passed_criteria": passed_criteria,
            "failed_criteria": failed_criteria,
        }
