# pylint: disable=too-many-lines
"""可视化系统数据模型

白皮书依据: 第五章 5.4 可视化系统

本模块定义了可视化系统所需的所有数据模型，包括：
- StrategyDashboardData: 策略仪表盘数据
- StockDashboardData: 个股仪表盘数据
- StockRecommendation: 个股建议
- SmartMoneyAnalysis: 主力资金深度分析
- 各种图表数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Tuple


class RecommendationAction(Enum):
    """操作建议枚举

    白皮书依据: 第五章 5.4.2 个股分析仪表盘
    """

    BUY = "买入"
    SELL = "卖出"
    HOLD = "持有"
    WATCH = "观望"


class SmartMoneyType(Enum):
    """主力类型枚举

    白皮书依据: 第五章 5.4.2 个股分析仪表盘
    """

    INSTITUTION = "机构"
    HOT_MONEY = "游资"
    FOREIGN = "外资"
    MIXED = "混合"


class BehaviorPattern(Enum):
    """行为模式枚举

    白皮书依据: 第五章 5.4.2 个股分析仪表盘
    """

    ACCUMULATING = "建仓中"
    WASHING = "洗筹"
    PULLING_UP = "拉升"
    DISTRIBUTING = "出货"
    WAITING = "观望"


class RiskLevel(Enum):
    """风险等级枚举

    白皮书依据: 第五章 5.4.2 个股分析仪表盘
    """

    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    VERY_HIGH = "极高"


class OverfittingRiskLevel(Enum):
    """过拟合风险等级枚举

    白皮书依据: 第五章 5.4.1 策略分析中心仪表盘
    """

    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"


class MarketAdaptation(Enum):
    """市场适配度枚举

    白皮书依据: 第五章 5.4.1 策略分析中心仪表盘
    """

    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class HoldingPeriod(Enum):
    """持有周期枚举

    白皮书依据: 第五章 5.4.2 个股分析仪表盘
    """

    SHORT = "短期（1-7天）"
    MEDIUM = "中期（30-60天）"
    LONG = "长期（60天以上）"


class PositionSuggestion(Enum):
    """仓位建议枚举

    白皮书依据: 第五章 5.4.2 个股分析仪表盘
    """

    LIGHT = "轻仓（1-3%）"
    STANDARD = "标准仓位（5-8%）"
    HEAVY = "重仓（10-15%）"


@dataclass
class StockRecommendation:
    """个股建议数据模型

    白皮书依据: 第五章 5.4.2 个股分析仪表盘

    Attributes:
        action: 操作建议（买入/卖出/持有/观望）
        confidence: 置信度
        current_price: 当前价格
        target_price: 目标价
        stop_loss_price: 止损价
        buy_price_range: 建议买入价区间
        position_suggestion: 仓位建议
        holding_period: 持有周期
        support_reasons: 支持原因列表
        risk_warnings: 风险提示列表
    """

    action: RecommendationAction
    confidence: float
    current_price: float
    target_price: float
    stop_loss_price: float
    buy_price_range: Tuple[float, float]
    position_suggestion: PositionSuggestion
    holding_period: HoldingPeriod
    support_reasons: List[str]
    risk_warnings: List[str]

    def __post_init__(self) -> None:
        """验证个股建议数据"""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"置信度必须在[0, 1]范围内，当前: {self.confidence}")
        if self.current_price <= 0:
            raise ValueError(f"当前价格必须大于0，当前: {self.current_price}")
        if self.target_price <= 0:
            raise ValueError(f"目标价必须大于0，当前: {self.target_price}")
        if self.stop_loss_price <= 0:
            raise ValueError(f"止损价必须大于0，当前: {self.stop_loss_price}")
        if self.buy_price_range[0] > self.buy_price_range[1]:
            raise ValueError("买入价区间下限不能大于上限")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "action": self.action.value,
            "confidence": self.confidence,
            "current_price": self.current_price,
            "target_price": self.target_price,
            "stop_loss_price": self.stop_loss_price,
            "buy_price_range": list(self.buy_price_range),
            "position_suggestion": self.position_suggestion.value,
            "holding_period": self.holding_period.value,
            "support_reasons": self.support_reasons,
            "risk_warnings": self.risk_warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StockRecommendation":
        """从字典创建个股建议对象"""
        return cls(
            action=RecommendationAction(data["action"]),
            confidence=data["confidence"],
            current_price=data["current_price"],
            target_price=data["target_price"],
            stop_loss_price=data["stop_loss_price"],
            buy_price_range=tuple(data["buy_price_range"]),
            position_suggestion=PositionSuggestion(data["position_suggestion"]),
            holding_period=HoldingPeriod(data["holding_period"]),
            support_reasons=data.get("support_reasons", []),
            risk_warnings=data.get("risk_warnings", []),
        )


@dataclass
class SmartMoneyAnalysis:
    """主力资金深度分析数据模型

    白皮书依据: 第五章 5.4.2 个股分析仪表盘

    Attributes:
        smart_money_type: 主力类型（机构/游资/外资）
        position_cost: 建仓成本
        holding_ratio: 持股比例
        current_profit: 当前盈利
        behavior_pattern: 行为模式（建仓中/洗筹/拉升/出货）
        risk_level: 风险等级
    """

    smart_money_type: SmartMoneyType
    position_cost: float
    holding_ratio: float
    current_profit: float
    behavior_pattern: BehaviorPattern
    risk_level: RiskLevel

    def __post_init__(self) -> None:
        """验证主力资金分析数据"""
        if self.position_cost <= 0:
            raise ValueError(f"建仓成本必须大于0，当前: {self.position_cost}")
        if not 0 <= self.holding_ratio <= 1:
            raise ValueError(f"持股比例必须在[0, 1]范围内，当前: {self.holding_ratio}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "smart_money_type": self.smart_money_type.value,
            "position_cost": self.position_cost,
            "holding_ratio": self.holding_ratio,
            "current_profit": self.current_profit,
            "behavior_pattern": self.behavior_pattern.value,
            "risk_level": self.risk_level.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SmartMoneyAnalysis":
        """从字典创建主力资金分析对象"""
        return cls(
            smart_money_type=SmartMoneyType(data["smart_money_type"]),
            position_cost=data["position_cost"],
            holding_ratio=data["holding_ratio"],
            current_profit=data["current_profit"],
            behavior_pattern=BehaviorPattern(data["behavior_pattern"]),
            risk_level=RiskLevel(data["risk_level"]),
        )


@dataclass
class StockDashboardData:
    """个股仪表盘数据模型

    白皮书依据: 第五章 5.4.2 个股分析仪表盘

    Attributes:
        symbol: 股票代码
        name: 股票名称
        recommendation: 结论性建议
        smart_money_analysis: 主力资金深度分析
        updated_at: 更新时间
    """

    symbol: str
    name: str
    recommendation: StockRecommendation
    smart_money_analysis: SmartMoneyAnalysis
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """验证个股仪表盘数据"""
        if not self.symbol:
            raise ValueError("股票代码不能为空")
        if not self.name:
            raise ValueError("股票名称不能为空")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "recommendation": self.recommendation.to_dict(),
            "smart_money_analysis": self.smart_money_analysis.to_dict(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StockDashboardData":
        """从字典创建个股仪表盘数据对象"""
        return cls(
            symbol=data["symbol"],
            name=data["name"],
            recommendation=StockRecommendation.from_dict(data["recommendation"]),
            smart_money_analysis=SmartMoneyAnalysis.from_dict(data["smart_money_analysis"]),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class StrategyDashboardData:
    """策略仪表盘数据模型

    白皮书依据: 第五章 5.4.1 策略分析中心仪表盘

    Attributes:
        strategy_id: 策略ID
        strategy_name: 策略名称
        overall_score: 综合评分
        overfitting_risk: 过拟合风险等级
        market_adaptation: 市场适配度
        essence_radar_data: 策略本质雷达图数据
        risk_matrix_data: 风险矩阵热力图数据
        feature_importance_data: 特征重要性排名数据
        market_adaptation_matrix: 市场适配性矩阵数据
        evolution_visualization_data: 进化过程可视化数据
        updated_at: 更新时间
    """

    strategy_id: str
    strategy_name: str
    overall_score: float
    overfitting_risk: OverfittingRiskLevel
    market_adaptation: MarketAdaptation
    essence_radar_data: Dict[str, float]
    risk_matrix_data: List[List[float]]
    feature_importance_data: List[Tuple[str, float]]
    market_adaptation_matrix: Dict[str, Dict[str, float]]
    evolution_visualization_data: Dict[str, Any]
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """验证策略仪表盘数据"""
        if not self.strategy_id:
            raise ValueError("策略ID不能为空")
        if not self.strategy_name:
            raise ValueError("策略名称不能为空")
        if not 0 <= self.overall_score <= 100:
            raise ValueError(f"综合评分必须在[0, 100]范围内，当前: {self.overall_score}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "overall_score": self.overall_score,
            "overfitting_risk": self.overfitting_risk.value,
            "market_adaptation": self.market_adaptation.value,
            "essence_radar_data": self.essence_radar_data,
            "risk_matrix_data": self.risk_matrix_data,
            "feature_importance_data": self.feature_importance_data,
            "market_adaptation_matrix": self.market_adaptation_matrix,
            "evolution_visualization_data": self.evolution_visualization_data,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyDashboardData":
        """从字典创建策略仪表盘数据对象"""
        return cls(
            strategy_id=data["strategy_id"],
            strategy_name=data["strategy_name"],
            overall_score=data["overall_score"],
            overfitting_risk=OverfittingRiskLevel(data["overfitting_risk"]),
            market_adaptation=MarketAdaptation(data["market_adaptation"]),
            essence_radar_data=data["essence_radar_data"],
            risk_matrix_data=data["risk_matrix_data"],
            feature_importance_data=[tuple(f) for f in data["feature_importance_data"]],
            market_adaptation_matrix=data["market_adaptation_matrix"],
            evolution_visualization_data=data["evolution_visualization_data"],
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


# ===== 图表数据模型 =====


@dataclass
class OverfittingData:
    """过拟合数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表2

    Attributes:
        in_sample_sharpe: 样本内夏普比率
        out_sample_sharpe: 样本外夏普比率
        parameter_sensitivity: 参数敏感度
        complexity_score: 复杂度评分
        risk_level: 风险等级
    """

    in_sample_sharpe: float
    out_sample_sharpe: float
    parameter_sensitivity: float
    complexity_score: float
    risk_level: OverfittingRiskLevel

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "in_sample_sharpe": self.in_sample_sharpe,
            "out_sample_sharpe": self.out_sample_sharpe,
            "parameter_sensitivity": self.parameter_sensitivity,
            "complexity_score": self.complexity_score,
            "risk_level": self.risk_level.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OverfittingData":
        """从字典创建过拟合数据对象"""
        return cls(
            in_sample_sharpe=data["in_sample_sharpe"],
            out_sample_sharpe=data["out_sample_sharpe"],
            parameter_sensitivity=data["parameter_sensitivity"],
            complexity_score=data["complexity_score"],
            risk_level=OverfittingRiskLevel(data["risk_level"]),
        )


@dataclass
class NonstationarityData:
    """非平稳性数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表5

    Attributes:
        adf_statistic: ADF统计量
        p_value: P值
        rolling_mean: 滚动均值列表
        rolling_std: 滚动标准差列表
        timestamps: 时间戳列表
    """

    adf_statistic: float
    p_value: float
    rolling_mean: List[float]
    rolling_std: List[float]
    timestamps: List[datetime]

    def __post_init__(self) -> None:
        """验证非平稳性数据"""
        if len(self.rolling_mean) != len(self.timestamps):
            raise ValueError("滚动均值和时间戳长度必须一致")
        if len(self.rolling_std) != len(self.timestamps):
            raise ValueError("滚动标准差和时间戳长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "adf_statistic": self.adf_statistic,
            "p_value": self.p_value,
            "rolling_mean": self.rolling_mean,
            "rolling_std": self.rolling_std,
            "timestamps": [t.isoformat() for t in self.timestamps],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NonstationarityData":
        """从字典创建非平稳性数据对象"""
        return cls(
            adf_statistic=data["adf_statistic"],
            p_value=data["p_value"],
            rolling_mean=data["rolling_mean"],
            rolling_std=data["rolling_std"],
            timestamps=[datetime.fromisoformat(t) for t in data["timestamps"]],
        )


@dataclass
class SignalNoiseData:
    """信噪比数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表6

    Attributes:
        snr_values: 信噪比值列表
        timestamps: 时间戳列表
        trend: 趋势（上升/下降/平稳）
    """

    snr_values: List[float]
    timestamps: List[datetime]
    trend: str

    def __post_init__(self) -> None:
        """验证信噪比数据"""
        if len(self.snr_values) != len(self.timestamps):
            raise ValueError("信噪比值和时间戳长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "snr_values": self.snr_values,
            "timestamps": [t.isoformat() for t in self.timestamps],
            "trend": self.trend,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignalNoiseData":
        """从字典创建信噪比数据对象"""
        return cls(
            snr_values=data["snr_values"],
            timestamps=[datetime.fromisoformat(t) for t in data["timestamps"]],
            trend=data["trend"],
        )


@dataclass
class CapacityData:
    """资金容量数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表7

    Attributes:
        capacity_levels: 资金容量级别列表
        impact_costs: 冲击成本列表
        optimal_capacity: 最优资金容量
    """

    capacity_levels: List[float]
    impact_costs: List[float]
    optimal_capacity: float

    def __post_init__(self) -> None:
        """验证资金容量数据"""
        if len(self.capacity_levels) != len(self.impact_costs):
            raise ValueError("资金容量级别和冲击成本长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "capacity_levels": self.capacity_levels,
            "impact_costs": self.impact_costs,
            "optimal_capacity": self.optimal_capacity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapacityData":
        """从字典创建资金容量数据对象"""
        return cls(
            capacity_levels=data["capacity_levels"],
            impact_costs=data["impact_costs"],
            optimal_capacity=data["optimal_capacity"],
        )


@dataclass
class StopLossData:
    """止损数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表9

    Attributes:
        strategies: 止损策略列表
        effectiveness: 有效性列表
        avg_loss_reduction: 平均损失减少列表
    """

    strategies: List[str]
    effectiveness: List[float]
    avg_loss_reduction: List[float]

    def __post_init__(self) -> None:
        """验证止损数据"""
        if len(self.strategies) != len(self.effectiveness):
            raise ValueError("止损策略和有效性长度必须一致")
        if len(self.strategies) != len(self.avg_loss_reduction):
            raise ValueError("止损策略和平均损失减少长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "strategies": self.strategies,
            "effectiveness": self.effectiveness,
            "avg_loss_reduction": self.avg_loss_reduction,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StopLossData":
        """从字典创建止损数据对象"""
        return cls(
            strategies=data["strategies"],
            effectiveness=data["effectiveness"],
            avg_loss_reduction=data["avg_loss_reduction"],
        )


@dataclass
class TradeRecord:
    """交易记录数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表11

    Attributes:
        trade_id: 交易ID
        symbol: 股票代码
        direction: 交易方向（买入/卖出）
        price: 成交价格
        quantity: 成交数量
        pnl: 盈亏
        timestamp: 时间戳
    """

    trade_id: str
    symbol: str
    direction: str
    price: float
    quantity: int
    pnl: float
    timestamp: datetime

    def __post_init__(self) -> None:
        """验证交易记录数据"""
        if not self.trade_id:
            raise ValueError("交易ID不能为空")
        if not self.symbol:
            raise ValueError("股票代码不能为空")
        if self.price <= 0:
            raise ValueError(f"成交价格必须大于0，当前: {self.price}")
        if self.quantity <= 0:
            raise ValueError(f"成交数量必须大于0，当前: {self.quantity}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "price": self.price,
            "quantity": self.quantity,
            "pnl": self.pnl,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TradeRecord":
        """从字典创建交易记录对象"""
        return cls(
            trade_id=data["trade_id"],
            symbol=data["symbol"],
            direction=data["direction"],
            price=data["price"],
            quantity=data["quantity"],
            pnl=data["pnl"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class SentimentData:
    """情绪数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表12

    Attributes:
        timestamps: 时间戳列表
        sentiment_scores: 情绪得分列表
        market_returns: 市场收益率列表
    """

    timestamps: List[datetime]
    sentiment_scores: List[float]
    market_returns: List[float]

    def __post_init__(self) -> None:
        """验证情绪数据"""
        if len(self.timestamps) != len(self.sentiment_scores):
            raise ValueError("时间戳和情绪得分长度必须一致")
        if len(self.timestamps) != len(self.market_returns):
            raise ValueError("时间戳和市场收益率长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "timestamps": [t.isoformat() for t in self.timestamps],
            "sentiment_scores": self.sentiment_scores,
            "market_returns": self.market_returns,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SentimentData":
        """从字典创建情绪数据对象"""
        return cls(
            timestamps=[datetime.fromisoformat(t) for t in data["timestamps"]],
            sentiment_scores=data["sentiment_scores"],
            market_returns=data["market_returns"],
        )


@dataclass
class SmartRetailData:
    """主力散户数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表13

    Attributes:
        smart_money_sentiment: 主力情绪字典
        retail_sentiment: 散户情绪字典
        divergence_score: 分歧度得分
    """

    smart_money_sentiment: Dict[str, float]
    retail_sentiment: Dict[str, float]
    divergence_score: float

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "smart_money_sentiment": self.smart_money_sentiment,
            "retail_sentiment": self.retail_sentiment,
            "divergence_score": self.divergence_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SmartRetailData":
        """从字典创建主力散户数据对象"""
        return cls(
            smart_money_sentiment=data["smart_money_sentiment"],
            retail_sentiment=data["retail_sentiment"],
            divergence_score=data["divergence_score"],
        )


@dataclass
class MarketTechnicalData:
    """大盘技术面数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表14

    Attributes:
        timestamps: 时间戳列表
        prices: 价格列表
        volumes: 成交量列表
        ma5: 5日均线列表
        ma10: 10日均线列表
        ma20: 20日均线列表
        macd: MACD列表
        rsi: RSI列表
    """

    timestamps: List[datetime]
    prices: List[float]
    volumes: List[float]
    ma5: List[float]
    ma10: List[float]
    ma20: List[float]
    macd: List[float]
    rsi: List[float]

    def __post_init__(self) -> None:
        """验证大盘技术面数据"""
        n = len(self.timestamps)
        if len(self.prices) != n:
            raise ValueError("价格和时间戳长度必须一致")
        if len(self.volumes) != n:
            raise ValueError("成交量和时间戳长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "timestamps": [t.isoformat() for t in self.timestamps],
            "prices": self.prices,
            "volumes": self.volumes,
            "ma5": self.ma5,
            "ma10": self.ma10,
            "ma20": self.ma20,
            "macd": self.macd,
            "rsi": self.rsi,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketTechnicalData":
        """从字典创建大盘技术面数据对象"""
        return cls(
            timestamps=[datetime.fromisoformat(t) for t in data["timestamps"]],
            prices=data["prices"],
            volumes=data["volumes"],
            ma5=data["ma5"],
            ma10=data["ma10"],
            ma20=data["ma20"],
            macd=data["macd"],
            rsi=data["rsi"],
        )


@dataclass
class LimitUpData:
    """涨停板数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表15

    Attributes:
        date: 日期
        sectors: 板块列表
        limit_up_counts: 涨停数量列表
        continuous_limit_up: 连板数量列表
    """

    date: datetime
    sectors: List[str]
    limit_up_counts: List[int]
    continuous_limit_up: List[int]

    def __post_init__(self) -> None:
        """验证涨停板数据"""
        if len(self.sectors) != len(self.limit_up_counts):
            raise ValueError("板块和涨停数量长度必须一致")
        if len(self.sectors) != len(self.continuous_limit_up):
            raise ValueError("板块和连板数量长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "date": self.date.isoformat(),
            "sectors": self.sectors,
            "limit_up_counts": self.limit_up_counts,
            "continuous_limit_up": self.continuous_limit_up,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LimitUpData":
        """从字典创建涨停板数据对象"""
        return cls(
            date=datetime.fromisoformat(data["date"]),
            sectors=data["sectors"],
            limit_up_counts=data["limit_up_counts"],
            continuous_limit_up=data["continuous_limit_up"],
        )


@dataclass
class SectorStrengthData:
    """行业强弱数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表16

    Attributes:
        sectors: 行业列表
        strength_scores: 强弱得分列表
        momentum_scores: 动量得分列表
        volume_ratios: 成交量比率列表
    """

    sectors: List[str]
    strength_scores: List[float]
    momentum_scores: List[float]
    volume_ratios: List[float]

    def __post_init__(self) -> None:
        """验证行业强弱数据"""
        n = len(self.sectors)
        if len(self.strength_scores) != n:
            raise ValueError("行业和强弱得分长度必须一致")
        if len(self.momentum_scores) != n:
            raise ValueError("行业和动量得分长度必须一致")
        if len(self.volume_ratios) != n:
            raise ValueError("行业和成交量比率长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "sectors": self.sectors,
            "strength_scores": self.strength_scores,
            "momentum_scores": self.momentum_scores,
            "volume_ratios": self.volume_ratios,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SectorStrengthData":
        """从字典创建行业强弱数据对象"""
        return cls(
            sectors=data["sectors"],
            strength_scores=data["strength_scores"],
            momentum_scores=data["momentum_scores"],
            volume_ratios=data["volume_ratios"],
        )


@dataclass
class SectorRotationData:
    """板块轮动数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表17

    Attributes:
        timestamps: 时间戳列表
        sector_rankings: 板块排名字典 {时间戳: {板块: 排名}}
        rotation_pattern: 轮动模式描述
    """

    timestamps: List[datetime]
    sector_rankings: Dict[str, Dict[str, int]]
    rotation_pattern: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "timestamps": [t.isoformat() for t in self.timestamps],
            "sector_rankings": self.sector_rankings,
            "rotation_pattern": self.rotation_pattern,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SectorRotationData":
        """从字典创建板块轮动数据对象"""
        return cls(
            timestamps=[datetime.fromisoformat(t) for t in data["timestamps"]],
            sector_rankings=data["sector_rankings"],
            rotation_pattern=data["rotation_pattern"],
        )


@dataclass
class DrawdownData:
    """回撤数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表18

    Attributes:
        timestamps: 时间戳列表
        equity_curve: 权益曲线列表
        drawdown_curve: 回撤曲线列表
        max_drawdown: 最大回撤
        max_drawdown_duration: 最大回撤持续时间（天）
    """

    timestamps: List[datetime]
    equity_curve: List[float]
    drawdown_curve: List[float]
    max_drawdown: float
    max_drawdown_duration: int

    def __post_init__(self) -> None:
        """验证回撤数据"""
        n = len(self.timestamps)
        if len(self.equity_curve) != n:
            raise ValueError("权益曲线和时间戳长度必须一致")
        if len(self.drawdown_curve) != n:
            raise ValueError("回撤曲线和时间戳长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "timestamps": [t.isoformat() for t in self.timestamps],
            "equity_curve": self.equity_curve,
            "drawdown_curve": self.drawdown_curve,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_duration": self.max_drawdown_duration,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DrawdownData":
        """从字典创建回撤数据对象"""
        return cls(
            timestamps=[datetime.fromisoformat(t) for t in data["timestamps"]],
            equity_curve=data["equity_curve"],
            drawdown_curve=data["drawdown_curve"],
            max_drawdown=data["max_drawdown"],
            max_drawdown_duration=data["max_drawdown_duration"],
        )


@dataclass
class EfficientFrontierData:
    """有效前沿数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表20

    Attributes:
        returns: 收益率列表
        risks: 风险列表
        sharpe_ratios: 夏普比率列表
        optimal_portfolio: 最优组合索引
    """

    returns: List[float]
    risks: List[float]
    sharpe_ratios: List[float]
    optimal_portfolio: int

    def __post_init__(self) -> None:
        """验证有效前沿数据"""
        n = len(self.returns)
        if len(self.risks) != n:
            raise ValueError("收益率和风险长度必须一致")
        if len(self.sharpe_ratios) != n:
            raise ValueError("收益率和夏普比率长度必须一致")
        if not 0 <= self.optimal_portfolio < n:
            raise ValueError(f"最优组合索引必须在[0, {n-1}]范围内")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "returns": self.returns,
            "risks": self.risks,
            "sharpe_ratios": self.sharpe_ratios,
            "optimal_portfolio": self.optimal_portfolio,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EfficientFrontierData":
        """从字典创建有效前沿数据对象"""
        return cls(
            returns=data["returns"],
            risks=data["risks"],
            sharpe_ratios=data["sharpe_ratios"],
            optimal_portfolio=data["optimal_portfolio"],
        )


@dataclass
class StressTestData:
    """压力测试数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表21

    Attributes:
        scenarios: 场景列表
        expected_losses: 预期损失列表
        var_95: 95% VaR列表
        var_99: 99% VaR列表
        recovery_days: 恢复天数列表
    """

    scenarios: List[str]
    expected_losses: List[float]
    var_95: List[float]
    var_99: List[float]
    recovery_days: List[int]

    def __post_init__(self) -> None:
        """验证压力测试数据"""
        n = len(self.scenarios)
        if len(self.expected_losses) != n:
            raise ValueError("场景和预期损失长度必须一致")
        if len(self.var_95) != n:
            raise ValueError("场景和95% VaR长度必须一致")
        if len(self.var_99) != n:
            raise ValueError("场景和99% VaR长度必须一致")
        if len(self.recovery_days) != n:
            raise ValueError("场景和恢复天数长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "scenarios": self.scenarios,
            "expected_losses": self.expected_losses,
            "var_95": self.var_95,
            "var_99": self.var_99,
            "recovery_days": self.recovery_days,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StressTestData":
        """从字典创建压力测试数据对象"""
        return cls(
            scenarios=data["scenarios"],
            expected_losses=data["expected_losses"],
            var_95=data["var_95"],
            var_99=data["var_99"],
            recovery_days=data["recovery_days"],
        )


@dataclass
class TradingCostData:
    """交易成本数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表22

    Attributes:
        cost_types: 成本类型列表
        amounts: 金额列表
        percentages: 百分比列表
        total_cost: 总成本
    """

    cost_types: List[str]
    amounts: List[float]
    percentages: List[float]
    total_cost: float

    def __post_init__(self) -> None:
        """验证交易成本数据"""
        n = len(self.cost_types)
        if len(self.amounts) != n:
            raise ValueError("成本类型和金额长度必须一致")
        if len(self.percentages) != n:
            raise ValueError("成本类型和百分比长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "cost_types": self.cost_types,
            "amounts": self.amounts,
            "percentages": self.percentages,
            "total_cost": self.total_cost,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TradingCostData":
        """从字典创建交易成本数据对象"""
        return cls(
            cost_types=data["cost_types"],
            amounts=data["amounts"],
            percentages=data["percentages"],
            total_cost=data["total_cost"],
        )


@dataclass
class DecayData:
    """策略衰减数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表23

    Attributes:
        timestamps: 时间戳列表
        performance_scores: 表现得分列表
        decay_rate: 衰减率
        estimated_half_life: 预估半衰期（天）
    """

    timestamps: List[datetime]
    performance_scores: List[float]
    decay_rate: float
    estimated_half_life: int

    def __post_init__(self) -> None:
        """验证策略衰减数据"""
        if len(self.timestamps) != len(self.performance_scores):
            raise ValueError("时间戳和表现得分长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "timestamps": [t.isoformat() for t in self.timestamps],
            "performance_scores": self.performance_scores,
            "decay_rate": self.decay_rate,
            "estimated_half_life": self.estimated_half_life,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecayData":
        """从字典创建策略衰减数据对象"""
        return cls(
            timestamps=[datetime.fromisoformat(t) for t in data["timestamps"]],
            performance_scores=data["performance_scores"],
            decay_rate=data["decay_rate"],
            estimated_half_life=data["estimated_half_life"],
        )


@dataclass
class PositionData:
    """仓位数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表24

    Attributes:
        symbols: 股票代码列表
        weights: 权重列表
        sectors: 板块列表
        risk_contributions: 风险贡献列表
    """

    symbols: List[str]
    weights: List[float]
    sectors: List[str]
    risk_contributions: List[float]

    def __post_init__(self) -> None:
        """验证仓位数据"""
        n = len(self.symbols)
        if len(self.weights) != n:
            raise ValueError("股票代码和权重长度必须一致")
        if len(self.sectors) != n:
            raise ValueError("股票代码和板块长度必须一致")
        if len(self.risk_contributions) != n:
            raise ValueError("股票代码和风险贡献长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "symbols": self.symbols,
            "weights": self.weights,
            "sectors": self.sectors,
            "risk_contributions": self.risk_contributions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PositionData":
        """从字典创建仓位数据对象"""
        return cls(
            symbols=data["symbols"],
            weights=data["weights"],
            sectors=data["sectors"],
            risk_contributions=data["risk_contributions"],
        )


@dataclass
class FitnessEvolutionData:
    """适应度演化数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表25

    Attributes:
        generations: 代数列表
        best_fitness: 最佳适应度列表
        avg_fitness: 平均适应度列表
        worst_fitness: 最差适应度列表
    """

    generations: List[int]
    best_fitness: List[float]
    avg_fitness: List[float]
    worst_fitness: List[float]

    def __post_init__(self) -> None:
        """验证适应度演化数据"""
        n = len(self.generations)
        if len(self.best_fitness) != n:
            raise ValueError("代数和最佳适应度长度必须一致")
        if len(self.avg_fitness) != n:
            raise ValueError("代数和平均适应度长度必须一致")
        if len(self.worst_fitness) != n:
            raise ValueError("代数和最差适应度长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "generations": self.generations,
            "best_fitness": self.best_fitness,
            "avg_fitness": self.avg_fitness,
            "worst_fitness": self.worst_fitness,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FitnessEvolutionData":
        """从字典创建适应度演化数据对象"""
        return cls(
            generations=data["generations"],
            best_fitness=data["best_fitness"],
            avg_fitness=data["avg_fitness"],
            worst_fitness=data["worst_fitness"],
        )


@dataclass
class ArenaComparisonData:
    """Arena表现对比数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表26

    Attributes:
        strategy_names: 策略名称列表
        reality_track_scores: 现实轨道得分列表
        hell_track_scores: 地狱轨道得分列表
        cross_market_scores: 跨市场得分列表
    """

    strategy_names: List[str]
    reality_track_scores: List[float]
    hell_track_scores: List[float]
    cross_market_scores: List[float]

    def __post_init__(self) -> None:
        """验证Arena表现对比数据"""
        n = len(self.strategy_names)
        if len(self.reality_track_scores) != n:
            raise ValueError("策略名称和现实轨道得分长度必须一致")
        if len(self.hell_track_scores) != n:
            raise ValueError("策略名称和地狱轨道得分长度必须一致")
        if len(self.cross_market_scores) != n:
            raise ValueError("策略名称和跨市场得分长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "strategy_names": self.strategy_names,
            "reality_track_scores": self.reality_track_scores,
            "hell_track_scores": self.hell_track_scores,
            "cross_market_scores": self.cross_market_scores,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArenaComparisonData":
        """从字典创建Arena表现对比数据对象"""
        return cls(
            strategy_names=data["strategy_names"],
            reality_track_scores=data["reality_track_scores"],
            hell_track_scores=data["hell_track_scores"],
            cross_market_scores=data["cross_market_scores"],
        )


@dataclass
class FactorEvolutionData:
    """因子演化数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表27

    Attributes:
        factor_names: 因子名称列表
        generations: 代数列表
        ic_values: IC值矩阵 [因子][代数]
        ir_values: IR值矩阵 [因子][代数]
    """

    factor_names: List[str]
    generations: List[int]
    ic_values: List[List[float]]
    ir_values: List[List[float]]

    def __post_init__(self) -> None:
        """验证因子演化数据"""
        n_factors = len(self.factor_names)
        n_generations = len(self.generations)
        if len(self.ic_values) != n_factors:
            raise ValueError("因子名称和IC值矩阵行数必须一致")
        if len(self.ir_values) != n_factors:
            raise ValueError("因子名称和IR值矩阵行数必须一致")
        for i, ic_row in enumerate(self.ic_values):
            if len(ic_row) != n_generations:
                raise ValueError(f"IC值矩阵第{i}行长度与代数列表长度不一致")
        for i, ir_row in enumerate(self.ir_values):
            if len(ir_row) != n_generations:
                raise ValueError(f"IR值矩阵第{i}行长度与代数列表长度不一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "factor_names": self.factor_names,
            "generations": self.generations,
            "ic_values": self.ic_values,
            "ir_values": self.ir_values,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactorEvolutionData":
        """从字典创建因子演化数据对象"""
        return cls(
            factor_names=data["factor_names"],
            generations=data["generations"],
            ic_values=data["ic_values"],
            ir_values=data["ir_values"],
        )


@dataclass
class SmartMoneyCostData:
    """主力成本分布数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表28

    Attributes:
        price_levels: 价格级别列表
        volume_distribution: 成交量分布列表
        cost_center: 成本中心
        support_levels: 支撑位列表
        resistance_levels: 阻力位列表
    """

    price_levels: List[float]
    volume_distribution: List[float]
    cost_center: float
    support_levels: List[float]
    resistance_levels: List[float]

    def __post_init__(self) -> None:
        """验证主力成本分布数据"""
        if len(self.price_levels) != len(self.volume_distribution):
            raise ValueError("价格级别和成交量分布长度必须一致")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "price_levels": self.price_levels,
            "volume_distribution": self.volume_distribution,
            "cost_center": self.cost_center,
            "support_levels": self.support_levels,
            "resistance_levels": self.resistance_levels,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SmartMoneyCostData":
        """从字典创建主力成本分布数据对象"""
        return cls(
            price_levels=data["price_levels"],
            volume_distribution=data["volume_distribution"],
            cost_center=data["cost_center"],
            support_levels=data["support_levels"],
            resistance_levels=data["resistance_levels"],
        )


@dataclass
class StockScorecardData:
    """个股综合评分卡数据模型

    白皮书依据: 第五章 5.4.3 29种可视化图表 - 图表29

    Attributes:
        symbol: 股票代码
        name: 股票名称
        overall_score: 综合评分
        dimension_scores: 维度评分字典
        strengths: 优势列表
        weaknesses: 劣势列表
        recommendation: 建议
    """

    symbol: str
    name: str
    overall_score: float
    dimension_scores: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    recommendation: str

    def __post_init__(self) -> None:
        """验证个股综合评分卡数据"""
        if not self.symbol:
            raise ValueError("股票代码不能为空")
        if not self.name:
            raise ValueError("股票名称不能为空")
        if not 0 <= self.overall_score <= 100:
            raise ValueError(f"综合评分必须在[0, 100]范围内，当前: {self.overall_score}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "overall_score": self.overall_score,
            "dimension_scores": self.dimension_scores,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StockScorecardData":
        """从字典创建个股综合评分卡数据对象"""
        return cls(
            symbol=data["symbol"],
            name=data["name"],
            overall_score=data["overall_score"],
            dimension_scores=data["dimension_scores"],
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            recommendation=data.get("recommendation", ""),
        )
