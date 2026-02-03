"""策略分析器核心模块

白皮书依据: 第五章 5.1 系统定位与架构
职责: 策略深度分析、进化指导、生命周期预测、知识积累
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from ...core.dependency_container import LifecycleScope, injectable
from ...infra.event_bus import Event, EventBus, EventType
from .data_models import ComprehensiveAnalysisReport, MacroAnalysisReport, SmartMoneyDeepAnalysis, StockRecommendation


@injectable(LifecycleScope.SINGLETON)
class StrategyAnalyzer:
    """策略分析器核心类

    白皮书依据: 第五章 5.1 系统定位与架构

    作为达尔文进化体系的智能大脑，负责29个维度的策略深度分析，
    指导策略进化方向，预测策略生命周期，实现全链溯源和知识积累。

    核心功能:
    - 综合分析接口
    - 29个维度协调
    - 结果聚合
    - Redis存储

    性能要求:
    - 单个维度分析: <5秒
    - 综合分析(29维度): <30秒
    - 可视化加载: <2秒
    """

    def __init__(self):
        """初始化策略分析器"""
        self.event_bus: Optional[EventBus] = None
        self.redis_storage = None  # Redis存储管理器

        # 分析器实例缓存
        self._analyzers: Dict[str, Any] = {}

        # 分析结果缓存（内存缓存）
        self._analysis_cache: Dict[str, ComprehensiveAnalysisReport] = {}
        self._cache_ttl = 3600  # 1小时缓存

        logger.info("StrategyAnalyzer初始化完成")

    async def initialize(self) -> bool:
        """初始化分析器

        Returns:
            bool: 初始化是否成功
        """
        try:
            # 获取事件总线
            from ...infra.event_bus import get_event_bus  # pylint: disable=import-outside-toplevel

            self.event_bus = await get_event_bus()

            # 初始化Redis存储
            from .redis_storage import get_redis_storage_manager  # pylint: disable=import-outside-toplevel

            self.redis_storage = await get_redis_storage_manager()

            # 初始化各个分析器
            await self._initialize_analyzers()

            logger.info("StrategyAnalyzer初始化完成")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"StrategyAnalyzer初始化失败: {e}")
            return False

    async def _initialize_analyzers(self):
        """初始化所有分析器"""
        try:
            # 延迟导入避免循环依赖
            from .capacity_analyzer import CapacityAnalyzer  # pylint: disable=import-outside-toplevel
            from .correlation_analyzer import CorrelationAnalyzer  # pylint: disable=import-outside-toplevel
            from .decay_analyzer import DecayAnalyzer  # pylint: disable=import-outside-toplevel
            from .essence_analyzer import EssenceAnalyzer  # pylint: disable=import-outside-toplevel
            from .factor_exposure_analyzer import FactorExposureAnalyzer  # pylint: disable=import-outside-toplevel
            from .feature_analyzer import FeatureAnalyzer  # pylint: disable=import-outside-toplevel
            from .macro_analyzer import MacroAnalyzer  # pylint: disable=import-outside-toplevel
            from .microstructure_analyzer import MicrostructureAnalyzer  # pylint: disable=import-outside-toplevel
            from .nonstationarity_analyzer import NonstationarityAnalyzer  # pylint: disable=import-outside-toplevel
            from .overfitting_detector import OverfittingDetector  # pylint: disable=import-outside-toplevel

            # 新增4个分析器 ⭐
            from .portfolio_optimization_analyzer import (  # pylint: disable=import-outside-toplevel
                PortfolioOptimizationAnalyzer,
            )
            from .position_sizing_analyzer import PositionSizingAnalyzer  # pylint: disable=import-outside-toplevel
            from .recommendation_engine import RecommendationEngine  # pylint: disable=import-outside-toplevel
            from .regime_adaptation_analyzer import RegimeAdaptationAnalyzer  # pylint: disable=import-outside-toplevel
            from .retail_sentiment_analyzer import RetailSentimentAnalyzer  # pylint: disable=import-outside-toplevel
            from .risk_analyzer import RiskAnalyzer  # pylint: disable=import-outside-toplevel
            from .sector_analyzer import SectorAnalyzer  # pylint: disable=import-outside-toplevel
            from .sentiment_analyzer import SentimentAnalyzer  # pylint: disable=import-outside-toplevel
            from .signal_noise_analyzer import SignalNoiseAnalyzer  # pylint: disable=import-outside-toplevel
            from .slippage_analyzer import SlippageAnalyzer  # pylint: disable=import-outside-toplevel
            from .smart_money_analyzer import SmartMoneyAnalyzer  # pylint: disable=import-outside-toplevel
            from .stop_loss_analyzer import StopLossAnalyzer  # pylint: disable=import-outside-toplevel
            from .stress_test_analyzer import StressTestAnalyzer  # pylint: disable=import-outside-toplevel
            from .trade_review_analyzer import TradeReviewAnalyzer  # pylint: disable=import-outside-toplevel
            from .trading_cost_analyzer import TradingCostAnalyzer  # pylint: disable=import-outside-toplevel
            from .transaction_cost_analyzer import TransactionCostAnalyzer  # pylint: disable=import-outside-toplevel

            self._analyzers = {
                "essence": EssenceAnalyzer(),
                "risk": RiskAnalyzer(),
                "overfitting": OverfittingDetector(),
                "feature": FeatureAnalyzer(),
                "macro": MacroAnalyzer(),
                "microstructure": MicrostructureAnalyzer(),
                "sector": SectorAnalyzer(),
                "smart_money": SmartMoneyAnalyzer(),
                "recommendation": RecommendationEngine(),
                "trading_cost": TradingCostAnalyzer(),
                "decay": DecayAnalyzer(),
                "stop_loss": StopLossAnalyzer(),
                "slippage": SlippageAnalyzer(),
                "nonstationarity": NonstationarityAnalyzer(),
                "signal_noise": SignalNoiseAnalyzer(),
                "capacity": CapacityAnalyzer(),
                "stress_test": StressTestAnalyzer(),
                "trade_review": TradeReviewAnalyzer(),
                "sentiment": SentimentAnalyzer(),
                "retail_sentiment": RetailSentimentAnalyzer(),
                "correlation": CorrelationAnalyzer(),
                "position_sizing": PositionSizingAnalyzer(),
                # 新增4个分析器 ⭐
                "portfolio_optimization": PortfolioOptimizationAnalyzer(),
                "regime_adaptation": RegimeAdaptationAnalyzer(),
                "factor_exposure": FactorExposureAnalyzer(),
                "transaction_cost_deep": TransactionCostAnalyzer(),
            }

            logger.info(f"已初始化 {len(self._analyzers)} 个分析器")

        except ImportError as e:
            logger.warning(f"部分分析器导入失败: {e}")

    async def analyze_strategy(
        self, strategy_id: str, strategy_data: Dict[str, Any], dimensions: Optional[List[str]] = None
    ) -> ComprehensiveAnalysisReport:
        """综合分析策略

        白皮书依据: 第五章 5.1 系统定位与架构

        Args:
            strategy_id: 策略ID
            strategy_data: 策略数据（包含代码、参数、历史表现等）
            dimensions: 要分析的维度列表，None表示全部29个维度

        Returns:
            ComprehensiveAnalysisReport: 综合分析报告
        """
        start_time = datetime.now()
        logger.info(f"开始综合分析策略: {strategy_id}")

        # 检查缓存
        cache_key = f"{strategy_id}:{hash(str(dimensions))}"
        if cache_key in self._analysis_cache:
            cached = self._analysis_cache[cache_key]
            cache_age = (datetime.now() - cached.analysis_timestamp).total_seconds()
            if cache_age < self._cache_ttl:
                logger.info(f"使用缓存的分析结果: {strategy_id}")
                return cached

        # 确定要分析的维度
        all_dimensions = [
            "essence",
            "risk",
            "overfitting",
            "feature",
            "macro",
            "microstructure",
            "sector",
            "smart_money",
            "recommendation",
            "trading_cost",
            "decay",
            "stop_loss",
            "slippage",
            "nonstationarity",
            "signal_noise",
            "capacity",
            "stress_test",
            "trade_review",
            "sentiment",
            "retail_sentiment",
            "correlation",
            "position_sizing",
            # 新增4个维度 ⭐
            "portfolio_optimization",
            "regime_adaptation",
            "factor_exposure",
            "transaction_cost_deep",
        ]

        dimensions_to_analyze = dimensions or all_dimensions

        # 并行执行分析
        analysis_tasks = []
        for dim in dimensions_to_analyze:
            if dim in self._analyzers:
                task = self._run_analyzer(dim, strategy_id, strategy_data)
                analysis_tasks.append((dim, task))

        # 收集结果
        results = {}
        for dim, task in analysis_tasks:
            try:
                result = await task
                results[dim] = result
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"分析维度 {dim} 失败: {e}")
                results[dim] = None

        # 计算综合评分
        overall_score = self._calculate_overall_score(results)

        # 构建综合报告
        report = ComprehensiveAnalysisReport(
            strategy_id=strategy_id,
            overall_score=overall_score,
            essence_report=results.get("essence"),
            risk_report=results.get("risk"),
            overfitting_report=results.get("overfitting"),
            feature_report=results.get("feature"),
            macro_report=results.get("macro"),
            microstructure_report=results.get("microstructure"),
            sector_report=results.get("sector"),
            smart_money_report=results.get("smart_money"),
            recommendation=results.get("recommendation"),
            trading_cost_report=results.get("trading_cost"),
            decay_report=results.get("decay"),
            stop_loss_report=results.get("stop_loss"),
            slippage_report=results.get("slippage"),
            nonstationarity_report=results.get("nonstationarity"),
            signal_noise_report=results.get("signal_noise"),
            capacity_report=results.get("capacity"),
            stress_test_report=results.get("stress_test"),
            trade_review_report=results.get("trade_review"),
            sentiment_report=results.get("sentiment"),
            retail_sentiment_report=results.get("retail_sentiment"),
            correlation_report=results.get("correlation"),
            position_sizing_report=results.get("position_sizing"),
            # 新增4个报告 ⭐
            portfolio_optimization_report=results.get("portfolio_optimization"),
            regime_adaptation_report=results.get("regime_adaptation"),
            factor_exposure_report=results.get("factor_exposure"),
            transaction_cost_report=results.get("transaction_cost_deep"),
        )

        # 缓存结果
        self._analysis_cache[cache_key] = report

        # 存储到Redis
        await self._store_to_redis(strategy_id, report)

        # 发布分析完成事件
        if self.event_bus:
            await self.event_bus.publish(
                Event(
                    event_type=EventType.ANALYSIS_COMPLETED,
                    data={
                        "strategy_id": strategy_id,
                        "overall_score": overall_score,
                        "dimensions_analyzed": len(dimensions_to_analyze),
                    },
                )
            )

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"策略分析完成: {strategy_id}, 耗时: {elapsed:.2f}秒, 评分: {overall_score:.1f}")

        return report

    async def _run_analyzer(self, dimension: str, strategy_id: str, strategy_data: Dict[str, Any]) -> Any:
        """运行单个分析器

        Args:
            dimension: 分析维度
            strategy_id: 策略ID
            strategy_data: 策略数据

        Returns:
            分析结果
        """
        analyzer = self._analyzers.get(dimension)
        if not analyzer:
            logger.warning(f"分析器不存在: {dimension}")
            return None

        try:
            # 调用分析器的analyze方法
            if hasattr(analyzer, "analyze"):  # pylint: disable=no-else-return
                return await analyzer.analyze(strategy_id, strategy_data)
            else:
                logger.warning(f"分析器 {dimension} 没有analyze方法")
                return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"运行分析器 {dimension} 失败: {e}")
            return None

    def _calculate_overall_score(self, results: Dict[str, Any]) -> float:
        """计算综合评分

        白皮书依据: 第五章 5.1 系统定位与架构

        Args:
            results: 各维度分析结果

        Returns:
            float: 综合评分 0-100
        """
        weights = {
            "essence": 0.10,
            "risk": 0.15,
            "overfitting": 0.12,
            "feature": 0.08,
            "macro": 0.05,
            "microstructure": 0.03,
            "sector": 0.03,
            "smart_money": 0.05,
            "trading_cost": 0.05,
            "decay": 0.08,
            "stop_loss": 0.04,
            "slippage": 0.03,
            "nonstationarity": 0.04,
            "signal_noise": 0.05,
            "capacity": 0.03,
            "stress_test": 0.05,
            "trade_review": 0.02,
            # 新增4个分析器权重 ⭐
            "portfolio_optimization": 0.04,
            "regime_adaptation": 0.05,
            "factor_exposure": 0.04,
            "transaction_cost_deep": 0.03,
        }

        total_weight = 0
        weighted_sum = 0

        for dim, result in results.items():
            if result is None:
                continue

            weight = weights.get(dim, 0.02)
            score = self._extract_score(dim, result)

            if score is not None:
                weighted_sum += score * weight
                total_weight += weight

        if total_weight == 0:
            return 50.0  # 默认中等评分

        return min(100, max(0, (weighted_sum / total_weight) * 100))

    def _extract_score(self, dimension: str, result: Any) -> Optional[float]:
        """从分析结果中提取评分

        Args:
            dimension: 分析维度
            result: 分析结果

        Returns:
            Optional[float]: 评分 0-1
        """
        if result is None:
            return None

        # 根据不同维度提取评分
        score_mappings = {
            "essence": lambda r: r.sustainability_score if hasattr(r, "sustainability_score") else None,
            "risk": lambda r: 1 - (r.risk_score / 100) if hasattr(r, "risk_score") else None,
            "overfitting": lambda r: (
                1 - (r.overfitting_probability / 100) if hasattr(r, "overfitting_probability") else None
            ),
            "feature": lambda r: (
                sum(r.stability_scores.values()) / len(r.stability_scores)
                if hasattr(r, "stability_scores") and r.stability_scores
                else None
            ),
            "trading_cost": lambda r: r.cost_efficiency if hasattr(r, "cost_efficiency") else None,
            "decay": lambda r: 1 - (r.return_decay_rate / 100) if hasattr(r, "return_decay_rate") else None,
            "stop_loss": lambda r: r.stop_loss_effectiveness if hasattr(r, "stop_loss_effectiveness") else None,
            "signal_noise": lambda r: r.overall_quality if hasattr(r, "overall_quality") else None,
            "capacity": lambda r: r.scalability_score if hasattr(r, "scalability_score") else None,
            "stress_test": lambda r: r.survival_probability if hasattr(r, "survival_probability") else None,
            "trade_review": lambda r: r.avg_quality_score if hasattr(r, "avg_quality_score") else None,
            # 新增4个分析器评分提取 ⭐
            "portfolio_optimization": lambda r: (
                r.sharpe_ratio / 3.0 if hasattr(r, "sharpe_ratio") else None
            ),  # 夏普比率归一化
            "regime_adaptation": lambda r: r.adaptation_score if hasattr(r, "adaptation_score") else None,
            "factor_exposure": lambda r: (
                r.information_ratio / 2.0 if hasattr(r, "information_ratio") else None
            ),  # IR归一化
            "transaction_cost_deep": lambda r: r.cost_efficiency if hasattr(r, "cost_efficiency") else None,
        }

        extractor = score_mappings.get(dimension)
        if extractor:
            try:
                return extractor(result)
            except Exception:  # pylint: disable=broad-exception-caught
                return None

        return 0.5  # 默认中等评分

    async def _store_to_redis(self, strategy_id: str, report: ComprehensiveAnalysisReport):
        """存储分析结果到Redis

        白皮书依据: 第五章 5.5 Redis数据结构

        Args:
            strategy_id: 策略ID
            report: 综合分析报告
        """
        if not self.redis_storage:
            logger.debug("Redis存储未初始化，跳过存储")
            return

        try:
            # 转换为字典
            report_dict = {
                "strategy_id": report.strategy_id,
                "overall_score": report.overall_score,
                "analysis_timestamp": (
                    report.analysis_timestamp.isoformat()
                    if hasattr(report, "analysis_timestamp")
                    else datetime.now().isoformat()
                ),
                # 存储各维度报告（简化版本，只存储关键信息）
                "dimensions": {},
            }

            # 添加各维度的关键信息
            if report.essence_report:
                report_dict["dimensions"]["essence"] = {"available": True}
            if report.risk_report:
                report_dict["dimensions"]["risk"] = {"available": True}
            # ... 其他维度类似

            # 存储到Redis
            await self.redis_storage.store_comprehensive_analysis(strategy_id=strategy_id, report=report_dict)

            logger.debug(f"分析结果已存储到Redis: {strategy_id}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"存储分析结果到Redis失败: {e}")

    async def get_cached_analysis(self, strategy_id: str) -> Optional[ComprehensiveAnalysisReport]:
        """获取缓存的分析结果

        Args:
            strategy_id: 策略ID

        Returns:
            Optional[ComprehensiveAnalysisReport]: 缓存的分析报告
        """
        # 先检查内存缓存
        for key, report in self._analysis_cache.items():
            if key.startswith(strategy_id):
                return report

        # 再检查Redis
        if self.redis_storage:
            try:
                data = await self.redis_storage.get_comprehensive_analysis(strategy_id)
                if data:
                    logger.debug(f"从Redis获取分析结果: {strategy_id}")
                    return data
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"从Redis获取分析结果失败: {e}")

        return None

    async def analyze_stock(self, symbol: str, market_data: Dict[str, Any]) -> StockRecommendation:
        """分析个股并生成建议

        白皮书依据: 第五章 5.2.9 个股结论性建议

        Args:
            symbol: 股票代码
            market_data: 市场数据

        Returns:
            StockRecommendation: 个股建议
        """
        logger.info(f"开始分析个股: {symbol}")

        recommendation_engine = self._analyzers.get("recommendation")
        if recommendation_engine:
            return await recommendation_engine.analyze(symbol, market_data)

        # 如果没有推荐引擎，返回默认建议
        from .data_models import ActionType, HoldingPeriod, PositionSize  # pylint: disable=import-outside-toplevel

        return StockRecommendation(
            symbol=symbol,
            action=ActionType.WATCH,
            confidence=0.5,
            reasons=["分析引擎未初始化"],
            risks=["无法进行完整分析"],
            entry_price=0.0,
            stop_loss=0.0,
            target_price=0.0,
            position_size=PositionSize.LIGHT,
            holding_period=HoldingPeriod.SHORT,
            overall_score={},
        )

    async def analyze_smart_money(self, symbol: str, level2_data: Dict[str, Any]) -> SmartMoneyDeepAnalysis:
        """分析主力资金

        白皮书依据: 第五章 5.2.8 主力资金深度分析

        Args:
            symbol: 股票代码
            level2_data: Level-2数据

        Returns:
            SmartMoneyDeepAnalysis: 主力资金分析
        """
        logger.info(f"开始分析主力资金: {symbol}")

        smart_money_analyzer = self._analyzers.get("smart_money")
        if smart_money_analyzer:
            return await smart_money_analyzer.analyze(symbol, level2_data)

        # 返回默认分析
        from .data_models import BehaviorPattern, MainForceType, RiskLevel  # pylint: disable=import-outside-toplevel

        return SmartMoneyDeepAnalysis(
            symbol=symbol,
            cost_basis=0.0,
            cost_range=(0.0, 0.0),
            estimated_holdings=0.0,
            holdings_pct=0.0,
            profit_loss=0.0,
            profit_loss_pct=0.0,
            main_force_type=MainForceType.MIXED,
            behavior_pattern=BehaviorPattern.WAITING,
            next_action_prediction="无法预测",
            follow_risk=RiskLevel.HIGH,
            confidence=0.0,
        )

    async def analyze_market(self) -> MacroAnalysisReport:
        """分析大盘和宏观环境

        白皮书依据: 第五章 5.2.5 大盘判断与宏观分析

        Returns:
            MacroAnalysisReport: 宏观分析报告
        """
        logger.info("开始分析大盘和宏观环境")

        macro_analyzer = self._analyzers.get("macro")
        if macro_analyzer:
            return await macro_analyzer.analyze()

        # 返回默认分析
        from .data_models import MarketScenario  # pylint: disable=import-outside-toplevel

        return MacroAnalysisReport(
            market_stage=MarketScenario.SIDEWAYS,
            confidence=0.5,
            technical_analysis={},
            sentiment_analysis={},
            macro_indicators={},
            policy_impact={},
            capital_flow={},
            sector_rotation={},
            position_recommendation="半仓",
            strategy_type_recommendation=["均衡配置"],
        )

    def get_analyzer_status(self) -> Dict[str, bool]:
        """获取各分析器状态

        Returns:
            Dict[str, bool]: 分析器名称 -> 是否可用
        """
        return {name: analyzer is not None for name, analyzer in self._analyzers.items()}
