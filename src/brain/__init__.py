"""Brain模块 - MIA系统智能大脑

白皮书依据: 第五章 LLM策略深度分析系统

本模块提供MIA系统的核心智能功能，包括：
- 达尔文进化体系 (DarwinSystem)
- 基因胶囊管理 (GeneCapsuleManager)
- 演化树 (EvolutionTree)
- 反向黑名单库 (AntiPatternLibrary)
- Redis存储管理 (RedisStorageManager, TTLManager)
- 可视化系统 (StrategyDashboard, StockDashboard, ChartGenerator)

性能要求:
- 单个维度分析: <5秒
- 综合分析(29维度): <30秒
- 可视化加载: <2秒
- PDF报告生成: <10秒
- 个股建议生成: <3秒
"""

# 反向黑名单库
from src.brain.anti_pattern_library import (
    AntiPattern,
    AntiPatternLibrary,
    FailureCase,
)

# 数据模型
from src.brain.darwin_data_models import (
    AcademicFactorMatch,
    ArenaPerformance,
    AuditResult,
    EvolutionContext,
    EvolutionRecord,
    EvolutionReport,
    EvolutionResult,
    Factor,
    FactorMeaningAnalysis,
    FailureLearningResult,
    FamilyComparisonResult,
    GeneCapsule,
    OptimizationSuggestions,
    PerformanceDiffAnalysis,
    PerformancePrediction,
    WeaknessReport,
    Z2HCertificationResult,
    Z2HStampStatus,
)

# 达尔文进化体系
from src.brain.darwin_system import (
    AcademicSearchError,
    ArenaTestError,
    AuditError,
    DarwinSystem,
    EvolutionError,
    FactorAnalysisError,
    Z2HCertificationError,
)

# 演化树
from src.brain.evolution_tree import (
    EvolutionEdge,
    EvolutionNode,
    EvolutionTree,
)

# 基因胶囊管理
from src.brain.gene_capsule_manager import GeneCapsuleManager

# Redis存储
from src.brain.redis_storage import (
    RedisStorageManager,
    TTLManager,
)

# 可视化系统
from src.brain.visualization import (
    ChartGenerationError,
    ChartGenerator,
    DashboardLoadError,
    DataExportError,
    PDFGenerationError,
    RecommendationRefreshError,
    SmartMoneyAnalysis,
    SmartMoneyAnalysisError,
    StockDashboard,
    StockDashboardData,
    StockDashboardLoadError,
    StockRecommendation,
    StrategyDashboard,
    StrategyDashboardData,
)

__all__ = [
    # 达尔文进化体系
    "DarwinSystem",
    "EvolutionError",
    "FactorAnalysisError",
    "AcademicSearchError",
    "AuditError",
    "ArenaTestError",
    "Z2HCertificationError",
    # 数据模型
    "Factor",
    "GeneCapsule",
    "EvolutionResult",
    "EvolutionReport",
    "EvolutionContext",
    "FactorMeaningAnalysis",
    "AcademicFactorMatch",
    "PerformanceDiffAnalysis",
    "WeaknessReport",
    "OptimizationSuggestions",
    "PerformancePrediction",
    "ArenaPerformance",
    "AuditResult",
    "Z2HStampStatus",
    "Z2HCertificationResult",
    "EvolutionRecord",
    "FamilyComparisonResult",
    "FailureLearningResult",
    # 基因胶囊管理
    "GeneCapsuleManager",
    # 演化树
    "EvolutionTree",
    "EvolutionNode",
    "EvolutionEdge",
    # 反向黑名单库
    "AntiPatternLibrary",
    "AntiPattern",
    "FailureCase",
    # Redis存储
    "RedisStorageManager",
    "TTLManager",
    # 可视化系统
    "StrategyDashboard",
    "StockDashboard",
    "ChartGenerator",
    "StrategyDashboardData",
    "StockDashboardData",
    "StockRecommendation",
    "SmartMoneyAnalysis",
    "ChartGenerationError",
    "DashboardLoadError",
    "PDFGenerationError",
    "DataExportError",
    "StockDashboardLoadError",
    "RecommendationRefreshError",
    "SmartMoneyAnalysisError",
]
