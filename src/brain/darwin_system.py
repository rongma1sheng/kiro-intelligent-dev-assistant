# pylint: disable=too-many-lines
"""达尔文进化体系集成系统

白皮书依据: 第五章 5.3.1 进化协同流程

本模块实现了达尔文进化体系集成系统，负责：
- 协调遗传算法、策略分析、Arena测试等模块
- 实现完整的策略进化闭环
- 管理基因胶囊、演化树、反向黑名单

进化协同流程:
1. Strategy_Analyzer分析因子意义
2. Scholar查找相似学术因子
3. Devil检测未来函数
4. Arena双轨测试
5. Strategy_Analyzer分析表现差异
6. 识别弱点和改进方向
7. Commander提供超参数优化建议
8. 预测优化后表现
9. Z2H认证
10. 生成完整进化报告
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.brain.anti_pattern_library import AntiPatternLibrary
from src.brain.darwin_data_models import (
    AcademicFactorMatch,
    ArenaPerformance,
    ArenaTestResult,
    AuditResult,
    EvolutionContext,
    EvolutionRecord,
    EvolutionReport,
    EvolutionResult,
    Factor,
    FactorMeaningAnalysis,
    FailureStep,
    GeneCapsule,
    MutationType,
    OptimizationSuggestions,
    PerformanceDiffAnalysis,
    PerformancePrediction,
    WeaknessReport,
    Z2HCertificationResult,
    Z2HStampStatus,
)
from src.brain.evolution_tree import EvolutionTree
from src.brain.gene_capsule_manager import GeneCapsuleManager
from src.brain.redis_storage import RedisStorageManager


class EvolutionError(Exception):
    """进化流程错误基类"""


class FactorAnalysisError(EvolutionError):
    """因子分析错误"""


class AcademicSearchError(EvolutionError):
    """学术搜索错误"""


class AuditError(EvolutionError):
    """审计错误"""


class ArenaTestError(EvolutionError):
    """Arena测试错误"""


class Z2HCertificationError(EvolutionError):
    """Z2H认证错误"""


class DarwinSystem:
    """达尔文进化体系集成系统

    白皮书依据: 第五章 5.3.1 进化协同流程

    协调遗传算法、策略分析、Arena测试等模块，实现完整的策略进化闭环。

    进化流程:
    1. Strategy_Analyzer分析因子意义
    2. Scholar查找相似学术因子
    3. Devil检测未来函数
    4. Arena双轨测试
    5. Strategy_Analyzer分析表现差异
    6. 识别弱点和改进方向
    7. Commander提供超参数优化建议
    8. 预测优化后表现
    9. Z2H认证
    10. 生成完整进化报告

    Attributes:
        redis_storage: Redis存储管理器
        gene_capsule_manager: 基因胶囊管理器
        evolution_tree: 演化树
        anti_pattern_library: 反向黑名单库
        strategy_analyzer: 策略分析器（外部依赖）
        scholar_engine: 学者引擎（外部依赖）
        devil_auditor: 魔鬼审计器（外部依赖）
        arena: Arena竞技场（外部依赖）
        commander_engine: 指挥官引擎（外部依赖）
        z2h_certifier: Z2H认证器（外部依赖）
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        redis_storage: RedisStorageManager,
        strategy_analyzer: Optional[Any] = None,
        scholar_engine: Optional[Any] = None,
        devil_auditor: Optional[Any] = None,
        arena: Optional[Any] = None,
        commander_engine: Optional[Any] = None,
        z2h_certifier: Optional[Any] = None,
    ) -> None:
        """初始化达尔文进化系统

        Args:
            redis_storage: Redis存储管理器实例
            strategy_analyzer: 策略分析器（可选，用于测试）
            scholar_engine: 学者引擎（可选，用于测试）
            devil_auditor: 魔鬼审计器（可选，用于测试）
            arena: Arena竞技场（可选，用于测试）
            commander_engine: 指挥官引擎（可选，用于测试）
            z2h_certifier: Z2H认证器（可选，用于测试）

        Raises:
            ValueError: 当redis_storage为None时
        """
        if redis_storage is None:
            raise ValueError("Redis存储管理器不能为None")

        self._redis_storage = redis_storage

        # 初始化内部组件
        self._gene_capsule_manager = GeneCapsuleManager(redis_storage)
        self._evolution_tree: Optional[EvolutionTree] = None
        self._anti_pattern_library = AntiPatternLibrary(redis_storage)

        # 外部依赖（可注入用于测试）
        self._strategy_analyzer = strategy_analyzer
        self._scholar_engine = scholar_engine
        self._devil_auditor = devil_auditor
        self._arena = arena
        self._commander_engine = commander_engine
        self._z2h_certifier = z2h_certifier

        logger.info("DarwinSystem初始化完成")

    @property
    def gene_capsule_manager(self) -> GeneCapsuleManager:
        """获取基因胶囊管理器"""
        return self._gene_capsule_manager

    @property
    def anti_pattern_library(self) -> AntiPatternLibrary:
        """获取反向黑名单库"""
        return self._anti_pattern_library

    async def get_or_create_evolution_tree(
        self,
        family_id: Optional[str] = None,
    ) -> EvolutionTree:
        """获取或创建演化树

        Args:
            family_id: 家族ID（可选）

        Returns:
            EvolutionTree: 演化树实例
        """
        if self._evolution_tree is None:
            # 尝试从Redis加载
            self._evolution_tree = await EvolutionTree.load_from_redis(self._redis_storage)

            if self._evolution_tree is None:
                # 创建新的演化树
                self._evolution_tree = EvolutionTree(self._redis_storage, family_id)

        return self._evolution_tree

    async def evolve_factor(
        self,
        factor: Factor,
        parent_capsule_id: Optional[str] = None,
    ) -> EvolutionResult:
        """执行完整的因子进化流程

        白皮书依据: 第五章 5.3.1 进化协同流程

        完整流程:
        1. Strategy_Analyzer分析因子意义
        2. Scholar查找相似学术因子
        3. Devil检测未来函数
        4. Arena双轨测试
        5. Strategy_Analyzer分析表现差异
        6. 识别弱点和改进方向
        7. Commander提供超参数优化建议
        8. 预测优化后表现
        9. Z2H认证
        10. 生成完整进化报告

        Args:
            factor: 待进化的因子
            parent_capsule_id: 父代基因胶囊ID（如果是变异后代）

        Returns:
            EvolutionResult: 进化结果，包含基因胶囊、进化报告等

        Raises:
            ValueError: 当factor为None时
        """
        if factor is None:
            raise ValueError("因子不能为None")

        logger.info(f"开始进化因子: {factor.factor_id}, 名称: {factor.name}")

        # 初始化进化上下文
        context = EvolutionContext(
            factor=factor,
            parent_capsule_id=parent_capsule_id,
        )

        try:
            # 检查是否匹配已知失败模式
            matched_pattern = await self._anti_pattern_library.check_pattern(factor.expression)
            if matched_pattern:
                logger.warning(
                    f"因子匹配已知失败模式: {matched_pattern.pattern_id}, " f"失败次数: {matched_pattern.failure_count}"
                )
                # 不直接拒绝，但记录警告

            # 步骤1: 分析因子意义
            context.meaning_analysis = await self._analyze_factor_meaning(factor)
            logger.info(f"因子意义分析完成: {context.meaning_analysis.factor_type}")

            # 步骤2: 查找相似学术因子
            context.academic_matches = await self._find_similar_academic_factors(factor)
            logger.info(f"找到{len(context.academic_matches)}个相似学术因子")

            # 步骤3: 检测未来函数
            context.audit_result = await self._detect_future_functions(factor)
            if not context.audit_result.passed:
                return await self._handle_evolution_failure(
                    factor=factor,
                    failure_reason="检测到未来函数",
                    step=FailureStep.FUTURE_FUNCTION_DETECTION,
                    context=context,
                )
            logger.info("未来函数检测通过")

            # 步骤4: Arena双轨测试
            context.arena_result = await self._run_arena_test(factor)
            if not context.arena_result.passed:
                return await self._handle_evolution_failure(
                    factor=factor,
                    failure_reason="Arena测试未通过",
                    step=FailureStep.ARENA_TEST,
                    context=context,
                )
            logger.info(f"Arena测试通过: 夏普比率={context.arena_result.performance.sharpe_ratio:.4f}")

            # 步骤5: 分析表现差异
            context.performance_diff = await self._analyze_performance_diff(factor, context.arena_result)
            logger.info(f"表现差异分析完成: {context.performance_diff.diff_summary}")

            # 步骤6: 识别弱点
            context.weakness_report = await self._identify_weaknesses(context.performance_diff)
            logger.info(f"识别到{len(context.weakness_report.weaknesses)}个弱点")

            # 步骤7: 获取优化建议
            context.optimization_suggestions = await self._get_optimization_suggestions(factor, context.weakness_report)
            logger.info(f"获取到{len(context.optimization_suggestions.structural_changes)}个优化建议")

            # 步骤8: 预测优化后表现
            context.performance_prediction = await self._predict_optimized_performance(
                factor, context.optimization_suggestions
            )
            logger.info(f"预测夏普比率: {context.performance_prediction.predicted_sharpe:.4f}")

            # 步骤9: Z2H认证
            context.z2h_result = await self._submit_z2h_certification(factor, context)
            logger.info(f"Z2H认证结果: {context.z2h_result.status.value}")

            # 步骤10: 生成进化报告和基因胶囊
            evolution_report = await self._generate_evolution_report(context)
            gene_capsule = await self._create_gene_capsule(factor, context)

            # 更新演化树
            await self._update_evolution_tree(factor, gene_capsule, parent_capsule_id)

            logger.info(f"因子进化成功: {factor.factor_id}, 胶囊ID: {gene_capsule.capsule_id}")

            return EvolutionResult(
                success=True,
                gene_capsule=gene_capsule,
                evolution_report=evolution_report,
            )

        except EvolutionError as e:
            logger.error(f"进化流程错误: {e}")
            return await self._handle_evolution_failure(
                factor=factor,
                failure_reason=str(e),
                step=self._determine_failure_step(e),
                context=context,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"进化流程未知错误: {e}")
            return await self._handle_evolution_failure(
                factor=factor,
                failure_reason=f"未知错误: {str(e)}",
                step=FailureStep.REPORT_GENERATION,
                context=context,
            )

    async def _analyze_factor_meaning(self, factor: Factor) -> FactorMeaningAnalysis:
        """分析因子意义

        白皮书依据: 第五章 5.3.1 进化协同流程 - 步骤1

        调用Strategy_Analyzer分析因子的经济学含义、预期行为和风险因素。

        Args:
            factor: 待分析的因子

        Returns:
            FactorMeaningAnalysis: 因子意义分析结果

        Raises:
            FactorAnalysisError: 当分析失败时
        """
        try:
            if self._strategy_analyzer is not None:
                # 使用注入的策略分析器
                result = await self._strategy_analyzer.analyze_factor_meaning(factor)
                return result

            # 默认实现：基于表达式特征分析
            factor_type = self._infer_factor_type(factor.expression)
            economic_meaning = self._infer_economic_meaning(factor.expression, factor_type)
            expected_behavior = self._infer_expected_behavior(factor_type)
            risk_factors = self._identify_risk_factors(factor.expression)

            return FactorMeaningAnalysis(
                factor_type=factor_type,
                economic_meaning=economic_meaning,
                expected_behavior=expected_behavior,
                risk_factors=risk_factors,
                confidence=0.75,  # 默认置信度
            )

        except Exception as e:
            logger.error(f"因子意义分析失败: {e}")
            raise FactorAnalysisError(f"因子意义分析失败: {str(e)}") from e

    def _infer_factor_type(self, expression: str) -> str:
        """推断因子类型"""
        expr_lower = expression.lower()

        if "momentum" in expr_lower or "return" in expr_lower:  # pylint: disable=no-else-return
            return "动量因子"
        elif "volatility" in expr_lower or "std" in expr_lower:
            return "波动率因子"
        elif "volume" in expr_lower or "turnover" in expr_lower:
            return "流动性因子"
        elif "value" in expr_lower or "pe" in expr_lower or "pb" in expr_lower:
            return "价值因子"
        elif "size" in expr_lower or "market_cap" in expr_lower:
            return "规模因子"
        elif "quality" in expr_lower or "roe" in expr_lower:
            return "质量因子"
        else:
            return "复合因子"

    def _infer_economic_meaning(self, expression: str, factor_type: str) -> str:  # pylint: disable=unused-argument
        """推断经济学含义"""
        meanings = {
            "动量因子": "捕捉价格趋势延续效应，反映市场对信息的渐进反应",
            "波动率因子": "衡量价格波动程度，反映市场不确定性和风险水平",
            "流动性因子": "衡量交易活跃度，反映市场参与者的关注程度",
            "价值因子": "衡量资产相对价值，反映市场对基本面的定价",
            "规模因子": "衡量公司规模，反映规模效应和信息不对称",
            "质量因子": "衡量公司质量，反映盈利能力和财务健康度",
            "复合因子": "综合多个维度的信息，捕捉复杂的市场规律",
        }
        return meanings.get(factor_type, "综合多维度信息的复合因子")

    def _infer_expected_behavior(self, factor_type: str) -> str:
        """推断预期行为"""
        behaviors = {
            "动量因子": "高因子值股票预期继续上涨，低因子值股票预期继续下跌",
            "波动率因子": "低波动率股票预期提供更稳定的收益",
            "流动性因子": "高流动性股票预期有更低的交易成本",
            "价值因子": "低估值股票预期有更高的长期收益",
            "规模因子": "小市值股票预期有更高的风险溢价",
            "质量因子": "高质量股票预期有更稳定的收益",
            "复合因子": "综合多个因子的预期行为",
        }
        return behaviors.get(factor_type, "根据因子值进行股票排序和选择")

    def _identify_risk_factors(self, expression: str) -> List[str]:
        """识别风险因素"""
        risks = []
        expr_lower = expression.lower()

        if "/" in expression:
            risks.append("除法运算可能导致除零错误")
        if "**" in expression or "pow" in expr_lower:
            risks.append("幂运算可能导致数值溢出")
        if "delay" in expr_lower or "shift" in expr_lower:
            risks.append("延迟函数可能引入前视偏差")
        if "rank" in expr_lower:
            risks.append("排名函数对异常值敏感")
        if len(expression) > 100:
            risks.append("表达式过于复杂，可能存在过拟合风险")

        if not risks:
            risks.append("暂未发现明显风险因素")

        return risks

    async def _find_similar_academic_factors(
        self,
        factor: Factor,
    ) -> List[AcademicFactorMatch]:
        """查找相似学术因子

        白皮书依据: 第五章 5.3.1 进化协同流程 - 步骤2

        调用Scholar引擎查找学术文献中的相似因子。

        Args:
            factor: 待查找的因子

        Returns:
            List[AcademicFactorMatch]: 学术因子匹配列表

        Raises:
            AcademicSearchError: 当搜索失败时
        """
        try:
            if self._scholar_engine is not None:
                # 使用注入的学者引擎
                result = await self._scholar_engine.find_similar_factors(factor)
                return result

            # 默认实现：返回常见学术因子匹配
            factor_type = self._infer_factor_type(factor.expression)

            academic_factors = self._get_academic_factors_by_type(factor_type)

            return academic_factors

        except Exception as e:
            logger.error(f"学术因子搜索失败: {e}")
            raise AcademicSearchError(f"学术因子搜索失败: {str(e)}") from e

    def _get_academic_factors_by_type(self, factor_type: str) -> List[AcademicFactorMatch]:
        """根据因子类型获取学术因子"""
        academic_db = {
            "动量因子": [
                AcademicFactorMatch(
                    paper_title="Returns to Buying Winners and Selling Losers",
                    paper_authors=["Jegadeesh", "Titman"],
                    factor_name="12-1 Momentum",
                    similarity_score=0.85,
                    paper_url="https://doi.org/10.1111/j.1540-6261.1993.tb04702.x",
                ),
                AcademicFactorMatch(
                    paper_title="Momentum Strategies",
                    paper_authors=["Chan", "Jegadeesh", "Lakonishok"],
                    factor_name="Price Momentum",
                    similarity_score=0.78,
                    paper_url="https://doi.org/10.1111/j.1540-6261.1996.tb05222.x",
                ),
            ],
            "价值因子": [
                AcademicFactorMatch(
                    paper_title="The Cross-Section of Expected Stock Returns",
                    paper_authors=["Fama", "French"],
                    factor_name="Book-to-Market",
                    similarity_score=0.82,
                    paper_url="https://doi.org/10.1111/j.1540-6261.1992.tb04398.x",
                ),
            ],
            "规模因子": [
                AcademicFactorMatch(
                    paper_title="The Cross-Section of Expected Stock Returns",
                    paper_authors=["Fama", "French"],
                    factor_name="Size (SMB)",
                    similarity_score=0.80,
                    paper_url="https://doi.org/10.1111/j.1540-6261.1992.tb04398.x",
                ),
            ],
            "质量因子": [
                AcademicFactorMatch(
                    paper_title="Quality Minus Junk",
                    paper_authors=["Asness", "Frazzini", "Pedersen"],
                    factor_name="Quality Factor",
                    similarity_score=0.75,
                    paper_url="https://doi.org/10.2139/ssrn.2312432",
                ),
            ],
        }

        return academic_db.get(
            factor_type,
            [
                AcademicFactorMatch(
                    paper_title="A Five-Factor Asset Pricing Model",
                    paper_authors=["Fama", "French"],
                    factor_name="Multi-Factor",
                    similarity_score=0.65,
                    paper_url="https://doi.org/10.1016/j.jfineco.2014.10.010",
                ),
            ],
        )

    async def _detect_future_functions(self, factor: Factor) -> AuditResult:
        """检测未来函数

        白皮书依据: 第五章 5.3.1 进化协同流程 - 步骤3

        调用Devil魔鬼审计器检测因子是否使用了未来数据。

        Args:
            factor: 待检测的因子

        Returns:
            AuditResult: 审计结果

        Raises:
            AuditError: 当审计失败时
        """
        try:
            if self._devil_auditor is not None:
                # 使用注入的魔鬼审计器
                result = await self._devil_auditor.audit_factor(factor)
                return result

            # 默认实现：基于表达式检测
            issues = []
            suggestions = []
            future_function_detected = False

            expr_lower = factor.expression.lower()

            # 检测常见的未来函数模式
            future_patterns = [
                ("future", "使用了future函数，存在前视偏差"),
                ("lead", "使用了lead函数，存在前视偏差"),
                ("shift(-", "使用了负向shift，存在前视偏差"),
                ("delay(-", "使用了负向delay，存在前视偏差"),
            ]

            for pattern, issue in future_patterns:
                if pattern in expr_lower:
                    issues.append(issue)
                    future_function_detected = True

            # 生成建议
            if future_function_detected:
                suggestions.append("移除所有使用未来数据的函数")
                suggestions.append("使用正向延迟函数替代")
            else:
                suggestions.append("因子表达式通过未来函数检测")

            return AuditResult(
                passed=not future_function_detected,
                future_function_detected=future_function_detected,
                issues=issues,
                suggestions=suggestions,
                audit_date=datetime.now(),
                confidence=0.95 if not future_function_detected else 0.99,
            )

        except Exception as e:
            logger.error(f"未来函数检测失败: {e}")
            raise AuditError(f"未来函数检测失败: {str(e)}") from e

    async def _run_arena_test(self, factor: Factor) -> ArenaTestResult:
        """运行Arena双轨测试

        白皮书依据: 第五章 5.3.1 进化协同流程 - 步骤4

        调用Arena竞技场进行双轨测试（现实轨道和地狱轨道）。

        Args:
            factor: 待测试的因子

        Returns:
            ArenaTestResult: Arena测试结果

        Raises:
            ArenaTestError: 当测试失败时
        """
        try:
            if self._arena is not None:
                # 使用注入的Arena
                result = await self._arena.run_test(factor)
                return result

            # 默认实现：模拟Arena测试
            import random  # pylint: disable=import-outside-toplevel

            # 模拟测试结果
            reality_score = random.uniform(0.6, 0.9)
            hell_score = random.uniform(0.5, 0.85)
            cross_market_score = random.uniform(0.55, 0.88)
            sharpe = random.uniform(0.8, 2.5)
            max_dd = random.uniform(0.05, 0.25)
            win_rate = random.uniform(0.45, 0.65)
            profit_factor = random.uniform(1.2, 2.5)

            performance = ArenaPerformance(
                reality_track_score=reality_score,
                hell_track_score=hell_score,
                cross_market_score=cross_market_score,
                sharpe_ratio=sharpe,
                max_drawdown=max_dd,
                win_rate=win_rate,
                profit_factor=profit_factor,
                test_date=datetime.now(),
            )

            # 判断是否通过（综合得分 > 0.6）
            avg_score = (reality_score + hell_score + cross_market_score) / 3
            passed = avg_score > 0.6 and sharpe > 1.0

            return ArenaTestResult(
                test_id=str(uuid.uuid4()),
                factor_id=factor.factor_id,
                performance=performance,
                passed=passed,
                test_duration_seconds=random.uniform(10, 60),
                test_date=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Arena测试失败: {e}")
            raise ArenaTestError(f"Arena测试失败: {str(e)}") from e

    async def _analyze_performance_diff(
        self,
        factor: Factor,  # pylint: disable=unused-argument
        arena_result: ArenaTestResult,
    ) -> PerformanceDiffAnalysis:
        """分析表现差异

        白皮书依据: 第五章 5.3.1 进化协同流程 - 步骤5

        分析因子在不同轨道（现实、地狱、跨市场）的表现差异。

        Args:
            factor: 因子
            arena_result: Arena测试结果

        Returns:
            PerformanceDiffAnalysis: 表现差异分析结果
        """
        perf = arena_result.performance

        # 计算差异
        reality_hell_diff = perf.reality_track_score - perf.hell_track_score
        reality_cross_diff = perf.reality_track_score - perf.cross_market_score

        # 生成差异总结
        if abs(reality_hell_diff) < 0.1:
            diff_summary = "因子在现实轨道和地狱轨道表现一致，稳定性良好"
        elif reality_hell_diff > 0.1:
            diff_summary = "因子在地狱轨道表现下降，可能存在过拟合风险"
        else:
            diff_summary = "因子在地狱轨道表现更好，可能具有逆向特性"

        # 识别关键差异
        key_differences = []

        if abs(reality_hell_diff) > 0.15:
            key_differences.append(f"现实轨道与地狱轨道得分差异较大: {reality_hell_diff:.4f}")

        if abs(reality_cross_diff) > 0.15:
            key_differences.append(f"现实轨道与跨市场得分差异较大: {reality_cross_diff:.4f}")

        if perf.max_drawdown > 0.2:
            key_differences.append(f"最大回撤较高: {perf.max_drawdown:.2%}")

        if perf.win_rate < 0.5:
            key_differences.append(f"胜率偏低: {perf.win_rate:.2%}")

        if not key_differences:
            key_differences.append("各项指标表现均衡")

        return PerformanceDiffAnalysis(
            reality_track_score=perf.reality_track_score,
            hell_track_score=perf.hell_track_score,
            cross_market_score=perf.cross_market_score,
            diff_summary=diff_summary,
            key_differences=key_differences,
        )

    async def _identify_weaknesses(
        self,
        diff_analysis: PerformanceDiffAnalysis,
    ) -> WeaknessReport:
        """识别弱点和改进方向

        白皮书依据: 第五章 5.3.1 进化协同流程 - 步骤6

        基于表现差异分析识别因子的弱点和改进方向。

        Args:
            diff_analysis: 表现差异分析结果

        Returns:
            WeaknessReport: 弱点报告
        """
        weaknesses = []
        improvement_directions = []
        priority_ranking = []

        # 分析各轨道得分
        if diff_analysis.hell_track_score < 0.6:
            weaknesses.append("地狱轨道表现不佳")
            improvement_directions.append("增强因子在极端市场条件下的稳定性")
            priority_ranking.append(("地狱轨道表现", 1))

        if diff_analysis.cross_market_score < 0.6:
            weaknesses.append("跨市场适应性不足")
            improvement_directions.append("提高因子的市场普适性")
            priority_ranking.append(("跨市场适应性", 2))

        if diff_analysis.reality_track_score < 0.7:
            weaknesses.append("现实轨道表现有待提升")
            improvement_directions.append("优化因子参数以提高实际表现")
            priority_ranking.append(("现实轨道表现", 3))

        # 分析差异
        reality_hell_diff = diff_analysis.reality_track_score - diff_analysis.hell_track_score
        if reality_hell_diff > 0.2:
            weaknesses.append("可能存在过拟合风险")
            improvement_directions.append("简化因子结构，减少参数数量")
            priority_ranking.append(("过拟合风险", 1))

        if not weaknesses:
            weaknesses.append("暂未发现明显弱点")
            improvement_directions.append("继续保持当前策略方向")

        return WeaknessReport(
            weaknesses=weaknesses,
            improvement_directions=improvement_directions,
            priority_ranking=priority_ranking,
        )

    async def _get_optimization_suggestions(
        self,
        factor: Factor,
        weakness_report: WeaknessReport,
    ) -> OptimizationSuggestions:
        """获取超参数优化建议

        白皮书依据: 第五章 5.3.1 进化协同流程 - 步骤7

        调用Commander引擎获取超参数优化建议。

        Args:
            factor: 因子
            weakness_report: 弱点报告

        Returns:
            OptimizationSuggestions: 优化建议
        """
        try:
            if self._commander_engine is not None:
                # 使用注入的Commander引擎
                result = await self._commander_engine.get_optimization_suggestions(factor, weakness_report)
                return result

            # 默认实现：基于弱点生成建议
            hyperparameter_changes = {}
            structural_changes = []
            expected_improvement = 0.0

            for weakness in weakness_report.weaknesses:
                if "过拟合" in weakness:
                    hyperparameter_changes["regularization"] = 0.1
                    structural_changes.append("增加正则化项")
                    expected_improvement += 0.05

                if "地狱轨道" in weakness:
                    hyperparameter_changes["volatility_adjustment"] = 0.8
                    structural_changes.append("增加波动率调整因子")
                    expected_improvement += 0.08

                if "跨市场" in weakness:
                    hyperparameter_changes["market_neutral"] = True
                    structural_changes.append("增加市场中性化处理")
                    expected_improvement += 0.06

            if not structural_changes:
                structural_changes.append("保持当前结构，微调参数")
                expected_improvement = 0.02

            return OptimizationSuggestions(
                hyperparameter_changes=hyperparameter_changes,
                structural_changes=structural_changes,
                expected_improvement=min(expected_improvement, 0.3),  # 最大30%改进
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"获取优化建议失败: {e}")
            return OptimizationSuggestions(
                hyperparameter_changes={},
                structural_changes=["建议人工审查"],
                expected_improvement=0.0,
            )

    async def _predict_optimized_performance(
        self,
        factor: Factor,  # pylint: disable=unused-argument
        suggestions: OptimizationSuggestions,
    ) -> PerformancePrediction:
        """预测优化后表现

        白皮书依据: 第五章 5.3.1 进化协同流程 - 步骤8

        基于优化建议预测优化后的因子表现。

        Args:
            factor: 因子
            suggestions: 优化建议

        Returns:
            PerformancePrediction: 性能预测
        """

        # 基础预测值
        base_sharpe = 1.5
        base_max_dd = 0.15
        base_win_rate = 0.55

        # 根据预期改进调整
        improvement = suggestions.expected_improvement

        predicted_sharpe = base_sharpe * (1 + improvement)
        predicted_max_dd = base_max_dd * (1 - improvement * 0.5)
        predicted_win_rate = min(base_win_rate * (1 + improvement * 0.3), 0.75)

        # 置信区间
        confidence_lower = predicted_sharpe * 0.8
        confidence_upper = predicted_sharpe * 1.2

        return PerformancePrediction(
            predicted_sharpe=predicted_sharpe,
            predicted_max_drawdown=predicted_max_dd,
            predicted_win_rate=predicted_win_rate,
            confidence_interval=(confidence_lower, confidence_upper),
        )

    async def _submit_z2h_certification(
        self,
        factor: Factor,
        context: EvolutionContext,
    ) -> Z2HCertificationResult:
        """提交Z2H认证

        白皮书依据: 第五章 5.3.1 进化协同流程 - 步骤9

        调用Z2H认证器进行因子认证。

        Args:
            factor: 因子
            context: 进化上下文

        Returns:
            Z2HCertificationResult: Z2H认证结果

        Raises:
            Z2HCertificationError: 当认证失败时
        """
        try:
            if self._z2h_certifier is not None:
                # 使用注入的Z2H认证器
                result = await self._z2h_certifier.certify(factor, context)
                return result

            # 默认实现：基于Arena表现判断认证等级
            if context.arena_result is None:
                raise Z2HCertificationError("缺少Arena测试结果")

            perf = context.arena_result.performance
            avg_score = (perf.reality_track_score + perf.hell_track_score + perf.cross_market_score) / 3

            # 判断认证等级
            if avg_score >= 0.85 and perf.sharpe_ratio >= 2.0:
                status = Z2HStampStatus.PLATINUM
                certification_level = "铂金级"
            elif avg_score >= 0.75 and perf.sharpe_ratio >= 1.5:
                status = Z2HStampStatus.GOLD
                certification_level = "黄金级"
            elif avg_score >= 0.65 and perf.sharpe_ratio >= 1.0:
                status = Z2HStampStatus.SILVER
                certification_level = "白银级"
            else:
                status = Z2HStampStatus.REJECTED
                certification_level = None

            # 设置过期日期（1年后）
            from datetime import timedelta  # pylint: disable=import-outside-toplevel

            expiry_date = datetime.now() + timedelta(days=365) if status != Z2HStampStatus.REJECTED else None

            remarks = f"综合得分: {avg_score:.4f}, 夏普比率: {perf.sharpe_ratio:.4f}"

            return Z2HCertificationResult(
                certification_id=str(uuid.uuid4()),
                factor_id=factor.factor_id,
                status=status,
                certification_level=certification_level,
                certification_date=datetime.now(),
                expiry_date=expiry_date,
                remarks=remarks,
            )

        except Exception as e:
            logger.error(f"Z2H认证失败: {e}")
            raise Z2HCertificationError(f"Z2H认证失败: {str(e)}") from e

    async def _generate_evolution_report(
        self,
        context: EvolutionContext,
    ) -> EvolutionReport:
        """生成完整进化报告

        白皮书依据: 第五章 5.3.1 进化协同流程 - 步骤10

        汇总所有分析结果生成完整的进化报告。

        Args:
            context: 进化上下文

        Returns:
            EvolutionReport: 进化报告

        Raises:
            ValueError: 当上下文数据不完整时
        """
        # 验证上下文完整性
        if context.meaning_analysis is None:
            raise ValueError("缺少因子意义分析")
        if context.audit_result is None:
            raise ValueError("缺少审计结果")
        if context.arena_result is None:
            raise ValueError("缺少Arena测试结果")
        if context.performance_diff is None:
            raise ValueError("缺少表现差异分析")
        if context.weakness_report is None:
            raise ValueError("缺少弱点报告")
        if context.optimization_suggestions is None:
            raise ValueError("缺少优化建议")
        if context.performance_prediction is None:
            raise ValueError("缺少性能预测")
        if context.z2h_result is None:
            raise ValueError("缺少Z2H认证结果")

        report = EvolutionReport(
            report_id=str(uuid.uuid4()),
            factor_id=context.factor.factor_id,
            capsule_id="",  # 将在创建胶囊后更新
            meaning_analysis=context.meaning_analysis,
            academic_matches=context.academic_matches,
            audit_result=context.audit_result,
            arena_result=context.arena_result,
            performance_diff=context.performance_diff,
            weakness_report=context.weakness_report,
            optimization_suggestions=context.optimization_suggestions,
            performance_prediction=context.performance_prediction,
            z2h_result=context.z2h_result,
            created_at=datetime.now(),
        )

        logger.info(f"生成进化报告: {report.report_id}")
        return report

    async def _create_gene_capsule(
        self,
        factor: Factor,
        context: EvolutionContext,
    ) -> GeneCapsule:
        """创建基因胶囊

        白皮书依据: 第五章 5.3.2 基因胶囊

        封装因子的完整元数据创建基因胶囊。

        Args:
            factor: 因子
            context: 进化上下文

        Returns:
            GeneCapsule: 创建的基因胶囊
        """
        # 构建29维度分析报告
        analysis_report_29d = self._build_29d_analysis_report(context)

        # 构建进化历史
        evolution_history = []
        if context.parent_capsule_id:
            # 获取父代胶囊的适应度
            parent_capsule = await self._gene_capsule_manager.get_capsule(context.parent_capsule_id)
            parent_fitness = 0.0
            if parent_capsule:
                parent_fitness = parent_capsule.arena_performance.sharpe_ratio

            evolution_record = EvolutionRecord(
                record_id=str(uuid.uuid4()),
                parent_capsule_id=context.parent_capsule_id,
                mutation_type=MutationType.OPTIMIZATION,
                mutation_description="基于优化建议的参数调整",
                fitness_before=parent_fitness,
                fitness_after=context.arena_result.performance.sharpe_ratio if context.arena_result else 0.0,
                timestamp=datetime.now(),
            )
            evolution_history.append(evolution_record)
        else:
            # 初始创建
            evolution_record = EvolutionRecord(
                record_id=str(uuid.uuid4()),
                parent_capsule_id=None,
                mutation_type=MutationType.INITIAL,
                mutation_description="初始因子创建",
                fitness_before=0.0,
                fitness_after=context.arena_result.performance.sharpe_ratio if context.arena_result else 0.0,
                timestamp=datetime.now(),
            )
            evolution_history.append(evolution_record)

        # 确定家族ID
        family_id = None
        if context.parent_capsule_id:
            parent_capsule = await self._gene_capsule_manager.get_capsule(context.parent_capsule_id)
            if parent_capsule:
                family_id = parent_capsule.family_id

        # 创建基因胶囊
        capsule = await self._gene_capsule_manager.create_capsule(
            strategy_code=factor.expression,
            parameter_config=factor.parameters,
            analysis_report=analysis_report_29d,
            arena_performance=context.arena_result.performance,
            audit_result=context.audit_result,
            evolution_history=evolution_history,
            z2h_status=context.z2h_result.status,
            family_id=family_id,
        )

        logger.info(f"创建基因胶囊: {capsule.capsule_id}")
        return capsule

    def _build_29d_analysis_report(self, context: EvolutionContext) -> Dict[str, Any]:
        """构建29维度分析报告"""
        report = {
            "factor_meaning": context.meaning_analysis.to_dict() if context.meaning_analysis else {},
            "academic_matches": [m.to_dict() for m in context.academic_matches],
            "audit_result": context.audit_result.to_dict() if context.audit_result else {},
            "arena_performance": context.arena_result.performance.to_dict() if context.arena_result else {},
            "performance_diff": context.performance_diff.to_dict() if context.performance_diff else {},
            "weakness_report": context.weakness_report.to_dict() if context.weakness_report else {},
            "optimization_suggestions": (
                context.optimization_suggestions.to_dict() if context.optimization_suggestions else {}
            ),
            "performance_prediction": (
                context.performance_prediction.to_dict() if context.performance_prediction else {}
            ),
            "z2h_certification": context.z2h_result.to_dict() if context.z2h_result else {},
        }
        return report

    async def _update_evolution_tree(
        self,
        factor: Factor,
        capsule: GeneCapsule,
        parent_capsule_id: Optional[str],
    ) -> None:
        """更新演化树

        白皮书依据: 第五章 5.3.3 演化树

        将新创建的基因胶囊添加到演化树中。

        Args:
            factor: 因子
            capsule: 基因胶囊
            parent_capsule_id: 父代胶囊ID
        """
        tree = await self.get_or_create_evolution_tree(capsule.family_id)

        fitness = capsule.arena_performance.sharpe_ratio

        if parent_capsule_id:
            # 查找父节点
            parent_node_id = None
            for node_id, node in tree.nodes.items():
                if node.capsule_id == parent_capsule_id:
                    parent_node_id = node_id
                    break

            if parent_node_id:
                # 添加子节点
                await tree.add_child(
                    parent_node_id=parent_node_id,
                    capsule_id=capsule.capsule_id,
                    strategy_name=factor.name,
                    fitness=fitness,
                    mutation_type=MutationType.OPTIMIZATION,
                    mutation_description="基于优化建议的参数调整",
                )
            else:
                # 父节点不存在，创建为根节点
                if tree.root_node_id is None:
                    await tree.create_root(
                        capsule_id=capsule.capsule_id,
                        strategy_name=factor.name,
                        fitness=fitness,
                    )
        else:
            # 创建根节点
            if tree.root_node_id is None:
                await tree.create_root(
                    capsule_id=capsule.capsule_id,
                    strategy_name=factor.name,
                    fitness=fitness,
                )

        logger.debug(f"更新演化树: 节点数={tree.node_count()}")

    async def _handle_evolution_failure(
        self,
        factor: Factor,
        failure_reason: str,
        step: FailureStep,
        context: Optional[EvolutionContext] = None,  # pylint: disable=unused-argument
    ) -> EvolutionResult:
        """处理进化失败

        白皮书依据: 第五章 5.3.1 进化协同流程 - 需求1.11

        记录失败原因并更新反向黑名单库。

        Args:
            factor: 因子
            failure_reason: 失败原因
            step: 失败步骤
            context: 进化上下文（可选）

        Returns:
            EvolutionResult: 失败的进化结果
        """
        logger.warning(f"进化失败: {factor.factor_id}, 原因: {failure_reason}, 步骤: {step.value}")

        # 记录到反向黑名单库
        await self._anti_pattern_library.record_failure(
            factor_expression=factor.expression,
            failure_reason=failure_reason,
            failure_step=step,
        )

        return EvolutionResult(
            success=False,
            failure_reason=failure_reason,
            failure_step=step,
        )

    def _determine_failure_step(self, error: Exception) -> FailureStep:
        """根据异常类型确定失败步骤"""
        if isinstance(error, FactorAnalysisError):  # pylint: disable=no-else-return
            return FailureStep.FACTOR_ANALYSIS
        elif isinstance(error, AcademicSearchError):
            return FailureStep.ACADEMIC_SEARCH
        elif isinstance(error, AuditError):
            return FailureStep.FUTURE_FUNCTION_DETECTION
        elif isinstance(error, ArenaTestError):
            return FailureStep.ARENA_TEST
        elif isinstance(error, Z2HCertificationError):
            return FailureStep.Z2H_CERTIFICATION
        else:
            return FailureStep.REPORT_GENERATION

    async def get_evolution_statistics(self) -> Dict[str, Any]:
        """获取进化统计信息

        Returns:
            Dict: 统计信息
        """
        capsule_count = await self._gene_capsule_manager.count_capsules()
        pattern_stats = await self._anti_pattern_library.get_statistics()

        tree = await self.get_or_create_evolution_tree()

        return {
            "total_capsules": capsule_count,
            "evolution_tree": {
                "node_count": tree.node_count(),
                "edge_count": tree.edge_count(),
                "max_generation": tree.max_generation(),
            },
            "anti_patterns": pattern_stats,
        }

    async def get_elite_capsules(self, limit: int = 10) -> List[GeneCapsule]:
        """获取精英基因胶囊

        Args:
            limit: 返回数量限制

        Returns:
            List[GeneCapsule]: 精英基因胶囊列表
        """
        # 获取铂金和黄金级别的胶囊
        platinum_capsules = await self._gene_capsule_manager.get_capsules_by_z2h_status(Z2HStampStatus.PLATINUM)
        gold_capsules = await self._gene_capsule_manager.get_capsules_by_z2h_status(Z2HStampStatus.GOLD)

        # 合并并按夏普比率排序
        all_elite = platinum_capsules + gold_capsules
        all_elite.sort(key=lambda c: c.arena_performance.sharpe_ratio, reverse=True)

        return all_elite[:limit]

    async def analyze_family_evolution(
        self,
        family_id: str,
    ) -> Dict[str, Any]:
        """分析家族进化历程

        Args:
            family_id: 家族ID

        Returns:
            Dict: 家族进化分析结果
        """
        # 获取家族所有胶囊
        capsules = await self._gene_capsule_manager.get_capsules_by_family(family_id)

        if not capsules:
            return {"error": f"未找到家族: {family_id}"}

        # 分析进化趋势
        fitness_history = [
            {
                "capsule_id": c.capsule_id,
                "fitness": c.arena_performance.sharpe_ratio,
                "created_at": c.created_at.isoformat(),
                "z2h_status": c.z2h_stamp_status.value,
            }
            for c in sorted(capsules, key=lambda x: x.created_at)
        ]

        # 计算进化效率
        if len(fitness_history) >= 2:
            first_fitness = fitness_history[0]["fitness"]
            last_fitness = fitness_history[-1]["fitness"]
            improvement = (last_fitness - first_fitness) / first_fitness if first_fitness > 0 else 0
        else:
            improvement = 0

        return {
            "family_id": family_id,
            "total_members": len(capsules),
            "fitness_history": fitness_history,
            "improvement_rate": improvement,
            "best_fitness": max(c.arena_performance.sharpe_ratio for c in capsules),
            "worst_fitness": min(c.arena_performance.sharpe_ratio for c in capsules),
        }
