# pylint: disable=too-many-lines
"""第五章数据模型定义

白皮书依据: 第五章 5.1-5.2 LLM策略深度分析系统
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ProfitSource(Enum):
    """盈利来源类型"""

    TREND = "trend"  # 趋势跟踪
    MEAN_REVERSION = "mean_reversion"  # 均值回归
    ARBITRAGE = "arbitrage"  # 套利
    VOLATILITY = "volatility"  # 波动率
    MOMENTUM = "momentum"  # 动量
    VALUE = "value"  # 价值
    MIXED = "mixed"  # 混合


class MarketScenario(Enum):
    """市场场景"""

    BULL = "bull"  # 牛市
    BEAR = "bear"  # 熊市
    SIDEWAYS = "sideways"  # 震荡市
    HIGH_VOLATILITY = "high_volatility"  # 高波动
    LOW_VOLATILITY = "low_volatility"  # 低波动


class RiskLevel(Enum):
    """风险等级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MainForceType(Enum):
    """主力类型"""

    INSTITUTION = "institution"  # 机构
    HOT_MONEY = "hot_money"  # 游资
    OLD_BANKER = "old_banker"  # 老庄
    MIXED = "mixed"  # 混合


class BehaviorPattern(Enum):
    """行为模式"""

    ACCUMULATING = "accumulating"  # 建仓
    WASHING = "washing"  # 洗盘
    PULLING = "pulling"  # 拉升
    DISTRIBUTING = "distributing"  # 出货
    WAITING = "waiting"  # 观望


class ActionType(Enum):
    """操作建议类型"""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WATCH = "watch"


class PositionSize(Enum):
    """仓位建议"""

    LIGHT = "light"  # 轻仓
    STANDARD = "standard"  # 标准
    HEAVY = "heavy"  # 重仓


class HoldingPeriod(Enum):
    """持有周期"""

    SHORT = "short"  # 短期 (<7天)
    MEDIUM = "medium"  # 中期 (7-60天)
    LONG = "long"  # 长期 (>60天)


class DecayStage(Enum):
    """衰减阶段"""

    EARLY = "early"
    MIDDLE = "middle"
    LATE = "late"
    CRITICAL = "critical"


class DecayTrend(Enum):
    """衰减趋势"""

    STABLE = "stable"
    DECLINING = "declining"
    ACCELERATING_DECLINE = "accelerating_decline"


class StopLossType(Enum):
    """止损类型"""

    FIXED = "fixed"  # 固定比例
    ATR = "atr"  # ATR止损
    TRAILING = "trailing"  # 追踪止损
    VOLATILITY = "volatility"  # 波动率止损


class SNRQuality(Enum):
    """信噪比质量"""

    EXCELLENT = "excellent"  # >3
    GOOD = "good"  # 2-3
    FAIR = "fair"  # 1-2
    POOR = "poor"  # <1


class StressTestGrade(Enum):
    """压力测试评级"""

    A = "A"  # 优秀
    B = "B"  # 良好
    C = "C"  # 中等
    D = "D"  # 较差
    F = "F"  # 很差


class SentimentCategory(Enum):
    """情绪分类"""

    EXTREME_FEAR = "extreme_fear"  # 极度恐慌
    FEAR = "fear"  # 恐慌
    NEUTRAL = "neutral"  # 中性
    GREED = "greed"  # 贪婪
    EXTREME_GREED = "extreme_greed"  # 极度贪婪


class SentimentTrend(Enum):
    """情绪趋势"""

    IMPROVING = "improving"
    STABLE = "stable"
    DETERIORATING = "deteriorating"


