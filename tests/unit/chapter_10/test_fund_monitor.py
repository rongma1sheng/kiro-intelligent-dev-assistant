"""资金监控器单元测试

白皮书依据: 第十章 10.2 资金监控系统
"""

import pytest
from unittest.mock import Mock, patch

from src.core.fund_monitor import (
    FundMonitor,
    AlertLevel,
    FundStatus
)


class TestAlertLevel:
    """AlertLevel枚举测试"""
    
    def test_alert_level_values(self):
        """测试告警级别枚举值"""
        assert AlertLevel.NORMAL == "normal"
        assert AlertLevel.WARNING == "warning"
        assert AlertLevel.DANGER == "danger"
        assert AlertLevel.CRITICAL == "critical"


class TestFundStatus:
    """FundStatus数据类测试"""
    
    def test_fund_status_creation(self):
        """测试FundStatus创建"""
        status = FundStatus(
            current_equity=100000.0,
            daily_pnl=-3000.0,
            daily_pnl_pct=-3.0,
            drawdown=5.0,
            alert_level=AlertLevel.WARNING
        )
        
        assert status.current_equity == 100000.0
        assert status.daily_pnl == -3000.0
        assert status.daily_pnl_pct == -3.0
        assert status.drawdown == 5.0
        assert status.alert_level == AlertLevel.WARNING


