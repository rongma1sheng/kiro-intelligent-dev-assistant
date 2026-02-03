"""Strategy Query Engine for Complex Queries

白皮书依据: 第四章 4.4.6 策略查询引擎
"""

from typing import Callable, List, Optional

from loguru import logger

from src.evolution.library.data_models import (
    LifecycleState,
    MarketRegime,
    StrategyMetadata,
    StrategyType,
)


class StrategyQueryEngine:
    """策略查询引擎

    白皮书依据: 第四章 4.4.6 策略查询引擎

    支持复杂的策略查询和过滤：
    - Z2H认证过滤
    - 策略类型过滤
    - 性能指标过滤
    - 市场状态过滤
    - 生命周期状态过滤
    """

    def __init__(self):
        """初始化查询引擎"""
        logger.info("StrategyQueryEngine初始化完成")

    def query(  # pylint: disable=too-many-positional-arguments
        self,
        strategies: List[StrategyMetadata],
        z2h_only: bool = False,
        strategy_types: Optional[List[StrategyType]] = None,
        min_sharpe: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        min_win_rate: Optional[float] = None,
        suitable_regimes: Optional[List[MarketRegime]] = None,
        lifecycle_states: Optional[List[LifecycleState]] = None,
        custom_filter: Optional[Callable[[StrategyMetadata], bool]] = None,
    ) -> List[StrategyMetadata]:
        """查询策略

        白皮书依据: 第四章 4.4.6 复合查询

        Args:
            strategies: 策略列表
            z2h_only: 是否只返回Z2H认证策略
            strategy_types: 策略类型列表
            min_sharpe: 最小夏普比率
            max_drawdown: 最大回撤上限（负数，如-0.15表示最多15%回撤）
            min_win_rate: 最小胜率
            suitable_regimes: 适用市场状态列表
            lifecycle_states: 生命周期状态列表
            custom_filter: 自定义过滤函数

        Returns:
            符合条件的策略列表
        """
        results = strategies.copy()

        # 过滤Z2H认证
        if z2h_only:
            results = self.filter_by_z2h(results)
            logger.debug(f"Z2H过滤后剩余: {len(results)}个策略")

        # 过滤策略类型
        if strategy_types:
            results = self.filter_by_type(results, strategy_types)
            logger.debug(f"类型过滤后剩余: {len(results)}个策略")

        # 过滤性能指标
        if min_sharpe is not None:
            results = self.filter_by_sharpe(results, min_sharpe)
            logger.debug(f"夏普比率过滤后剩余: {len(results)}个策略")

        if max_drawdown is not None:
            results = self.filter_by_drawdown(results, max_drawdown)
            logger.debug(f"回撤过滤后剩余: {len(results)}个策略")

        if min_win_rate is not None:
            results = self.filter_by_win_rate(results, min_win_rate)
            logger.debug(f"胜率过滤后剩余: {len(results)}个策略")

        # 过滤市场状态
        if suitable_regimes:
            results = self.filter_by_regime(results, suitable_regimes)
            logger.debug(f"市场状态过滤后剩余: {len(results)}个策略")

        # 过滤生命周期状态
        if lifecycle_states:
            results = self.filter_by_lifecycle(results, lifecycle_states)
            logger.debug(f"生命周期过滤后剩余: {len(results)}个策略")

        # 自定义过滤
        if custom_filter:
            results = [s for s in results if custom_filter(s)]
            logger.debug(f"自定义过滤后剩余: {len(results)}个策略")

        logger.info(f"查询完成: 从{len(strategies)}个策略中筛选出{len(results)}个符合条件的策略")

        return results

    def filter_by_z2h(self, strategies: List[StrategyMetadata]) -> List[StrategyMetadata]:
        """过滤Z2H认证策略

        白皮书依据: Requirement 5.1 - 只返回Z2H认证策略

        Args:
            strategies: 策略列表

        Returns:
            Z2H认证的策略列表
        """
        return [s for s in strategies if s.z2h_certified]

    def filter_by_type(
        self, strategies: List[StrategyMetadata], strategy_types: List[StrategyType]
    ) -> List[StrategyMetadata]:
        """按策略类型过滤

        白皮书依据: Requirement 5.2 - 按类型过滤

        Args:
            strategies: 策略列表
            strategy_types: 策略类型列表

        Returns:
            符合类型的策略列表
        """
        return [s for s in strategies if s.strategy_type in strategy_types]

    def filter_by_sharpe(self, strategies: List[StrategyMetadata], min_sharpe: float) -> List[StrategyMetadata]:
        """按夏普比率过滤

        白皮书依据: Requirement 5.3 - 按性能指标过滤

        Args:
            strategies: 策略列表
            min_sharpe: 最小夏普比率

        Returns:
            夏普比率 >= min_sharpe的策略列表
        """
        return [s for s in strategies if s.sharpe_ratio >= min_sharpe]

    def filter_by_drawdown(self, strategies: List[StrategyMetadata], max_drawdown: float) -> List[StrategyMetadata]:
        """按最大回撤过滤

        白皮书依据: Requirement 5.3 - 按性能指标过滤

        Args:
            strategies: 策略列表
            max_drawdown: 最大回撤上限（负数）

        Returns:
            回撤 >= max_drawdown的策略列表（回撤越小越好）
        """
        return [s for s in strategies if s.max_drawdown >= max_drawdown]

    def filter_by_win_rate(self, strategies: List[StrategyMetadata], min_win_rate: float) -> List[StrategyMetadata]:
        """按胜率过滤

        白皮书依据: Requirement 5.3 - 按性能指标过滤

        Args:
            strategies: 策略列表
            min_win_rate: 最小胜率

        Returns:
            胜率 >= min_win_rate的策略列表
        """
        return [s for s in strategies if s.win_rate >= min_win_rate]

    def filter_by_regime(
        self, strategies: List[StrategyMetadata], suitable_regimes: List[MarketRegime]
    ) -> List[StrategyMetadata]:
        """按市场状态过滤

        白皮书依据: Requirement 5.4 - 按市场状态过滤

        Args:
            strategies: 策略列表
            suitable_regimes: 适用市场状态列表

        Returns:
            适用于指定市场状态的策略列表
        """
        results = []
        for strategy in strategies:
            # 检查策略是否适用于任一指定的市场状态
            if any(regime in strategy.suitable_regimes for regime in suitable_regimes):
                results.append(strategy)

        return results

    def filter_by_lifecycle(
        self, strategies: List[StrategyMetadata], lifecycle_states: List[LifecycleState]
    ) -> List[StrategyMetadata]:
        """按生命周期状态过滤

        Args:
            strategies: 策略列表
            lifecycle_states: 生命周期状态列表

        Returns:
            符合生命周期状态的策略列表
        """
        return [s for s in strategies if s.lifecycle_state in lifecycle_states]

    def sort_by_sharpe(self, strategies: List[StrategyMetadata], descending: bool = True) -> List[StrategyMetadata]:
        """按夏普比率排序

        Args:
            strategies: 策略列表
            descending: 是否降序

        Returns:
            排序后的策略列表
        """
        return sorted(strategies, key=lambda s: s.sharpe_ratio, reverse=descending)

    def sort_by_arena_score(
        self, strategies: List[StrategyMetadata], descending: bool = True
    ) -> List[StrategyMetadata]:
        """按Arena评分排序

        Args:
            strategies: 策略列表
            descending: 是否降序

        Returns:
            排序后的策略列表
        """
        return sorted(strategies, key=lambda s: s.arena_score, reverse=descending)

    def get_top_strategies(
        self, strategies: List[StrategyMetadata], n: int = 10, sort_by: str = "sharpe"
    ) -> List[StrategyMetadata]:
        """获取Top N策略

        Args:
            strategies: 策略列表
            n: 返回数量
            sort_by: 排序依据（'sharpe', 'arena_score', 'win_rate'）

        Returns:
            Top N策略列表
        """
        if sort_by == "sharpe":
            sorted_strategies = self.sort_by_sharpe(strategies)
        elif sort_by == "arena_score":
            sorted_strategies = self.sort_by_arena_score(strategies)
        elif sort_by == "win_rate":
            sorted_strategies = sorted(strategies, key=lambda s: s.win_rate, reverse=True)
        else:
            logger.warning(f"未知的排序依据: {sort_by}，使用夏普比率排序")
            sorted_strategies = self.sort_by_sharpe(strategies)

        return sorted_strategies[:n]