@dataclass
class StrategyEssenceReport:
    """策略本质分析报告

    白皮书依据: 第五章 5.2.1 策略本质分析
    """

    strategy_id: str
    profit_source: ProfitSource
    market_assumptions: List[str]
    applicable_scenarios: List[MarketScenario]
    sustainability_score: float  # 0-1
    core_logic: str
    advantages: List[str]
    limitations: List[str]
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "profit_source": self.profit_source.value,
            "market_assumptions": self.market_assumptions,
            "applicable_scenarios": [s.value for s in self.applicable_scenarios],
            "sustainability_score": self.sustainability_score,
            "core_logic": self.core_logic,
            "advantages": self.advantages,
            "limitations": self.limitations,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class RiskAssessmentReport:
    """风险评估报告

    白皮书依据: 第五章 5.2.2 风险识别与评估
    """

    strategy_id: str
    systematic_risks: List[Dict[str, Any]]  # 系统性风险
    specific_risks: List[Dict[str, Any]]  # 特异性风险
    risk_matrix: Dict[str, RiskLevel]  # 风险名 -> 严重程度
    mitigation_plan: List[str]  # 缓解方案
    overall_risk_level: RiskLevel
    risk_score: float  # 0-100
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "systematic_risks": self.systematic_risks,
            "specific_risks": self.specific_risks,
            "risk_matrix": {k: v.value for k, v in self.risk_matrix.items()},
            "mitigation_plan": self.mitigation_plan,
            "overall_risk_level": self.overall_risk_level.value,
            "risk_score": self.risk_score,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class OverfittingReport:
    """过拟合检测报告

    白皮书依据: 第五章 5.2.3 过度拟合检测
    """

    strategy_id: str
    future_functions: List[str]  # 未来函数列表
    parameter_ratio: float  # 参数数量/样本数量
    is_oos_gap: float  # 样本内外差异
    overfitting_probability: float  # 0-100%
    evidence: List[str]  # 证据列表
    suggestions: List[str]  # 修复建议
    is_overfitted: bool
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "future_functions": self.future_functions,
            "parameter_ratio": self.parameter_ratio,
            "is_oos_gap": self.is_oos_gap,
            "overfitting_probability": self.overfitting_probability,
            "evidence": self.evidence,
            "suggestions": self.suggestions,
            "is_overfitted": self.is_overfitted,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class FeatureAnalysisReport:
    """特征工程分析报告

    白皮书依据: 第五章 5.2.4 特征工程分析
    """

    strategy_id: str
    feature_importance: Dict[str, float]  # 特征重要性排名
    correlation_matrix: Dict[str, Dict[str, float]]  # 相关性矩阵
    multicollinearity_issues: List[str]  # 共线性问题
    stability_scores: Dict[str, float]  # 稳定性评分
    recommendations: List[str]  # 新特征推荐
    ic_values: Dict[str, float]  # IC值
    ir_values: Dict[str, float]  # IR值
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "feature_importance": self.feature_importance,
            "correlation_matrix": self.correlation_matrix,
            "multicollinearity_issues": self.multicollinearity_issues,
            "stability_scores": self.stability_scores,
            "recommendations": self.recommendations,
            "ic_values": self.ic_values,
            "ir_values": self.ir_values,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class MacroAnalysisReport:
    """大盘判断与宏观分析报告

    白皮书依据: 第五章 5.2.5 大盘判断与宏观分析
    """

    market_stage: MarketScenario
    confidence: float  # 0-1
    technical_analysis: Dict[str, Any]
    sentiment_analysis: Dict[str, Any]
    macro_indicators: Dict[str, Any]
    policy_impact: Dict[str, Any]
    capital_flow: Dict[str, Any]
    sector_rotation: Dict[str, Any]
    position_recommendation: str  # 满仓/半仓/空仓
    strategy_type_recommendation: List[str]
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "market_stage": self.market_stage.value,
            "confidence": self.confidence,
            "technical_analysis": self.technical_analysis,
            "sentiment_analysis": self.sentiment_analysis,
            "macro_indicators": self.macro_indicators,
            "policy_impact": self.policy_impact,
            "capital_flow": self.capital_flow,
            "sector_rotation": self.sector_rotation,
            "position_recommendation": self.position_recommendation,
            "strategy_type_recommendation": self.strategy_type_recommendation,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class MicrostructureReport:
    """市场微观结构分析报告

    白皮书依据: 第五章 5.2.6 市场微观结构分析
    """

    analysis_date: str
    limit_up_count: int  # 涨停家数
    limit_down_count: int  # 跌停家数
    seal_strength: Dict[str, float]  # 封单强度
    blow_up_rate: float  # 炸板率
    money_making_effect: float  # 赚钱效应指数 0-1
    distribution: Dict[str, Any]  # 分布（题材/行业/市值）
    hot_spots: List[str]  # 热点列表
    sentiment_strength: str  # 强/中/弱
    next_day_prediction: str  # 延续/反转
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "analysis_date": self.analysis_date,
            "limit_up_count": self.limit_up_count,
            "limit_down_count": self.limit_down_count,
            "seal_strength": self.seal_strength,
            "blow_up_rate": self.blow_up_rate,
            "money_making_effect": self.money_making_effect,
            "distribution": self.distribution,
            "hot_spots": self.hot_spots,
            "sentiment_strength": self.sentiment_strength,
            "next_day_prediction": self.next_day_prediction,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class SectorAnalysisReport:
    """行业与板块分析报告

    白皮书依据: 第五章 5.2.7 行业与板块分析
    """

    sector_fundamentals: Dict[str, Dict[str, Any]]  # 行业基本面
    policy_support: Dict[str, float]  # 政策支持评分
    capital_flow: Dict[str, float]  # 资金流向
    relative_strength: Dict[str, float]  # 相对强度
    rotation_prediction: List[str]  # 轮动预测
    sector_matrix: Dict[str, Dict[str, Any]]  # 行业矩阵
    top_sectors: List[str]  # 强势板块
    weak_sectors: List[str]  # 弱势板块
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "sector_fundamentals": self.sector_fundamentals,
            "policy_support": self.policy_support,
            "capital_flow": self.capital_flow,
            "relative_strength": self.relative_strength,
            "rotation_prediction": self.rotation_prediction,
            "sector_matrix": self.sector_matrix,
            "top_sectors": self.top_sectors,
            "weak_sectors": self.weak_sectors,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class SmartMoneyDeepAnalysis:
    """主力资金深度分析

    白皮书依据: 第五章 5.2.8 主力资金深度分析
    """

    symbol: str
    cost_basis: float  # 主力建仓成本
    cost_range: tuple  # 成本区间 (min, max)
    estimated_holdings: float  # 估算持股量
    holdings_pct: float  # 占流通盘比例
    profit_loss: float  # 主力浮盈浮亏
    profit_loss_pct: float  # 主力盈利比例
    main_force_type: MainForceType  # 主力类型
    behavior_pattern: BehaviorPattern  # 行为模式
    next_action_prediction: str  # 下一步预测
    follow_risk: RiskLevel  # 跟随风险
    confidence: float  # 分析置信度 0-1
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "cost_basis": self.cost_basis,
            "cost_range": self.cost_range,
            "estimated_holdings": self.estimated_holdings,
            "holdings_pct": self.holdings_pct,
            "profit_loss": self.profit_loss,
            "profit_loss_pct": self.profit_loss_pct,
            "main_force_type": self.main_force_type.value,
            "behavior_pattern": self.behavior_pattern.value,
            "next_action_prediction": self.next_action_prediction,
            "follow_risk": self.follow_risk.value,
            "confidence": self.confidence,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class StockRecommendation:
    """个股结论性建议

    白皮书依据: 第五章 5.2.9 个股结论性建议
    """

    symbol: str
    action: ActionType  # 操作建议
    confidence: float  # 置信度 0-1
    reasons: List[str]  # 支持原因
    risks: List[str]  # 风险提示
    entry_price: float  # 建议买入价
    stop_loss: float  # 止损价
    target_price: float  # 目标价
    position_size: PositionSize  # 仓位建议
    holding_period: HoldingPeriod  # 持有周期
    overall_score: Dict[str, float]  # 综合评分
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "action": self.action.value,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "risks": self.risks,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "target_price": self.target_price,
            "position_size": self.position_size.value,
            "holding_period": self.holding_period.value,
            "overall_score": self.overall_score,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class TradingCostAnalysis:
    """交易成本分析

    白皮书依据: 第五章 5.2.10 交易成本分析
    """

    strategy_id: str
    total_trades: int
    commission_cost: float  # 佣金成本
    stamp_duty: float  # 印花税
    slippage_cost: float  # 滑点成本
    impact_cost: float  # 冲击成本
    total_cost: float  # 总成本
    cost_ratio: float  # 成本占收益比
    cost_efficiency: float  # 成本效率评分 0-1
    cost_level: str  # low/medium/high/very_high
    optimization_suggestions: List[str]
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "total_trades": self.total_trades,
            "commission_cost": self.commission_cost,
            "stamp_duty": self.stamp_duty,
            "slippage_cost": self.slippage_cost,
            "impact_cost": self.impact_cost,
            "total_cost": self.total_cost,
            "cost_ratio": self.cost_ratio,
            "cost_efficiency": self.cost_efficiency,
            "cost_level": self.cost_level,
            "optimization_suggestions": self.optimization_suggestions,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class DecayAnalysis:
    """策略衰减分析

    白皮书依据: 第五章 5.2.11 策略衰减分析
    """

    strategy_id: str
    return_decay_rate: float  # 收益率衰减率 %/年
    sharpe_decay_rate: float  # 夏普比率衰减率 %/年
    win_rate_decay_rate: float  # 胜率衰减率 %/年
    decay_trend: DecayTrend
    estimated_lifetime: int  # 预计生命周期（天）
    decay_stage: DecayStage
    update_urgency: str  # low/medium/high/critical
    decay_factors: List[str]
    update_recommendations: List[str]
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "return_decay_rate": self.return_decay_rate,
            "sharpe_decay_rate": self.sharpe_decay_rate,
            "win_rate_decay_rate": self.win_rate_decay_rate,
            "decay_trend": self.decay_trend.value,
            "estimated_lifetime": self.estimated_lifetime,
            "decay_stage": self.decay_stage.value,
            "update_urgency": self.update_urgency,
            "decay_factors": self.decay_factors,
            "update_recommendations": self.update_recommendations,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class StopLossAnalysis:
    """止损逻辑优化分析

    白皮书依据: 第五章 5.2.12 止损逻辑优化
    """

    strategy_id: str
    current_stop_loss: float
    optimal_stop_loss: float
    optimal_stop_loss_type: StopLossType
    stop_loss_effectiveness: float  # 0-1
    stopped_trades: int
    avg_stopped_loss: float
    alternative_strategies: List[Dict[str, Any]]
    recommendations: List[str]
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "current_stop_loss": self.current_stop_loss,
            "optimal_stop_loss": self.optimal_stop_loss,
            "optimal_stop_loss_type": self.optimal_stop_loss_type.value,
            "stop_loss_effectiveness": self.stop_loss_effectiveness,
            "stopped_trades": self.stopped_trades,
            "avg_stopped_loss": self.avg_stopped_loss,
            "alternative_strategies": self.alternative_strategies,
            "recommendations": self.recommendations,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class SlippageAnalysis:  # pylint: disable=too-many-instance-attributes
    """滑点分析

    白皮书依据: 第五章 5.2.13 滑点分析
    """

    strategy_id: str
    avg_slippage: float  # 平均滑点 (bp)
    median_slippage: float  # 中位数滑点 (bp)
    max_slippage: float  # 最大滑点 (bp)
    slippage_distribution: Dict[str, int]  # 滑点分布
    percentiles: Dict[str, float]  # 百分位数
    total_slippage_cost: float
    slippage_cost_ratio: float
    time_of_day_analysis: Dict[str, float]
    worst_time_slots: List[str]
    best_time_slots: List[str]
    market_cap_impact: Dict[str, float]
    liquidity_impact: Dict[str, float]
    optimization_suggestions: List[str]
    potential_reduction: float  # bp
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "avg_slippage": self.avg_slippage,
            "median_slippage": self.median_slippage,
            "max_slippage": self.max_slippage,
            "slippage_distribution": self.slippage_distribution,
            "percentiles": self.percentiles,
            "total_slippage_cost": self.total_slippage_cost,
            "slippage_cost_ratio": self.slippage_cost_ratio,
            "time_of_day_analysis": self.time_of_day_analysis,
            "worst_time_slots": self.worst_time_slots,
            "best_time_slots": self.best_time_slots,
            "market_cap_impact": self.market_cap_impact,
            "liquidity_impact": self.liquidity_impact,
            "optimization_suggestions": self.optimization_suggestions,
            "potential_reduction": self.potential_reduction,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class NonstationarityAnalysis:  # pylint: disable=too-many-instance-attributes
    """非平稳性处理分析

    白皮书依据: 第五章 5.2.14 非平稳性处理
    """

    strategy_id: str
    adf_statistic: float
    adf_p_value: float
    is_stationary: bool
    stationarity_confidence: float  # 0-1
    regime_count: int
    current_regime: str
    regime_changes: List[Dict[str, Any]]
    regime_characteristics: Dict[str, Dict[str, Any]]
    parameter_stability: float  # 0-1
    unstable_parameters: List[str]
    stability_trend: str  # stable/improving/deteriorating
    market_changes: List[str]
    adaptation_urgency: str  # low/medium/high/critical
    recommendations: List[str]
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "adf_statistic": self.adf_statistic,
            "adf_p_value": self.adf_p_value,
            "is_stationary": self.is_stationary,
            "stationarity_confidence": self.stationarity_confidence,
            "regime_count": self.regime_count,
            "current_regime": self.current_regime,
            "regime_changes": self.regime_changes,
            "regime_characteristics": self.regime_characteristics,
            "parameter_stability": self.parameter_stability,
            "unstable_parameters": self.unstable_parameters,
            "stability_trend": self.stability_trend,
            "market_changes": self.market_changes,
            "adaptation_urgency": self.adaptation_urgency,
            "recommendations": self.recommendations,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class SignalNoiseAnalysis:
    """信噪比分析

    白皮书依据: 第五章 5.2.15 信噪比分析
    """

    strategy_id: str
    signal_strength: float  # 0-1
    signal_consistency: float  # 0-1
    signal_clarity: float  # 0-1
    noise_level: float  # 0-1
    signal_to_noise_ratio: float
    snr_quality: SNRQuality
    overall_quality: float  # 0-1
    temporal_stability: float  # 0-1
    noise_sources: List[str]
    improvement_suggestions: List[str]
    expected_improvement: float  # 0-1
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "signal_strength": self.signal_strength,
            "signal_consistency": self.signal_consistency,
            "signal_clarity": self.signal_clarity,
            "noise_level": self.noise_level,
            "signal_to_noise_ratio": self.signal_to_noise_ratio,
            "snr_quality": self.snr_quality.value,
            "overall_quality": self.overall_quality,
            "temporal_stability": self.temporal_stability,
            "noise_sources": self.noise_sources,
            "improvement_suggestions": self.improvement_suggestions,
            "expected_improvement": self.expected_improvement,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class CapacityAnalysis:
    """资金容量评估

    白皮书依据: 第五章 5.2.16 资金容量评估
    """

    strategy_id: str
    max_capacity: float  # 最大资金容量
    capacity_confidence: float  # 0-1
    current_capital: float
    capacity_utilization: float  # 0-1
    decay_curve: List[Dict[str, float]]  # 资金-收益关系
    decay_rate: float  # 0-1
    optimal_capacity: float
    scalability_score: float  # 0-1
    primary_bottleneck: str
    bottlenecks: List[str]
    expansion_recommendations: List[str]
    expansion_potential: float
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "max_capacity": self.max_capacity,
            "capacity_confidence": self.capacity_confidence,
            "current_capital": self.current_capital,
            "capacity_utilization": self.capacity_utilization,
            "decay_curve": self.decay_curve,
            "decay_rate": self.decay_rate,
            "optimal_capacity": self.optimal_capacity,
            "scalability_score": self.scalability_score,
            "primary_bottleneck": self.primary_bottleneck,
            "bottlenecks": self.bottlenecks,
            "expansion_recommendations": self.expansion_recommendations,
            "expansion_potential": self.expansion_potential,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class StressTestAnalysis:  # pylint: disable=too-many-instance-attributes
    """压力测试分析

    白皮书依据: 第五章 5.2.17 压力测试
    """

    strategy_id: str
    historical_events: List[Dict[str, Any]]
    worst_event: str
    worst_event_loss: float
    scenario_tests: List[Dict[str, Any]]
    worst_scenario: str
    worst_scenario_loss: float
    risk_tolerance: float  # 0-1
    survival_probability: float  # 0-1
    max_tolerable_loss: float
    stress_test_grade: StressTestGrade
    vulnerabilities: List[str]
    critical_vulnerabilities: List[str]
    contingency_plans: List[str]
    recommended_actions: List[str]
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "historical_events": self.historical_events,
            "worst_event": self.worst_event,
            "worst_event_loss": self.worst_event_loss,
            "scenario_tests": self.scenario_tests,
            "worst_scenario": self.worst_scenario,
            "worst_scenario_loss": self.worst_scenario_loss,
            "risk_tolerance": self.risk_tolerance,
            "survival_probability": self.survival_probability,
            "max_tolerable_loss": self.max_tolerable_loss,
            "stress_test_grade": self.stress_test_grade.value,
            "vulnerabilities": self.vulnerabilities,
            "critical_vulnerabilities": self.critical_vulnerabilities,
            "contingency_plans": self.contingency_plans,
            "recommended_actions": self.recommended_actions,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class TradeReviewAnalysis:  # pylint: disable=too-many-instance-attributes
    """交易复盘分析

    白皮书依据: 第五章 5.2.18 交易复盘
    """

    strategy_id: str
    total_trades: int
    avg_quality_score: float  # 0-1
    excellent_trades: List[Dict[str, Any]]
    excellent_trade_count: int
    excellent_trade_characteristics: List[str]
    poor_trades: List[Dict[str, Any]]
    poor_trade_count: int
    common_mistakes: List[str]
    discipline_score: float  # 0-1
    discipline_violations: List[str]
    execution_quality: float  # 0-1
    execution_issues: List[str]
    timing_analysis: Dict[str, Any]
    timing_score: float  # 0-1
    improvement_suggestions: List[str]
    priority_improvements: List[str]
    key_learnings: List[str]
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "total_trades": self.total_trades,
            "avg_quality_score": self.avg_quality_score,
            "excellent_trades": self.excellent_trades,
            "excellent_trade_count": self.excellent_trade_count,
            "excellent_trade_characteristics": self.excellent_trade_characteristics,
            "poor_trades": self.poor_trades,
            "poor_trade_count": self.poor_trade_count,
            "common_mistakes": self.common_mistakes,
            "discipline_score": self.discipline_score,
            "discipline_violations": self.discipline_violations,
            "execution_quality": self.execution_quality,
            "execution_issues": self.execution_issues,
            "timing_analysis": self.timing_analysis,
            "timing_score": self.timing_score,
            "improvement_suggestions": self.improvement_suggestions,
            "priority_improvements": self.priority_improvements,
            "key_learnings": self.key_learnings,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class SentimentAnalysis:
    """市场情绪分析

    白皮书依据: 第五章 5.2.19 市场情绪
    """

    analysis_date: str
    overall_sentiment: float  # 0-1
    sentiment_category: SentimentCategory
    sentiment_strength: float  # 0-1
    sentiment_trend: SentimentTrend
    extreme_sentiment: bool
    extreme_sentiment_type: Optional[str]
    sentiment_indicators: Dict[str, float]
    fear_greed_index: int  # 0-100
    investment_advice: List[str]
    risk_warnings: List[str]
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "analysis_date": self.analysis_date,
            "overall_sentiment": self.overall_sentiment,
            "sentiment_category": self.sentiment_category.value,
            "sentiment_strength": self.sentiment_strength,
            "sentiment_trend": self.sentiment_trend.value,
            "extreme_sentiment": self.extreme_sentiment,
            "extreme_sentiment_type": self.extreme_sentiment_type,
            "sentiment_indicators": self.sentiment_indicators,
            "fear_greed_index": self.fear_greed_index,
            "investment_advice": self.investment_advice,
            "risk_warnings": self.risk_warnings,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class RetailSentimentAnalysis:
    """散户情绪分析

    白皮书依据: 第五章 5.2.20 散户情绪
    """

    analysis_date: str
    retail_position_ratio: float  # 0-1
    retail_activity: float  # 0-1
    retail_sentiment: float  # 0-1
    sentiment_category: SentimentCategory
    behavior_characteristics: List[str]
    chase_kill_index: float  # 追涨杀跌指数 0-1
    herd_behavior_index: float  # 羊群效应指数 0-1
    contrarian_signal: str
    contrarian_strength: float  # 0-1
    common_mistakes: List[str]
    professional_advice: List[str]
    risk_warnings: List[str]
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "analysis_date": self.analysis_date,
            "retail_position_ratio": self.retail_position_ratio,
            "retail_activity": self.retail_activity,
            "retail_sentiment": self.retail_sentiment,
            "sentiment_category": self.sentiment_category.value,
            "behavior_characteristics": self.behavior_characteristics,
            "chase_kill_index": self.chase_kill_index,
            "herd_behavior_index": self.herd_behavior_index,
            "contrarian_signal": self.contrarian_signal,
            "contrarian_strength": self.contrarian_strength,
            "common_mistakes": self.common_mistakes,
            "professional_advice": self.professional_advice,
            "risk_warnings": self.risk_warnings,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class CorrelationAnalysis:
    """相关性分析

    白皮书依据: 第五章 5.2.21 相关性分析
    """

    strategy_count: int
    correlation_matrix: Dict[str, Dict[str, float]]
    high_correlation_pairs: List[tuple]  # >0.7
    low_correlation_pairs: List[tuple]  # <0.3
    avg_correlation: float
    diversification_score: float  # 0-1
    portfolio_recommendations: List[str]
    optimal_weights: Dict[str, float]
    risk_reduction: float  # 0-1
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_count": self.strategy_count,
            "correlation_matrix": self.correlation_matrix,
            "high_correlation_pairs": [list(p) for p in self.high_correlation_pairs],
            "low_correlation_pairs": [list(p) for p in self.low_correlation_pairs],
            "avg_correlation": self.avg_correlation,
            "diversification_score": self.diversification_score,
            "portfolio_recommendations": self.portfolio_recommendations,
            "optimal_weights": self.optimal_weights,
            "risk_reduction": self.risk_reduction,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class PositionSizingAnalysis:
    """仓位管理分析

    白皮书依据: 第五章 5.2.22 仓位管理
    """

    strategy_id: str
    kelly_fraction: float
    adjusted_kelly: float  # 半Kelly
    fixed_fraction: float
    volatility_adjusted: float
    risk_budget_position: float
    recommended_position: float  # 0-1
    max_position: float  # 0-1
    min_position: float  # 0-1
    dynamic_adjustment_rules: List[str]
    strategy_comparison: Dict[str, Dict[str, float]]
    risk_assessment: Dict[str, Any]
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "kelly_fraction": self.kelly_fraction,
            "adjusted_kelly": self.adjusted_kelly,
            "fixed_fraction": self.fixed_fraction,
            "volatility_adjusted": self.volatility_adjusted,
            "risk_budget_position": self.risk_budget_position,
            "recommended_position": self.recommended_position,
            "max_position": self.max_position,
            "min_position": self.min_position,
            "dynamic_adjustment_rules": self.dynamic_adjustment_rules,
            "strategy_comparison": self.strategy_comparison,
            "risk_assessment": self.risk_assessment,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class PortfolioOptimizationAnalysis:  # pylint: disable=too-many-instance-attributes
    """投资组合优化分析

    白皮书依据: 第五章 5.2.14 投资组合优化分析
    """

    portfolio_id: str
    efficient_frontier: List[Dict[str, float]]  # 有效前沿曲线数据
    optimal_portfolio: Dict[str, Any]  # 最优组合配置
    optimal_weights: Dict[str, float]  # 最优权重字典
    expected_return: float  # 预期收益率
    expected_risk: float  # 预期风险（标准差）
    sharpe_ratio: float  # 夏普比率
    max_sharpe_portfolio: Dict[str, Any]  # 最大夏普比率组合
    min_variance_portfolio: Dict[str, Any]  # 最小方差组合
    risk_parity_portfolio: Dict[str, Any]  # 风险平价组合
    equal_weight_portfolio: Dict[str, Any]  # 等权重组合
    portfolio_comparison: Dict[str, Dict[str, float]]  # 各组合对比
    rebalancing_frequency: str  # 建议再平衡频率
    rebalancing_threshold: float  # 再平衡阈值
    diversification_benefit: float  # 分散化收益
    concentration_risk: float  # 集中度风险
    optimization_method: str  # 优化方法
    constraints: Dict[str, Any]  # 约束条件
    sensitivity_analysis: Dict[str, Any]  # 敏感性分析
    recommendations: List[str]  # 优化建议列表
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "portfolio_id": self.portfolio_id,
            "efficient_frontier": self.efficient_frontier,
            "optimal_portfolio": self.optimal_portfolio,
            "optimal_weights": self.optimal_weights,
            "expected_return": self.expected_return,
            "expected_risk": self.expected_risk,
            "sharpe_ratio": self.sharpe_ratio,
            "max_sharpe_portfolio": self.max_sharpe_portfolio,
            "min_variance_portfolio": self.min_variance_portfolio,
            "risk_parity_portfolio": self.risk_parity_portfolio,
            "equal_weight_portfolio": self.equal_weight_portfolio,
            "portfolio_comparison": self.portfolio_comparison,
            "rebalancing_frequency": self.rebalancing_frequency,
            "rebalancing_threshold": self.rebalancing_threshold,
            "diversification_benefit": self.diversification_benefit,
            "concentration_risk": self.concentration_risk,
            "optimization_method": self.optimization_method,
            "constraints": self.constraints,
            "sensitivity_analysis": self.sensitivity_analysis,
            "recommendations": self.recommendations,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class RegimeAdaptationAnalysis:  # pylint: disable=too-many-instance-attributes
    """市场状态适应分析

    白皮书依据: 第五章 5.2.15 市场状态适应分析
    """

    strategy_id: str
    regime_classification: str  # 市场状态分类
    regime_detection_method: str  # 检测方法
    current_regime: str  # 当前市场状态
    regime_probability: Dict[str, float]  # 各状态概率分布
    regime_duration: int  # 当前状态持续时间（天）
    regime_transition_matrix: Dict[str, Dict[str, float]]  # 状态转移矩阵
    strategy_performance_by_regime: Dict[str, Dict[str, float]]  # 各状态下策略表现
    best_regime: str  # 最佳适应状态
    worst_regime: str  # 最差适应状态
    adaptation_score: float  # 适应性评分（0-1）
    regime_sensitivity: float  # 状态敏感度
    adaptation_recommendations: List[str]  # 适应性建议
    parameter_adjustment_rules: Dict[str, Any]  # 参数调整规则
    dynamic_allocation_strategy: Dict[str, Any]  # 动态配置策略
    regime_forecast: str  # 未来状态预测
    forecast_confidence: float  # 预测置信度
    early_warning_signals: List[str]  # 状态切换预警信号
    hedging_recommendations: List[str]  # 对冲建议
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "regime_classification": self.regime_classification,
            "regime_detection_method": self.regime_detection_method,
            "current_regime": self.current_regime,
            "regime_probability": self.regime_probability,
            "regime_duration": self.regime_duration,
            "regime_transition_matrix": self.regime_transition_matrix,
            "strategy_performance_by_regime": self.strategy_performance_by_regime,
            "best_regime": self.best_regime,
            "worst_regime": self.worst_regime,
            "adaptation_score": self.adaptation_score,
            "regime_sensitivity": self.regime_sensitivity,
            "adaptation_recommendations": self.adaptation_recommendations,
            "parameter_adjustment_rules": self.parameter_adjustment_rules,
            "dynamic_allocation_strategy": self.dynamic_allocation_strategy,
            "regime_forecast": self.regime_forecast,
            "forecast_confidence": self.forecast_confidence,
            "early_warning_signals": self.early_warning_signals,
            "hedging_recommendations": self.hedging_recommendations,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class FactorExposureAnalysis:  # pylint: disable=too-many-instance-attributes
    """因子暴露分析

    白皮书依据: 第五章 5.2.16 因子暴露分析
    """

    strategy_id: str
    factor_exposures: Dict[str, float]  # 因子暴露度字典
    market_beta: float  # 市场Beta
    size_exposure: float  # 规模因子暴露
    value_exposure: float  # 价值因子暴露
    momentum_exposure: float  # 动量因子暴露
    quality_exposure: float  # 质量因子暴露
    volatility_exposure: float  # 波动率因子暴露
    liquidity_exposure: float  # 流动性因子暴露
    sector_exposures: Dict[str, float]  # 行业暴露度
    style_exposures: Dict[str, float]  # 风格暴露度
    factor_contribution: Dict[str, float]  # 因子收益贡献
    alpha: float  # 超额收益（Alpha）
    r_squared: float  # R²（解释度）
    tracking_error: float  # 跟踪误差
    information_ratio: float  # 信息比率
    factor_timing: float  # 因子择时能力
    factor_selection: float  # 因子选择能力
    risk_decomposition: Dict[str, float]  # 风险分解
    systematic_risk: float  # 系统性风险
    idiosyncratic_risk: float  # 特异性风险
    concentration_analysis: Dict[str, Any]  # 因子集中度分析
    factor_correlation: Dict[str, Dict[str, float]]  # 因子相关性矩阵
    exposure_stability: float  # 暴露度稳定性
    exposure_drift: float  # 暴露度漂移
    rebalancing_needs: List[str]  # 再平衡需求
    hedging_recommendations: List[str]  # 对冲建议
    factor_rotation_signals: List[str]  # 因子轮动信号
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "factor_exposures": self.factor_exposures,
            "market_beta": self.market_beta,
            "size_exposure": self.size_exposure,
            "value_exposure": self.value_exposure,
            "momentum_exposure": self.momentum_exposure,
            "quality_exposure": self.quality_exposure,
            "volatility_exposure": self.volatility_exposure,
            "liquidity_exposure": self.liquidity_exposure,
            "sector_exposures": self.sector_exposures,
            "style_exposures": self.style_exposures,
            "factor_contribution": self.factor_contribution,
            "alpha": self.alpha,
            "r_squared": self.r_squared,
            "tracking_error": self.tracking_error,
            "information_ratio": self.information_ratio,
            "factor_timing": self.factor_timing,
            "factor_selection": self.factor_selection,
            "risk_decomposition": self.risk_decomposition,
            "systematic_risk": self.systematic_risk,
            "idiosyncratic_risk": self.idiosyncratic_risk,
            "concentration_analysis": self.concentration_analysis,
            "factor_correlation": self.factor_correlation,
            "exposure_stability": self.exposure_stability,
            "exposure_drift": self.exposure_drift,
            "rebalancing_needs": self.rebalancing_needs,
            "hedging_recommendations": self.hedging_recommendations,
            "factor_rotation_signals": self.factor_rotation_signals,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class TransactionCostAnalysis:  # pylint: disable=too-many-instance-attributes
    """交易成本深度分析

    白皮书依据: 第五章 5.2.17 交易成本深度分析
    """

    strategy_id: str
    total_trades: int  # 总交易次数
    commission_cost: float  # 佣金成本
    stamp_duty: float  # 印花税
    slippage_cost: float  # 滑点成本
    impact_cost: float  # 市场冲击成本
    opportunity_cost: float  # 机会成本
    timing_cost: float  # 时机成本
    total_cost: float  # 总成本
    cost_ratio: float  # 成本占收益比
    cost_efficiency: float  # 成本效率评分（0-1）
    cost_level: str  # 成本水平
    cost_breakdown_by_type: Dict[str, float]  # 按类型分解
    cost_breakdown_by_time: Dict[str, float]  # 按时间分解
    cost_breakdown_by_symbol: Dict[str, float]  # 按股票分解
    cost_breakdown_by_size: Dict[str, float]  # 按交易规模分解
    high_cost_trades: List[Dict[str, Any]]  # 高成本交易列表
    cost_outliers: List[Dict[str, Any]]  # 成本异常值
    execution_quality_score: float  # 执行质量评分（0-1）
    vwap_deviation: float  # VWAP偏离度
    implementation_shortfall: float  # 实施缺口
    arrival_price_analysis: Dict[str, Any]  # 到达价格分析
    optimal_execution_strategy: str  # 最优执行策略
    execution_algorithm_recommendation: str  # 执行算法推荐
    order_splitting_strategy: Dict[str, Any]  # 订单拆分策略
    timing_optimization: List[str]  # 时机优化建议
    liquidity_seeking_strategy: Dict[str, Any]  # 流动性寻求策略
    dark_pool_opportunities: List[str]  # 暗池交易机会
    cost_reduction_potential: float  # 成本降低潜力
    optimization_suggestions: List[str]  # 优化建议列表
    expected_savings: float  # 预期节省
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "total_trades": self.total_trades,
            "commission_cost": self.commission_cost,
            "stamp_duty": self.stamp_duty,
            "slippage_cost": self.slippage_cost,
            "impact_cost": self.impact_cost,
            "opportunity_cost": self.opportunity_cost,
            "timing_cost": self.timing_cost,
            "total_cost": self.total_cost,
            "cost_ratio": self.cost_ratio,
            "cost_efficiency": self.cost_efficiency,
            "cost_level": self.cost_level,
            "cost_breakdown_by_type": self.cost_breakdown_by_type,
            "cost_breakdown_by_time": self.cost_breakdown_by_time,
            "cost_breakdown_by_symbol": self.cost_breakdown_by_symbol,
            "cost_breakdown_by_size": self.cost_breakdown_by_size,
            "high_cost_trades": self.high_cost_trades,
            "cost_outliers": self.cost_outliers,
            "execution_quality_score": self.execution_quality_score,
            "vwap_deviation": self.vwap_deviation,
            "implementation_shortfall": self.implementation_shortfall,
            "arrival_price_analysis": self.arrival_price_analysis,
            "optimal_execution_strategy": self.optimal_execution_strategy,
            "execution_algorithm_recommendation": self.execution_algorithm_recommendation,
            "order_splitting_strategy": self.order_splitting_strategy,
            "timing_optimization": self.timing_optimization,
            "liquidity_seeking_strategy": self.liquidity_seeking_strategy,
            "dark_pool_opportunities": self.dark_pool_opportunities,
            "cost_reduction_potential": self.cost_reduction_potential,
            "optimization_suggestions": self.optimization_suggestions,
            "expected_savings": self.expected_savings,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


