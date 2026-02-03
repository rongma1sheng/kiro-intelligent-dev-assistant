"""Margin Watchdog单元测试

白皮书依据: 第六章 5.4 风险门闸
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.execution.margin_watchdog import (
    MarginWatchdog,
    MarginWatchdogConfig,
    MarginWatchdogState,
    MarginPosition,
    RiskLevel
)


@pytest.fixture
def watchdog_config():
    """Watchdog配置fixture"""
    return MarginWatchdogConfig(
        max_margin_ratio=0.30,
        warning_risk_ratio=0.50,
        danger_risk_ratio=0.70,
        critical_risk_ratio=0.85,
        monitor_interval=5,
        auto_liquidation_enabled=True
    )


@pytest.fixture
def watchdog(watchdog_config):
    """Watchdog实例fixture"""
    return MarginWatchdog(config=watchdog_config)


class TestMarginWatchdogConfig:
    """Watchdog配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = MarginWatchdogConfig()
        
        assert config.max_margin_ratio == 0.30
        assert config.critical_risk_ratio == 0.85
        assert config.auto_liquidation_enabled is True
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = MarginWatchdogConfig(
            max_margin_ratio=0.25,
            critical_risk_ratio=0.90,
            auto_liquidation_enabled=False
        )
        
        assert config.max_margin_ratio == 0.25
        assert config.critical_risk_ratio == 0.90
        assert config.auto_liquidation_enabled is False


class TestRiskLevel:
    """风险等级测试"""
    
    def test_risk_levels(self):
        """测试风险等级枚举"""
        assert RiskLevel.SAFE.value == "safe"
        assert RiskLevel.WARNING.value == "warning"
        assert RiskLevel.DANGER.value == "danger"
        assert RiskLevel.CRITICAL.value == "critical"


class TestMarginPosition:
    """保证金持仓测试"""
    
    def test_create_position(self):
        """测试创建持仓"""
        position = MarginPosition(
            symbol='IC2401',
            position_type='futures',
            quantity=10,
            margin_required=100000,
            market_value=500000,
            unrealized_pnl=5000,
            risk_contribution=0.2
        )
        
        assert position.symbol == 'IC2401'
        assert position.position_type == 'futures'
        assert position.margin_required == 100000


