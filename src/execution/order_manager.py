"""OrderManager (订单管理器) - 订单生命周期管理

白皮书依据: 第六章 6.2 订单管理系统

核心功能:
- 订单创建、路由、执行、状态跟踪
- 订单取消和修改
- 风控集成
- 审计日志
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class OrderStatus(Enum):
    """订单状态"""

    PENDING = "pending"  # 待提交
    SUBMITTED = "submitted"  # 已提交
    ACCEPTED = "accepted"  # 已接受
    PARTIALLY_FILLED = "partially_filled"  # 部分成交
    FILLED = "filled"  # 完全成交
    CANCELLED = "cancelled"  # 已取消
    REJECTED = "rejected"  # 已拒绝
    FAILED = "failed"  # 失败


class OrderType(Enum):
    """订单类型"""

    MARKET = "market"  # 市价单
    LIMIT = "limit"  # 限价单
    STOP = "stop"  # 止损单
    STOP_LIMIT = "stop_limit"  # 止损限价单


class OrderSide(Enum):
    """订单方向"""

    BUY = "buy"  # 买入
    SELL = "sell"  # 卖出


@dataclass
class Order:  # pylint: disable=too-many-instance-attributes
    """订单数据模型

    白皮书依据: 第六章 6.2 订单数据结构
    """

    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    strategy_id: Optional[str] = None
    submit_time: Optional[datetime] = None
    fill_time: Optional[datetime] = None
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    commission: float = 0.0
    slippage: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "status": self.status.value,
            "strategy_id": self.strategy_id,
            "submit_time": self.submit_time.isoformat() if self.submit_time else None,
            "fill_time": self.fill_time.isoformat() if self.fill_time else None,
            "filled_quantity": self.filled_quantity,
            "average_price": self.average_price,
            "commission": self.commission,
            "slippage": self.slippage,
            "metadata": self.metadata,
        }


@dataclass
class OrderResult:
    """订单执行结果"""

    success: bool
    order_id: str
    message: str
    status: OrderStatus
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    commission: float = 0.0
    slippage: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class OrderManagerError(Exception):
    """订单管理器异常"""


class OrderValidationError(OrderManagerError):
    """订单验证异常"""


class RiskViolationError(OrderManagerError):
    """风控违规异常"""


class OrderManager:
    """订单管理器

    白皮书依据: 第六章 6.2 订单管理系统

    管理交易订单的完整生命周期，包括订单创建、路由、
    执行、状态跟踪和取消修改。

    Attributes:
        orders: 订单字典
        risk_manager: 风险管理器
        execution_engine: 执行引擎
        auditor: 审计器
        event_bus: 事件总线
    """

    def __init__(
        self,
        risk_manager: Optional[Any] = None,
        execution_engine: Optional[Any] = None,
        auditor: Optional[Any] = None,
        event_bus: Optional[Any] = None,
    ):
        """初始化订单管理器

        Args:
            risk_manager: 风险管理器
            execution_engine: 执行引擎
            auditor: 审计器
            event_bus: 事件总线
        """
        self.orders: Dict[str, Order] = {}
        self.risk_manager = risk_manager
        self.execution_engine = execution_engine
        self.auditor = auditor
        self.event_bus = event_bus

        # 订单状态回调
        self._status_callbacks: List[Callable[[Order], None]] = []

        logger.info("OrderManager初始化完成")

    def register_status_callback(self, callback: Callable[[Order], None]) -> None:
        """注册订单状态变化回调

        Args:
            callback: 回调函数
        """
        self._status_callbacks.append(callback)

    async def submit_order(  # pylint: disable=too-many-positional-arguments
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
        """提交订单

        白皮书依据: 第六章 6.2 订单管理系统

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

        Raises:
            OrderValidationError: 订单验证失败
            RiskViolationError: 违反风控规则
        """
        # 创建订单
        order = Order(
            order_id=self._generate_order_id(),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            strategy_id=strategy_id,
            metadata=metadata or {},
        )

        logger.info(
            f"提交订单 - {order.order_id}: {order.side.value} {order.symbol} "
            f"{order.quantity}@{order.price or 'MARKET'}"
        )

        try:
            # 订单验证
            self._validate_order(order)

            # 风控检查
            if self.risk_manager:
                risk_check = await self.risk_manager.check_order(order)
                if not risk_check.get("passed", False):
                    raise RiskViolationError(risk_check.get("reason", "风控检查未通过"))

            # 订单路由
            routed_order = self._route_order(order)

            # 提交执行
            result = await self._execute_order(routed_order)

            # 更新订单状态
            order.status = result.status
            order.submit_time = datetime.now()
            self.orders[order.order_id] = order

            # 触发状态回调
            self._trigger_status_callbacks(order)

            # 审计日志
            if self.auditor:
                await self.auditor.log_order(order, result)

            # 发布事件
            if self.event_bus:
                await self.event_bus.publish(
                    {"event_type": "order_submitted", "order": order.to_dict(), "result": result.__dict__}
                )

            logger.info(f"订单提交成功 - {order.order_id}: {result.message}")

            return result

        except OrderValidationError as e:
            logger.error(f"订单验证失败 - {order.order_id}: {e}")
            order.status = OrderStatus.REJECTED
            self.orders[order.order_id] = order

            return OrderResult(
                success=False, order_id=order.order_id, message=f"订单验证失败: {e}", status=OrderStatus.REJECTED
            )

        except RiskViolationError as e:
            logger.error(f"风控违规 - {order.order_id}: {e}")
            order.status = OrderStatus.REJECTED
            self.orders[order.order_id] = order

            # 发送风控告警
            if self.event_bus:
                await self.event_bus.publish(
                    {"event_type": "risk_violation", "order": order.to_dict(), "reason": str(e)}
                )

            return OrderResult(
                success=False, order_id=order.order_id, message=f"风控违规: {e}", status=OrderStatus.REJECTED
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"订单提交异常 - {order.order_id}: {e}")
            order.status = OrderStatus.FAILED
            self.orders[order.order_id] = order

            return OrderResult(
                success=False, order_id=order.order_id, message=f"订单提交异常: {e}", status=OrderStatus.FAILED
            )

    def _validate_order(self, order: Order) -> None:
        """验证订单

        Args:
            order: 订单对象

        Raises:
            OrderValidationError: 验证失败
        """
        # 检查股票代码
        if not order.symbol:
            raise OrderValidationError("股票代码不能为空")

        # 检查数量
        if order.quantity <= 0:
            raise OrderValidationError(f"订单数量必须大于0: {order.quantity}")

        # 检查数量是否为100的倍数（A股规则）
        if order.quantity % 100 != 0:
            raise OrderValidationError(f"订单数量必须为100的倍数: {order.quantity}")

        # 检查限价单价格
        if order.order_type == OrderType.LIMIT and order.price is None:
            raise OrderValidationError("限价单必须指定价格")

        # 检查止损单价格
        if order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
            if order.stop_price is None:
                raise OrderValidationError("止损单必须指定止损价")

        # 检查价格合理性
        if order.price is not None and order.price <= 0:
            raise OrderValidationError(f"订单价格必须大于0: {order.price}")

        if order.stop_price is not None and order.stop_price <= 0:
            raise OrderValidationError(f"止损价必须大于0: {order.stop_price}")

    def _route_order(self, order: Order) -> Order:
        """订单路由

        根据订单类型、市场、流动性等因素选择最优执行路径

        Args:
            order: 订单对象

        Returns:
            路由后的订单
        """
        # 简化实现：直接返回原订单
        # 实际应该根据市场、流动性、成本等因素选择最优路径
        logger.debug(f"订单路由 - {order.order_id}: 默认路径")
        return order

    async def _execute_order(self, order: Order) -> OrderResult:
        """执行订单

        Args:
            order: 订单对象

        Returns:
            执行结果
        """
        if self.execution_engine:  # pylint: disable=no-else-return
            # 调用执行引擎
            result = await self.execution_engine.execute_order(order)

            return OrderResult(
                success=result.get("success", False),
                order_id=order.order_id,
                message=result.get("message", ""),
                status=OrderStatus(result.get("status", "submitted")),
                filled_quantity=result.get("filled_quantity", 0),
                average_price=result.get("average_price"),
                commission=result.get("commission", 0),
                slippage=result.get("slippage", 0),
                metadata=result.get("metadata", {}),
            )
        else:
            # 模拟执行
            logger.info(f"[模拟] 执行订单 - {order.order_id}")

            return OrderResult(
                success=True,
                order_id=order.order_id,
                message="模拟执行成功",
                status=OrderStatus.SUBMITTED,
                filled_quantity=0,
                average_price=order.price,
                commission=0,
                slippage=0,
            )

    async def cancel_order(self, order_id: str) -> OrderResult:
        """取消订单

        白皮书依据: 第六章 6.2 订单取消

        Args:
            order_id: 订单ID

        Returns:
            取消结果
        """
        order = self.orders.get(order_id)

        if not order:
            return OrderResult(success=False, order_id=order_id, message="订单不存在", status=OrderStatus.FAILED)

        # 检查订单状态
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            return OrderResult(
                success=False,
                order_id=order_id,
                message=f"订单状态为{order.status.value}，无法取消",
                status=order.status,
            )

        logger.info(f"取消订单 - {order_id}")

        try:
            if self.execution_engine:  # pylint: disable=no-else-return
                # 调用执行引擎取消订单
                result = await self.execution_engine.cancel_order(order_id)

                if result.get("success", False):
                    order.status = OrderStatus.CANCELLED
                    self._trigger_status_callbacks(order)

                    # 审计日志
                    if self.auditor:
                        await self.auditor.log_order_cancellation(order)

                    # 发布事件
                    if self.event_bus:
                        await self.event_bus.publish({"event_type": "order_cancelled", "order": order.to_dict()})

                return OrderResult(
                    success=result.get("success", False),
                    order_id=order_id,
                    message=result.get("message", ""),
                    status=OrderStatus.CANCELLED if result.get("success") else order.status,
                )
            else:
                # 模拟取消
                order.status = OrderStatus.CANCELLED
                self._trigger_status_callbacks(order)

                logger.info(f"[模拟] 订单已取消 - {order_id}")

                return OrderResult(
                    success=True, order_id=order_id, message="模拟取消成功", status=OrderStatus.CANCELLED
                )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"取消订单异常 - {order_id}: {e}")

            return OrderResult(success=False, order_id=order_id, message=f"取消订单异常: {e}", status=order.status)

    async def modify_order(
        self, order_id: str, new_price: Optional[float] = None, new_quantity: Optional[float] = None
    ) -> OrderResult:
        """修改订单

        白皮书依据: 第六章 6.2 订单修改

        Args:
            order_id: 订单ID
            new_price: 新价格
            new_quantity: 新数量

        Returns:
            修改结果
        """
        order = self.orders.get(order_id)

        if not order:
            return OrderResult(success=False, order_id=order_id, message="订单不存在", status=OrderStatus.FAILED)

        # 检查订单状态
        if order.status not in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.ACCEPTED]:
            return OrderResult(
                success=False,
                order_id=order_id,
                message=f"订单状态为{order.status.value}，无法修改",
                status=order.status,
            )

        logger.info(f"修改订单 - {order_id}: price={new_price}, quantity={new_quantity}")

        try:
            # 保存旧值
            old_price = order.price
            old_quantity = order.quantity

            # 更新订单
            if new_price is not None:
                order.price = new_price
            if new_quantity is not None:
                order.quantity = new_quantity

            # 验证修改后的订单
            self._validate_order(order)

            # 风控检查
            if self.risk_manager:
                risk_check = await self.risk_manager.check_order(order)
                if not risk_check.get("passed", False):
                    # 恢复旧值
                    order.price = old_price
                    order.quantity = old_quantity
                    raise RiskViolationError(risk_check.get("reason", "风控检查未通过"))

            if self.execution_engine:  # pylint: disable=no-else-return
                # 调用执行引擎修改订单
                result = await self.execution_engine.modify_order(
                    order_id=order_id, new_price=new_price, new_quantity=new_quantity
                )

                if result.get("success", False):
                    self._trigger_status_callbacks(order)

                    # 审计日志
                    if self.auditor:
                        await self.auditor.log_order_modification(order, old_price=old_price, old_quantity=old_quantity)

                    # 发布事件
                    if self.event_bus:
                        await self.event_bus.publish(
                            {
                                "event_type": "order_modified",
                                "order": order.to_dict(),
                                "old_price": old_price,
                                "old_quantity": old_quantity,
                            }
                        )
                else:
                    # 恢复旧值
                    order.price = old_price
                    order.quantity = old_quantity

                return OrderResult(
                    success=result.get("success", False),
                    order_id=order_id,
                    message=result.get("message", ""),
                    status=order.status,
                )
            else:
                # 模拟修改
                self._trigger_status_callbacks(order)

                logger.info(f"[模拟] 订单已修改 - {order_id}")

                return OrderResult(success=True, order_id=order_id, message="模拟修改成功", status=order.status)

        except OrderValidationError as e:
            # 恢复旧值
            order.price = old_price
            order.quantity = old_quantity

            logger.error(f"订单修改验证失败 - {order_id}: {e}")

            return OrderResult(success=False, order_id=order_id, message=f"订单修改验证失败: {e}", status=order.status)

        except RiskViolationError as e:
            logger.error(f"订单修改风控违规 - {order_id}: {e}")

            return OrderResult(success=False, order_id=order_id, message=f"风控违规: {e}", status=order.status)

        except Exception as e:  # pylint: disable=broad-exception-caught
            # 恢复旧值
            order.price = old_price
            order.quantity = old_quantity

            logger.error(f"修改订单异常 - {order_id}: {e}")

            return OrderResult(success=False, order_id=order_id, message=f"修改订单异常: {e}", status=order.status)

    async def update_order_status(  # pylint: disable=too-many-positional-arguments
        self,
        order_id: str,
        status: OrderStatus,
        filled_quantity: Optional[float] = None,
        average_price: Optional[float] = None,
        commission: Optional[float] = None,
        slippage: Optional[float] = None,
    ) -> None:
        """更新订单状态

        Args:
            order_id: 订单ID
            status: 新状态
            filled_quantity: 成交数量
            average_price: 成交均价
            commission: 佣金
            slippage: 滑点
        """
        order = self.orders.get(order_id)

        if not order:
            logger.warning(f"订单不存在 - {order_id}")
            return

        old_status = order.status
        order.status = status

        if filled_quantity is not None:
            order.filled_quantity = filled_quantity

        if average_price is not None:
            order.average_price = average_price

        if commission is not None:
            order.commission = commission

        if slippage is not None:
            order.slippage = slippage

        if status == OrderStatus.FILLED:
            order.fill_time = datetime.now()

        logger.info(f"订单状态更新 - {order_id}: {old_status.value} -> {status.value}")

        # 触发状态回调
        self._trigger_status_callbacks(order)

        # 发布事件
        if self.event_bus:
            await self.event_bus.publish(
                {"event_type": "order_status_updated", "order": order.to_dict(), "old_status": old_status.value}
            )

    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单

        Args:
            order_id: 订单ID

        Returns:
            订单对象或None
        """
        return self.orders.get(order_id)

    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """获取指定股票的所有订单

        Args:
            symbol: 股票代码

        Returns:
            订单列表
        """
        return [order for order in self.orders.values() if order.symbol == symbol]

    def get_orders_by_strategy(self, strategy_id: str) -> List[Order]:
        """获取指定策略的所有订单

        Args:
            strategy_id: 策略ID

        Returns:
            订单列表
        """
        return [order for order in self.orders.values() if order.strategy_id == strategy_id]

    def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """获取指定状态的所有订单

        Args:
            status: 订单状态

        Returns:
            订单列表
        """
        return [order for order in self.orders.values() if order.status == status]

    def get_active_orders(self) -> List[Order]:
        """获取所有活跃订单（未完成、未取消、未拒绝）

        Returns:
            活跃订单列表
        """
        active_statuses = [
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.ACCEPTED,
            OrderStatus.PARTIALLY_FILLED,
        ]

        return [order for order in self.orders.values() if order.status in active_statuses]

    def get_all_orders(self) -> List[Order]:
        """获取所有订单

        Returns:
            所有订单列表
        """
        return list(self.orders.values())

    def get_order_statistics(self) -> Dict[str, Any]:
        """获取订单统计信息

        Returns:
            统计信息字典
        """
        total_orders = len(self.orders)

        status_counts = {}
        for status in OrderStatus:
            status_counts[status.value] = len(self.get_orders_by_status(status))

        filled_orders = self.get_orders_by_status(OrderStatus.FILLED)
        total_commission = sum(order.commission for order in filled_orders)
        total_slippage = sum(order.slippage for order in filled_orders)

        return {
            "total_orders": total_orders,
            "active_orders": len(self.get_active_orders()),
            "status_counts": status_counts,
            "filled_orders": len(filled_orders),
            "total_commission": total_commission,
            "total_slippage": total_slippage,
        }

    def _generate_order_id(self) -> str:
        """生成订单ID

        Returns:
            订单ID
        """
        return f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def _trigger_status_callbacks(self, order: Order) -> None:
        """触发订单状态回调

        Args:
            order: 订单对象
        """
        for callback in self._status_callbacks:
            try:
                callback(order)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"订单状态回调异常: {e}")

    def clear_completed_orders(self, keep_days: int = 7) -> int:
        """清理已完成的订单（保留指定天数）

        Args:
            keep_days: 保留天数

        Returns:
            清理的订单数量
        """
        cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 3600)

        orders_to_remove = []
        for order_id, order in self.orders.items():
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                if order.submit_time and order.submit_time.timestamp() < cutoff_time:
                    orders_to_remove.append(order_id)

        for order_id in orders_to_remove:
            del self.orders[order_id]

        logger.info(f"清理已完成订单 - 共清理{len(orders_to_remove)}个订单")

        return len(orders_to_remove)

    def reset(self) -> None:
        """重置订单管理器（仅用于测试）"""
        self.orders.clear()
        logger.warning("OrderManager已重置")