@dataclass
class ComprehensiveAnalysisReport:  # pylint: disable=too-many-instance-attributes
    """综合分析报告

    白皮书依据: 第五章 5.1 系统定位与架构
    """

    strategy_id: str
    overall_score: float  # 0-100
    essence_report: Optional[StrategyEssenceReport] = None
    risk_report: Optional[RiskAssessmentReport] = None
    overfitting_report: Optional[OverfittingReport] = None
    feature_report: Optional[FeatureAnalysisReport] = None
    macro_report: Optional[MacroAnalysisReport] = None
    microstructure_report: Optional[MicrostructureReport] = None
    sector_report: Optional[SectorAnalysisReport] = None
    smart_money_report: Optional[SmartMoneyDeepAnalysis] = None
    recommendation: Optional[StockRecommendation] = None
    trading_cost_report: Optional[TradingCostAnalysis] = None
    decay_report: Optional[DecayAnalysis] = None
    stop_loss_report: Optional[StopLossAnalysis] = None
    slippage_report: Optional[SlippageAnalysis] = None
    nonstationarity_report: Optional[NonstationarityAnalysis] = None
    signal_noise_report: Optional[SignalNoiseAnalysis] = None
    capacity_report: Optional[CapacityAnalysis] = None
    stress_test_report: Optional[StressTestAnalysis] = None
    trade_review_report: Optional[TradeReviewAnalysis] = None
    sentiment_report: Optional[SentimentAnalysis] = None
    retail_sentiment_report: Optional[RetailSentimentAnalysis] = None
    correlation_report: Optional[CorrelationAnalysis] = None
    position_sizing_report: Optional[PositionSizingAnalysis] = None
    portfolio_optimization_report: Optional[PortfolioOptimizationAnalysis] = None
    regime_adaptation_report: Optional[RegimeAdaptationAnalysis] = None
    factor_exposure_report: Optional[FactorExposureAnalysis] = None
    transaction_cost_report: Optional[TransactionCostAnalysis] = None
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:  # pylint: disable=too-many-branches
        """转换为字典"""
        result = {
            "strategy_id": self.strategy_id,
            "overall_score": self.overall_score,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }

        if self.essence_report:
            result["essence_report"] = self.essence_report.to_dict()
        if self.risk_report:
            result["risk_report"] = self.risk_report.to_dict()
        if self.overfitting_report:
            result["overfitting_report"] = self.overfitting_report.to_dict()
        if self.feature_report:
            result["feature_report"] = self.feature_report.to_dict()
        if self.macro_report:
            result["macro_report"] = self.macro_report.to_dict()
        if self.microstructure_report:
            result["microstructure_report"] = self.microstructure_report.to_dict()
        if self.sector_report:
            result["sector_report"] = self.sector_report.to_dict()
        if self.smart_money_report:
            result["smart_money_report"] = self.smart_money_report.to_dict()
        if self.recommendation:
            result["recommendation"] = self.recommendation.to_dict()
        if self.trading_cost_report:
            result["trading_cost_report"] = self.trading_cost_report.to_dict()
        if self.decay_report:
            result["decay_report"] = self.decay_report.to_dict()
        if self.stop_loss_report:
            result["stop_loss_report"] = self.stop_loss_report.to_dict()
        if self.slippage_report:
            result["slippage_report"] = self.slippage_report.to_dict()
        if self.nonstationarity_report:
            result["nonstationarity_report"] = self.nonstationarity_report.to_dict()
        if self.signal_noise_report:
            result["signal_noise_report"] = self.signal_noise_report.to_dict()
        if self.capacity_report:
            result["capacity_report"] = self.capacity_report.to_dict()
        if self.stress_test_report:
            result["stress_test_report"] = self.stress_test_report.to_dict()
        if self.trade_review_report:
            result["trade_review_report"] = self.trade_review_report.to_dict()
        if self.sentiment_report:
            result["sentiment_report"] = self.sentiment_report.to_dict()
        if self.retail_sentiment_report:
            result["retail_sentiment_report"] = self.retail_sentiment_report.to_dict()
        if self.correlation_report:
            result["correlation_report"] = self.correlation_report.to_dict()
        if self.position_sizing_report:
            result["position_sizing_report"] = self.position_sizing_report.to_dict()
        if self.portfolio_optimization_report:
            result["portfolio_optimization_report"] = self.portfolio_optimization_report.to_dict()
        if self.regime_adaptation_report:
            result["regime_adaptation_report"] = self.regime_adaptation_report.to_dict()
        if self.factor_exposure_report:
            result["factor_exposure_report"] = self.factor_exposure_report.to_dict()
        if self.transaction_cost_report:
            result["transaction_cost_report"] = self.transaction_cost_report.to_dict()

        return result


