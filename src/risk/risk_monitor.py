"""
风控监控器 (Risk Monitor)

白皮书依据: 第一章 1.5.2 战争态任务调度
- 实时仓位监控
- 止损止盈检查
- 末日开关监控

功能:
- 实时监控持仓风险
- 自动触发止损止盈
- 监控末日开关条件
"""

import threading
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class RiskLevel(Enum):
    """风险等级"""

    SAFE = "安全"  # 风险可控
    WARNING = "警告"  # 需要关注
    DANGER = "危险"  # 需要干预
    CRITICAL = "紧急"  # 立即处理
    DOOMSDAY = "末日"  # 触发末日开关


class AlertType(Enum):
    """告警类型"""

    POSITION_LIMIT = "仓位超限"
    STOP_LOSS = "止损触发"
    TAKE_PROFIT = "止盈触发"
    DAILY_LOSS = "日亏损超限"
    DRAWDOWN = "回撤超限"
    CONCENTRATION = "集中度超限"
    DOOMSDAY = "末日开关"


@dataclass
class RiskAlert:
    """风险告警

    Attributes:
        alert_type: 告警类型
        level: 风险等级
        message: 告警消息
        symbol: 相关标的
        value: 触发值
        threshold: 阈值
        timestamp: 时间戳
    """

    alert_type: AlertType
    level: RiskLevel
    message: str
    symbol: Optional[str] = None
    value: float = 0.0
    threshold: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "alert_type": self.alert_type.value,
            "level": self.level.value,
            "message": self.message,
            "symbol": self.symbol,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Position:
    """持仓信息

    Attributes:
        symbol: 标的代码
        quantity: 持仓数量
        cost_price: 成本价
        current_price: 当前价
        market_value: 市值
        pnl: 盈亏
        pnl_ratio: 盈亏比例
    """

    symbol: str
    quantity: int
    cost_price: float
    current_price: float = 0.0
    market_value: float = 0.0
    pnl: float = 0.0
    pnl_ratio: float = 0.0

    def update_price(self, price: float) -> None:
        """更新价格"""
        self.current_price = price
        self.market_value = self.quantity * price
        self.pnl = self.market_value - self.quantity * self.cost_price
        if self.cost_price > 0:
            self.pnl_ratio = self.pnl / (self.quantity * self.cost_price)


@dataclass
class RiskConfig:
    """风控配置

    Attributes:
        max_position_ratio: 单只股票最大仓位比例
        max_daily_loss_ratio: 单日最大亏损比例
        max_drawdown_ratio: 最大回撤比例
        stop_loss_ratio: 止损比例
        take_profit_ratio: 止盈比例
        max_concentration: 最大集中度
        doomsday_loss_ratio: 末日开关触发亏损比例
    """

    max_position_ratio: float = 0.20  # 单只最大20%
    max_daily_loss_ratio: float = 0.05  # 单日最大亏损5%
    max_drawdown_ratio: float = 0.10  # 最大回撤10%
    stop_loss_ratio: float = 0.08  # 止损8%
    take_profit_ratio: float = 0.20  # 止盈20%
    max_concentration: float = 0.30  # 最大集中度30%
    doomsday_loss_ratio: float = 0.10  # 末日开关10%
    check_interval: float = 1.0  # 检查间隔(秒)


