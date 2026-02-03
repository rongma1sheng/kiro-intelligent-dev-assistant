"""策略选择器

白皮书依据: 第一章 1.3 资本分配, 第四章 4.2 斯巴达竞技场

根据资金档位、市场环境、Arena表现选择最优策略组合
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from loguru import logger

from src.strategies.data_models import StrategyMetadata


@dataclass
class StrategyRecommendation:
    """策略推荐结果

    Attributes:
        strategy_name: 策略名称
        recommended_weight: 推荐权重 (0.0-1.0)
        tier: 适用档位
        arena_performance: Arena表现指标
        reason: 推荐原因
    """

    strategy_name: str
    recommended_weight: float
    tier: str
    arena_performance: Dict[str, float]
    reason: str

    def __post_init__(self):
        """验证数据"""
        if not 0.0 <= self.recommended_weight <= 1.0:
            raise ValueError(f"推荐权重必须在[0.0, 1.0]范围内: {self.recommended_weight}")


class StrategySelector:
    """策略选择器

    白皮书依据: 第一章 1.3 资本分配

    功能：
    1. 根据档位筛选策略
    2. 优先选择Arena表现最好的策略
    3. 只选择Z2H认证的策略
    4. 考虑市场环境
    5. 返回策略列表及推荐权重
    """

    def __init__(self):
        """初始化策略选择器"""
        self.strategy_pool: Dict[str, StrategyMetadata] = {}

        logger.info("StrategySelector初始化完成")

    def register_strategy(self, metadata: StrategyMetadata) -> None:
        """注册策略到策略池

        Args:
            metadata: 策略元数据
        """
        self.strategy_pool[metadata.strategy_name] = metadata

        logger.info(
            f"策略注册 - {metadata.strategy_name}: "
            f"Z2H认证={metadata.z2h_certified}, "
            f"最佳档位={metadata.best_tier}"
        )

    def select_strategies(
        self, tier: str, market_regime: Optional[str] = None, top_n: int = 5
    ) -> List[StrategyRecommendation]:
        """选择适合当前档位的策略组合

        白皮书依据: Requirement 3.1-3.6

        选择逻辑：
        1. 筛选Z2H认证的策略
        2. 筛选适合当前档位的策略
        3. 根据Arena表现排序
        4. 考虑市场环境（可选）
        5. 返回Top N策略及推荐权重

        Args:
            tier: 当前资金档位
            market_regime: 市场环境（可选）
            top_n: 返回策略数量，默认5

        Returns:
            策略推荐列表
        """
        logger.info(f"开始选择策略 - 档位={tier}, " f"市场环境={market_regime}, " f"Top N={top_n}")

        # 1. 筛选Z2H认证的策略
        certified_strategies = self._filter_z2h_certified()

        if not certified_strategies:
            logger.warning("没有找到Z2H认证的策略")
            return []

        logger.info(f"Z2H认证策略数量: {len(certified_strategies)}")

        # 2. 筛选适合当前档位的策略
        tier_compatible_strategies = self._filter_tier_compatible(certified_strategies, tier)

        if not tier_compatible_strategies:
            logger.warning(f"没有找到适合{tier}档位的策略")
            return []

        logger.info(f"档位兼容策略数量: {len(tier_compatible_strategies)}")

        # 3. 根据Arena表现排序
        ranked_strategies = self._rank_by_arena_performance(tier_compatible_strategies, tier)

        # 4. 考虑市场环境（可选）
        if market_regime:
            ranked_strategies = self._adjust_for_market_regime(ranked_strategies, market_regime)

        # 5. 选择Top N策略
        selected_strategies = ranked_strategies[:top_n]

        # 6. 计算推荐权重
        recommendations = self._calculate_recommended_weights(selected_strategies, tier)

        logger.info(f"策略选择完成 - 选中{len(recommendations)}个策略")

        for rec in recommendations:
            logger.info(f"  • {rec.strategy_name}: " f"权重={rec.recommended_weight:.2%}, " f"原因={rec.reason}")

        return recommendations

    def _filter_z2h_certified(self) -> List[StrategyMetadata]:
        """筛选Z2H认证的策略（内部方法）

        白皮书依据: Requirement 3.3

        Returns:
            Z2H认证的策略列表
        """
        certified = []

        for metadata in self.strategy_pool.values():
            if metadata.z2h_certified:
                certified.append(metadata)

        return certified

    def _filter_tier_compatible(self, strategies: List[StrategyMetadata], tier: str) -> List[StrategyMetadata]:
        """筛选适合当前档位的策略（内部方法）

        白皮书依据: Requirement 3.1

        筛选逻辑：
        1. 策略在Arena中测试过该档位
        2. 策略在该档位有Arena测试结果
        3. 策略标记为multi_tier_compatible或best_tier匹配

        Args:
            strategies: 策略列表
            tier: 目标档位

        Returns:
            档位兼容的策略列表
        """
        compatible = []

        for metadata in strategies:
            # 检查是否在Arena中测试过该档位
            if tier not in metadata.arena_results:
                logger.debug(f"{metadata.strategy_name} 未在{tier}档位测试")
                continue

            # 检查是否多档位兼容或最佳档位匹配
            if metadata.multi_tier_compatible or metadata.best_tier == tier:
                compatible.append(metadata)
                logger.debug(f"{metadata.strategy_name} 兼容{tier}档位")
            else:
                logger.debug(f"{metadata.strategy_name} 最佳档位={metadata.best_tier}, " f"不兼容{tier}")

        return compatible

    def _rank_by_arena_performance(
        self, strategies: List[StrategyMetadata], tier: str
    ) -> List[Tuple[StrategyMetadata, float]]:
        """根据Arena表现排序（内部方法）

        白皮书依据: Requirement 3.2

        排序指标：
        1. 夏普比率（权重40%）
        2. 总收益率（权重30%）
        3. 最大回撤（权重20%，越小越好）
        4. 胜率（权重10%）

        Args:
            strategies: 策略列表
            tier: 目标档位

        Returns:
            排序后的策略列表，每个元素为(metadata, score)
        """
        scored_strategies = []

        for metadata in strategies:
            # 获取该档位的Arena测试结果
            arena_result = metadata.arena_results.get(tier)

            if not arena_result:
                logger.warning(f"{metadata.strategy_name} 缺少{tier}档位Arena结果")
                continue

            # 计算综合得分
            sharpe_ratio = arena_result.sharpe_ratio
            total_return = arena_result.total_return_pct
            max_drawdown = arena_result.max_drawdown_pct
            win_rate = arena_result.win_rate

            # 归一化指标（假设合理范围）
            sharpe_score = min(sharpe_ratio / 3.0, 1.0)  # 夏普3.0为满分
            return_score = min(total_return / 0.5, 1.0)  # 50%收益为满分
            drawdown_score = max(1.0 + max_drawdown / 0.3, 0.0)  # 30%回撤为0分
            win_rate_score = win_rate  # 胜率本身就是0-1

            # 加权综合得分
            score = sharpe_score * 0.40 + return_score * 0.30 + drawdown_score * 0.20 + win_rate_score * 0.10

            scored_strategies.append((metadata, score))

            logger.debug(
                f"{metadata.strategy_name} Arena得分={score:.3f} - "
                f"夏普={sharpe_ratio:.2f}, "
                f"收益={total_return*100:.1f}%, "
                f"回撤={max_drawdown*100:.1f}%, "
                f"胜率={win_rate*100:.1f}%"
            )

        # 按得分降序排序
        scored_strategies.sort(key=lambda x: x[1], reverse=True)

        return scored_strategies

    def _adjust_for_market_regime(
        self, ranked_strategies: List[Tuple[StrategyMetadata, float]], market_regime: str
    ) -> List[Tuple[StrategyMetadata, float]]:
        """根据市场环境调整策略排序（内部方法）

        白皮书依据: Requirement 3.4

        市场环境适配：
        - 牛市(bull): 偏好动量策略
        - 熊市(bear): 偏好均值回归策略
        - 震荡(sideways): 偏好套利策略
        - 未知(unknown): 不调整

        Args:
            ranked_strategies: 排序后的策略列表
            market_regime: 市场环境

        Returns:
            调整后的策略列表
        """
        if market_regime == "unknown":
            return ranked_strategies

        # 策略类型偏好权重
        regime_preferences = {
            "bull": {"momentum": 1.2, "mean_reversion": 0.8, "arbitrage": 1.0, "unknown": 1.0},
            "bear": {"momentum": 0.8, "mean_reversion": 1.2, "arbitrage": 1.0, "unknown": 1.0},
            "sideways": {"momentum": 0.9, "mean_reversion": 1.0, "arbitrage": 1.3, "unknown": 1.0},
        }

        preferences = regime_preferences.get(market_regime, {})

        if not preferences:
            logger.warning(f"未知的市场环境: {market_regime}")
            return ranked_strategies

        # 调整得分
        adjusted_strategies = []

        for metadata, score in ranked_strategies:
            strategy_type = metadata.strategy_type
            adjustment = preferences.get(strategy_type, 1.0)
            adjusted_score = score * adjustment

            adjusted_strategies.append((metadata, adjusted_score))

            if adjustment != 1.0:
                logger.debug(
                    f"{metadata.strategy_name} 市场环境调整 - "
                    f"类型={strategy_type}, "
                    f"调整系数={adjustment:.2f}, "
                    f"原始得分={score:.3f}, "
                    f"调整后={adjusted_score:.3f}"
                )

        # 重新排序
        adjusted_strategies.sort(key=lambda x: x[1], reverse=True)

        return adjusted_strategies

    def _calculate_recommended_weights(
        self, scored_strategies: List[Tuple[StrategyMetadata, float]], tier: str
    ) -> List[StrategyRecommendation]:
        """计算推荐权重（内部方法）

        白皮书依据: Requirement 3.6

        权重分配逻辑：
        1. 根据得分分配初始权重
        2. 确保权重之和为1.0
        3. 确保单个策略权重在[0.05, 0.40]范围内

        Args:
            scored_strategies: 评分后的策略列表
            tier: 目标档位

        Returns:
            策略推荐列表
        """
        if not scored_strategies:
            return []

        # 1. 根据得分分配初始权重（得分平方，增加差异）
        total_score_squared = sum(score**2 for _, score in scored_strategies)

        if total_score_squared == 0:
            # 所有得分为0，均分权重
            equal_weight = 1.0 / len(scored_strategies)
            initial_weights = [equal_weight] * len(scored_strategies)
        else:
            initial_weights = [(score**2) / total_score_squared for _, score in scored_strategies]

        # 2. 应用权重约束
        constrained_weights = self._apply_weight_constraints(initial_weights)

        # 3. 归一化权重（确保总和为1.0）
        total_weight = sum(constrained_weights)
        normalized_weights = [w / total_weight for w in constrained_weights]

        # 4. 生成推荐结果
        recommendations = []

        for (metadata, score), weight in zip(scored_strategies, normalized_weights):
            # 获取Arena表现
            arena_result = metadata.arena_results.get(tier)
            arena_performance = {
                "sharpe_ratio": arena_result.sharpe_ratio,
                "total_return_pct": arena_result.total_return_pct,
                "max_drawdown_pct": arena_result.max_drawdown_pct,
                "win_rate": arena_result.win_rate,
            }

            # 生成推荐原因
            reason = (
                f"Arena得分{score:.3f}, "
                f"夏普{arena_result.sharpe_ratio:.2f}, "
                f"收益{arena_result.total_return_pct*100:.1f}%"
            )

            recommendation = StrategyRecommendation(
                strategy_name=metadata.strategy_name,
                recommended_weight=weight,
                tier=tier,
                arena_performance=arena_performance,
                reason=reason,
            )

            recommendations.append(recommendation)

        return recommendations

    def _apply_weight_constraints(self, weights: List[float]) -> List[float]:
        """应用权重约束（内部方法）

        约束：
        - 单个策略权重 >= 0.05 (5%)
        - 单个策略权重 <= 0.40 (40%)

        Args:
            weights: 初始权重列表

        Returns:
            约束后的权重列表
        """
        constrained = []

        for weight in weights:
            # 应用下限
            if weight < 0.05:
                constrained.append(0.05)
            # 应用上限
            elif weight > 0.40:
                constrained.append(0.40)
            else:
                constrained.append(weight)

        return constrained

    def get_strategy_metadata(self, strategy_name: str) -> Optional[StrategyMetadata]:
        """获取策略元数据

        Args:
            strategy_name: 策略名称

        Returns:
            策略元数据，如果不存在则返回None
        """
        return self.strategy_pool.get(strategy_name)

    def list_all_strategies(self) -> List[str]:
        """列出所有已注册的策略

        Returns:
            策略名称列表
        """
        return list(self.strategy_pool.keys())

    def get_strategy_count(self) -> int:
        """获取策略池中的策略数量

        Returns:
            策略数量
        """
        return len(self.strategy_pool)
