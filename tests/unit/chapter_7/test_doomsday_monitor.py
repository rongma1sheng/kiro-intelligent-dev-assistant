"""DoomsdayMonitor单元测试

白皮书依据: 第七章 6.4 末日风控

测试末日风控监控器的各项功能：
- lock文件检测
- 日亏损计算（>10%触发）
- 连续亏损计算（3日>20%触发）
- 保证金风险计算（>95%触发）
- 紧急停止流程
- 通知发送
"""

import pytest
import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock

from src.compliance.doomsday_monitor import (
    DoomsdayMonitor,
    DoomsdayError,
    DoomsdayAlreadyTriggeredError,
    DoomsdayTriggerType,
    DoomsdayEvent,
    DoomsdayStatus,
)


class TestDoomsdayMonitorInit:
    """DoomsdayMonitor初始化测试"""
    
    def test_init_default_values(self, tmp_path):
        """测试默认参数初始化"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        assert monitor.lock_file == lock_file
        assert monitor.daily_loss_threshold == 10.0
        assert monitor.consecutive_loss_threshold == 20.0
        assert monitor.consecutive_days == 3
        assert monitor.margin_risk_threshold == 95.0
        assert not monitor.is_triggered
    
    def test_init_custom_values(self, tmp_path):
        """测试自定义参数初始化"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(
            lock_file=lock_file,
            daily_loss_threshold=15.0,
            consecutive_loss_threshold=25.0,
            consecutive_days=5,
            margin_risk_threshold=90.0,
        )
        
        assert monitor.daily_loss_threshold == 15.0
        assert monitor.consecutive_loss_threshold == 25.0
        assert monitor.consecutive_days == 5
        assert monitor.margin_risk_threshold == 90.0
    
    def test_init_with_trading_engine(self, tmp_path):
        """测试带交易引擎初始化"""
        lock_file = tmp_path / ".doomsday.lock"
        mock_engine = Mock()
        monitor = DoomsdayMonitor(
            lock_file=lock_file,
            trading_engine=mock_engine,
        )
        
        assert monitor.trading_engine is mock_engine
    
    def test_init_with_notification_manager(self, tmp_path):
        """测试带通知管理器初始化"""
        lock_file = tmp_path / ".doomsday.lock"
        mock_notifier = Mock()
        monitor = DoomsdayMonitor(
            lock_file=lock_file,
            notification_manager=mock_notifier,
        )
        
        assert monitor.notification_manager is mock_notifier
    
    def test_init_with_audit_logger(self, tmp_path):
        """测试带审计日志初始化"""
        lock_file = tmp_path / ".doomsday.lock"
        mock_logger = Mock()
        monitor = DoomsdayMonitor(
            lock_file=lock_file,
            audit_logger=mock_logger,
        )
        
        assert monitor.audit_logger is mock_logger
    
    def test_init_invalid_daily_loss_threshold(self, tmp_path):
        """测试无效的单日亏损阈值"""
        lock_file = tmp_path / ".doomsday.lock"
        
        with pytest.raises(ValueError, match="单日亏损阈值必须在"):
            DoomsdayMonitor(lock_file=lock_file, daily_loss_threshold=0)
        
        with pytest.raises(ValueError, match="单日亏损阈值必须在"):
            DoomsdayMonitor(lock_file=lock_file, daily_loss_threshold=101)
        
        with pytest.raises(ValueError, match="单日亏损阈值必须在"):
            DoomsdayMonitor(lock_file=lock_file, daily_loss_threshold=-5)
    
    def test_init_invalid_consecutive_loss_threshold(self, tmp_path):
        """测试无效的连续亏损阈值"""
        lock_file = tmp_path / ".doomsday.lock"
        
        with pytest.raises(ValueError, match="连续亏损阈值必须在"):
            DoomsdayMonitor(lock_file=lock_file, consecutive_loss_threshold=0)
        
        with pytest.raises(ValueError, match="连续亏损阈值必须在"):
            DoomsdayMonitor(lock_file=lock_file, consecutive_loss_threshold=150)
    
    def test_init_invalid_consecutive_days(self, tmp_path):
        """测试无效的连续天数"""
        lock_file = tmp_path / ".doomsday.lock"
        
        with pytest.raises(ValueError, match="连续亏损天数必须大于0"):
            DoomsdayMonitor(lock_file=lock_file, consecutive_days=0)
        
        with pytest.raises(ValueError, match="连续亏损天数必须大于0"):
            DoomsdayMonitor(lock_file=lock_file, consecutive_days=-1)
    
    def test_init_invalid_margin_risk_threshold(self, tmp_path):
        """测试无效的保证金风险阈值"""
        lock_file = tmp_path / ".doomsday.lock"
        
        with pytest.raises(ValueError, match="保证金风险阈值必须在"):
            DoomsdayMonitor(lock_file=lock_file, margin_risk_threshold=0)
        
        with pytest.raises(ValueError, match="保证金风险阈值必须在"):
            DoomsdayMonitor(lock_file=lock_file, margin_risk_threshold=105)