class TestMarginWatchdog:
    """Margin Watchdog测试"""
    
    def test_init(self, watchdog):
        """测试初始化"""
        assert watchdog.config.max_margin_ratio == 0.30
        assert watchdog.state.risk_level == RiskLevel.SAFE
        assert watchdog._monitoring is False
    
    def test_calculate_risk_level_safe(self, watchdog):
        """测试安全风险等级"""
        level = watchdog._calculate_risk_level(0.30)
        assert level == RiskLevel.SAFE
    
    def test_calculate_risk_level_warning(self, watchdog):
        """测试警告风险等级"""
        level = watchdog._calculate_risk_level(0.55)
        assert level == RiskLevel.WARNING
    
    def test_calculate_risk_level_danger(self, watchdog):
        """测试危险风险等级"""
        level = watchdog._calculate_risk_level(0.75)
        assert level == RiskLevel.DANGER
    
    def test_calculate_risk_level_critical(self, watchdog):
        """测试临界风险等级"""
        level = watchdog._calculate_risk_level(0.90)
        assert level == RiskLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_check_margin_risk_safe(self, watchdog):
        """测试安全状态检查"""
        account_data = {
            'total_assets': 1000000,
            'margin_used': 100000,
            'margin_available': 200000,
            'derivative_positions': []
        }
        
        result = await watchdog.check_margin_risk(account_data)
        
        assert result['success'] is True
        assert result['margin_ratio'] == 0.1  # 100000 / 1000000
        assert result['risk_level'] == 'safe'
    
    @pytest.mark.asyncio
    async def test_check_margin_risk_warning(self, watchdog):
        """测试警告状态检查"""
        account_data = {
            'total_assets': 1000000,
            'margin_used': 150000,
            'margin_available': 100000,  # risk_ratio = 150000 / 250000 = 0.6
            'derivative_positions': []
        }
        
        result = await watchdog.check_margin_risk(account_data)
        
        assert result['success'] is True
        assert result['risk_level'] == 'warning'
    
    @pytest.mark.asyncio
    async def test_check_margin_risk_critical_triggers_liquidation(self, watchdog):
        """测试临界状态触发强制平仓"""
        watchdog.config.auto_liquidation_enabled = True
        
        account_data = {
            'total_assets': 1000000,
            'margin_used': 180000,
            'margin_available': 20000,  # risk_ratio = 180000 / 200000 = 0.9
            'derivative_positions': [
                {
                    'symbol': 'IC2401',
                    'type': 'futures',
                    'quantity': 10,
                    'margin_required': 100000,
                    'market_value': 500000,
                    'unrealized_pnl': -5000,
                    'risk_contribution': 0.5
                }
            ]
        }
        
        with patch.object(watchdog, '_execute_forced_liquidation', new_callable=AsyncMock) as mock_liquidate:
            mock_liquidate.return_value = {'success': True, 'liquidation_count': 1}
            result = await watchdog.check_margin_risk(account_data)
        
        assert result['risk_level'] == 'critical'
        mock_liquidate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_margin_risk_zero_assets(self, watchdog):
        """测试总资产为0"""
        account_data = {
            'total_assets': 0,
            'margin_used': 0,
            'margin_available': 0,
            'derivative_positions': []
        }
        
        result = await watchdog.check_margin_risk(account_data)
        
        assert result['success'] is False
        assert '总资产为0' in result['message']
    
    def test_sort_positions_by_priority(self, watchdog):
        """测试持仓优先级排序"""
        watchdog.state.positions = [
            MarginPosition('STOCK1', 'margin_stock', 100, 10000, 50000, 0, 0.1),
            MarginPosition('OPT1', 'option', 10, 5000, 10000, 0, 0.3),
            MarginPosition('FUT1', 'futures', 5, 50000, 100000, 0, 0.2),
        ]
        
        sorted_positions = watchdog._sort_positions_by_priority()
        
        # 期权应该排在最前面（优先平仓）
        assert sorted_positions[0].position_type == 'option'
        assert sorted_positions[1].position_type == 'futures'
        assert sorted_positions[2].position_type == 'margin_stock'
    
    @pytest.mark.asyncio
    async def test_liquidate_position_simulation(self, watchdog):
        """测试模拟平仓"""
        position = MarginPosition(
            symbol='IC2401',
            position_type='futures',
            quantity=10,
            margin_required=100000,
            market_value=500000,
            unrealized_pnl=-5000,
            risk_contribution=0.5
        )
        
        result = await watchdog._liquidate_position(position)
        
        assert result['success'] is True
        assert result['symbol'] == 'IC2401'
        assert result['quantity'] == 10
    
    def test_get_state(self, watchdog):
        """测试获取状态"""
        state = watchdog.get_state()
        
        assert 'margin_ratio' in state
        assert 'risk_ratio' in state
        assert 'risk_level' in state
        assert 'monitoring' in state
        assert 'config' in state
    
    def test_get_alert_history(self, watchdog):
        """测试获取告警历史"""
        history = watchdog.get_alert_history()
        assert history == []
    
    def test_get_liquidation_history(self, watchdog):
        """测试获取平仓历史"""
        history = watchdog.get_liquidation_history()
        assert history == []
    
    def test_reset_state(self, watchdog):
        """测试重置状态"""
        watchdog.state.current_risk_ratio = 0.8
        watchdog.state.risk_level = RiskLevel.DANGER
        
        watchdog.reset_state()
        
        assert watchdog.state.current_risk_ratio == 0.0
        assert watchdog.state.risk_level == RiskLevel.SAFE
    
    @pytest.mark.asyncio
    async def test_send_alert(self, watchdog):
        """测试发送告警"""
        alert_received = []
        
        def alert_callback(alert_data):
            alert_received.append(alert_data)
        
        watchdog.alert_callback = alert_callback
        
        await watchdog._send_alert({
            'type': 'test_alert',
            'message': '测试告警'
        })
        
        assert len(alert_received) == 1
        assert alert_received[0]['type'] == 'test_alert'
        assert len(watchdog.state.alert_history) == 1
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, watchdog):
        """测试启动和停止监控"""
        assert watchdog._monitoring is False
        
        # 启动监控
        await watchdog.start_monitoring()
        assert watchdog._monitoring is True
        
        # 等待一小段时间
        await asyncio.sleep(0.1)
        
        # 停止监控
        await watchdog.stop_monitoring()
        assert watchdog._monitoring is False


