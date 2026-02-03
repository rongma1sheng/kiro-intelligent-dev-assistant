"""
归因分析器 (Attribution Analyzer)

白皮书依据: 第一章 1.5.3 诊疗态任务调度
- Alpha/Beta分解
- 策略贡献度分析
- 因子暴露分析
- 交易成本分析

功能:
- 分解收益来源
- 计算策略贡献
- 分析因子暴露
"""

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("numpy/pandas未安装，部分功能不可用")


class AttributionType(Enum):
    """归因类型"""

    ALPHA_BETA = "Alpha/Beta分解"
    STRATEGY = "策略贡献"
    FACTOR = "因子暴露"
    SECTOR = "行业归因"
    TIMING = "择时归因"
    SELECTION = "选股归因"


@dataclass
class AlphaBetaDecomposition:
    """Alpha/Beta分解结果

    Attributes:
        alpha: Alpha收益
        beta: Beta系数
        benchmark_return: 基准收益
        portfolio_return: 组合收益
        tracking_error: 跟踪误差
        information_ratio: 信息比率
        r_squared: R平方
    """

    alpha: float
    beta: float
    benchmark_return: float
    portfolio_return: float
    tracking_error: float = 0.0
    information_ratio: float = 0.0
    r_squared: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "alpha": self.alpha,
            "beta": self.beta,
            "benchmark_return": self.benchmark_return,
            "portfolio_return": self.portfolio_return,
            "tracking_error": self.tracking_error,
            "information_ratio": self.information_ratio,
            "r_squared": self.r_squared,
        }


@dataclass
class StrategyContribution:
    """策略贡献

    Attributes:
        strategy_name: 策略名称
        return_contribution: 收益贡献
        weight: 策略权重
        sharpe_ratio: 夏普比率
        win_rate: 胜率
        trade_count: 交易次数
    """

    strategy_name: str
    return_contribution: float
    weight: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    trade_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_name": self.strategy_name,
            "return_contribution": self.return_contribution,
            "weight": self.weight,
            "sharpe_ratio": self.sharpe_ratio,
            "win_rate": self.win_rate,
            "trade_count": self.trade_count,
        }


@dataclass
class FactorExposure:
    """因子暴露

    Attributes:
        factor_name: 因子名称
        exposure: 暴露度
        return_contribution: 收益贡献
        t_stat: t统计量
        is_significant: 是否显著
    """

    factor_name: str
    exposure: float
    return_contribution: float = 0.0
    t_stat: float = 0.0
    is_significant: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "factor_name": self.factor_name,
            "exposure": self.exposure,
            "return_contribution": self.return_contribution,
            "t_stat": self.t_stat,
            "is_significant": self.is_significant,
        }


@dataclass
class SectorAttribution:
    """行业归因

    Attributes:
        sector: 行业名称
        allocation_effect: 配置效应
        selection_effect: 选择效应
        interaction_effect: 交互效应
        total_effect: 总效应
    """

    sector: str
    allocation_effect: float
    selection_effect: float
    interaction_effect: float = 0.0
    total_effect: float = 0.0

    def __post_init__(self):
        """计算总效应"""
        if self.total_effect == 0.0:
            self.total_effect = self.allocation_effect + self.selection_effect + self.interaction_effect

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "sector": self.sector,
            "allocation_effect": self.allocation_effect,
            "selection_effect": self.selection_effect,
            "interaction_effect": self.interaction_effect,
            "total_effect": self.total_effect,
        }


@dataclass
class AttributionReport:
    """归因分析报告

    Attributes:
        report_date: 报告日期
        period_start: 分析期间开始
        period_end: 分析期间结束
        alpha_beta: Alpha/Beta分解
        strategy_contributions: 策略贡献列表
        factor_exposures: 因子暴露列表
        sector_attributions: 行业归因列表
        total_return: 总收益
        benchmark_return: 基准收益
        excess_return: 超额收益
        timestamp: 生成时间
    """

    report_date: date
    period_start: date
    period_end: date
    alpha_beta: Optional[AlphaBetaDecomposition] = None
    strategy_contributions: List[StrategyContribution] = field(default_factory=list)
    factor_exposures: List[FactorExposure] = field(default_factory=list)
    sector_attributions: List[SectorAttribution] = field(default_factory=list)
    total_return: float = 0.0
    benchmark_return: float = 0.0
    excess_return: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_date": self.report_date.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "alpha_beta": self.alpha_beta.to_dict() if self.alpha_beta else None,
            "strategy_contributions": [s.to_dict() for s in self.strategy_contributions],
            "factor_exposures": [f.to_dict() for f in self.factor_exposures],
            "sector_attributions": [s.to_dict() for s in self.sector_attributions],
            "total_return": self.total_return,
            "benchmark_return": self.benchmark_return,
            "excess_return": self.excess_return,
            "timestamp": self.timestamp.isoformat(),
        }


