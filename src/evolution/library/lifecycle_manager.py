"""Lifecycle Manager for Strategy Library

白皮书依据: 第四章 4.4.3 策略生命周期管理
"""

from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from src.evolution.library.data_models import (
    LifecycleState,
    StrategyMetadata,
)


class LifecycleManager:
    """策略生命周期管理器

    白皮书依据: 第四章 4.4.3 策略生命周期管理

    管理策略的生命周期状态转换：
    ACTIVE → MONITORING → DEPRECATED → RETIRED
    """

    # 性能阈值
    IC_THRESHOLD = 0.03  # IC阈值
    IC_DECAY_DAYS = 30  # IC低于阈值的连续天数阈值
    SHARPE_THRESHOLD = 1.0  # 夏普比率阈值
    DRAWDOWN_THRESHOLD = -0.20  # 最大回撤阈值（-20%）

    def __init__(self):
        """初始化生命周期管理器"""
        logger.info("LifecycleManager初始化完成")

    def update_lifecycle_state(
        self,
        metadata: StrategyMetadata,
        recent_ic: Optional[float] = None,
        recent_sharpe: Optional[float] = None,
        recent_drawdown: Optional[float] = None,
    ) -> LifecycleState:
        """更新策略生命周期状态

        白皮书依据: 第四章 4.4.3 状态转换规则

        状态转换规则：
        1. ACTIVE → MONITORING: 性能下降但未达到废弃标准
        2. MONITORING → DEPRECATED: IC连续30天低于0.03
        3. DEPRECATED → RETIRED: 严重衰减
        4. MONITORING → ACTIVE: 性能恢复

        Args:
            metadata: 策略元数据
            recent_ic: 最近IC值
            recent_sharpe: 最近夏普比率
            recent_drawdown: 最近最大回撤

        Returns:
            更新后的生命周期状态
        """
        current_state = metadata.lifecycle_state
        new_state = current_state

        # 更新IC监控
        if recent_ic is not None:
            metadata.recent_ic = recent_ic

            if recent_ic < self.IC_THRESHOLD:
                metadata.ic_below_threshold_days += 1
            else:
                metadata.ic_below_threshold_days = 0

        # 状态转换逻辑
        if current_state == LifecycleState.ACTIVE:
            # ACTIVE → MONITORING: 性能下降
            if self._should_monitor(metadata, recent_ic, recent_sharpe, recent_drawdown):
                new_state = LifecycleState.MONITORING
                logger.warning(
                    f"策略进入监控状态: {metadata.strategy_id}, "
                    f"IC={recent_ic}, Sharpe={recent_sharpe}, DD={recent_drawdown}"
                )

        elif current_state == LifecycleState.MONITORING:
            # MONITORING → DEPRECATED: IC连续30天低于阈值
            if metadata.ic_below_threshold_days >= self.IC_DECAY_DAYS:
                new_state = LifecycleState.DEPRECATED
                logger.error(
                    f"策略被废弃: {metadata.strategy_id}, "
                    f"IC连续{metadata.ic_below_threshold_days}天低于{self.IC_THRESHOLD}"
                )

            # MONITORING → ACTIVE: 性能恢复
            elif self._should_reactivate(metadata, recent_ic, recent_sharpe):
                new_state = LifecycleState.ACTIVE
                logger.info(f"策略恢复活跃状态: {metadata.strategy_id}")

        elif current_state == LifecycleState.DEPRECATED:
            # DEPRECATED → RETIRED: 严重衰减
            if self._should_retire(metadata, recent_ic, recent_sharpe, recent_drawdown):
                new_state = LifecycleState.RETIRED
                logger.critical(f"策略退役: {metadata.strategy_id}")

        # 更新状态
        if new_state != current_state:
            metadata.lifecycle_state = new_state
            metadata.last_updated = datetime.now()

        return new_state

    def _should_monitor(
        self,
        metadata: StrategyMetadata,  # pylint: disable=unused-argument
        recent_ic: Optional[float],
        recent_sharpe: Optional[float],
        recent_drawdown: Optional[float],
    ) -> bool:
        """判断是否应该进入监控状态

        条件：
        - IC < 0.03
        - 或 Sharpe < 1.0
        - 或 回撤 < -15%
        """
        if recent_ic is not None and recent_ic < self.IC_THRESHOLD:
            return True

        if recent_sharpe is not None and recent_sharpe < self.SHARPE_THRESHOLD:
            return True

        if recent_drawdown is not None and recent_drawdown < -0.15:
            return True

        return False

    def _should_reactivate(
        self,
        metadata: StrategyMetadata,
        recent_ic: Optional[float],
        recent_sharpe: Optional[float],
    ) -> bool:
        """判断是否应该恢复活跃状态

        条件：
        - IC > 0.03
        - 且 Sharpe > 1.0
        - 且 IC连续低于阈值天数 = 0
        """
        if metadata.ic_below_threshold_days > 0:
            return False

        if recent_ic is not None and recent_ic <= self.IC_THRESHOLD:
            return False

        if recent_sharpe is not None and recent_sharpe <= self.SHARPE_THRESHOLD:
            return False

        return True

    def _should_retire(
        self,
        metadata: StrategyMetadata,
        recent_ic: Optional[float],  # pylint: disable=unused-argument
        recent_sharpe: Optional[float],
        recent_drawdown: Optional[float],
    ) -> bool:
        """判断是否应该退役

        条件：
        - IC连续60天低于0.03
        - 或 Sharpe < 0.5
        - 或 回撤 < -30%
        """
        if metadata.ic_below_threshold_days >= self.IC_DECAY_DAYS * 2:
            return True

        if recent_sharpe is not None and recent_sharpe < 0.5:
            return True

        if recent_drawdown is not None and recent_drawdown < -0.30:
            return True

        return False

    def can_allocate_capital(self, metadata: StrategyMetadata) -> bool:
        """判断策略是否可以分配新资金

        白皮书依据: Requirement 5.7 - 废弃策略禁止新资金

        Args:
            metadata: 策略元数据

        Returns:
            是否可以分配新资金
        """
        # DEPRECATED和RETIRED状态禁止新资金
        if metadata.lifecycle_state in [LifecycleState.DEPRECATED, LifecycleState.RETIRED]:
            logger.warning(f"策略{metadata.strategy_id}处于{metadata.lifecycle_state.value}状态，" f"禁止分配新资金")
            return False

        return True

    def get_capital_multiplier(self, metadata: StrategyMetadata) -> float:
        """获取资金分配乘数

        根据生命周期状态调整资金分配：
        - ACTIVE: 1.0（正常分配）
        - MONITORING: 0.5（减半分配）
        - DEPRECATED: 0.0（禁止分配）
        - RETIRED: 0.0（禁止分配）

        Args:
            metadata: 策略元数据

        Returns:
            资金分配乘数
        """
        multipliers = {
            LifecycleState.ACTIVE: 1.0,
            LifecycleState.MONITORING: 0.5,
            LifecycleState.DEPRECATED: 0.0,
            LifecycleState.RETIRED: 0.0,
        }

        return multipliers.get(metadata.lifecycle_state, 0.0)

    def get_statistics(self, strategies: List[StrategyMetadata]) -> Dict[str, int]:
        """获取生命周期统计信息

        Args:
            strategies: 策略列表

        Returns:
            各状态的策略数量
        """
        stats = {
            "ACTIVE": 0,
            "MONITORING": 0,
            "DEPRECATED": 0,
            "RETIRED": 0,
        }

        for strategy in strategies:
            state_name = strategy.lifecycle_state.value.upper()
            if state_name in stats:
                stats[state_name] += 1

        logger.info(
            f"生命周期统计: "
            f"ACTIVE={stats['ACTIVE']}, "
            f"MONITORING={stats['MONITORING']}, "
            f"DEPRECATED={stats['DEPRECATED']}, "
            f"RETIRED={stats['RETIRED']}"
        )

        return stats
