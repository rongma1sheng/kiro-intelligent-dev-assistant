"""DaemonManager单元测试

白皮书依据: 第十章 10.3 守护进程管理
"""

import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, patch, call

from src.core.daemon_manager import DaemonManager
from src.core.health_checker import (
    HealthChecker,
    HealthCheckResult,
    ComponentHealth,
    ComponentStatus,
    OverallStatus
)
from src.core.fund_monitor import (
    FundMonitor,
    FundStatus,
    AlertLevel
)


class TestDaemonManagerInitialization:
    """测试DaemonManager初始化"""
    
    def test_init_with_valid_parameters(self):
        """测试使用有效参数初始化"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            health_check_interval=30,
            fund_monitor_interval=60
        )
        
        assert daemon.health_checker is health_checker
        assert daemon.fund_monitor is fund_monitor
        assert daemon.health_check_interval == 30
        assert daemon.fund_monitor_interval == 60
        assert daemon._running is False
        assert daemon._health_check_thread is None
        assert daemon._fund_monitor_thread is None
    
    def test_init_with_custom_intervals(self):
        """测试使用自定义间隔初始化"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            health_check_interval=10,
            fund_monitor_interval=20
        )
        
        assert daemon.health_check_interval == 10
        assert daemon.fund_monitor_interval == 20
    
    def test_init_with_invalid_health_checker_type(self):
        """测试使用无效health_checker类型初始化"""
        fund_monitor = FundMonitor(initial_equity=100000.0)
        
        with pytest.raises(TypeError, match="health_checker必须是HealthChecker实例"):
            DaemonManager(
                health_checker="not_a_health_checker",
                fund_monitor=fund_monitor
            )
    
    def test_init_with_invalid_fund_monitor_type(self):
        """测试使用无效fund_monitor类型初始化"""
        health_checker = HealthChecker()
        
        with pytest.raises(TypeError, match="fund_monitor必须是FundMonitor实例"):
            DaemonManager(
                health_checker=health_checker,
                fund_monitor="not_a_fund_monitor"
            )
    
    def test_init_with_zero_health_check_interval(self):
        """测试使用零健康检查间隔初始化"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        
        with pytest.raises(ValueError, match="健康检查间隔必须 > 0"):
            DaemonManager(
                health_checker=health_checker,
                fund_monitor=fund_monitor,
                health_check_interval=0
            )
    
    def test_init_with_negative_health_check_interval(self):
        """测试使用负健康检查间隔初始化"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        
        with pytest.raises(ValueError, match="健康检查间隔必须 > 0"):
            DaemonManager(
                health_checker=health_checker,
                fund_monitor=fund_monitor,
                health_check_interval=-10
            )
    
    def test_init_with_zero_fund_monitor_interval(self):
        """测试使用零资金监控间隔初始化"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        
        with pytest.raises(ValueError, match="资金监控间隔必须 > 0"):
            DaemonManager(
                health_checker=health_checker,
                fund_monitor=fund_monitor,
                fund_monitor_interval=0
            )
    
    def test_init_with_negative_fund_monitor_interval(self):
        """测试使用负资金监控间隔初始化"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        
        with pytest.raises(ValueError, match="资金监控间隔必须 > 0"):
            DaemonManager(
                health_checker=health_checker,
                fund_monitor=fund_monitor,
                fund_monitor_interval=-20
            )