class TestMarginWatchdogRiskLevelTransitions:
    """风险等级转换测试
    
    白皮书依据: 第六章 5.4 风险门闸
    测试需求: Requirements 12.3
    """
    
    @pytest.mark.asyncio
    async def test_risk_level_safe_to_warning(self, watchdog):
        """测试从安全到警告的转换"""
        alert_received = []
        watchdog.alert_callback = lambda alert: alert_received.append(alert)
        
        # 初始状态：安全
        account_data_safe = {
            'total_assets': 1000000,
            'margin_used': 100000,
            'margin_available': 200000,  # risk_ratio = 100000/300000 = 0.33
            'derivative_positions': []
        }
        await watchdog.check_margin_risk(account_data_safe)
        assert watchdog.state.risk_level == RiskLevel.SAFE
        
        # 转换到警告
        account_data_warning = {
            'total_assets': 1000000,
            'margin_used': 150000,
            'margin_available': 100000,  # risk_ratio = 150000/250000 = 0.6
            'derivative_positions': []
        }
        await watchdog.check_margin_risk(account_data_warning)
        
        assert watchdog.state.risk_level == RiskLevel.WARNING
        assert len(alert_received) > 0
        assert any(a['type'] == 'risk_level_change' for a in alert_received)
    
    @pytest.mark.asyncio
    async def test_risk_level_warning_to_danger(self, watchdog):
        """测试从警告到危险的转换"""
        alert_received = []
        watchdog.alert_callback = lambda alert: alert_received.append(alert)
        
        # 初始状态：警告
        account_data_warning = {
            'total_assets': 1000000,
            'margin_used': 150000,
            'margin_available': 100000,  # risk_ratio = 0.6
            'derivative_positions': []
        }
        await watchdog.check_margin_risk(account_data_warning)
        assert watchdog.state.risk_level == RiskLevel.WARNING
        
        # 转换到危险
        account_data_danger = {
            'total_assets': 1000000,
            'margin_used': 175000,
            'margin_available': 75000,  # risk_ratio = 175000/250000 = 0.7
            'derivative_positions': []
        }
        await watchdog.check_margin_risk(account_data_danger)
        
        assert watchdog.state.risk_level == RiskLevel.DANGER
        assert len(alert_received) > 0
    
    @pytest.mark.asyncio
    async def test_risk_level_danger_to_critical(self, watchdog):
        """测试从危险到临界的转换"""
        watchdog.config.auto_liquidation_enabled = False  # 禁用自动平仓以便测试
        alert_received = []
        watchdog.alert_callback = lambda alert: alert_received.append(alert)
        
        # 初始状态：危险
        account_data_danger = {
            'total_assets': 1000000,
            'margin_used': 175000,
            'margin_available': 75000,  # risk_ratio = 0.7
            'derivative_positions': []
        }
        await watchdog.check_margin_risk(account_data_danger)
        assert watchdog.state.risk_level == RiskLevel.DANGER
        
        # 转换到临界
        account_data_critical = {
            'total_assets': 1000000,
            'margin_used': 190000,
            'margin_available': 10000,  # risk_ratio = 190000/200000 = 0.95
            'derivative_positions': []
        }
        await watchdog.check_margin_risk(account_data_critical)
        
        assert watchdog.state.risk_level == RiskLevel.CRITICAL
        assert len(alert_received) > 0
    
    @pytest.mark.asyncio
    async def test_risk_level_critical_to_danger(self, watchdog):
        """测试从临界回到危险（风险降低）"""
        watchdog.config.auto_liquidation_enabled = False
        alert_received = []
        watchdog.alert_callback = lambda alert: alert_received.append(alert)
        
        # 初始状态：临界
        account_data_critical = {
            'total_assets': 1000000,
            'margin_used': 190000,
            'margin_available': 10000,  # risk_ratio = 0.95
            'derivative_positions': []
        }
        await watchdog.check_margin_risk(account_data_critical)
        assert watchdog.state.risk_level == RiskLevel.CRITICAL
        
        # 回到危险
        account_data_danger = {
            'total_assets': 1000000,
            'margin_used': 175000,
            'margin_available': 75000,  # risk_ratio = 0.7
            'derivative_positions': []
        }
        await watchdog.check_margin_risk(account_data_danger)
        
        assert watchdog.state.risk_level == RiskLevel.DANGER
        assert len(alert_received) > 0


