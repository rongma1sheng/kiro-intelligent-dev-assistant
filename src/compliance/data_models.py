"""合规模块数据模型

白皮书依据: 第七章 7.3 合规体系
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class ComplianceCheckType(Enum):
    """合规检查类型

    白皮书依据: 第七章 7.3 合规体系
    """

    DAILY_TRADE_LIMIT = "daily_trade_limit"
    SINGLE_TRADE_AMOUNT = "single_trade_amount"
    ST_STOCK = "st_stock"
    SUSPENDED_STOCK = "suspended_stock"
    NEW_STOCK = "new_stock"
    MARGIN_RATIO = "margin_ratio"


@dataclass
class TradeOrder:
    """交易订单

    白皮书依据: 第七章 7.3 合规体系

    Attributes:
        symbol: 股票代码
        action: 交易动作（buy/sell）
        quantity: 交易数量
        price: 交易价格
        is_derivative: 是否为衍生品
        strategy_id: 策略ID
        order_id: 订单ID
    """

    symbol: str
    action: str
    quantity: float
    price: float
    is_derivative: bool = False
    strategy_id: str = ""
    order_id: str = ""

    @property
    def amount(self) -> float:
        """计算交易金额"""
        return self.quantity * self.price

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "action": self.action,
            "quantity": self.quantity,
            "price": self.price,
            "amount": self.amount,
            "is_derivative": self.is_derivative,
            "strategy_id": self.strategy_id,
            "order_id": self.order_id,
        }


@dataclass
class ComplianceViolation:
    """合规违规记录

    白皮书依据: 第七章 7.3 合规体系

    Attributes:
        check_type: 检查类型
        message: 违规消息
        details: 详细信息
    """

    check_type: ComplianceCheckType
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "check_type": self.check_type.value,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class StockInfo:
    """股票信息

    白皮书依据: 第七章 7.3 合规体系

    Attributes:
        symbol: 股票代码
        name: 股票名称
        is_st: 是否为ST股票
        is_suspended: 是否停牌
        list_date: 上市日期
    """

    symbol: str
    name: str = ""
    is_st: bool = False
    is_suspended: bool = False
    list_date: Optional[datetime] = None

    def days_since_listing(self) -> int:
        """计算上市天数"""
        if self.list_date is None:
            return 999  # 默认返回大值，表示已上市很久
        return (datetime.now() - self.list_date).days

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "is_st": self.is_st,
            "is_suspended": self.is_suspended,
            "list_date": self.list_date.isoformat() if self.list_date else None,
        }