class TestDaemonManagerStart:
    """测试DaemonManager启动"""
    
    def test_start_creates_threads(self):
        """测试启动创建线程"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor
        )
        
        daemon.start()
        
        try:
            assert daemon._running is True
            assert daemon._health_check_thread is not None
            assert daemon._fund_monitor_thread is not None
            assert daemon._health_check_thread.is_alive()
            assert daemon._fund_monitor_thread.is_alive()
            assert daemon._health_check_thread.name == "HealthCheckThread"
            assert daemon._fund_monitor_thread.name == "FundMonitorThread"
        finally:
            daemon.graceful_shutdown()
    
    def test_start_when_already_running(self):
        """测试重复启动抛出异常"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor
        )
        
        daemon.start()
        
        try:
            with pytest.raises(RuntimeError, match="守护进程已经在运行"):
                daemon.start()
        finally:
            daemon.graceful_shutdown()
    
    @patch('signal.signal')
    def test_start_registers_signal_handlers(self, mock_signal):
        """测试启动注册信号处理器"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor
        )
        
        daemon.start()
        
        try:
            # 验证信号处理器已注册
            import signal
            calls = mock_signal.call_args_list
            signal_nums = [call[0][0] for call in calls]
            
            assert signal.SIGINT in signal_nums
            assert signal.SIGTERM in signal_nums
        finally:
            daemon.graceful_shutdown()


class TestDaemonManagerHealthCheckLoop:
    """测试健康检查循环"""
    
    def test_health_check_loop_executes_checks(self):
        """测试健康检查循环执行检查"""
        health_checker = Mock(spec=HealthChecker)
        fund_monitor = FundMonitor(initial_equity=100000.0)
        
        # 模拟健康检查结果
        mock_result = HealthCheckResult(
            overall_status=OverallStatus.HEALTHY,
            components={
                "redis": ComponentHealth(
                    status=ComponentStatus.HEALTHY,
                    message="Redis正常",
                    metrics={}
                )
            },
            timestamp=Mock()
        )
        health_checker.run_health_check.return_value = mock_result
        
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            health_check_interval=1  # 1秒间隔用于快速测试
        )
        
        daemon.start()
        
        try:
            # 等待至少执行一次检查
            time.sleep(1.5)
            
            # 验证健康检查被调用
            assert health_checker.run_health_check.call_count >= 1
        finally:
            daemon.graceful_shutdown()
    
    def test_health_check_loop_attempts_redis_recovery(self):
        """测试健康检查循环在Redis不健康时尝试恢复"""
        health_checker = Mock(spec=HealthChecker)
        fund_monitor = FundMonitor(initial_equity=100000.0)
        
        # 模拟Redis不健康的结果
        mock_result = HealthCheckResult(
            overall_status=OverallStatus.CRITICAL,
            components={
                "redis": ComponentHealth(
                    status=ComponentStatus.UNHEALTHY,
                    message="Redis连接失败",
                    metrics={}
                )
            },
            timestamp=Mock()
        )
        health_checker.run_health_check.return_value = mock_result
        health_checker.attempt_redis_recovery.return_value = True
        
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            health_check_interval=1
        )
        
        daemon.start()
        
        try:
            # 等待至少执行一次检查
            time.sleep(1.5)
            
            # 验证Redis恢复被调用
            assert health_checker.attempt_redis_recovery.call_count >= 1
        finally:
            daemon.graceful_shutdown()
    
    def test_health_check_loop_handles_exceptions(self):
        """测试健康检查循环处理异常"""
        health_checker = Mock(spec=HealthChecker)
        fund_monitor = FundMonitor(initial_equity=100000.0)
        
        # 模拟健康检查抛出异常
        health_checker.run_health_check.side_effect = Exception("测试异常")
        
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            health_check_interval=1
        )
        
        daemon.start()
        
        try:
            # 等待至少执行一次检查
            time.sleep(1.5)
            
            # 验证循环继续运行（没有崩溃）
            assert daemon._running is True
            assert daemon._health_check_thread.is_alive()
        finally:
            daemon.graceful_shutdown()


class TestDaemonManagerFundMonitorLoop:
    """测试资金监控循环"""
    
    def test_fund_monitor_loop_executes_checks(self):
        """测试资金监控循环执行检查"""
        health_checker = HealthChecker()
        fund_monitor = Mock(spec=FundMonitor)
        fund_monitor.initial_equity = 100000.0
        
        # 模拟资金状态
        mock_status = FundStatus(
            current_equity=100000.0,
            daily_pnl=0.0,
            daily_pnl_pct=0.0,
            drawdown=0.0,
            alert_level=AlertLevel.NORMAL
        )
        fund_monitor.check_fund_status.return_value = mock_status
        
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            fund_monitor_interval=1  # 1秒间隔用于快速测试
        )
        
        daemon.start()
        
        try:
            # 等待至少执行一次检查
            time.sleep(1.5)
            
            # 验证资金监控被调用
            assert fund_monitor.check_fund_status.call_count >= 1
        finally:
            daemon.graceful_shutdown()
    
    def test_fund_monitor_loop_uses_callback(self):
        """测试资金监控循环使用回调函数获取权益"""
        health_checker = HealthChecker()
        fund_monitor = Mock(spec=FundMonitor)
        fund_monitor.initial_equity = 100000.0
        
        # 模拟资金状态
        mock_status = FundStatus(
            current_equity=95000.0,
            daily_pnl=-5000.0,
            daily_pnl_pct=-5.0,
            drawdown=5.0,
            alert_level=AlertLevel.DANGER
        )
        fund_monitor.check_fund_status.return_value = mock_status
        
        # 设置回调函数
        equity_callback = Mock(return_value=95000.0)
        
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            fund_monitor_interval=1
        )
        daemon.set_get_current_equity_callback(equity_callback)
        
        daemon.start()
        
        try:
            # 等待至少执行一次检查
            time.sleep(1.5)
            
            # 验证回调函数被调用
            assert equity_callback.call_count >= 1
            # 验证资金监控使用回调返回的权益
            assert fund_monitor.check_fund_status.call_count >= 1
            fund_monitor.check_fund_status.assert_called_with(95000.0)
        finally:
            daemon.graceful_shutdown()
    
    def test_fund_monitor_loop_handles_callback_exception(self):
        """测试资金监控循环处理回调异常"""
        health_checker = HealthChecker()
        fund_monitor = Mock(spec=FundMonitor)
        fund_monitor.initial_equity = 100000.0
        
        # 设置抛出异常的回调函数
        equity_callback = Mock(side_effect=Exception("回调异常"))
        
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            fund_monitor_interval=1
        )
        daemon.set_get_current_equity_callback(equity_callback)
        
        daemon.start()
        
        try:
            # 等待至少执行一次检查
            time.sleep(1.5)
            
            # 验证循环继续运行（没有崩溃）
            assert daemon._running is True
            assert daemon._fund_monitor_thread.is_alive()
        finally:
            daemon.graceful_shutdown()
    
    def test_fund_monitor_loop_handles_check_exception(self):
        """测试资金监控循环处理检查异常"""
        health_checker = HealthChecker()
        fund_monitor = Mock(spec=FundMonitor)
        fund_monitor.initial_equity = 100000.0
        
        # 模拟检查抛出异常
        fund_monitor.check_fund_status.side_effect = Exception("检查异常")
        
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            fund_monitor_interval=1
        )
        
        daemon.start()
        
        try:
            # 等待至少执行一次检查
            time.sleep(1.5)
            
            # 验证循环继续运行（没有崩溃）
            assert daemon._running is True
            assert daemon._fund_monitor_thread.is_alive()
        finally:
            daemon.graceful_shutdown()


class TestDaemonManagerGracefulShutdown:
    """测试优雅关闭"""
    
    def test_graceful_shutdown_stops_threads(self):
        """测试优雅关闭停止线程"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            health_check_interval=1,  # 短间隔用于快速测试
            fund_monitor_interval=1
        )
        
        daemon.start()
        
        # 等待线程启动
        time.sleep(0.5)
        
        daemon.graceful_shutdown()
        
        # 等待线程结束（最多等待6秒：5秒超时 + 1秒余量）
        time.sleep(6)
        
        assert daemon._running is False
        assert not daemon._health_check_thread.is_alive()
        assert not daemon._fund_monitor_thread.is_alive()
    
    def test_graceful_shutdown_when_not_running(self):
        """测试未运行时优雅关闭"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor
        )
        
        # 未启动就关闭，应该不抛出异常
        daemon.graceful_shutdown()
        
        assert daemon._running is False
    
    def test_graceful_shutdown_waits_for_threads(self):
        """测试优雅关闭等待线程完成"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            health_check_interval=10,  # 长间隔
            fund_monitor_interval=10
        )
        
        daemon.start()
        
        # 等待线程启动
        time.sleep(0.5)
        
        start_time = time.time()
        daemon.graceful_shutdown()
        shutdown_time = time.time() - start_time
        
        # 关闭应该在超时时间内完成（5秒超时 * 2个线程 = 最多10秒）
        assert shutdown_time < 12  # 留一些余量
        assert daemon._running is False