# ============================================================================
# 可视化系统数据模型
# 白皮书依据: 第五章 5.4 可视化系统
# ============================================================================


@dataclass
class KLineData:
    """单根K线数据

    白皮书依据: 第五章 5.4.4 K线图可视化系统
    """

    date: datetime
    open: float  # 开盘价
    close: float  # 收盘价
    high: float  # 最高价
    low: float  # 最低价
    volume: float  # 成交量
    amount: float  # 成交额
    change_pct: float  # 涨跌幅
    color: str  # 'red' (涨) or 'green' (跌) or 'white' (平)


@dataclass
class MainForceCostLine:
    """主力成本线数据

    白皮书依据: 第五章 5.4.4 K线图可视化系统
    """

    cost_basis: float  # 主力建仓成本
    cost_range_upper: float  # 成本区间上限（成本+10%）
    cost_range_lower: float  # 成本区间下限（成本-10%）
    confidence: float  # 成本估算置信度（0-1）
    last_update: datetime  # 最后更新时间


@dataclass
class TradingSignal:
    """买卖点信号

    白皮书依据: 第五章 5.4.4 K线图可视化系统
    """

    date: datetime
    price: float  # 信号价格
    signal_type: str  # 'buy' or 'sell'
    source: str  # 信号来源（'technical', 'smart_money', 'sector_rotation', 'risk_warning'）
    confidence: float  # 信号置信度（0-1）
    reason: str  # 信号原因描述
    marker_color: str  # 标记颜色（'green' for buy, 'red' for sell）
    marker_symbol: str  # 标记符号（'↑' for buy, '↓' for sell）