class RiskMonitor:  # pylint: disable=too-many-instance-attributes
    """风控监控器

    白皮书依据: 第一章 1.5.2 战争态任务调度

    负责实时监控持仓风险，自动触发止损止盈，监控末日开关条件。

    Attributes:
        config: 风控配置
        positions: 持仓字典
        total_capital: 总资金
        daily_pnl: 当日盈亏
        alerts: 告警列表
        on_alert: 告警回调
        on_stop_loss: 止损回调
        on_take_profit: 止盈回调
        on_doomsday: 末日开关回调

    Example:
        >>> monitor = RiskMonitor(total_capital=1000000)
        >>> monitor.on_alert = lambda alert: print(alert.message)
        >>> monitor.start()
    """

    def __init__(
        self,
        total_capital: float = 1000000.0,
        config: Optional[RiskConfig] = None,
        doomsday_lock_path: str = "DOOMSDAY_SWITCH.lock",
    ):
        """初始化风控监控器

        Args:
            total_capital: 总资金
            config: 风控配置
            doomsday_lock_path: 末日开关锁文件路径

        Raises:
            ValueError: 当参数无效时
        """
        if total_capital <= 0:
            raise ValueError(f"总资金必须 > 0，当前: {total_capital}")

        self.total_capital = total_capital
        self.config = config or RiskConfig()
        self.doomsday_lock_path = Path(doomsday_lock_path)

        self.positions: Dict[str, Position] = {}
        self.daily_pnl: float = 0.0
        self.peak_capital: float = total_capital
        self.alerts: List[RiskAlert] = []
        self.today: date = date.today()

        # 回调函数
        self.on_alert: Optional[Callable[[RiskAlert], None]] = None
        self.on_stop_loss: Optional[Callable[[str, float], None]] = None
        self.on_take_profit: Optional[Callable[[str, float], None]] = None
        self.on_doomsday: Optional[Callable[[str], None]] = None

        self._is_running = False
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._doomsday_triggered = False

        logger.info(
            f"风控监控器初始化: "
            f"总资金={total_capital:,.0f}, "
            f"止损={self.config.stop_loss_ratio:.1%}, "
            f"止盈={self.config.take_profit_ratio:.1%}"
        )

    def start(self) -> bool:
        """启动风控监控

        Returns:
            启动是否成功
        """
        if self._is_running:
            logger.warning("风控监控器已在运行")
            return True

        try:
            self._is_running = True
            self._stop_event.clear()

            self._monitor_thread = threading.Thread(target=self._monitor_loop, name="RiskMonitorThread", daemon=True)
            self._monitor_thread.start()

            logger.info("风控监控器已启动")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            self._is_running = False
            logger.error(f"启动风控监控器失败: {e}")
            return False

    def stop(self) -> bool:
        """停止风控监控

        Returns:
            停止是否成功
        """
        if not self._is_running:
            return True

        try:
            self._stop_event.set()

            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=5)

            self._is_running = False
            logger.info("风控监控器已停止")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"停止风控监控器失败: {e}")
            return False

    def _monitor_loop(self) -> None:
        """监控循环"""
        while not self._stop_event.is_set():
            try:
                self._check_risks()
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"风控检查失败: {e}")

            self._stop_event.wait(self.config.check_interval)

    def _check_risks(self) -> None:
        """检查所有风险"""
        with self._lock:
            # 检查日期变化，重置日盈亏
            if date.today() != self.today:
                self.today = date.today()
                self.daily_pnl = 0.0
                logger.info("新交易日，重置日盈亏")

            # 1. 检查末日开关文件
            self._check_doomsday_file()

            # 2. 检查日亏损
            self._check_daily_loss()

            # 3. 检查回撤
            self._check_drawdown()

            # 4. 检查各持仓
            for symbol, position in self.positions.items():  # pylint: disable=unused-variable
                self._check_position(position)

    def _check_doomsday_file(self) -> None:
        """检查末日开关文件"""
        if self.doomsday_lock_path.exists() and not self._doomsday_triggered:
            self._trigger_doomsday("检测到末日开关锁文件")

    def _check_daily_loss(self) -> None:
        """检查日亏损"""
        if self.total_capital <= 0:
            return

        daily_loss_ratio = -self.daily_pnl / self.total_capital

        if daily_loss_ratio >= self.config.doomsday_loss_ratio:
            self._trigger_doomsday(
                f"单日亏损超过{self.config.doomsday_loss_ratio:.1%}，" f"当前亏损{daily_loss_ratio:.2%}"
            )
        elif daily_loss_ratio >= self.config.max_daily_loss_ratio:
            self._create_alert(
                AlertType.DAILY_LOSS,
                RiskLevel.DANGER,
                f"单日亏损{daily_loss_ratio:.2%}，超过阈值{self.config.max_daily_loss_ratio:.1%}",
                value=daily_loss_ratio,
                threshold=self.config.max_daily_loss_ratio,
            )

    def _check_drawdown(self) -> None:
        """检查回撤"""
        current_capital = self.total_capital + self.daily_pnl

        # 更新峰值
        if current_capital > self.peak_capital:  # pylint: disable=r1731
            self.peak_capital = current_capital

        # 计算回撤
        if self.peak_capital > 0:
            drawdown = (self.peak_capital - current_capital) / self.peak_capital

            if drawdown >= self.config.max_drawdown_ratio:
                self._create_alert(
                    AlertType.DRAWDOWN,
                    RiskLevel.DANGER,
                    f"回撤{drawdown:.2%}，超过阈值{self.config.max_drawdown_ratio:.1%}",
                    value=drawdown,
                    threshold=self.config.max_drawdown_ratio,
                )

    def _check_position(self, position: Position) -> None:
        """检查单个持仓"""
        # 1. 检查仓位比例
        if self.total_capital > 0:
            position_ratio = position.market_value / self.total_capital
            if position_ratio > self.config.max_position_ratio:
                self._create_alert(
                    AlertType.POSITION_LIMIT,
                    RiskLevel.WARNING,
                    f"{position.symbol}仓位{position_ratio:.1%}，" f"超过阈值{self.config.max_position_ratio:.1%}",
                    symbol=position.symbol,
                    value=position_ratio,
                    threshold=self.config.max_position_ratio,
                )

        # 2. 检查止损
        if position.pnl_ratio <= -self.config.stop_loss_ratio:
            self._create_alert(
                AlertType.STOP_LOSS,
                RiskLevel.DANGER,
                f"{position.symbol}亏损{position.pnl_ratio:.2%}，触发止损",
                symbol=position.symbol,
                value=position.pnl_ratio,
                threshold=-self.config.stop_loss_ratio,
            )

            if self.on_stop_loss:
                try:
                    self.on_stop_loss(position.symbol, position.pnl_ratio)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"止损回调失败: {e}")

        # 3. 检查止盈
        if position.pnl_ratio >= self.config.take_profit_ratio:
            self._create_alert(
                AlertType.TAKE_PROFIT,
                RiskLevel.WARNING,
                f"{position.symbol}盈利{position.pnl_ratio:.2%}，触发止盈",
                symbol=position.symbol,
                value=position.pnl_ratio,
                threshold=self.config.take_profit_ratio,
            )

            if self.on_take_profit:
                try:
                    self.on_take_profit(position.symbol, position.pnl_ratio)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"止盈回调失败: {e}")

    def _create_alert(  # pylint: disable=too-many-positional-arguments
        self,
        alert_type: AlertType,
        level: RiskLevel,
        message: str,
        symbol: Optional[str] = None,
        value: float = 0.0,
        threshold: float = 0.0,
    ) -> None:
        """创建告警"""
        alert = RiskAlert(
            alert_type=alert_type, level=level, message=message, symbol=symbol, value=value, threshold=threshold
        )

        self.alerts.append(alert)

        # 保留最近1000条告警
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-500:]

        logger.warning(f"[{level.value}] {message}")

        if self.on_alert:
            try:
                self.on_alert(alert)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"告警回调失败: {e}")

    def _trigger_doomsday(self, reason: str) -> None:
        """触发末日开关

        白皮书依据: 第六章 6.4 末日风控
        """
        if self._doomsday_triggered:
            return

        self._doomsday_triggered = True

        logger.critical(f"[末日开关] 触发原因: {reason}")

        # 创建锁文件
        try:
            self.doomsday_lock_path.write_text(
                f"DOOMSDAY TRIGGERED\n" f"Time: {datetime.now().isoformat()}\n" f"Reason: {reason}\n"
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"创建末日开关锁文件失败: {e}")

        # 创建告警
        self._create_alert(AlertType.DOOMSDAY, RiskLevel.DOOMSDAY, f"末日开关已触发: {reason}")

        # 触发回调
        if self.on_doomsday:
            try:
                self.on_doomsday(reason)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"末日开关回调失败: {e}")

    def update_position(self, symbol: str, quantity: int, cost_price: float, current_price: float) -> None:
        """更新持仓

        Args:
            symbol: 标的代码
            quantity: 持仓数量
            cost_price: 成本价
            current_price: 当前价
        """
        with self._lock:
            if quantity <= 0:
                # 清仓
                if symbol in self.positions:
                    del self.positions[symbol]
            else:
                if symbol in self.positions:
                    self.positions[symbol].quantity = quantity
                    self.positions[symbol].cost_price = cost_price
                    self.positions[symbol].update_price(current_price)
                else:
                    position = Position(symbol=symbol, quantity=quantity, cost_price=cost_price)
                    position.update_price(current_price)
                    self.positions[symbol] = position

    def update_price(self, symbol: str, price: float) -> None:
        """更新价格

        Args:
            symbol: 标的代码
            price: 当前价格
        """
        with self._lock:
            if symbol in self.positions:
                self.positions[symbol].update_price(price)

    def update_daily_pnl(self, pnl: float) -> None:
        """更新日盈亏

        Args:
            pnl: 日盈亏金额
        """
        with self._lock:
            self.daily_pnl = pnl

    def get_risk_level(self) -> RiskLevel:
        """获取当前风险等级

        Returns:
            当前风险等级
        """
        with self._lock:
            if self._doomsday_triggered:
                return RiskLevel.DOOMSDAY

            # 检查最近告警
            recent_alerts = [a for a in self.alerts if (datetime.now() - a.timestamp).total_seconds() < 300]

            if any(a.level == RiskLevel.CRITICAL for a in recent_alerts):  # pylint: disable=no-else-return
                return RiskLevel.CRITICAL
            elif any(a.level == RiskLevel.DANGER for a in recent_alerts):
                return RiskLevel.DANGER
            elif any(a.level == RiskLevel.WARNING for a in recent_alerts):
                return RiskLevel.WARNING

            return RiskLevel.SAFE

    def get_alerts(self, limit: int = 100) -> List[RiskAlert]:
        """获取最近告警

        Args:
            limit: 返回数量限制

        Returns:
            告警列表
        """
        with self._lock:
            return self.alerts[-limit:]

    def is_doomsday_triggered(self) -> bool:
        """检查末日开关是否已触发

        Returns:
            是否已触发
        """
        return self._doomsday_triggered

    def reset_doomsday(self, password: str = "") -> bool:  # pylint: disable=unused-argument
        """重置末日开关

        白皮书依据: 第十二章 12.3 末日开关与应急响应

        Args:
            password: 重置密码

        Returns:
            重置是否成功
        """
        # 简化实现，实际应该验证密码
        if not self._doomsday_triggered:
            return True

        try:
            if self.doomsday_lock_path.exists():
                self.doomsday_lock_path.unlink()

            self._doomsday_triggered = False
            logger.info("末日开关已重置")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"重置末日开关失败: {e}")
            return False

    def is_running(self) -> bool:
        """检查监控器是否运行中

        Returns:
            是否运行中
        """
        return self._is_running