class TestDaemonManagerSignalHandler:
    """测试信号处理"""
    
    def test_signal_handler_triggers_shutdown(self):
        """测试信号处理器触发关闭"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor
        )
        
        daemon.start()
        
        # 等待线程启动
        time.sleep(0.5)
        
        # 模拟信号
        import signal
        daemon._signal_handler(signal.SIGINT, None)
        
        # 等待关闭完成
        time.sleep(1)
        
        assert daemon._running is False
    
    def test_signal_handler_with_sigterm(self):
        """测试SIGTERM信号处理"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor
        )
        
        daemon.start()
        
        # 等待线程启动
        time.sleep(0.5)
        
        # 模拟SIGTERM信号
        import signal
        daemon._signal_handler(signal.SIGTERM, None)
        
        # 等待关闭完成
        time.sleep(1)
        
        assert daemon._running is False


class TestDaemonManagerIntegration:
    """测试DaemonManager集成场景"""
    
    def test_concurrent_health_check_and_fund_monitor(self):
        """测试健康检查和资金监控并发运行"""
        health_checker = Mock(spec=HealthChecker)
        fund_monitor = Mock(spec=FundMonitor)
        fund_monitor.initial_equity = 100000.0
        
        # 模拟健康检查结果
        mock_health_result = HealthCheckResult(
            overall_status=OverallStatus.HEALTHY,
            components={},
            timestamp=Mock()
        )
        health_checker.run_health_check.return_value = mock_health_result
        
        # 模拟资金状态
        mock_fund_status = FundStatus(
            current_equity=100000.0,
            daily_pnl=0.0,
            daily_pnl_pct=0.0,
            drawdown=0.0,
            alert_level=AlertLevel.NORMAL
        )
        fund_monitor.check_fund_status.return_value = mock_fund_status
        
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            health_check_interval=1,
            fund_monitor_interval=1
        )
        
        daemon.start()
        
        try:
            # 等待多次检查
            time.sleep(2.5)
            
            # 验证两个循环都在运行
            assert health_checker.run_health_check.call_count >= 2
            assert fund_monitor.check_fund_status.call_count >= 2
        finally:
            daemon.graceful_shutdown()
    
    def test_different_check_intervals(self):
        """测试不同的检查间隔"""
        health_checker = Mock(spec=HealthChecker)
        fund_monitor = Mock(spec=FundMonitor)
        fund_monitor.initial_equity = 100000.0
        
        # 模拟健康检查结果
        mock_health_result = HealthCheckResult(
            overall_status=OverallStatus.HEALTHY,
            components={},
            timestamp=Mock()
        )
        health_checker.run_health_check.return_value = mock_health_result
        
        # 模拟资金状态
        mock_fund_status = FundStatus(
            current_equity=100000.0,
            daily_pnl=0.0,
            daily_pnl_pct=0.0,
            drawdown=0.0,
            alert_level=AlertLevel.NORMAL
        )
        fund_monitor.check_fund_status.return_value = mock_fund_status
        
        # 健康检查1秒，资金监控2秒
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            health_check_interval=1,
            fund_monitor_interval=2
        )
        
        daemon.start()
        
        try:
            # 等待3秒
            time.sleep(3.5)
            
            # 健康检查应该执行约3次，资金监控应该执行约1-2次
            health_check_count = health_checker.run_health_check.call_count
            fund_monitor_count = fund_monitor.check_fund_status.call_count
            
            assert health_check_count >= 3
            assert fund_monitor_count >= 1
            assert health_check_count > fund_monitor_count
        finally:
            daemon.graceful_shutdown()


