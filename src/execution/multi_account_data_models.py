"""多账户管理数据模型

白皮书依据: 第十七章 17.3.1 多账户管理系统
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from src.evolution.qmt_broker_api import QMTConnectionConfig


@dataclass
class AccountConfig:
    """账户配置

    白皮书依据: 第十七章 17.3.1 多账户管理系统

    Attributes:
        account_id: 账户ID（唯一标识）
        broker_name: 券商名称（国金/华泰/中信等）
        account_type: 账户类型（实盘/模拟盘）
        qmt_config: QMT连接配置
        max_capital: 最大资金容量
        enabled: 是否启用
        priority: 优先级（1-10，数字越大优先级越高）
        metadata: 额外元数据
    """

    account_id: str
    broker_name: str
    account_type: str
    qmt_config: QMTConnectionConfig
    max_capital: float
    enabled: bool = True
    priority: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后验证"""
        if self.max_capital <= 0:
            raise ValueError(f"最大资金容量必须大于0: {self.max_capital}")

        if not 1 <= self.priority <= 10:
            raise ValueError(f"优先级必须在1-10之间: {self.priority}")

        if self.account_type not in ["实盘", "模拟盘"]:
            raise ValueError(f"账户类型必须是'实盘'或'模拟盘': {self.account_type}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "account_id": self.account_id,
            "broker_name": self.broker_name,
            "account_type": self.account_type,
            "qmt_config": {"account_id": self.qmt_config.account_id, "mini_qmt_path": self.qmt_config.mini_qmt_path},
            "max_capital": self.max_capital,
            "enabled": self.enabled,
            "priority": self.priority,
            "metadata": self.metadata,
        }


@dataclass
class AccountStatus:
    """账户状态

    白皮书依据: 第十七章 17.3.1 多账户管理系统

    Attributes:
        account_id: 账户ID
        broker_name: 券商名称
        connected: 是否已连接
        total_assets: 总资产
        available_cash: 可用资金
        market_value: 持仓市值
        position_count: 持仓数量
        today_pnl: 今日盈亏
        health_status: 健康状态（healthy/warning/error）
        last_update_time: 最后更新时间
        error_message: 错误信息（如果有）
    """

    account_id: str
    broker_name: str
    connected: bool
    total_assets: float
    available_cash: float
    market_value: float
    position_count: int
    today_pnl: float
    health_status: str
    last_update_time: datetime
    error_message: Optional[str] = None

    def __post_init__(self):
        """初始化后验证"""
        if self.health_status not in ["healthy", "warning", "error"]:
            raise ValueError(f"健康状态必须是'healthy'、'warning'或'error': {self.health_status}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "account_id": self.account_id,
            "broker_name": self.broker_name,
            "connected": self.connected,
            "total_assets": self.total_assets,
            "available_cash": self.available_cash,
            "market_value": self.market_value,
            "position_count": self.position_count,
            "today_pnl": self.today_pnl,
            "health_status": self.health_status,
            "last_update_time": self.last_update_time.isoformat(),
            "error_message": self.error_message,
        }


@dataclass
class OrderRoutingResult:
    """订单路由结果

    白皮书依据: 第十七章 17.3.1 多账户管理系统

    Attributes:
        account_id: 选中的账户ID
        reason: 选择原因
        confidence: 置信度（0-1）
        routing_strategy: 使用的路由策略
        timestamp: 路由时间戳
    """

    account_id: str
    reason: str
    confidence: float
    routing_strategy: str
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """初始化后验证"""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"置信度必须在0-1之间: {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "account_id": self.account_id,
            "reason": self.reason,
            "confidence": self.confidence,
            "routing_strategy": self.routing_strategy,
            "timestamp": self.timestamp.isoformat(),
        }
