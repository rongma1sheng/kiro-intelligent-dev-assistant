"""末日风控监控器

白皮书依据: 第七章 6.4 末日风控

监控极端损失条件，触发紧急停止。

触发条件：
- lock文件存在
- 单日亏损 > 10%
- 连续3日亏损 > 20%
- 保证金风险度 > 95%
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol

from loguru import logger


class DoomsdayTriggerType(Enum):
    """末日触发类型"""

    LOCK_FILE = "lock_file"
    DAILY_LOSS = "daily_loss"
    CONSECUTIVE_LOSS = "consecutive_loss"
    MARGIN_RISK = "margin_risk"
    MANUAL = "manual"


class DoomsdayError(Exception):
    """末日风控错误"""


class DoomsdayAlreadyTriggeredError(DoomsdayError):
    """末日开关已触发错误"""


@dataclass
class DoomsdayEvent:
    """末日事件"""

    timestamp: str
    trigger_type: DoomsdayTriggerType
    reason: str
    trigger_value: float
    threshold: float
    actions_taken: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "trigger_type": self.trigger_type.value,
            "reason": self.reason,
            "trigger_value": self.trigger_value,
            "threshold": self.threshold,
            "actions_taken": self.actions_taken,
        }


@dataclass
class DoomsdayStatus:
    """末日状态"""

    is_triggered: bool
    trigger_time: Optional[str] = None
    trigger_type: Optional[DoomsdayTriggerType] = None
    reason: Optional[str] = None
    daily_pnl_percentage: float = 0.0
    consecutive_loss_percentage: float = 0.0
    margin_risk_ratio: float = 0.0
    lock_file_exists: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_triggered": self.is_triggered,
            "trigger_time": self.trigger_time,
            "trigger_type": self.trigger_type.value if self.trigger_type else None,
            "reason": self.reason,
            "daily_pnl_percentage": self.daily_pnl_percentage,
            "consecutive_loss_percentage": self.consecutive_loss_percentage,
            "margin_risk_ratio": self.margin_risk_ratio,
            "lock_file_exists": self.lock_file_exists,
        }


class TradingEngineProtocol(Protocol):
    """交易引擎协议"""

    async def emergency_stop(self) -> None:
        """紧急停止"""
        ...  # pylint: disable=w2301

    async def cancel_all_orders(self) -> int:
        """取消所有订单"""
        ...  # pylint: disable=w2301

    async def close_all_positions(self) -> int:
        """平掉所有仓位"""
        ...  # pylint: disable=w2301


class NotificationManagerProtocol(Protocol):
    """通知管理器协议"""

    async def send_alert(self, title: str, message: str, level: str) -> None:
        """发送告警"""
        ...  # pylint: disable=w2301


class PortfolioDataProviderProtocol(Protocol):
    """投资组合数据提供者协议"""

    def get_daily_pnl(self) -> float:
        """获取当日盈亏金额"""
        ...  # pylint: disable=w2301

    def get_total_assets(self) -> float:
        """获取总资产"""
        ...  # pylint: disable=w2301

    def get_historical_pnl(self, days: int) -> List[float]:
        """获取历史盈亏列表"""
        ...  # pylint: disable=w2301

    def get_margin_used(self) -> float:
        """获取已用保证金"""
        ...  # pylint: disable=w2301

    def get_margin_available(self) -> float:
        """获取可用保证金"""
        ...  # pylint: disable=w2301


class DoomsdayMonitor:  # pylint: disable=too-many-instance-attributes
    """末日风控监控器

    白皮书依据: 第七章 6.4 末日风控

    监控极端损失条件，触发紧急停止。

    触发条件：
    - lock文件存在
    - 单日亏损 > 10%
    - 连续3日亏损 > 20%
    - 保证金风险度 > 95%

    Attributes:
        lock_file: 末日开关文件路径
        daily_loss_threshold: 单日亏损阈值（百分比）
        consecutive_loss_threshold: 连续亏损阈值（百分比）
        consecutive_days: 连续亏损天数
        margin_risk_threshold: 保证金风险阈值（百分比）
        trading_engine: 交易引擎
        notification_manager: 通知管理器
        audit_logger: 审计日志
        portfolio_provider: 投资组合数据提供者
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        lock_file: Optional[Path] = None,
        daily_loss_threshold: float = 10.0,
        consecutive_loss_threshold: float = 20.0,
        consecutive_days: int = 3,
        margin_risk_threshold: float = 95.0,
        trading_engine: Optional[TradingEngineProtocol] = None,
        notification_manager: Optional[NotificationManagerProtocol] = None,
        audit_logger: Optional[Any] = None,
        portfolio_provider: Optional[PortfolioDataProviderProtocol] = None,
    ):
        """初始化DoomsdayMonitor

        白皮书依据: 第七章 6.4 末日风控

        Args:
            lock_file: 末日开关文件路径，默认D:/MIA_Data/.doomsday.lock
            daily_loss_threshold: 单日亏损阈值（百分比），默认10%
            consecutive_loss_threshold: 连续亏损阈值（百分比），默认20%
            consecutive_days: 连续亏损天数，默认3天
            margin_risk_threshold: 保证金风险阈值（百分比），默认95%
            trading_engine: 交易引擎
            notification_manager: 通知管理器
            audit_logger: 审计日志
            portfolio_provider: 投资组合数据提供者

        Raises:
            ValueError: 当阈值参数无效时
        """
        # 参数验证
        if daily_loss_threshold <= 0 or daily_loss_threshold > 100:
            raise ValueError(f"单日亏损阈值必须在(0, 100]范围内，当前: {daily_loss_threshold}")

        if consecutive_loss_threshold <= 0 or consecutive_loss_threshold > 100:
            raise ValueError(f"连续亏损阈值必须在(0, 100]范围内，当前: {consecutive_loss_threshold}")

        if consecutive_days <= 0:
            raise ValueError(f"连续亏损天数必须大于0，当前: {consecutive_days}")

        if margin_risk_threshold <= 0 or margin_risk_threshold > 100:
            raise ValueError(f"保证金风险阈值必须在(0, 100]范围内，当前: {margin_risk_threshold}")

        # 设置lock文件路径
        if lock_file is None:
            self.lock_file = Path("D:/MIA_Data/.doomsday.lock")
        else:
            self.lock_file = Path(lock_file)

        # 阈值设置
        self.daily_loss_threshold = daily_loss_threshold
        self.consecutive_loss_threshold = consecutive_loss_threshold
        self.consecutive_days = consecutive_days
        self.margin_risk_threshold = margin_risk_threshold

        # 依赖组件
        self.trading_engine = trading_engine
        self.notification_manager = notification_manager
        self.audit_logger = audit_logger
        self.portfolio_provider = portfolio_provider

        # 内部状态
        self._is_triggered = False
        self._trigger_time: Optional[str] = None
        self._trigger_type: Optional[DoomsdayTriggerType] = None
        self._trigger_reason: Optional[str] = None
        self._events: List[DoomsdayEvent] = []
        self._callbacks: List[Callable[[DoomsdayEvent], None]] = []

        # 模拟数据（用于测试）
        self._mock_daily_pnl: Optional[float] = None
        self._mock_total_assets: Optional[float] = None
        self._mock_historical_pnl: Optional[List[float]] = None
        self._mock_margin_used: Optional[float] = None
        self._mock_margin_available: Optional[float] = None

        logger.info(
            f"初始化DoomsdayMonitor: "
            f"lock_file={self.lock_file}, "
            f"daily_loss_threshold={daily_loss_threshold}%, "
            f"consecutive_loss_threshold={consecutive_loss_threshold}%, "
            f"consecutive_days={consecutive_days}, "
            f"margin_risk_threshold={margin_risk_threshold}%"
        )

    @property
    def is_triggered(self) -> bool:
        """是否已触发末日开关"""
        return self._is_triggered

    def get_status(self) -> DoomsdayStatus:
        """获取末日状态

        Returns:
            末日状态对象
        """
        return DoomsdayStatus(
            is_triggered=self._is_triggered,
            trigger_time=self._trigger_time,
            trigger_type=self._trigger_type,
            reason=self._trigger_reason,
            daily_pnl_percentage=self.get_daily_pnl_percentage(),
            consecutive_loss_percentage=self.get_consecutive_loss_percentage(),
            margin_risk_ratio=self.get_margin_risk_ratio(),
            lock_file_exists=self.check_lock_file(),
        )

    def check_lock_file(self) -> bool:
        """检查lock文件是否存在

        白皮书依据: 第七章 6.4 末日风控 - lock文件检测

        Returns:
            lock文件是否存在
        """
        return self.lock_file.exists()

    def get_daily_pnl_percentage(self) -> float:
        """获取当日盈亏百分比

        白皮书依据: 第七章 6.4 末日风控 - 日亏损计算

        Returns:
            当日盈亏百分比（正数为盈利，负数为亏损）
        """
        # 使用模拟数据（测试用）
        if self._mock_daily_pnl is not None and self._mock_total_assets is not None:
            if self._mock_total_assets == 0:
                return 0.0
            return (self._mock_daily_pnl / self._mock_total_assets) * 100

        # 使用数据提供者
        if self.portfolio_provider is not None:
            daily_pnl = self.portfolio_provider.get_daily_pnl()
            total_assets = self.portfolio_provider.get_total_assets()
            if total_assets == 0:
                return 0.0
            return (daily_pnl / total_assets) * 100

        return 0.0

    def get_consecutive_loss_percentage(self, days: Optional[int] = None) -> float:
        """获取连续N日亏损百分比

        白皮书依据: 第七章 6.4 末日风控 - 连续亏损计算

        Args:
            days: 天数，默认使用consecutive_days

        Returns:
            连续N日累计亏损百分比（正数为盈利，负数为亏损）
        """
        if days is None:
            days = self.consecutive_days

        # 使用模拟数据（测试用）
        if self._mock_historical_pnl is not None and self._mock_total_assets is not None:
            if self._mock_total_assets == 0:
                return 0.0
            pnl_list = self._mock_historical_pnl[:days]
            total_pnl = sum(pnl_list)
            return (total_pnl / self._mock_total_assets) * 100

        # 使用数据提供者
        if self.portfolio_provider is not None:
            pnl_list = self.portfolio_provider.get_historical_pnl(days)
            total_assets = self.portfolio_provider.get_total_assets()
            if total_assets == 0:
                return 0.0
            total_pnl = sum(pnl_list)
            return (total_pnl / total_assets) * 100

        return 0.0

    def get_margin_risk_ratio(self) -> float:
        """获取保证金风险度

        白皮书依据: 第七章 6.4 末日风控 - 保证金风险计算

        风险度 = 已用保证金 / (已用保证金 + 可用保证金) * 100

        Returns:
            保证金风险度百分比
        """
        # 使用模拟数据（测试用）
        if self._mock_margin_used is not None and self._mock_margin_available is not None:
            total_margin = self._mock_margin_used + self._mock_margin_available
            if total_margin == 0:
                return 0.0
            return (self._mock_margin_used / total_margin) * 100

        # 使用数据提供者
        if self.portfolio_provider is not None:
            margin_used = self.portfolio_provider.get_margin_used()
            margin_available = self.portfolio_provider.get_margin_available()
            total_margin = margin_used + margin_available
            if total_margin == 0:
                return 0.0
            return (margin_used / total_margin) * 100

        return 0.0

    async def check_doomsday_conditions(self) -> Optional[DoomsdayEvent]:
        """检查末日条件

        白皮书依据: 第七章 6.4 末日风控

        检查项：
        - lock文件存在
        - 单日亏损 > 10%
        - 连续3日亏损 > 20%
        - 保证金风险度 > 95%

        Returns:
            如果触发末日条件，返回DoomsdayEvent；否则返回None

        Raises:
            DoomsdayAlreadyTriggeredError: 末日开关已触发
        """
        if self._is_triggered:
            raise DoomsdayAlreadyTriggeredError("末日开关已触发，无法再次检查")

        # 检查lock文件
        if self.check_lock_file():
            event = await self.trigger_doomsday(
                reason="检测到末日开关文件",
                trigger_type=DoomsdayTriggerType.LOCK_FILE,
                trigger_value=1.0,
                threshold=0.0,
            )
            return event

        # 检查单日亏损
        daily_pnl = self.get_daily_pnl_percentage()
        if daily_pnl < -self.daily_loss_threshold:
            event = await self.trigger_doomsday(
                reason=f"单日亏损{abs(daily_pnl):.2f}%超过阈值{self.daily_loss_threshold}%",
                trigger_type=DoomsdayTriggerType.DAILY_LOSS,
                trigger_value=daily_pnl,
                threshold=-self.daily_loss_threshold,
            )
            return event

        # 检查连续亏损
        consecutive_loss = self.get_consecutive_loss_percentage()
        if consecutive_loss < -self.consecutive_loss_threshold:
            event = await self.trigger_doomsday(
                reason=f"连续{self.consecutive_days}日亏损{abs(consecutive_loss):.2f}%超过阈值{self.consecutive_loss_threshold}%",  # pylint: disable=line-too-long
                trigger_type=DoomsdayTriggerType.CONSECUTIVE_LOSS,
                trigger_value=consecutive_loss,
                threshold=-self.consecutive_loss_threshold,
            )
            return event

        # 检查保证金风险
        margin_risk = self.get_margin_risk_ratio()
        if margin_risk > self.margin_risk_threshold:
            event = await self.trigger_doomsday(
                reason=f"保证金风险度{margin_risk:.2f}%超过阈值{self.margin_risk_threshold}%",
                trigger_type=DoomsdayTriggerType.MARGIN_RISK,
                trigger_value=margin_risk,
                threshold=self.margin_risk_threshold,
            )
            return event

        logger.debug(
            f"末日条件检查通过: "
            f"daily_pnl={daily_pnl:.2f}%, "
            f"consecutive_loss={consecutive_loss:.2f}%, "
            f"margin_risk={margin_risk:.2f}%"
        )

        return None

    async def trigger_doomsday(
        self,
        reason: str,
        trigger_type: DoomsdayTriggerType = DoomsdayTriggerType.MANUAL,
        trigger_value: float = 0.0,
        threshold: float = 0.0,
    ) -> DoomsdayEvent:
        """触发末日开关

        白皮书依据: 第七章 6.4 末日风控

        执行紧急停止流程：
        1. 创建lock文件
        2. 取消所有订单
        3. 平掉所有仓位
        4. 发送告警通知
        5. 记录审计日志

        Args:
            reason: 触发原因
            trigger_type: 触发类型
            trigger_value: 触发值
            threshold: 阈值

        Returns:
            末日事件

        Raises:
            DoomsdayAlreadyTriggeredError: 末日开关已触发
        """
        if self._is_triggered:
            raise DoomsdayAlreadyTriggeredError("末日开关已触发，无法再次触发")

        timestamp = datetime.now().isoformat()
        actions_taken: List[str] = []

        logger.critical(f"触发末日开关: {reason}")

        # 1. 创建lock文件
        try:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            self.lock_file.write_text(  # pylint: disable=w1514
                json.dumps(
                    {
                        "timestamp": timestamp,
                        "reason": reason,
                        "trigger_type": trigger_type.value,
                    },
                    ensure_ascii=False,
                )
            )
            actions_taken.append("创建lock文件")
            logger.info(f"创建末日lock文件: {self.lock_file}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"创建lock文件失败: {e}")

        # 2. 取消所有订单
        if self.trading_engine is not None:
            try:
                cancelled_count = await self.trading_engine.cancel_all_orders()
                actions_taken.append(f"取消{cancelled_count}个订单")
                logger.info(f"取消所有订单: {cancelled_count}个")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"取消订单失败: {e}")

        # 3. 平掉所有仓位
        if self.trading_engine is not None:
            try:
                closed_count = await self.trading_engine.close_all_positions()
                actions_taken.append(f"平掉{closed_count}个仓位")
                logger.info(f"平掉所有仓位: {closed_count}个")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"平仓失败: {e}")

        # 4. 紧急停止交易引擎
        if self.trading_engine is not None:
            try:
                await self.trading_engine.emergency_stop()
                actions_taken.append("紧急停止交易引擎")
                logger.info("交易引擎已紧急停止")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"紧急停止失败: {e}")

        # 5. 发送告警通知
        if self.notification_manager is not None:
            try:
                await self.notification_manager.send_alert(
                    title="🚨 末日风控触发",
                    message=f"触发原因: {reason}\n触发时间: {timestamp}",
                    level="critical",
                )
                actions_taken.append("发送告警通知")
                logger.info("告警通知已发送")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"发送通知失败: {e}")

        # 6. 记录审计日志
        if self.audit_logger is not None:
            try:
                self.audit_logger.log_event(
                    {
                        "event_type": "DOOMSDAY_TRIGGERED",
                        "timestamp": timestamp,
                        "reason": reason,
                        "trigger_type": trigger_type.value,
                        "trigger_value": trigger_value,
                        "threshold": threshold,
                        "actions_taken": actions_taken,
                    }
                )
                actions_taken.append("记录审计日志")
                logger.info("审计日志已记录")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"记录审计日志失败: {e}")

        # 更新内部状态
        self._is_triggered = True
        self._trigger_time = timestamp
        self._trigger_type = trigger_type
        self._trigger_reason = reason

        # 创建事件
        event = DoomsdayEvent(
            timestamp=timestamp,
            trigger_type=trigger_type,
            reason=reason,
            trigger_value=trigger_value,
            threshold=threshold,
            actions_taken=actions_taken,
        )
        self._events.append(event)

        # 调用回调
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"回调执行失败: {e}")

        return event

    def reset(self) -> None:
        """重置末日状态

        注意：此方法仅用于测试或手动恢复，生产环境需要人工确认

        Raises:
            DoomsdayError: 如果lock文件仍然存在
        """
        if self.check_lock_file():
            raise DoomsdayError("lock文件仍然存在，请先删除lock文件再重置")

        self._is_triggered = False
        self._trigger_time = None
        self._trigger_type = None
        self._trigger_reason = None

        logger.info("末日状态已重置")

    def delete_lock_file(self) -> bool:
        """删除lock文件

        Returns:
            是否成功删除
        """
        if self.lock_file.exists():
            try:
                self.lock_file.unlink()
                logger.info(f"删除末日lock文件: {self.lock_file}")
                return True
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"删除lock文件失败: {e}")
                return False
        return False

    def register_callback(self, callback: Callable[[DoomsdayEvent], None]) -> None:
        """注册末日事件回调

        Args:
            callback: 回调函数
        """
        self._callbacks.append(callback)

    def get_events(self) -> List[DoomsdayEvent]:
        """获取所有末日事件

        Returns:
            末日事件列表
        """
        return self._events.copy()

    def set_mock_data(  # pylint: disable=too-many-positional-arguments
        self,
        daily_pnl: Optional[float] = None,
        total_assets: Optional[float] = None,
        historical_pnl: Optional[List[float]] = None,
        margin_used: Optional[float] = None,
        margin_available: Optional[float] = None,
    ) -> None:
        """设置模拟数据（测试用）

        Args:
            daily_pnl: 当日盈亏金额
            total_assets: 总资产
            historical_pnl: 历史盈亏列表
            margin_used: 已用保证金
            margin_available: 可用保证金
        """
        self._mock_daily_pnl = daily_pnl
        self._mock_total_assets = total_assets
        self._mock_historical_pnl = historical_pnl
        self._mock_margin_used = margin_used
        self._mock_margin_available = margin_available

    def clear_mock_data(self) -> None:
        """清除模拟数据"""
        self._mock_daily_pnl = None
        self._mock_total_assets = None
        self._mock_historical_pnl = None
        self._mock_margin_used = None
        self._mock_margin_available = None
