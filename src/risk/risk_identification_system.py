"""风险识别系统

白皮书依据: 第十九章 19.1 风险识别与评估

风险类型:
1. 市场风险 (Market Risk): 价格波动、流动性风险
2. 系统风险 (System Risk): Redis故障、GPU崩溃、网络中断
3. 运营风险 (Operational Risk): 策略过拟合、数据质量问题
4. 流动性风险 (Liquidity Risk): 流动性枯竭、滑点过大
5. 对手方风险 (Counterparty Risk): 券商风险、清算风险
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from loguru import logger


class RiskLevel(Enum):
    """风险等级

    白皮书依据: 第十九章 19.1.2 风险评估矩阵
    """

    LOW = "low"  # 低风险
    MEDIUM = "medium"  # 中风险
    HIGH = "high"  # 高风险
    CRITICAL = "critical"  # 极高风险


@dataclass
class RiskEvent:
    """风险事件

    Attributes:
        risk_type: 风险类型
        risk_level: 风险等级
        description: 风险描述
        timestamp: 发生时间
        metrics: 相关指标
    """

    risk_type: str
    risk_level: RiskLevel
    description: str
    timestamp: datetime
    metrics: Dict[str, float]


class RiskIdentificationSystem:
    """风险识别系统

    白皮书依据: 第十九章 19.1 风险识别与评估

    功能:
    1. 监控市场风险 (价格波动、流动性)
    2. 监控系统风险 (Redis、GPU、网络)
    3. 监控运营风险 (策略、数据质量)
    4. 监控流动性风险 (流动性枯竭)
    5. 监控对手方风险 (券商、清算)

    Attributes:
        risk_thresholds: 风险阈值配置
        risk_events: 风险事件历史
    """

    def __init__(
        self,
        market_volatility_threshold: float = 0.05,
        daily_loss_threshold: float = 0.10,
        liquidity_threshold: float = 0.20,
        system_health_threshold: float = 0.80,
    ):
        """初始化风险识别系统

        白皮书依据: 第十九章 19.1.2 风险评估矩阵

        Args:
            market_volatility_threshold: 市场波动率阈值，默认5%
            daily_loss_threshold: 单日亏损阈值，默认10%
            liquidity_threshold: 流动性阈值，默认20%
            system_health_threshold: 系统健康度阈值，默认80%

        Raises:
            ValueError: 当阈值参数不在有效范围时
        """
        if not 0 < market_volatility_threshold < 1:
            raise ValueError(f"市场波动率阈值必须在(0, 1)范围内: {market_volatility_threshold}")

        if not 0 < daily_loss_threshold < 1:
            raise ValueError(f"单日亏损阈值必须在(0, 1)范围内: {daily_loss_threshold}")

        if not 0 < liquidity_threshold < 1:
            raise ValueError(f"流动性阈值必须在(0, 1)范围内: {liquidity_threshold}")

        if not 0 < system_health_threshold < 1:
            raise ValueError(f"系统健康度阈值必须在(0, 1)范围内: {system_health_threshold}")

        self.risk_thresholds = {
            "market_volatility": market_volatility_threshold,
            "daily_loss": daily_loss_threshold,
            "liquidity": liquidity_threshold,
            "system_health": system_health_threshold,
        }

        self.risk_events: List[RiskEvent] = []

        logger.info(
            f"风险识别系统初始化完成 - "
            f"市场波动率阈值: {market_volatility_threshold:.1%}, "
            f"单日亏损阈值: {daily_loss_threshold:.1%}, "
            f"流动性阈值: {liquidity_threshold:.1%}, "
            f"系统健康度阈值: {system_health_threshold:.1%}"
        )

    def monitor_market_risk(
        self, volatility: float, daily_pnl_ratio: float, market_trend: str = "normal"
    ) -> Optional[RiskEvent]:
        """监控市场风险

        白皮书依据: 第十九章 19.1.1 风险清单 - 业务风险

        Args:
            volatility: 市场波动率 (0-1)
            daily_pnl_ratio: 单日盈亏比例 (可为负)
            market_trend: 市场趋势 ("normal", "volatile", "crash")

        Returns:
            如果检测到风险，返回RiskEvent；否则返回None

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if not 0 <= volatility <= 1:
            raise ValueError(f"市场波动率必须在[0, 1]范围内: {volatility}")

        if not -1 <= daily_pnl_ratio <= 1:
            raise ValueError(f"单日盈亏比例必须在[-1, 1]范围内: {daily_pnl_ratio}")

        if market_trend not in ["normal", "volatile", "crash"]:
            raise ValueError(f"市场趋势必须是 'normal', 'volatile' 或 'crash': {market_trend}")

        # 检查市场波动率
        if volatility > self.risk_thresholds["market_volatility"]:
            risk_level = self._determine_risk_level(volatility, self.risk_thresholds["market_volatility"])

            event = RiskEvent(
                risk_type="market_risk",
                risk_level=risk_level,
                description=f"市场波动率过高: {volatility:.2%} > {self.risk_thresholds['market_volatility']:.2%}",
                timestamp=datetime.now(),
                metrics={"volatility": volatility, "threshold": self.risk_thresholds["market_volatility"]},
            )

            self.risk_events.append(event)
            logger.warning(f"[Risk] {event.description}")
            return event

        # 检查单日亏损
        if daily_pnl_ratio < -self.risk_thresholds["daily_loss"]:
            risk_level = RiskLevel.CRITICAL  # 单日亏损超阈值为极高风险

            event = RiskEvent(
                risk_type="market_risk",
                risk_level=risk_level,
                description=f"单日亏损超阈值: {daily_pnl_ratio:.2%} < -{self.risk_thresholds['daily_loss']:.2%}",
                timestamp=datetime.now(),
                metrics={"daily_pnl_ratio": daily_pnl_ratio, "threshold": -self.risk_thresholds["daily_loss"]},
            )

            self.risk_events.append(event)
            logger.error(f"[Risk] {event.description}")
            return event

        # 检查市场趋势
        if market_trend == "crash":
            event = RiskEvent(
                risk_type="market_risk",
                risk_level=RiskLevel.CRITICAL,
                description="市场崩盘风险",
                timestamp=datetime.now(),
                metrics={"market_trend": market_trend, "volatility": volatility},
            )

            self.risk_events.append(event)
            logger.error(f"[Risk] {event.description}")
            return event

        return None

    def monitor_system_risk(self, redis_health: float, gpu_health: float, network_health: float) -> Optional[RiskEvent]:
        """监控系统风险

        白皮书依据: 第十九章 19.1.1 风险清单 - 技术风险

        Args:
            redis_health: Redis健康度 (0-1)
            gpu_health: GPU健康度 (0-1)
            network_health: 网络健康度 (0-1)

        Returns:
            如果检测到风险，返回RiskEvent；否则返回None

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if not 0 <= redis_health <= 1:
            raise ValueError(f"Redis健康度必须在[0, 1]范围内: {redis_health}")

        if not 0 <= gpu_health <= 1:
            raise ValueError(f"GPU健康度必须在[0, 1]范围内: {gpu_health}")

        if not 0 <= network_health <= 1:
            raise ValueError(f"网络健康度必须在[0, 1]范围内: {network_health}")

        # 计算系统整体健康度（取最小值）
        overall_health = min(redis_health, gpu_health, network_health)

        if overall_health < self.risk_thresholds["system_health"]:
            # 确定具体故障组件
            failed_components = []
            if redis_health < self.risk_thresholds["system_health"]:
                failed_components.append(f"Redis({redis_health:.1%})")
            if gpu_health < self.risk_thresholds["system_health"]:
                failed_components.append(f"GPU({gpu_health:.1%})")
            if network_health < self.risk_thresholds["system_health"]:
                failed_components.append(f"Network({network_health:.1%})")

            risk_level = self._determine_risk_level(
                1 - overall_health, 1 - self.risk_thresholds["system_health"]  # 转换为风险值
            )

            event = RiskEvent(
                risk_type="system_risk",
                risk_level=risk_level,
                description=f"系统健康度低: {', '.join(failed_components)}",
                timestamp=datetime.now(),
                metrics={
                    "redis_health": redis_health,
                    "gpu_health": gpu_health,
                    "network_health": network_health,
                    "overall_health": overall_health,
                    "threshold": self.risk_thresholds["system_health"],
                },
            )

            self.risk_events.append(event)
            logger.warning(f"[Risk] {event.description}")
            return event

        return None

    def monitor_operational_risk(
        self, strategy_sharpe: float, data_quality_score: float, overfitting_score: float
    ) -> Optional[RiskEvent]:
        """监控运营风险

        白皮书依据: 第十九章 19.1.1 风险清单 - 业务风险

        Args:
            strategy_sharpe: 策略夏普比率
            data_quality_score: 数据质量评分 (0-1)
            overfitting_score: 过拟合评分 (0-1，越高越过拟合)

        Returns:
            如果检测到风险，返回RiskEvent；否则返回None

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if not 0 <= data_quality_score <= 1:
            raise ValueError(f"数据质量评分必须在[0, 1]范围内: {data_quality_score}")

        if not 0 <= overfitting_score <= 1:
            raise ValueError(f"过拟合评分必须在[0, 1]范围内: {overfitting_score}")

        # 检查策略夏普比率
        if strategy_sharpe < 1.0:
            risk_level = RiskLevel.MEDIUM if strategy_sharpe > 0.5 else RiskLevel.HIGH

            event = RiskEvent(
                risk_type="operational_risk",
                risk_level=risk_level,
                description=f"策略夏普比率过低: {strategy_sharpe:.2f} < 1.0",
                timestamp=datetime.now(),
                metrics={"strategy_sharpe": strategy_sharpe, "threshold": 1.0},
            )

            self.risk_events.append(event)
            logger.warning(f"[Risk] {event.description}")
            return event

        # 检查数据质量
        if data_quality_score < 0.80:
            risk_level = self._determine_risk_level(1 - data_quality_score, 1 - 0.80)

            event = RiskEvent(
                risk_type="operational_risk",
                risk_level=risk_level,
                description=f"数据质量过低: {data_quality_score:.2%} < 80%",
                timestamp=datetime.now(),
                metrics={"data_quality_score": data_quality_score, "threshold": 0.80},
            )

            self.risk_events.append(event)
            logger.warning(f"[Risk] {event.description}")
            return event

        # 检查过拟合
        if overfitting_score > 0.70:
            risk_level = self._determine_risk_level(overfitting_score, 0.70)

            event = RiskEvent(
                risk_type="operational_risk",
                risk_level=risk_level,
                description=f"策略过拟合风险: {overfitting_score:.2%} > 70%",
                timestamp=datetime.now(),
                metrics={"overfitting_score": overfitting_score, "threshold": 0.70},
            )

            self.risk_events.append(event)
            logger.warning(f"[Risk] {event.description}")
            return event

        return None

    def monitor_liquidity_risk(
        self, bid_ask_spread: float, volume_ratio: float, market_depth: float
    ) -> Optional[RiskEvent]:
        """监控流动性风险

        白皮书依据: 第十九章 19.1.1 风险清单 - 业务风险

        Args:
            bid_ask_spread: 买卖价差比例 (0-1)
            volume_ratio: 成交量比率 (当前/平均)
            market_depth: 市场深度评分 (0-1)

        Returns:
            如果检测到风险，返回RiskEvent；否则返回None

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if not 0 <= bid_ask_spread <= 1:
            raise ValueError(f"买卖价差比例必须在[0, 1]范围内: {bid_ask_spread}")

        if volume_ratio < 0:
            raise ValueError(f"成交量比率必须 >= 0: {volume_ratio}")

        if not 0 <= market_depth <= 1:
            raise ValueError(f"市场深度评分必须在[0, 1]范围内: {market_depth}")

        # 检查买卖价差
        if bid_ask_spread > self.risk_thresholds["liquidity"]:
            risk_level = self._determine_risk_level(bid_ask_spread, self.risk_thresholds["liquidity"])

            event = RiskEvent(
                risk_type="liquidity_risk",
                risk_level=risk_level,
                description=f"买卖价差过大: {bid_ask_spread:.2%} > {self.risk_thresholds['liquidity']:.2%}",
                timestamp=datetime.now(),
                metrics={"bid_ask_spread": bid_ask_spread, "threshold": self.risk_thresholds["liquidity"]},
            )

            self.risk_events.append(event)
            logger.warning(f"[Risk] {event.description}")
            return event

        # 检查成交量
        if volume_ratio < 0.30:  # 成交量低于平均30%
            risk_level = RiskLevel.MEDIUM if volume_ratio > 0.10 else RiskLevel.HIGH

            event = RiskEvent(
                risk_type="liquidity_risk",
                risk_level=risk_level,
                description=f"成交量过低: {volume_ratio:.2%} < 30%",
                timestamp=datetime.now(),
                metrics={"volume_ratio": volume_ratio, "threshold": 0.30},
            )

            self.risk_events.append(event)
            logger.warning(f"[Risk] {event.description}")
            return event

        # 检查市场深度
        if market_depth < 0.50:
            risk_level = self._determine_risk_level(1 - market_depth, 1 - 0.50)

            event = RiskEvent(
                risk_type="liquidity_risk",
                risk_level=risk_level,
                description=f"市场深度不足: {market_depth:.2%} < 50%",
                timestamp=datetime.now(),
                metrics={"market_depth": market_depth, "threshold": 0.50},
            )

            self.risk_events.append(event)
            logger.warning(f"[Risk] {event.description}")
            return event

        return None

    def monitor_counterparty_risk(
        self, broker_rating: float, settlement_delay: int, credit_exposure: float
    ) -> Optional[RiskEvent]:
        """监控对手方风险

        白皮书依据: 第十九章 19.1.1 风险清单 - 合规风险

        Args:
            broker_rating: 券商评级 (0-1，1为最高)
            settlement_delay: 结算延迟天数
            credit_exposure: 信用敞口比例 (0-1)

        Returns:
            如果检测到风险，返回RiskEvent；否则返回None

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if not 0 <= broker_rating <= 1:
            raise ValueError(f"券商评级必须在[0, 1]范围内: {broker_rating}")

        if settlement_delay < 0:
            raise ValueError(f"结算延迟天数必须 >= 0: {settlement_delay}")

        if not 0 <= credit_exposure <= 1:
            raise ValueError(f"信用敞口比例必须在[0, 1]范围内: {credit_exposure}")

        # 检查券商评级
        if broker_rating < 0.70:
            risk_level = self._determine_risk_level(1 - broker_rating, 1 - 0.70)

            event = RiskEvent(
                risk_type="counterparty_risk",
                risk_level=risk_level,
                description=f"券商评级过低: {broker_rating:.2%} < 70%",
                timestamp=datetime.now(),
                metrics={"broker_rating": broker_rating, "threshold": 0.70},
            )

            self.risk_events.append(event)
            logger.warning(f"[Risk] {event.description}")
            return event

        # 检查结算延迟
        if settlement_delay > 2:  # T+2以上
            risk_level = RiskLevel.MEDIUM if settlement_delay <= 5 else RiskLevel.HIGH

            event = RiskEvent(
                risk_type="counterparty_risk",
                risk_level=risk_level,
                description=f"结算延迟过长: T+{settlement_delay} > T+2",
                timestamp=datetime.now(),
                metrics={"settlement_delay": settlement_delay, "threshold": 2},
            )

            self.risk_events.append(event)
            logger.warning(f"[Risk] {event.description}")
            return event

        # 检查信用敞口
        if credit_exposure > 0.30:
            risk_level = self._determine_risk_level(credit_exposure, 0.30)

            event = RiskEvent(
                risk_type="counterparty_risk",
                risk_level=risk_level,
                description=f"信用敞口过大: {credit_exposure:.2%} > 30%",
                timestamp=datetime.now(),
                metrics={"credit_exposure": credit_exposure, "threshold": 0.30},
            )

            self.risk_events.append(event)
            logger.warning(f"[Risk] {event.description}")
            return event

        return None

    def get_overall_risk_level(self) -> RiskLevel:
        """获取整体风险等级

        白皮书依据: 第十九章 19.1.2 风险评估矩阵

        Returns:
            整体风险等级（取所有风险事件中的最高等级）
        """
        if not self.risk_events:
            return RiskLevel.LOW

        # 获取最近的风险事件（最近1小时内）
        recent_events = [
            event for event in self.risk_events if (datetime.now() - event.timestamp).total_seconds() < 3600
        ]

        if not recent_events:
            return RiskLevel.LOW

        # 返回最高风险等级
        risk_levels = [event.risk_level for event in recent_events]

        if RiskLevel.CRITICAL in risk_levels:  # pylint: disable=no-else-return
            return RiskLevel.CRITICAL
        elif RiskLevel.HIGH in risk_levels:
            return RiskLevel.HIGH
        elif RiskLevel.MEDIUM in risk_levels:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def get_risk_summary(self) -> Dict[str, any]:
        """获取风险摘要

        Returns:
            风险摘要字典，包含各类风险的统计信息
        """
        # 统计各类风险事件数量
        risk_counts = {
            "market_risk": 0,
            "system_risk": 0,
            "operational_risk": 0,
            "liquidity_risk": 0,
            "counterparty_risk": 0,
        }

        # 统计各风险等级数量
        level_counts = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 0, RiskLevel.HIGH: 0, RiskLevel.CRITICAL: 0}

        # 获取最近1小时的风险事件
        recent_events = [
            event for event in self.risk_events if (datetime.now() - event.timestamp).total_seconds() < 3600
        ]

        for event in recent_events:
            risk_counts[event.risk_type] += 1
            level_counts[event.risk_level] += 1

        return {
            "overall_risk_level": self.get_overall_risk_level().value,
            "total_events": len(recent_events),
            "risk_counts": risk_counts,
            "level_counts": {level.value: count for level, count in level_counts.items()},
            "recent_events": [
                {
                    "risk_type": event.risk_type,
                    "risk_level": event.risk_level.value,
                    "description": event.description,
                    "timestamp": event.timestamp.isoformat(),
                }
                for event in recent_events[-5:]  # 最近5个事件
            ],
        }

    def clear_old_events(self, hours: int = 24):
        """清理旧的风险事件

        Args:
            hours: 保留最近多少小时的事件，默认24小时

        Raises:
            ValueError: 当hours <= 0时
        """
        if hours <= 0:
            raise ValueError(f"保留时间必须 > 0: {hours}")

        cutoff_time = datetime.now()
        cutoff_seconds = hours * 3600

        initial_count = len(self.risk_events)

        self.risk_events = [
            event for event in self.risk_events if (cutoff_time - event.timestamp).total_seconds() < cutoff_seconds
        ]

        removed_count = initial_count - len(self.risk_events)

        if removed_count > 0:
            logger.info(f"清理了 {removed_count} 个旧风险事件（保留最近{hours}小时）")

    def _determine_risk_level(self, value: float, threshold: float) -> RiskLevel:
        """根据值和阈值确定风险等级

        Args:
            value: 当前值
            threshold: 阈值

        Returns:
            风险等级
        """
        ratio = value / threshold

        if ratio >= 2.0:  # pylint: disable=no-else-return
            return RiskLevel.CRITICAL
        elif ratio >= 1.5:
            return RiskLevel.HIGH
        elif ratio >= 1.0:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