class TestMarginWatchdogMultiPositionLiquidation:
    """多持仓强制平仓测试
    
    白皮书依据: 第六章 5.4 风险门闸 - 风险度 > 85% 强制平仓
    测试需求: Requirements 12.4
    """
    
    @pytest.mark.asyncio
    async def test_liquidate_multiple_positions(self, watchdog):
        """测试多持仓强制平仓"""
        watchdog.state.positions = [
            MarginPosition('OPT1', 'option', 10, 50000, 100000, -5000, 0.3),
            MarginPosition('FUT1', 'futures', 5, 80000, 200000, -3000, 0.4),
            MarginPosition('STOCK1', 'margin_stock', 100, 30000, 150000, 2000, 0.2),
        ]
        watchdog.state.current_risk_ratio = 0.90
        
        liquidation_count = 0
        
        async def mock_liquidate(position):
            nonlocal liquidation_count
            liquidation_count += 1
            # 平仓3次后风险度降低
            if liquidation_count >= 3:
                watchdog.state.current_risk_ratio = 0.65
            return {'symbol': position.symbol, 'success': True}
        
        with patch.object(watchdog, '_liquidate_position', side_effect=mock_liquidate):
            with patch.object(watchdog, 'check_margin_risk', new_callable=AsyncMock):
                result = await watchdog._execute_forced_liquidation()
        
        assert result['success'] is True
        assert result['liquidation_count'] == 3
        assert len(watchdog.state.liquidation_history) == 1
    
    @pytest.mark.asyncio
    async def test_liquidation_stops_when_safe(self, watchdog):
        """测试风险降低后停止平仓"""
        watchdog.state.positions = [
            MarginPosition('OPT1', 'option', 10, 50000, 100000, -5000, 0.3),
            MarginPosition('FUT1', 'futures', 5, 80000, 200000, -3000, 0.4),
            MarginPosition('STOCK1', 'margin_stock', 100, 30000, 150000, 2000, 0.2),
        ]
        watchdog.state.current_risk_ratio = 0.90
        
        liquidation_count = 0
        
        async def mock_liquidate(position):
            nonlocal liquidation_count
            liquidation_count += 1
            # 第一次平仓后风险度降低
            if liquidation_count == 1:
                watchdog.state.current_risk_ratio = 0.65
            return {'symbol': position.symbol, 'success': True}
        
        with patch.object(watchdog, '_liquidate_position', side_effect=mock_liquidate):
            with patch.object(watchdog, 'check_margin_risk', new_callable=AsyncMock):
                result = await watchdog._execute_forced_liquidation()
        
        # 应该只平仓1个持仓就停止了
        assert liquidation_count == 1
        assert result['liquidation_count'] == 1
    
    @pytest.mark.asyncio
    async def test_liquidation_continues_on_error(self, watchdog):
        """测试平仓失败后继续平仓其他持仓"""
        watchdog.state.positions = [
            MarginPosition('OPT1', 'option', 10, 50000, 100000, -5000, 0.3),
            MarginPosition('FUT1', 'futures', 5, 80000, 200000, -3000, 0.4),
        ]
        watchdog.state.current_risk_ratio = 0.90
        
        call_count = 0
        
        async def mock_liquidate(position):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # 第一次平仓失败
                raise Exception("平仓失败")
            else:
                # 第二次平仓成功
                watchdog.state.current_risk_ratio = 0.65
                return {'symbol': position.symbol, 'success': True}
        
        with patch.object(watchdog, '_liquidate_position', side_effect=mock_liquidate):
            with patch.object(watchdog, 'check_margin_risk', new_callable=AsyncMock):
                result = await watchdog._execute_forced_liquidation()
        
        assert call_count == 2
        assert result['liquidation_count'] == 2
        # 一个成功，一个失败
        assert result['results'][0]['success'] is False
        assert result['results'][1]['success'] is True


