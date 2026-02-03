# pylint: disable=too-many-lines
"""RiskControlSystem (风控系统) - 统一风险控制系统

白皮书依据: 第六章 6.3 风险控制系统

核心功能:
- 事前风控（订单合规检查、资金充足性）
- 事中风控（实时持仓监控、止损触发）
- 事后风控（交易复盘、风险归因）
- 风险限额（单票限额、行业限额、总仓位限额）
- 紧急熔断（极端行情、系统异常）
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class RiskLevel(IntEnum):
    """风险等级

    使用IntEnum支持比较操作，数值越大风险越高
    """

    LOW = 1  # 低风险
    MEDIUM = 2  # 中风险
    HIGH = 3  # 高风险
    CRITICAL = 4  # 危急

    @property
    def value_str(self) -> str:
        """获取字符串值（兼容旧代码）"""
        return self.name.lower()


class RiskCheckType(Enum):
    """风控检查类型"""

    POSITION_LIMIT = "position_limit"  # 仓位限制
    SECTOR_LIMIT = "sector_limit"  # 行业限制
    STOP_LOSS = "stop_loss"  # 止损
    TAKE_PROFIT = "take_profit"  # 止盈
    LIQUIDITY = "liquidity"  # 流动性
    MARGIN = "margin"  # 保证金
    DAILY_LOSS = "daily_loss"  # 日亏损
    CAPITAL_SUFFICIENCY = "capital_sufficiency"  # 资金充足性


@dataclass
class RiskCheckResult:
    """风控检查结果"""

    passed: bool
    check_type: RiskCheckType
    reason: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "passed": self.passed,
            "check_type": self.check_type.value,
            "reason": self.reason,
            "risk_level": self.risk_level.name.lower(),
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class PositionRisk:
    """持仓风险"""

    symbol: str
    quantity: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    position_ratio: float  # 占总资产比例
    sector: str
    risk_level: RiskLevel
    stop_loss_triggered: bool = False
    take_profit_triggered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "market_value": self.market_value,
            "cost_basis": self.cost_basis,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "position_ratio": self.position_ratio,
            "sector": self.sector,
            "risk_level": self.risk_level.name.lower(),
            "stop_loss_triggered": self.stop_loss_triggered,
            "take_profit_triggered": self.take_profit_triggered,
        }


@dataclass
class RiskLimit:
    """风险限额"""

    limit_type: str
    current_value: float
    limit_value: float
    utilization: float  # 使用率
    breached: bool

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "limit_type": self.limit_type,
            "current_value": self.current_value,
            "limit_value": self.limit_value,
            "utilization": self.utilization,
            "breached": self.breached,
        }


@dataclass
class Position:
    """持仓数据"""

    symbol: str
    quantity: float
    cost_basis: float
    current_price: float
    sector: str = ""
    strategy_id: Optional[str] = None

    @property
    def market_value(self) -> float:
        """市值"""
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        return self.market_value - (self.quantity * self.cost_basis)

    @property
    def unrealized_pnl_pct(self) -> float:
        """未实现盈亏百分比"""
        if self.cost_basis <= 0:
            return 0.0
        return (self.current_price - self.cost_basis) / self.cost_basis


class RiskControlError(Exception):
    """风控系统异常"""


class RiskViolationError(RiskControlError):
    """风控违规异常"""


class EmergencyShutdownError(RiskControlError):
    """紧急熔断异常"""


class RiskControlSystem:
    """风控系统

    白皮书依据: 第六章 6.3 风险控制系统

    提供完整的风险控制功能，包括事前风控、事中风控、事后风控、
    风险限额管理和紧急熔断机制。

    Attributes:
        total_capital: 总资本
        positions: 持仓字典
        risk_limits: 风险限额配置
        risk_level: 当前风险等级
        event_bus: 事件总线
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        total_capital: float = 1000000.0,
        max_position_ratio: float = 0.20,
        max_single_stock_ratio: float = 0.10,
        max_sector_ratio: float = 0.30,
        stop_loss_ratio: float = 0.08,
        take_profit_ratio: float = 0.20,
        daily_loss_limit: float = 0.05,
        margin_limit: float = 0.30,
        min_liquidity_ratio: float = 0.01,
        event_bus: Optional[Any] = None,
    ):
        """初始化风控系统

        白皮书依据: 第六章 6.3 风险控制系统

        Args:
            total_capital: 总资本
            max_position_ratio: 最大总仓位比例，默认20%
            max_single_stock_ratio: 单股最大仓位比例，默认10%
            max_sector_ratio: 行业最大仓位比例，默认30%
            stop_loss_ratio: 止损比例，默认8%
            take_profit_ratio: 止盈比例，默认20%
            daily_loss_limit: 日亏损限制，默认5%
            margin_limit: 保证金限制，默认30%
            min_liquidity_ratio: 最小流动性比例，默认1%
            event_bus: 事件总线

        Raises:
            ValueError: 当参数不在有效范围时
        """
        # 参数验证
        if total_capital <= 0:
            raise ValueError(f"总资本必须大于0: {total_capital}")

        if not 0 < max_position_ratio <= 1:
            raise ValueError(f"最大仓位比例必须在(0, 1]范围内: {max_position_ratio}")

        if not 0 < max_single_stock_ratio <= 1:
            raise ValueError(f"单股最大仓位比例必须在(0, 1]范围内: {max_single_stock_ratio}")

        if not 0 < max_sector_ratio <= 1:
            raise ValueError(f"行业最大仓位比例必须在(0, 1]范围内: {max_sector_ratio}")

        if not 0 < stop_loss_ratio <= 1:
            raise ValueError(f"止损比例必须在(0, 1]范围内: {stop_loss_ratio}")

        if not 0 < take_profit_ratio <= 1:
            raise ValueError(f"止盈比例必须在(0, 1]范围内: {take_profit_ratio}")

        # 初始化属性
        self.total_capital = total_capital
        self.positions: Dict[str, Position] = {}
        self.event_bus = event_bus

        # 风险限额配置
        self.risk_limits = {
            "max_position_ratio": max_position_ratio,
            "max_single_stock_ratio": max_single_stock_ratio,
            "max_sector_ratio": max_sector_ratio,
            "stop_loss_ratio": stop_loss_ratio,
            "take_profit_ratio": take_profit_ratio,
            "daily_loss_limit": daily_loss_limit,
            "margin_limit": margin_limit,
            "min_liquidity_ratio": min_liquidity_ratio,
        }

        # 当前风险等级
        self.risk_level = RiskLevel.LOW

        # 日亏损跟踪
        self.daily_pnl = 0.0
        self.daily_pnl_reset_time = datetime.now().replace(hour=0, minute=0, second=0)

        # 紧急熔断状态
        self.emergency_shutdown_active = False
        self.shutdown_reason = ""

        # 风控回调
        self._risk_callbacks: List[Callable[[RiskCheckResult], None]] = []

        logger.info(
            f"RiskControlSystem初始化完成 - "
            f"总资本: {total_capital:,.0f}, "
            f"最大仓位: {max_position_ratio:.1%}, "
            f"单股限制: {max_single_stock_ratio:.1%}, "
            f"止损: {stop_loss_ratio:.1%}"
        )

    def register_risk_callback(self, callback: Callable[[RiskCheckResult], None]) -> None:
        """注册风控回调

        Args:
            callback: 回调函数
        """
        self._risk_callbacks.append(callback)

    async def check_order(self, order: Any) -> Dict[str, Any]:
        """检查订单风控

        白皮书依据: 第六章 6.3 事前风控

        Args:
            order: 订单对象

        Returns:
            风控检查结果字典
        """
        # 检查紧急熔断状态
        if self.emergency_shutdown_active:
            return {
                "passed": False,
                "reason": f"紧急熔断已激活: {self.shutdown_reason}",
                "risk_level": RiskLevel.CRITICAL.name.lower(),
            }

        results = []

        # 1. 资金充足性检查
        capital_check = await self._check_capital_sufficiency(order)
        results.append(capital_check)

        # 2. 仓位限制检查
        position_check = await self._check_position_limit(order)
        results.append(position_check)

        # 3. 行业限制检查
        sector_check = await self._check_sector_limit(order)
        results.append(sector_check)

        # 4. 流动性检查
        liquidity_check = await self._check_liquidity(order)
        results.append(liquidity_check)

        # 5. 日亏损限制检查
        daily_loss_check = await self._check_daily_loss_limit()
        results.append(daily_loss_check)

        # 汇总结果
        all_passed = all(r.passed for r in results)
        failed_checks = [r for r in results if not r.passed]

        if not all_passed:
            reasons = [r.reason for r in failed_checks]
            highest_risk = max(r.risk_level for r in failed_checks)

            result = {
                "passed": False,
                "reason": "; ".join(reasons),
                "risk_level": highest_risk.name.lower(),
                "failed_checks": [r.to_dict() for r in failed_checks],
            }

            # 触发风控回调
            for check in failed_checks:
                self._trigger_risk_callbacks(check)

            logger.warning(f"订单风控检查未通过: {result['reason']}")

            return result

        logger.debug(f"订单风控检查通过")  # pylint: disable=w1309

        return {"passed": True, "reason": "", "risk_level": RiskLevel.LOW.name.lower()}

    async def _check_capital_sufficiency(self, order: Any) -> RiskCheckResult:
        """检查资金充足性

        Args:
            order: 订单对象

        Returns:
            检查结果
        """
        # 计算订单所需资金
        order_value = order.quantity * (order.price or 0)

        # 计算当前可用资金
        total_position_value = sum(pos.market_value for pos in self.positions.values())
        available_capital = self.total_capital - total_position_value

        if order_value > available_capital:
            return RiskCheckResult(
                passed=False,
                check_type=RiskCheckType.CAPITAL_SUFFICIENCY,
                reason=f"资金不足: 需要{order_value:,.0f}, 可用{available_capital:,.0f}",
                risk_level=RiskLevel.HIGH,
                details={"required": order_value, "available": available_capital},
            )

        return RiskCheckResult(
            passed=True,
            check_type=RiskCheckType.CAPITAL_SUFFICIENCY,
            details={"required": order_value, "available": available_capital},
        )

    async def _check_position_limit(self, order: Any) -> RiskCheckResult:
        """检查仓位限制

        白皮书依据: 第六章 6.3 仓位限制

        Args:
            order: 订单对象

        Returns:
            检查结果
        """
        # 计算当前总仓位
        total_position_value = sum(pos.market_value for pos in self.positions.values())
        current_position_ratio = total_position_value / self.total_capital

        # 计算订单后的仓位
        order_value = order.quantity * (order.price or 0)

        # 判断是买入还是卖出
        is_buy = hasattr(order, "side") and order.side.value == "buy"

        if is_buy:
            new_position_ratio = (total_position_value + order_value) / self.total_capital

            # 检查总仓位限制
            if new_position_ratio > self.risk_limits["max_position_ratio"]:
                return RiskCheckResult(
                    passed=False,
                    check_type=RiskCheckType.POSITION_LIMIT,
                    reason=f'总仓位超限: {new_position_ratio:.1%} > {self.risk_limits["max_position_ratio"]:.1%}',
                    risk_level=RiskLevel.HIGH,
                    details={
                        "current_ratio": current_position_ratio,
                        "new_ratio": new_position_ratio,
                        "limit": self.risk_limits["max_position_ratio"],
                    },
                )

            # 检查单股仓位限制
            symbol = order.symbol
            current_stock_value = self.positions.get(symbol, Position(symbol, 0, 0, 0)).market_value
            new_stock_value = current_stock_value + order_value
            new_stock_ratio = new_stock_value / self.total_capital

            if new_stock_ratio > self.risk_limits["max_single_stock_ratio"]:
                return RiskCheckResult(
                    passed=False,
                    check_type=RiskCheckType.POSITION_LIMIT,
                    reason=f'单股仓位超限: {symbol} {new_stock_ratio:.1%} > {self.risk_limits["max_single_stock_ratio"]:.1%}',
                    risk_level=RiskLevel.HIGH,
                    details={
                        "symbol": symbol,
                        "current_ratio": current_stock_value / self.total_capital,
                        "new_ratio": new_stock_ratio,
                        "limit": self.risk_limits["max_single_stock_ratio"],
                    },
                )

        return RiskCheckResult(
            passed=True,
            check_type=RiskCheckType.POSITION_LIMIT,
            details={"current_position_ratio": current_position_ratio},
        )

    async def _check_sector_limit(self, order: Any) -> RiskCheckResult:
        """检查行业限制

        白皮书依据: 第六章 6.3 行业限制

        Args:
            order: 订单对象

        Returns:
            检查结果
        """
        # 获取订单股票的行业
        symbol = order.symbol
        sector = getattr(order, "sector", "") or self._get_sector(symbol)

        if not sector:
            # 无法确定行业，跳过检查
            return RiskCheckResult(passed=True, check_type=RiskCheckType.SECTOR_LIMIT, details={"sector": "unknown"})

        # 计算当前行业仓位
        sector_value = sum(pos.market_value for pos in self.positions.values() if pos.sector == sector)
        current_sector_ratio = sector_value / self.total_capital

        # 判断是买入还是卖出
        is_buy = hasattr(order, "side") and order.side.value == "buy"

        if is_buy:
            order_value = order.quantity * (order.price or 0)
            new_sector_ratio = (sector_value + order_value) / self.total_capital

            if new_sector_ratio > self.risk_limits["max_sector_ratio"]:
                return RiskCheckResult(
                    passed=False,
                    check_type=RiskCheckType.SECTOR_LIMIT,
                    reason=f'行业仓位超限: {sector} {new_sector_ratio:.1%} > {self.risk_limits["max_sector_ratio"]:.1%}',
                    risk_level=RiskLevel.MEDIUM,
                    details={
                        "sector": sector,
                        "current_ratio": current_sector_ratio,
                        "new_ratio": new_sector_ratio,
                        "limit": self.risk_limits["max_sector_ratio"],
                    },
                )

        return RiskCheckResult(
            passed=True,
            check_type=RiskCheckType.SECTOR_LIMIT,
            details={"sector": sector, "current_ratio": current_sector_ratio},
        )

    async def _check_liquidity(self, order: Any) -> RiskCheckResult:
        """检查流动性约束

        白皮书依据: 第六章 6.3 流动性约束

        Args:
            order: 订单对象

        Returns:
            检查结果
        """
        # 获取股票的日均成交量
        symbol = order.symbol
        avg_volume = getattr(order, "avg_volume", 0) or self._get_avg_volume(symbol)

        if avg_volume <= 0:
            # 无法获取成交量，跳过检查
            return RiskCheckResult(passed=True, check_type=RiskCheckType.LIQUIDITY, details={"avg_volume": "unknown"})

        # 计算订单占日均成交量的比例
        order_volume_ratio = order.quantity / avg_volume

        if order_volume_ratio > self.risk_limits["min_liquidity_ratio"]:
            return RiskCheckResult(
                passed=False,
                check_type=RiskCheckType.LIQUIDITY,
                reason=f'流动性不足: 订单量占日均成交量{order_volume_ratio:.1%} > {self.risk_limits["min_liquidity_ratio"]:.1%}',
                risk_level=RiskLevel.MEDIUM,
                details={
                    "symbol": symbol,
                    "order_quantity": order.quantity,
                    "avg_volume": avg_volume,
                    "ratio": order_volume_ratio,
                    "limit": self.risk_limits["min_liquidity_ratio"],
                },
            )

        return RiskCheckResult(
            passed=True,
            check_type=RiskCheckType.LIQUIDITY,
            details={
                "symbol": symbol,
                "order_quantity": order.quantity,
                "avg_volume": avg_volume,
                "ratio": order_volume_ratio,
            },
        )

    async def _check_daily_loss_limit(self) -> RiskCheckResult:
        """检查日亏损限制

        Returns:
            检查结果
        """
        # 重置日亏损（如果是新的一天）
        self._reset_daily_pnl_if_needed()

        daily_loss_ratio = abs(min(0, self.daily_pnl)) / self.total_capital

        if daily_loss_ratio >= self.risk_limits["daily_loss_limit"]:
            return RiskCheckResult(
                passed=False,
                check_type=RiskCheckType.DAILY_LOSS,
                reason=f'日亏损超限: {daily_loss_ratio:.1%} >= {self.risk_limits["daily_loss_limit"]:.1%}',
                risk_level=RiskLevel.CRITICAL,
                details={
                    "daily_pnl": self.daily_pnl,
                    "daily_loss_ratio": daily_loss_ratio,
                    "limit": self.risk_limits["daily_loss_limit"],
                },
            )

        return RiskCheckResult(
            passed=True,
            check_type=RiskCheckType.DAILY_LOSS,
            details={"daily_pnl": self.daily_pnl, "daily_loss_ratio": daily_loss_ratio},
        )

    async def monitor_position(self, symbol: str) -> PositionRisk:
        """实时持仓监控

        白皮书依据: 第六章 6.3 事中风控

        Args:
            symbol: 股票代码

        Returns:
            持仓风险信息

        Raises:
            ValueError: 当持仓不存在时
        """
        position = self.positions.get(symbol)

        if not position:
            raise ValueError(f"持仓不存在: {symbol}")

        # 计算持仓风险
        position_ratio = position.market_value / self.total_capital

        # 判断风险等级
        risk_level = self._calculate_position_risk_level(position)

        # 检查止损止盈
        stop_loss_triggered = position.unrealized_pnl_pct <= -self.risk_limits["stop_loss_ratio"]
        take_profit_triggered = position.unrealized_pnl_pct >= self.risk_limits["take_profit_ratio"]

        position_risk = PositionRisk(
            symbol=symbol,
            quantity=position.quantity,
            market_value=position.market_value,
            cost_basis=position.cost_basis,
            unrealized_pnl=position.unrealized_pnl,
            unrealized_pnl_pct=position.unrealized_pnl_pct,
            position_ratio=position_ratio,
            sector=position.sector,
            risk_level=risk_level,
            stop_loss_triggered=stop_loss_triggered,
            take_profit_triggered=take_profit_triggered,
        )

        # 如果触发止损或止盈，发送告警
        if stop_loss_triggered:
            await self._trigger_stop_loss_alert(position_risk)

        if take_profit_triggered:
            await self._trigger_take_profit_alert(position_risk)

        return position_risk

    async def check_stop_loss(self, position: Position) -> bool:
        """止损检查

        白皮书依据: 第六章 6.3 止损机制

        Args:
            position: 持仓对象

        Returns:
            是否触发止损
        """
        if position.unrealized_pnl_pct <= -self.risk_limits["stop_loss_ratio"]:
            logger.warning(
                f"止损触发 - {position.symbol}: "
                f"亏损{position.unrealized_pnl_pct:.1%} <= -{self.risk_limits['stop_loss_ratio']:.1%}"
            )

            # 发送止损事件
            if self.event_bus:
                await self.event_bus.publish(
                    {
                        "event_type": "stop_loss_triggered",
                        "symbol": position.symbol,
                        "unrealized_pnl_pct": position.unrealized_pnl_pct,
                        "threshold": -self.risk_limits["stop_loss_ratio"],
                    }
                )

            return True

        return False

    async def check_take_profit(self, position: Position) -> bool:
        """止盈检查

        白皮书依据: 第六章 6.3 止盈机制

        Args:
            position: 持仓对象

        Returns:
            是否触发止盈
        """
        if position.unrealized_pnl_pct >= self.risk_limits["take_profit_ratio"]:
            logger.info(
                f"止盈触发 - {position.symbol}: "
                f"盈利{position.unrealized_pnl_pct:.1%} >= {self.risk_limits['take_profit_ratio']:.1%}"
            )

            # 发送止盈事件
            if self.event_bus:
                await self.event_bus.publish(
                    {
                        "event_type": "take_profit_triggered",
                        "symbol": position.symbol,
                        "unrealized_pnl_pct": position.unrealized_pnl_pct,
                        "threshold": self.risk_limits["take_profit_ratio"],
                    }
                )

            return True

        return False

    async def check_risk_limits(self) -> Dict[str, RiskLimit]:
        """风险限额检查

        白皮书依据: 第六章 6.3 风险限额

        Returns:
            风险限额字典
        """
        limits = {}

        # 1. 总仓位限额
        total_position_value = sum(pos.market_value for pos in self.positions.values())
        position_ratio = total_position_value / self.total_capital
        limits["total_position"] = RiskLimit(
            limit_type="total_position",
            current_value=position_ratio,
            limit_value=self.risk_limits["max_position_ratio"],
            utilization=position_ratio / self.risk_limits["max_position_ratio"],
            breached=position_ratio > self.risk_limits["max_position_ratio"],
        )

        # 2. 单股仓位限额
        for symbol, position in self.positions.items():
            stock_ratio = position.market_value / self.total_capital
            limits[f"single_stock_{symbol}"] = RiskLimit(
                limit_type="single_stock",
                current_value=stock_ratio,
                limit_value=self.risk_limits["max_single_stock_ratio"],
                utilization=stock_ratio / self.risk_limits["max_single_stock_ratio"],
                breached=stock_ratio > self.risk_limits["max_single_stock_ratio"],
            )

        # 3. 行业仓位限额
        sector_values: Dict[str, float] = {}
        for position in self.positions.values():
            if position.sector:
                sector_values[position.sector] = sector_values.get(position.sector, 0) + position.market_value

        for sector, value in sector_values.items():
            sector_ratio = value / self.total_capital
            limits[f"sector_{sector}"] = RiskLimit(
                limit_type="sector",
                current_value=sector_ratio,
                limit_value=self.risk_limits["max_sector_ratio"],
                utilization=sector_ratio / self.risk_limits["max_sector_ratio"],
                breached=sector_ratio > self.risk_limits["max_sector_ratio"],
            )

        # 4. 日亏损限额
        self._reset_daily_pnl_if_needed()
        daily_loss_ratio = abs(min(0, self.daily_pnl)) / self.total_capital
        limits["daily_loss"] = RiskLimit(
            limit_type="daily_loss",
            current_value=daily_loss_ratio,
            limit_value=self.risk_limits["daily_loss_limit"],
            utilization=(
                daily_loss_ratio / self.risk_limits["daily_loss_limit"]
                if self.risk_limits["daily_loss_limit"] > 0
                else 0
            ),
            breached=daily_loss_ratio >= self.risk_limits["daily_loss_limit"],
        )

        # 检查是否有限额被突破
        breached_limits = [k for k, v in limits.items() if v.breached]
        if breached_limits:
            logger.warning(f"风险限额突破: {breached_limits}")

            # 更新风险等级
            self._update_risk_level_from_limits(limits)

        return limits

    async def emergency_shutdown(self, reason: str) -> None:
        """紧急熔断

        白皮书依据: 第六章 6.3 紧急熔断

        Args:
            reason: 熔断原因
        """
        logger.critical(f"紧急熔断激活: {reason}")

        self.emergency_shutdown_active = True
        self.shutdown_reason = reason
        self.risk_level = RiskLevel.CRITICAL

        # 发送紧急熔断事件
        if self.event_bus:
            await self.event_bus.publish(
                {"event_type": "emergency_shutdown", "reason": reason, "timestamp": datetime.now().isoformat()}
            )

        # 触发风控回调
        shutdown_result = RiskCheckResult(
            passed=False,
            check_type=RiskCheckType.DAILY_LOSS,
            reason=f"紧急熔断: {reason}",
            risk_level=RiskLevel.CRITICAL,
        )
        self._trigger_risk_callbacks(shutdown_result)

    async def deactivate_emergency_shutdown(self) -> None:
        """解除紧急熔断"""
        if not self.emergency_shutdown_active:
            logger.warning("紧急熔断未激活，无需解除")
            return

        logger.info(f"解除紧急熔断: {self.shutdown_reason}")

        self.emergency_shutdown_active = False
        self.shutdown_reason = ""
        self.risk_level = RiskLevel.LOW

        # 发送解除事件
        if self.event_bus:
            await self.event_bus.publish(
                {"event_type": "emergency_shutdown_deactivated", "timestamp": datetime.now().isoformat()}
            )

    def update_position(  # pylint: disable=too-many-positional-arguments
        self,
        symbol: str,
        quantity: float,
        cost_basis: float,
        current_price: float,
        sector: str = "",
        strategy_id: Optional[str] = None,
    ) -> None:
        """更新持仓

        Args:
            symbol: 股票代码
            quantity: 数量
            cost_basis: 成本价
            current_price: 当前价格
            sector: 行业
            strategy_id: 策略ID
        """
        if quantity <= 0:
            # 清仓
            if symbol in self.positions:
                del self.positions[symbol]
                logger.info(f"清仓 - {symbol}")
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                cost_basis=cost_basis,
                current_price=current_price,
                sector=sector,
                strategy_id=strategy_id,
            )
            logger.debug(f"更新持仓 - {symbol}: {quantity}股 @ {current_price}")

    def update_price(self, symbol: str, current_price: float) -> None:
        """更新股票价格

        Args:
            symbol: 股票代码
            current_price: 当前价格
        """
        if symbol in self.positions:
            self.positions[symbol].current_price = current_price

    def update_daily_pnl(self, pnl: float) -> None:
        """更新日盈亏

        Args:
            pnl: 盈亏金额
        """
        self._reset_daily_pnl_if_needed()
        self.daily_pnl += pnl

        logger.debug(f"日盈亏更新: {pnl:+,.0f}, 累计: {self.daily_pnl:+,.0f}")

    def update_total_capital(self, capital: float) -> None:
        """更新总资本

        Args:
            capital: 新的总资本
        """
        if capital <= 0:
            raise ValueError(f"总资本必须大于0: {capital}")

        old_capital = self.total_capital
        self.total_capital = capital

        logger.info(f"总资本更新: {old_capital:,.0f} -> {capital:,.0f}")

    def update_risk_limits(self, **kwargs) -> None:
        """更新风险限额

        Args:
            **kwargs: 风险限额参数
        """
        for key, value in kwargs.items():
            if key in self.risk_limits:
                old_value = self.risk_limits[key]
                self.risk_limits[key] = value
                logger.info(f"风险限额更新 - {key}: {old_value} -> {value}")
            else:
                logger.warning(f"未知的风险限额参数: {key}")

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """获取投资组合摘要

        Returns:
            投资组合摘要
        """
        total_position_value = sum(pos.market_value for pos in self.positions.values())
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())

        # 行业分布
        sector_distribution: Dict[str, float] = {}
        for position in self.positions.values():
            if position.sector:
                sector_distribution[position.sector] = (
                    sector_distribution.get(position.sector, 0) + position.market_value
                )

        return {
            "total_capital": self.total_capital,
            "total_position_value": total_position_value,
            "position_ratio": total_position_value / self.total_capital,
            "cash": self.total_capital - total_position_value,
            "total_unrealized_pnl": total_unrealized_pnl,
            "daily_pnl": self.daily_pnl,
            "position_count": len(self.positions),
            "sector_distribution": sector_distribution,
            "risk_level": self.risk_level.name.lower(),
            "emergency_shutdown_active": self.emergency_shutdown_active,
        }

    def get_all_positions(self) -> List[Position]:
        """获取所有持仓

        Returns:
            持仓列表
        """
        return list(self.positions.values())

    def get_position(self, symbol: str) -> Optional[Position]:
        """获取指定持仓

        Args:
            symbol: 股票代码

        Returns:
            持仓对象或None
        """
        return self.positions.get(symbol)

    def _calculate_position_risk_level(self, position: Position) -> RiskLevel:
        """计算持仓风险等级

        Args:
            position: 持仓对象

        Returns:
            风险等级
        """
        pnl_pct = position.unrealized_pnl_pct

        if pnl_pct <= -self.risk_limits["stop_loss_ratio"]:  # pylint: disable=no-else-return
            return RiskLevel.CRITICAL
        elif pnl_pct <= -self.risk_limits["stop_loss_ratio"] * 0.5:
            return RiskLevel.HIGH
        elif pnl_pct <= -self.risk_limits["stop_loss_ratio"] * 0.25:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _update_risk_level_from_limits(self, limits: Dict[str, RiskLimit]) -> None:
        """根据限额更新风险等级

        Args:
            limits: 风险限额字典
        """
        breached_count = sum(1 for v in limits.values() if v.breached)
        high_utilization_count = sum(1 for v in limits.values() if v.utilization > 0.8)

        if breached_count > 0:
            self.risk_level = RiskLevel.CRITICAL
        elif high_utilization_count >= 3:
            self.risk_level = RiskLevel.HIGH
        elif high_utilization_count >= 1:
            self.risk_level = RiskLevel.MEDIUM
        else:
            self.risk_level = RiskLevel.LOW

    async def _trigger_stop_loss_alert(self, position_risk: PositionRisk) -> None:
        """触发止损告警

        Args:
            position_risk: 持仓风险
        """
        logger.warning(f"止损告警 - {position_risk.symbol}: " f"亏损{position_risk.unrealized_pnl_pct:.1%}")

        if self.event_bus:
            await self.event_bus.publish({"event_type": "stop_loss_alert", "position": position_risk.to_dict()})

    async def _trigger_take_profit_alert(self, position_risk: PositionRisk) -> None:
        """触发止盈告警

        Args:
            position_risk: 持仓风险
        """
        logger.info(f"止盈告警 - {position_risk.symbol}: " f"盈利{position_risk.unrealized_pnl_pct:.1%}")

        if self.event_bus:
            await self.event_bus.publish({"event_type": "take_profit_alert", "position": position_risk.to_dict()})

    def _trigger_risk_callbacks(self, result: RiskCheckResult) -> None:
        """触发风控回调

        Args:
            result: 风控检查结果
        """
        for callback in self._risk_callbacks:
            try:
                callback(result)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"风控回调异常: {e}")

    def _reset_daily_pnl_if_needed(self) -> None:
        """如果是新的一天，重置日盈亏"""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if self.daily_pnl_reset_time < today_start:
            self.daily_pnl = 0.0
            self.daily_pnl_reset_time = today_start
            logger.debug("日盈亏已重置")

    def _get_sector(self, symbol: str) -> str:
        """获取股票行业（简化实现）

        Args:
            symbol: 股票代码

        Returns:
            行业名称
        """
        # 简化实现：根据股票代码前缀判断
        # 实际应该从数据源获取
        if symbol.startswith("60"):  # pylint: disable=no-else-return
            return "上海主板"
        elif symbol.startswith("00"):
            return "深圳主板"
        elif symbol.startswith("30"):
            return "创业板"
        elif symbol.startswith("68"):
            return "科创板"
        else:
            return ""

    def _get_avg_volume(self, symbol: str) -> float:  # pylint: disable=unused-argument
        """获取股票日均成交量（简化实现）

        Args:
            symbol: 股票代码

        Returns:
            日均成交量
        """
        # 简化实现：返回默认值
        # 实际应该从数据源获取
        return 10000000.0  # 1000万股

    def reset(self) -> None:
        """重置风控系统（仅用于测试）"""
        self.positions.clear()
        self.daily_pnl = 0.0
        self.daily_pnl_reset_time = datetime.now().replace(hour=0, minute=0, second=0)
        self.emergency_shutdown_active = False
        self.shutdown_reason = ""
        self.risk_level = RiskLevel.LOW
        logger.warning("RiskControlSystem已重置")
