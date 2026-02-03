"""审计模块数据模型

白皮书依据: 第七章 7.2 审计体系
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict


class AuditEventType(Enum):
    """审计事件类型

    白皮书依据: 第七章 7.2.2 审计日志系统
    """

    TRADE_EXECUTION = "TRADE_EXECUTION"
    POSITION_CHANGE = "POSITION_CHANGE"
    BALANCE_CHANGE = "BALANCE_CHANGE"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    USER_LOGIN = "USER_LOGIN"
    API_CALL = "API_CALL"
    ALERT_TRIGGERED = "ALERT_TRIGGERED"


@dataclass
class AuditEntry:
    """审计日志条目

    白皮书依据: 第七章 7.2.2 审计日志系统

    Attributes:
        timestamp: 时间戳
        event_type: 事件类型
        data: 事件数据
        audit_signature: 审计签名（SHA256）
        user_id: 用户ID
    """

    timestamp: datetime
    event_type: AuditEventType
    data: Dict[str, Any]
    audit_signature: str
    user_id: str = "system"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "data": self.data,
            "audit_signature": self.audit_signature,
            "user_id": self.user_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEntry":
        """从字典创建"""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=AuditEventType(data["event_type"]),
            data=data["data"],
            audit_signature=data["audit_signature"],
            user_id=data.get("user_id", "system"),
        )


@dataclass
class ShadowLedgerEntry:
    """影子账本条目

    白皮书依据: 第七章 7.2.1 独立审计进程

    Attributes:
        symbol: 股票代码
        quantity: 持仓数量
        avg_cost: 平均成本
        last_sync: 最后同步时间
    """

    symbol: str
    quantity: int
    avg_cost: float
    last_sync: datetime

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_cost": self.avg_cost,
            "last_sync": self.last_sync.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShadowLedgerEntry":
        """从字典创建"""
        return cls(
            symbol=data["symbol"],
            quantity=data["quantity"],
            avg_cost=data["avg_cost"],
            last_sync=datetime.fromisoformat(data["last_sync"]),
        )


@dataclass
class ShadowPosition:
    """影子账本持仓

    白皮书依据: 第七章 7.2.1 独立审计进程

    Attributes:
        symbol: 股票代码
        quantity: 持仓数量（支持小数）
        avg_cost: 平均成本
        last_sync: 最后同步时间（ISO格式字符串）
    """

    symbol: str
    quantity: float
    avg_cost: float
    last_sync: str

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_cost": self.avg_cost,
            "last_sync": self.last_sync,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShadowPosition":
        """从字典创建"""
        return cls(
            symbol=data["symbol"],
            quantity=data["quantity"],
            avg_cost=data["avg_cost"],
            last_sync=data["last_sync"],
        )


@dataclass
class ReconciliationDiscrepancy:
    """对账差异

    白皮书依据: 第七章 7.2.1 独立审计进程

    Attributes:
        symbol: 股票代码
        shadow_quantity: 影子账本数量
        execution_quantity: 执行进程数量
        difference: 差异
    """

    symbol: str
    shadow_quantity: float
    execution_quantity: float
    difference: float

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "shadow_quantity": self.shadow_quantity,
            "execution_quantity": self.execution_quantity,
            "difference": self.difference,
        }