class TestMarginWatchdogPositionPriority:
    """持仓优先级排序测试
    
    白皮书依据: 第六章 5.4 风险门闸
    测试需求: Requirements 12.5
    """
    
    def test_sort_by_type_priority(self, watchdog):
        """测试按类型优先级排序"""
        watchdog.state.positions = [
            MarginPosition('STOCK1', 'margin_stock', 100, 30000, 150000, 0, 0.2),
            MarginPosition('OPT1', 'option', 10, 50000, 100000, 0, 0.2),
            MarginPosition('FUT1', 'futures', 5, 80000, 200000, 0, 0.2),
        ]
        
        sorted_positions = watchdog._sort_positions_by_priority()
        
        # 期权 > 期货 > 融资融券
        assert sorted_positions[0].position_type == 'option'
        assert sorted_positions[1].position_type == 'futures'
        assert sorted_positions[2].position_type == 'margin_stock'
    
    def test_sort_by_risk_contribution(self, watchdog):
        """测试按风险贡献度排序（同类型）"""
        watchdog.state.positions = [
            MarginPosition('OPT1', 'option', 10, 50000, 100000, 0, 0.2),
            MarginPosition('OPT2', 'option', 20, 80000, 150000, 0, 0.5),
            MarginPosition('OPT3', 'option', 5, 30000, 50000, 0, 0.1),
        ]
        
        sorted_positions = watchdog._sort_positions_by_priority()
        
        # 风险贡献度高的优先：0.5 > 0.2 > 0.1
        assert sorted_positions[0].risk_contribution == 0.5
        assert sorted_positions[1].risk_contribution == 0.2
        assert sorted_positions[2].risk_contribution == 0.1
    
    def test_sort_mixed_priority(self, watchdog):
        """测试混合优先级排序"""
        watchdog.state.positions = [
            MarginPosition('STOCK1', 'margin_stock', 100, 30000, 150000, 0, 0.8),  # 高风险但低优先级
            MarginPosition('OPT1', 'option', 10, 50000, 100000, 0, 0.1),  # 低风险但高优先级
            MarginPosition('FUT1', 'futures', 5, 80000, 200000, 0, 0.5),
        ]
        
        sorted_positions = watchdog._sort_positions_by_priority()
        
        # 类型优先级优先于风险贡献度
        assert sorted_positions[0].position_type == 'option'
        assert sorted_positions[1].position_type == 'futures'
        assert sorted_positions[2].position_type == 'margin_stock'