class TestLockFileDetection:
    """lock文件检测测试"""
    
    def test_check_lock_file_not_exists(self, tmp_path):
        """测试lock文件不存在"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        assert not monitor.check_lock_file()
    
    def test_check_lock_file_exists(self, tmp_path):
        """测试lock文件存在"""
        lock_file = tmp_path / ".doomsday.lock"
        lock_file.write_text("locked")
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        assert monitor.check_lock_file()
    
    def test_delete_lock_file(self, tmp_path):
        """测试删除lock文件"""
        lock_file = tmp_path / ".doomsday.lock"
        lock_file.write_text("locked")
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        assert monitor.check_lock_file()
        result = monitor.delete_lock_file()
        assert result
        assert not monitor.check_lock_file()
    
    def test_delete_lock_file_not_exists(self, tmp_path):
        """测试删除不存在的lock文件"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        result = monitor.delete_lock_file()
        assert not result


class TestDailyPnlCalculation:
    """日亏损计算测试"""
    
    def test_get_daily_pnl_percentage_profit(self, tmp_path):
        """测试盈利情况"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(daily_pnl=10000, total_assets=100000)
        
        pnl = monitor.get_daily_pnl_percentage()
        
        assert pnl == 10.0
    
    def test_get_daily_pnl_percentage_loss(self, tmp_path):
        """测试亏损情况"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(daily_pnl=-15000, total_assets=100000)
        
        pnl = monitor.get_daily_pnl_percentage()
        
        assert pnl == -15.0
    
    def test_get_daily_pnl_percentage_zero_assets(self, tmp_path):
        """测试零资产情况"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(daily_pnl=1000, total_assets=0)
        
        pnl = monitor.get_daily_pnl_percentage()
        
        assert pnl == 0.0
    
    def test_get_daily_pnl_percentage_no_data(self, tmp_path):
        """测试无数据情况"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        pnl = monitor.get_daily_pnl_percentage()
        
        assert pnl == 0.0