class TestDaemonManagerEdgeCases:
    """测试边界情况"""
    
    def test_rapid_start_stop(self):
        """测试快速启动停止"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor
        )
        
        daemon.start()
        time.sleep(0.1)  # 很短的运行时间
        daemon.graceful_shutdown()
        
        assert daemon._running is False
    
    def test_multiple_shutdown_calls(self):
        """测试多次关闭调用"""
        health_checker = HealthChecker()
        fund_monitor = FundMonitor(initial_equity=100000.0)
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor
        )
        
        daemon.start()
        time.sleep(0.5)
        
        daemon.graceful_shutdown()
        daemon.graceful_shutdown()  # 第二次关闭应该不抛出异常
        
        assert daemon._running is False
    
    def test_set_callback_before_start(self):
        """测试启动前设置回调"""
        health_checker = HealthChecker()
        fund_monitor = Mock(spec=FundMonitor)
        fund_monitor.initial_equity = 100000.0
        
        mock_status = FundStatus(
            current_equity=105000.0,
            daily_pnl=5000.0,
            daily_pnl_pct=5.0,
            drawdown=0.0,
            alert_level=AlertLevel.NORMAL
        )
        fund_monitor.check_fund_status.return_value = mock_status
        
        equity_callback = Mock(return_value=105000.0)
        
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            fund_monitor_interval=1
        )
        
        # 启动前设置回调
        daemon.set_get_current_equity_callback(equity_callback)
        
        daemon.start()
        
        try:
            time.sleep(1.5)
            
            # 验证回调被使用
            assert equity_callback.call_count >= 1
        finally:
            daemon.graceful_shutdown()
    
    def test_set_callback_after_start(self):
        """测试启动后设置回调"""
        health_checker = HealthChecker()
        fund_monitor = Mock(spec=FundMonitor)
        fund_monitor.initial_equity = 100000.0
        
        mock_status = FundStatus(
            current_equity=98000.0,
            daily_pnl=-2000.0,
            daily_pnl_pct=-2.0,
            drawdown=2.0,
            alert_level=AlertLevel.NORMAL
        )
        fund_monitor.check_fund_status.return_value = mock_status
        
        equity_callback = Mock(return_value=98000.0)
        
        daemon = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            fund_monitor_interval=1
        )
        
        daemon.start()
        
        try:
            # 启动后设置回调
            daemon.set_get_current_equity_callback(equity_callback)
            
            time.sleep(1.5)
            
            # 验证回调被使用
            assert equity_callback.call_count >= 1
        finally:
            daemon.graceful_shutdown()



class TestDaemonManagerCoverageCompletion:
    """测试DaemonManager未覆盖的代码路径
    
    这些测试覆盖daemon_manager.py中未被覆盖的代码路径，
    以达到100%测试覆盖率目标。
    """
    
    def test_health_check_loop_redis_recovery_success(self):
        """测试健康检查循环中Redis恢复成功的情况
        
        覆盖: daemon_manager.py line 163 (Redis recovery success branch)
        """
        from datetime import datetime
        
        health_checker = Mock(spec=HealthChecker)
        fund_monitor = Mock(spec=FundMonitor)
        
        # 第一次检查Redis不健康，第二次恢复成功
        redis_unhealthy = ComponentHealth(
            status=ComponentStatus.UNHEALTHY,
            message="Redis不健康",
            metrics={}
        )
        
        health_result = HealthCheckResult(
            overall_status=OverallStatus.CRITICAL,
            components={"redis": redis_unhealthy},
            timestamp=datetime.now()
        )
        
        health_checker.run_health_check.return_value = health_result
        health_checker.attempt_redis_recovery.return_value = True  # 恢复成功
        
        manager = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            health_check_interval=0.1
        )
        
        # 启动并快速停止
        manager.start()
        time.sleep(0.2)
        manager.graceful_shutdown()
        
        # 验证恢复被调用
        health_checker.attempt_redis_recovery.assert_called()
    
    def test_health_check_loop_redis_recovery_failure(self):
        """测试健康检查循环中Redis恢复失败的情况
        
        覆盖: daemon_manager.py line 171 (Redis recovery failure branch)
        """
        from datetime import datetime
        
        health_checker = Mock(spec=HealthChecker)
        fund_monitor = Mock(spec=FundMonitor)
        
        # Redis不健康且恢复失败
        redis_unhealthy = ComponentHealth(
            status=ComponentStatus.UNHEALTHY,
            message="Redis不健康",
            metrics={}
        )
        
        health_result = HealthCheckResult(
            overall_status=OverallStatus.CRITICAL,
            components={"redis": redis_unhealthy},
            timestamp=datetime.now()
        )
        
        health_checker.run_health_check.return_value = health_result
        health_checker.attempt_redis_recovery.return_value = False  # 恢复失败
        
        manager = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            health_check_interval=0.1
        )
        
        # 启动并快速停止
        manager.start()
        time.sleep(0.2)
        manager.graceful_shutdown()
        
        # 验证恢复被调用
        health_checker.attempt_redis_recovery.assert_called()
    
    def test_health_check_loop_degraded_status(self):
        """测试健康检查循环中系统降级状态
        
        覆盖: daemon_manager.py line 171 (DEGRADED status logging)
        """
        from datetime import datetime
        
        health_checker = Mock(spec=HealthChecker)
        fund_monitor = Mock(spec=FundMonitor)
        
        # 系统降级状态
        health_result = HealthCheckResult(
            overall_status=OverallStatus.DEGRADED,
            components={},
            timestamp=datetime.now()
        )
        
        health_checker.run_health_check.return_value = health_result
        
        manager = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            health_check_interval=0.05  # 更短的间隔
        )
        
        # 启动并等待足够时间让循环执行多次
        manager.start()
        time.sleep(0.5)  # 更长的等待时间
        manager.graceful_shutdown()
        
        # 验证健康检查被调用多次
        assert health_checker.run_health_check.call_count >= 2
    
    def test_fund_monitor_loop_critical_status(self):
        """测试资金监控循环中严重状态
        
        覆盖: daemon_manager.py line 210 (CRITICAL status logging)
        """
        health_checker = Mock(spec=HealthChecker)
        fund_monitor = Mock(spec=FundMonitor)
        
        # 资金状态严重
        critical_status = FundStatus(
            current_equity=80000.0,
            daily_pnl=-20000.0,
            daily_pnl_pct=-20.0,
            drawdown=20.0,
            alert_level=AlertLevel.CRITICAL
        )
        
        fund_monitor.check_fund_status.return_value = critical_status
        
        manager = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            fund_monitor_interval=0.05  # 更短的间隔
        )
        
        # 设置equity回调
        manager.set_get_current_equity_callback(lambda: 80000.0)
        
        # 启动并等待足够时间让循环执行多次
        manager.start()
        time.sleep(0.5)  # 更长的等待时间
        manager.graceful_shutdown()
        
        # 验证资金检查被调用多次
        assert fund_monitor.check_fund_status.call_count >= 2
    
    def test_fund_monitor_loop_warning_status(self):
        """测试资金监控循环中警告状态
        
        覆盖: daemon_manager.py line 224 (WARNING status logging)
        """
        health_checker = Mock(spec=HealthChecker)
        fund_monitor = Mock(spec=FundMonitor)
        
        # 资金状态警告
        warning_status = FundStatus(
            current_equity=95000.0,
            daily_pnl=-5000.0,
            daily_pnl_pct=-5.0,
            drawdown=5.0,
            alert_level=AlertLevel.WARNING
        )
        
        fund_monitor.check_fund_status.return_value = warning_status
        
        manager = DaemonManager(
            health_checker=health_checker,
            fund_monitor=fund_monitor,
            fund_monitor_interval=0.05  # 更短的间隔
        )
        
        # 设置equity回调
        manager.set_get_current_equity_callback(lambda: 95000.0)
        
        # 启动并等待足够时间让循环执行多次
        manager.start()
        time.sleep(0.5)  # 更长的等待时间
        manager.graceful_shutdown()
        
        # 验证资金检查被调用多次
        assert fund_monitor.check_fund_status.call_count >= 2