class TestMarginWatchdogAlertCallback:
    """告警回调测试
    
    白皮书依据: 第六章 5.4 风险门闸
    测试需求: Requirements 12.6
    """
    
    @pytest.mark.asyncio
    async def test_alert_callback_called(self, watchdog):
        """测试告警回调被调用"""
        alert_received = []
        
        def alert_callback(alert_data):
            alert_received.append(alert_data)
        
        watchdog.alert_callback = alert_callback
        
        await watchdog._send_alert({
            'type': 'test_alert',
            'message': '测试告警'
        })
        
        assert len(alert_received) == 1
        assert alert_received[0]['type'] == 'test_alert'
        assert 'timestamp' in alert_received[0]
    
    @pytest.mark.asyncio
    async def test_alert_callback_exception_handling(self, watchdog):
        """测试告警回调异常处理"""
        def failing_callback(alert_data):
            raise Exception("回调失败")
        
        watchdog.alert_callback = failing_callback
        
        # 不应该抛出异常
        await watchdog._send_alert({
            'type': 'test_alert',
            'message': '测试告警'
        })
        
        # 告警历史应该仍然记录
        assert len(watchdog.state.alert_history) == 1
    
    @pytest.mark.asyncio
    async def test_multiple_alert_types(self, watchdog):
        """测试多种告警类型"""
        alert_received = []
        watchdog.alert_callback = lambda alert: alert_received.append(alert)
        
        # 风险等级变化告警
        await watchdog._send_alert({
            'type': 'risk_level_change',
            'old_level': 'safe',
            'new_level': 'warning',
            'message': '风险等级变化'
        })
        
        # 保证金比例超限告警
        await watchdog._send_alert({
            'type': 'margin_ratio_exceeded',
            'margin_ratio': 0.35,
            'threshold': 0.30,
            'message': '保证金比例超限'
        })
        
        # 强制平仓告警
        await watchdog._send_alert({
            'type': 'forced_liquidation',
            'positions_count': 3,
            'message': '强制平仓完成'
        })
        
        assert len(alert_received) == 3
        assert alert_received[0]['type'] == 'risk_level_change'
        assert alert_received[1]['type'] == 'margin_ratio_exceeded'
        assert alert_received[2]['type'] == 'forced_liquidation'


class TestMarginWatchdogMonitoringLifecycle:
    """监控生命周期测试
    
    白皮书依据: 第六章 5.4 风险门闸
    测试需求: Requirements 12.7
    """
    
    @pytest.mark.asyncio
    async def test_start_monitoring_twice(self, watchdog):
        """测试重复启动监控"""
        await watchdog.start_monitoring()
        assert watchdog._monitoring is True
        
        # 再次启动应该被忽略
        await watchdog.start_monitoring()
        assert watchdog._monitoring is True
        
        await watchdog.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring_when_not_running(self, watchdog):
        """测试停止未运行的监控"""
        assert watchdog._monitoring is False
        
        # 停止未运行的监控不应该报错
        await watchdog.stop_monitoring()
        assert watchdog._monitoring is False
    
    @pytest.mark.asyncio
    async def test_monitoring_loop_continues_on_error(self, watchdog):
        """测试监控循环在错误后继续运行"""
        check_count = 0
        
        async def mock_check(*args, **kwargs):
            nonlocal check_count
            check_count += 1
            if check_count == 1:
                raise Exception("检查失败")
            return {'success': True}
        
        with patch.object(watchdog, 'check_margin_risk', side_effect=mock_check):
            watchdog.config.monitor_interval = 0.1
            await watchdog.start_monitoring()
            
            # 等待至少2次检查
            await asyncio.sleep(0.3)
            
            await watchdog.stop_monitoring()
        
        # 应该至少执行了2次检查（第一次失败，第二次成功）
        assert check_count >= 2
    
    @pytest.mark.asyncio
    async def test_monitoring_state_persistence(self, watchdog):
        """测试监控状态持久化"""
        account_data = {
            'total_assets': 1000000,
            'margin_used': 150000,
            'margin_available': 100000,
            'derivative_positions': []
        }
        
        # 第一次检查
        await watchdog.check_margin_risk(account_data)
        first_check_time = watchdog.state.last_check_time
        
        # 等待一小段时间
        await asyncio.sleep(0.1)
        
        # 第二次检查
        await watchdog.check_margin_risk(account_data)
        second_check_time = watchdog.state.last_check_time
        
        # 检查时间应该不同
        assert first_check_time != second_check_time
        assert watchdog.state.current_risk_ratio == 0.6