class TestConsecutiveLossCalculation:
    """连续亏损计算测试"""
    
    def test_get_consecutive_loss_percentage_loss(self, tmp_path):
        """测试连续亏损"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(
            historical_pnl=[-5000, -8000, -7000],
            total_assets=100000,
        )
        
        loss = monitor.get_consecutive_loss_percentage()
        
        assert loss == -20.0
    
    def test_get_consecutive_loss_percentage_profit(self, tmp_path):
        """测试连续盈利"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(
            historical_pnl=[5000, 3000, 2000],
            total_assets=100000,
        )
        
        loss = monitor.get_consecutive_loss_percentage()
        
        assert loss == 10.0
    
    def test_get_consecutive_loss_percentage_mixed(self, tmp_path):
        """测试盈亏混合"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(
            historical_pnl=[-5000, 3000, -2000],
            total_assets=100000,
        )
        
        loss = monitor.get_consecutive_loss_percentage()
        
        assert loss == -4.0
    
    def test_get_consecutive_loss_percentage_custom_days(self, tmp_path):
        """测试自定义天数"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file, consecutive_days=5)
        monitor.set_mock_data(
            historical_pnl=[-5000, -3000, -2000, -4000, -6000],
            total_assets=100000,
        )
        
        loss = monitor.get_consecutive_loss_percentage()
        
        assert loss == -20.0
    
    def test_get_consecutive_loss_percentage_zero_assets(self, tmp_path):
        """测试零资产情况"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(
            historical_pnl=[-5000, -3000, -2000],
            total_assets=0,
        )
        
        loss = monitor.get_consecutive_loss_percentage()
        
        assert loss == 0.0


class TestMarginRiskCalculation:
    """保证金风险计算测试"""
    
    def test_get_margin_risk_ratio_low(self, tmp_path):
        """测试低风险"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(margin_used=30000, margin_available=70000)
        
        risk = monitor.get_margin_risk_ratio()
        
        assert risk == 30.0
    
    def test_get_margin_risk_ratio_high(self, tmp_path):
        """测试高风险"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(margin_used=96000, margin_available=4000)
        
        risk = monitor.get_margin_risk_ratio()
        
        assert risk == 96.0
    
    def test_get_margin_risk_ratio_zero_margin(self, tmp_path):
        """测试零保证金"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(margin_used=0, margin_available=0)
        
        risk = monitor.get_margin_risk_ratio()
        
        assert risk == 0.0
    
    def test_get_margin_risk_ratio_full_used(self, tmp_path):
        """测试全部使用"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(margin_used=100000, margin_available=0)
        
        risk = monitor.get_margin_risk_ratio()
        
        assert risk == 100.0


class TestCheckDoomsdayConditions:
    """检查末日条件测试"""
    
    @pytest.mark.asyncio
    async def test_check_no_trigger(self, tmp_path):
        """测试无触发条件"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(
            daily_pnl=-5000,
            total_assets=100000,
            historical_pnl=[-3000, -2000, -1000],
            margin_used=50000,
            margin_available=50000,
        )
        
        event = await monitor.check_doomsday_conditions()
        
        assert event is None
        assert not monitor.is_triggered
    
    @pytest.mark.asyncio
    async def test_check_lock_file_trigger(self, tmp_path):
        """测试lock文件触发"""
        lock_file = tmp_path / ".doomsday.lock"
        lock_file.write_text("locked")
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        event = await monitor.check_doomsday_conditions()
        
        assert event is not None
        assert event.trigger_type == DoomsdayTriggerType.LOCK_FILE
        assert monitor.is_triggered
    
    @pytest.mark.asyncio
    async def test_check_daily_loss_trigger(self, tmp_path):
        """测试单日亏损触发"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(
            daily_pnl=-12000,  # -12%
            total_assets=100000,
            historical_pnl=[-3000, -2000, -1000],
            margin_used=50000,
            margin_available=50000,
        )
        
        event = await monitor.check_doomsday_conditions()
        
        assert event is not None
        assert event.trigger_type == DoomsdayTriggerType.DAILY_LOSS
        assert "12.00%" in event.reason
        assert monitor.is_triggered
    
    @pytest.mark.asyncio
    async def test_check_consecutive_loss_trigger(self, tmp_path):
        """测试连续亏损触发"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(
            daily_pnl=-5000,  # -5%，不触发单日
            total_assets=100000,
            historical_pnl=[-8000, -7000, -6000],  # -21%
            margin_used=50000,
            margin_available=50000,
        )
        
        event = await monitor.check_doomsday_conditions()
        
        assert event is not None
        assert event.trigger_type == DoomsdayTriggerType.CONSECUTIVE_LOSS
        assert "21.00%" in event.reason
        assert monitor.is_triggered
    
    @pytest.mark.asyncio
    async def test_check_margin_risk_trigger(self, tmp_path):
        """测试保证金风险触发"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(
            daily_pnl=-5000,  # -5%
            total_assets=100000,
            historical_pnl=[-3000, -2000, -1000],  # -6%
            margin_used=96000,  # 96%
            margin_available=4000,
        )
        
        event = await monitor.check_doomsday_conditions()
        
        assert event is not None
        assert event.trigger_type == DoomsdayTriggerType.MARGIN_RISK
        assert "96.00%" in event.reason
        assert monitor.is_triggered
    
    @pytest.mark.asyncio
    async def test_check_already_triggered(self, tmp_path):
        """测试已触发后再次检查"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(
            daily_pnl=-12000,
            total_assets=100000,
            historical_pnl=[-3000, -2000, -1000],
            margin_used=50000,
            margin_available=50000,
        )
        
        await monitor.check_doomsday_conditions()
        
        with pytest.raises(DoomsdayAlreadyTriggeredError, match="已触发"):
            await monitor.check_doomsday_conditions()
    
    @pytest.mark.asyncio
    async def test_check_priority_lock_file_first(self, tmp_path):
        """测试优先级：lock文件优先"""
        lock_file = tmp_path / ".doomsday.lock"
        lock_file.write_text("locked")
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(
            daily_pnl=-15000,  # 也触发单日亏损
            total_assets=100000,
            historical_pnl=[-10000, -8000, -7000],  # 也触发连续亏损
            margin_used=98000,  # 也触发保证金风险
            margin_available=2000,
        )
        
        event = await monitor.check_doomsday_conditions()
        
        # lock文件优先
        assert event.trigger_type == DoomsdayTriggerType.LOCK_FILE


