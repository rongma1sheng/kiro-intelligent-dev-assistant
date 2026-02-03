"""
MIA系统四档资金分层Z2H认证系统

白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统 - 四档分层认证
版本: v1.6.0
作者: MIA Team
日期: 2026-01-18

核心理念: 不要定死收益，让策略跑出最优表现，基于相对评估

功能特性:
1. 四档分层认证标准 (微型/小型/中型/大型)
2. 差异化认证要求 (小资金高要求，大资金重稳定)
3. 相对表现评估体系
4. 跨档位策略推广机制
5. 动态认证级别调整
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import redis

from ..base.models import SimulationResult, Strategy
from ..utils.logger import get_logger
from .multi_tier_simulation_manager import CapitalTier
from .multi_tier_simulation_manager import SimulationManager as MultiTierSimulationManager
from .relative_performance_evaluator import RelativePerformanceEvaluator, RelativePerformanceResult

logger = get_logger(__name__)


class CertificationLevel(Enum):
    """认证级别"""

    PLATINUM = "PLATINUM"  # 白金级 - 顶级表现
    GOLD = "GOLD"  # 黄金级 - 优秀表现
    SILVER = "SILVER"  # 白银级 - 良好表现
    BRONZE = "BRONZE"  # 青铜级 - 基础表现
    NONE = "NONE"  # 未通过认证


@dataclass
class TierCertificationStandards:
    """档位认证标准"""

    tier: CapitalTier
    tier_name: str

    # 基础要求
    min_sharpe_ratio: float
    max_drawdown: float
    min_win_rate: float

    # 相对表现要求 - 让策略跑出最优表现
    min_benchmark_outperformance: float  # 最低基准超额收益
    min_peer_ranking_percentile: float  # 最低同类排名百分位
    min_risk_adjusted_score: float  # 最低风险调整评分
    min_consistency_score: float  # 最低一致性评分

    # 档位特定要求
    max_turnover: float  # 最大换手率
    max_tracking_error: float  # 最大跟踪误差
    min_position_count: int  # 最少持仓数
    max_position_count: int  # 最多持仓数
    liquidity_requirement: float  # 流动性要求
    volatility_tolerance: float  # 波动率容忍度


@dataclass
class Z2HCertificationResult:  # pylint: disable=too-many-instance-attributes
    """Z2H认证结果"""

    strategy_id: str
    strategy_name: str
    tier: CapitalTier
    certification_level: CertificationLevel
    certification_date: datetime

    # 认证评分
    overall_score: float
    tier_specific_score: float
    relative_performance_score: float

    # 详细结果
    simulation_result: SimulationResult
    relative_performance: RelativePerformanceResult

    # 认证详情
    passed_requirements: List[str]
    failed_requirements: List[str]
    certification_notes: List[str]

    # 资金配置建议
    recommended_allocation: Dict[str, Any]
    max_allocation_ratio: float
    leverage_allowed: float

    # 有效期
    valid_until: datetime
    renewal_required: bool


class FourTierZ2HCertification:
    """四档资金分层Z2H认证系统

    白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统

    核心理念:
    - 不要定死收益，让策略跑出最优表现
    - 基于相对评估而非固定收益要求
    - 差异化认证 (小资金高要求，大资金重稳定)
    - 升级路径 (微型→小型→中型→大型的认证升级)

    认证特色:
    1. 四档分层标准 - 每个档位都有专门的认证要求
    2. 相对表现评估 - 与基准和同类策略对比
    3. 动态调整机制 - 根据市场环境调整标准
    4. 跨档位推广 - 优秀策略可升级到更大资金档位
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """初始化四档Z2H认证系统

        Args:
            redis_client: Redis客户端，用于存储认证结果
        """
        self.redis_client = redis_client or redis.Redis(host="localhost", port=6379, db=0)

        # 初始化组件
        self.multi_tier_manager = MultiTierSimulationManager(redis_client)
        self.performance_evaluator = RelativePerformanceEvaluator(redis_client)

        # 四档认证标准
        self.tier_standards = self._initialize_tier_standards()

        # 认证历史记录
        self.certification_history: Dict[str, List[Z2HCertificationResult]] = {}

        logger.info("FourTierZ2HCertification 初始化完成")
        logger.info("核心理念: 让策略跑出最优表现，基于相对评估")
        logger.info(f"支持档位: {list(self.tier_standards.keys())}")  # pylint: disable=logging-fstring-interpolation

    def _initialize_tier_standards(self) -> Dict[CapitalTier, Dict[CertificationLevel, TierCertificationStandards]]:
        """初始化四档认证标准

        核心设计理念:
        - 小资金档位: 高收益要求，允许高波动和集中持仓
        - 大资金档位: 重稳定性，要求分散持仓和低波动
        - 相对表现评估: 与基准和同类策略对比，而非固定收益要求
        """
        return {
            # 微型资金档 (1千-1万) - 让策略跑出最优表现
            CapitalTier.TIER_1: {
                CertificationLevel.PLATINUM: TierCertificationStandards(
                    tier=CapitalTier.TIER_1,
                    tier_name="微型资金档",
                    min_sharpe_ratio=2.8,
                    max_drawdown=0.12,
                    min_win_rate=0.65,
                    min_benchmark_outperformance=0.20,
                    min_peer_ranking_percentile=0.90,
                    min_risk_adjusted_score=0.85,
                    min_consistency_score=0.75,
                    max_turnover=15.0,
                    max_tracking_error=0.25,
                    min_position_count=2,
                    max_position_count=8,
                    liquidity_requirement=0.2,
                    volatility_tolerance=1.0,
                ),
                CertificationLevel.GOLD: TierCertificationStandards(
                    tier=CapitalTier.TIER_1,
                    tier_name="微型资金档",
                    min_sharpe_ratio=2.3,
                    max_drawdown=0.15,
                    min_win_rate=0.60,
                    min_benchmark_outperformance=0.15,
                    min_peer_ranking_percentile=0.75,
                    min_risk_adjusted_score=0.75,
                    min_consistency_score=0.65,
                    max_turnover=12.0,
                    max_tracking_error=0.22,
                    min_position_count=2,
                    max_position_count=10,
                    liquidity_requirement=0.25,
                    volatility_tolerance=0.9,
                ),
                CertificationLevel.SILVER: TierCertificationStandards(
                    tier=CapitalTier.TIER_1,
                    tier_name="微型资金档",
                    min_sharpe_ratio=1.8,
                    max_drawdown=0.18,
                    min_win_rate=0.55,
                    min_benchmark_outperformance=0.10,
                    min_peer_ranking_percentile=0.60,
                    min_risk_adjusted_score=0.65,
                    min_consistency_score=0.55,
                    max_turnover=10.0,
                    max_tracking_error=0.20,
                    min_position_count=2,
                    max_position_count=12,
                    liquidity_requirement=0.3,
                    volatility_tolerance=0.8,
                ),
            },
            # 小型资金档 (1万-5万)
            CapitalTier.TIER_2: {
                CertificationLevel.PLATINUM: TierCertificationStandards(
                    tier=CapitalTier.TIER_2,
                    tier_name="小型资金档",
                    min_sharpe_ratio=2.5,
                    max_drawdown=0.10,
                    min_win_rate=0.62,
                    min_benchmark_outperformance=0.15,
                    min_peer_ranking_percentile=0.85,
                    min_risk_adjusted_score=0.80,
                    min_consistency_score=0.75,
                    max_turnover=8.0,
                    max_tracking_error=0.18,
                    min_position_count=3,
                    max_position_count=15,
                    liquidity_requirement=0.4,
                    volatility_tolerance=0.7,
                ),
                CertificationLevel.GOLD: TierCertificationStandards(
                    tier=CapitalTier.TIER_2,
                    tier_name="小型资金档",
                    min_sharpe_ratio=2.0,
                    max_drawdown=0.12,
                    min_win_rate=0.58,
                    min_benchmark_outperformance=0.12,
                    min_peer_ranking_percentile=0.70,
                    min_risk_adjusted_score=0.70,
                    min_consistency_score=0.65,
                    max_turnover=6.0,
                    max_tracking_error=0.15,
                    min_position_count=3,
                    max_position_count=18,
                    liquidity_requirement=0.45,
                    volatility_tolerance=0.6,
                ),
                CertificationLevel.SILVER: TierCertificationStandards(
                    tier=CapitalTier.TIER_2,
                    tier_name="小型资金档",
                    min_sharpe_ratio=1.5,
                    max_drawdown=0.15,
                    min_win_rate=0.55,
                    min_benchmark_outperformance=0.08,
                    min_peer_ranking_percentile=0.55,
                    min_risk_adjusted_score=0.60,
                    min_consistency_score=0.55,
                    max_turnover=5.0,
                    max_tracking_error=0.15,
                    min_position_count=3,
                    max_position_count=20,
                    liquidity_requirement=0.5,
                    volatility_tolerance=0.6,
                ),
            },
            # 中型资金档 (10万-20万)
            CapitalTier.TIER_3: {
                CertificationLevel.PLATINUM: TierCertificationStandards(
                    tier=CapitalTier.TIER_3,
                    tier_name="中型资金档",
                    min_sharpe_ratio=2.2,
                    max_drawdown=0.08,
                    min_win_rate=0.60,
                    min_benchmark_outperformance=0.12,
                    min_peer_ranking_percentile=0.80,
                    min_risk_adjusted_score=0.75,
                    min_consistency_score=0.80,
                    max_turnover=4.0,
                    max_tracking_error=0.12,
                    min_position_count=5,
                    max_position_count=25,
                    liquidity_requirement=0.6,
                    volatility_tolerance=0.5,
                ),
                CertificationLevel.GOLD: TierCertificationStandards(
                    tier=CapitalTier.TIER_3,
                    tier_name="中型资金档",
                    min_sharpe_ratio=1.8,
                    max_drawdown=0.10,
                    min_win_rate=0.57,
                    min_benchmark_outperformance=0.10,
                    min_peer_ranking_percentile=0.65,
                    min_risk_adjusted_score=0.65,
                    min_consistency_score=0.70,
                    max_turnover=3.5,
                    max_tracking_error=0.12,
                    min_position_count=5,
                    max_position_count=28,
                    liquidity_requirement=0.65,
                    volatility_tolerance=0.45,
                ),
                CertificationLevel.SILVER: TierCertificationStandards(
                    tier=CapitalTier.TIER_3,
                    tier_name="中型资金档",
                    min_sharpe_ratio=1.4,
                    max_drawdown=0.12,
                    min_win_rate=0.54,
                    min_benchmark_outperformance=0.06,
                    min_peer_ranking_percentile=0.50,
                    min_risk_adjusted_score=0.55,
                    min_consistency_score=0.60,
                    max_turnover=3.0,
                    max_tracking_error=0.12,
                    min_position_count=5,
                    max_position_count=30,
                    liquidity_requirement=0.7,
                    volatility_tolerance=0.4,
                ),
            },
            # 大型资金档 (21万-70万) - 重稳定性
            CapitalTier.TIER_4: {
                CertificationLevel.PLATINUM: TierCertificationStandards(
                    tier=CapitalTier.TIER_4,
                    tier_name="大型资金档",
                    min_sharpe_ratio=2.0,
                    max_drawdown=0.06,
                    min_win_rate=0.58,
                    min_benchmark_outperformance=0.08,
                    min_peer_ranking_percentile=0.75,
                    min_risk_adjusted_score=0.70,
                    min_consistency_score=0.85,
                    max_turnover=2.5,
                    max_tracking_error=0.15,
                    min_position_count=10,
                    max_position_count=40,
                    liquidity_requirement=0.8,
                    volatility_tolerance=0.3,
                ),
                CertificationLevel.GOLD: TierCertificationStandards(
                    tier=CapitalTier.TIER_4,
                    tier_name="大型资金档",
                    min_sharpe_ratio=1.6,
                    max_drawdown=0.08,
                    min_win_rate=0.55,
                    min_benchmark_outperformance=0.06,
                    min_peer_ranking_percentile=0.60,
                    min_risk_adjusted_score=0.60,
                    min_consistency_score=0.75,
                    max_turnover=2.0,
                    max_tracking_error=0.15,
                    min_position_count=10,
                    max_position_count=45,
                    liquidity_requirement=0.75,
                    volatility_tolerance=0.35,
                ),
                CertificationLevel.SILVER: TierCertificationStandards(
                    tier=CapitalTier.TIER_4,
                    tier_name="大型资金档",
                    min_sharpe_ratio=1.2,
                    max_drawdown=0.10,
                    min_win_rate=0.52,
                    min_benchmark_outperformance=0.04,
                    min_peer_ranking_percentile=0.45,
                    min_risk_adjusted_score=0.50,
                    min_consistency_score=0.65,
                    max_turnover=2.0,
                    max_tracking_error=0.18,
                    min_position_count=8,
                    max_position_count=50,
                    liquidity_requirement=0.8,
                    volatility_tolerance=0.3,
                ),
            },
        }

    async def certify_strategy(
        self,
        strategy: Strategy,
        simulation_result: SimulationResult,
        tier: CapitalTier,
        target_level: Optional[CertificationLevel] = None,
    ) -> Z2HCertificationResult:
        """对策略进行Z2H认证

        Args:
            strategy: 待认证策略
            simulation_result: 模拟验证结果
            tier: 资金档位
            target_level: 目标认证级别 (None表示自动确定最高可达级别)

        Returns:
            Z2H认证结果
        """
        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"开始对策略 {strategy.name} 进行 {tier.value} Z2H认证"
        )  # pylint: disable=logging-fstring-interpolation
        logger.info("核心理念: 让策略跑出最优表现，基于相对评估")

        # 1. 相对表现评估
        logger.info("步骤1: 相对表现评估")
        relative_performance = await self.performance_evaluator.evaluate_relative_performance(
            simulation_result, strategy
        )

        # 2. 确定认证级别
        logger.info("步骤2: 确定认证级别")
        if target_level:
            certification_level = await self._validate_target_level(
                simulation_result, relative_performance, tier, target_level
            )
        else:
            certification_level = await self._determine_certification_level(
                simulation_result, relative_performance, tier
            )

        # 3. 详细认证检查
        logger.info(f"步骤3: {certification_level.value} 级认证检查")  # pylint: disable=logging-fstring-interpolation
        passed_requirements, failed_requirements = await self._check_certification_requirements(
            simulation_result, relative_performance, tier, certification_level
        )

        # 4. 计算认证评分
        logger.info("步骤4: 计算认证评分")
        overall_score, tier_specific_score, relative_performance_score = self._calculate_certification_scores(
            simulation_result, relative_performance, tier, certification_level
        )

        # 5. 生成资金配置建议
        logger.info("步骤5: 生成资金配置建议")
        allocation_recommendation = self._generate_allocation_recommendation(
            tier, certification_level, simulation_result
        )

        # 6. 生成认证说明
        certification_notes = self._generate_certification_notes(
            tier, certification_level, passed_requirements, failed_requirements, relative_performance
        )

        # 7. 构建认证结果
        certification_result = Z2HCertificationResult(
            strategy_id=strategy.strategy_id,
            strategy_name=strategy.name,
            tier=tier,
            certification_level=certification_level,
            certification_date=datetime.now(),
            overall_score=overall_score,
            tier_specific_score=tier_specific_score,
            relative_performance_score=relative_performance_score,
            simulation_result=simulation_result,
            relative_performance=relative_performance,
            passed_requirements=passed_requirements,
            failed_requirements=failed_requirements,
            certification_notes=certification_notes,
            recommended_allocation=allocation_recommendation,
            max_allocation_ratio=allocation_recommendation["max_allocation_ratio"],
            leverage_allowed=allocation_recommendation["leverage_allowed"],
            valid_until=datetime.now() + timedelta(days=90),
            renewal_required=len(failed_requirements) > 0,
        )

        # 8. 保存认证结果
        await self._save_certification_result(certification_result)

        logger.info("Z2H认证完成")
        logger.info(f"  认证级别: {certification_level.value}")  # pylint: disable=logging-fstring-interpolation
        logger.info(f"  综合评分: {overall_score:.2f}")  # pylint: disable=logging-fstring-interpolation
        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"  通过要求: {len(passed_requirements)}/{len(passed_requirements) + len(failed_requirements)}"
        )  # pylint: disable=logging-fstring-interpolation
        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"  最大配置比例: {allocation_recommendation['max_allocation_ratio']:.1%}"
        )  # pylint: disable=logging-fstring-interpolation

        return certification_result

    async def _determine_certification_level(
        self, simulation_result: SimulationResult, relative_performance: RelativePerformanceResult, tier: CapitalTier
    ) -> CertificationLevel:
        """确定策略可达到的最高认证级别"""
        logger.debug(f"确定 {tier.value} 档位的最高认证级别")  # pylint: disable=logging-fstring-interpolation

        for level in [
            CertificationLevel.PLATINUM,
            CertificationLevel.GOLD,
            CertificationLevel.SILVER,
            CertificationLevel.BRONZE,
        ]:
            if level not in self.tier_standards[tier]:
                continue
            standards = self.tier_standards[tier][level]
            if await self._meets_basic_requirements(simulation_result, relative_performance, standards):
                logger.info(f"策略满足 {level.value} 级认证要求")  # pylint: disable=logging-fstring-interpolation
                return level

        logger.info("策略未满足任何认证级别要求")
        return CertificationLevel.NONE

    async def _validate_target_level(
        self,
        simulation_result: SimulationResult,
        relative_performance: RelativePerformanceResult,
        tier: CapitalTier,
        target_level: CertificationLevel,
    ) -> CertificationLevel:
        """验证目标认证级别是否可达"""
        if target_level not in self.tier_standards[tier]:
            logger.warning(  # pylint: disable=logging-fstring-interpolation
                f"{tier.value} 不支持 {target_level.value} 级认证，自动确定级别"
            )  # pylint: disable=logging-fstring-interpolation
            return await self._determine_certification_level(simulation_result, relative_performance, tier)

        standards = self.tier_standards[tier][target_level]
        if await self._meets_basic_requirements(  # pylint: disable=no-else-return
            simulation_result, relative_performance, standards
        ):  # pylint: disable=no-else-return
            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"策略满足目标 {target_level.value} 级认证要求"
            )  # pylint: disable=logging-fstring-interpolation
            return target_level
        else:
            logger.warning(  # pylint: disable=logging-fstring-interpolation
                f"策略不满足目标 {target_level.value} 级要求，自动降级"
            )  # pylint: disable=logging-fstring-interpolation
            return await self._determine_certification_level(simulation_result, relative_performance, tier)

    async def _meets_basic_requirements(  # pylint: disable=r0911
        self,
        simulation_result: SimulationResult,
        relative_performance: RelativePerformanceResult,
        standards: TierCertificationStandards,
    ) -> bool:
        """检查是否满足基础认证要求"""
        if simulation_result.sharpe_ratio < standards.min_sharpe_ratio:
            return False
        if simulation_result.max_drawdown > standards.max_drawdown:
            return False
        if simulation_result.win_rate < standards.min_win_rate:
            return False
        if relative_performance.benchmark_outperformance < standards.min_benchmark_outperformance:
            return False
        if relative_performance.peer_ranking_percentile < standards.min_peer_ranking_percentile:
            return False
        if relative_performance.risk_adjusted_score < standards.min_risk_adjusted_score:
            return False
        if relative_performance.consistency_score < standards.min_consistency_score:
            return False

        monthly_turnover = getattr(simulation_result, "monthly_turnover", 2.0)
        if monthly_turnover > standards.max_turnover:
            return False

        tracking_error = getattr(relative_performance, "tracking_error", 0.1)
        if tracking_error > standards.max_tracking_error:
            return False

        return True

    async def _check_certification_requirements(
        self,
        simulation_result: SimulationResult,
        relative_performance: RelativePerformanceResult,
        tier: CapitalTier,
        certification_level: CertificationLevel,
    ) -> Tuple[List[str], List[str]]:
        """详细检查认证要求"""
        if certification_level == CertificationLevel.NONE:
            return [], ["未满足任何认证级别的基础要求"]

        standards = self.tier_standards[tier][certification_level]
        passed_requirements = []
        failed_requirements = []

        # 基础指标检查
        if simulation_result.sharpe_ratio >= standards.min_sharpe_ratio:
            passed_requirements.append(f"夏普比率 {simulation_result.sharpe_ratio:.2f} >= {standards.min_sharpe_ratio}")
        else:
            failed_requirements.append(f"夏普比率 {simulation_result.sharpe_ratio:.2f} < {standards.min_sharpe_ratio}")

        if simulation_result.max_drawdown <= standards.max_drawdown:
            passed_requirements.append(f"最大回撤 {simulation_result.max_drawdown:.1%} <= {standards.max_drawdown:.1%}")
        else:
            failed_requirements.append(f"最大回撤 {simulation_result.max_drawdown:.1%} > {standards.max_drawdown:.1%}")

        if simulation_result.win_rate >= standards.min_win_rate:
            passed_requirements.append(f"胜率 {simulation_result.win_rate:.1%} >= {standards.min_win_rate:.1%}")
        else:
            failed_requirements.append(f"胜率 {simulation_result.win_rate:.1%} < {standards.min_win_rate:.1%}")

        # 相对表现检查
        if relative_performance.benchmark_outperformance >= standards.min_benchmark_outperformance:
            passed_requirements.append(
                f"基准超额收益 {relative_performance.benchmark_outperformance:.1%} >= {standards.min_benchmark_outperformance:.1%}"  # pylint: disable=line-too-long
            )
        else:
            failed_requirements.append(
                f"基准超额收益 {relative_performance.benchmark_outperformance:.1%} < {standards.min_benchmark_outperformance:.1%}"  # pylint: disable=line-too-long
            )

        if relative_performance.peer_ranking_percentile >= standards.min_peer_ranking_percentile:
            passed_requirements.append(f"同类排名 前{(1-relative_performance.peer_ranking_percentile)*100:.0f}%")
        else:
            failed_requirements.append(f"同类排名不达标")  # pylint: disable=w1309

        if relative_performance.risk_adjusted_score >= standards.min_risk_adjusted_score:
            passed_requirements.append(
                f"风险调整评分 {relative_performance.risk_adjusted_score:.2f} >= {standards.min_risk_adjusted_score}"
            )
        else:
            failed_requirements.append(
                f"风险调整评分 {relative_performance.risk_adjusted_score:.2f} < {standards.min_risk_adjusted_score}"
            )

        if relative_performance.consistency_score >= standards.min_consistency_score:
            passed_requirements.append(
                f"一致性评分 {relative_performance.consistency_score:.2f} >= {standards.min_consistency_score}"
            )
        else:
            failed_requirements.append(
                f"一致性评分 {relative_performance.consistency_score:.2f} < {standards.min_consistency_score}"
            )

        # 档位特定检查
        monthly_turnover = getattr(simulation_result, "monthly_turnover", 2.0)
        if monthly_turnover <= standards.max_turnover:
            passed_requirements.append(f"月换手率 {monthly_turnover:.1f} <= {standards.max_turnover}")
        else:
            failed_requirements.append(f"月换手率 {monthly_turnover:.1f} > {standards.max_turnover}")

        tracking_error = getattr(relative_performance, "tracking_error", 0.1)
        if tracking_error <= standards.max_tracking_error:
            passed_requirements.append(f"跟踪误差 {tracking_error:.1%} <= {standards.max_tracking_error:.1%}")
        else:
            failed_requirements.append(f"跟踪误差 {tracking_error:.1%} > {standards.max_tracking_error:.1%}")

        return passed_requirements, failed_requirements

    def _calculate_certification_scores(
        self,
        simulation_result: SimulationResult,
        relative_performance: RelativePerformanceResult,
        tier: CapitalTier,
        certification_level: CertificationLevel,
    ) -> Tuple[float, float, float]:
        """计算认证评分"""
        if certification_level == CertificationLevel.NONE:
            return 0.0, 0.0, 0.0

        standards = self.tier_standards[tier][certification_level]

        # 档位特定评分
        sharpe_score = min(simulation_result.sharpe_ratio / (standards.min_sharpe_ratio * 1.5), 1.0)
        drawdown_score = max(0, 1 - simulation_result.max_drawdown / standards.max_drawdown)
        win_rate_score = min(simulation_result.win_rate / (standards.min_win_rate * 1.2), 1.0)
        tier_specific_score = sharpe_score * 0.4 + drawdown_score * 0.35 + win_rate_score * 0.25

        # 相对表现评分
        benchmark_score = min(
            relative_performance.benchmark_outperformance / (standards.min_benchmark_outperformance * 1.5), 1.0
        )
        peer_score = min(
            relative_performance.peer_ranking_percentile / (standards.min_peer_ranking_percentile * 1.1), 1.0
        )
        risk_adj_score = min(relative_performance.risk_adjusted_score / (standards.min_risk_adjusted_score * 1.2), 1.0)
        consistency_score = min(relative_performance.consistency_score / (standards.min_consistency_score * 1.2), 1.0)
        relative_performance_score = (
            benchmark_score * 0.3 + peer_score * 0.25 + risk_adj_score * 0.25 + consistency_score * 0.2
        )

        # 综合评分
        overall_score = tier_specific_score * 0.6 + relative_performance_score * 0.4

        logger.debug(  # pylint: disable=logging-fstring-interpolation
            f"认证评分: 综合={overall_score:.2f}, 档位特定={tier_specific_score:.2f}, 相对表现={relative_performance_score:.2f}"
        )

        return overall_score, tier_specific_score, relative_performance_score

    def _generate_allocation_recommendation(
        self, tier: CapitalTier, certification_level: CertificationLevel, simulation_result: SimulationResult
    ) -> Dict[str, Any]:
        """生成资金配置建议

        白皮书依据: 第四章 4.3.2 资金配置规则

        Args:
            tier: 资金档位
            certification_level: 认证级别
            simulation_result: 模拟结果

        Returns:
            Dict[str, Any]: 资金配置建议
        """
        # 基础配置规则
        base_allocation_rules = {
            CertificationLevel.PLATINUM: {
                CapitalTier.TIER_1: {"max_ratio": 0.30, "leverage": 1.0},
                CapitalTier.TIER_2: {"max_ratio": 0.25, "leverage": 1.0},
                CapitalTier.TIER_3: {"max_ratio": 0.20, "leverage": 1.2},
                CapitalTier.TIER_4: {"max_ratio": 0.15, "leverage": 1.5},
            },
            CertificationLevel.GOLD: {
                CapitalTier.TIER_1: {"max_ratio": 0.25, "leverage": 1.0},
                CapitalTier.TIER_2: {"max_ratio": 0.20, "leverage": 1.0},
                CapitalTier.TIER_3: {"max_ratio": 0.15, "leverage": 1.0},
                CapitalTier.TIER_4: {"max_ratio": 0.12, "leverage": 1.2},
            },
            CertificationLevel.SILVER: {
                CapitalTier.TIER_1: {"max_ratio": 0.20, "leverage": 1.0},
                CapitalTier.TIER_2: {"max_ratio": 0.15, "leverage": 1.0},
                CapitalTier.TIER_3: {"max_ratio": 0.12, "leverage": 1.0},
                CapitalTier.TIER_4: {"max_ratio": 0.10, "leverage": 1.0},
            },
        }

        # 档位资金范围和最优资金
        tier_capital_configs = {
            CapitalTier.TIER_1: {"capital_range": (1000, 10000), "optimal_capital": 5000},
            CapitalTier.TIER_2: {"capital_range": (10000, 70000), "optimal_capital": 50000},
            CapitalTier.TIER_3: {"capital_range": (70000, 210000), "optimal_capital": 150000},
            CapitalTier.TIER_4: {"capital_range": (210000, 700000), "optimal_capital": 500000},
        }

        # 获取基础规则
        if certification_level in base_allocation_rules and tier in base_allocation_rules[certification_level]:
            base_rule = base_allocation_rules[certification_level][tier]
        else:
            base_rule = {"max_ratio": 0.05, "leverage": 1.0}

        # 获取档位资金配置
        capital_config = tier_capital_configs.get(tier, {"capital_range": (1000, 10000), "optimal_capital": 5000})

        # 生成风险警告
        risk_warnings = self._generate_risk_warnings(tier, certification_level, simulation_result)

        # 生成使用指导
        usage_guidelines = self._generate_usage_guidelines(tier, certification_level)

        # 生成监控要求
        monitoring_requirements = self._generate_monitoring_requirements(tier, certification_level)

        return {
            "max_allocation_ratio": base_rule["max_ratio"],
            "leverage_allowed": base_rule["leverage"],
            "tier": tier.value,
            "certification_level": certification_level.value,
            "risk_budget": base_rule["max_ratio"] * 0.5,
            "recommended_capital_range": capital_config["capital_range"],
            "optimal_capital": capital_config["optimal_capital"],
            "risk_warnings": risk_warnings,
            "usage_guidelines": usage_guidelines,
            "monitoring_requirements": monitoring_requirements,
        }

    def _generate_risk_warnings(
        self, tier: CapitalTier, certification_level: CertificationLevel, simulation_result: SimulationResult
    ) -> List[str]:
        """生成风险警告

        Args:
            tier: 资金档位
            certification_level: 认证级别
            simulation_result: 模拟结果

        Returns:
            List[str]: 风险警告列表
        """
        warnings = []

        # 档位特定警告
        if tier == CapitalTier.TIER_1:
            warnings.append("微型资金档波动较大，请做好风险管理")
            warnings.append("集中持仓风险较高，建议设置严格止损")
        elif tier == CapitalTier.TIER_4:
            warnings.append("大型资金档流动性要求高，注意市场冲击成本")
            warnings.append("建议分批建仓和平仓，避免单次大额交易")

        # 认证级别警告
        if certification_level == CertificationLevel.SILVER:
            warnings.append("银级认证策略表现一般，建议谨慎配置")

        # 模拟结果警告
        if simulation_result.max_drawdown > 0.10:
            warnings.append(f"历史最大回撤{simulation_result.max_drawdown:.1%}，注意回撤风险")

        return warnings

    def _generate_usage_guidelines(self, tier: CapitalTier, certification_level: CertificationLevel) -> List[str]:
        """生成使用指导

        Args:
            tier: 资金档位
            certification_level: 认证级别

        Returns:
            List[str]: 使用指导列表
        """
        guidelines = []

        # 通用指导
        guidelines.append("建议在模拟盘验证后再进行实盘交易")
        guidelines.append("定期复核策略表现，及时调整配置")

        # 档位特定指导
        if tier == CapitalTier.TIER_1:
            guidelines.append("微型资金档适合高频交易和集中持仓策略")
            guidelines.append("建议单股仓位不超过20%")
        elif tier == CapitalTier.TIER_4:
            guidelines.append("大型资金档适合分散持仓和低换手策略")
            guidelines.append("建议单股仓位不超过5%")

        # 认证级别指导
        if certification_level == CertificationLevel.PLATINUM:
            guidelines.append("白金级策略表现优秀，可适当提高配置比例")

        return guidelines

    def _generate_monitoring_requirements(
        self, tier: CapitalTier, certification_level: CertificationLevel
    ) -> List[str]:
        """生成监控要求

        Args:
            tier: 资金档位
            certification_level: 认证级别

        Returns:
            List[str]: 监控要求列表
        """
        requirements = []

        # 通用监控要求
        requirements.append("每日监控策略收益和回撤")
        requirements.append("每周复核持仓分布和风险敞口")

        # 档位特定监控
        if tier == CapitalTier.TIER_1:
            requirements.append("实时监控单股仓位，防止过度集中")
            requirements.append("监控换手率，控制交易成本")
        elif tier == CapitalTier.TIER_4:
            requirements.append("监控流动性指标，确保可及时平仓")
            requirements.append("监控市场冲击成本，优化交易执行")

        # 认证级别监控
        if certification_level in [CertificationLevel.SILVER, CertificationLevel.BRONZE]:
            requirements.append("加强监控频率，每日复核策略表现")

        return requirements

    def _generate_certification_notes(  # pylint: disable=too-many-positional-arguments
        self,
        tier: CapitalTier,
        certification_level: CertificationLevel,
        passed_requirements: List[str],
        failed_requirements: List[str],
        relative_performance: RelativePerformanceResult,
    ) -> List[str]:
        """生成认证说明

        Args:
            tier: 资金档位
            certification_level: 认证级别
            passed_requirements: 通过的要求列表
            failed_requirements: 未通过的要求列表
            relative_performance: 相对表现结果

        Returns:
            List[str]: 认证说明列表
        """
        notes = []

        # 基本信息
        notes.append(f"档位: {tier.value}")
        notes.append(f"认证级别: {certification_level.value}")
        notes.append(f"通过要求数: {len(passed_requirements)}")
        notes.append(f"未通过要求数: {len(failed_requirements)}")

        # 档位特点
        if tier == CapitalTier.TIER_1:
            notes.append("微型资金档特点: 高收益要求，允许高波动和集中持仓")
        elif tier == CapitalTier.TIER_4:
            notes.append("大型资金档特点: 重稳定性，要求分散持仓和低波动")

        # 策略优势分析
        strengths = []
        if relative_performance.benchmark_outperformance > 0.15:
            strengths.append("显著超越基准表现")
        if relative_performance.peer_ranking_percentile > 0.80:
            strengths.append("同类策略排名前20%")
        if relative_performance.risk_adjusted_score > 0.75:
            strengths.append("优秀的风险调整收益")
        if relative_performance.consistency_score > 0.75:
            strengths.append("表现稳定一致")

        if strengths:
            notes.append(f"策略优势: {', '.join(strengths)}")

        # 改进建议 - 即使表现优秀也给出建议
        suggestions = []
        if relative_performance.benchmark_outperformance < 0.10:
            suggestions.append("基准超额收益有待提升")
        if relative_performance.consistency_score < 0.60:
            suggestions.append("表现一致性需要改善")

        # 如果没有明显弱点，给出通用建议
        if not suggestions:
            if certification_level == CertificationLevel.PLATINUM:
                suggestions.append("继续保持优秀表现，定期复核策略有效性")
            elif certification_level == CertificationLevel.GOLD:
                suggestions.append("可考虑优化风险调整收益，争取白金级认证")
            else:
                suggestions.append("建议提升夏普比率和一致性评分")

        notes.append(f"改进建议: {', '.join(suggestions)}")

        # 认证有效期
        notes.append("认证有效期: 90天")

        return notes

    async def _save_certification_result(self, result: Z2HCertificationResult) -> None:
        """保存认证结果到Redis"""
        try:
            key = f"z2h_certification:{result.strategy_id}:{result.tier.value}"
            data = {
                "strategy_id": result.strategy_id,
                "strategy_name": result.strategy_name,
                "tier": result.tier.value,
                "certification_level": result.certification_level.value,
                "certification_date": result.certification_date.isoformat(),
                "overall_score": result.overall_score,
                "tier_specific_score": result.tier_specific_score,
                "relative_performance_score": result.relative_performance_score,
                "passed_requirements": result.passed_requirements,
                "failed_requirements": result.failed_requirements,
                "certification_notes": result.certification_notes,
                "max_allocation_ratio": result.max_allocation_ratio,
                "leverage_allowed": result.leverage_allowed,
                "valid_until": result.valid_until.isoformat(),
            }
            self.redis_client.set(key, json.dumps(data), ex=86400 * 90)  # 90天过期
            logger.info(f"认证结果已保存: {key}")  # pylint: disable=logging-fstring-interpolation
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"保存认证结果失败: {e}")  # pylint: disable=logging-fstring-interpolation

    def get_tier_standards(self, tier: CapitalTier) -> Dict[CertificationLevel, TierCertificationStandards]:
        """获取指定档位的认证标准"""
        return self.tier_standards.get(tier, {})

    def get_all_tier_standards(self) -> Dict[CapitalTier, Dict[CertificationLevel, TierCertificationStandards]]:
        """获取所有档位的认证标准"""
        return self.tier_standards