@dataclass
class VolumeData:
    """成交量数据

    白皮书依据: 第五章 5.4.4 K线图可视化系统
    """

    date: datetime
    volume: float  # 成交量
    color: str  # 'red' (上涨日) or 'green' (下跌日)
    main_force_flow: Optional[float] = None  # 主力资金净流入（可选）


@dataclass
class IndicatorData:
    """技术指标数据（通用）

    白皮书依据: 第五章 5.4.4 K线图可视化系统
    """

    indicator_name: str  # 指标名称（'MACD', 'KDJ', 'RSI', 'BOLL'）
    data: Dict[str, List[float]]  # 指标数据


@dataclass
class KLineChartData:
    """K线图数据

    白皮书依据: 第五章 5.4.4 K线图可视化系统
    """

    symbol: str
    name: str
    period: str  # 'daily', 'weekly', 'monthly', '5min', '15min', '60min'

    # K线数据
    klines: List[KLineData]

    # 均线数据
    ma_lines: Dict[int, List[float]]  # {5: [ma5数据], 10: [ma10数据], ...}

    # 主力成本线
    main_force_cost_line: Optional[MainForceCostLine]

    # 买卖点标注
    buy_signals: List[TradingSignal]
    sell_signals: List[TradingSignal]

    # 成交量数据
    volumes: List[VolumeData]

    # 技术指标数据（可选）
    indicators: Dict[str, IndicatorData]  # {'MACD': data, 'KDJ': data, ...}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "period": self.period,
            "klines": [
                {
                    "date": k.date.isoformat(),
                    "open": k.open,
                    "close": k.close,
                    "high": k.high,
                    "low": k.low,
                    "volume": k.volume,
                    "amount": k.amount,
                    "change_pct": k.change_pct,
                    "color": k.color,
                }
                for k in self.klines
            ],
            "ma_lines": self.ma_lines,
            "main_force_cost_line": (
                {
                    "cost_basis": self.main_force_cost_line.cost_basis,
                    "cost_range_upper": self.main_force_cost_line.cost_range_upper,
                    "cost_range_lower": self.main_force_cost_line.cost_range_lower,
                    "confidence": self.main_force_cost_line.confidence,
                    "last_update": self.main_force_cost_line.last_update.isoformat(),
                }
                if self.main_force_cost_line
                else None
            ),
            "buy_signals": [
                {
                    "date": s.date.isoformat(),
                    "price": s.price,
                    "signal_type": s.signal_type,
                    "source": s.source,
                    "confidence": s.confidence,
                    "reason": s.reason,
                    "marker_color": s.marker_color,
                    "marker_symbol": s.marker_symbol,
                }
                for s in self.buy_signals
            ],
            "sell_signals": [
                {
                    "date": s.date.isoformat(),
                    "price": s.price,
                    "signal_type": s.signal_type,
                    "source": s.source,
                    "confidence": s.confidence,
                    "reason": s.reason,
                    "marker_color": s.marker_color,
                    "marker_symbol": s.marker_symbol,
                }
                for s in self.sell_signals
            ],
            "volumes": [
                {"date": v.date.isoformat(), "volume": v.volume, "color": v.color, "main_force_flow": v.main_force_flow}
                for v in self.volumes
            ],
            "indicators": {
                name: {"indicator_name": ind.indicator_name, "data": ind.data} for name, ind in self.indicators.items()
            },
        }


