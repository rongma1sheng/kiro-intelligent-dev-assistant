"""OrderRiskIntegration (订单风控集成) - 订单管理与风控系统的集成层

白皮书依据: 第六章 6.3 风险控制系统

核心功能:
- 订单提交前风控验证
- 风控规则检查
- 违规拒绝与告警
- 保护性操作触发
- 风控告警日志记录
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from src.execution.order_manager import Order, OrderManager, OrderResult, OrderSide, OrderStatus, OrderType
from src.execution.risk_control_system import RiskCheckResult, RiskCheckType, RiskControlSystem, RiskLevel


class AlertLevel(Enum):
    """告警级别"""

    INFO = "info"  # 信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 危急


class AlertType(Enum):
    """告警类型"""

    POSITION_LIMIT = "position_limit"  # 仓位限制
    SECTOR_LIMIT = "sector_limit"  # 行业限制
    STOP_LOSS = "stop_loss"  # 止损触发
    TAKE_PROFIT = "take_profit"  # 止盈触发
    LIQUIDITY = "liquidity"  # 流动性不足
    DAILY_LOSS = "daily_loss"  # 日亏损超限
    CAPITAL_INSUFFICIENT = "capital_insufficient"  # 资金不足
    EMERGENCY_SHUTDOWN = "emergency_shutdown"  # 紧急熔断
    RISK_VIOLATION = "risk_violation"  # 风控违规


@dataclass
class RiskAlert:
    """风控告警

    白皮书依据: 第六章 6.3 风控告警
    """

    alert_id: str
    alert_type: AlertType
    alert_level: AlertLevel
    message: str
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "alert_level": self.alert_level.value,
            "message": self.message,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
        }


@dataclass
class ProtectiveAction:
    """保护性操作

    白皮书依据: 第六章 6.3 保护性操作
    """

    action_id: str
    action_type: str  # cancel_order, reduce_position, emergency_shutdown
    reason: str
    target_order_id: Optional[str] = None
    target_symbol: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    executed: bool = False
    result: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "reason": self.reason,
            "target_order_id": self.target_order_id,
            "target_symbol": self.target_symbol,
            "details": self.details,
            "executed": self.executed,
            "result": self.result,
            "timestamp": self.timestamp.isoformat(),
        }


class OrderRiskIntegration:
    """订单风控集成

    白皮书依据: 第六章 6.3 风险控制系统

    提供订单管理与风控系统之间的集成层，实现订单提交前验证、
    风控规则检查、违规拒绝、告警和保护性操作。

    Attributes:
        order_manager: 订单管理器
        risk_control: 风控系统
        alerts: 告警列表
        protective_actions: 保护性操作列表
        event_bus: 事件总线
    """

    def __init__(
        self,
        order_manager: OrderManager,
        risk_control: RiskControlSystem,
        event_bus: Optional[Any] = None,
        auto_protective_actions: bool = True,
    ):
        """初始化订单风控集成

        白皮书依据: 第六章 6.3 风险控制系统

        Args:
            order_manager: 订单管理器
            risk_control: 风控系统
            event_bus: 事件总线
            auto_protective_actions: 是否自动执行保护性操作

        Raises:
            ValueError: 当order_manager或risk_control为None时
        """
        if order_manager is None:
            raise ValueError("order_manager不能为None")

        if risk_control is None:
            raise ValueError("risk_control不能为None")

        self.order_manager = order_manager
        self.risk_control = risk_control
        self.event_bus = event_bus
        self.auto_protective_actions = auto_protective_actions

        # 告警列表
        self.alerts: List[RiskAlert] = []

        # 保护性操作列表
        self.protective_actions: List[ProtectiveAction] = []

        # 告警回调
        self._alert_callbacks: List[Callable[[RiskAlert], None]] = []

        # 保护性操作回调
        self._action_callbacks: List[Callable[[ProtectiveAction], None]] = []

        # 告警计数器
        self._alert_counter = 0

        # 保护性操作计数器
        self._action_counter = 0

        # 注册风控回调
        self.risk_control.register_risk_callback(self._on_risk_check_failed)

        # 将风控系统设置为订单管理器的风险管理器
        self.order_manager.risk_manager = self.risk_control

        logger.info(f"OrderRiskIntegration初始化完成 - " f"auto_protective_actions={auto_protective_actions}")

    def register_alert_callback(self, callback: Callable[[RiskAlert], None]) -> None:
        """注册告警回调

        Args:
            callback: 回调函数
        """
        self._alert_callbacks.append(callback)

    def register_action_callback(self, callback: Callable[[ProtectiveAction], None]) -> None:
        """注册保护性操作回调

        Args:
            callback: 回调函数
        """
        self._action_callbacks.append(callback)

    async def validate_and_submit_order(  # pylint: disable=too-many-positional-arguments
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        strategy_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OrderResult:
        """验证并提交订单

        白皮书依据: 第六章 6.3 订单风控验证

        在提交订单前进行完整的风控验证，包括仓位限制、行业限制、
        流动性约束、日亏损限制等检查。

        Args:
            symbol: 股票代码
            side: 买卖方向
            order_type: 订单类型
            quantity: 数量
            price: 价格（限价单必填）
            stop_price: 止损价（止损单必填）
            strategy_id: 策略ID
            metadata: 元数据

        Returns:
            订单结果
        """
        logger.info(f"订单风控验证 - {symbol}: {side.value} {quantity}@{price or 'MARKET'}")

        # 检查紧急熔断状态
        if self.risk_control.emergency_shutdown_active:
            alert = self._create_alert(
                alert_type=AlertType.EMERGENCY_SHUTDOWN,
                alert_level=AlertLevel.CRITICAL,
                message=f"紧急熔断已激活: {self.risk_control.shutdown_reason}",
                symbol=symbol,
                details={"shutdown_reason": self.risk_control.shutdown_reason},
            )
            self._trigger_alert(alert)

            return OrderResult(
                success=False,
                order_id="",
                message=f"紧急熔断已激活: {self.risk_control.shutdown_reason}",
                status=OrderStatus.REJECTED,
            )

        # 提交订单（OrderManager会调用risk_control.check_order）
        result = await self.order_manager.submit_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            strategy_id=strategy_id,
            metadata=metadata,
        )

        # 如果订单被拒绝，记录告警
        if not result.success and result.status == OrderStatus.REJECTED:
            if "风控违规" in result.message:
                alert = self._create_alert(
                    alert_type=AlertType.RISK_VIOLATION,
                    alert_level=AlertLevel.ERROR,
                    message=result.message,
                    order_id=result.order_id,
                    symbol=symbol,
                    details={"reason": result.message},
                )
                self._trigger_alert(alert)

        return result

    async def check_order_risk(self, order: Order) -> Dict[str, Any]:
        """检查订单风控

        白皮书依据: 第六章 6.3 风控规则检查

        对订单进行完整的风控检查，返回检查结果。

        Args:
            order: 订单对象

        Returns:
            风控检查结果
        """
        result = await self.risk_control.check_order(order)

        if not result.get("passed", False):
            # 解析失败原因并创建相应告警
            reason = result.get("reason", "")

            if "资金不足" in reason:
                alert_type = AlertType.CAPITAL_INSUFFICIENT
            elif "总仓位超限" in reason or "单股仓位超限" in reason:
                alert_type = AlertType.POSITION_LIMIT
            elif "行业仓位超限" in reason:
                alert_type = AlertType.SECTOR_LIMIT
            elif "流动性不足" in reason:
                alert_type = AlertType.LIQUIDITY
            elif "日亏损超限" in reason:
                alert_type = AlertType.DAILY_LOSS
            else:
                alert_type = AlertType.RISK_VIOLATION

            # 确定告警级别
            risk_level = result.get("risk_level", "medium")
            if risk_level == "critical":
                alert_level = AlertLevel.CRITICAL
            elif risk_level == "high":
                alert_level = AlertLevel.ERROR
            elif risk_level == "medium":
                alert_level = AlertLevel.WARNING
            else:
                alert_level = AlertLevel.INFO

            alert = self._create_alert(
                alert_type=alert_type,
                alert_level=alert_level,
                message=reason,
                order_id=order.order_id,
                symbol=order.symbol,
                details=result.get("failed_checks", []),
            )
            self._trigger_alert(alert)

        return result

    async def monitor_positions(self) -> List[Dict[str, Any]]:
        """监控所有持仓

        白皮书依据: 第六章 6.3 事中风控

        监控所有持仓的风险状态，触发止损止盈告警。

        Returns:
            持仓风险列表
        """
        position_risks = []

        for symbol in list(self.risk_control.positions.keys()):
            try:
                position_risk = await self.risk_control.monitor_position(symbol)
                position_risks.append(position_risk.to_dict())

                # 检查止损触发
                if position_risk.stop_loss_triggered:
                    alert = self._create_alert(
                        alert_type=AlertType.STOP_LOSS,
                        alert_level=AlertLevel.CRITICAL,
                        message=f"止损触发 - {symbol}: 亏损{position_risk.unrealized_pnl_pct:.1%}",
                        symbol=symbol,
                        details=position_risk.to_dict(),
                    )
                    self._trigger_alert(alert)

                    # 自动执行保护性操作
                    if self.auto_protective_actions:
                        await self._execute_stop_loss_action(symbol, position_risk)

                # 检查止盈触发
                if position_risk.take_profit_triggered:
                    alert = self._create_alert(
                        alert_type=AlertType.TAKE_PROFIT,
                        alert_level=AlertLevel.INFO,
                        message=f"止盈触发 - {symbol}: 盈利{position_risk.unrealized_pnl_pct:.1%}",
                        symbol=symbol,
                        details=position_risk.to_dict(),
                    )
                    self._trigger_alert(alert)

                    # 自动执行保护性操作
                    if self.auto_protective_actions:
                        await self._execute_take_profit_action(symbol, position_risk)

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"监控持仓异常 - {symbol}: {e}")

        return position_risks

    async def check_risk_limits(self) -> Dict[str, Any]:
        """检查风险限额

        白皮书依据: 第六章 6.3 风险限额

        检查所有风险限额，对突破的限额发出告警。

        Returns:
            风险限额检查结果
        """
        limits = await self.risk_control.check_risk_limits()

        breached_limits = []
        for name, limit in limits.items():
            if limit.breached:
                breached_limits.append({"name": name, "limit": limit.to_dict()})

                # 确定告警类型
                if "position" in name:
                    alert_type = AlertType.POSITION_LIMIT
                elif "sector" in name:
                    alert_type = AlertType.SECTOR_LIMIT
                elif "daily_loss" in name:
                    alert_type = AlertType.DAILY_LOSS
                else:
                    alert_type = AlertType.RISK_VIOLATION

                alert = self._create_alert(
                    alert_type=alert_type,
                    alert_level=AlertLevel.ERROR,
                    message=f"风险限额突破 - {name}: {limit.current_value:.1%} > {limit.limit_value:.1%}",
                    details=limit.to_dict(),
                )
                self._trigger_alert(alert)

        return {
            "limits": {k: v.to_dict() for k, v in limits.items()},
            "breached_limits": breached_limits,
            "risk_level": self.risk_control.risk_level.name.lower(),
        }

    async def trigger_emergency_shutdown(self, reason: str) -> None:
        """触发紧急熔断

        白皮书依据: 第六章 6.3 紧急熔断

        Args:
            reason: 熔断原因
        """
        logger.critical(f"触发紧急熔断: {reason}")

        # 激活风控系统的紧急熔断
        await self.risk_control.emergency_shutdown(reason)

        # 创建告警
        alert = self._create_alert(
            alert_type=AlertType.EMERGENCY_SHUTDOWN,
            alert_level=AlertLevel.CRITICAL,
            message=f"紧急熔断已激活: {reason}",
            details={"reason": reason},
        )
        self._trigger_alert(alert)

        # 取消所有活跃订单
        if self.auto_protective_actions:
            await self._cancel_all_active_orders(reason)

        # 发布事件
        if self.event_bus:
            await self.event_bus.publish(
                {
                    "event_type": "emergency_shutdown_triggered",
                    "reason": reason,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    async def deactivate_emergency_shutdown(self) -> None:
        """解除紧急熔断"""
        await self.risk_control.deactivate_emergency_shutdown()

        logger.info("紧急熔断已解除")

        # 发布事件
        if self.event_bus:
            await self.event_bus.publish(
                {"event_type": "emergency_shutdown_deactivated", "timestamp": datetime.now().isoformat()}
            )

    async def _execute_stop_loss_action(self, symbol: str, position_risk: Any) -> None:
        """执行止损保护性操作

        Args:
            symbol: 股票代码
            position_risk: 持仓风险
        """
        action = self._create_protective_action(
            action_type="reduce_position",
            reason=f"止损触发 - 亏损{position_risk.unrealized_pnl_pct:.1%}",
            target_symbol=symbol,
            details={"position_risk": position_risk.to_dict(), "action": "sell_all"},
        )

        try:
            # 创建卖出订单
            position = self.risk_control.get_position(symbol)
            if position and position.quantity > 0:
                # 调整数量为100的倍数
                sell_quantity = int(position.quantity // 100) * 100

                if sell_quantity > 0:
                    result = await self.order_manager.submit_order(
                        symbol=symbol,
                        side=OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        quantity=sell_quantity,
                        strategy_id="stop_loss_protection",
                        metadata={"protective_action": True},
                    )

                    action.executed = True
                    action.result = f"订单已提交: {result.order_id}"

                    logger.info(f"止损保护性操作执行 - {symbol}: 卖出{sell_quantity}股")
                else:
                    action.executed = False
                    action.result = "持仓数量不足100股，无法卖出"
            else:
                action.executed = False
                action.result = "持仓不存在或数量为0"

        except Exception as e:  # pylint: disable=broad-exception-caught
            action.executed = False
            action.result = f"执行失败: {e}"
            logger.error(f"止损保护性操作失败 - {symbol}: {e}")

        self.protective_actions.append(action)
        self._trigger_action_callbacks(action)

    async def _execute_take_profit_action(self, symbol: str, position_risk: Any) -> None:
        """执行止盈保护性操作

        Args:
            symbol: 股票代码
            position_risk: 持仓风险
        """
        action = self._create_protective_action(
            action_type="reduce_position",
            reason=f"止盈触发 - 盈利{position_risk.unrealized_pnl_pct:.1%}",
            target_symbol=symbol,
            details={"position_risk": position_risk.to_dict(), "action": "sell_partial"},  # 止盈时可以部分卖出
        )

        try:
            # 创建卖出订单（止盈时卖出50%）
            position = self.risk_control.get_position(symbol)
            if position and position.quantity > 0:
                # 卖出50%，调整为100的倍数
                sell_quantity = int((position.quantity * 0.5) // 100) * 100

                if sell_quantity > 0:
                    result = await self.order_manager.submit_order(
                        symbol=symbol,
                        side=OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        quantity=sell_quantity,
                        strategy_id="take_profit_protection",
                        metadata={"protective_action": True},
                    )

                    action.executed = True
                    action.result = f"订单已提交: {result.order_id}"

                    logger.info(f"止盈保护性操作执行 - {symbol}: 卖出{sell_quantity}股")
                else:
                    action.executed = False
                    action.result = "持仓数量不足200股，无法部分卖出"
            else:
                action.executed = False
                action.result = "持仓不存在或数量为0"

        except Exception as e:  # pylint: disable=broad-exception-caught
            action.executed = False
            action.result = f"执行失败: {e}"
            logger.error(f"止盈保护性操作失败 - {symbol}: {e}")

        self.protective_actions.append(action)
        self._trigger_action_callbacks(action)

    async def _cancel_all_active_orders(self, reason: str) -> None:
        """取消所有活跃订单

        Args:
            reason: 取消原因
        """
        active_orders = self.order_manager.get_active_orders()

        for order in active_orders:
            action = self._create_protective_action(
                action_type="cancel_order",
                reason=f"紧急熔断: {reason}",
                target_order_id=order.order_id,
                target_symbol=order.symbol,
                details={"order": order.to_dict()},
            )

            try:
                result = await self.order_manager.cancel_order(order.order_id)

                action.executed = result.success
                action.result = result.message

                if result.success:
                    logger.info(f"紧急取消订单成功 - {order.order_id}")
                else:
                    logger.warning(f"紧急取消订单失败 - {order.order_id}: {result.message}")

            except Exception as e:  # pylint: disable=broad-exception-caught
                action.executed = False
                action.result = f"取消失败: {e}"
                logger.error(f"紧急取消订单异常 - {order.order_id}: {e}")

            self.protective_actions.append(action)
            self._trigger_action_callbacks(action)

    def _on_risk_check_failed(self, result: RiskCheckResult) -> None:
        """风控检查失败回调

        Args:
            result: 风控检查结果
        """
        # 将RiskCheckType映射到AlertType
        type_mapping = {
            RiskCheckType.POSITION_LIMIT: AlertType.POSITION_LIMIT,
            RiskCheckType.SECTOR_LIMIT: AlertType.SECTOR_LIMIT,
            RiskCheckType.STOP_LOSS: AlertType.STOP_LOSS,
            RiskCheckType.TAKE_PROFIT: AlertType.TAKE_PROFIT,
            RiskCheckType.LIQUIDITY: AlertType.LIQUIDITY,
            RiskCheckType.DAILY_LOSS: AlertType.DAILY_LOSS,
            RiskCheckType.CAPITAL_SUFFICIENCY: AlertType.CAPITAL_INSUFFICIENT,
        }

        alert_type = type_mapping.get(result.check_type, AlertType.RISK_VIOLATION)

        # 将RiskLevel映射到AlertLevel
        level_mapping = {
            RiskLevel.LOW: AlertLevel.INFO,
            RiskLevel.MEDIUM: AlertLevel.WARNING,
            RiskLevel.HIGH: AlertLevel.ERROR,
            RiskLevel.CRITICAL: AlertLevel.CRITICAL,
        }

        alert_level = level_mapping.get(result.risk_level, AlertLevel.WARNING)

        alert = self._create_alert(
            alert_type=alert_type, alert_level=alert_level, message=result.reason, details=result.details
        )
        self._trigger_alert(alert)

    def _create_alert(  # pylint: disable=too-many-positional-arguments
        self,
        alert_type: AlertType,
        alert_level: AlertLevel,
        message: str,
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> RiskAlert:
        """创建告警

        Args:
            alert_type: 告警类型
            alert_level: 告警级别
            message: 告警消息
            order_id: 订单ID
            symbol: 股票代码
            details: 详细信息

        Returns:
            告警对象
        """
        self._alert_counter += 1

        alert = RiskAlert(
            alert_id=f"ALERT_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._alert_counter:04d}",
            alert_type=alert_type,
            alert_level=alert_level,
            message=message,
            order_id=order_id,
            symbol=symbol,
            details=details or {},
        )

        self.alerts.append(alert)

        return alert

    def _create_protective_action(  # pylint: disable=too-many-positional-arguments
        self,
        action_type: str,
        reason: str,
        target_order_id: Optional[str] = None,
        target_symbol: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> ProtectiveAction:
        """创建保护性操作

        Args:
            action_type: 操作类型
            reason: 原因
            target_order_id: 目标订单ID
            target_symbol: 目标股票代码
            details: 详细信息

        Returns:
            保护性操作对象
        """
        self._action_counter += 1

        action = ProtectiveAction(
            action_id=f"ACTION_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._action_counter:04d}",
            action_type=action_type,
            reason=reason,
            target_order_id=target_order_id,
            target_symbol=target_symbol,
            details=details or {},
        )

        return action

    def _trigger_alert(self, alert: RiskAlert) -> None:
        """触发告警

        Args:
            alert: 告警对象
        """
        # 记录日志
        log_method = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical,
        }.get(alert.alert_level, logger.warning)

        log_method(f"风控告警 [{alert.alert_type.value}]: {alert.message}")

        # 触发回调
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"告警回调异常: {e}")

        # 发布事件
        if self.event_bus:
            asyncio.create_task(self.event_bus.publish({"event_type": "risk_alert", "alert": alert.to_dict()}))

    def _trigger_action_callbacks(self, action: ProtectiveAction) -> None:
        """触发保护性操作回调

        Args:
            action: 保护性操作对象
        """
        for callback in self._action_callbacks:
            try:
                callback(action)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"保护性操作回调异常: {e}")

        # 发布事件
        if self.event_bus:
            asyncio.create_task(self.event_bus.publish({"event_type": "protective_action", "action": action.to_dict()}))

    def get_alerts(
        self,
        alert_type: Optional[AlertType] = None,
        alert_level: Optional[AlertLevel] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100,
    ) -> List[RiskAlert]:
        """获取告警列表

        Args:
            alert_type: 告警类型过滤
            alert_level: 告警级别过滤
            acknowledged: 是否已确认过滤
            limit: 返回数量限制

        Returns:
            告警列表
        """
        filtered = self.alerts

        if alert_type is not None:
            filtered = [a for a in filtered if a.alert_type == alert_type]

        if alert_level is not None:
            filtered = [a for a in filtered if a.alert_level == alert_level]

        if acknowledged is not None:
            filtered = [a for a in filtered if a.acknowledged == acknowledged]

        # 按时间倒序排列
        filtered = sorted(filtered, key=lambda a: a.timestamp, reverse=True)

        return filtered[:limit]

    def get_unacknowledged_alerts(self) -> List[RiskAlert]:
        """获取未确认的告警

        Returns:
            未确认告警列表
        """
        return self.get_alerts(acknowledged=False)

    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警

        Args:
            alert_id: 告警ID

        Returns:
            是否成功
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                logger.info(f"告警已确认: {alert_id}")
                return True

        logger.warning(f"告警不存在: {alert_id}")
        return False

    def acknowledge_all_alerts(self) -> int:
        """确认所有告警

        Returns:
            确认的告警数量
        """
        count = 0
        for alert in self.alerts:
            if not alert.acknowledged:
                alert.acknowledged = True
                count += 1

        logger.info(f"已确认{count}个告警")
        return count

    def get_protective_actions(
        self, action_type: Optional[str] = None, executed: Optional[bool] = None, limit: int = 100
    ) -> List[ProtectiveAction]:
        """获取保护性操作列表

        Args:
            action_type: 操作类型过滤
            executed: 是否已执行过滤
            limit: 返回数量限制

        Returns:
            保护性操作列表
        """
        filtered = self.protective_actions

        if action_type is not None:
            filtered = [a for a in filtered if a.action_type == action_type]

        if executed is not None:
            filtered = [a for a in filtered if a.executed == executed]

        # 按时间倒序排列
        filtered = sorted(filtered, key=lambda a: a.timestamp, reverse=True)

        return filtered[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        # 告警统计
        alert_counts = {}
        for alert_type in AlertType:
            alert_counts[alert_type.value] = len([a for a in self.alerts if a.alert_type == alert_type])

        unacknowledged_count = len([a for a in self.alerts if not a.acknowledged])

        # 保护性操作统计
        action_counts = {}
        for action in self.protective_actions:
            action_counts[action.action_type] = action_counts.get(action.action_type, 0) + 1

        executed_count = len([a for a in self.protective_actions if a.executed])

        return {
            "total_alerts": len(self.alerts),
            "unacknowledged_alerts": unacknowledged_count,
            "alert_counts": alert_counts,
            "total_protective_actions": len(self.protective_actions),
            "executed_actions": executed_count,
            "action_counts": action_counts,
            "risk_level": self.risk_control.risk_level.name.lower(),
            "emergency_shutdown_active": self.risk_control.emergency_shutdown_active,
        }

    def clear_old_alerts(self, keep_hours: int = 24) -> int:
        """清理旧告警

        Args:
            keep_hours: 保留小时数

        Returns:
            清理的告警数量
        """
        cutoff_time = datetime.now().timestamp() - (keep_hours * 3600)

        old_count = len(self.alerts)
        self.alerts = [a for a in self.alerts if a.timestamp.timestamp() >= cutoff_time]

        cleared = old_count - len(self.alerts)
        logger.info(f"清理旧告警 - 共清理{cleared}个告警")

        return cleared

    def clear_old_actions(self, keep_hours: int = 24) -> int:
        """清理旧保护性操作记录

        Args:
            keep_hours: 保留小时数

        Returns:
            清理的记录数量
        """
        cutoff_time = datetime.now().timestamp() - (keep_hours * 3600)

        old_count = len(self.protective_actions)
        self.protective_actions = [a for a in self.protective_actions if a.timestamp.timestamp() >= cutoff_time]

        cleared = old_count - len(self.protective_actions)
        logger.info(f"清理旧保护性操作记录 - 共清理{cleared}条记录")

        return cleared

    def reset(self) -> None:
        """重置（仅用于测试）"""
        self.alerts.clear()
        self.protective_actions.clear()
        self._alert_counter = 0
        self._action_counter = 0
        logger.warning("OrderRiskIntegration已重置")
