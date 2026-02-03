# pylint: disable=too-many-lines
"""Commander因子决策引擎

白皮书依据: 第四章 4.2.3 Commander因子集成

将Arena验证的因子集成到Commander的投资决策流程中，
生成因子驱动的投资建议。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger


class RecommendationAction(Enum):
    """投资建议动作"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class MarketRegime(Enum):
    """市场状态"""

    BULL = "牛市"
    BEAR = "熊市"
    SIDEWAYS = "震荡市"
    HIGH_VOLATILITY = "高波动"
    LOW_VOLATILITY = "低波动"


@dataclass
class RiskMetrics:
    """风险指标

    白皮书依据: 第四章 4.2.3 风险指标计算
    """

    volatility: float
    beta: float
    var_95: float
    max_drawdown: float
    sharpe_ratio: float

    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            "volatility": self.volatility,
            "beta": self.beta,
            "var_95": self.var_95,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
        }


@dataclass
class FactorRecommendation:
    """因子投资建议

    白皮书依据: 第四章 4.2.3 因子建议生成

    Attributes:
        symbol: 股票代码
        action: 投资动作 (BUY/SELL/HOLD)
        target_weight: 目标仓位权重
        confidence: 置信度 [0, 1]
        factor_source: 来源因子ID
        factor_value: 因子值
        factor_rank: 因子排名百分位
        reasoning: 建议理由
        risk_metrics: 风险指标
        expected_return: 预期收益率
        timestamp: 生成时间
    """

    symbol: str
    action: RecommendationAction
    target_weight: float
    confidence: float
    factor_source: str
    factor_value: float
    factor_rank: float
    reasoning: str
    risk_metrics: Optional[RiskMetrics] = None
    expected_return: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def apply_weight(self, weight: float) -> "FactorRecommendation":
        """应用因子权重

        Args:
            weight: 因子权重

        Returns:
            加权后的建议
        """
        return FactorRecommendation(
            symbol=self.symbol,
            action=self.action,
            target_weight=self.target_weight * weight,
            confidence=self.confidence * weight,
            factor_source=self.factor_source,
            factor_value=self.factor_value,
            factor_rank=self.factor_rank,
            reasoning=self.reasoning,
            risk_metrics=self.risk_metrics,
            expected_return=self.expected_return * weight,
            timestamp=self.timestamp,
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "action": self.action.value,
            "target_weight": self.target_weight,
            "confidence": self.confidence,
            "factor_source": self.factor_source,
            "factor_value": self.factor_value,
            "factor_rank": self.factor_rank,
            "reasoning": self.reasoning,
            "risk_metrics": self.risk_metrics.to_dict() if self.risk_metrics else None,
            "expected_return": self.expected_return,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class IntegratedFactor:
    """集成的因子

    白皮书依据: 第四章 4.2.3 因子集成
    """

    factor_id: str
    name: str
    expression: str
    arena_score: float
    z2h_certified: bool
    integration_date: datetime
    initial_weight: float
    current_weight: float
    baseline_ic: float
    expected_sharpe: float
    regime_weights: Dict[MarketRegime, float] = field(default_factory=dict)
    performance_history: List[Dict[str, float]] = field(default_factory=list)
    hit_rate: float = 0.0
    total_recommendations: int = 0
    successful_recommendations: int = 0


@dataclass
class FactorPerformanceTracker:
    """因子表现跟踪器

    白皮书依据: 第四章 4.2.3 因子表现跟踪
    """

    factor_id: str
    baseline_ic: float
    expected_sharpe: float
    recent_ic: List[float] = field(default_factory=list)
    recent_returns: List[float] = field(default_factory=list)
    hit_count: int = 0
    miss_count: int = 0

    def update_performance(self, ic: float, realized_return: float, predicted_direction: bool) -> None:
        """更新表现

        Args:
            ic: 当前IC值
            realized_return: 实现收益
            predicted_direction: 预测方向是否正确
        """
        self.recent_ic.append(ic)
        self.recent_returns.append(realized_return)

        # 保留最近20个数据点
        if len(self.recent_ic) > 20:
            self.recent_ic = self.recent_ic[-20:]
        if len(self.recent_returns) > 20:
            self.recent_returns = self.recent_returns[-20:]

        if predicted_direction:
            self.hit_count += 1
        else:
            self.miss_count += 1

    def get_recent_performance(self) -> Dict[str, float]:
        """获取近期表现"""
        if not self.recent_ic:
            return {
                "avg_ic": self.baseline_ic,
                "ic_std": 0.0,
                "avg_return": 0.0,
                "hit_rate": 0.5,
                "sharpe": self.expected_sharpe,
            }

        avg_ic = np.mean(self.recent_ic)
        ic_std = np.std(self.recent_ic) if len(self.recent_ic) > 1 else 0.0
        avg_return = np.mean(self.recent_returns) if self.recent_returns else 0.0

        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total if total > 0 else 0.5

        # 计算夏普比率
        if self.recent_returns and len(self.recent_returns) > 1:
            ret_std = np.std(self.recent_returns)
            sharpe = (avg_return * 252) / (ret_std * np.sqrt(252)) if ret_std > 0 else 0.0
        else:
            sharpe = self.expected_sharpe

        return {"avg_ic": avg_ic, "ic_std": ic_std, "avg_return": avg_return, "hit_rate": hit_rate, "sharpe": sharpe}


@dataclass
class FactorCorrelationMatrix:
    """因子相关性矩阵

    白皮书依据: 第四章 4.2.3 因子相关性分析
    """

    factor_ids: List[str] = field(default_factory=list)
    correlation_matrix: Optional[np.ndarray] = None
    last_update: Optional[datetime] = None

    def update(self, factor_values: Dict[str, pd.Series]) -> None:
        """更新相关性矩阵

        Args:
            factor_values: 因子ID到因子值序列的映射
        """
        if not factor_values:
            return

        self.factor_ids = list(factor_values.keys())
        n = len(self.factor_ids)

        if n < 2:
            self.correlation_matrix = np.array([[1.0]])
            self.last_update = datetime.now()
            return

        # 构建数据框
        df = pd.DataFrame(factor_values)

        # 计算相关性矩阵
        corr = df.corr(method="spearman").values

        # 处理NaN
        corr = np.nan_to_num(corr, nan=0.0)

        self.correlation_matrix = corr
        self.last_update = datetime.now()

    def get_correlation(self, factor_id1: str, factor_id2: str) -> float:
        """获取两个因子的相关性

        Args:
            factor_id1: 因子1 ID
            factor_id2: 因子2 ID

        Returns:
            相关系数
        """
        if self.correlation_matrix is None:
            return 0.0

        if factor_id1 not in self.factor_ids or factor_id2 not in self.factor_ids:
            return 0.0

        idx1 = self.factor_ids.index(factor_id1)
        idx2 = self.factor_ids.index(factor_id2)

        return float(self.correlation_matrix[idx1, idx2])

    def get_redundant_pairs(self, threshold: float = 0.9) -> List[Tuple[str, str, float]]:
        """获取冗余因子对

        Args:
            threshold: 相关性阈值

        Returns:
            冗余因子对列表 [(factor_id1, factor_id2, correlation), ...]
        """
        if self.correlation_matrix is None or len(self.factor_ids) < 2:
            return []

        redundant = []
        n = len(self.factor_ids)

        for i in range(n):
            for j in range(i + 1, n):
                corr = abs(self.correlation_matrix[i, j])
                if corr > threshold:
                    redundant.append((self.factor_ids[i], self.factor_ids[j], corr))

        return redundant


class CommanderFactorDecisionEngine:
    """Commander因子决策引擎

    白皮书依据: 第四章 4.2.3 Commander因子集成

    将Arena验证的因子集成到Commander的投资决策流程中，
    生成因子驱动的投资建议。

    Attributes:
        validated_factors: 验证因子字典 {factor_id: IntegratedFactor}
        factor_weights: 因子权重字典 {factor_id: weight}
        factor_performance: 因子表现跟踪器字典
        factor_correlations: 因子相关性矩阵
        current_regime: 当前市场状态
        current_holdings: 当前持仓
    """

    def __init__(self):
        """初始化Commander因子决策引擎

        白皮书依据: 第四章 4.2.3 Commander因子集成
        """
        self.validated_factors: Dict[str, IntegratedFactor] = {}
        self.factor_weights: Dict[str, float] = {}
        self.factor_performance: Dict[str, FactorPerformanceTracker] = {}
        self.factor_correlations = FactorCorrelationMatrix()
        self.current_regime: MarketRegime = MarketRegime.SIDEWAYS
        self.current_holdings: Dict[str, float] = {}
        self._recommendation_history: List[FactorRecommendation] = []

        logger.info("Commander因子决策引擎初始化完成")

    async def integrate_arena_factors(self, arena_results: List[Dict[str, Any]]) -> int:
        """集成Arena验证的因子

        白皮书依据: 第四章 4.2.3 因子集成

        Args:
            arena_results: Arena测试结果列表，每个结果包含:
                - factor_id: 因子ID
                - name: 因子名称
                - expression: 因子表达式
                - passed: 是否通过
                - overall_score: 综合得分
                - reality_score: 现实轨道得分
                - z2h_eligible: 是否Z2H合格

        Returns:
            成功集成的因子数量

        Raises:
            ValueError: 当arena_results为空时
        """
        if not arena_results:
            raise ValueError("Arena结果列表不能为空")

        integrated_count = 0

        for result in arena_results:
            if not result.get("passed", False):
                logger.debug(f"因子 {result.get('factor_id', 'unknown')} 未通过Arena测试，跳过")
                continue

            factor_id = result["factor_id"]

            # 计算初始权重
            initial_weight = self._calculate_initial_weight(
                arena_score=result.get("overall_score", 0.5), z2h_certified=result.get("z2h_eligible", False)
            )

            # 创建集成因子
            integrated_factor = IntegratedFactor(
                factor_id=factor_id,
                name=result.get("name", f"Factor_{factor_id}"),
                expression=result.get("expression", ""),
                arena_score=result.get("overall_score", 0.5),
                z2h_certified=result.get("z2h_eligible", False),
                integration_date=datetime.now(),
                initial_weight=initial_weight,
                current_weight=initial_weight,
                baseline_ic=result.get("reality_score", 0.03),
                expected_sharpe=result.get("overall_score", 0.5) * 1.2,
            )

            # 初始化市场状态权重（确保在有效范围内）
            integrated_factor.regime_weights = {
                MarketRegime.BULL: min(1.0, initial_weight * 1.1),
                MarketRegime.BEAR: max(0.1, initial_weight * 0.8),
                MarketRegime.SIDEWAYS: initial_weight,
                MarketRegime.HIGH_VOLATILITY: max(0.1, initial_weight * 0.9),
                MarketRegime.LOW_VOLATILITY: min(1.0, initial_weight * 1.05),
            }

            # 添加到验证因子库
            self.validated_factors[factor_id] = integrated_factor
            self.factor_weights[factor_id] = initial_weight

            # 初始化性能跟踪
            self.factor_performance[factor_id] = FactorPerformanceTracker(
                factor_id=factor_id,
                baseline_ic=result.get("reality_score", 0.03),
                expected_sharpe=result.get("overall_score", 0.5) * 1.2,
            )

            integrated_count += 1
            logger.info(f"因子 {integrated_factor.name} 已集成到Commander决策系统，初始权重: {initial_weight:.4f}")

        return integrated_count

    def _calculate_initial_weight(self, arena_score: float, z2h_certified: bool) -> float:
        """计算初始因子权重

        白皮书依据: 第四章 4.2.3 因子权重计算

        Args:
            arena_score: Arena综合得分
            z2h_certified: 是否Z2H认证

        Returns:
            初始权重 [0.1, 1.0]
        """
        # 基础权重 = Arena得分
        base_weight = arena_score

        # Z2H认证加成
        if z2h_certified:
            base_weight *= 1.2

        # 限制在有效范围内
        return max(0.1, min(1.0, base_weight))

    async def generate_factor_based_recommendations(
        self, market_data: pd.DataFrame, factor_values: Optional[Dict[str, pd.Series]] = None
    ) -> List[FactorRecommendation]:
        """基于验证因子生成投资建议

        白皮书依据: 第四章 4.2.3 因子建议生成

        Args:
            market_data: 市场数据，索引为日期，列为股票代码
            factor_values: 预计算的因子值，如果为None则自动计算

        Returns:
            投资建议列表

        Raises:
            ValueError: 当没有验证因子时
        """
        if not self.validated_factors:
            raise ValueError("没有可用的验证因子，请先调用integrate_arena_factors")

        if market_data.empty:
            raise ValueError("市场数据不能为空")

        recommendations: List[FactorRecommendation] = []

        # 如果提供了因子值，更新相关性矩阵
        if factor_values:
            self.factor_correlations.update(factor_values)

        for factor_id, validated_factor in self.validated_factors.items():
            # 获取因子值
            if factor_values and factor_id in factor_values:
                current_factor_values = factor_values[factor_id]
            else:
                # 使用模拟因子值（实际应用中应计算真实因子值）
                current_factor_values = self._simulate_factor_values(market_data)

            # 动态调整因子权重
            current_performance = self.factor_performance[factor_id].get_recent_performance()
            adjusted_weight = self._adjust_factor_weight(factor_id, current_performance)
            self.factor_weights[factor_id] = adjusted_weight
            validated_factor.current_weight = adjusted_weight

            # 生成因子建议
            factor_recommendations = await self._generate_factor_recommendations(
                validated_factor, current_factor_values, market_data
            )

            # 应用因子权重
            weighted_recommendations = [rec.apply_weight(adjusted_weight) for rec in factor_recommendations]

            recommendations.extend(weighted_recommendations)

        # 去相关性处理
        decorrelated_recommendations = await self._decorrelate_recommendations(recommendations)

        # 冲突解决
        resolved_recommendations = await self._resolve_conflicts(decorrelated_recommendations)

        # 风险预算分配
        final_recommendations = await self._apply_risk_budgeting(resolved_recommendations)

        # 记录历史
        self._recommendation_history.extend(final_recommendations)

        return final_recommendations

    def _simulate_factor_values(self, market_data: pd.DataFrame) -> pd.Series:
        """模拟因子值（用于测试）

        Args:
            market_data: 市场数据

        Returns:
            模拟的因子值序列
        """
        if market_data.empty:
            return pd.Series(dtype=float)

        # 使用收益率作为模拟因子值
        if len(market_data) > 1:
            returns = market_data.iloc[-1] / market_data.iloc[-2] - 1
        else:
            returns = pd.Series(0.0, index=market_data.columns)

        return returns

    def _adjust_factor_weight(self, factor_id: str, performance: Dict[str, float]) -> float:
        """动态调整因子权重

        白皮书依据: 第四章 4.2.3 动态权重调整

        Args:
            factor_id: 因子ID
            performance: 近期表现指标

        Returns:
            调整后的权重
        """
        if factor_id not in self.validated_factors:
            return 0.5

        factor = self.validated_factors[factor_id]
        base_weight = factor.initial_weight

        # 基于IC调整
        avg_ic = performance.get("avg_ic", factor.baseline_ic)
        ic_ratio = avg_ic / factor.baseline_ic if factor.baseline_ic > 0 else 1.0

        # 基于命中率调整
        hit_rate = performance.get("hit_rate", 0.5)
        hit_rate_factor = hit_rate / 0.5  # 50%为基准

        # 基于夏普比率调整
        sharpe = performance.get("sharpe", factor.expected_sharpe)
        sharpe_ratio = sharpe / factor.expected_sharpe if factor.expected_sharpe > 0 else 1.0

        # 综合调整
        adjustment = ic_ratio * 0.4 + hit_rate_factor * 0.3 + sharpe_ratio * 0.3
        adjusted_weight = base_weight * adjustment

        # 应用市场状态权重
        regime_weight = factor.regime_weights.get(self.current_regime, base_weight)
        adjusted_weight = (adjusted_weight + regime_weight) / 2

        # 限制在有效范围内
        return max(0.1, min(1.0, adjusted_weight))

    async def _generate_factor_recommendations(
        self, validated_factor: IntegratedFactor, factor_values: pd.Series, market_data: pd.DataFrame
    ) -> List[FactorRecommendation]:
        """生成单个因子的投资建议

        白皮书依据: 第四章 4.2.3 因子建议生成

        Args:
            validated_factor: 验证因子
            factor_values: 因子值序列
            market_data: 市场数据

        Returns:
            投资建议列表
        """
        recommendations = []

        if factor_values.empty:
            return recommendations

        # 因子排序
        factor_ranks = factor_values.rank(pct=True)

        # 生成买入建议（顶部20%）
        top_stocks = factor_ranks[factor_ranks > 0.8].index.tolist()
        for symbol in top_stocks:
            factor_strength = factor_ranks[symbol]
            confidence = self._calculate_confidence(validated_factor, symbol, factor_strength)

            target_weight = self._calculate_target_weight(validated_factor, factor_strength, confidence)

            risk_metrics = self._calculate_risk_metrics(symbol, market_data)
            expected_return = self._estimate_expected_return(validated_factor, factor_strength)

            recommendation = FactorRecommendation(
                symbol=symbol,
                action=RecommendationAction.BUY,
                target_weight=target_weight,
                confidence=confidence,
                factor_source=validated_factor.factor_id,
                factor_value=factor_values[symbol],
                factor_rank=factor_strength,
                reasoning=f"基于{validated_factor.name}因子，该股票排名前20%",
                risk_metrics=risk_metrics,
                expected_return=expected_return,
            )

            recommendations.append(recommendation)

        # 生成卖出建议（底部20%，如果当前持有）
        bottom_stocks = factor_ranks[factor_ranks < 0.2].index.tolist()

        for symbol in bottom_stocks:
            if symbol in self.current_holdings:
                confidence = self._calculate_confidence(validated_factor, symbol, factor_ranks[symbol])

                risk_metrics = self._calculate_risk_metrics(symbol, market_data)

                recommendation = FactorRecommendation(
                    symbol=symbol,
                    action=RecommendationAction.SELL,
                    target_weight=0.0,
                    confidence=confidence,
                    factor_source=validated_factor.factor_id,
                    factor_value=factor_values[symbol],
                    factor_rank=factor_ranks[symbol],
                    reasoning=f"基于{validated_factor.name}因子，该股票排名后20%",
                    risk_metrics=risk_metrics,
                    expected_return=0.0,
                )

                recommendations.append(recommendation)

        return recommendations

    def _calculate_confidence(
        self, validated_factor: IntegratedFactor, symbol: str, factor_strength: float  # pylint: disable=unused-argument
    ) -> float:  # pylint: disable=unused-argument
        """计算建议置信度

        Args:
            validated_factor: 验证因子
            symbol: 股票代码
            factor_strength: 因子强度

        Returns:
            置信度 [0, 1]
        """
        # 基础置信度 = Arena得分
        base_confidence = validated_factor.arena_score

        # 因子强度调整
        strength_factor = abs(factor_strength - 0.5) * 2  # 距离中位数越远越强

        # Z2H认证加成
        z2h_bonus = 0.1 if validated_factor.z2h_certified else 0.0

        # 命中率调整
        hit_rate = validated_factor.hit_rate if validated_factor.total_recommendations > 10 else 0.5
        hit_rate_factor = hit_rate

        confidence = base_confidence * 0.4 + strength_factor * 0.3 + hit_rate_factor * 0.2 + z2h_bonus

        return max(0.0, min(1.0, confidence))

    def _calculate_target_weight(
        self, validated_factor: IntegratedFactor, factor_strength: float, confidence: float
    ) -> float:
        """计算目标仓位权重

        Args:
            validated_factor: 验证因子
            factor_strength: 因子强度
            confidence: 置信度

        Returns:
            目标权重 [0, 0.1]
        """
        # 基础权重
        base_weight = 0.05  # 5%基础仓位

        # 因子强度调整
        strength_adjustment = (factor_strength - 0.5) * 0.1

        # 置信度调整
        confidence_adjustment = confidence * 0.05

        # Arena得分调整
        arena_adjustment = validated_factor.arena_score * 0.02

        target = base_weight + strength_adjustment + confidence_adjustment + arena_adjustment

        return max(0.01, min(0.1, target))

    def _calculate_risk_metrics(self, symbol: str, market_data: pd.DataFrame) -> RiskMetrics:
        """计算风险指标

        Args:
            symbol: 股票代码
            market_data: 市场数据

        Returns:
            风险指标
        """
        if symbol not in market_data.columns or len(market_data) < 2:
            return RiskMetrics(volatility=0.2, beta=1.0, var_95=0.05, max_drawdown=0.1, sharpe_ratio=0.0)

        prices = market_data[symbol].dropna()
        if len(prices) < 2:
            return RiskMetrics(volatility=0.2, beta=1.0, var_95=0.05, max_drawdown=0.1, sharpe_ratio=0.0)

        returns = prices.pct_change().dropna()

        # 波动率（年化）
        volatility = returns.std() * np.sqrt(252) if len(returns) > 0 else 0.2

        # VaR 95%
        var_95 = np.percentile(returns, 5) if len(returns) > 0 else -0.05

        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0.1

        # 夏普比率
        mean_return = returns.mean() * 252 if len(returns) > 0 else 0.0
        sharpe = mean_return / volatility if volatility > 0 else 0.0

        return RiskMetrics(
            volatility=float(volatility),
            beta=1.0,  # 简化处理
            var_95=float(abs(var_95)),
            max_drawdown=float(max_drawdown),
            sharpe_ratio=float(sharpe),
        )

    def _estimate_expected_return(self, validated_factor: IntegratedFactor, factor_strength: float) -> float:
        """估计预期收益

        Args:
            validated_factor: 验证因子
            factor_strength: 因子强度

        Returns:
            预期收益率
        """
        # 基于IC估计
        base_return = validated_factor.baseline_ic * 12  # 年化

        # 因子强度调整
        strength_adjustment = (factor_strength - 0.5) * 0.1

        # Arena得分调整
        arena_adjustment = validated_factor.arena_score * 0.05

        return base_return + strength_adjustment + arena_adjustment

    async def _decorrelate_recommendations(
        self, recommendations: List[FactorRecommendation]
    ) -> List[FactorRecommendation]:
        """去相关性处理

        白皮书依据: 第四章 4.2.3 去相关性处理

        Args:
            recommendations: 原始建议列表

        Returns:
            去相关后的建议列表
        """
        if len(recommendations) <= 1:
            return recommendations

        # 按股票分组
        symbol_recommendations: Dict[str, List[FactorRecommendation]] = {}
        for rec in recommendations:
            if rec.symbol not in symbol_recommendations:
                symbol_recommendations[rec.symbol] = []
            symbol_recommendations[rec.symbol].append(rec)

        decorrelated = []

        for symbol, recs in symbol_recommendations.items():  # pylint: disable=unused-variable
            if len(recs) == 1:
                decorrelated.append(recs[0])
                continue

            # 检查因子相关性
            [rec.factor_source for rec in recs]  # pylint: disable=w0104

            # 保留相关性最低的因子建议
            selected_recs = []
            used_factors = set()

            # 按置信度排序
            sorted_recs = sorted(recs, key=lambda x: x.confidence, reverse=True)

            for rec in sorted_recs:
                # 检查与已选因子的相关性
                is_redundant = False
                for used_factor in used_factors:
                    corr = self.factor_correlations.get_correlation(rec.factor_source, used_factor)
                    if abs(corr) > 0.7:  # 高相关性阈值
                        is_redundant = True
                        break

                if not is_redundant:
                    selected_recs.append(rec)
                    used_factors.add(rec.factor_source)

            decorrelated.extend(selected_recs)

        return decorrelated

    async def _resolve_conflicts(self, recommendations: List[FactorRecommendation]) -> List[FactorRecommendation]:
        """解决建议冲突

        白皮书依据: 第四章 4.2.3 冲突解决

        Args:
            recommendations: 建议列表

        Returns:
            解决冲突后的建议列表
        """
        if len(recommendations) <= 1:
            return recommendations

        # 按股票分组
        symbol_recommendations: Dict[str, List[FactorRecommendation]] = {}
        for rec in recommendations:
            if rec.symbol not in symbol_recommendations:
                symbol_recommendations[rec.symbol] = []
            symbol_recommendations[rec.symbol].append(rec)

        resolved = []

        for symbol, recs in symbol_recommendations.items():
            if len(recs) == 1:
                resolved.append(recs[0])
                continue

            # 检查是否有冲突（同时有买入和卖出建议）
            buy_recs = [r for r in recs if r.action == RecommendationAction.BUY]
            sell_recs = [r for r in recs if r.action == RecommendationAction.SELL]

            if buy_recs and sell_recs:
                # 有冲突，使用置信度加权投票
                buy_confidence = sum(r.confidence for r in buy_recs)
                sell_confidence = sum(r.confidence for r in sell_recs)

                if buy_confidence > sell_confidence:
                    # 选择置信度最高的买入建议
                    best_buy = max(buy_recs, key=lambda x: x.confidence)
                    # 调整置信度反映冲突
                    conflict_factor = buy_confidence / (buy_confidence + sell_confidence)
                    best_buy = FactorRecommendation(
                        symbol=best_buy.symbol,
                        action=best_buy.action,
                        target_weight=best_buy.target_weight * conflict_factor,
                        confidence=best_buy.confidence * conflict_factor,
                        factor_source=best_buy.factor_source,
                        factor_value=best_buy.factor_value,
                        factor_rank=best_buy.factor_rank,
                        reasoning=f"{best_buy.reasoning} (冲突解决: 买入信号更强)",
                        risk_metrics=best_buy.risk_metrics,
                        expected_return=best_buy.expected_return,
                    )
                    resolved.append(best_buy)
                else:
                    # 选择置信度最高的卖出建议
                    best_sell = max(sell_recs, key=lambda x: x.confidence)
                    conflict_factor = sell_confidence / (buy_confidence + sell_confidence)
                    best_sell = FactorRecommendation(
                        symbol=best_sell.symbol,
                        action=best_sell.action,
                        target_weight=0.0,
                        confidence=best_sell.confidence * conflict_factor,
                        factor_source=best_sell.factor_source,
                        factor_value=best_sell.factor_value,
                        factor_rank=best_sell.factor_rank,
                        reasoning=f"{best_sell.reasoning} (冲突解决: 卖出信号更强)",
                        risk_metrics=best_sell.risk_metrics,
                        expected_return=0.0,
                    )
                    resolved.append(best_sell)
            else:
                # 无冲突，合并同方向建议
                if buy_recs:
                    # 加权平均买入建议
                    total_confidence = sum(r.confidence for r in buy_recs)
                    avg_weight = sum(r.target_weight * r.confidence for r in buy_recs) / total_confidence
                    avg_expected_return = sum(r.expected_return * r.confidence for r in buy_recs) / total_confidence

                    best_rec = max(buy_recs, key=lambda x: x.confidence)
                    merged = FactorRecommendation(
                        symbol=symbol,
                        action=RecommendationAction.BUY,
                        target_weight=avg_weight,
                        confidence=min(1.0, total_confidence / len(buy_recs)),
                        factor_source=best_rec.factor_source,
                        factor_value=best_rec.factor_value,
                        factor_rank=best_rec.factor_rank,
                        reasoning=f"多因子综合买入建议 ({len(buy_recs)}个因子)",
                        risk_metrics=best_rec.risk_metrics,
                        expected_return=avg_expected_return,
                    )
                    resolved.append(merged)

                if sell_recs:
                    best_rec = max(sell_recs, key=lambda x: x.confidence)
                    total_confidence = sum(r.confidence for r in sell_recs)
                    merged = FactorRecommendation(
                        symbol=symbol,
                        action=RecommendationAction.SELL,
                        target_weight=0.0,
                        confidence=min(1.0, total_confidence / len(sell_recs)),
                        factor_source=best_rec.factor_source,
                        factor_value=best_rec.factor_value,
                        factor_rank=best_rec.factor_rank,
                        reasoning=f"多因子综合卖出建议 ({len(sell_recs)}个因子)",
                        risk_metrics=best_rec.risk_metrics,
                        expected_return=0.0,
                    )
                    resolved.append(merged)

        return resolved

    async def _apply_risk_budgeting(self, recommendations: List[FactorRecommendation]) -> List[FactorRecommendation]:
        """应用风险预算分配

        白皮书依据: 第四章 4.2.3 风险预算分配

        Args:
            recommendations: 建议列表

        Returns:
            风险预算调整后的建议列表
        """
        if not recommendations:
            return recommendations

        # 计算总目标权重
        buy_recs = [r for r in recommendations if r.action == RecommendationAction.BUY]
        total_weight = sum(r.target_weight for r in buy_recs)

        # 如果总权重超过100%，按比例缩减
        if total_weight > 1.0:
            scale_factor = 1.0 / total_weight
            adjusted = []
            for rec in recommendations:
                if rec.action == RecommendationAction.BUY:
                    adjusted_rec = FactorRecommendation(
                        symbol=rec.symbol,
                        action=rec.action,
                        target_weight=rec.target_weight * scale_factor,
                        confidence=rec.confidence,
                        factor_source=rec.factor_source,
                        factor_value=rec.factor_value,
                        factor_rank=rec.factor_rank,
                        reasoning=rec.reasoning,
                        risk_metrics=rec.risk_metrics,
                        expected_return=rec.expected_return,
                    )
                    adjusted.append(adjusted_rec)
                else:
                    adjusted.append(rec)
            return adjusted

        return recommendations

    def update_market_regime(self, regime: MarketRegime) -> None:
        """更新市场状态

        白皮书依据: 第四章 4.2.3 市场状态调整

        Args:
            regime: 新的市场状态
        """
        old_regime = self.current_regime
        self.current_regime = regime

        # 更新所有因子的当前权重
        for factor_id, factor in self.validated_factors.items():
            regime_weight = factor.regime_weights.get(regime, factor.initial_weight)
            self.factor_weights[factor_id] = regime_weight
            factor.current_weight = regime_weight

        logger.info(f"市场状态从 {old_regime.value} 更新为 {regime.value}")

    def update_holdings(self, holdings: Dict[str, float]) -> None:
        """更新当前持仓

        Args:
            holdings: 持仓字典 {symbol: weight}
        """
        self.current_holdings = holdings.copy()

    def update_recommendation_result(
        self, recommendation: FactorRecommendation, realized_return: float, was_successful: bool
    ) -> None:
        """更新建议结果

        白皮书依据: 第四章 4.2.3 建议跟踪

        Args:
            recommendation: 原始建议
            realized_return: 实现收益
            was_successful: 是否成功
        """
        factor_id = recommendation.factor_source

        if factor_id in self.factor_performance:
            # 计算IC（简化版本）
            ic = 0.05 if was_successful else -0.02

            self.factor_performance[factor_id].update_performance(
                ic=ic, realized_return=realized_return, predicted_direction=was_successful
            )

        if factor_id in self.validated_factors:
            factor = self.validated_factors[factor_id]
            factor.total_recommendations += 1
            if was_successful:
                factor.successful_recommendations += 1
            factor.hit_rate = (
                factor.successful_recommendations / factor.total_recommendations
                if factor.total_recommendations > 0
                else 0.0
            )

    def get_factor_attribution(self, recommendations: List[FactorRecommendation]) -> Dict[str, Dict[str, Any]]:
        """获取因子归因

        白皮书依据: 第四章 4.2.3 因子归因

        Args:
            recommendations: 建议列表

        Returns:
            因子归因字典
        """
        attribution: Dict[str, Dict[str, Any]] = {}

        for rec in recommendations:
            factor_id = rec.factor_source

            if factor_id not in attribution:
                factor = self.validated_factors.get(factor_id)
                attribution[factor_id] = {
                    "factor_name": factor.name if factor else factor_id,
                    "arena_score": factor.arena_score if factor else 0.0,
                    "z2h_certified": factor.z2h_certified if factor else False,
                    "current_weight": self.factor_weights.get(factor_id, 0.0),
                    "hit_rate": factor.hit_rate if factor else 0.0,
                    "recommendations": [],
                    "total_confidence": 0.0,
                }

            attribution[factor_id]["recommendations"].append(
                {
                    "symbol": rec.symbol,
                    "action": rec.action.value,
                    "confidence": rec.confidence,
                    "target_weight": rec.target_weight,
                }
            )
            attribution[factor_id]["total_confidence"] += rec.confidence

        return attribution

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        total_factors = len(self.validated_factors)
        z2h_certified = sum(1 for f in self.validated_factors.values() if f.z2h_certified)

        avg_arena_score = (
            np.mean([f.arena_score for f in self.validated_factors.values()]) if self.validated_factors else 0.0
        )

        avg_hit_rate = (
            np.mean([f.hit_rate for f in self.validated_factors.values() if f.total_recommendations > 0])
            if any(f.total_recommendations > 0 for f in self.validated_factors.values())
            else 0.0
        )

        return {
            "total_factors": total_factors,
            "z2h_certified_factors": z2h_certified,
            "avg_arena_score": float(avg_arena_score),
            "avg_hit_rate": float(avg_hit_rate),
            "current_regime": self.current_regime.value,
            "total_recommendations": len(self._recommendation_history),
            "factor_weights": dict(self.factor_weights),
        }
