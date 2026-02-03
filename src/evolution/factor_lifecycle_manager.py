"""
因子生命周期管理器 (Factor Lifecycle Manager)

白皮书依据: 第四章 4.2.4 因子生命周期管理

管理因子从发现到退役的完整生命周期
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

from src.evolution.arena.factor_performance_monitor import (
    DegradationSeverity,
    FactorDecayStatus,
    FactorPerformanceMonitor,
    PerformanceMetrics,
    RiskFactor,
)


class FactorStatus(Enum):
    """因子状态

    白皮书依据: 第四章 4.2.4 因子生命周期管理 - 状态定义
    """

    ACTIVE = "active"  # 活跃状态
    PAUSED = "paused"  # 暂停状态
    DEGRADING = "degrading"  # 衰减中
    RETIRED = "retired"  # 已退役
    ARCHIVED = "archived"  # 已归档


class MarketRegime(Enum):
    """市场环境

    白皮书依据: 第四章 4.2.4 因子生命周期管理 - 市场环境识别
    """

    BULL = "bull"  # 牛市
    BEAR = "bear"  # 熊市
    SIDEWAYS = "sideways"  # 震荡市
    HIGH_VOLATILITY = "high_volatility"  # 高波动
    LOW_VOLATILITY = "low_volatility"  # 低波动


@dataclass
class FactorInfo:
    """因子信息

    白皮书依据: 第四章 4.2.4 因子生命周期管理 - 因子元数据

    Attributes:
        factor_id: 因子ID
        name: 因子名称
        expression: 因子表达式
        status: 因子状态
        weight: 当前权重
        baseline_ic: 基准IC
        created_at: 创建时间
        last_updated: 最后更新时间
        arena_score: Arena评分
        z2h_certified: 是否Z2H认证
        regime_weights: 不同市场环境下的权重
    """

    factor_id: str
    name: str
    expression: str
    status: FactorStatus = FactorStatus.ACTIVE
    weight: float = 1.0
    baseline_ic: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    arena_score: float = 0.0
    z2h_certified: bool = False
    regime_weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class ArchivedFactor:
    """归档因子

    白皮书依据: 第四章 4.2.4 因子生命周期管理 - 因子归档

    Attributes:
        factor_info: 因子信息
        performance_history: 性能历史
        retirement_reason: 退役原因
        archived_at: 归档时间
        risk_factor: 转换后的风险因子（如果有）
    """

    factor_info: FactorInfo
    performance_history: List[PerformanceMetrics]
    retirement_reason: str
    archived_at: datetime = field(default_factory=datetime.now)
    risk_factor: Optional[RiskFactor] = None


@dataclass
class LifecycleReport:
    """生命周期报告

    白皮书依据: 第四章 4.2.4 因子生命周期管理 - 报告生成

    Attributes:
        report_date: 报告日期
        total_factors: 总因子数
        active_factors: 活跃因子数
        degrading_factors: 衰减因子数
        retired_factors: 退役因子数
        top_performers: 表现最佳因子
        worst_performers: 表现最差因子
        weight_changes: 权重变化
        attribution_analysis: 归因分析
    """

    report_date: datetime
    total_factors: int
    active_factors: int
    degrading_factors: int
    retired_factors: int
    top_performers: List[Tuple[str, float]]
    worst_performers: List[Tuple[str, float]]
    weight_changes: Dict[str, float]
    attribution_analysis: Dict[str, Any]


class FactorLifecycleManager:
    """因子生命周期管理器

    白皮书依据: 第四章 4.2.4 因子生命周期管理

    管理因子从发现到退役的完整生命周期:
    1. 因子注册和初始化
    2. 权重动态调整
    3. 市场环境适应
    4. 衰减检测和处理
    5. 因子退役和归档
    6. 风险因子转换
    7. 生命周期报告
    """

    # 权重调整参数
    WEIGHT_ADJUSTMENT_RATE = 0.1  # 权重调整速率
    MIN_WEIGHT = 0.1  # 最小权重
    MAX_WEIGHT = 3.0  # 最大权重

    # 退役阈值
    RETIREMENT_HEALTH_THRESHOLD = 0.3  # 健康评分退役阈值
    RETIREMENT_IC_DECAY_THRESHOLD = 0.7  # IC衰减退役阈值

    def __init__(self, performance_monitor: Optional[FactorPerformanceMonitor] = None):
        """初始化因子生命周期管理器

        白皮书依据: MIA编码铁律2 - 禁止简化和占位符

        Args:
            performance_monitor: 性能监控器实例，如果为None则创建新实例
        """
        logger.info("初始化FactorLifecycleManager")

        # 性能监控器
        self.performance_monitor = performance_monitor or FactorPerformanceMonitor()

        # 因子注册表
        self._factor_registry: Dict[str, FactorInfo] = {}

        # 归档因子
        self._archived_factors: Dict[str, ArchivedFactor] = {}

        # 当前市场环境
        self._current_regime: MarketRegime = MarketRegime.SIDEWAYS

        # 权重历史
        self._weight_history: Dict[str, List[Tuple[datetime, float]]] = {}

    def register_factor(  # pylint: disable=too-many-positional-arguments
        self,
        factor_id: str,
        name: str,
        expression: str,
        baseline_ic: float,
        arena_score: float = 0.0,
        z2h_certified: bool = False,
    ) -> FactorInfo:
        """注册新因子

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 因子注册
        **Validates: Requirements 7.6**

        Args:
            factor_id: 因子ID
            name: 因子名称
            expression: 因子表达式
            baseline_ic: 基准IC
            arena_score: Arena评分
            z2h_certified: 是否Z2H认证

        Returns:
            因子信息

        Raises:
            ValueError: 当因子ID已存在时
        """
        if factor_id in self._factor_registry:
            raise ValueError(f"因子{factor_id}已存在")

        if not factor_id:
            raise ValueError("因子ID不能为空")

        if not name:
            raise ValueError("因子名称不能为空")

        # 创建因子信息
        factor_info = FactorInfo(
            factor_id=factor_id,
            name=name,
            expression=expression,
            status=FactorStatus.ACTIVE,
            weight=1.0,
            baseline_ic=baseline_ic,
            arena_score=arena_score,
            z2h_certified=z2h_certified,
            regime_weights={
                MarketRegime.BULL.value: 1.0,
                MarketRegime.BEAR.value: 1.0,
                MarketRegime.SIDEWAYS.value: 1.0,
                MarketRegime.HIGH_VOLATILITY.value: 1.0,
                MarketRegime.LOW_VOLATILITY.value: 1.0,
            },
        )

        # 注册因子
        self._factor_registry[factor_id] = factor_info

        # 设置基准IC
        self.performance_monitor.set_baseline_ic(factor_id, baseline_ic)

        # 初始化权重历史
        self._weight_history[factor_id] = [(datetime.now(), 1.0)]

        logger.info(f"注册因子: {factor_id}, 名称: {name}, 基准IC: {baseline_ic:.4f}")

        return factor_info

    def get_factor(self, factor_id: str) -> Optional[FactorInfo]:
        """获取因子信息

        Args:
            factor_id: 因子ID

        Returns:
            因子信息，如果不存在则返回None
        """
        return self._factor_registry.get(factor_id)

    def get_active_factors(self) -> List[FactorInfo]:
        """获取所有活跃因子

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 活跃因子查询

        Returns:
            活跃因子列表
        """
        return [factor for factor in self._factor_registry.values() if factor.status == FactorStatus.ACTIVE]

    def get_critical_factors(self) -> List[FactorInfo]:
        """获取关键因子（Z2H认证且权重较高）

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 关键因子识别

        Returns:
            关键因子列表
        """
        return [
            factor
            for factor in self._factor_registry.values()
            if factor.z2h_certified and factor.weight >= 1.5 and factor.status == FactorStatus.ACTIVE
        ]

    def adapt_factor_weight(self, factor_id: str, recent_performance: PerformanceMetrics) -> float:
        """动态调整因子权重

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 权重动态调整
        **Validates: Requirements 7.4**

        根据最近表现动态调整因子权重:
        - 健康评分高 -> 增加权重
        - 健康评分低 -> 降低权重
        - 考虑市场环境

        Args:
            factor_id: 因子ID
            recent_performance: 最近性能指标

        Returns:
            调整后的权重

        Raises:
            ValueError: 当因子不存在时
        """
        factor = self._factor_registry.get(factor_id)
        if factor is None:
            raise ValueError(f"因子{factor_id}不存在")

        if factor.status != FactorStatus.ACTIVE:
            logger.warning(f"因子{factor_id}不是活跃状态，跳过权重调整")
            return factor.weight

        # 计算权重调整
        health_score = recent_performance.health_score
        current_weight = factor.weight

        # 基于健康评分调整
        if health_score > 0.7:
            # 表现良好，增加权重
            adjustment = self.WEIGHT_ADJUSTMENT_RATE * (health_score - 0.5)
        elif health_score < 0.5:
            # 表现不佳，降低权重
            adjustment = -self.WEIGHT_ADJUSTMENT_RATE * (0.5 - health_score)
        else:
            # 表现一般，小幅调整
            adjustment = self.WEIGHT_ADJUSTMENT_RATE * (health_score - 0.5) * 0.5

        # 考虑市场环境
        regime_weight = factor.regime_weights.get(self._current_regime.value, 1.0)
        adjustment *= regime_weight

        # 应用调整
        new_weight = current_weight + adjustment
        new_weight = float(np.clip(new_weight, self.MIN_WEIGHT, self.MAX_WEIGHT))

        # 更新因子权重
        factor.weight = new_weight
        factor.last_updated = datetime.now()

        # 记录权重历史
        self._weight_history[factor_id].append((datetime.now(), new_weight))

        # 限制历史记录长度
        if len(self._weight_history[factor_id]) > 100:
            self._weight_history[factor_id] = self._weight_history[factor_id][-100:]

        logger.debug(
            f"因子{factor_id}权重调整: {current_weight:.4f} -> {new_weight:.4f}, " f"健康评分: {health_score:.4f}"
        )

        return new_weight

    def set_regime_weight(self, factor_id: str, regime: MarketRegime, weight: float) -> None:
        """设置因子在特定市场环境下的权重

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 市场环境适应
        **Validates: Requirements 7.4**

        Args:
            factor_id: 因子ID
            regime: 市场环境
            weight: 权重

        Raises:
            ValueError: 当因子不存在或权重无效时
        """
        factor = self._factor_registry.get(factor_id)
        if factor is None:
            raise ValueError(f"因子{factor_id}不存在")

        if not 0 <= weight <= self.MAX_WEIGHT:
            raise ValueError(f"权重必须在[0, {self.MAX_WEIGHT}]范围内")

        factor.regime_weights[regime.value] = weight
        factor.last_updated = datetime.now()

        logger.info(f"设置因子{factor_id}在{regime.value}环境下的权重: {weight:.4f}")

    def update_market_regime(self, regime: MarketRegime) -> None:
        """更新当前市场环境

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 市场环境识别

        Args:
            regime: 新的市场环境
        """
        old_regime = self._current_regime
        self._current_regime = regime

        logger.info(f"市场环境更新: {old_regime.value} -> {regime.value}")

    async def handle_factor_decay(self, factor_id: str, decay_status: FactorDecayStatus) -> None:
        """处理因子衰减

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 衰减处理
        **Validates: Requirements 7.5**

        根据衰减严重程度采取不同措施:
        - 轻微衰减: 降低权重
        - 中度衰减: 暂停使用，重新测试
        - 严重衰减: 立即退役

        Args:
            factor_id: 因子ID
            decay_status: 衰减状态
        """
        factor = self._factor_registry.get(factor_id)
        if factor is None:
            logger.warning(f"因子{factor_id}不存在，跳过衰减处理")
            return

        if decay_status.severity == DegradationSeverity.MILD:
            # 轻微衰减：降低权重30%
            new_weight = factor.weight * 0.7
            factor.weight = max(new_weight, self.MIN_WEIGHT)
            factor.status = FactorStatus.DEGRADING
            logger.info(f"因子{factor_id}轻微衰减，权重降低至{factor.weight:.4f}")

        elif decay_status.severity == DegradationSeverity.MODERATE:
            # 中度衰减：暂停使用
            factor.status = FactorStatus.PAUSED
            logger.warning(f"因子{factor_id}中度衰减，已暂停使用")

        elif decay_status.severity == DegradationSeverity.SEVERE:
            # 严重衰减：立即退役
            await self.retire_factor(factor_id, "严重衰减")
            logger.error(f"因子{factor_id}严重衰减，已退役")

        factor.last_updated = datetime.now()

    async def retire_factor(
        self, factor_id: str, reason: str, convert_to_risk: bool = True
    ) -> Optional[ArchivedFactor]:
        """退役因子

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 因子退役
        **Validates: Requirements 7.5, 7.8**

        Args:
            factor_id: 因子ID
            reason: 退役原因
            convert_to_risk: 是否转换为风险因子

        Returns:
            归档因子信息
        """
        factor = self._factor_registry.get(factor_id)
        if factor is None:
            logger.warning(f"因子{factor_id}不存在，无法退役")
            return None

        # 更新状态
        factor.status = FactorStatus.RETIRED
        factor.last_updated = datetime.now()

        # 获取性能历史
        performance_history = self.performance_monitor.get_performance_history(factor_id)

        # 转换为风险因子（如果需要）
        risk_factor = None
        if convert_to_risk:
            risk_factor = self.performance_monitor.get_risk_factor(factor_id)

        # 创建归档记录
        archived = ArchivedFactor(
            factor_info=factor,
            performance_history=performance_history,
            retirement_reason=reason,
            archived_at=datetime.now(),
            risk_factor=risk_factor,
        )

        # 存储归档
        self._archived_factors[factor_id] = archived

        logger.info(f"因子{factor_id}已退役，原因: {reason}")

        return archived

    def archive_factor(self, factor_id: str) -> Optional[ArchivedFactor]:
        """归档因子

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 因子归档
        **Validates: Requirements 7.8**

        Args:
            factor_id: 因子ID

        Returns:
            归档因子信息
        """
        factor = self._factor_registry.get(factor_id)
        if factor is None:
            logger.warning(f"因子{factor_id}不存在，无法归档")
            return None

        if factor.status != FactorStatus.RETIRED:
            logger.warning(f"因子{factor_id}未退役，无法归档")
            return None

        # 更新状态
        factor.status = FactorStatus.ARCHIVED
        factor.last_updated = datetime.now()

        # 获取归档记录
        archived = self._archived_factors.get(factor_id)
        if archived:
            archived.factor_info.status = FactorStatus.ARCHIVED

        logger.info(f"因子{factor_id}已归档")

        return archived

    def get_archived_factor(self, factor_id: str) -> Optional[ArchivedFactor]:
        """获取归档因子

        Args:
            factor_id: 因子ID

        Returns:
            归档因子信息
        """
        return self._archived_factors.get(factor_id)

    def get_all_archived_factors(self) -> List[ArchivedFactor]:
        """获取所有归档因子

        Returns:
            归档因子列表
        """
        return list(self._archived_factors.values())

    def generate_lifecycle_report(self) -> LifecycleReport:
        """生成生命周期报告

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 报告生成
        **Validates: Requirements 7.7**

        Returns:
            生命周期报告
        """
        # 统计各状态因子数量
        total_factors = len(self._factor_registry)
        active_factors = len([f for f in self._factor_registry.values() if f.status == FactorStatus.ACTIVE])
        degrading_factors = len([f for f in self._factor_registry.values() if f.status == FactorStatus.DEGRADING])
        retired_factors = len(
            [f for f in self._factor_registry.values() if f.status in [FactorStatus.RETIRED, FactorStatus.ARCHIVED]]
        )

        # 获取表现最佳和最差因子
        active_factor_list = [f for f in self._factor_registry.values() if f.status == FactorStatus.ACTIVE]

        # 按权重排序
        sorted_by_weight = sorted(active_factor_list, key=lambda f: f.weight, reverse=True)
        top_performers = [(f.factor_id, f.weight) for f in sorted_by_weight[:5]]
        worst_performers = [(f.factor_id, f.weight) for f in sorted_by_weight[-5:]]

        # 计算权重变化
        weight_changes = {}
        for factor_id, history in self._weight_history.items():
            if len(history) >= 2:
                old_weight = history[-2][1]
                new_weight = history[-1][1]
                weight_changes[factor_id] = new_weight - old_weight

        # 归因分析
        attribution_analysis = {
            "total_weight": sum(f.weight for f in active_factor_list),
            "avg_weight": np.mean([f.weight for f in active_factor_list]) if active_factor_list else 0,
            "z2h_certified_count": len([f for f in active_factor_list if f.z2h_certified]),
            "regime": self._current_regime.value,
        }

        report = LifecycleReport(
            report_date=datetime.now(),
            total_factors=total_factors,
            active_factors=active_factors,
            degrading_factors=degrading_factors,
            retired_factors=retired_factors,
            top_performers=top_performers,
            worst_performers=worst_performers,
            weight_changes=weight_changes,
            attribution_analysis=attribution_analysis,
        )

        logger.info(
            f"生成生命周期报告: 总因子={total_factors}, "
            f"活跃={active_factors}, 衰减={degrading_factors}, 退役={retired_factors}"
        )

        return report

    def get_weight_history(self, factor_id: str) -> List[Tuple[datetime, float]]:
        """获取因子权重历史

        Args:
            factor_id: 因子ID

        Returns:
            权重历史列表 [(timestamp, weight), ...]
        """
        return self._weight_history.get(factor_id, [])

    async def monitor_lifecycle(self) -> None:
        """监控因子生命周期（主循环）

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 生命周期监控

        持续监控所有活跃因子的表现，检测衰减并采取相应措施
        """
        logger.info("启动因子生命周期监控")

        while True:
            try:
                # 获取所有活跃因子
                active_factors = self.get_active_factors()

                for factor in active_factors:
                    # 获取最新性能指标
                    history = self.performance_monitor.get_performance_history(factor.factor_id)

                    if not history:
                        continue

                    recent_performance = history[-1]

                    # 检测衰减
                    decay_status = self.performance_monitor.detect_degradation(
                        factor_id=factor.factor_id,
                        health_score=recent_performance.health_score,
                        ic_decay_rate=recent_performance.ic_decay_rate,
                    )

                    if decay_status.is_decaying:
                        await self.handle_factor_decay(factor.factor_id, decay_status)
                    else:
                        # 调整权重
                        self.adapt_factor_weight(factor.factor_id, recent_performance)

                # 每小时检查一次
                await asyncio.sleep(3600)

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"因子生命周期监控异常: {e}")
                await asyncio.sleep(300)
