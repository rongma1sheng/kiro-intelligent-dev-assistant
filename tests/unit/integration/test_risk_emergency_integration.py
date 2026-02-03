"""Unit tests for Risk Emergency Integration

白皮书依据: 第十九章 19.3 应急响应流程, 第十二章 12.3 末日开关与应急响应
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.integration.risk_emergency_integration import (
    RiskEmergencyIntegration,
    RiskEmergencyStatus,
    get_risk_emergency_integration
)
from src.risk.risk_identification_system import (
    RiskIdentificationSystem,
    RiskLevel,
    RiskEvent
)
from src.risk.emergency_response_system import (
    EmergencyResponseSystem,
    AlertLevel,
    EmergencyProcedure
)
from src.core.doomsday_switch import DoomsdaySwitch
from src.infra.cross_chapter_event_bus import (
    CrossChapterEventBus,
    CrossChapterEventType,
    CrossChapterEvent
)
from src.infra.event_bus import EventBus, EventPriority


class TestRiskEmergencyIntegration:
    """测试风险应急集成类"""
    
    @pytest.fixture
    def mock_risk_system(self):
        """创建模拟风险识别系统"""
        system = Mock(spec=RiskIdentificationSystem)
        system.get_overall_risk_level = Mock(return_value=RiskLevel.LOW)
        system.monitor_market_risk = Mock(return_value=None)
        system.monitor_system_risk = Mock(return_value=None)
        system.monitor_operational_risk = Mock(return_value=None)
        system.monitor_liquidity_risk = Mock(return_value=None)
        system.monitor_counterparty_risk = Mock(return_value=None)
        return system
    
    @pytest.fixture
    def mock_emergency_system(self):
        """创建模拟应急响应系统"""
        system = Mock(spec=EmergencyResponseSystem)
        system.trigger_alert = Mock(return_value=EmergencyProcedure(
            procedure_id='test_001',
            alert_level=AlertLevel.WARNING,
            description='Test alert',
            actions=['action1'],
            executed_at=datetime.now(),
            success=True
        ))
        system.get_emergency_history = Mock(return_value=[])
        system.emergency_history = []
        return system
    
    @pytest.fixture
    def mock_doomsday_switch(self):
        """创建模拟末日开关"""
        switch = Mock(spec=DoomsdaySwitch)
        switch.is_triggered = Mock(return_value=False)
        switch.check_triggers = Mock(return_value=[])
        switch.trigger = Mock()
        return switch
    
    @pytest.fixture
    def mock_event_bus(self):
        """创建模拟事件总线"""
        mock_base_bus = Mock(spec=EventBus)
        mock_base_bus.publish = AsyncMock(return_value=True)
        
        mock_cross_bus = Mock(spec=CrossChapterEventBus)
        mock_cross_bus.base_event_bus = mock_base_bus
        mock_cross_bus.publish = AsyncMock(return_value=True)
        
        return mock_cross_bus
    
    @pytest.fixture
    def integration(
        self,
        mock_risk_system,
        mock_emergency_system,
        mock_doomsday_switch,
        mock_event_bus
    ):
        """创建集成实例"""
        return RiskEmergencyIntegration(
            risk_system=mock_risk_system,
            emergency_system=mock_emergency_system,
            doomsday_switch=mock_doomsday_switch,
            event_bus=mock_event_bus,
            monitor_interval=60
        )
    
    def test_initialization(
        self,
        integration,
        mock_risk_system,
        mock_emergency_system,
        mock_doomsday_switch
    ):
        """测试初始化"""
        assert integration.risk_system == mock_risk_system
        assert integration.emergency_system == mock_emergency_system
        assert integration.doomsday_switch == mock_doomsday_switch
        assert integration.monitor_interval == 60
        
        # 验证风险等级映射
        assert integration._risk_to_alert_mapping[RiskLevel.LOW] is None
        assert integration._risk_to_alert_mapping[RiskLevel.MEDIUM] == AlertLevel.WARNING
        assert integration._risk_to_alert_mapping[RiskLevel.HIGH] == AlertLevel.DANGER
        assert integration._risk_to_alert_mapping[RiskLevel.CRITICAL] == AlertLevel.CRITICAL
    
    def test_initialization_invalid_params(self, mock_emergency_system, mock_doomsday_switch, mock_event_bus):
        """测试无效参数初始化"""
        with pytest.raises(ValueError, match="risk_system不能为None"):
            RiskEmergencyIntegration(
                risk_system=None,
                emergency_system=mock_emergency_system,
                doomsday_switch=mock_doomsday_switch,
                event_bus=mock_event_bus
            )
        
        with pytest.raises(ValueError, match="emergency_system不能为None"):
            RiskEmergencyIntegration(
                risk_system=Mock(),
                emergency_system=None,
                doomsday_switch=mock_doomsday_switch,
                event_bus=mock_event_bus
            )
        
        with pytest.raises(ValueError, match="doomsday_switch不能为None"):
            RiskEmergencyIntegration(
                risk_system=Mock(),
                emergency_system=mock_emergency_system,
                doomsday_switch=None,
                event_bus=mock_event_bus
            )
        
        with pytest.raises(ValueError, match="监控间隔必须 >= 1秒"):
            RiskEmergencyIntegration(
                risk_system=Mock(),
                emergency_system=mock_emergency_system,
                doomsday_switch=mock_doomsday_switch,
                event_bus=mock_event_bus,
                monitor_interval=0
            )
    
    @pytest.mark.asyncio
    async def test_initialize(self, integration):
        """测试初始化方法"""
        await integration.initialize()
        
        assert integration.stats['start_time'] is not None
    
    @pytest.mark.asyncio
    async def test_initialize_without_event_bus(
        self,
        mock_risk_system,
        mock_emergency_system,
        mock_doomsday_switch
    ):
        """测试无事件总线的初始化"""
        integration = RiskEmergencyIntegration(
            risk_system=mock_risk_system,
            emergency_system=mock_emergency_system,
            doomsday_switch=mock_doomsday_switch,
            event_bus=None
        )
        
        with patch('src.infra.cross_chapter_event_bus.get_cross_chapter_event_bus') as mock_get:
            mock_bus = Mock(spec=CrossChapterEventBus)
            mock_get.return_value = mock_bus
            
            await integration.initialize()
            
            assert integration.event_bus == mock_bus
            mock_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitor_and_respond_no_risk(self, integration):
        """测试监控无风险情况"""
        await integration.initialize()
        
        result = await integration.monitor_and_respond()
        
        assert result is None
        assert integration.stats['total_risks_detected'] == 0
    
    @pytest.mark.asyncio
    async def test_monitor_and_respond_with_market_risk(self, integration):
        """测试监控市场风险"""
        await integration.initialize()
        
        # Mock市场风险事件
        risk_event = RiskEvent(
            risk_type='market_risk',
            risk_level=RiskLevel.HIGH,
            description='市场波动率过高',
            timestamp=datetime.now(),
            metrics={'volatility': 0.08}
        )
        integration.risk_system.monitor_market_risk = Mock(return_value=risk_event)
        
        market_data = {
            'volatility': 0.08,
            'daily_pnl_ratio': -0.05,
            'market_trend': 'volatile'
        }
        
        result = await integration.monitor_and_respond(market_data=market_data)
        
        assert result is not None
        assert integration.stats['total_risks_detected'] == 1
        assert integration.stats['total_alerts_triggered'] == 1
        
        # 验证应急响应被触发
        integration.emergency_system.trigger_alert.assert_called_once()
        call_args = integration.emergency_system.trigger_alert.call_args
        assert call_args[1]['alert_level'] == AlertLevel.DANGER
        assert call_args[1]['description'] == '市场波动率过高'
    
    @pytest.mark.asyncio
    async def test_monitor_and_respond_with_system_risk(self, integration):
        """测试监控系统风险"""
        await integration.initialize()
        
        # Mock系统风险事件
        risk_event = RiskEvent(
            risk_type='system_risk',
            risk_level=RiskLevel.MEDIUM,
            description='系统健康度低',
            timestamp=datetime.now(),
            metrics={'overall_health': 0.75}
        )
        integration.risk_system.monitor_system_risk = Mock(return_value=risk_event)
        
        system_data = {
            'redis_health': 0.75,
            'gpu_health': 0.85,
            'network_health': 0.90
        }
        
        result = await integration.monitor_and_respond(system_data=system_data)
        
        assert result is not None
        assert integration.stats['total_risks_detected'] == 1
        
        # 验证应急响应被触发
        integration.emergency_system.trigger_alert.assert_called_once()
        call_args = integration.emergency_system.trigger_alert.call_args
        assert call_args[1]['alert_level'] == AlertLevel.WARNING
    
    @pytest.mark.asyncio
    async def test_monitor_and_respond_critical_risk_triggers_doomsday(self, integration):
        """测试极高风险触发末日开关"""
        await integration.initialize()
        
        # Mock极高市场风险事件
        risk_event = RiskEvent(
            risk_type='market_risk',
            risk_level=RiskLevel.CRITICAL,
            description='市场崩盘风险',
            timestamp=datetime.now(),
            metrics={'market_trend': 'crash'}
        )
        integration.risk_system.monitor_market_risk = Mock(return_value=risk_event)
        
        market_data = {
            'volatility': 0.15,
            'daily_pnl_ratio': -0.15,
            'market_trend': 'crash'
        }
        
        result = await integration.monitor_and_respond(market_data=market_data)
        
        assert result is not None
        assert integration.stats['total_risks_detected'] == 1
        
        # 验证末日开关被触发
        integration.doomsday_switch.trigger.assert_called_once()
        call_args = integration.doomsday_switch.trigger.call_args
        assert '极高风险' in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_monitor_and_respond_doomsday_already_triggered(self, integration):
        """测试末日开关已触发时跳过监控"""
        await integration.initialize()
        
        # Mock末日开关已触发
        integration.doomsday_switch.is_triggered = Mock(return_value=True)
        
        result = await integration.monitor_and_respond()
        
        assert result is None
        assert integration.stats['total_risks_detected'] == 0
    
    @pytest.mark.asyncio
    async def test_check_doomsday_triggers(self, integration):
        """测试检查末日开关触发条件"""
        await integration.initialize()
        
        # Mock触发条件
        integration.doomsday_switch.check_triggers = Mock(return_value=[
            'Redis failures: 3',
            'Memory critical: 96%'
        ])
        
        await integration._check_doomsday_triggers()
        
        # 验证末日开关被触发
        integration.doomsday_switch.trigger.assert_called_once()
        call_args = integration.doomsday_switch.trigger.call_args
        assert 'Redis failures: 3' in call_args[0][0]
        assert 'Memory critical: 96%' in call_args[0][0]
        
        # 验证统计信息
        assert integration.stats['total_doomsday_checks'] == 1
    
    @pytest.mark.asyncio
    async def test_publish_risk_event(self, integration):
        """测试发布风险事件"""
        await integration.initialize()
        
        risk_event = RiskEvent(
            risk_type='market_risk',
            risk_level=RiskLevel.HIGH,
            description='市场波动率过高',
            timestamp=datetime.now(),
            metrics={'volatility': 0.08}
        )
        
        await integration._publish_risk_event(risk_event, AlertLevel.DANGER)
        
        # 验证事件发布
        integration.event_bus.publish.assert_called_once()
        published_event = integration.event_bus.publish.call_args[0][0]
        
        assert published_event.event_type == CrossChapterEventType.RISK_LEVEL_CHANGED
        assert published_event.source_chapter == 19
        assert published_event.target_chapter == 13
        assert published_event.priority == EventPriority.HIGH
        assert published_event.data['risk_type'] == 'market_risk'
        assert published_event.data['risk_level'] == 'high'
        assert published_event.data['alert_level'] == 'danger'
        
        # 验证统计信息
        assert integration.stats['events_published'] == 1
    
    @pytest.mark.asyncio
    async def test_publish_doomsday_event(self, integration):
        """测试发布末日开关事件"""
        await integration.initialize()
        
        reason = '触发条件: Redis failures: 3, Memory critical: 96%'
        triggers_fired = ['Redis failures: 3', 'Memory critical: 96%']
        
        await integration._publish_doomsday_event(reason, triggers_fired)
        
        # 验证事件发布
        integration.event_bus.publish.assert_called_once()
        published_event = integration.event_bus.publish.call_args[0][0]
        
        assert published_event.event_type == CrossChapterEventType.DOOMSDAY_TRIGGERED
        assert published_event.source_chapter == 12
        assert published_event.target_chapter == 13
        assert published_event.priority == EventPriority.CRITICAL
        assert published_event.data['reason'] == reason
        assert published_event.data['triggers_fired'] == triggers_fired
        
        # 验证统计信息
        assert integration.stats['events_published'] == 1
    
    @pytest.mark.asyncio
    async def test_publish_event_without_event_bus(
        self,
        mock_risk_system,
        mock_emergency_system,
        mock_doomsday_switch
    ):
        """测试无事件总线时发布事件"""
        integration = RiskEmergencyIntegration(
            risk_system=mock_risk_system,
            emergency_system=mock_emergency_system,
            doomsday_switch=mock_doomsday_switch,
            event_bus=None
        )
        await integration.initialize()
        
        # 设置event_bus为None
        integration.event_bus = None
        
        risk_event = RiskEvent(
            risk_type='market_risk',
            risk_level=RiskLevel.HIGH,
            description='测试',
            timestamp=datetime.now(),
            metrics={}
        )
        
        # 应该不抛出异常，只是记录警告
        await integration._publish_risk_event(risk_event, AlertLevel.DANGER)
        
        # 验证统计信息未更新
        assert integration.stats['events_published'] == 0
    
    @pytest.mark.asyncio
    async def test_get_integration_status(self, integration):
        """测试获取集成状态"""
        await integration.initialize()
        
        # Mock数据
        integration.risk_system.get_overall_risk_level = Mock(return_value=RiskLevel.MEDIUM)
        integration.doomsday_switch.is_triggered = Mock(return_value=False)
        integration.emergency_system.get_emergency_history = Mock(return_value=[
            Mock(), Mock(), Mock()
        ])
        integration.emergency_system.emergency_history = [Mock()] * 10
        
        status = await integration.get_integration_status()
        
        assert isinstance(status, RiskEmergencyStatus)
        assert status.overall_risk_level == 'medium'
        assert status.is_doomsday_triggered is False
        assert status.active_alerts == 3
        assert status.emergency_procedures_executed == 10
        assert status.timestamp is not None
    
    def test_get_stats(self, integration):
        """测试获取统计信息"""
        integration.stats['start_time'] = datetime.now()
        integration.stats['total_risks_detected'] = 50
        integration.stats['total_alerts_triggered'] = 30
        integration.stats['total_doomsday_checks'] = 100
        integration.stats['events_published'] = 25
        
        stats = integration.get_stats()
        
        assert stats['total_risks_detected'] == 50
        assert stats['total_alerts_triggered'] == 30
        assert stats['total_doomsday_checks'] == 100
        assert stats['events_published'] == 25
        assert 'uptime_seconds' in stats
        assert 'risk_detection_rate' in stats
        assert 'alert_rate' in stats
    
    @pytest.mark.asyncio
    async def test_monitor_operational_risk(self, integration):
        """测试监控运营风险"""
        await integration.initialize()
        
        risk_event = RiskEvent(
            risk_type='operational_risk',
            risk_level=RiskLevel.MEDIUM,
            description='策略夏普比率过低',
            timestamp=datetime.now(),
            metrics={'strategy_sharpe': 0.8}
        )
        integration.risk_system.monitor_operational_risk = Mock(return_value=risk_event)
        
        system_data = {
            'strategy_sharpe': 0.8,
            'data_quality_score': 0.85,
            'overfitting_score': 0.60
        }
        
        result = await integration.monitor_and_respond(system_data=system_data)
        
        assert result is not None
        assert integration.stats['total_risks_detected'] == 1
    
    @pytest.mark.asyncio
    async def test_monitor_liquidity_risk(self, integration):
        """测试监控流动性风险"""
        await integration.initialize()
        
        risk_event = RiskEvent(
            risk_type='liquidity_risk',
            risk_level=RiskLevel.HIGH,
            description='买卖价差过大',
            timestamp=datetime.now(),
            metrics={'bid_ask_spread': 0.25}
        )
        integration.risk_system.monitor_liquidity_risk = Mock(return_value=risk_event)
        
        market_data = {
            'bid_ask_spread': 0.25,
            'volume_ratio': 0.40,
            'market_depth': 0.60
        }
        
        result = await integration.monitor_and_respond(market_data=market_data)
        
        assert result is not None
        assert integration.stats['total_risks_detected'] == 1
    
    @pytest.mark.asyncio
    async def test_monitor_counterparty_risk(self, integration):
        """测试监控对手方风险"""
        await integration.initialize()
        
        risk_event = RiskEvent(
            risk_type='counterparty_risk',
            risk_level=RiskLevel.MEDIUM,
            description='券商评级过低',
            timestamp=datetime.now(),
            metrics={'broker_rating': 0.65}
        )
        integration.risk_system.monitor_counterparty_risk = Mock(return_value=risk_event)
        
        system_data = {
            'broker_rating': 0.65,
            'settlement_delay': 1,
            'credit_exposure': 0.25
        }
        
        result = await integration.monitor_and_respond(system_data=system_data)
        
        assert result is not None
        assert integration.stats['total_risks_detected'] == 1
    
    @pytest.mark.asyncio
    async def test_low_risk_no_alert(self, integration):
        """测试低风险不触发告警"""
        await integration.initialize()
        
        # Mock低风险事件
        risk_event = RiskEvent(
            risk_type='market_risk',
            risk_level=RiskLevel.LOW,
            description='市场正常',
            timestamp=datetime.now(),
            metrics={}
        )
        integration.risk_system.monitor_market_risk = Mock(return_value=risk_event)
        
        market_data = {
            'volatility': 0.02,
            'daily_pnl_ratio': 0.01,
            'market_trend': 'normal'
        }
        
        result = await integration.monitor_and_respond(market_data=market_data)
        
        # 低风险应该返回None（不触发告警）
        assert result is None
        assert integration.stats['total_risks_detected'] == 1
        assert integration.stats['total_alerts_triggered'] == 0


class TestGlobalFunctions:
    """测试全局函数"""
    
    @pytest.mark.asyncio
    async def test_get_risk_emergency_integration(self):
        """测试获取全局集成实例"""
        # 重置全局实例
        import src.integration.risk_emergency_integration as module
        module._global_risk_emergency_integration = None
        
        mock_risk_system = Mock(spec=RiskIdentificationSystem)
        mock_emergency_system = Mock(spec=EmergencyResponseSystem)
        mock_doomsday_switch = Mock(spec=DoomsdaySwitch)
        mock_event_bus = Mock(spec=CrossChapterEventBus)
        
        integration = await get_risk_emergency_integration(
            risk_system=mock_risk_system,
            emergency_system=mock_emergency_system,
            doomsday_switch=mock_doomsday_switch,
            event_bus=mock_event_bus
        )
        
        assert integration is not None
        assert integration.risk_system == mock_risk_system
        assert integration.emergency_system == mock_emergency_system
        assert integration.doomsday_switch == mock_doomsday_switch
        assert integration.event_bus == mock_event_bus
        
        # 再次调用应该返回同一实例
        integration2 = await get_risk_emergency_integration()
        assert integration2 is integration
    
    @pytest.mark.asyncio
    async def test_get_risk_emergency_integration_without_params(self):
        """测试无参数获取全局集成实例"""
        # 重置全局实例
        import src.integration.risk_emergency_integration as module
        module._global_risk_emergency_integration = None
        
        with pytest.raises(ValueError, match="首次调用必须提供risk_system、emergency_system和doomsday_switch"):
            await get_risk_emergency_integration()
