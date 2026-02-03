"""Z2H认证系统 v2.0

白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统

本模块实现升级版的Z2H认证系统，集成完整的斯巴达Arena四层验证体系。

核心功能：
- 集成Arena四层验证结果
- 评定认证等级（PLATINUM/GOLD/SILVER）
- 生成完整的Z2H基因胶囊
- 确定资金配置规则
- 管理认证状态
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from .capital_allocation_rules_determiner import CapitalAllocationRulesDeterminer
from .certification_level_evaluator import CertificationLevelEvaluator
from .z2h_data_models import (
    CapitalAllocationRules,
    CertificationEligibility,
    CertificationLevel,
    CertificationStatus,
    CertifiedStrategy,
    SimulationResult,
    Z2HGeneCapsule,
)


class Z2HCertificationV2:
    """Z2H认证系统 v2.0

    白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统

    核心功能：
    - 集成Arena四层验证结果
    - 评定认证等级（PLATINUM/GOLD/SILVER）
    - 生成完整的Z2H基因胶囊
    - 确定资金配置规则
    - 管理认证状态

    Attributes:
        level_evaluator: 认证等级评估器
        capital_rules_determiner: 资金配置规则确定器
        certified_strategies: 已认证策略字典
    """

    def __init__(
        self,
        level_evaluator: Optional[CertificationLevelEvaluator] = None,
        capital_rules_determiner: Optional[CapitalAllocationRulesDeterminer] = None,
    ):
        """初始化Z2H认证系统v2.0

        Args:
            level_evaluator: 认证等级评估器（可选）
            capital_rules_determiner: 资金配置规则确定器（可选）
        """
        self.level_evaluator = level_evaluator or CertificationLevelEvaluator()
        self.capital_rules_determiner = capital_rules_determiner or CapitalAllocationRulesDeterminer()

        # 已认证策略存储
        self.certified_strategies: Dict[str, CertifiedStrategy] = {}

        logger.info("Z2HCertificationV2初始化完成")

    async def evaluate_certification_eligibility(
        self,
        arena_overall_score: float,
        arena_layer_results: Dict[str, Dict[str, Any]],
        simulation_result: SimulationResult,
    ) -> CertificationEligibility:
        """评估认证资格

        白皮书依据: Requirement 1.1-1.5

        集成Arena四层验证结果和模拟盘验证结果，评估策略是否符合认证条件。

        Args:
            arena_overall_score: Arena综合评分
            arena_layer_results: Arena四层验证详细结果
            simulation_result: 模拟盘验证结果

        Returns:
            CertificationEligibility: 认证资格评估结果

        Raises:
            ValueError: 当输入参数无效时
        """
        logger.info("开始评估认证资格")

        # 验证输入
        if not 0.0 <= arena_overall_score <= 1.0:
            raise ValueError(f"Arena综合评分必须在[0, 1]范围内: {arena_overall_score}")

        if not arena_layer_results:
            raise ValueError("Arena层级结果不能为空")

        if not simulation_result:
            raise ValueError("模拟盘结果不能为空")

        # 评估认证等级
        # 提取模拟盘指标
        simulation_metrics = {
            "sharpe_ratio": simulation_result.overall_metrics.get("sharpe_ratio", 0.0),
            "max_drawdown": simulation_result.overall_metrics.get("max_drawdown", 1.0),
            "win_rate": simulation_result.overall_metrics.get("win_rate", 0.0),
        }

        level_result = self.level_evaluator.evaluate_level(
            arena_overall_score=arena_overall_score,
            arena_layer_results=arena_layer_results,
            simulation_passed=simulation_result.passed,
            simulation_metrics=simulation_metrics,
        )

        # 计算模拟盘综合评分
        simulation_score = self._calculate_simulation_score(simulation_result)

        # 收集通过和失败的标准
        passed_criteria = []
        failed_criteria = []
        failure_reasons = []

        # Arena标准
        if level_result.meets_requirements:
            passed_criteria.append(f"Arena综合评分{arena_overall_score:.2f}达标")
            passed_criteria.append(f"Arena通过{level_result.passed_layers}/4层")
        else:
            failed_criteria.append(f"Arena综合评分{arena_overall_score:.2f}不达标")
            if level_result.failed_layers:
                failed_criteria.append(f"Arena未通过层级: {', '.join(level_result.failed_layers)}")
                failure_reasons.append(level_result.evaluation_reason)

        # 模拟盘标准
        if simulation_result.passed:
            passed_criteria.append(f"模拟盘通过{simulation_result.passed_criteria_count}/10项标准")
        else:
            failed_criteria.append(f"模拟盘仅通过{simulation_result.passed_criteria_count}/10项标准")
            failure_reasons.extend(simulation_result.failed_criteria)

        # 判断是否符合认证条件
        eligible = level_result.meets_requirements and simulation_result.passed

        eligibility = CertificationEligibility(
            eligible=eligible,
            certification_level=level_result.certification_level if eligible else CertificationLevel.NONE,
            arena_score=arena_overall_score,
            simulation_score=simulation_score,
            passed_criteria=passed_criteria,
            failed_criteria=failed_criteria,
            failure_reasons=failure_reasons,
        )

        logger.info(f"认证资格评估完成 - " f"符合条件: {eligible}, " f"等级: {eligibility.certification_level.value}")

        return eligibility

    async def determine_certification_level(
        self,
        arena_overall_score: float,
        arena_layer_results: Dict[str, Dict[str, Any]],
        simulation_result: SimulationResult,
    ) -> CertificationLevel:
        """确定认证等级

        白皮书依据: Requirement 4.1-4.6

        根据Arena综合评分和各层表现确定认证等级：
        - PLATINUM: Arena≥0.90, 所有层级优秀
        - GOLD: Arena≥0.80, 所有层级良好
        - SILVER: Arena≥0.75, 所有层级合格

        Args:
            arena_overall_score: Arena综合评分
            arena_layer_results: Arena四层验证详细结果
            simulation_result: 模拟盘验证结果

        Returns:
            CertificationLevel: 认证等级
        """
        logger.info("确定认证等级")

        # 提取模拟盘指标
        simulation_metrics = {
            "sharpe_ratio": simulation_result.overall_metrics.get("sharpe_ratio", 0.0),
            "max_drawdown": simulation_result.overall_metrics.get("max_drawdown", 1.0),
            "win_rate": simulation_result.overall_metrics.get("win_rate", 0.0),
        }

        level_result = self.level_evaluator.evaluate_level(
            arena_overall_score=arena_overall_score,
            arena_layer_results=arena_layer_results,
            simulation_passed=simulation_result.passed,
            simulation_metrics=simulation_metrics,
        )

        return level_result.certification_level

    async def determine_capital_allocation_rules(
        self, certification_level: CertificationLevel, simulation_result: SimulationResult
    ) -> CapitalAllocationRules:
        """确定资金配置规则

        白皮书依据: Requirement 5.1-5.8

        根据认证等级和模拟盘验证结果确定资金配置规则。

        Args:
            certification_level: 认证等级
            simulation_result: 模拟盘验证结果

        Returns:
            CapitalAllocationRules: 资金配置规则
        """
        logger.info(f"确定资金配置规则 - 等级: {certification_level.value}")

        rules = self.capital_rules_determiner.determine_rules(
            certification_level=certification_level,
            best_tier=simulation_result.best_tier,
            simulation_metrics=simulation_result.overall_metrics,
            strategy_characteristics=None,  # 可选：从simulation_result提取
        )

        return rules

    async def generate_z2h_gene_capsule(  # pylint: disable=too-many-positional-arguments
        self,
        strategy_id: str,
        strategy_name: str,
        strategy_type: str,
        source_factors: List[str],
        creation_date: datetime,
        certification_level: CertificationLevel,
        arena_overall_score: float,
        arena_layer_results: Dict[str, Dict[str, Any]],
        simulation_result: SimulationResult,
        capital_rules: CapitalAllocationRules,
    ) -> Z2HGeneCapsule:
        """生成Z2H基因胶囊

        白皮书依据: Requirement 3.1-3.8

        生成包含完整策略元数据和认证信息的Z2H基因胶囊。

        Args:
            strategy_id: 策略ID
            strategy_name: 策略名称
            strategy_type: 策略类型
            source_factors: 源因子列表
            creation_date: 策略创建日期
            certification_level: 认证等级
            arena_overall_score: Arena综合评分
            arena_layer_results: Arena四层验证详细结果
            simulation_result: 模拟盘验证结果
            capital_rules: 资金配置规则

        Returns:
            Z2HGeneCapsule: Z2H基因胶囊
        """
        logger.info(f"生成Z2H基因胶囊 - 策略: {strategy_name}")

        # 提取Arena失败层级
        arena_failed_layers = [
            layer_name for layer_name, layer_data in arena_layer_results.items() if not layer_data.get("passed", False)
        ]

        # 提取模拟盘各档位结果
        simulation_tier_results = {}
        for tier, tier_result in simulation_result.tier_results.items():
            simulation_tier_results[tier.value] = {
                "initial_capital": tier_result.initial_capital,
                "final_capital": tier_result.final_capital,
                "total_return": tier_result.total_return,
                "sharpe_ratio": tier_result.sharpe_ratio,
                "max_drawdown": tier_result.max_drawdown,
                "win_rate": tier_result.win_rate,
            }

        # 从模拟盘结果提取交易特征（简化）
        best_tier_result = simulation_result.tier_results[simulation_result.best_tier]

        gene_capsule = Z2HGeneCapsule(
            # 基本信息
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            strategy_type=strategy_type,
            source_factors=source_factors,
            creation_date=creation_date,
            certification_date=datetime.now(),
            certification_level=certification_level,
            # Arena验证结果
            arena_overall_score=arena_overall_score,
            arena_layer_results=arena_layer_results,
            arena_passed_layers=4 - len(arena_failed_layers),
            arena_failed_layers=arena_failed_layers,
            # 模拟盘验证结果
            simulation_duration_days=simulation_result.duration_days,
            simulation_tier_results=simulation_tier_results,
            simulation_best_tier=simulation_result.best_tier,
            simulation_metrics=simulation_result.overall_metrics,
            # 资金配置规则
            max_allocation_ratio=capital_rules.max_allocation_ratio,
            recommended_capital_scale={
                "min": capital_rules.min_capital,
                "max": capital_rules.max_capital,
                "optimal": capital_rules.optimal_capital,
            },
            optimal_trade_size=capital_rules.optimal_capital / 10,  # 简化：1/10仓位
            liquidity_requirements={"buffer": capital_rules.liquidity_buffer},
            market_impact_analysis={"estimated_impact": 0.001},  # 简化
            # 交易特征（从最佳档位提取）
            avg_holding_period_days=5.0,  # 简化
            turnover_rate=2.0,  # 简化
            avg_position_count=10,  # 简化
            sector_distribution={},  # 简化
            market_cap_preference="mid_cap",  # 简化
            # 风险分析
            var_95=best_tier_result.var_95,
            expected_shortfall=best_tier_result.var_95 * 1.3,  # 简化估算
            max_drawdown=best_tier_result.max_drawdown,
            drawdown_duration_days=30,  # 简化
            volatility=simulation_result.risk_metrics.get("volatility", 0.2),
            beta=1.0,  # 简化
            market_correlation=0.5,  # 简化
            # 市场环境表现
            bull_market_performance=simulation_result.market_environment_performance.get("bull_market", {}),
            bear_market_performance=simulation_result.market_environment_performance.get("bear_market", {}),
            sideways_market_performance=simulation_result.market_environment_performance.get("sideways_market", {}),
            high_volatility_performance={},  # 简化
            low_volatility_performance={},  # 简化
            market_adaptability_score=0.8,  # 简化
            # 使用建议
            optimal_deployment_timing=["bull_market", "sideways_market"],
            risk_management_rules={"max_drawdown_stop": 0.15},
            monitoring_indicators=["sharpe_ratio", "max_drawdown", "win_rate"],
            exit_conditions=["drawdown > 15%", "sharpe < 1.0"],
            portfolio_strategy_suggestions=["适合作为核心持仓", "建议配置10-20%资金"],
        )

        logger.info(f"Z2H基因胶囊生成完成 - 策略: {strategy_name}")

        return gene_capsule

    async def grant_certification(self, gene_capsule: Z2HGeneCapsule) -> CertifiedStrategy:
        """颁发Z2H认证

        白皮书依据: Requirement 7.2

        Args:
            gene_capsule: Z2H基因胶囊

        Returns:
            CertifiedStrategy: 已认证策略
        """
        logger.info(f"颁发Z2H认证 - 策略: {gene_capsule.strategy_name}")

        certified_strategy = CertifiedStrategy(
            strategy_id=gene_capsule.strategy_id,
            strategy_name=gene_capsule.strategy_name,
            certification_level=gene_capsule.certification_level,
            gene_capsule=gene_capsule,
            certification_date=gene_capsule.certification_date,
            status=CertificationStatus.CERTIFIED,
            last_review_date=None,
            next_review_date=self._calculate_next_review_date(gene_capsule.certification_date),
        )

        # 保存到已认证策略字典
        self.certified_strategies[gene_capsule.strategy_id] = certified_strategy

        logger.info(
            f"Z2H认证颁发成功 - "
            f"策略: {gene_capsule.strategy_name}, "
            f"等级: {gene_capsule.certification_level.value}, "
            f"日期: {gene_capsule.certification_date.strftime('%Y-%m-%d')}"
        )

        return certified_strategy

    async def revoke_certification(self, strategy_id: str, reason: str) -> bool:
        """撤销Z2H认证

        白皮书依据: Requirement 7.3

        Args:
            strategy_id: 策略ID
            reason: 撤销原因

        Returns:
            bool: 是否撤销成功
        """
        if strategy_id not in self.certified_strategies:
            logger.warning(f"策略不存在或未认证: {strategy_id}")
            return False

        certified_strategy = self.certified_strategies[strategy_id]

        logger.warning(f"撤销Z2H认证 - " f"策略: {certified_strategy.strategy_name}, " f"原因: {reason}")

        # 更新状态
        certified_strategy.status = CertificationStatus.REVOKED
        certified_strategy.last_review_date = datetime.now()

        # 可以选择从字典中移除或保留记录
        # del self.certified_strategies[strategy_id]

        return True

    async def downgrade_certification(self, strategy_id: str, new_level: CertificationLevel, reason: str) -> bool:
        """降级认证等级

        白皮书依据: Requirement 7.4

        Args:
            strategy_id: 策略ID
            new_level: 新的认证等级
            reason: 降级原因

        Returns:
            bool: 是否降级成功
        """
        if strategy_id not in self.certified_strategies:
            logger.warning(f"策略不存在或未认证: {strategy_id}")
            return False

        certified_strategy = self.certified_strategies[strategy_id]
        old_level = certified_strategy.certification_level

        # 定义等级顺序（从高到低）
        level_order = {
            CertificationLevel.PLATINUM: 3,
            CertificationLevel.GOLD: 2,
            CertificationLevel.SILVER: 1,
            CertificationLevel.NONE: 0,
        }

        # 比较等级
        if level_order[new_level] >= level_order[old_level]:
            logger.warning(f"新等级不低于当前等级，无法降级: {new_level.value} >= {old_level.value}")
            return False

        logger.warning(
            f"降级认证等级 - "
            f"策略: {certified_strategy.strategy_name}, "
            f"从 {old_level.value} 降至 {new_level.value}, "
            f"原因: {reason}"
        )

        # 更新等级和状态
        certified_strategy.certification_level = new_level
        certified_strategy.gene_capsule.certification_level = new_level
        certified_strategy.status = CertificationStatus.DOWNGRADED
        certified_strategy.last_review_date = datetime.now()

        return True

    def get_certified_strategy(self, strategy_id: str) -> Optional[CertifiedStrategy]:
        """获取已认证策略

        Args:
            strategy_id: 策略ID

        Returns:
            CertifiedStrategy: 已认证策略，如果不存在返回None
        """
        return self.certified_strategies.get(strategy_id)

    def list_certified_strategies(
        self, certification_level: Optional[CertificationLevel] = None, status: Optional[CertificationStatus] = None
    ) -> List[CertifiedStrategy]:
        """列出已认证策略

        Args:
            certification_level: 筛选认证等级（可选）
            status: 筛选认证状态（可选）

        Returns:
            List[CertifiedStrategy]: 已认证策略列表
        """
        strategies = list(self.certified_strategies.values())

        if certification_level:
            strategies = [s for s in strategies if s.certification_level == certification_level]

        if status:
            strategies = [s for s in strategies if s.status == status]

        return strategies

    def _calculate_simulation_score(self, simulation_result: SimulationResult) -> float:
        """计算模拟盘综合评分

        Args:
            simulation_result: 模拟盘验证结果

        Returns:
            float: 综合评分（0-1）
        """
        # 简化：基于通过标准数量
        return simulation_result.passed_criteria_count / 10.0

    def _calculate_next_review_date(self, certification_date: datetime) -> datetime:
        """计算下次复核日期

        Args:
            certification_date: 认证日期

        Returns:
            datetime: 下次复核日期（1个月后）
        """
        from datetime import timedelta  # pylint: disable=import-outside-toplevel

        return certification_date + timedelta(days=30)


class CertificationError(Exception):
    """认证异常"""