class TestMarginWatchdogEdgeCases:
    """边界条件测试
    
    白皮书依据: 第六章 5.4 风险门闸
    测试需求: Requirements 12.8
    """
    
    @pytest.mark.asyncio
    async def test_zero_total_assets(self, watchdog):
        """测试总资产为0"""
        account_data = {
            'total_assets': 0,
            'margin_used': 0,
            'margin_available': 0,
            'derivative_positions': []
        }
        
        result = await watchdog.check_margin_risk(account_data)
        
        assert result['success'] is False
        assert '总资产为0' in result['message']
    
    @pytest.mark.asyncio
    async def test_negative_pnl(self, watchdog):
        """测试负盈亏"""
        account_data = {
            'total_assets': 1000000,
            'margin_used': 150000,
            'margin_available': 100000,
            'derivative_positions': [
                {
                    'symbol': 'IC2401',
                    'type': 'futures',
                    'quantity': 10,
                    'margin_required': 100000,
                    'market_value': 500000,
                    'unrealized_pnl': -50000,  # 负盈亏
                    'risk_contribution': 0.5
                }
            ]
        }
        
        result = await watchdog.check_margin_risk(account_data)
        
        assert result['success'] is True
        assert len(watchdog.state.positions) == 1
        assert watchdog.state.positions[0].unrealized_pnl == -50000
    
    @pytest.mark.asyncio
    async def test_empty_positions(self, watchdog):
        """测试空持仓"""
        account_data = {
            'total_assets': 1000000,
            'margin_used': 0,
            'margin_available': 300000,
            'derivative_positions': []
        }
        
        result = await watchdog.check_margin_risk(account_data)
        
        assert result['success'] is True
        assert result['positions_count'] == 0
        assert watchdog.state.risk_level == RiskLevel.SAFE
    
    @pytest.mark.asyncio
    async def test_zero_margin_available(self, watchdog):
        """测试可用保证金为0"""
        account_data = {
            'total_assets': 1000000,
            'margin_used': 200000,
            'margin_available': 0,  # 可用保证金为0
            'derivative_positions': []
        }
        
        result = await watchdog.check_margin_risk(account_data)
        
        assert result['success'] is True
        # risk_ratio = 200000 / 200000 = 1.0
        assert result['risk_ratio'] == 1.0
        assert watchdog.state.risk_level == RiskLevel.CRITICAL
    
    def test_sort_empty_positions(self, watchdog):
        """测试排序空持仓列表"""
        watchdog.state.positions = []
        
        sorted_positions = watchdog._sort_positions_by_priority()
        
        assert sorted_positions == []
    
    @pytest.mark.asyncio
    async def test_margin_ratio_exactly_at_threshold(self, watchdog):
        """测试保证金比例恰好在阈值"""
        account_data = {
            'total_assets': 1000000,
            'margin_used': 300000,  # 恰好30%
            'margin_available': 200000,
            'derivative_positions': []
        }
        
        result = await watchdog.check_margin_risk(account_data)
        
        assert result['success'] is True
        assert result['margin_ratio'] == 0.30
    
    @pytest.mark.asyncio
    async def test_risk_ratio_exactly_at_critical(self, watchdog):
        """测试风险度恰好在临界值"""
        watchdog.config.auto_liquidation_enabled = False
        
        account_data = {
            'total_assets': 1000000,
            'margin_used': 170000,
            'margin_available': 30000,  # risk_ratio = 170000/200000 = 0.85
            'derivative_positions': []
        }
        
        result = await watchdog.check_margin_risk(account_data)
        
        assert result['success'] is True
        assert result['risk_ratio'] == 0.85
        assert watchdog.state.risk_level == RiskLevel.CRITICAL
