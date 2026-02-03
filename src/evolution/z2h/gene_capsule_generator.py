"""Gene Capsule Generator for Z2H Certification

白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统
"""

from datetime import datetime
from typing import Any, Dict, List

from loguru import logger

from src.evolution.z2h.data_models import (
    CERTIFICATION_STANDARDS,
    CertificationLevel,
    CertificationResult,
    Z2HGeneCapsule,
)


class GeneCapsuleGenerator:
    """基因胶囊生成器

    白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统

    负责生成Z2H基因胶囊，包含策略的完整认证信息
    """

    def __init__(self):
        """初始化基因胶囊生成器"""
        logger.info("GeneCapsuleGenerator初始化完成")

    def generate_capsule(  # pylint: disable=too-many-positional-arguments
        self,
        strategy_id: str,
        strategy_name: str,
        source_factors: List[str],
        arena_score: float,
        simulation_metrics: Dict[str, float],
        metadata: Dict[str, Any] = None,
    ) -> Z2HGeneCapsule:
        """生成Z2H基因胶囊

        白皮书依据: 第四章 4.3.2 Z2HGeneCapsule

        Args:
            strategy_id: 策略唯一标识
            strategy_name: 策略名称
            source_factors: 源因子ID列表
            arena_score: Arena综合评分
            simulation_metrics: 模拟盘指标
            metadata: 额外元数据

        Returns:
            Z2H基因胶囊

        Raises:
            ValueError: 当参数无效时
        """
        # 验证参数
        if not strategy_id:
            raise ValueError("strategy_id不能为空")

        if not strategy_name:
            raise ValueError("strategy_name不能为空")

        if not source_factors:
            raise ValueError("source_factors不能为空")

        if not 0.0 <= arena_score <= 1.0:
            raise ValueError(f"arena_score必须在[0.0, 1.0]范围内，当前: {arena_score}")

        # 验证simulation_metrics包含必需字段
        required_metrics = ["sharpe_ratio", "max_drawdown", "total_return", "win_rate", "profit_factor"]
        for metric in required_metrics:
            if metric not in simulation_metrics:
                raise ValueError(f"simulation_metrics缺少必需指标: {metric}")

        # 确定认证等级
        certification_result = self.determine_certification_level(arena_score, simulation_metrics)

        if not certification_result.eligible:
            raise ValueError(f"策略不符合Z2H认证条件: {certification_result.reason}")

        # 创建基因胶囊
        capsule = Z2HGeneCapsule(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            source_factors=source_factors,
            arena_score=arena_score,
            simulation_metrics=simulation_metrics,
            certification_date=datetime.now(),
            certification_level=certification_result.certification_level,
            metadata=metadata or {},
        )

        logger.info(
            f"生成Z2H基因胶囊: {strategy_id}, "
            f"认证等级: {certification_result.certification_level.value}, "
            f"Arena评分: {arena_score:.3f}, "
            f"夏普比率: {simulation_metrics['sharpe_ratio']:.2f}"
        )

        return capsule

    def determine_certification_level(
        self,
        arena_score: float,
        simulation_metrics: Dict[str, float],
    ) -> CertificationResult:
        """确定认证等级

        白皮书依据: 第四章 4.3.2 Z2H认证标准

        认证等级基于Arena四层验证和模拟盘表现综合评定：
        - PLATINUM: 白金级，顶级表现
        - GOLD: 黄金级，优秀表现
        - SILVER: 白银级，良好表现

        Args:
            arena_score: Arena综合评分
            simulation_metrics: 模拟盘指标

        Returns:
            认证结果
        """
        # 提取关键指标
        sharpe_ratio = simulation_metrics.get("sharpe_ratio", 0.0)
        max_drawdown = abs(simulation_metrics.get("max_drawdown", 1.0))  # 转为正数
        win_rate = simulation_metrics.get("win_rate", 0.0)
        profit_factor = simulation_metrics.get("profit_factor", 0.0)
        total_return = simulation_metrics.get("total_return", 0.0)

        # 按从高到低的顺序检查认证等级
        for level in [CertificationLevel.PLATINUM, CertificationLevel.GOLD, CertificationLevel.SILVER]:
            criteria = CERTIFICATION_STANDARDS[level]

            # 检查是否满足所有标准
            if (
                sharpe_ratio >= criteria.min_sharpe_ratio  # pylint: disable=r0916
                and max_drawdown <= criteria.max_drawdown
                and win_rate >= criteria.min_win_rate
                and profit_factor >= criteria.min_profit_factor
                and total_return >= criteria.min_total_return
                and arena_score >= criteria.min_arena_score
            ):

                logger.info(
                    f"策略符合{level.value}认证标准 - "
                    f"夏普: {sharpe_ratio:.2f} (≥{criteria.min_sharpe_ratio}), "
                    f"回撤: {max_drawdown:.2%} (≤{criteria.max_drawdown:.2%}), "
                    f"胜率: {win_rate:.2%} (≥{criteria.min_win_rate:.2%}), "
                    f"盈亏比: {profit_factor:.2f} (≥{criteria.min_profit_factor}), "
                    f"收益: {total_return:.2%} (≥{criteria.min_total_return:.2%}), "
                    f"Arena: {arena_score:.3f} (≥{criteria.min_arena_score})"
                )

                return CertificationResult(
                    eligible=True,
                    certification_level=level,
                    metrics_summary={
                        "sharpe_ratio": sharpe_ratio,
                        "max_drawdown": max_drawdown,
                        "win_rate": win_rate,
                        "profit_factor": profit_factor,
                        "total_return": total_return,
                        "arena_score": arena_score,
                    },
                )

        # 不符合任何认证等级
        min_criteria = CERTIFICATION_STANDARDS[CertificationLevel.SILVER]

        # 找出不符合的指标
        failed_checks = []
        if sharpe_ratio < min_criteria.min_sharpe_ratio:
            failed_checks.append(f"夏普比率{sharpe_ratio:.2f} < {min_criteria.min_sharpe_ratio}")
        if max_drawdown > min_criteria.max_drawdown:
            failed_checks.append(f"最大回撤{max_drawdown:.2%} > {min_criteria.max_drawdown:.2%}")
        if win_rate < min_criteria.min_win_rate:
            failed_checks.append(f"胜率{win_rate:.2%} < {min_criteria.min_win_rate:.2%}")
        if profit_factor < min_criteria.min_profit_factor:
            failed_checks.append(f"盈亏比{profit_factor:.2f} < {min_criteria.min_profit_factor}")
        if total_return < min_criteria.min_total_return:
            failed_checks.append(f"总收益{total_return:.2%} < {min_criteria.min_total_return:.2%}")
        if arena_score < min_criteria.min_arena_score:
            failed_checks.append(f"Arena评分{arena_score:.3f} < {min_criteria.min_arena_score}")

        reason = "不符合最低认证标准(SILVER): " + ", ".join(failed_checks)

        logger.warning(f"策略不符合Z2H认证条件: {reason}")

        return CertificationResult(
            eligible=False,
            reason=reason,
            metrics_summary={
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "total_return": total_return,
                "arena_score": arena_score,
            },
        )

    def validate_capsule(self, capsule: Z2HGeneCapsule) -> bool:
        """验证基因胶囊的完整性和一致性

        Args:
            capsule: Z2H基因胶囊

        Returns:
            是否有效
        """
        try:
            # 验证认证等级与指标是否一致
            result = self.determine_certification_level(capsule.arena_score, capsule.simulation_metrics)

            if not result.eligible:
                logger.error(f"基因胶囊验证失败: {result.reason}")
                return False

            if result.certification_level != capsule.certification_level:
                logger.error(
                    f"基因胶囊认证等级不一致: "
                    f"实际{result.certification_level.value} vs "
                    f"声明{capsule.certification_level.value}"
                )
                return False

            logger.info(f"基因胶囊验证通过: {capsule.strategy_id}")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"基因胶囊验证异常: {e}")
            return False
