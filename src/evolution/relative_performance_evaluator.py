"""
MIA系统相对表现评估器

白皮书依据: 第四章 4.3.1 相对表现评估体系
版本: v1.6.0
作者: MIA Team
日期: 2026-01-18

核心理念: 不要定死收益，让策略跑出最优表现，基于相对评估

功能特性:
1. 基准对比评估 (沪深300/中证500)
2. 同类策略排名
3. 风险调整后收益评估
4. 表现一致性分析
5. 市场适应性评估
6. 多维度综合评分
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import redis
from scipy import stats

from ..base.models import SimulationResult, Strategy
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BenchmarkType(Enum):
    """基准类型"""

    CSI_300 = "csi_300"  # 沪深300
    CSI_500 = "csi_500"  # 中证500
    CSI_1000 = "csi_1000"  # 中证1000
    SZSE_COMPONENT = "szse_comp"  # 深证成指
    CUSTOM = "custom"  # 自定义基准


class MarketRegime(Enum):
    """市场环境"""

    BULL = "bull"  # 牛市
    BEAR = "bear"  # 熊市
    SIDEWAYS = "sideways"  # 震荡市
    HIGH_VOL = "high_volatility"  # 高波动
    LOW_VOL = "low_volatility"  # 低波动


@dataclass
class RelativePerformanceResult:  # pylint: disable=too-many-instance-attributes
    """相对表现评估结果"""

    # 基准对比
    benchmark_outperformance: float  # 基准超额收益
    benchmark_correlation: float  # 与基准相关性
    tracking_error: float  # 跟踪误差
    information_ratio: float  # 信息比率

    # 同类对比
    peer_ranking_percentile: float  # 同类排名百分位
    peer_outperformance_rate: float  # 超越同类策略比例
    peer_risk_adjusted_ranking: float  # 风险调整后排名

    # 风险调整评估
    risk_adjusted_score: float  # 风险调整评分
    sharpe_ranking: float  # 夏普比率排名
    calmar_ranking: float  # 卡玛比率排名
    sortino_ranking: float  # 索提诺比率排名

    # 一致性评估
    consistency_score: float  # 表现一致性
    stability_score: float  # 收益稳定性
    drawdown_control_score: float  # 回撤控制评分

    # 适应性评估
    market_adaptation_score: float  # 市场适应性
    regime_performance: Dict[str, float]  # 不同环境表现
    volatility_adaptation: float  # 波动率适应性

    # 综合评分
    overall_relative_score: float  # 综合相对评分
    grade: str  # 评级 (A+, A, B+, B, C+, C, D)

    # 详细分析
    strengths: List[str]  # 优势分析
    weaknesses: List[str]  # 劣势分析
    recommendations: List[str]  # 改进建议


class RelativePerformanceEvaluator:
    """相对表现评估器

    白皮书依据: 第四章 4.3.1 相对表现评估体系

    核心理念: 让策略跑出最优表现，基于相对评估而非固定收益要求

    评估维度:
    1. 基准对比 - 与市场指数的相对表现
    2. 同类对比 - 与同类策略的排名
    3. 风险调整 - 夏普、卡玛、索提诺比率
    4. 一致性 - 不同时期的表现稳定性
    5. 适应性 - 不同市场环境的适应能力
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """初始化相对表现评估器

        Args:
            redis_client: Redis客户端，用于缓存基准数据
        """
        self.redis_client = redis_client or redis.Redis(host="localhost", port=6379, db=0)

        # 基准配置
        self.benchmark_configs = {
            BenchmarkType.CSI_300: {"name": "沪深300", "symbol": "000300.SH", "description": "大盘蓝筹股基准"},
            BenchmarkType.CSI_500: {"name": "中证500", "symbol": "000905.SH", "description": "中盘成长股基准"},
            BenchmarkType.CSI_1000: {"name": "中证1000", "symbol": "000852.SH", "description": "小盘股基准"},
        }

        # 评分权重配置
        self.evaluation_weights = {
            "benchmark_comparison": 0.30,  # 基准对比权重30%
            "peer_comparison": 0.25,  # 同类对比权重25%
            "risk_adjustment": 0.25,  # 风险调整权重25%
            "consistency": 0.15,  # 一致性权重15%
            "adaptation": 0.05,  # 适应性权重5%
        }

        logger.info("RelativePerformanceEvaluator 初始化完成")
        logger.info("核心理念: 让策略跑出最优表现，基于相对评估")

    async def evaluate_relative_performance(
        self,
        simulation_result: SimulationResult,
        strategy: Strategy,
        benchmark_type: BenchmarkType = BenchmarkType.CSI_300,
    ) -> RelativePerformanceResult:
        """评估策略相对表现

        Args:
            simulation_result: 模拟结果
            strategy: 策略对象
            benchmark_type: 基准类型

        Returns:
            相对表现评估结果
        """
        logger.info(f"开始评估策略 {strategy.name} 的相对表现")  # pylint: disable=logging-fstring-interpolation
        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"评估期间: {simulation_result.start_date} - {simulation_result.end_date}"
        )  # pylint: disable=logging-fstring-interpolation
        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"基准指数: {self.benchmark_configs[benchmark_type]['name']}"
        )  # pylint: disable=logging-fstring-interpolation

        # 1. 基准对比评估
        benchmark_analysis = await self._evaluate_benchmark_comparison(simulation_result, benchmark_type)

        # 2. 同类策略对比
        peer_analysis = await self._evaluate_peer_comparison(simulation_result, strategy)

        # 3. 风险调整评估
        risk_analysis = self._evaluate_risk_adjustment(simulation_result)

        # 4. 一致性评估
        consistency_analysis = self._evaluate_consistency(simulation_result)

        # 5. 适应性评估
        adaptation_analysis = await self._evaluate_market_adaptation(simulation_result, strategy)

        # 6. 综合评分计算
        overall_score = self._calculate_overall_score(
            benchmark_analysis, peer_analysis, risk_analysis, consistency_analysis, adaptation_analysis
        )

        # 7. 生成评级和建议
        grade = self._determine_grade(overall_score)
        strengths, weaknesses, recommendations = self._generate_analysis_insights(
            benchmark_analysis, peer_analysis, risk_analysis, consistency_analysis, adaptation_analysis
        )

        # 8. 构建结果
        result = RelativePerformanceResult(
            # 基准对比
            benchmark_outperformance=benchmark_analysis["outperformance"],
            benchmark_correlation=benchmark_analysis["correlation"],
            tracking_error=benchmark_analysis["tracking_error"],
            information_ratio=benchmark_analysis["information_ratio"],
            # 同类对比
            peer_ranking_percentile=peer_analysis["ranking_percentile"],
            peer_outperformance_rate=peer_analysis["outperformance_rate"],
            peer_risk_adjusted_ranking=peer_analysis["risk_adjusted_ranking"],
            # 风险调整
            risk_adjusted_score=risk_analysis["overall_score"],
            sharpe_ranking=risk_analysis["sharpe_ranking"],
            calmar_ranking=risk_analysis["calmar_ranking"],
            sortino_ranking=risk_analysis["sortino_ranking"],
            # 一致性
            consistency_score=consistency_analysis["overall_score"],
            stability_score=consistency_analysis["stability_score"],
            drawdown_control_score=consistency_analysis["drawdown_score"],
            # 适应性
            market_adaptation_score=adaptation_analysis["overall_score"],
            regime_performance=adaptation_analysis["regime_performance"],
            volatility_adaptation=adaptation_analysis["volatility_adaptation"],
            # 综合
            overall_relative_score=overall_score,
            grade=grade,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
        )

        logger.info("相对表现评估完成")
        logger.info(f"  综合评分: {overall_score:.2f}")  # pylint: disable=logging-fstring-interpolation
        logger.info(f"  评级: {grade}")  # pylint: disable=logging-fstring-interpolation
        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"  基准超额收益: {benchmark_analysis['outperformance']:.2%}"
        )  # pylint: disable=logging-fstring-interpolation
        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"  同类排名: {peer_analysis['ranking_percentile']:.1%}"
        )  # pylint: disable=logging-fstring-interpolation

        return result

    async def _evaluate_benchmark_comparison(
        self, simulation_result: SimulationResult, benchmark_type: BenchmarkType
    ) -> Dict[str, float]:
        """评估与基准的对比表现

        Args:
            simulation_result: 模拟结果
            benchmark_type: 基准类型

        Returns:
            基准对比分析结果
        """
        logger.debug(f"评估与 {benchmark_type.value} 的对比表现")  # pylint: disable=logging-fstring-interpolation

        # 1. 获取基准数据
        benchmark_data = await self._get_benchmark_data(
            benchmark_type, simulation_result.start_date, simulation_result.end_date
        )

        # 2. 计算基准收益
        benchmark_return = benchmark_data["total_return"]
        strategy_return = simulation_result.total_return

        # 3. 超额收益
        outperformance = strategy_return - benchmark_return

        # 4. 相关性分析
        if hasattr(simulation_result, "daily_returns") and len(simulation_result.daily_returns) > 0:
            strategy_daily_returns = np.array(simulation_result.daily_returns)
            benchmark_daily_returns = np.array(benchmark_data["daily_returns"])

            # 确保长度一致
            min_length = min(len(strategy_daily_returns), len(benchmark_daily_returns))
            strategy_daily_returns = strategy_daily_returns[:min_length]
            benchmark_daily_returns = benchmark_daily_returns[:min_length]

            # 相关系数
            correlation = np.corrcoef(strategy_daily_returns, benchmark_daily_returns)[0, 1]

            # 跟踪误差 (超额收益的标准差)
            excess_returns = strategy_daily_returns - benchmark_daily_returns
            tracking_error = np.std(excess_returns) * np.sqrt(252)  # 年化

            # 信息比率 (超额收益 / 跟踪误差)
            information_ratio = (outperformance / tracking_error) if tracking_error > 0 else 0
        else:
            correlation = 0.0
            tracking_error = 0.0
            information_ratio = 0.0

        # 5. Beta系数
        if hasattr(simulation_result, "daily_returns") and len(simulation_result.daily_returns) > 0:
            covariance = np.cov(strategy_daily_returns, benchmark_daily_returns)[0, 1]
            benchmark_variance = np.var(benchmark_daily_returns)
            beta = covariance / benchmark_variance if benchmark_variance > 0 else 1.0
        else:
            beta = 1.0

        result = {
            "outperformance": outperformance,
            "correlation": correlation,
            "tracking_error": tracking_error,
            "information_ratio": information_ratio,
            "beta": beta,
            "benchmark_return": benchmark_return,
            "strategy_return": strategy_return,
        }

        logger.debug(  # pylint: disable=logging-fstring-interpolation
            f"基准对比结果: 超额收益={outperformance:.2%}, 相关性={correlation:.2f}, 跟踪误差={tracking_error:.2%}"
        )
        return result

    async def _get_benchmark_data(
        self, benchmark_type: BenchmarkType, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """获取基准数据

        Args:
            benchmark_type: 基准类型
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            基准数据
        """
        # 尝试从Redis缓存获取
        cache_key = f"benchmark:{benchmark_type.value}:{start_date.strftime('%Y%m%d')}:{end_date.strftime('%Y%m%d')}"

        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                import json  # pylint: disable=import-outside-toplevel

                return json.loads(cached_data)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"Redis缓存读取失败: {e}")  # pylint: disable=logging-fstring-interpolation

        # 生成模拟基准数据 (实际应该从数据源获取)
        days = (end_date - start_date).days

        # 根据基准类型设置不同的收益特征
        if benchmark_type == BenchmarkType.CSI_300:
            daily_mean_return = 0.0003  # 沪深300日均收益0.03%
            daily_volatility = 0.015  # 日波动率1.5%
        elif benchmark_type == BenchmarkType.CSI_500:
            daily_mean_return = 0.0004  # 中证500日均收益0.04%
            daily_volatility = 0.018  # 日波动率1.8%
        else:
            daily_mean_return = 0.0002  # 其他指数日均收益0.02%
            daily_volatility = 0.020  # 日波动率2.0%

        # 生成日收益序列
        np.random.seed(42)  # 固定种子确保可重复
        daily_returns = np.random.normal(daily_mean_return, daily_volatility, days)

        # 计算累计收益
        cumulative_returns = np.cumprod(1 + daily_returns)
        total_return = cumulative_returns[-1] - 1

        benchmark_data = {
            "total_return": total_return,
            "daily_returns": daily_returns.tolist(),
            "volatility": daily_volatility * np.sqrt(252),  # 年化波动率
            "sharpe_ratio": (total_return * 252 / days) / (daily_volatility * np.sqrt(252)),
            "max_drawdown": self._calculate_max_drawdown(cumulative_returns),
        }

        # 缓存到Redis (缓存1小时)
        try:
            import json  # pylint: disable=import-outside-toplevel

            self.redis_client.setex(cache_key, 3600, json.dumps(benchmark_data))
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"Redis缓存写入失败: {e}")  # pylint: disable=logging-fstring-interpolation

        logger.debug(  # pylint: disable=logging-fstring-interpolation
            f"基准数据: 总收益={total_return:.2%}, 波动率={benchmark_data['volatility']:.2%}"
        )  # pylint: disable=logging-fstring-interpolation
        return benchmark_data

    def _calculate_max_drawdown(self, cumulative_returns: np.ndarray) -> float:
        """计算最大回撤

        Args:
            cumulative_returns: 累计收益序列

        Returns:
            最大回撤
        """
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / peak
        return abs(np.min(drawdown))

    async def _evaluate_peer_comparison(
        self, simulation_result: SimulationResult, strategy: Strategy
    ) -> Dict[str, float]:
        """评估与同类策略的对比

        Args:
            simulation_result: 模拟结果
            strategy: 策略对象

        Returns:
            同类对比分析结果
        """
        logger.debug(f"评估与同类 {strategy.type} 策略的对比")  # pylint: disable=logging-fstring-interpolation

        # 1. 获取同类策略数据
        peer_strategies = await self._get_peer_strategies_data(strategy.type)

        if not peer_strategies:
            logger.warning("未找到同类策略数据，使用默认评分")
            return {
                "ranking_percentile": 0.5,
                "outperformance_rate": 0.5,
                "risk_adjusted_ranking": 0.5,
                "peer_count": 0,
            }

        # 2. 收益排名
        peer_returns = [peer["total_return"] for peer in peer_strategies]
        strategy_return = simulation_result.total_return

        better_count = sum(1 for ret in peer_returns if strategy_return > ret)
        ranking_percentile = better_count / len(peer_returns)

        # 3. 超越比例
        outperformance_rate = ranking_percentile

        # 4. 风险调整后排名
        peer_sharpe_ratios = [peer.get("sharpe_ratio", 0) for peer in peer_strategies]
        strategy_sharpe = simulation_result.sharpe_ratio

        better_sharpe_count = sum(1 for sharpe in peer_sharpe_ratios if strategy_sharpe > sharpe)
        risk_adjusted_ranking = better_sharpe_count / len(peer_sharpe_ratios)

        result = {
            "ranking_percentile": ranking_percentile,
            "outperformance_rate": outperformance_rate,
            "risk_adjusted_ranking": risk_adjusted_ranking,
            "peer_count": len(peer_strategies),
            "peer_avg_return": np.mean(peer_returns),
            "peer_avg_sharpe": np.mean(peer_sharpe_ratios),
        }

        logger.debug(  # pylint: disable=logging-fstring-interpolation
            f"同类对比结果: 排名百分位={ranking_percentile:.1%}, 风险调整排名={risk_adjusted_ranking:.1%}"
        )  # pylint: disable=logging-fstring-interpolation
        return result

    async def _get_peer_strategies_data(self, strategy_type: str) -> List[Dict[str, float]]:
        """获取同类策略数据

        Args:
            strategy_type: 策略类型

        Returns:
            同类策略数据列表
        """
        # 尝试从Redis获取缓存数据
        cache_key = f"peer_strategies:{strategy_type}"

        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                import json  # pylint: disable=import-outside-toplevel

                return json.loads(cached_data)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"同类策略缓存读取失败: {e}")  # pylint: disable=logging-fstring-interpolation

        # 生成模拟同类策略数据 (实际应该从策略库获取)
        peer_count = 20  # 假设有20个同类策略

        # 根据策略类型设置不同的表现分布
        if strategy_type == "momentum":
            base_return = 0.08
            return_std = 0.04
            base_sharpe = 1.5
            sharpe_std = 0.3
        elif strategy_type == "mean_reversion":
            base_return = 0.06
            return_std = 0.03
            base_sharpe = 1.3
            sharpe_std = 0.25
        elif strategy_type == "factor_based":
            base_return = 0.10
            return_std = 0.05
            base_sharpe = 1.8
            sharpe_std = 0.4
        else:
            base_return = 0.07
            return_std = 0.035
            base_sharpe = 1.4
            sharpe_std = 0.3

        # 生成同类策略数据
        np.random.seed(hash(strategy_type) % 2**32)  # 基于策略类型的固定种子

        peer_strategies = []
        for i in range(peer_count):
            total_return = np.random.normal(base_return, return_std)
            sharpe_ratio = np.random.normal(base_sharpe, sharpe_std)

            peer_strategies.append(
                {
                    "strategy_id": f"peer_{strategy_type}_{i:02d}",
                    "total_return": max(total_return, -0.5),  # 限制最大亏损50%
                    "sharpe_ratio": max(sharpe_ratio, 0.1),  # 限制最小夏普0.1
                    "max_drawdown": np.random.uniform(0.05, 0.25),
                }
            )

        # 缓存数据 (缓存6小时)
        try:
            import json  # pylint: disable=import-outside-toplevel

            self.redis_client.setex(cache_key, 21600, json.dumps(peer_strategies))
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"同类策略缓存写入失败: {e}")  # pylint: disable=logging-fstring-interpolation

        logger.debug(  # pylint: disable=logging-fstring-interpolation
            f"获取到 {len(peer_strategies)} 个同类 {strategy_type} 策略"
        )  # pylint: disable=logging-fstring-interpolation
        return peer_strategies

    def _evaluate_risk_adjustment(self, simulation_result: SimulationResult) -> Dict[str, float]:
        """评估风险调整后表现

        Args:
            simulation_result: 模拟结果

        Returns:
            风险调整分析结果
        """
        logger.debug("评估风险调整后表现")

        # 1. 夏普比率评分 (2.0为优秀，3.0为卓越)
        sharpe_ratio = simulation_result.sharpe_ratio
        sharpe_score = min(sharpe_ratio / 3.0, 1.0)
        sharpe_ranking = self._score_to_percentile(sharpe_score)

        # 2. 卡玛比率评分 (年化收益/最大回撤)
        calmar_ratio = simulation_result.calmar_ratio
        calmar_score = min(calmar_ratio / 5.0, 1.0)  # 5.0为卓越
        calmar_ranking = self._score_to_percentile(calmar_score)

        # 3. 索提诺比率评分 (下行风险调整收益)
        if hasattr(simulation_result, "downside_deviation") and simulation_result.downside_deviation:
            sortino_ratio = simulation_result.annual_return / simulation_result.downside_deviation
        else:
            # 如果没有下行偏差数据，使用总波动率估算
            sortino_ratio = simulation_result.annual_return / (
                simulation_result.volatility * 0.7
            )  # 假设下行波动是总波动的70%

        sortino_score = min(sortino_ratio / 3.0, 1.0)  # 3.0为卓越
        sortino_ranking = self._score_to_percentile(sortino_score)

        # 4. 综合风险调整评分
        overall_score = sharpe_score * 0.4 + calmar_score * 0.35 + sortino_score * 0.25

        result = {
            "overall_score": overall_score,
            "sharpe_ranking": sharpe_ranking,
            "calmar_ranking": calmar_ranking,
            "sortino_ranking": sortino_ranking,
            "sharpe_ratio": sharpe_ratio,
            "calmar_ratio": calmar_ratio,
            "sortino_ratio": sortino_ratio,
        }

        logger.debug(  # pylint: disable=logging-fstring-interpolation
            f"风险调整评分: {overall_score:.2f} (夏普:{sharpe_score:.2f}, 卡玛:{calmar_score:.2f}, 索提诺:{sortino_score:.2f})"
        )
        return result

    def _score_to_percentile(self, score: float) -> float:
        """将评分转换为百分位排名

        Args:
            score: 评分 (0-1)

        Returns:
            百分位排名 (0-1)
        """
        # 使用sigmoid函数将评分映射到百分位
        # 这样可以让中等评分更集中在中位数附近
        return 1 / (1 + np.exp(-5 * (score - 0.5)))

    def _evaluate_consistency(self, simulation_result: SimulationResult) -> Dict[str, float]:
        """评估表现一致性

        Args:
            simulation_result: 模拟结果

        Returns:
            一致性分析结果
        """
        logger.debug("评估表现一致性")

        # 1. 收益稳定性评分
        if hasattr(simulation_result, "daily_returns") and len(simulation_result.daily_returns) > 0:
            daily_returns = np.array(simulation_result.daily_returns)

            # 偏度和峰度 (越接近正态分布越好)
            skewness = abs(stats.skew(daily_returns))
            kurtosis = abs(stats.kurtosis(daily_returns))

            # 稳定性评分 (偏度和峰度越小越好)
            stability_score = max(0, 1 - skewness * 0.2 - kurtosis * 0.1)

            # 收益序列的变异系数
            mean_return = np.mean(daily_returns)
            std_return = np.std(daily_returns)
            cv = abs(std_return / mean_return) if mean_return != 0 else float("inf")
            cv_score = max(0, 1 - min(cv / 5, 1))  # 变异系数5为临界点
        else:
            stability_score = 0.5
            cv_score = 0.5

        # 2. 回撤控制评分
        max_drawdown = simulation_result.max_drawdown
        drawdown_score = max(0, 1 - max_drawdown * 3)  # 回撤33%为0分

        # 3. 胜率稳定性
        win_rate = simulation_result.win_rate
        win_rate_score = win_rate  # 胜率本身就是稳定性指标

        # 4. 综合一致性评分
        overall_score = stability_score * 0.3 + drawdown_score * 0.4 + win_rate_score * 0.2 + cv_score * 0.1

        result = {
            "overall_score": overall_score,
            "stability_score": stability_score,
            "drawdown_score": drawdown_score,
            "win_rate_score": win_rate_score,
            "cv_score": cv_score,
            "skewness": skewness if "skewness" in locals() else 0,
            "kurtosis": kurtosis if "kurtosis" in locals() else 0,
        }

        logger.debug(  # pylint: disable=logging-fstring-interpolation
            f"一致性评分: {overall_score:.2f} (稳定性:{stability_score:.2f}, 回撤:{drawdown_score:.2f}, 胜率:{win_rate_score:.2f})"
        )
        return result

    async def _evaluate_market_adaptation(
        self, simulation_result: SimulationResult, strategy: Strategy  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:
        """评估市场适应性

        Args:
            simulation_result: 模拟结果
            strategy: 策略对象

        Returns:
            适应性分析结果
        """
        logger.debug("评估市场适应性")

        # 1. 波动率适应性
        strategy_volatility = simulation_result.volatility
        market_volatility = 0.20  # 假设市场年化波动率20%

        # 策略波动率与市场波动率的比值，接近1.0表示适应性好
        vol_ratio = strategy_volatility / market_volatility
        volatility_adaptation = max(0, 1 - abs(vol_ratio - 1.0))

        # 2. 不同市场环境表现 (模拟数据)
        regime_performance = {
            "bull_market": min(1.0, simulation_result.sharpe_ratio / 2.0),
            "bear_market": min(1.0, max(0, 1 + simulation_result.total_return)),  # 熊市中正收益为好
            "sideways_market": (
                min(1.0, simulation_result.information_ratio / 1.5) if simulation_result.information_ratio else 0.5
            ),
            "high_volatility": volatility_adaptation,
            "low_volatility": min(1.0, simulation_result.sharpe_ratio / 1.5),
        }

        # 3. 综合适应性评分
        overall_score = np.mean(list(regime_performance.values()))

        result = {
            "overall_score": overall_score,
            "volatility_adaptation": volatility_adaptation,
            "regime_performance": regime_performance,
            "vol_ratio": vol_ratio,
        }

        logger.debug(  # pylint: disable=logging-fstring-interpolation
            f"适应性评分: {overall_score:.2f} (波动率适应:{volatility_adaptation:.2f})"
        )  # pylint: disable=logging-fstring-interpolation
        return result

    def _calculate_overall_score(  # pylint: disable=too-many-positional-arguments
        self,
        benchmark_analysis: Dict[str, float],
        peer_analysis: Dict[str, float],
        risk_analysis: Dict[str, float],
        consistency_analysis: Dict[str, float],
        adaptation_analysis: Dict[str, Any],
    ) -> float:
        """计算综合相对评分

        Args:
            benchmark_analysis: 基准对比分析
            peer_analysis: 同类对比分析
            risk_analysis: 风险调整分析
            consistency_analysis: 一致性分析
            adaptation_analysis: 适应性分析

        Returns:
            综合相对评分 (0-1)
        """
        # 1. 基准对比评分 (30%)
        benchmark_score = min(1.0, max(0, benchmark_analysis["outperformance"] * 5 + 0.5))  # 超额收益20%为满分

        # 2. 同类对比评分 (25%)
        peer_score = peer_analysis["ranking_percentile"]

        # 3. 风险调整评分 (25%)
        risk_score = risk_analysis["overall_score"]

        # 4. 一致性评分 (15%)
        consistency_score = consistency_analysis["overall_score"]

        # 5. 适应性评分 (5%)
        adaptation_score = adaptation_analysis["overall_score"]

        # 6. 加权综合评分
        overall_score = (
            benchmark_score * self.evaluation_weights["benchmark_comparison"]
            + peer_score * self.evaluation_weights["peer_comparison"]
            + risk_score * self.evaluation_weights["risk_adjustment"]
            + consistency_score * self.evaluation_weights["consistency"]
            + adaptation_score * self.evaluation_weights["adaptation"]
        )

        logger.debug(  # pylint: disable=logging-fstring-interpolation
            f"综合评分计算: 基准({benchmark_score:.2f})*{self.evaluation_weights['benchmark_comparison']} + "
            f"同类({peer_score:.2f})*{self.evaluation_weights['peer_comparison']} + "
            f"风险({risk_score:.2f})*{self.evaluation_weights['risk_adjustment']} + "
            f"一致性({consistency_score:.2f})*{self.evaluation_weights['consistency']} + "
            f"适应性({adaptation_score:.2f})*{self.evaluation_weights['adaptation']} = {overall_score:.2f}"
        )

        return overall_score

    def _determine_grade(self, overall_score: float) -> str:  # pylint: disable=r0911
        """根据综合评分确定评级

        Args:
            overall_score: 综合评分 (0-1)

        Returns:
            评级字符串
        """
        if overall_score >= 0.90:  # pylint: disable=no-else-return
            return "A+"
        elif overall_score >= 0.85:
            return "A"
        elif overall_score >= 0.80:
            return "A-"
        elif overall_score >= 0.75:
            return "B+"
        elif overall_score >= 0.70:
            return "B"
        elif overall_score >= 0.65:
            return "B-"
        elif overall_score >= 0.60:
            return "C+"
        elif overall_score >= 0.55:
            return "C"
        elif overall_score >= 0.50:
            return "C-"
        else:
            return "D"

    def _generate_analysis_insights(  # pylint: disable=too-many-positional-arguments
        self,
        benchmark_analysis: Dict[str, float],
        peer_analysis: Dict[str, float],
        risk_analysis: Dict[str, float],
        consistency_analysis: Dict[str, float],
        adaptation_analysis: Dict[str, Any],
    ) -> Tuple[List[str], List[str], List[str]]:
        """生成分析洞察和建议

        Args:
            各项分析结果

        Returns:
            (优势列表, 劣势列表, 建议列表)
        """
        strengths = []
        weaknesses = []
        recommendations = []

        # 基准对比分析
        if benchmark_analysis["outperformance"] > 0.05:
            strengths.append(f"显著超越基准 {benchmark_analysis['outperformance']:.1%}")
        elif benchmark_analysis["outperformance"] < -0.02:
            weaknesses.append(f"跑输基准 {abs(benchmark_analysis['outperformance']):.1%}")
            recommendations.append("考虑优化选股逻辑或调整仓位管理")

        # 同类对比分析
        if peer_analysis["ranking_percentile"] > 0.8:
            strengths.append(f"同类策略排名前 {(1-peer_analysis['ranking_percentile'])*100:.0f}%")
        elif peer_analysis["ranking_percentile"] < 0.3:
            weaknesses.append(f"同类策略排名后 {peer_analysis['ranking_percentile']*100:.0f}%")
            recommendations.append("分析优秀同类策略的特征，学习改进")

        # 风险调整分析
        if risk_analysis["sharpe_ratio"] > 2.0:
            strengths.append(f"优秀的夏普比率 {risk_analysis['sharpe_ratio']:.2f}")
        elif risk_analysis["sharpe_ratio"] < 1.0:
            weaknesses.append(f"夏普比率偏低 {risk_analysis['sharpe_ratio']:.2f}")
            recommendations.append("提高收益或降低波动率以改善风险调整收益")

        # 一致性分析
        if consistency_analysis["overall_score"] > 0.8:
            strengths.append("表现一致性优秀")
        elif consistency_analysis["overall_score"] < 0.5:
            weaknesses.append("表现一致性不足")
            recommendations.append("优化策略参数以提高表现稳定性")

        # 回撤控制
        if consistency_analysis["drawdown_score"] > 0.8:
            strengths.append("回撤控制优秀")
        elif consistency_analysis["drawdown_score"] < 0.5:
            weaknesses.append("回撤控制不足")
            recommendations.append("加强止损机制和风险管理")

        # 适应性分析
        if adaptation_analysis["overall_score"] > 0.7:
            strengths.append("市场适应性良好")
        elif adaptation_analysis["overall_score"] < 0.4:
            weaknesses.append("市场适应性不足")
            recommendations.append("增强策略在不同市场环境下的鲁棒性")

        # 通用建议
        if not recommendations:
            recommendations.append("继续保持当前优秀表现")

        return strengths, weaknesses, recommendations
