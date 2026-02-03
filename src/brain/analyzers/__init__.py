"""第五章 LLM策略深度分析系统

白皮书依据: 第五章 5.1-5.2 LLM策略深度分析系统

本模块包含26个专业分析器，覆盖29个分析维度：
1. 策略本质分析 (EssenceAnalyzer)
2. 风险识别与评估 (RiskAnalyzer)
3. 过度拟合检测 (OverfittingDetector)
4. 特征工程分析 (FeatureAnalyzer)
5. 大盘判断与宏观分析 (MacroAnalyzer)
6. 市场微观结构分析 (MicrostructureAnalyzer)
7. 行业与板块分析 (SectorAnalyzer)
8. 主力资金深度分析 (SmartMoneyAnalyzer)
9. 个股结论性建议 (RecommendationEngine)
10. 交易成本分析 (TradingCostAnalyzer)
11. 策略衰减分析 (DecayAnalyzer)
12. 止损逻辑优化 (StopLossAnalyzer)
13. 滑点分析 (SlippageAnalyzer)
14. 非平稳性处理 (NonstationarityAnalyzer)
15. 信噪比分析 (SignalNoiseAnalyzer)
16. 资金容量评估 (CapacityAnalyzer)
17. 压力测试 (StressTestAnalyzer)
18. 交易复盘 (TradeReviewAnalyzer)
19. 市场情绪分析 (SentimentAnalyzer)
20. 散户情绪分析 (RetailSentimentAnalyzer)
21. 相关性分析 (CorrelationAnalyzer)
22. 仓位管理分析 (PositionSizingAnalyzer)
23. 投资组合优化分析 (PortfolioOptimizationAnalyzer) ⭐ 新增
24. 市场状态适应分析 (RegimeAdaptationAnalyzer) ⭐ 新增
25. 因子暴露分析 (FactorExposureAnalyzer) ⭐ 新增
26. 交易成本深度分析 (TransactionCostAnalyzer) ⭐ 新增
"""

from .capacity_analyzer import CapacityAnalyzer
from .correlation_analyzer import CorrelationAnalyzer

# 数据模型
from .data_models import (  # 枚举类型; 报告数据类
    ActionType,
    BehaviorPattern,
    CapacityAnalysis,
    ComprehensiveAnalysisReport,
    CorrelationAnalysis,
    DecayAnalysis,
    DecayStage,
    DecayTrend,
    FactorExposureAnalysis,
    FeatureAnalysisReport,
    HoldingPeriod,
    MacroAnalysisReport,
    MainForceType,
    MarketScenario,
    MicrostructureReport,
    NonstationarityAnalysis,
    OverfittingReport,
    PortfolioOptimizationAnalysis,
    PositionSize,
    PositionSizingAnalysis,
    ProfitSource,
    RegimeAdaptationAnalysis,
    RetailSentimentAnalysis,
    RiskAssessmentReport,
    RiskLevel,
    SectorAnalysisReport,
    SentimentAnalysis,
    SentimentCategory,
    SentimentTrend,
    SignalNoiseAnalysis,
    SlippageAnalysis,
    SmartMoneyDeepAnalysis,
    SNRQuality,
    StockRecommendation,
    StopLossAnalysis,
    StopLossType,
    StrategyEssenceReport,
    StressTestAnalysis,
    StressTestGrade,
    TradeReviewAnalysis,
    TradingCostAnalysis,
    TransactionCostAnalysis,
)
from .decay_analyzer import DecayAnalyzer
from .essence_analyzer import EssenceAnalyzer
from .factor_exposure_analyzer import FactorExposureAnalyzer
from .feature_analyzer import FeatureAnalyzer
from .macro_analyzer import MacroAnalyzer
from .microstructure_analyzer import MicrostructureAnalyzer
from .nonstationarity_analyzer import NonstationarityAnalyzer
from .overfitting_detector import OverfittingDetector
from .portfolio_optimization_analyzer import PortfolioOptimizationAnalyzer
from .position_sizing_analyzer import PositionSizingAnalyzer
from .recommendation_engine import RecommendationEngine
from .regime_adaptation_analyzer import RegimeAdaptationAnalyzer
from .retail_sentiment_analyzer import RetailSentimentAnalyzer
from .risk_analyzer import RiskAnalyzer
from .sector_analyzer import SectorAnalyzer
from .sentiment_analyzer import SentimentAnalyzer
from .signal_noise_analyzer import SignalNoiseAnalyzer
from .slippage_analyzer import SlippageAnalyzer
from .smart_money_analyzer import SmartMoneyAnalyzer
from .stop_loss_analyzer import StopLossAnalyzer

# 分析器
from .strategy_analyzer import StrategyAnalyzer
from .stress_test_analyzer import StressTestAnalyzer
from .trade_review_analyzer import TradeReviewAnalyzer
from .trading_cost_analyzer import TradingCostAnalyzer
from .transaction_cost_analyzer import TransactionCostAnalyzer

__all__ = [
    # 枚举类型
    "ProfitSource",
    "MarketScenario",
    "RiskLevel",
    "MainForceType",
    "BehaviorPattern",
    "ActionType",
    "PositionSize",
    "HoldingPeriod",
    "DecayStage",
    "DecayTrend",
    "StopLossType",
    "SNRQuality",
    "StressTestGrade",
    "SentimentCategory",
    "SentimentTrend",
    # 报告数据类
    "StrategyEssenceReport",
    "RiskAssessmentReport",
    "OverfittingReport",
    "FeatureAnalysisReport",
    "MacroAnalysisReport",
    "MicrostructureReport",
    "SectorAnalysisReport",
    "SmartMoneyDeepAnalysis",
    "StockRecommendation",
    "TradingCostAnalysis",
    "DecayAnalysis",
    "StopLossAnalysis",
    "SlippageAnalysis",
    "NonstationarityAnalysis",
    "SignalNoiseAnalysis",
    "CapacityAnalysis",
    "StressTestAnalysis",
    "TradeReviewAnalysis",
    "SentimentAnalysis",
    "RetailSentimentAnalysis",
    "CorrelationAnalysis",
    "PositionSizingAnalysis",
    "PortfolioOptimizationAnalysis",
    "RegimeAdaptationAnalysis",
    "FactorExposureAnalysis",
    "TransactionCostAnalysis",
    "ComprehensiveAnalysisReport",
    # 分析器
    "StrategyAnalyzer",
    "EssenceAnalyzer",
    "RiskAnalyzer",
    "OverfittingDetector",
    "FeatureAnalyzer",
    "MacroAnalyzer",
    "MicrostructureAnalyzer",
    "SectorAnalyzer",
    "SmartMoneyAnalyzer",
    "RecommendationEngine",
    "TradingCostAnalyzer",
    "DecayAnalyzer",
    "StopLossAnalyzer",
    "SlippageAnalyzer",
    "NonstationarityAnalyzer",
    "SignalNoiseAnalyzer",
    "CapacityAnalyzer",
    "StressTestAnalyzer",
    "TradeReviewAnalyzer",
    "SentimentAnalyzer",
    "RetailSentimentAnalyzer",
    "CorrelationAnalyzer",
    "PositionSizingAnalyzer",
    "PortfolioOptimizationAnalyzer",
    "RegimeAdaptationAnalyzer",
    "FactorExposureAnalyzer",
    "TransactionCostAnalyzer",
]
