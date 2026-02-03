"""
风控监控器单元测试

白皮书依据: 第一章 1.5.2 战争态任务调度
"""

import pytest
import time
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from src.risk.risk_monitor import (
    RiskMonitor,
    RiskLevel,
    AlertType,
    RiskAlert,
    Position,
    RiskConfig
)


class TestRiskLevel:
    """风险等级测试"""
    
    def test_level_values(self):
        """测试等级值"""
        assert RiskLevel.SAFE.value == "安全"
        assert RiskLevel.WARNING.value == "警告"
        assert RiskLevel.DANGER.value == "危险"
        assert RiskLevel.CRITICAL.value == "紧急"
        assert RiskLevel.DOOMSDAY.value == "末日"


class TestPosition:
    """持仓测试"""
    
    def test_update_price(self):
        """测试更新价格"""
        position = Position(
            symbol="000001.SZ",
            quantity=1000,
            cost_price=10.0
        )
        
        position.update_price(11.0)
        
        assert position.current_price == 11.0
        assert position.market_value == 11000.0
        assert position.pnl == 1000.0
        assert position.pnl_ratio == 0.1


class TestRiskConfig:
    """风控配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = RiskConfig()
        
        assert config.max_position_ratio == 0.20
        assert config.stop_loss_ratio == 0.08
        assert config.take_profit_ratio == 0.20
        assert config.doomsday_loss_ratio == 0.10


class TestRiskMonitor:
    """风控监控器测试"""
    
    @pytest.fixture
    def monitor(self, tmp_path):
        """创建监控器实例"""
        lock_path = tmp_path / "DOOMSDAY.lock"
        return RiskMonitor(
            total_capital=1000000.0,
            doomsday_lock_path=str(lock_path)
        )
    
    def test_init(self, monitor):
        """测试初始化"""
        assert monitor.total_capital == 1000000.0
        assert not monitor.is_running()
        assert monitor.get_risk_level() == RiskLevel.SAFE
    
    def test_init_invalid_capital(self, tmp_path):
        """测试无效资金"""
        with pytest.raises(ValueError):
            RiskMonitor(total_capital=0)
    
    def test_start_stop(self, monitor):
        """测试启动停止"""
        assert monitor.start()
        assert monitor.is_running()
        
        assert monitor.stop()
        assert not monitor.is_running()
    
    def test_update_position(self, monitor):
        """测试更新持仓"""
        monitor.update_position(
            symbol="000001.SZ",
            quantity=1000,
            cost_price=10.0,
            current_price=11.0
        )
        
        assert "000001.SZ" in monitor.positions
        assert monitor.positions["000001.SZ"].pnl == 1000.0
    
    def test_update_price(self, monitor):
        """测试更新价格"""
        monitor.update_position(
            symbol="000001.SZ",
            quantity=1000,
            cost_price=10.0,
            current_price=10.0
        )
        
        monitor.update_price("000001.SZ", 12.0)
        
        assert monitor.positions["000001.SZ"].current_price == 12.0
    
    def test_clear_position(self, monitor):
        """测试清仓"""
        monitor.update_position(
            symbol="000001.SZ",
            quantity=1000,
            cost_price=10.0,
            current_price=10.0
        )
        
        monitor.update_position(
            symbol="000001.SZ",
            quantity=0,
            cost_price=10.0,
            current_price=10.0
        )
        
        assert "000001.SZ" not in monitor.positions
    
    def test_stop_loss_alert(self, monitor):
        """测试止损告警"""
        alerts = []
        monitor.on_alert = lambda a: alerts.append(a)
        
        # 添加亏损持仓
        monitor.update_position(
            symbol="000001.SZ",
            quantity=1000,
            cost_price=10.0,
            current_price=9.0  # 亏损10%
        )
        
        monitor._check_risks()
        
        # 应该触发止损告警
        stop_loss_alerts = [a for a in alerts if a.alert_type == AlertType.STOP_LOSS]
        assert len(stop_loss_alerts) > 0
    
    def test_take_profit_alert(self, monitor):
        """测试止盈告警"""
        alerts = []
        monitor.on_alert = lambda a: alerts.append(a)
        
        # 添加盈利持仓
        monitor.update_position(
            symbol="000001.SZ",
            quantity=1000,
            cost_price=10.0,
            current_price=12.5  # 盈利25%
        )
        
        monitor._check_risks()
        
        # 应该触发止盈告警
        take_profit_alerts = [a for a in alerts if a.alert_type == AlertType.TAKE_PROFIT]
        assert len(take_profit_alerts) > 0
    
    def test_daily_loss_alert(self, monitor):
        """测试日亏损告警"""
        alerts = []
        monitor.on_alert = lambda a: alerts.append(a)
        
        # 设置日亏损
        monitor.update_daily_pnl(-60000)  # 亏损6%
        
        monitor._check_risks()
        
        # 应该触发日亏损告警
        daily_loss_alerts = [a for a in alerts if a.alert_type == AlertType.DAILY_LOSS]
        assert len(daily_loss_alerts) > 0
    
    def test_doomsday_trigger(self, monitor):
        """测试末日开关触发"""
        doomsday_called = []
        monitor.on_doomsday = lambda reason: doomsday_called.append(reason)
        
        # 设置超过10%的日亏损
        monitor.update_daily_pnl(-110000)  # 亏损11%
        
        monitor._check_risks()
        
        assert monitor.is_doomsday_triggered()
        assert len(doomsday_called) > 0
    
    def test_doomsday_file_trigger(self, monitor, tmp_path):
        """测试末日开关文件触发"""
        # 创建锁文件
        lock_path = Path(monitor.doomsday_lock_path)
        lock_path.write_text("DOOMSDAY")
        
        monitor._check_risks()
        
        assert monitor.is_doomsday_triggered()
    
    def test_reset_doomsday(self, monitor):
        """测试重置末日开关"""
        # 触发末日开关
        monitor._trigger_doomsday("测试")
        assert monitor.is_doomsday_triggered()
        
        # 重置
        assert monitor.reset_doomsday()
        assert not monitor.is_doomsday_triggered()
    
    def test_get_alerts(self, monitor):
        """测试获取告警"""
        monitor._create_alert(
            AlertType.POSITION_LIMIT,
            RiskLevel.WARNING,
            "测试告警"
        )
        
        alerts = monitor.get_alerts()
        assert len(alerts) == 1
        assert alerts[0].message == "测试告警"
    
    def test_get_risk_level(self, monitor):
        """测试获取风险等级"""
        assert monitor.get_risk_level() == RiskLevel.SAFE
        
        # 创建危险告警
        monitor._create_alert(
            AlertType.STOP_LOSS,
            RiskLevel.DANGER,
            "止损触发"
        )
        
        assert monitor.get_risk_level() == RiskLevel.DANGER


class TestRiskMonitorIntegration:
    """集成测试"""
    
    def test_full_monitoring_cycle(self, tmp_path):
        """测试完整监控周期"""
        lock_path = tmp_path / "DOOMSDAY.lock"
        monitor = RiskMonitor(
            total_capital=1000000.0,
            doomsday_lock_path=str(lock_path)
        )
        
        # 启动
        monitor.start()
        assert monitor.is_running()
        
        # 添加持仓
        monitor.update_position(
            symbol="000001.SZ",
            quantity=1000,
            cost_price=10.0,
            current_price=10.5
        )
        
        # 等待检查
        time.sleep(1.5)
        
        # 获取风险等级
        level = monitor.get_risk_level()
        assert level in [RiskLevel.SAFE, RiskLevel.WARNING]
        
        # 停止
        monitor.stop()
        assert not monitor.is_running()
