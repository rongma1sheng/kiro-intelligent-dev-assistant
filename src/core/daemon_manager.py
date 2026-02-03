"""守护进程管理系统

白皮书依据: 第十章 10.3 守护进程管理
"""

import signal
import threading
import time
from typing import Optional

from loguru import logger

from src.core.fund_monitor import AlertLevel, FundMonitor
from src.core.health_checker import HealthChecker, OverallStatus


class DaemonManager:
    """守护进程管理器

    白皮书依据: 第十章 10.3 守护进程管理

    管理健康检查和资金监控的守护线程，实现7×24无人值守运行。
    - 健康检查线程：每30秒执行一次
    - 资金监控线程：每60秒执行一次
    - 优雅关闭：响应SIGINT和SIGTERM信号

    Attributes:
        health_checker: 健康检查器实例
        fund_monitor: 资金监控器实例
        health_check_interval: 健康检查间隔（秒），默认30秒
        fund_monitor_interval: 资金监控间隔（秒），默认60秒
    """

    def __init__(
        self,
        health_checker: HealthChecker,
        fund_monitor: FundMonitor,
        health_check_interval: int = 30,
        fund_monitor_interval: int = 60,
    ):
        """初始化守护进程管理器

        白皮书依据: 第十章 10.3 守护进程管理

        Args:
            health_checker: 健康检查器实例
            fund_monitor: 资金监控器实例
            health_check_interval: 健康检查间隔（秒），默认30秒
            fund_monitor_interval: 资金监控间隔（秒），默认60秒

        Raises:
            ValueError: 当参数不在有效范围时
            TypeError: 当参数类型不正确时
        """
        if not isinstance(health_checker, HealthChecker):
            raise TypeError(f"health_checker必须是HealthChecker实例，" f"当前类型: {type(health_checker)}")

        if not isinstance(fund_monitor, FundMonitor):
            raise TypeError(f"fund_monitor必须是FundMonitor实例，" f"当前类型: {type(fund_monitor)}")

        if health_check_interval <= 0:
            raise ValueError(f"健康检查间隔必须 > 0，当前: {health_check_interval}")

        if fund_monitor_interval <= 0:
            raise ValueError(f"资金监控间隔必须 > 0，当前: {fund_monitor_interval}")

        self.health_checker = health_checker
        self.fund_monitor = fund_monitor
        self.health_check_interval = health_check_interval
        self.fund_monitor_interval = fund_monitor_interval

        # 线程控制
        self._running = False
        self._health_check_thread: Optional[threading.Thread] = None
        self._fund_monitor_thread: Optional[threading.Thread] = None

        # 用于测试的回调函数
        self._get_current_equity_callback: Optional[callable] = None

        logger.info(
            f"初始化DaemonManager: "
            f"health_check_interval={health_check_interval}s, "
            f"fund_monitor_interval={fund_monitor_interval}s"
        )

    def start(self) -> None:
        """启动守护进程

        白皮书依据: 第十章 10.3 守护进程管理

        启动健康检查和资金监控线程，并注册信号处理器。

        Raises:
            RuntimeError: 当守护进程已经在运行时
        """
        if self._running:
            raise RuntimeError("守护进程已经在运行")

        logger.info("启动守护进程...")

        self._running = True

        # 启动健康检查线程
        self._health_check_thread = threading.Thread(
            target=self.health_check_loop, name="HealthCheckThread", daemon=True
        )
        self._health_check_thread.start()
        logger.info("健康检查线程已启动")

        # 启动资金监控线程
        self._fund_monitor_thread = threading.Thread(
            target=self.fund_monitor_loop, name="FundMonitorThread", daemon=True
        )
        self._fund_monitor_thread.start()
        logger.info("资金监控线程已启动")

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        logger.info("信号处理器已注册（SIGINT, SIGTERM）")

        logger.info("守护进程启动完成")

    def health_check_loop(self) -> None:
        """健康检查循环（每30秒执行一次）

        白皮书依据: 第十章 10.3 守护进程管理

        持续执行健康检查，直到收到停止信号。
        当检测到Redis故障时，自动尝试恢复。
        """
        logger.info(f"健康检查循环开始，间隔{self.health_check_interval}秒")

        while self._running:
            try:
                # 执行健康检查
                result = self.health_checker.run_health_check()

                # 检查Redis状态，如果不健康则尝试恢复
                redis_health = result.components.get("redis")
                if redis_health and redis_health.status.value == "unhealthy":
                    logger.warning("检测到Redis不健康，尝试自动恢复...")
                    recovery_success = self.health_checker.attempt_redis_recovery()

                    if recovery_success:
                        logger.info("Redis自动恢复成功")
                    else:
                        logger.error("Redis自动恢复失败")

                # 检查整体状态
                if result.overall_status == OverallStatus.CRITICAL:
                    logger.critical(f"系统状态严重: {result.overall_status.value}")
                elif result.overall_status == OverallStatus.DEGRADED:
                    logger.warning(f"系统状态降级: {result.overall_status.value}")
                else:
                    logger.info(f"系统状态正常: {result.overall_status.value}")

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"健康检查循环异常: {e}", exc_info=True)

            # 等待下一次检查
            time.sleep(self.health_check_interval)

        logger.info("健康检查循环已停止")

    def fund_monitor_loop(self) -> None:
        """资金监控循环（每60秒执行一次）

        白皮书依据: 第十章 10.3 守护进程管理

        持续监控账户资金状态，直到收到停止信号。
        当检测到严重亏损时，触发紧急告警和锁定。
        """
        logger.info(f"资金监控循环开始，间隔{self.fund_monitor_interval}秒")

        while self._running:
            try:
                # 获取当前权益
                current_equity = self._get_current_equity()

                if current_equity is not None:
                    # 检查资金状态
                    status = self.fund_monitor.check_fund_status(current_equity)

                    # 根据告警级别记录日志
                    if status.alert_level == AlertLevel.CRITICAL:
                        logger.critical(
                            f"资金状态严重: "
                            f"权益={status.current_equity:.2f}, "
                            f"盈亏={status.daily_pnl_pct:+.2f}%, "
                            f"回撤={status.drawdown:.2f}%"
                        )
                    elif status.alert_level == AlertLevel.DANGER:
                        logger.error(
                            f"资金状态危险: "
                            f"权益={status.current_equity:.2f}, "
                            f"盈亏={status.daily_pnl_pct:+.2f}%, "
                            f"回撤={status.drawdown:.2f}%"
                        )
                    elif status.alert_level == AlertLevel.WARNING:
                        logger.warning(
                            f"资金状态警告: "
                            f"权益={status.current_equity:.2f}, "
                            f"盈亏={status.daily_pnl_pct:+.2f}%, "
                            f"回撤={status.drawdown:.2f}%"
                        )
                    else:
                        logger.info(
                            f"资金状态正常: "
                            f"权益={status.current_equity:.2f}, "
                            f"盈亏={status.daily_pnl_pct:+.2f}%, "
                            f"回撤={status.drawdown:.2f}%"
                        )
                else:
                    logger.warning("无法获取当前权益，跳过本次资金监控")

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"资金监控循环异常: {e}", exc_info=True)

            # 等待下一次检查
            time.sleep(self.fund_monitor_interval)

        logger.info("资金监控循环已停止")

    def graceful_shutdown(self) -> None:
        """优雅关闭守护进程

        白皮书依据: 第十章 10.3 守护进程管理

        停止所有守护线程，等待线程完成当前任务后退出。
        """
        if not self._running:
            logger.warning("守护进程未运行，无需关闭")
            return

        logger.info("开始优雅关闭守护进程...")

        # 设置停止标志
        self._running = False

        # 等待健康检查线程结束
        if self._health_check_thread and self._health_check_thread.is_alive():
            logger.info("等待健康检查线程结束...")
            self._health_check_thread.join(timeout=5)

            if self._health_check_thread.is_alive():
                logger.warning("健康检查线程未在超时时间内结束")
            else:
                logger.info("健康检查线程已结束")

        # 等待资金监控线程结束
        if self._fund_monitor_thread and self._fund_monitor_thread.is_alive():
            logger.info("等待资金监控线程结束...")
            self._fund_monitor_thread.join(timeout=5)

            if self._fund_monitor_thread.is_alive():
                logger.warning("资金监控线程未在超时时间内结束")
            else:
                logger.info("资金监控线程已结束")

        logger.info("守护进程已优雅关闭")

    def set_get_current_equity_callback(self, callback: callable) -> None:
        """设置获取当前权益的回调函数（用于测试）

        Args:
            callback: 返回当前权益的回调函数
        """
        self._get_current_equity_callback = callback

    def _get_current_equity(self) -> Optional[float]:
        """获取当前权益

        Returns:
            float: 当前权益，如果无法获取则返回None
        """
        # 如果设置了回调函数（测试模式），使用回调函数
        if self._get_current_equity_callback:
            try:
                return self._get_current_equity_callback()
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"回调函数获取权益失败: {e}", exc_info=True)
                return None

        # 实际实现中，这里会调用交易系统获取当前权益
        # 例如：return self.trading_system.get_current_equity()

        # 默认返回初始权益（用于演示）
        return self.fund_monitor.initial_equity

    def _signal_handler(self, signum: int, frame) -> None:  # pylint: disable=unused-argument
        """信号处理器

        处理SIGINT（Ctrl+C）和SIGTERM信号，触发优雅关闭。

        Args:
            signum: 信号编号
            frame: 当前栈帧
        """
        signal_name = signal.Signals(signum).name
        logger.info(f"收到信号 {signal_name}，开始优雅关闭...")
        self.graceful_shutdown()