@dataclass
class StockFlowData:
    """个股资金流向数据

    白皮书依据: 第五章 5.4.3 板块资金异动监控仪表盘
    """

    symbol: str
    name: str
    net_inflow: float  # 净流入金额（万元）
    price_change_pct: float  # 涨跌幅
    current_price: float  # 当前价格


@dataclass
class SectorFlowData:
    """板块资金流向数据

    白皮书依据: 第五章 5.4.3 板块资金异动监控仪表盘
    """

    sector_name: str
    net_inflow: float  # 净流入金额（亿元）
    inflow_amount: float  # 流入金额
    outflow_amount: float  # 流出金额
    price_change_pct: float  # 涨跌幅
    leading_stocks: List[StockFlowData]  # 领涨/领跌股（TOP3）
    stock_count: int  # 板块内股票数量
    rising_stock_count: int  # 上涨股票数量
    falling_stock_count: int  # 下跌股票数量


@dataclass
class SectorRotationAnalysis:
    """板块轮动分析

    白皮书依据: 第五章 5.4.3 板块资金异动监控仪表盘
    """

    current_stage: str  # 当前阶段（成长股主导/价值股主导/周期股主导）
    dominant_sectors: List[str]  # 当前主导板块
    rotation_prediction: str  # 轮动预测（下一阶段预测）
    confidence: float  # 置信度（0-1）
    allocation_suggestion: Dict[str, float]  # 配置建议（板块 -> 仓位比例）


