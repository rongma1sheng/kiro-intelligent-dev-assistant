"""IPC标准化协议

白皮书依据: 第三章 3.6 IPC标准化协议

使用Pydantic定义标准化的进程间通信数据模型，确保数据完整性和类型安全。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from loguru import logger
from pydantic import BaseModel, Field, field_validator, model_validator


class OrderSide(Enum):
    """订单方向

    白皮书依据: 第三章 3.6
    """

    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """订单类型

    白皮书依据: 第三章 3.6
    """

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """订单状态

    白皮书依据: 第三章 3.6
    """

    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TickData(BaseModel):
    """Tick数据模型

    白皮书依据: 第三章 3.6 IPC标准化协议

    用于高频Tick数据传输，包含最新价格、成交量、买卖盘等信息。

    Attributes:
        symbol: 标的代码
        timestamp: 时间戳
        last_price: 最新价
        volume: 成交量
        turnover: 成交额
        bid_price_1: 买一价
        bid_volume_1: 买一量
        ask_price_1: 卖一价
        ask_volume_1: 卖一量
        open_interest: 持仓量(期货)

    Example:
        >>> tick = TickData(
        ...     symbol="000001.SZ",
        ...     timestamp=datetime.now(),
        ...     last_price=10.50,
        ...     volume=1000000
        ... )
    """

    # 基础信息
    symbol: str = Field(..., description="标的代码")
    timestamp: datetime = Field(..., description="时间戳")

    # 价格信息
    last_price: float = Field(..., gt=0, description="最新价")
    open_price: Optional[float] = Field(None, gt=0, description="开盘价")
    high_price: Optional[float] = Field(None, gt=0, description="最高价")
    low_price: Optional[float] = Field(None, gt=0, description="最低价")
    pre_close: Optional[float] = Field(None, gt=0, description="昨收价")

    # 成交信息
    volume: int = Field(..., ge=0, description="成交量")
    turnover: float = Field(0.0, ge=0, description="成交额")

    # 买卖盘信息 (5档)
    bid_price_1: Optional[float] = Field(None, gt=0, description="买一价")
    bid_volume_1: Optional[int] = Field(None, ge=0, description="买一量")
    bid_price_2: Optional[float] = Field(None, gt=0, description="买二价")
    bid_volume_2: Optional[int] = Field(None, ge=0, description="买二量")
    bid_price_3: Optional[float] = Field(None, gt=0, description="买三价")
    bid_volume_3: Optional[int] = Field(None, ge=0, description="买三量")
    bid_price_4: Optional[float] = Field(None, gt=0, description="买四价")
    bid_volume_4: Optional[int] = Field(None, ge=0, description="买四量")
    bid_price_5: Optional[float] = Field(None, gt=0, description="买五价")
    bid_volume_5: Optional[int] = Field(None, ge=0, description="买五量")

    ask_price_1: Optional[float] = Field(None, gt=0, description="卖一价")
    ask_volume_1: Optional[int] = Field(None, ge=0, description="卖一量")
    ask_price_2: Optional[float] = Field(None, gt=0, description="卖二价")
    ask_volume_2: Optional[int] = Field(None, ge=0, description="卖二量")
    ask_price_3: Optional[float] = Field(None, gt=0, description="卖三价")
    ask_volume_3: Optional[int] = Field(None, ge=0, description="卖三量")
    ask_price_4: Optional[float] = Field(None, gt=0, description="卖四价")
    ask_volume_4: Optional[int] = Field(None, ge=0, description="卖四量")
    ask_price_5: Optional[float] = Field(None, gt=0, description="卖五价")
    ask_volume_5: Optional[int] = Field(None, ge=0, description="卖五量")

    # 期货特有
    open_interest: Optional[int] = Field(None, ge=0, description="持仓量")

    # 元数据
    exchange: Optional[str] = Field(None, description="交易所")
    data_source: Optional[str] = Field(None, description="数据源")

    class Config:
        """Pydantic配置"""

        json_encoders = {datetime: lambda v: v.isoformat()}

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """验证标的代码格式"""
        if not v or len(v) < 6:
            raise ValueError(f"Invalid symbol format: {v}")
        return v.upper()

    @model_validator(mode="after")
    def validate_prices(self):
        """验证价格一致性"""
        last_price = self.last_price
        high_price = self.high_price
        low_price = self.low_price

        if high_price and low_price:
            if high_price < low_price:
                raise ValueError(f"High price {high_price} < Low price {low_price}")

        if high_price and last_price:
            if last_price > high_price * 1.01:  # 允许1%误差
                logger.warning(f"Last price {last_price} > High price {high_price}")

        if low_price and last_price:
            if last_price < low_price * 0.99:  # 允许1%误差
                logger.warning(f"Last price {last_price} < Low price {low_price}")

        return self

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.dict(exclude_none=True)

    def get_mid_price(self) -> Optional[float]:
        """获取中间价"""
        if self.bid_price_1 and self.ask_price_1:
            return (self.bid_price_1 + self.ask_price_1) / 2
        return None

    def get_spread(self) -> Optional[float]:
        """获取买卖价差"""
        if self.bid_price_1 and self.ask_price_1:
            return self.ask_price_1 - self.bid_price_1
        return None

    def get_spread_bps(self) -> Optional[float]:
        """获取买卖价差(基点)"""
        spread = self.get_spread()
        mid_price = self.get_mid_price()

        if spread and mid_price and mid_price > 0:
            return (spread / mid_price) * 10000
        return None


class BarData(BaseModel):
    """K线数据模型

    白皮书依据: 第三章 3.6 IPC标准化协议

    用于K线数据传输，支持多种周期(1分钟、5分钟、日线等)。

    Attributes:
        symbol: 标的代码
        timestamp: 时间戳
        open: 开盘价
        high: 最高价
        low: 最低价
        close: 收盘价
        volume: 成交量
        turnover: 成交额
        interval: K线周期

    Example:
        >>> bar = BarData(
        ...     symbol="000001.SZ",
        ...     timestamp=datetime.now(),
        ...     open=10.0,
        ...     high=10.5,
        ...     low=9.8,
        ...     close=10.2,
        ...     volume=1000000,
        ...     interval="1m"
        ... )
    """

    # 基础信息
    symbol: str = Field(..., description="标的代码")
    timestamp: datetime = Field(..., description="时间戳")
    interval: str = Field(..., description="K线周期(1m/5m/15m/30m/1h/1d)")

    # OHLC价格
    open: float = Field(..., gt=0, description="开盘价")
    high: float = Field(..., gt=0, description="最高价")
    low: float = Field(..., gt=0, description="最低价")
    close: float = Field(..., gt=0, description="收盘价")

    # 成交信息
    volume: int = Field(..., ge=0, description="成交量")
    turnover: float = Field(0.0, ge=0, description="成交额")

    # 期货特有
    open_interest: Optional[int] = Field(None, ge=0, description="持仓量")

    # 元数据
    exchange: Optional[str] = Field(None, description="交易所")
    data_source: Optional[str] = Field(None, description="数据源")

    class Config:
        """Pydantic配置"""

        json_encoders = {datetime: lambda v: v.isoformat()}

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """验证标的代码格式"""
        if not v or len(v) < 6:
            raise ValueError(f"Invalid symbol format: {v}")
        return v.upper()

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v):
        """验证K线周期"""
        valid_intervals = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d", "1w", "1M"]
        if v not in valid_intervals:
            raise ValueError(f"Invalid interval: {v}, must be one of {valid_intervals}")
        return v

    @model_validator(mode="after")
    def validate_ohlc(self):
        """验证OHLC一致性

        白皮书依据: 第三章 3.3 Layer 3 HLOC一致性检查
        """
        open_price = self.open
        high = self.high
        low = self.low
        close = self.close

        if not all([open_price, high, low, close]):
            return self

        # 检查high >= max(open, close)
        if high < max(open_price, close):
            raise ValueError(f"High {high} < max(open {open_price}, close {close})")

        # 检查low <= min(open, close)
        if low > min(open_price, close):
            raise ValueError(f"Low {low} > min(open {open_price}, close {close})")

        # 检查high >= low
        if high < low:
            raise ValueError(f"High {high} < Low {low}")

        return self

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.dict(exclude_none=True)

    def get_return(self) -> float:
        """获取收益率"""
        if self.open > 0:
            return (self.close - self.open) / self.open
        return 0.0

    def get_amplitude(self) -> float:
        """获取振幅"""
        if self.open > 0:
            return (self.high - self.low) / self.open
        return 0.0

    def is_bullish(self) -> bool:
        """是否阳线"""
        return self.close > self.open

    def is_bearish(self) -> bool:
        """是否阴线"""
        return self.close < self.open


class OrderData(BaseModel):
    """订单数据模型

    白皮书依据: 第三章 3.6 IPC标准化协议

    用于订单信息传输，包含订单的完整生命周期信息。

    Attributes:
        order_id: 订单ID
        symbol: 标的代码
        side: 买卖方向
        order_type: 订单类型
        price: 委托价格
        quantity: 委托数量
        status: 订单状态
        filled_quantity: 已成交数量
        filled_amount: 已成交金额

    Example:
        >>> order = OrderData(
        ...     order_id="ORD001",
        ...     symbol="000001.SZ",
        ...     side=OrderSide.BUY,
        ...     order_type=OrderType.LIMIT,
        ...     price=10.50,
        ...     quantity=1000
        ... )
    """

    # 订单标识
    order_id: str = Field(..., description="订单ID")
    client_order_id: Optional[str] = Field(None, description="客户端订单ID")

    # 标的信息
    symbol: str = Field(..., description="标的代码")
    exchange: Optional[str] = Field(None, description="交易所")

    # 订单信息
    side: OrderSide = Field(..., description="买卖方向")
    order_type: OrderType = Field(..., description="订单类型")
    price: float = Field(..., gt=0, description="委托价格")
    quantity: int = Field(..., gt=0, description="委托数量")

    # 止损止盈
    stop_price: Optional[float] = Field(None, gt=0, description="止损价")

    # 状态信息
    status: OrderStatus = Field(OrderStatus.PENDING, description="订单状态")
    filled_quantity: int = Field(0, ge=0, description="已成交数量")
    filled_amount: float = Field(0.0, ge=0, description="已成交金额")

    # 时间信息
    created_time: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_time: Optional[datetime] = Field(None, description="更新时间")
    filled_time: Optional[datetime] = Field(None, description="成交时间")

    # 策略信息
    strategy_id: Optional[str] = Field(None, description="策略ID")
    strategy_name: Optional[str] = Field(None, description="策略名称")

    # 备注
    notes: Optional[str] = Field(None, description="备注")

    class Config:
        """Pydantic配置"""

        use_enum_values = False
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            OrderSide: lambda v: v.value,
            OrderType: lambda v: v.value,
            OrderStatus: lambda v: v.value,
        }

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """验证标的代码格式"""
        if not v or len(v) < 6:
            raise ValueError(f"Invalid symbol format: {v}")
        return v.upper()

    @model_validator(mode="after")
    def validate_filled_quantity(self):
        """验证已成交数量"""
        if self.filled_quantity > self.quantity:
            raise ValueError(f"Filled quantity {self.filled_quantity} > Order quantity {self.quantity}")
        return self

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = self.dict(exclude_none=True)
        # 转换枚举为字符串
        if "side" in data:
            data["side"] = self.side.value  # pylint: disable=no-member
        if "order_type" in data:
            data["order_type"] = self.order_type.value  # pylint: disable=no-member
        if "status" in data:
            data["status"] = self.status.value
        return data

    def get_average_price(self) -> Optional[float]:
        """获取平均成交价"""
        if self.filled_quantity > 0 and self.filled_amount > 0:
            return self.filled_amount / self.filled_quantity
        return None

    def get_fill_ratio(self) -> float:
        """获取成交比例"""
        if self.quantity > 0:
            return self.filled_quantity / self.quantity
        return 0.0

    def is_filled(self) -> bool:
        """是否完全成交"""
        return self.status == OrderStatus.FILLED

    def is_active(self) -> bool:
        """是否活跃订单"""
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILLED]

    def update_fill(self, filled_quantity: int, filled_amount: float) -> None:
        """更新成交信息"""
        self.filled_quantity = filled_quantity
        self.filled_amount = filled_amount
        self.updated_time = datetime.now()

        # 更新状态
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
            self.filled_time = datetime.now()
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIAL_FILLED


class TradeData(BaseModel):
    """成交数据模型

    白皮书依据: 第三章 3.6 IPC标准化协议

    用于成交记录传输，记录每笔实际成交的详细信息。

    Attributes:
        trade_id: 成交ID
        order_id: 订单ID
        symbol: 标的代码
        side: 买卖方向
        price: 成交价格
        quantity: 成交数量
        amount: 成交金额
        commission: 手续费

    Example:
        >>> trade = TradeData(
        ...     trade_id="TRD001",
        ...     order_id="ORD001",
        ...     symbol="000001.SZ",
        ...     side=OrderSide.BUY,
        ...     price=10.50,
        ...     quantity=1000
        ... )
    """

    # 成交标识
    trade_id: str = Field(..., description="成交ID")
    order_id: str = Field(..., description="订单ID")

    # 标的信息
    symbol: str = Field(..., description="标的代码")
    exchange: Optional[str] = Field(None, description="交易所")

    # 成交信息
    side: OrderSide = Field(..., description="买卖方向")
    price: float = Field(..., gt=0, description="成交价格")
    quantity: int = Field(..., gt=0, description="成交数量")
    amount: float = Field(..., gt=0, description="成交金额")

    # 费用信息
    commission: float = Field(0.0, ge=0, description="手续费")
    tax: float = Field(0.0, ge=0, description="印花税")

    # 时间信息
    trade_time: datetime = Field(default_factory=datetime.now, description="成交时间")

    # 策略信息
    strategy_id: Optional[str] = Field(None, description="策略ID")
    strategy_name: Optional[str] = Field(None, description="策略名称")

    class Config:
        """Pydantic配置"""

        use_enum_values = False
        json_encoders = {datetime: lambda v: v.isoformat(), OrderSide: lambda v: v.value}

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """验证标的代码格式"""
        if not v or len(v) < 6:
            raise ValueError(f"Invalid symbol format: {v}")
        return v.upper()

    @model_validator(mode="after")
    def validate_amount(self):
        """验证成交金额"""
        price = self.price
        quantity = self.quantity
        amount = self.amount

        if price > 0 and quantity > 0:
            expected_amount = price * quantity
            # 允许0.1%误差
            if abs(amount - expected_amount) / expected_amount > 0.001:
                logger.warning(f"Amount {amount} != price {price} * quantity {quantity}")

        return self

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = self.dict(exclude_none=True)
        # 转换枚举为字符串
        if "side" in data:
            data["side"] = self.side.value  # pylint: disable=no-member
        return data

    def get_net_amount(self) -> float:
        """获取净成交金额(扣除费用)"""
        if self.side == OrderSide.BUY:  # pylint: disable=no-else-return
            return self.amount + self.commission + self.tax
        else:
            return self.amount - self.commission - self.tax


class PositionData(BaseModel):
    """持仓数据模型

    白皮书依据: 第三章 3.6 IPC标准化协议

    用于持仓信息传输，记录当前持仓状态和盈亏情况。

    Attributes:
        symbol: 标的代码
        quantity: 持仓数量
        available_quantity: 可用数量
        avg_price: 平均成本
        last_price: 最新价
        market_value: 市值
        pnl: 浮动盈亏

    Example:
        >>> position = PositionData(
        ...     symbol="000001.SZ",
        ...     quantity=1000,
        ...     available_quantity=1000,
        ...     avg_price=10.0,
        ...     last_price=10.5
        ... )
    """

    # 标的信息
    symbol: str = Field(..., description="标的代码")
    exchange: Optional[str] = Field(None, description="交易所")

    # 持仓数量
    quantity: int = Field(..., description="持仓数量")
    available_quantity: int = Field(..., description="可用数量")
    frozen_quantity: int = Field(0, ge=0, description="冻结数量")

    # 成本信息
    avg_price: float = Field(..., gt=0, description="平均成本")
    total_cost: float = Field(0.0, gt=0, description="总成本")

    # 市场信息
    last_price: float = Field(..., gt=0, description="最新价")
    market_value: float = Field(0.0, gt=0, description="市值")

    # 盈亏信息
    pnl: float = Field(0.0, description="浮动盈亏")
    pnl_ratio: float = Field(0.0, description="盈亏比例")

    # 时间信息
    updated_time: datetime = Field(default_factory=datetime.now, description="更新时间")

    # 策略信息
    strategy_id: Optional[str] = Field(None, description="策略ID")
    strategy_name: Optional[str] = Field(None, description="策略名称")

    class Config:
        """Pydantic配置"""

        json_encoders = {datetime: lambda v: v.isoformat()}

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """验证标的代码格式"""
        if not v or len(v) < 6:
            raise ValueError(f"Invalid symbol format: {v}")
        return v.upper()

    @model_validator(mode="after")
    def validate_available_quantity(self):
        """验证可用数量"""
        if self.available_quantity > self.quantity:
            raise ValueError(f"Available quantity {self.available_quantity} > Total quantity {self.quantity}")
        return self

    @model_validator(mode="after")
    def calculate_derived_fields(self):
        """计算派生字段"""
        quantity = self.quantity
        avg_price = self.avg_price
        last_price = self.last_price

        # 计算总成本
        if self.total_cost == 0:
            self.total_cost = quantity * avg_price

        # 计算市值
        if self.market_value == 0:
            self.market_value = quantity * last_price

        # 计算盈亏
        self.pnl = self.market_value - self.total_cost

        # 计算盈亏比例
        if self.total_cost > 0:
            self.pnl_ratio = self.pnl / self.total_cost
        else:
            self.pnl_ratio = 0.0

        return self

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.dict(exclude_none=True)

    def update_price(self, last_price: float) -> None:
        """更新价格并重新计算盈亏"""
        self.last_price = last_price
        self.market_value = self.quantity * last_price
        self.pnl = self.market_value - self.total_cost
        if self.total_cost > 0:
            self.pnl_ratio = self.pnl / self.total_cost
        self.updated_time = datetime.now()


# 工具函数


def validate_ipc_data(data: BaseModel) -> bool:
    """验证IPC数据

    白皮书依据: 第三章 3.6

    Args:
        data: IPC数据模型实例

    Returns:
        是否验证通过
    """
    try:
        # Pydantic会自动验证
        data.dict()
        return True
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"IPC data validation failed: {e}")
        return False


def serialize_ipc_data(data: BaseModel) -> bytes:
    """序列化IPC数据

    白皮书依据: 第三章 3.6

    Args:
        data: IPC数据模型实例

    Returns:
        序列化后的字节数据
    """
    json_str = data.json()
    return json_str.encode("utf-8")


def deserialize_ipc_data(data_bytes: bytes, model_class: type) -> BaseModel:
    """反序列化IPC数据

    白皮书依据: 第三章 3.6

    Args:
        data_bytes: 序列化的字节数据
        model_class: 数据模型类

    Returns:
        数据模型实例
    """
    json_str = data_bytes.decode("utf-8")
    return model_class.parse_raw(json_str)
