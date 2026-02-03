"""Risk Emergency Integration - 风险管理与应急响应集成

白皮书依据: 第十九章 19.3 应急响应流程, 第十二章 12.3 末日开关与应急响应
版本: v1.0.0
作者: MIA Team
日期: 2026-01-27

核心功能:
1. 集成风险识别系统与应急响应系统
2. 自动触发应急响应
3. 集成末日开关
4. 发布跨章节事件通知
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

from src.core.doomsday_switch import DoomsdaySwitch
from src.infra.cross_chapter_event_bus import CrossChapterEvent, CrossChapterEventBus, CrossChapterEventType
from src.infra.event_bus import EventPriority
from src.risk.emergency_response_system import AlertLevel, EmergencyProcedure, EmergencyResponseSystem
from src.risk.risk_identification_system import RiskEvent, RiskIdentificationSystem, RiskLevel


@dataclass
class RiskEmergencyStatus:
    """风险应急状态

    白皮书依据: 第十九章 19.3 应急响应流程

    Attributes:
        overall_risk_level: 整体风险等级
        is_doomsday_triggered: 末日开关是否触发
        active_alerts: 活跃告警数量
        emergency_procedures_executed: 已执行应急程序数量
        timestamp: 状态时间戳
    """

    overall_risk_level: str
    is_doomsday_triggered: bool
    active_alerts: int
    emergency_procedures_executed: int
    timestamp: datetime


class RiskEmergencyIntegration:
    """风险管理与应急响应集成

    白皮书依据: 第十九章 19.3 应急响应流程, 第十二章 12.3 末日开关与应急响应

    核心功能:
    1. 集成风险识别与应急响应
    2. 自动触发应急响应
    3. 集成末日开关
    4. 发布跨章节事件

    集成流程:
    1. 风险识别系统检测风险
    2. 根据风险等级触发应急响应
    3. 极高风险触发末日开关
    4. 发布跨章节事件通知监控系统

    使用示例:
        >>> integration = RiskEmergencyIntegration(
        ...     risk_system=risk_system,
        ...     emergency_system=emergency_system,
        ...     doomsday_switch=doomsday_switch,
        ...     event_bus=cross_chapter_bus
        ... )
        >>> await integration.initialize()
        >>>
        >>> # 监控风险并自动触发应急响应
        >>> await integration.monitor_and_respond()
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        risk_system: RiskIdentificationSystem,
        emergency_system: EmergencyResponseSystem,
        doomsday_switch: DoomsdaySwitch,
        event_bus: Optional[CrossChapterEventBus] = None,
        monitor_interval: int = 60,
    ):
        """初始化风险应急集成

        Args:
            risk_system: 风险识别系统实例
            emergency_system: 应急响应系统实例
            doomsday_switch: 末日开关实例
            event_bus: 跨章节事件总线实例
            monitor_interval: 监控间隔（秒），默认60秒

        Raises:
            ValueError: 当参数无效时
        """
        if risk_system is None:
            raise ValueError("risk_system不能为None")

        if emergency_system is None:
            raise ValueError("emergency_system不能为None")

        if doomsday_switch is None:
            raise ValueError("doomsday_switch不能为None")

        if monitor_interval < 1:
            raise ValueError(f"监控间隔必须 >= 1秒: {monitor_interval}")

        self.risk_system = risk_system
        self.emergency_system = emergency_system
        self.doomsday_switch = doomsday_switch
        self.event_bus = event_bus
        self.monitor_interval = monitor_interval

        # 统计信息
        self.stats = {
            "total_risks_detected": 0,
            "total_alerts_triggered": 0,
            "total_doomsday_checks": 0,
            "events_published": 0,
            "start_time": None,
        }

        # 风险等级到告警级别的映射
        self._risk_to_alert_mapping = {
            RiskLevel.LOW: None,  # 低风险不触发告警
            RiskLevel.MEDIUM: AlertLevel.WARNING,
            RiskLevel.HIGH: AlertLevel.DANGER,
            RiskLevel.CRITICAL: AlertLevel.CRITICAL,
        }

        logger.info(f"风险应急集成初始化完成: monitor_interval={monitor_interval}s")

    async def initialize(self):
        """初始化集成模块"""
        try:
            # 如果没有提供事件总线，获取全局实例
            if self.event_bus is None:
                from src.infra.cross_chapter_event_bus import (  # pylint: disable=import-outside-toplevel
                    get_cross_chapter_event_bus,
                )

                self.event_bus = await get_cross_chapter_event_bus()

            self.stats["start_time"] = datetime.now()

            logger.info("风险应急集成启动成功")

        except Exception as e:
            logger.error(f"风险应急集成初始化失败: {e}")
            raise

    async def monitor_and_respond(
        self, market_data: Optional[Dict[str, Any]] = None, system_data: Optional[Dict[str, Any]] = None
    ) -> Optional[EmergencyProcedure]:
        """监控风险并自动响应

        白皮书依据: 第十九章 19.3 应急响应流程

        Args:
            market_data: 市场数据（可选）
            system_data: 系统数据（可选）

        Returns:
            如果触发应急响应，返回EmergencyProcedure；否则返回None
        """
        try:
            # 1. 检查末日开关状态
            if self.doomsday_switch.is_triggered():
                logger.warning("[RiskEmergency] 末日开关已触发，跳过监控")
                return None

            # 2. 检查末日开关触发条件
            await self._check_doomsday_triggers()

            # 3. 监控各类风险
            risk_event = await self._monitor_all_risks(market_data, system_data)

            # 4. 如果检测到风险，触发应急响应
            if risk_event:
                self.stats["total_risks_detected"] += 1
                return await self._trigger_emergency_response(risk_event)

            return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"风险监控失败: {e}")
            return None

    async def _monitor_all_risks(
        self, market_data: Optional[Dict[str, Any]], system_data: Optional[Dict[str, Any]]
    ) -> Optional[RiskEvent]:
        """监控所有风险类型

        Args:
            market_data: 市场数据
            system_data: 系统数据

        Returns:
            如果检测到风险，返回RiskEvent；否则返回None
        """
        market_data = market_data or {}
        system_data = system_data or {}

        # 监控市场风险
        if "volatility" in market_data and "daily_pnl_ratio" in market_data:
            risk_event = self.risk_system.monitor_market_risk(
                volatility=market_data["volatility"],
                daily_pnl_ratio=market_data["daily_pnl_ratio"],
                market_trend=market_data.get("market_trend", "normal"),
            )
            if risk_event:
                return risk_event

        # 监控系统风险
        if all(k in system_data for k in ["redis_health", "gpu_health", "network_health"]):
            risk_event = self.risk_system.monitor_system_risk(
                redis_health=system_data["redis_health"],
                gpu_health=system_data["gpu_health"],
                network_health=system_data["network_health"],
            )
            if risk_event:
                return risk_event

        # 监控运营风险
        if all(k in system_data for k in ["strategy_sharpe", "data_quality_score", "overfitting_score"]):
            risk_event = self.risk_system.monitor_operational_risk(
                strategy_sharpe=system_data["strategy_sharpe"],
                data_quality_score=system_data["data_quality_score"],
                overfitting_score=system_data["overfitting_score"],
            )
            if risk_event:
                return risk_event

        # 监控流动性风险
        if all(k in market_data for k in ["bid_ask_spread", "volume_ratio", "market_depth"]):
            risk_event = self.risk_system.monitor_liquidity_risk(
                bid_ask_spread=market_data["bid_ask_spread"],
                volume_ratio=market_data["volume_ratio"],
                market_depth=market_data["market_depth"],
            )
            if risk_event:
                return risk_event

        # 监控对手方风险
        if all(k in system_data for k in ["broker_rating", "settlement_delay", "credit_exposure"]):
            risk_event = self.risk_system.monitor_counterparty_risk(
                broker_rating=system_data["broker_rating"],
                settlement_delay=system_data["settlement_delay"],
                credit_exposure=system_data["credit_exposure"],
            )
            if risk_event:
                return risk_event

        return None

    async def _trigger_emergency_response(self, risk_event: RiskEvent) -> EmergencyProcedure:
        """触发应急响应

        白皮书依据: 第十九章 19.3 应急响应流程

        Args:
            risk_event: 风险事件

        Returns:
            应急程序执行结果
        """
        # 映射风险等级到告警级别
        alert_level = self._risk_to_alert_mapping.get(risk_event.risk_level)

        if alert_level is None:
            logger.debug(f"[RiskEmergency] 低风险不触发告警: {risk_event.description}")
            return None

        # 触发告警
        procedure = self.emergency_system.trigger_alert(
            alert_level=alert_level,
            description=risk_event.description,
            context={
                "risk_type": risk_event.risk_type,
                "risk_level": risk_event.risk_level.value,
                "metrics": risk_event.metrics,
                "timestamp": risk_event.timestamp.isoformat(),
            },
        )

        self.stats["total_alerts_triggered"] += 1

        # 发布跨章节事件
        await self._publish_risk_event(risk_event, alert_level)

        # 如果是极高风险，考虑触发末日开关
        if risk_event.risk_level == RiskLevel.CRITICAL:
            await self._consider_doomsday_trigger(risk_event)

        return procedure

    async def _check_doomsday_triggers(self):
        """检查末日开关触发条件

        白皮书依据: 第十二章 12.3 末日开关与应急响应
        """
        self.stats["total_doomsday_checks"] += 1

        triggers_fired = self.doomsday_switch.check_triggers()

        if triggers_fired:
            reason = f"触发条件: {', '.join(triggers_fired)}"
            logger.critical(f"[RiskEmergency] 末日开关触发条件满足: {reason}")

            # 触发末日开关
            self.doomsday_switch.trigger(reason)

            # 发布跨章节事件
            await self._publish_doomsday_event(reason, triggers_fired)

    async def _consider_doomsday_trigger(self, risk_event: RiskEvent):
        """考虑触发末日开关

        白皮书依据: 第十二章 12.3 末日开关与应急响应

        Args:
            risk_event: 风险事件
        """
        # 仅在特定极高风险时触发末日开关
        critical_risk_types = ["market_risk", "system_risk"]

        if risk_event.risk_type in critical_risk_types:
            reason = f"极高风险: {risk_event.description}"
            logger.critical(f"[RiskEmergency] 考虑触发末日开关: {reason}")

            # 这里可以添加额外的判断逻辑
            # 例如：连续多次极高风险才触发
            # 目前简化为直接触发
            self.doomsday_switch.trigger(reason)

            # 发布跨章节事件
            await self._publish_doomsday_event(reason, [risk_event.description])

    async def _publish_risk_event(self, risk_event: RiskEvent, alert_level: AlertLevel):
        """发布风险事件

        白皮书依据: 第十二章 12.4 跨章节集成

        事件路由: Chapter 19 (Risk) -> Chapter 13 (Monitoring)

        Args:
            risk_event: 风险事件
            alert_level: 告警级别
        """
        try:
            if self.event_bus is None:
                logger.warning("事件总线未初始化，跳过事件发布")
                return

            # 确定事件优先级
            priority_mapping = {
                AlertLevel.WARNING: EventPriority.NORMAL,
                AlertLevel.DANGER: EventPriority.HIGH,
                AlertLevel.CRITICAL: EventPriority.CRITICAL,
            }

            event = CrossChapterEvent(
                event_type=CrossChapterEventType.RISK_LEVEL_CHANGED,
                source_chapter=19,
                target_chapter=13,
                data={
                    "risk_type": risk_event.risk_type,
                    "risk_level": risk_event.risk_level.value,
                    "alert_level": alert_level.value,
                    "description": risk_event.description,
                    "metrics": risk_event.metrics,
                    "timestamp": risk_event.timestamp.isoformat(),
                },
                priority=priority_mapping[alert_level],
            )

            success = await self.event_bus.publish(event)

            if success:
                self.stats["events_published"] += 1
                logger.info(
                    f"风险事件已发布 (Chapter 19 -> 13): " f"{risk_event.risk_level.value} - {risk_event.description}"
                )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"发布风险事件失败: {e}")

    async def _publish_doomsday_event(self, reason: str, triggers_fired: list):
        """发布末日开关事件

        白皮书依据: 第十二章 12.4 跨章节集成

        事件路由: Chapter 12 (Doomsday) -> Chapter 13 (Monitoring)

        Args:
            reason: 触发原因
            triggers_fired: 触发的条件列表
        """
        try:
            if self.event_bus is None:
                logger.warning("事件总线未初始化，跳过事件发布")
                return

            event = CrossChapterEvent(
                event_type=CrossChapterEventType.DOOMSDAY_TRIGGERED,
                source_chapter=12,
                target_chapter=13,
                data={"reason": reason, "triggers_fired": triggers_fired, "timestamp": datetime.now().isoformat()},
                priority=EventPriority.CRITICAL,
            )

            success = await self.event_bus.publish(event)

            if success:
                self.stats["events_published"] += 1
                logger.critical(f"末日开关事件已发布 (Chapter 12 -> 13): {reason}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"发布末日开关事件失败: {e}")

    async def get_integration_status(self) -> RiskEmergencyStatus:
        """获取集成状态

        Returns:
            集成状态
        """
        overall_risk_level = self.risk_system.get_overall_risk_level()
        is_doomsday_triggered = self.doomsday_switch.is_triggered()

        # 统计活跃告警（最近1小时）
        recent_procedures = self.emergency_system.get_emergency_history(hours=1)
        active_alerts = len(recent_procedures)

        # 统计已执行应急程序
        emergency_procedures_executed = len(self.emergency_system.emergency_history)

        return RiskEmergencyStatus(
            overall_risk_level=overall_risk_level.value,
            is_doomsday_triggered=is_doomsday_triggered,
            active_alerts=active_alerts,
            emergency_procedures_executed=emergency_procedures_executed,
            timestamp=datetime.now(),
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds() if self.stats["start_time"] else 0

        return {
            **self.stats,
            "uptime_seconds": uptime,
            "risk_detection_rate": self.stats["total_risks_detected"] / max(uptime, 1),
            "alert_rate": self.stats["total_alerts_triggered"] / max(uptime, 1),
        }


# 全局集成实例
_global_risk_emergency_integration: Optional[RiskEmergencyIntegration] = None


async def get_risk_emergency_integration(
    risk_system: Optional[RiskIdentificationSystem] = None,
    emergency_system: Optional[EmergencyResponseSystem] = None,
    doomsday_switch: Optional[DoomsdaySwitch] = None,
    event_bus: Optional[CrossChapterEventBus] = None,
) -> RiskEmergencyIntegration:
    """获取全局风险应急集成实例

    Args:
        risk_system: 风险识别系统实例
        emergency_system: 应急响应系统实例
        doomsday_switch: 末日开关实例
        event_bus: 跨章节事件总线实例

    Returns:
        风险应急集成实例
    """
    global _global_risk_emergency_integration  # pylint: disable=w0603

    if _global_risk_emergency_integration is None:
        if risk_system is None or emergency_system is None or doomsday_switch is None:
            raise ValueError("首次调用必须提供risk_system、emergency_system和doomsday_switch")

        _global_risk_emergency_integration = RiskEmergencyIntegration(
            risk_system=risk_system,
            emergency_system=emergency_system,
            doomsday_switch=doomsday_switch,
            event_bus=event_bus,
        )
        await _global_risk_emergency_integration.initialize()

    return _global_risk_emergency_integration