@dataclass
class SectorFlowTrend:
    """板块资金流向趋势

    白皮书依据: 第五章 5.4.3 板块资金异动监控仪表盘
    """

    sector_name: str
    period_days: int  # 统计周期（5/20/60天）
    cumulative_net_inflow: float  # 累计净流入
    trend_direction: str  # 趋势方向（'inflow', 'outflow', 'neutral'）
    trend_strength: float  # 趋势强度（0-1）
    daily_flows: List[float]  # 每日净流入数据


@dataclass
class SectorCapitalFlowMonitoring:
    """板块资金流向监控数据

    白皮书依据: 第五章 5.4.3 板块资金异动监控仪表盘
    """

    timestamp: datetime
    period: str  # 'daily', 'weekly', 'monthly'

    # 热点板块（资金流入TOP10）
    top_inflow_sectors: List[SectorFlowData]

    # 资金流出板块（资金流出TOP10）
    top_outflow_sectors: List[SectorFlowData]

    # 板块轮动分析
    rotation_analysis: SectorRotationAnalysis

    # 板块资金流向趋势
    flow_trends: Dict[str, SectorFlowTrend]

    # 配置建议
    allocation_recommendation: Dict[str, float]  # 板块 -> 建议仓位比例

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "period": self.period,
            "top_inflow_sectors": [
                {
                    "sector_name": s.sector_name,
                    "net_inflow": s.net_inflow,
                    "inflow_amount": s.inflow_amount,
                    "outflow_amount": s.outflow_amount,
                    "price_change_pct": s.price_change_pct,
                    "leading_stocks": [
                        {
                            "symbol": stock.symbol,
                            "name": stock.name,
                            "net_inflow": stock.net_inflow,
                            "price_change_pct": stock.price_change_pct,
                            "current_price": stock.current_price,
                        }
                        for stock in s.leading_stocks
                    ],
                    "stock_count": s.stock_count,
                    "rising_stock_count": s.rising_stock_count,
                    "falling_stock_count": s.falling_stock_count,
                }
                for s in self.top_inflow_sectors
            ],
            "top_outflow_sectors": [
                {
                    "sector_name": s.sector_name,
                    "net_inflow": s.net_inflow,
                    "inflow_amount": s.inflow_amount,
                    "outflow_amount": s.outflow_amount,
                    "price_change_pct": s.price_change_pct,
                    "leading_stocks": [
                        {
                            "symbol": stock.symbol,
                            "name": stock.name,
                            "net_inflow": stock.net_inflow,
                            "price_change_pct": stock.price_change_pct,
                            "current_price": stock.current_price,
                        }
                        for stock in s.leading_stocks
                    ],
                    "stock_count": s.stock_count,
                    "rising_stock_count": s.rising_stock_count,
                    "falling_stock_count": s.falling_stock_count,
                }
                for s in self.top_outflow_sectors
            ],
            "rotation_analysis": {
                "current_stage": self.rotation_analysis.current_stage,
                "dominant_sectors": self.rotation_analysis.dominant_sectors,
                "rotation_prediction": self.rotation_analysis.rotation_prediction,
                "confidence": self.rotation_analysis.confidence,
                "allocation_suggestion": self.rotation_analysis.allocation_suggestion,
            },
            "flow_trends": {
                name: {
                    "sector_name": trend.sector_name,
                    "period_days": trend.period_days,
                    "cumulative_net_inflow": trend.cumulative_net_inflow,
                    "trend_direction": trend.trend_direction,
                    "trend_strength": trend.trend_strength,
                    "daily_flows": trend.daily_flows,
                }
                for name, trend in self.flow_trends.items()
            },
            "allocation_recommendation": self.allocation_recommendation,
        }