class AttributionAnalyzer:
    """归因分析器

    白皮书依据: 第一章 1.5.3 诊疗态任务调度

    负责分解收益来源，计算策略贡献，分析因子暴露。

    Attributes:
        risk_free_rate: 无风险利率
        significance_level: 显著性水平

    Example:
        >>> analyzer = AttributionAnalyzer()
        >>> report = analyzer.analyze(portfolio_returns, benchmark_returns)
        >>> print(f"Alpha: {report.alpha_beta.alpha:.2%}")
    """

    def __init__(self, risk_free_rate: float = 0.03, significance_level: float = 0.05):
        """初始化归因分析器

        Args:
            risk_free_rate: 无风险利率 (年化)
            significance_level: 显著性水平
        """
        self.risk_free_rate = risk_free_rate
        self.significance_level = significance_level

        logger.info(f"归因分析器初始化: " f"无风险利率={risk_free_rate:.2%}, " f"显著性水平={significance_level}")

    def analyze(  # pylint: disable=too-many-positional-arguments
        self,
        portfolio_returns: List[float],
        benchmark_returns: List[float],
        strategy_returns: Optional[Dict[str, List[float]]] = None,
        factor_returns: Optional[Dict[str, List[float]]] = None,
        sector_data: Optional[Dict[str, Dict[str, float]]] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> AttributionReport:
        """执行归因分析

        白皮书依据: 第一章 1.5.3 归因分析

        Args:
            portfolio_returns: 组合收益序列
            benchmark_returns: 基准收益序列
            strategy_returns: 策略收益 {策略名: 收益序列}
            factor_returns: 因子收益 {因子名: 收益序列}
            sector_data: 行业数据 {行业: {权重, 收益}}
            period_start: 分析期间开始
            period_end: 分析期间结束

        Returns:
            归因分析报告
        """
        logger.info("开始归因分析")

        if period_start is None:
            period_start = date.today()
        if period_end is None:
            period_end = date.today()

        # 1. Alpha/Beta分解
        alpha_beta = self._decompose_alpha_beta(portfolio_returns, benchmark_returns)

        # 2. 策略贡献分析
        strategy_contributions = []
        if strategy_returns:
            strategy_contributions = self._analyze_strategy_contributions(strategy_returns, portfolio_returns)

        # 3. 因子暴露分析
        factor_exposures = []
        if factor_returns:
            factor_exposures = self._analyze_factor_exposures(portfolio_returns, factor_returns)

        # 4. 行业归因分析
        sector_attributions = []
        if sector_data:
            sector_attributions = self._analyze_sector_attribution(sector_data)

        # 计算总收益
        total_return = sum(portfolio_returns) if portfolio_returns else 0.0
        benchmark_total = sum(benchmark_returns) if benchmark_returns else 0.0
        excess_return = total_return - benchmark_total

        report = AttributionReport(
            report_date=date.today(),
            period_start=period_start,
            period_end=period_end,
            alpha_beta=alpha_beta,
            strategy_contributions=strategy_contributions,
            factor_exposures=factor_exposures,
            sector_attributions=sector_attributions,
            total_return=total_return,
            benchmark_return=benchmark_total,
            excess_return=excess_return,
        )

        logger.info(f"归因分析完成: " f"Alpha={alpha_beta.alpha:.4f}, " f"Beta={alpha_beta.beta:.4f}")

        return report

    def _decompose_alpha_beta(
        self, portfolio_returns: List[float], benchmark_returns: List[float]
    ) -> AlphaBetaDecomposition:
        """Alpha/Beta分解

        白皮书依据: 第一章 1.5.3 Alpha/Beta分解
        """
        if not portfolio_returns or not benchmark_returns:
            return AlphaBetaDecomposition(alpha=0.0, beta=1.0, benchmark_return=0.0, portfolio_return=0.0)

        # 确保长度一致
        min_len = min(len(portfolio_returns), len(benchmark_returns))
        p_returns = portfolio_returns[:min_len]
        b_returns = benchmark_returns[:min_len]

        # 计算均值
        p_mean = sum(p_returns) / len(p_returns)
        b_mean = sum(b_returns) / len(b_returns)

        # 计算Beta (协方差/方差)
        covariance = sum((p - p_mean) * (b - b_mean) for p, b in zip(p_returns, b_returns)) / len(p_returns)

        variance = sum((b - b_mean) ** 2 for b in b_returns) / len(b_returns)

        beta = covariance / variance if variance > 0 else 1.0

        # 计算Alpha
        alpha = p_mean - beta * b_mean

        # 计算跟踪误差
        tracking_errors = [p - b for p, b in zip(p_returns, b_returns)]
        te_mean = sum(tracking_errors) / len(tracking_errors)
        tracking_error = (sum((te - te_mean) ** 2 for te in tracking_errors) / len(tracking_errors)) ** 0.5

        # 计算信息比率
        information_ratio = alpha / tracking_error if tracking_error > 0 else 0.0

        # 计算R平方
        ss_res = sum((p - (alpha + beta * b)) ** 2 for p, b in zip(p_returns, b_returns))
        ss_tot = sum((p - p_mean) ** 2 for p in p_returns)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        return AlphaBetaDecomposition(
            alpha=alpha,
            beta=beta,
            benchmark_return=sum(b_returns),
            portfolio_return=sum(p_returns),
            tracking_error=tracking_error,
            information_ratio=information_ratio,
            r_squared=r_squared,
        )

    def _analyze_strategy_contributions(
        self, strategy_returns: Dict[str, List[float]], portfolio_returns: List[float]
    ) -> List[StrategyContribution]:
        """策略贡献分析

        白皮书依据: 第一章 1.5.3 策略贡献度分析
        """
        contributions = []
        sum(portfolio_returns) if portfolio_returns else 0.0  # pylint: disable=w0106

        for strategy_name, returns in strategy_returns.items():
            if not returns:
                continue

            strategy_return = sum(returns)

            # 计算权重 (假设等权)
            weight = 1.0 / len(strategy_returns)

            # 计算收益贡献
            return_contribution = strategy_return * weight

            # 计算夏普比率
            mean_return = sum(returns) / len(returns)
            std_return = (sum((r - mean_return) ** 2 for r in returns) / len(returns)) ** 0.5

            daily_rf = self.risk_free_rate / 252
            sharpe_ratio = (mean_return - daily_rf) / std_return * (252**0.5) if std_return > 0 else 0.0

            # 计算胜率
            winning_days = sum(1 for r in returns if r > 0)
            win_rate = winning_days / len(returns) if returns else 0.0

            contributions.append(
                StrategyContribution(
                    strategy_name=strategy_name,
                    return_contribution=return_contribution,
                    weight=weight,
                    sharpe_ratio=sharpe_ratio,
                    win_rate=win_rate,
                    trade_count=len(returns),
                )
            )

        # 按贡献排序
        contributions.sort(key=lambda x: x.return_contribution, reverse=True)

        return contributions

    def _analyze_factor_exposures(
        self, portfolio_returns: List[float], factor_returns: Dict[str, List[float]]
    ) -> List[FactorExposure]:
        """因子暴露分析

        白皮书依据: 第一章 1.5.3 因子暴露分析
        """
        exposures = []

        for factor_name, f_returns in factor_returns.items():
            if not f_returns or not portfolio_returns:
                continue

            # 确保长度一致
            min_len = min(len(portfolio_returns), len(f_returns))
            p_returns = portfolio_returns[:min_len]
            f_rets = f_returns[:min_len]

            # 计算因子暴露 (回归系数)
            p_mean = sum(p_returns) / len(p_returns)
            f_mean = sum(f_rets) / len(f_rets)

            covariance = sum((p - p_mean) * (f - f_mean) for p, f in zip(p_returns, f_rets)) / len(p_returns)

            variance = sum((f - f_mean) ** 2 for f in f_rets) / len(f_rets)

            exposure = covariance / variance if variance > 0 else 0.0

            # 计算收益贡献
            return_contribution = exposure * sum(f_rets)

            # 计算t统计量 (简化版)
            residuals = [p - exposure * f for p, f in zip(p_returns, f_rets)]
            residual_std = (sum(r**2 for r in residuals) / len(residuals)) ** 0.5

            se = residual_std / (variance**0.5 * len(f_rets) ** 0.5) if variance > 0 else 1.0
            t_stat = exposure / se if se > 0 else 0.0

            # 判断显著性 (简化: |t| > 2)
            is_significant = abs(t_stat) > 2.0

            exposures.append(
                FactorExposure(
                    factor_name=factor_name,
                    exposure=exposure,
                    return_contribution=return_contribution,
                    t_stat=t_stat,
                    is_significant=is_significant,
                )
            )

        # 按暴露度排序
        exposures.sort(key=lambda x: abs(x.exposure), reverse=True)

        return exposures

    def _analyze_sector_attribution(self, sector_data: Dict[str, Dict[str, float]]) -> List[SectorAttribution]:
        """行业归因分析

        白皮书依据: 第一章 1.5.3 行业归因

        使用Brinson模型分解:
        - 配置效应: (组合权重 - 基准权重) * 基准收益
        - 选择效应: 基准权重 * (组合收益 - 基准收益)
        - 交互效应: (组合权重 - 基准权重) * (组合收益 - 基准收益)
        """
        attributions = []

        for sector, data in sector_data.items():
            portfolio_weight = data.get("portfolio_weight", 0.0)
            benchmark_weight = data.get("benchmark_weight", 0.0)
            portfolio_return = data.get("portfolio_return", 0.0)
            benchmark_return = data.get("benchmark_return", 0.0)

            # Brinson归因
            allocation_effect = (portfolio_weight - benchmark_weight) * benchmark_return
            selection_effect = benchmark_weight * (portfolio_return - benchmark_return)
            interaction_effect = (portfolio_weight - benchmark_weight) * (portfolio_return - benchmark_return)

            attributions.append(
                SectorAttribution(
                    sector=sector,
                    allocation_effect=allocation_effect,
                    selection_effect=selection_effect,
                    interaction_effect=interaction_effect,
                )
            )

        # 按总效应排序
        attributions.sort(key=lambda x: x.total_effect, reverse=True)

        return attributions

    def calculate_sharpe_ratio(self, returns: List[float], annualize: bool = True) -> float:
        """计算夏普比率

        Args:
            returns: 收益序列
            annualize: 是否年化

        Returns:
            夏普比率
        """
        if not returns:
            return 0.0

        mean_return = sum(returns) / len(returns)
        std_return = (sum((r - mean_return) ** 2 for r in returns) / len(returns)) ** 0.5

        if std_return == 0:
            return 0.0

        daily_rf = self.risk_free_rate / 252
        sharpe = (mean_return - daily_rf) / std_return

        if annualize:
            sharpe *= 252**0.5

        return sharpe

    def calculate_information_ratio(self, portfolio_returns: List[float], benchmark_returns: List[float]) -> float:
        """计算信息比率

        Args:
            portfolio_returns: 组合收益序列
            benchmark_returns: 基准收益序列

        Returns:
            信息比率
        """
        if not portfolio_returns or not benchmark_returns:
            return 0.0

        min_len = min(len(portfolio_returns), len(benchmark_returns))
        excess_returns = [p - b for p, b in zip(portfolio_returns[:min_len], benchmark_returns[:min_len])]

        mean_excess = sum(excess_returns) / len(excess_returns)
        std_excess = (sum((r - mean_excess) ** 2 for r in excess_returns) / len(excess_returns)) ** 0.5

        if std_excess == 0:
            return 0.0

        return mean_excess / std_excess * (252**0.5)

    async def analyze_async(
        self, portfolio_returns: List[float], benchmark_returns: List[float], **kwargs
    ) -> AttributionReport:
        """异步执行归因分析

        Args:
            portfolio_returns: 组合收益序列
            benchmark_returns: 基准收益序列
            **kwargs: 其他参数

        Returns:
            归因分析报告
        """
        return await asyncio.to_thread(self.analyze, portfolio_returns, benchmark_returns, **kwargs)
