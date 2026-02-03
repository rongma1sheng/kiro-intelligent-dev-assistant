"""可视化系统模块

白皮书依据: 第五章 5.4 可视化系统

本模块提供MIA系统的可视化功能，包括：
- 策略分析中心仪表盘 (StrategyDashboard)
- 个股分析仪表盘 (StockDashboard)
- 29种可视化图表生成器 (ChartGenerator)

性能要求:
- 可视化加载: <2秒
- PDF报告生成: <10秒
- 个股建议生成: <3秒
"""

from src.brain.visualization.charts import (
    ChartGenerationError,
    ChartGenerator,
)
from src.brain.visualization.data_models import (
    ArenaComparisonData,
    BehaviorPattern,
    CapacityData,
    DecayData,
    DrawdownData,
    EfficientFrontierData,
    FactorEvolutionData,
    FitnessEvolutionData,
    HoldingPeriod,
    LimitUpData,
    MarketAdaptation,
    MarketTechnicalData,
    NonstationarityData,
    OverfittingData,
    OverfittingRiskLevel,
    PositionData,
    PositionSuggestion,
    RecommendationAction,
    RiskLevel,
    SectorRotationData,
    SectorStrengthData,
    SentimentData,
    SignalNoiseData,
    SmartMoneyAnalysis,
    SmartMoneyCostData,
    SmartMoneyType,
    SmartRetailData,
    StockDashboardData,
    StockRecommendation,
    StockScorecardData,
    StopLossData,
    StrategyDashboardData,
    StressTestData,
    TradeRecord,
    TradingCostData,
)
from src.brain.visualization.stock_dashboard import (
    RecommendationRefreshError,
    SmartMoneyAnalysisError,
    StockDashboard,
    StockDashboardLoadError,
)
from src.brain.visualization.strategy_dashboard import (
    DashboardLoadError,
    DataExportError,
    PDFGenerationError,
    StrategyDashboard,
)

__all__ = [
    # 仪表盘类
    "StrategyDashboard",
    "StockDashboard",
    # 图表生成器
    "ChartGenerator",
    # 仪表盘数据模型
    "StrategyDashboardData",
    "StockDashboardData",
    "StockRecommendation",
    "SmartMoneyAnalysis",
    # 枚举类型
    "RecommendationAction",
    "SmartMoneyType",
    "BehaviorPattern",
    "RiskLevel",
    "OverfittingRiskLevel",
    "MarketAdaptation",
    "HoldingPeriod",
    "PositionSuggestion",
    # 图表数据模型
    "OverfittingData",
    "NonstationarityData",
    "SignalNoiseData",
    "CapacityData",
    "StopLossData",
    "TradeRecord",
    "SentimentData",
    "SmartRetailData",
    "MarketTechnicalData",
    "LimitUpData",
    "SectorStrengthData",
    "SectorRotationData",
    "DrawdownData",
    "EfficientFrontierData",
    "StressTestData",
    "TradingCostData",
    "DecayData",
    "PositionData",
    "FitnessEvolutionData",
    "ArenaComparisonData",
    "FactorEvolutionData",
    "SmartMoneyCostData",
    "StockScorecardData",
    # 异常类
    "ChartGenerationError",
    "DashboardLoadError",
    "PDFGenerationError",
    "DataExportError",
    "StockDashboardLoadError",
    "RecommendationRefreshError",
    "SmartMoneyAnalysisError",
]
