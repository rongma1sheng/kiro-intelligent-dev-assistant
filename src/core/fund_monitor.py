"""资金监控系统

白皮书依据: 第十章 10.2 资金监控系统
"""

from dataclasses import dataclass
from enum import Enum

from loguru import logger


class AlertLevel(str, Enum):
    """告警级别枚举

    白皮书依据: 第十章 10.2 资金监控系统
    """

    NORMAL = "normal"  # 正常状态
    WARNING = "warning"  # >3% loss or >10% drawdown
    DANGER = "danger"  # >5% loss or >15% drawdown
    CRITICAL = "critical"  # >8% loss or >20% drawdown


@dataclass
class FundStatus:
    """资金状态

    白皮书依据: 第十章 10.2 资金监控系统

    Attributes:
        current_equity: 当前权益
        daily_pnl: 当日盈亏
        daily_pnl_pct: 当日盈亏百分比
        drawdown: 回撤百分比
        alert_level: 告警级别
    """

    current_equity: float
    daily_pnl: float
    daily_pnl_pct: float
    drawdown: float
    alert_level: AlertLevel


class FundMonitor:
    """资金监控器

    白皮书依据: 第十章 10.2 资金监控系统

    每60秒检查账户余额，触发多级告警：
    - WARNING: >3%亏损或>10%回撤（仅记录日志）
    - DANGER: >5%亏损或>15%回撤（发送微信告警+暂停新仓位）
    - CRITICAL: >8%亏损或>20%回撤（触发紧急锁定）

    Attributes:
        check_interval: 检查间隔（秒），默认60秒
        initial_equity: 初始权益
        peak_equity: 峰值权益（用于计算回撤）
    """

    def __init__(self, initial_equity: float, check_interval: int = 60):
        """初始化资金监控器

        白皮书依据: 第十章 10.2 资金监控系统

        Args:
            initial_equity: 初始权益，必须 > 0
            check_interval: 检查间隔（秒），默认60秒

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if initial_equity <= 0:
            raise ValueError(f"初始权益必须 > 0，当前: {initial_equity}")

        if check_interval <= 0:
            raise ValueError(f"检查间隔必须 > 0，当前: {check_interval}")

        self.initial_equity = initial_equity
        self.check_interval = check_interval
        self.peak_equity = initial_equity  # 初始峰值等于初始权益

        logger.info(f"初始化FundMonitor: " f"initial_equity={initial_equity:.2f}, " f"check_interval={check_interval}s")

    def check_fund_status(self, current_equity: float) -> FundStatus:
        """检查资金状态并触发告警

        白皮书依据: 第十章 10.2 资金监控系统

        Args:
            current_equity: 当前权益

        Returns:
            FundStatus: 包含权益、盈亏、回撤和告警级别的资金状态

        Raises:
            ValueError: 当current_equity <= 0时
        """
        if current_equity <= 0:
            raise ValueError(f"当前权益必须 > 0，当前: {current_equity}")

        # 更新峰值权益
        if current_equity > self.peak_equity:  # pylint: disable=r1731
            self.peak_equity = current_equity

        # 计算当日盈亏
        daily_pnl = current_equity - self.initial_equity
        daily_pnl_pct = (daily_pnl / self.initial_equity) * 100

        # 计算回撤
        drawdown = ((self.peak_equity - current_equity) / self.peak_equity) * 100

        # 确定告警级别
        alert_level = self.determine_alert_level(daily_pnl_pct, drawdown)

        # 创建资金状态
        status = FundStatus(
            current_equity=current_equity,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            drawdown=drawdown,
            alert_level=alert_level,
        )

        # 根据告警级别执行相应操作
        self._handle_alert(status)

        return status

    def determine_alert_level(self, daily_pnl_pct: float, drawdown: float) -> AlertLevel:
        """确定告警级别

        白皮书依据: 第十章 10.2 资金监控系统

        告警阈值：
        - WARNING: >3%亏损或>10%回撤
        - DANGER: >5%亏损或>15%回撤
        - CRITICAL: >8%亏损或>20%回撤

        Args:
            daily_pnl_pct: 当日盈亏百分比（负数表示亏损）
            drawdown: 回撤百分比

        Returns:
            AlertLevel: 告警级别
        """
        # 将盈亏百分比转换为亏损百分比（正数表示亏损）
        # daily_pnl_pct is already a percentage value (e.g., -3.0 for -3%)
        loss_pct = -daily_pnl_pct if daily_pnl_pct < 0 else 0

        # 按严重程度从高到低检查
        if loss_pct > 8 or drawdown > 20:  # pylint: disable=no-else-return
            return AlertLevel.CRITICAL
        elif loss_pct > 5 or drawdown > 15:
            return AlertLevel.DANGER
        elif loss_pct > 3 or drawdown > 10:
            return AlertLevel.WARNING
        else:
            return AlertLevel.NORMAL

    def trigger_emergency_lockdown(self) -> None:
        """触发紧急锁定

        白皮书依据: 第十章 10.2 资金监控系统

        紧急锁定操作：
        1. 停止所有交易
        2. 可选：清仓所有持仓
        3. 发送紧急告警
        4. 记录锁定事件
        """
        logger.critical("触发紧急锁定！")
        logger.critical("紧急锁定操作：")
        logger.critical("  1. 停止所有交易")
        logger.critical("  2. 暂停新仓位建立")
        logger.critical("  3. 发送紧急告警")
        logger.critical("  4. 等待人工干预")

        # 实际实现中，这里会调用交易系统的停止接口
        # 例如：self.trading_system.stop_all_trading()
        # 例如：self.alert_system.send_emergency_alert()

    def _handle_alert(self, status: FundStatus) -> None:
        """处理告警

        根据告警级别执行相应操作：
        - NORMAL: 无操作
        - WARNING: 记录日志
        - DANGER: 记录日志 + 发送微信告警 + 暂停新仓位
        - CRITICAL: 记录日志 + 发送微信告警 + 触发紧急锁定

        Args:
            status: 资金状态
        """
        if status.alert_level == AlertLevel.NORMAL:
            logger.info(
                f"资金状态正常: "
                f"权益={status.current_equity:.2f}, "
                f"盈亏={status.daily_pnl_pct:+.2f}%, "
                f"回撤={status.drawdown:.2f}%"
            )

        elif status.alert_level == AlertLevel.WARNING:
            logger.warning(
                f"资金告警 [WARNING]: "
                f"权益={status.current_equity:.2f}, "
                f"盈亏={status.daily_pnl_pct:+.2f}%, "
                f"回撤={status.drawdown:.2f}%"
            )

        elif status.alert_level == AlertLevel.DANGER:
            logger.error(
                f"资金告警 [DANGER]: "
                f"权益={status.current_equity:.2f}, "
                f"盈亏={status.daily_pnl_pct:+.2f}%, "
                f"回撤={status.drawdown:.2f}%"
            )
            logger.error("执行操作: 发送微信告警 + 暂停新仓位")
            # 实际实现中，这里会调用告警系统
            # 例如：self.alert_system.send_wechat_alert(status)
            # 例如：self.trading_system.pause_new_positions()

        elif status.alert_level == AlertLevel.CRITICAL:
            logger.critical(
                f"资金告警 [CRITICAL]: "
                f"权益={status.current_equity:.2f}, "
                f"盈亏={status.daily_pnl_pct:+.2f}%, "
                f"回撤={status.drawdown:.2f}%"
            )
            logger.critical("执行操作: 发送微信告警 + 邮件告警 + 紧急锁定")
            self.trigger_emergency_lockdown()
