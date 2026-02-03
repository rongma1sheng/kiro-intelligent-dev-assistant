"""执行与风控模块

白皮书依据: 第六章 执行与风控 (Execution & Risk)

核心组件：
- OrderManager: 订单管理器 - 订单生命周期管理
- RiskControlSystem: 风控系统 - 统一风险控制
- LockBox: 资本基因与诺亚方舟 - 利润物理隔离
- MarginWatchdog: 风险门闸 - 衍生品保证金监控
"""

from src.execution.lockbox import LockBox, LockBoxConfig, SafeAssetType
from src.execution.margin_watchdog import MarginPosition, MarginWatchdog, MarginWatchdogConfig, RiskLevel
from src.execution.order_manager import (
    Order,
    OrderManager,
    OrderManagerError,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    OrderValidationError,
    RiskViolationError,
)
from src.execution.risk_control_system import (
    EmergencyShutdownError,
    Position,
    PositionRisk,
    RiskCheckResult,
    RiskCheckType,
    RiskControlError,
    RiskControlSystem,
)
from src.execution.risk_control_system import RiskLevel as RiskControlLevel
from src.execution.risk_control_system import (
    RiskLimit,
)

__all__ = [
    # OrderManager
    "OrderManager",
    "Order",
    "OrderResult",
    "OrderStatus",
    "OrderType",
    "OrderSide",
    "OrderManagerError",
    "OrderValidationError",
    "RiskViolationError",
    # RiskControlSystem
    "RiskControlSystem",
    "RiskCheckResult",
    "RiskCheckType",
    "RiskLimit",
    "Position",
    "PositionRisk",
    "RiskControlError",
    "EmergencyShutdownError",
    "RiskControlLevel",
    # LockBox
    "LockBox",
    "LockBoxConfig",
    "SafeAssetType",
    # MarginWatchdog
    "MarginWatchdog",
    "MarginWatchdogConfig",
    "RiskLevel",
    "MarginPosition",
]
