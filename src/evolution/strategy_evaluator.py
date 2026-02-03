"""策略评价器 - 投研级评价体系

白皮书依据: 第四章 4.2 斯巴达竞技场

基于量化投研专业标准的策略评价系统，包含：
- 收益质量评估
- 风险结构分析
- 交易层面指标
- 稳健性测试
- 分市场阈值体系
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger


class MarketType(Enum):
    """市场类型"""

    A_STOCK = "a_stock"  # A股
    FUTURES = "futures"  # 期货
    CRYPTO = "crypto"  # 加密货币


@dataclass
class EvaluationThresholds:
    """评价阈值

    定义不同市场的合格/优秀标准
    """

    # 收益质量
    min_annual_return: float
    excellent_annual_return: float
    min_sharpe: float
    excellent_sharpe: float
    min_calmar: float
    excellent_calmar: float

    # 风险结构
    max_drawdown: float
    excellent_max_drawdown: float
    max_dd_duration_months: int
    excellent_dd_duration_months: int

    # 交易结构
    min_win_rate: Optional[float] = None
    min_payoff_ratio: Optional[float] = None
    max_single_loss_pct: Optional[float] = None

    # 尾部风险
    min_cvar: float = -0.05  # CVaR(5%)
    excellent_cvar: float = -0.03


# 分市场阈值配置
MARKET_THRESHOLDS = {
    MarketType.A_STOCK: EvaluationThresholds(
        min_annual_return=0.12,
        excellent_annual_return=0.18,
        min_sharpe=1.2,
        excellent_sharpe=1.6,
        min_calmar=0.6,
        excellent_calmar=1.0,
        max_drawdown=-0.20,
        excellent_max_drawdown=-0.15,
        max_dd_duration_months=6,
        excellent_dd_duration_months=3,
        min_win_rate=0.45,
        min_cvar=-0.03,
        excellent_cvar=-0.02,
    ),
    MarketType.FUTURES: EvaluationThresholds(
        min_annual_return=0.15,
        excellent_annual_return=0.25,
        min_sharpe=1.0,
        excellent_sharpe=1.4,
        min_calmar=0.8,
        excellent_calmar=1.2,
        max_drawdown=-0.25,
        excellent_max_drawdown=-0.18,
        max_dd_duration_months=9,
        excellent_dd_duration_months=5,
        min_payoff_ratio=2.0,
        max_single_loss_pct=-0.02,
        min_cvar=-0.05,
        excellent_cvar=-0.03,
    ),
    MarketType.CRYPTO: EvaluationThresholds(
        min_annual_return=0.20,
        excellent_annual_return=0.40,
        min_sharpe=1.0,
        excellent_sharpe=1.5,
        min_calmar=0.8,
        excellent_calmar=1.2,
        max_drawdown=-0.30,
        excellent_max_drawdown=-0.20,
        max_dd_duration_months=4,
        excellent_dd_duration_months=2,
        min_cvar=-0.05,
        excellent_cvar=-0.03,
    ),
}


class StrategyEvaluator:
    """策略评价器

    白皮书依据: 第四章 4.2 斯巴达竞技场

    提供投研级的策略评价功能，包括：
    1. 收益质量评估（Return Quality）
    2. 风险结构分析（Risk Structure）
    3. 交易层面指标（Trade Structure）
    4. 稳健性测试（Robustness）
    """

    def __init__(self, market_type: MarketType = MarketType.A_STOCK):
        """初始化策略评价器

        Args:
            market_type: 市场类型，决定评价阈值
        """
        self.market_type = market_type
        self.thresholds = MARKET_THRESHOLDS[market_type]

        # 市场类型中文映射
        market_names = {MarketType.A_STOCK: "A股", MarketType.FUTURES: "期货", MarketType.CRYPTO: "加密货币"}

        logger.info(f"StrategyEvaluator初始化完成 - 市场类型: {market_names[market_type]}")

    # ============================
    # 基础收益指标
    # ============================

    def calc_returns(self, equity: pd.Series) -> pd.Series:
        """计算收益率序列

        Args:
            equity: 净值曲线

        Returns:
            收益率序列
        """
        return equity.pct_change().dropna()

    def annualized_return(self, equity: pd.Series, freq: int = 252) -> float:
        """计算年化收益率

        Args:
            equity: 净值曲线
            freq: 年化频率（252=日频，12=月频）

        Returns:
            年化收益率
        """
        if len(equity) < 2:
            return 0.0

        total_return = equity.iloc[-1] / equity.iloc[0] - 1
        years = len(equity) / freq

        if years <= 0:
            return 0.0

        return (1 + total_return) ** (1 / years) - 1

    def sharpe_ratio(self, ret: pd.Series, rf: float = 0.0, freq: int = 252) -> float:
        """计算夏普比率

        白皮书依据: 第四章 4.1 因子评估标准

        Args:
            ret: 收益率序列
            rf: 无风险利率
            freq: 年化频率

        Returns:
            夏普比率
        """
        if len(ret) == 0:
            return 0.0

        excess = ret - rf / freq
        std = excess.std()

        # 处理零标准差或接近零的情况
        if std == 0 or std < 1e-10:
            return 0.0

        return np.sqrt(freq) * excess.mean() / std

    def sortino_ratio(self, ret: pd.Series, rf: float = 0.0, freq: int = 252) -> float:
        """计算Sortino比率（只惩罚下行波动）

        Args:
            ret: 收益率序列
            rf: 无风险利率
            freq: 年化频率

        Returns:
            Sortino比率
        """
        downside = ret[ret < 0]

        if len(downside) == 0 or downside.std() == 0:
            return 0.0

        excess = ret - rf / freq
        return np.sqrt(freq) * excess.mean() / downside.std()

    # ============================
    # 回撤与风险结构
    # ============================

    def max_drawdown(self, equity: pd.Series) -> float:
        """计算最大回撤

        Args:
            equity: 净值曲线

        Returns:
            最大回撤（负数）
        """
        if len(equity) == 0:
            return 0.0

        cummax = equity.cummax()
        drawdown = equity / cummax - 1
        return drawdown.min()

    def drawdown_duration(self, equity: pd.Series) -> int:
        """计算最大回撤持续时间

        Args:
            equity: 净值曲线

        Returns:
            最大回撤持续天数
        """
        if len(equity) == 0:
            return 0

        cummax = equity.cummax()
        underwater = equity < cummax

        if not underwater.any():
            return 0

        durations = underwater.astype(int).groupby((~underwater).cumsum()).sum()
        return int(durations.max())

    def calmar_ratio(self, equity: pd.Series, freq: int = 252) -> float:
        """计算Calmar比率（年化收益/最大回撤）

        Args:
            equity: 净值曲线
            freq: 年化频率

        Returns:
            Calmar比率
        """
        ann_ret = self.annualized_return(equity, freq)
        mdd = abs(self.max_drawdown(equity))

        if mdd == 0:
            return np.nan

        return ann_ret / mdd

    def cvar(self, ret: pd.Series, alpha: float = 0.05) -> float:
        """计算条件风险价值（CVaR / Expected Shortfall）

        Args:
            ret: 收益率序列
            alpha: 置信水平（默认5%）

        Returns:
            CVaR值
        """
        if len(ret) == 0:
            return 0.0

        threshold = ret.quantile(alpha)
        return ret[ret <= threshold].mean()

    # ============================
    # 交易层面指标
    # ============================

    def trade_expectancy(self, trades: pd.Series) -> Tuple[float, float, float]:
        """计算交易期望值

        白皮书依据: 第四章 4.1 交易评估标准

        Args:
            trades: 每笔交易收益率序列

        Returns:
            (胜率, 盈亏比, 期望值)
        """
        if len(trades) == 0:
            return 0.0, 0.0, 0.0

        win = trades[trades > 0]
        loss = trades[trades < 0]

        win_rate = len(win) / len(trades)

        # 计算盈亏比
        if len(loss) == 0:
            payoff = np.inf if len(win) > 0 else 0.0
        elif len(win) == 0:
            payoff = 0.0
        else:
            payoff = win.mean() / abs(loss.mean())

        # 计算期望值
        if len(win) == 0 and len(loss) == 0:
            expectancy = 0.0
        elif len(win) == 0:
            # 全亏损情况
            expectancy = loss.mean()
        elif len(loss) == 0:
            # 全盈利情况
            expectancy = win.mean()
        else:
            # 正常情况
            expectancy = win_rate * win.mean() + (1 - win_rate) * loss.mean()

        return win_rate, payoff, expectancy

    def max_consecutive_losses(self, trades: pd.Series) -> int:
        """计算最大连续亏损次数

        Args:
            trades: 每笔交易收益率序列

        Returns:
            最大连续亏损次数
        """
        if len(trades) == 0:
            return 0

        is_loss = trades < 0
        consecutive = is_loss.astype(int).groupby((~is_loss).cumsum()).sum()

        return int(consecutive.max()) if len(consecutive) > 0 else 0

    # ============================
    # 综合评价
    # ============================

    def evaluate_strategy(
        self, equity: pd.Series, trades: Optional[pd.Series] = None, freq: int = 252
    ) -> Dict[str, Any]:
        """综合评价策略

        Args:
            equity: 净值曲线
            trades: 每笔交易收益率序列（可选）
            freq: 年化频率

        Returns:
            评价结果字典
        """
        logger.info(f"开始策略评价 - 数据点数: {len(equity)}")

        ret = self.calc_returns(equity)

        # 收益质量
        result = {
            "annual_return": self.annualized_return(equity, freq),
            "sharpe": self.sharpe_ratio(ret, freq=freq),
            "sortino": self.sortino_ratio(ret, freq=freq),
            "max_drawdown": self.max_drawdown(equity),
            "calmar": self.calmar_ratio(equity, freq),
            "max_dd_duration_days": self.drawdown_duration(equity),
            "cvar_5pct": self.cvar(ret, alpha=0.05),
        }

        # 交易层面指标
        if trades is not None and len(trades) > 0:
            win_rate, payoff, expectancy = self.trade_expectancy(trades)
            max_consec_loss = self.max_consecutive_losses(trades)

            result.update(
                {
                    "win_rate": win_rate,
                    "payoff_ratio": payoff,
                    "expectancy": expectancy,
                    "max_consecutive_losses": max_consec_loss,
                    "max_single_loss": trades.min() if len(trades) > 0 else 0.0,
                }
            )

        logger.info(f"策略评价完成 - 年化收益: {result['annual_return']:.2%}, 夏普: {result['sharpe']:.2f}")

        return result

    def check_thresholds(self, metrics: Dict[str, Any]) -> Dict[str, Any]:  # pylint: disable=too-many-branches
        """检查指标是否达到阈值

        Args:
            metrics: 评价指标字典

        Returns:
            {
                'qualified': bool,
                'excellent': bool,
                'passed_criteria': List[str],
                'failed_criteria': List[str],
                'grade': str
            }
        """
        logger.info("开始阈值检查")

        passed_criteria = []
        failed_criteria = []
        excellent_count = 0
        total_criteria = 0

        # 检查年化收益
        total_criteria += 1
        if metrics["annual_return"] >= self.thresholds.min_annual_return:
            passed_criteria.append(f"年化收益达标: {metrics['annual_return']:.2%}")
            if metrics["annual_return"] >= self.thresholds.excellent_annual_return:
                excellent_count += 1
        else:
            failed_criteria.append(
                f"年化收益不达标: {metrics['annual_return']:.2%} < " f"{self.thresholds.min_annual_return:.2%}"
            )

        # 检查夏普比率
        total_criteria += 1
        if metrics["sharpe"] >= self.thresholds.min_sharpe:
            passed_criteria.append(f"夏普比率达标: {metrics['sharpe']:.2f}")
            if metrics["sharpe"] >= self.thresholds.excellent_sharpe:
                excellent_count += 1
        else:
            failed_criteria.append(f"夏普比率不达标: {metrics['sharpe']:.2f} < " f"{self.thresholds.min_sharpe:.2f}")

        # 检查Calmar比率
        total_criteria += 1
        if not np.isnan(metrics["calmar"]) and metrics["calmar"] >= self.thresholds.min_calmar:
            passed_criteria.append(f"Calmar比率达标: {metrics['calmar']:.2f}")
            if metrics["calmar"] >= self.thresholds.excellent_calmar:
                excellent_count += 1
        else:
            failed_criteria.append(f"Calmar比率不达标: {metrics['calmar']:.2f} < " f"{self.thresholds.min_calmar:.2f}")

        # 检查最大回撤
        total_criteria += 1
        if metrics["max_drawdown"] >= self.thresholds.max_drawdown:
            passed_criteria.append(f"最大回撤达标: {metrics['max_drawdown']:.2%}")
            if metrics["max_drawdown"] >= self.thresholds.excellent_max_drawdown:
                excellent_count += 1
        else:
            failed_criteria.append(
                f"最大回撤超限: {metrics['max_drawdown']:.2%} < " f"{self.thresholds.max_drawdown:.2%}"
            )

        # 检查回撤持续时间
        total_criteria += 1
        dd_duration_months = metrics["max_dd_duration_days"] / 21  # 约21个交易日/月
        if dd_duration_months <= self.thresholds.max_dd_duration_months:
            passed_criteria.append(f"回撤持续时间达标: {dd_duration_months:.1f}月")
            if dd_duration_months <= self.thresholds.excellent_dd_duration_months:
                excellent_count += 1
        else:
            failed_criteria.append(
                f"回撤持续时间过长: {dd_duration_months:.1f}月 > " f"{self.thresholds.max_dd_duration_months}月"
            )

        # 检查CVaR
        total_criteria += 1
        if metrics["cvar_5pct"] >= self.thresholds.min_cvar:
            passed_criteria.append(f"CVaR(5%)达标: {metrics['cvar_5pct']:.2%}")
            if metrics["cvar_5pct"] >= self.thresholds.excellent_cvar:
                excellent_count += 1
        else:
            failed_criteria.append(f"CVaR(5%)风险过高: {metrics['cvar_5pct']:.2%} < " f"{self.thresholds.min_cvar:.2%}")

        # 检查交易层面指标（如果有）
        if "win_rate" in metrics and self.thresholds.min_win_rate is not None:
            total_criteria += 1
            if metrics["win_rate"] >= self.thresholds.min_win_rate:
                passed_criteria.append(f"胜率达标: {metrics['win_rate']:.2%}")
            else:
                failed_criteria.append(
                    f"胜率不达标: {metrics['win_rate']:.2%} < " f"{self.thresholds.min_win_rate:.2%}"
                )

        if "payoff_ratio" in metrics and self.thresholds.min_payoff_ratio is not None:
            total_criteria += 1
            if metrics["payoff_ratio"] >= self.thresholds.min_payoff_ratio:
                passed_criteria.append(f"盈亏比达标: {metrics['payoff_ratio']:.2f}")
            else:
                failed_criteria.append(
                    f"盈亏比不达标: {metrics['payoff_ratio']:.2f} < " f"{self.thresholds.min_payoff_ratio:.2f}"
                )

        if "max_single_loss" in metrics and self.thresholds.max_single_loss_pct is not None:
            total_criteria += 1
            if metrics["max_single_loss"] >= self.thresholds.max_single_loss_pct:
                passed_criteria.append(f"单笔最大亏损可控: {metrics['max_single_loss']:.2%}")
            else:
                failed_criteria.append(
                    f"单笔最大亏损过大: {metrics['max_single_loss']:.2%} < "
                    f"{self.thresholds.max_single_loss_pct:.2%}"
                )

        # 判断是否合格
        qualified = len(failed_criteria) == 0

        # 判断是否优秀（80%以上指标达到优秀标准）
        excellent = qualified and (excellent_count / total_criteria >= 0.8)

        # 评级
        if excellent:
            grade = "优秀"
        elif qualified:
            grade = "合格"
        else:
            grade = "不合格"

        logger.info(
            f"阈值检查完成 - "
            f"合格: {qualified}, "
            f"优秀: {excellent}, "
            f"评级: {grade}, "
            f"通过: {len(passed_criteria)}/{total_criteria}"
        )

        return {
            "qualified": qualified,
            "excellent": excellent,
            "passed_criteria": passed_criteria,
            "failed_criteria": failed_criteria,
            "grade": grade,
            "excellent_ratio": excellent_count / total_criteria if total_criteria > 0 else 0.0,
        }

    # ============================
    # 稳健性测试
    # ============================

    def parameter_sensitivity_test(self, metric_series: pd.Series, metric_name: str = "Sharpe") -> Dict[str, Any]:
        """参数敏感性测试

        Args:
            metric_series: 不同参数下的指标值序列
            metric_name: 指标名称

        Returns:
            {
                'mean': float,
                'std': float,
                'min': float,
                'max': float,
                'robust': bool  # 最小值是否仍为正
            }
        """
        logger.info(f"参数敏感性测试 - 指标: {metric_name}, 样本数: {len(metric_series)}")

        result = {
            "mean": metric_series.mean(),
            "std": metric_series.std(),
            "min": metric_series.min(),
            "max": metric_series.max(),
            "robust": metric_series.min() > 0,
        }

        logger.info(
            f"敏感性测试完成 - "
            f"均值: {result['mean']:.2f}, "
            f"标准差: {result['std']:.2f}, "
            f"稳健: {result['robust']}"
        )

        return result