class TestFundMonitor:
    """FundMonitor单元测试"""
    
    def test_init_valid_parameters(self):
        """测试有效参数初始化"""
        monitor = FundMonitor(
            initial_equity=100000.0,
            check_interval=60
        )
        
        assert monitor.initial_equity == 100000.0
        assert monitor.check_interval == 60
        assert monitor.peak_equity == 100000.0
    
    def test_init_invalid_initial_equity_zero(self):
        """测试无效初始权益（零）"""
        with pytest.raises(ValueError, match="初始权益必须 > 0"):
            FundMonitor(initial_equity=0)
    
    def test_init_invalid_initial_equity_negative(self):
        """测试无效初始权益（负数）"""
        with pytest.raises(ValueError, match="初始权益必须 > 0"):
            FundMonitor(initial_equity=-1000.0)
    
    def test_init_invalid_check_interval_zero(self):
        """测试无效检查间隔（零）"""
        with pytest.raises(ValueError, match="检查间隔必须 > 0"):
            FundMonitor(initial_equity=100000.0, check_interval=0)
    
    def test_init_invalid_check_interval_negative(self):
        """测试无效检查间隔（负数）"""
        with pytest.raises(ValueError, match="检查间隔必须 > 0"):
            FundMonitor(initial_equity=100000.0, check_interval=-10)
    
    def test_check_fund_status_invalid_equity(self):
        """测试检查资金状态时权益无效"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        with pytest.raises(ValueError, match="当前权益必须 > 0"):
            monitor.check_fund_status(current_equity=0)
        
        with pytest.raises(ValueError, match="当前权益必须 > 0"):
            monitor.check_fund_status(current_equity=-1000.0)
    
    def test_check_fund_status_profit(self):
        """测试盈利状态"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        status = monitor.check_fund_status(current_equity=105000.0)
        
        assert status.current_equity == 105000.0
        assert status.daily_pnl == 5000.0
        assert status.daily_pnl_pct == pytest.approx(5.0)
        assert status.drawdown == 0.0
        assert status.alert_level == AlertLevel.NORMAL
    
    def test_check_fund_status_small_loss(self):
        """测试小额亏损（<3%）"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        status = monitor.check_fund_status(current_equity=98000.0)
        
        assert status.current_equity == 98000.0
        assert status.daily_pnl == -2000.0
        assert status.daily_pnl_pct == pytest.approx(-2.0)
        assert status.drawdown == pytest.approx(2.0)
        assert status.alert_level == AlertLevel.NORMAL
    
    def test_check_fund_status_warning_loss(self):
        """测试WARNING级别亏损（>3%）"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        status = monitor.check_fund_status(current_equity=96500.0)
        
        assert status.current_equity == 96500.0
        assert status.daily_pnl == -3500.0
        assert status.daily_pnl_pct == pytest.approx(-3.5)
        assert status.drawdown == pytest.approx(3.5)
        assert status.alert_level == AlertLevel.WARNING
    
    def test_check_fund_status_danger_loss(self):
        """测试DANGER级别亏损（>5%）"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        status = monitor.check_fund_status(current_equity=94000.0)
        
        assert status.current_equity == 94000.0
        assert status.daily_pnl == -6000.0
        assert status.daily_pnl_pct == pytest.approx(-6.0)
        assert status.drawdown == pytest.approx(6.0)
        assert status.alert_level == AlertLevel.DANGER
    
    def test_check_fund_status_critical_loss(self):
        """测试CRITICAL级别亏损（>8%）"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        status = monitor.check_fund_status(current_equity=91000.0)
        
        assert status.current_equity == 91000.0
        assert status.daily_pnl == -9000.0
        assert status.daily_pnl_pct == pytest.approx(-9.0)
        assert status.drawdown == pytest.approx(9.0)
        assert status.alert_level == AlertLevel.CRITICAL
    
    def test_check_fund_status_peak_equity_update(self):
        """测试峰值权益更新"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        # 第1次检查：盈利到105000
        status1 = monitor.check_fund_status(current_equity=105000.0)
        assert monitor.peak_equity == 105000.0
        assert status1.drawdown == 0.0
        
        # 第2次检查：回撤到102000
        status2 = monitor.check_fund_status(current_equity=102000.0)
        assert monitor.peak_equity == 105000.0  # 峰值不变
        # 回撤 = (105000 - 102000) / 105000 * 100 = 2.857%
        assert status2.drawdown == pytest.approx(2.857, rel=0.01)
        assert status2.alert_level == AlertLevel.NORMAL
        
        # 第3次检查：继续盈利到108000
        status3 = monitor.check_fund_status(current_equity=108000.0)
        assert monitor.peak_equity == 108000.0  # 峰值更新
        assert status3.drawdown == 0.0
    
    def test_check_fund_status_warning_by_drawdown(self):
        """测试通过回撤触发WARNING（>10%回撤）"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        # 先盈利到110000，建立峰值
        monitor.check_fund_status(current_equity=110000.0)
        assert monitor.peak_equity == 110000.0
        
        # 回撤到98000
        # 回撤 = (110000 - 98000) / 110000 * 100 = 10.909%
        status = monitor.check_fund_status(current_equity=98000.0)
        assert status.drawdown == pytest.approx(10.909, rel=0.01)
        assert status.alert_level == AlertLevel.WARNING
    
    def test_check_fund_status_danger_by_drawdown(self):
        """测试通过回撤触发DANGER（>15%回撤）"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        # 先盈利到120000，建立峰值
        monitor.check_fund_status(current_equity=120000.0)
        assert monitor.peak_equity == 120000.0
        
        # 回撤到100000
        # 回撤 = (120000 - 100000) / 120000 * 100 = 16.667%
        status = monitor.check_fund_status(current_equity=100000.0)
        assert status.drawdown == pytest.approx(16.667, rel=0.01)
        assert status.alert_level == AlertLevel.DANGER
    
    def test_check_fund_status_critical_by_drawdown(self):
        """测试通过回撤触发CRITICAL（>20%回撤）"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        # 先盈利到125000，建立峰值
        monitor.check_fund_status(current_equity=125000.0)
        assert monitor.peak_equity == 125000.0
        
        # 回撤到98000
        # 回撤 = (125000 - 98000) / 125000 * 100 = 21.6%
        status = monitor.check_fund_status(current_equity=98000.0)
        assert status.drawdown == pytest.approx(21.6, rel=0.01)
        assert status.alert_level == AlertLevel.CRITICAL
    
    def test_determine_alert_level_normal_profit(self):
        """测试正常盈利状态"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        level = monitor.determine_alert_level(
            daily_pnl_pct=5.0,  # 盈利5%
            drawdown=0.0
        )
        
        assert level == AlertLevel.NORMAL
    
    def test_determine_alert_level_normal_small_loss(self):
        """测试正常小额亏损"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        level = monitor.determine_alert_level(
            daily_pnl_pct=-2.0,  # 亏损2%
            drawdown=2.0
        )
        
        assert level == AlertLevel.NORMAL
    
    def test_determine_alert_level_warning_by_loss(self):
        """测试通过亏损触发WARNING（>3%）"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        level = monitor.determine_alert_level(
            daily_pnl_pct=-3.5,  # 亏损3.5%
            drawdown=3.5
        )
        
        assert level == AlertLevel.WARNING
    
    def test_determine_alert_level_warning_by_drawdown(self):
        """测试通过回撤触发WARNING（>10%）"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        level = monitor.determine_alert_level(
            daily_pnl_pct=2.0,  # 盈利2%（但有回撤）
            drawdown=11.0  # 回撤11%
        )
        
        assert level == AlertLevel.WARNING
    
    def test_determine_alert_level_warning_boundary(self):
        """测试WARNING边界条件"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        # 刚好3%亏损
        level1 = monitor.determine_alert_level(
            daily_pnl_pct=-3.0,
            drawdown=0.0
        )
        assert level1 == AlertLevel.NORMAL
        
        # 刚好超过3%亏损
        level2 = monitor.determine_alert_level(
            daily_pnl_pct=-3.01,
            drawdown=0.0
        )
        assert level2 == AlertLevel.WARNING
        
        # 刚好10%回撤
        level3 = monitor.determine_alert_level(
            daily_pnl_pct=0.0,
            drawdown=10.0
        )
        assert level3 == AlertLevel.NORMAL
        
        # 刚好超过10%回撤
        level4 = monitor.determine_alert_level(
            daily_pnl_pct=0.0,
            drawdown=10.01
        )
        assert level4 == AlertLevel.WARNING
    
    def test_determine_alert_level_danger_by_loss(self):
        """测试通过亏损触发DANGER（>5%）"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        level = monitor.determine_alert_level(
            daily_pnl_pct=-5.5,  # 亏损5.5%
            drawdown=5.5
        )
        
        assert level == AlertLevel.DANGER
    
    def test_determine_alert_level_danger_by_drawdown(self):
        """测试通过回撤触发DANGER（>15%）"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        level = monitor.determine_alert_level(
            daily_pnl_pct=0.0,
            drawdown=16.0  # 回撤16%
        )
        
        assert level == AlertLevel.DANGER
    
    def test_determine_alert_level_danger_boundary(self):
        """测试DANGER边界条件"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        # 刚好5%亏损
        level1 = monitor.determine_alert_level(
            daily_pnl_pct=-5.0,
            drawdown=0.0
        )
        assert level1 == AlertLevel.WARNING
        
        # 刚好超过5%亏损
        level2 = monitor.determine_alert_level(
            daily_pnl_pct=-5.01,
            drawdown=0.0
        )
        assert level2 == AlertLevel.DANGER
        
        # 刚好15%回撤
        level3 = monitor.determine_alert_level(
            daily_pnl_pct=0.0,
            drawdown=15.0
        )
        assert level3 == AlertLevel.WARNING
        
        # 刚好超过15%回撤
        level4 = monitor.determine_alert_level(
            daily_pnl_pct=0.0,
            drawdown=15.01
        )
        assert level4 == AlertLevel.DANGER
    
    def test_determine_alert_level_critical_by_loss(self):
        """测试通过亏损触发CRITICAL（>8%）"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        level = monitor.determine_alert_level(
            daily_pnl_pct=-9.0,  # 亏损9%
            drawdown=9.0
        )
        
        assert level == AlertLevel.CRITICAL
    
    def test_determine_alert_level_critical_by_drawdown(self):
        """测试通过回撤触发CRITICAL（>20%）"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        level = monitor.determine_alert_level(
            daily_pnl_pct=0.0,
            drawdown=22.0  # 回撤22%
        )
        
        assert level == AlertLevel.CRITICAL
    
    def test_determine_alert_level_critical_boundary(self):
        """测试CRITICAL边界条件"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        # 刚好8%亏损
        level1 = monitor.determine_alert_level(
            daily_pnl_pct=-8.0,
            drawdown=0.0
        )
        assert level1 == AlertLevel.DANGER
        
        # 刚好超过8%亏损
        level2 = monitor.determine_alert_level(
            daily_pnl_pct=-8.01,
            drawdown=0.0
        )
        assert level2 == AlertLevel.CRITICAL
        
        # 刚好20%回撤
        level3 = monitor.determine_alert_level(
            daily_pnl_pct=0.0,
            drawdown=20.0
        )
        assert level3 == AlertLevel.DANGER
        
        # 刚好超过20%回撤
        level4 = monitor.determine_alert_level(
            daily_pnl_pct=0.0,
            drawdown=20.01
        )
        assert level4 == AlertLevel.CRITICAL
    
    def test_determine_alert_level_takes_max(self):
        """测试告警级别取最高级"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        # 亏损4%（WARNING）+ 回撤18%（DANGER）= DANGER
        level = monitor.determine_alert_level(
            daily_pnl_pct=-4.0,
            drawdown=18.0
        )
        assert level == AlertLevel.DANGER
        
        # 亏损6%（DANGER）+ 回撤25%（CRITICAL）= CRITICAL
        level = monitor.determine_alert_level(
            daily_pnl_pct=-6.0,
            drawdown=25.0
        )
        assert level == AlertLevel.CRITICAL
    
    @patch('src.core.fund_monitor.logger')
    def test_trigger_emergency_lockdown(self, mock_logger):
        """测试触发紧急锁定"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        monitor.trigger_emergency_lockdown()
        
        # 验证日志记录
        assert mock_logger.critical.call_count >= 4
        mock_logger.critical.assert_any_call("触发紧急锁定！")
    
    @patch('src.core.fund_monitor.logger')
    def test_handle_alert_normal(self, mock_logger):
        """测试处理NORMAL告警"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        status = FundStatus(
            current_equity=105000.0,
            daily_pnl=5000.0,
            daily_pnl_pct=5.0,
            drawdown=0.0,
            alert_level=AlertLevel.NORMAL
        )
        
        monitor._handle_alert(status)
        
        # 验证info日志（logger.info会被调用2次：1次在__init__，1次在_handle_alert）
        assert mock_logger.info.call_count == 2
        # 检查最后一次调用
        assert "资金状态正常" in mock_logger.info.call_args[0][0]
    
    @patch('src.core.fund_monitor.logger')
    def test_handle_alert_warning(self, mock_logger):
        """测试处理WARNING告警"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        status = FundStatus(
            current_equity=96000.0,
            daily_pnl=-4000.0,
            daily_pnl_pct=-4.0,
            drawdown=4.0,
            alert_level=AlertLevel.WARNING
        )
        
        monitor._handle_alert(status)
        
        # 验证warning日志
        mock_logger.warning.assert_called_once()
        assert "资金告警 [WARNING]" in mock_logger.warning.call_args[0][0]
    
    @patch('src.core.fund_monitor.logger')
    def test_handle_alert_danger(self, mock_logger):
        """测试处理DANGER告警"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        status = FundStatus(
            current_equity=94000.0,
            daily_pnl=-6000.0,
            daily_pnl_pct=-6.0,
            drawdown=6.0,
            alert_level=AlertLevel.DANGER
        )
        
        monitor._handle_alert(status)
        
        # 验证error日志
        assert mock_logger.error.call_count >= 2
        assert "资金告警 [DANGER]" in mock_logger.error.call_args_list[0][0][0]
        assert "发送微信告警 + 暂停新仓位" in mock_logger.error.call_args_list[1][0][0]
    
    @patch('src.core.fund_monitor.logger')
    def test_handle_alert_critical(self, mock_logger):
        """测试处理CRITICAL告警"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        status = FundStatus(
            current_equity=90000.0,
            daily_pnl=-10000.0,
            daily_pnl_pct=-10.0,
            drawdown=10.0,
            alert_level=AlertLevel.CRITICAL
        )
        
        monitor._handle_alert(status)
        
        # 验证critical日志
        assert mock_logger.critical.call_count >= 2
        assert "资金告警 [CRITICAL]" in mock_logger.critical.call_args_list[0][0][0]
    
    @patch('src.core.fund_monitor.logger')
    def test_check_fund_status_calls_handle_alert(self, mock_logger):
        """测试check_fund_status调用_handle_alert"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        # 触发DANGER告警
        status = monitor.check_fund_status(current_equity=94000.0)
        
        assert status.alert_level == AlertLevel.DANGER
        # 验证_handle_alert被调用（通过日志验证）
        assert mock_logger.error.call_count >= 2
    
    def test_multiple_checks_scenario(self):
        """测试多次检查场景"""
        monitor = FundMonitor(initial_equity=100000.0)
        
        # 第1天：盈利5%
        status1 = monitor.check_fund_status(current_equity=105000.0)
        assert status1.alert_level == AlertLevel.NORMAL
        assert monitor.peak_equity == 105000.0
        
        # 第2天：回撤到102000（回撤2.857%，盈亏+2%）
        status2 = monitor.check_fund_status(current_equity=102000.0)
        assert status2.alert_level == AlertLevel.NORMAL
        assert monitor.peak_equity == 105000.0
        
        # 第3天：继续回撤到98000（回撤6.667%，盈亏-2%）
        status3 = monitor.check_fund_status(current_equity=98000.0)
        assert status3.alert_level == AlertLevel.NORMAL  # 还未达到WARNING
        assert monitor.peak_equity == 105000.0
        
        # 第4天：继续回撤到93000（回撤11.429%，盈亏-7%）
        # 注意：-7%亏损触发DANGER（>5%），回撤11.429%也触发WARNING（>10%），取最高级DANGER
        status4 = monitor.check_fund_status(current_equity=93000.0)
        assert status4.alert_level == AlertLevel.DANGER  # 亏损>5%触发DANGER
        assert monitor.peak_equity == 105000.0
        
        # 第5天：继续回撤到88000（回撤16.19%，盈亏-12%）
        status5 = monitor.check_fund_status(current_equity=88000.0)
        assert status5.alert_level == AlertLevel.CRITICAL  # 亏损>8%触发CRITICAL
        assert monitor.peak_equity == 105000.0
        
        # 第6天：反弹到95000（回撤9.524%，盈亏-5%）
        # 注意：-5%亏损 = loss_pct 5，刚好不触发DANGER（需要>5%），但触发WARNING（>3%）
        status6 = monitor.check_fund_status(current_equity=95000.0)
        assert status6.alert_level == AlertLevel.WARNING  # 亏损5%触发WARNING
        assert monitor.peak_equity == 105000.0
        
        # 第7天：继续反弹到97000（回撤7.619%，盈亏-3%）
        # 注意：-3%亏损刚好在WARNING边界，不触发（需要>3%）
        status7 = monitor.check_fund_status(current_equity=97000.0)
        assert status7.alert_level == AlertLevel.NORMAL  # 刚好在边界，未触发
        assert monitor.peak_equity == 105000.0