class TestTriggerDoomsday:
    """触发末日开关测试"""
    
    @pytest.mark.asyncio
    async def test_trigger_creates_lock_file(self, tmp_path):
        """测试触发创建lock文件"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        await monitor.trigger_doomsday(reason="测试触发")
        
        assert lock_file.exists()
        content = json.loads(lock_file.read_text())
        assert content['reason'] == "测试触发"
    
    @pytest.mark.asyncio
    async def test_trigger_updates_state(self, tmp_path):
        """测试触发更新状态"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        event = await monitor.trigger_doomsday(
            reason="测试触发",
            trigger_type=DoomsdayTriggerType.MANUAL,
        )
        
        assert monitor.is_triggered
        assert monitor._trigger_reason == "测试触发"
        assert monitor._trigger_type == DoomsdayTriggerType.MANUAL
        assert monitor._trigger_time is not None
    
    @pytest.mark.asyncio
    async def test_trigger_returns_event(self, tmp_path):
        """测试触发返回事件"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        event = await monitor.trigger_doomsday(
            reason="测试触发",
            trigger_type=DoomsdayTriggerType.DAILY_LOSS,
            trigger_value=-12.0,
            threshold=-10.0,
        )
        
        assert event.reason == "测试触发"
        assert event.trigger_type == DoomsdayTriggerType.DAILY_LOSS
        assert event.trigger_value == -12.0
        assert event.threshold == -10.0
    
    @pytest.mark.asyncio
    async def test_trigger_calls_trading_engine(self, tmp_path):
        """测试触发调用交易引擎"""
        lock_file = tmp_path / ".doomsday.lock"
        mock_engine = AsyncMock()
        mock_engine.cancel_all_orders.return_value = 5
        mock_engine.close_all_positions.return_value = 3
        
        monitor = DoomsdayMonitor(
            lock_file=lock_file,
            trading_engine=mock_engine,
        )
        
        await monitor.trigger_doomsday(reason="测试触发")
        
        mock_engine.cancel_all_orders.assert_called_once()
        mock_engine.close_all_positions.assert_called_once()
        mock_engine.emergency_stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_trigger_sends_notification(self, tmp_path):
        """测试触发发送通知"""
        lock_file = tmp_path / ".doomsday.lock"
        mock_notifier = AsyncMock()
        
        monitor = DoomsdayMonitor(
            lock_file=lock_file,
            notification_manager=mock_notifier,
        )
        
        await monitor.trigger_doomsday(reason="测试触发")
        
        mock_notifier.send_alert.assert_called_once()
        call_args = mock_notifier.send_alert.call_args
        assert "末日风控触发" in call_args[1]['title']
        assert call_args[1]['level'] == "critical"
    
    @pytest.mark.asyncio
    async def test_trigger_logs_audit(self, tmp_path):
        """测试触发记录审计日志"""
        lock_file = tmp_path / ".doomsday.lock"
        mock_logger = Mock()
        
        monitor = DoomsdayMonitor(
            lock_file=lock_file,
            audit_logger=mock_logger,
        )
        
        await monitor.trigger_doomsday(reason="测试触发")
        
        mock_logger.log_event.assert_called_once()
        call_args = mock_logger.log_event.call_args[0][0]
        assert call_args['event_type'] == 'DOOMSDAY_TRIGGERED'
        assert call_args['reason'] == "测试触发"
    
    @pytest.mark.asyncio
    async def test_trigger_already_triggered(self, tmp_path):
        """测试重复触发"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        await monitor.trigger_doomsday(reason="第一次触发")
        
        with pytest.raises(DoomsdayAlreadyTriggeredError, match="已触发"):
            await monitor.trigger_doomsday(reason="第二次触发")
    
    @pytest.mark.asyncio
    async def test_trigger_callback(self, tmp_path):
        """测试触发回调"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        callback_events = []
        monitor.register_callback(lambda e: callback_events.append(e))
        
        await monitor.trigger_doomsday(reason="测试触发")
        
        assert len(callback_events) == 1
        assert callback_events[0].reason == "测试触发"


class TestReset:
    """重置测试"""
    
    @pytest.mark.asyncio
    async def test_reset_success(self, tmp_path):
        """测试成功重置"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        await monitor.trigger_doomsday(reason="测试触发")
        assert monitor.is_triggered
        
        # 删除lock文件后重置
        monitor.delete_lock_file()
        monitor.reset()
        
        assert not monitor.is_triggered
        assert monitor._trigger_time is None
        assert monitor._trigger_type is None
        assert monitor._trigger_reason is None
    
    @pytest.mark.asyncio
    async def test_reset_with_lock_file(self, tmp_path):
        """测试lock文件存在时重置失败"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        await monitor.trigger_doomsday(reason="测试触发")
        
        with pytest.raises(DoomsdayError, match="lock文件仍然存在"):
            monitor.reset()


class TestGetStatus:
    """获取状态测试"""
    
    def test_get_status_not_triggered(self, tmp_path):
        """测试未触发状态"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        monitor.set_mock_data(
            daily_pnl=-5000,
            total_assets=100000,
            historical_pnl=[-3000, -2000, -1000],
            margin_used=50000,
            margin_available=50000,
        )
        
        status = monitor.get_status()
        
        assert not status.is_triggered
        assert status.trigger_time is None
        assert status.trigger_type is None
        assert status.daily_pnl_percentage == -5.0
        assert status.consecutive_loss_percentage == -6.0
        assert status.margin_risk_ratio == 50.0
        assert not status.lock_file_exists
    
    @pytest.mark.asyncio
    async def test_get_status_triggered(self, tmp_path):
        """测试已触发状态"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        await monitor.trigger_doomsday(
            reason="测试触发",
            trigger_type=DoomsdayTriggerType.DAILY_LOSS,
        )
        
        status = monitor.get_status()
        
        assert status.is_triggered
        assert status.trigger_time is not None
        assert status.trigger_type == DoomsdayTriggerType.DAILY_LOSS
        assert status.reason == "测试触发"
        assert status.lock_file_exists
    
    def test_status_to_dict(self, tmp_path):
        """测试状态转换为字典"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        status = monitor.get_status()
        status_dict = status.to_dict()
        
        assert 'is_triggered' in status_dict
        assert 'daily_pnl_percentage' in status_dict
        assert 'consecutive_loss_percentage' in status_dict
        assert 'margin_risk_ratio' in status_dict


class TestDoomsdayEvent:
    """DoomsdayEvent数据类测试"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        event = DoomsdayEvent(
            timestamp="2024-01-01T00:00:00",
            trigger_type=DoomsdayTriggerType.DAILY_LOSS,
            reason="单日亏损超过阈值",
            trigger_value=-12.0,
            threshold=-10.0,
            actions_taken=["取消订单", "平仓"],
        )
        
        result = event.to_dict()
        
        assert result['timestamp'] == "2024-01-01T00:00:00"
        assert result['trigger_type'] == "daily_loss"
        assert result['reason'] == "单日亏损超过阈值"
        assert result['trigger_value'] == -12.0
        assert result['threshold'] == -10.0
        assert result['actions_taken'] == ["取消订单", "平仓"]


class TestMockData:
    """模拟数据测试"""
    
    def test_set_mock_data(self, tmp_path):
        """测试设置模拟数据"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        monitor.set_mock_data(
            daily_pnl=-10000,
            total_assets=100000,
            historical_pnl=[-5000, -3000, -2000],
            margin_used=80000,
            margin_available=20000,
        )
        
        assert monitor.get_daily_pnl_percentage() == -10.0
        assert monitor.get_consecutive_loss_percentage() == -10.0
        assert monitor.get_margin_risk_ratio() == 80.0
    
    def test_clear_mock_data(self, tmp_path):
        """测试清除模拟数据"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        monitor.set_mock_data(daily_pnl=-10000, total_assets=100000)
        assert monitor.get_daily_pnl_percentage() == -10.0
        
        monitor.clear_mock_data()
        assert monitor.get_daily_pnl_percentage() == 0.0


class TestGetEvents:
    """获取事件测试"""
    
    @pytest.mark.asyncio
    async def test_get_events(self, tmp_path):
        """测试获取事件列表"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        await monitor.trigger_doomsday(reason="测试触发")
        
        events = monitor.get_events()
        
        assert len(events) == 1
        assert events[0].reason == "测试触发"
    
    def test_get_events_empty(self, tmp_path):
        """测试空事件列表"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        events = monitor.get_events()
        
        assert len(events) == 0


class TestEdgeCases:
    """边界条件测试"""
    
    @pytest.mark.asyncio
    async def test_exactly_at_daily_threshold(self, tmp_path):
        """测试恰好在单日阈值"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file, daily_loss_threshold=10.0)
        monitor.set_mock_data(
            daily_pnl=-10000,  # 恰好-10%
            total_assets=100000,
            historical_pnl=[-3000, -2000, -1000],
            margin_used=50000,
            margin_available=50000,
        )
        
        event = await monitor.check_doomsday_conditions()
        
        # 恰好等于阈值不触发（需要超过）
        assert event is None
    
    @pytest.mark.asyncio
    async def test_just_over_daily_threshold(self, tmp_path):
        """测试刚超过单日阈值"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file, daily_loss_threshold=10.0)
        monitor.set_mock_data(
            daily_pnl=-10001,  # 刚超过-10%
            total_assets=100000,
            historical_pnl=[-3000, -2000, -1000],
            margin_used=50000,
            margin_available=50000,
        )
        
        event = await monitor.check_doomsday_conditions()
        
        assert event is not None
        assert event.trigger_type == DoomsdayTriggerType.DAILY_LOSS
    
    @pytest.mark.asyncio
    async def test_exactly_at_margin_threshold(self, tmp_path):
        """测试恰好在保证金阈值"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file, margin_risk_threshold=95.0)
        monitor.set_mock_data(
            daily_pnl=-5000,
            total_assets=100000,
            historical_pnl=[-3000, -2000, -1000],
            margin_used=95000,  # 恰好95%
            margin_available=5000,
        )
        
        event = await monitor.check_doomsday_conditions()
        
        # 恰好等于阈值不触发（需要超过）
        assert event is None
    
    @pytest.mark.asyncio
    async def test_just_over_margin_threshold(self, tmp_path):
        """测试刚超过保证金阈值"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file, margin_risk_threshold=95.0)
        monitor.set_mock_data(
            daily_pnl=-5000,
            total_assets=100000,
            historical_pnl=[-3000, -2000, -1000],
            margin_used=95001,  # 刚超过95%
            margin_available=4999,
        )
        
        event = await monitor.check_doomsday_conditions()
        
        assert event is not None
        assert event.trigger_type == DoomsdayTriggerType.MARGIN_RISK


class TestPortfolioDataProvider:
    """使用PortfolioDataProvider的测试"""
    
    def test_get_daily_pnl_with_provider(self, tmp_path):
        """测试使用数据提供者获取日盈亏"""
        lock_file = tmp_path / ".doomsday.lock"
        
        # 创建模拟的数据提供者
        mock_provider = Mock()
        mock_provider.get_daily_pnl.return_value = -15000
        mock_provider.get_total_assets.return_value = 100000
        
        monitor = DoomsdayMonitor(
            lock_file=lock_file,
            portfolio_provider=mock_provider
        )
        
        pnl = monitor.get_daily_pnl_percentage()
        
        assert pnl == -15.0
        mock_provider.get_daily_pnl.assert_called_once()
        mock_provider.get_total_assets.assert_called_once()
    
    def test_get_consecutive_loss_with_provider(self, tmp_path):
        """测试使用数据提供者获取连续亏损"""
        lock_file = tmp_path / ".doomsday.lock"
        
        mock_provider = Mock()
        mock_provider.get_historical_pnl.return_value = [-8000, -7000, -6000]
        mock_provider.get_total_assets.return_value = 100000
        
        monitor = DoomsdayMonitor(
            lock_file=lock_file,
            portfolio_provider=mock_provider
        )
        
        loss = monitor.get_consecutive_loss_percentage()
        
        assert loss == -21.0
        mock_provider.get_historical_pnl.assert_called_once_with(3)
        mock_provider.get_total_assets.assert_called_once()
    
    def test_get_margin_risk_with_provider(self, tmp_path):
        """测试使用数据提供者获取保证金风险"""
        lock_file = tmp_path / ".doomsday.lock"
        
        mock_provider = Mock()
        mock_provider.get_margin_used.return_value = 96000
        mock_provider.get_margin_available.return_value = 4000
        
        monitor = DoomsdayMonitor(
            lock_file=lock_file,
            portfolio_provider=mock_provider
        )
        
        risk = monitor.get_margin_risk_ratio()
        
        assert risk == 96.0
        mock_provider.get_margin_used.assert_called_once()
        mock_provider.get_margin_available.assert_called_once()


class TestTriggerDoomsdayExceptionHandling:
    """触发末日开关异常处理测试"""
    
    @pytest.mark.asyncio
    async def test_trigger_with_trading_engine_exception(self, tmp_path):
        """测试交易引擎异常处理"""
        lock_file = tmp_path / ".doomsday.lock"
        mock_engine = AsyncMock()
        mock_engine.cancel_all_orders.side_effect = Exception("取消订单失败")
        mock_engine.close_all_positions.side_effect = Exception("平仓失败")
        mock_engine.emergency_stop.side_effect = Exception("紧急停止失败")
        
        monitor = DoomsdayMonitor(
            lock_file=lock_file,
            trading_engine=mock_engine
        )
        
        # 应该不抛出异常，只记录日志
        event = await monitor.trigger_doomsday(reason="测试异常处理")
        
        assert event is not None
        assert monitor.is_triggered
    
    @pytest.mark.asyncio
    async def test_trigger_with_notification_exception(self, tmp_path):
        """测试通知管理器异常处理"""
        lock_file = tmp_path / ".doomsday.lock"
        mock_notifier = AsyncMock()
        mock_notifier.send_alert.side_effect = Exception("发送通知失败")
        
        monitor = DoomsdayMonitor(
            lock_file=lock_file,
            notification_manager=mock_notifier
        )
        
        event = await monitor.trigger_doomsday(reason="测试通知异常")
        
        assert event is not None
        assert monitor.is_triggered
    
    @pytest.mark.asyncio
    async def test_trigger_with_audit_logger_exception(self, tmp_path):
        """测试审计日志异常处理"""
        lock_file = tmp_path / ".doomsday.lock"
        mock_logger = Mock()
        mock_logger.log_event.side_effect = Exception("记录日志失败")
        
        monitor = DoomsdayMonitor(
            lock_file=lock_file,
            audit_logger=mock_logger
        )
        
        event = await monitor.trigger_doomsday(reason="测试日志异常")
        
        assert event is not None
        assert monitor.is_triggered
    
    @pytest.mark.asyncio
    async def test_trigger_callback_exception(self, tmp_path):
        """测试回调异常处理"""
        lock_file = tmp_path / ".doomsday.lock"
        monitor = DoomsdayMonitor(lock_file=lock_file)
        
        def failing_callback(event):
            raise Exception("回调失败")
        
        monitor.register_callback(failing_callback)
        
        # 应该不抛出异常
        event = await monitor.trigger_doomsday(reason="测试回调异常")
        
        assert event is not None
        assert monitor.is_triggered
