"""Property-based tests for AlertManager alert routing

白皮书依据: 第十三章 13.4 告警规则配置

Property 13: Alert Routing by Severity
For any alert with severity level S, the alert should be routed to channels 
appropriate for S (Emergency→Phone+WeChat, Critical→WeChat, Warning→WeChat work hours, Info→Log).

Validates: Requirements 5.10
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck
from datetime import datetime
from unittest.mock import AsyncMock, patch
import asyncio

from src.monitoring.alert_manager import (
    AlertManager,
    Alert,
    AlertLevel
)


# Hypothesis strategies for generating test data
@st.composite
def alert_strategy(draw):
    """Generate random Alert instances"""
    name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), 
        whitelist_characters=' -_'
    )))
    level = draw(st.sampled_from(list(AlertLevel)))
    message = draw(st.text(min_size=1, max_size=200))
    timestamp = datetime.now()
    
    # Optional labels and annotations
    has_labels = draw(st.booleans())
    has_annotations = draw(st.booleans())
    
    labels = None
    if has_labels:
        labels = {
            'severity': draw(st.sampled_from(['low', 'medium', 'high'])),
            'component': draw(st.sampled_from(['redis', 'gpu', 'soldier', 'system']))
        }
    
    annotations = None
    if has_annotations:
        annotations = {
            'summary': draw(st.text(min_size=1, max_size=100)),
            'description': draw(st.text(min_size=1, max_size=200))
        }
    
    return Alert(
        name=name,
        level=level,
        message=message,
        timestamp=timestamp,
        labels=labels,
        annotations=annotations
    )


class TestAlertRoutingProperty:
    """Property-based tests for alert routing
    
    白皮书依据: 第十三章 13.4 告警规则配置
    
    **Validates: Requirements 5.10**
    """
    
    @pytest.mark.asyncio
    @given(alert=alert_strategy())
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_property_13_emergency_alerts_route_to_phone_and_wechat(self, alert):
        """Property 13: Emergency alerts should route to both phone and WeChat
        
        白皮书依据: 第十三章 13.4 告警规则配置
        
        **Validates: Requirements 5.10**
        
        Property: For any alert with severity EMERGENCY, 
        the alert should be routed to both phone and WeChat channels.
        """
        # Arrange: Only test EMERGENCY alerts
        assume(alert.level == AlertLevel.EMERGENCY)
        
        manager = AlertManager(
            wechat_webhook_url="https://wechat.example.com",
            phone_webhook_url="https://phone.example.com"
        )
        
        # Act & Assert
        with patch.object(manager, 'send_wechat_alert', new_callable=AsyncMock) as mock_wechat, \
             patch.object(manager, '_send_phone_alert', new_callable=AsyncMock) as mock_phone:
            
            await manager.route_alert(alert)
            
            # Property verification: Both channels must be called
            assert mock_wechat.called, \
                f"Emergency alert '{alert.name}' did not route to WeChat"
            assert mock_phone.called, \
                f"Emergency alert '{alert.name}' did not route to phone"
            
            # Verify called with correct alert
            mock_wechat.assert_called_once_with(alert)
            mock_phone.assert_called_once_with(alert)
    
    @pytest.mark.asyncio
    @given(alert=alert_strategy())
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
    )
    async def test_property_13_critical_alerts_route_to_wechat_only(self, alert):
        """Property 13: Critical alerts should route to WeChat only
        
        白皮书依据: 第十三章 13.4 告警规则配置
        
        **Validates: Requirements 5.10**
        
        Property: For any alert with severity CRITICAL, 
        the alert should be routed to WeChat but NOT phone.
        """
        # Arrange: Only test CRITICAL alerts
        assume(alert.level == AlertLevel.CRITICAL)
        
        manager = AlertManager(
            wechat_webhook_url="https://wechat.example.com",
            phone_webhook_url="https://phone.example.com"
        )
        
        # Act & Assert
        with patch.object(manager, 'send_wechat_alert', new_callable=AsyncMock) as mock_wechat, \
             patch.object(manager, '_send_phone_alert', new_callable=AsyncMock) as mock_phone:
            
            await manager.route_alert(alert)
            
            # Property verification: Only WeChat should be called
            assert mock_wechat.called, \
                f"Critical alert '{alert.name}' did not route to WeChat"
            assert not mock_phone.called, \
                f"Critical alert '{alert.name}' incorrectly routed to phone"
            
            mock_wechat.assert_called_once_with(alert)
    
    @pytest.mark.asyncio
    @given(alert=alert_strategy(), is_work_hours=st.booleans())
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
    )
    async def test_property_13_warning_alerts_respect_work_hours(self, alert, is_work_hours):
        """Property 13: Warning alerts should respect work hours
        
        白皮书依据: 第十三章 13.4 告警规则配置
        
        **Validates: Requirements 5.10**
        
        Property: For any alert with severity WARNING, 
        the alert should be routed to WeChat ONLY during work hours.
        """
        # Arrange: Only test WARNING alerts
        assume(alert.level == AlertLevel.WARNING)
        
        manager = AlertManager(
            wechat_webhook_url="https://wechat.example.com"
        )
        
        # Act & Assert
        with patch.object(manager, 'send_wechat_alert', new_callable=AsyncMock) as mock_wechat, \
             patch.object(manager, '_is_work_hours', return_value=is_work_hours):
            
            await manager.route_alert(alert)
            
            # Property verification: WeChat called only during work hours
            if is_work_hours:
                assert mock_wechat.called, \
                    f"Warning alert '{alert.name}' did not route to WeChat during work hours"
                mock_wechat.assert_called_once_with(alert)
            else:
                assert not mock_wechat.called, \
                    f"Warning alert '{alert.name}' incorrectly routed to WeChat outside work hours"
    
    @pytest.mark.asyncio
    @given(alert=alert_strategy())
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
    )
    async def test_property_13_info_alerts_log_only(self, alert):
        """Property 13: Info alerts should only be logged
        
        白皮书依据: 第十三章 13.4 告警规则配置
        
        **Validates: Requirements 5.10**
        
        Property: For any alert with severity INFO, 
        the alert should NOT be routed to any external channel.
        """
        # Arrange: Only test INFO alerts
        assume(alert.level == AlertLevel.INFO)
        
        manager = AlertManager(
            wechat_webhook_url="https://wechat.example.com",
            phone_webhook_url="https://phone.example.com"
        )
        
        # Act & Assert
        with patch.object(manager, 'send_wechat_alert', new_callable=AsyncMock) as mock_wechat, \
             patch.object(manager, '_send_phone_alert', new_callable=AsyncMock) as mock_phone:
            
            await manager.route_alert(alert)
            
            # Property verification: No external channels should be called
            assert not mock_wechat.called, \
                f"Info alert '{alert.name}' incorrectly routed to WeChat"
            assert not mock_phone.called, \
                f"Info alert '{alert.name}' incorrectly routed to phone"
    
    @pytest.mark.asyncio
    @given(alerts=st.lists(alert_strategy(), min_size=1, max_size=20))
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_property_13_routing_consistency_across_multiple_alerts(self, alerts):
        """Property 13: Routing should be consistent across multiple alerts
        
        白皮书依据: 第十三章 13.4 告警规则配置
        
        **Validates: Requirements 5.10**
        
        Property: For any sequence of alerts, each alert should be routed 
        according to its severity level consistently.
        """
        manager = AlertManager(
            wechat_webhook_url="https://wechat.example.com",
            phone_webhook_url="https://phone.example.com"
        )
        
        # Track routing decisions
        routing_decisions = {
            AlertLevel.EMERGENCY: {'wechat': 0, 'phone': 0},
            AlertLevel.CRITICAL: {'wechat': 0, 'phone': 0},
            AlertLevel.WARNING: {'wechat': 0, 'phone': 0},
            AlertLevel.INFO: {'wechat': 0, 'phone': 0}
        }
        
        with patch.object(manager, 'send_wechat_alert', new_callable=AsyncMock) as mock_wechat, \
             patch.object(manager, '_send_phone_alert', new_callable=AsyncMock) as mock_phone, \
             patch.object(manager, '_is_work_hours', return_value=True):
            
            # Route all alerts
            for alert in alerts:
                mock_wechat.reset_mock()
                mock_phone.reset_mock()
                
                await manager.route_alert(alert)
                
                if mock_wechat.called:
                    routing_decisions[alert.level]['wechat'] += 1
                if mock_phone.called:
                    routing_decisions[alert.level]['phone'] += 1
        
        # Property verification: Check routing consistency
        # Count alerts by level
        alert_counts = {level: 0 for level in AlertLevel}
        for alert in alerts:
            alert_counts[alert.level] += 1
        
        # Verify EMERGENCY alerts
        if alert_counts[AlertLevel.EMERGENCY] > 0:
            assert routing_decisions[AlertLevel.EMERGENCY]['wechat'] == alert_counts[AlertLevel.EMERGENCY], \
                "Not all EMERGENCY alerts routed to WeChat"
            assert routing_decisions[AlertLevel.EMERGENCY]['phone'] == alert_counts[AlertLevel.EMERGENCY], \
                "Not all EMERGENCY alerts routed to phone"
        
        # Verify CRITICAL alerts
        if alert_counts[AlertLevel.CRITICAL] > 0:
            assert routing_decisions[AlertLevel.CRITICAL]['wechat'] == alert_counts[AlertLevel.CRITICAL], \
                "Not all CRITICAL alerts routed to WeChat"
            assert routing_decisions[AlertLevel.CRITICAL]['phone'] == 0, \
                "CRITICAL alerts incorrectly routed to phone"
        
        # Verify WARNING alerts (during work hours)
        if alert_counts[AlertLevel.WARNING] > 0:
            assert routing_decisions[AlertLevel.WARNING]['wechat'] == alert_counts[AlertLevel.WARNING], \
                "Not all WARNING alerts routed to WeChat during work hours"
            assert routing_decisions[AlertLevel.WARNING]['phone'] == 0, \
                "WARNING alerts incorrectly routed to phone"
        
        # Verify INFO alerts
        if alert_counts[AlertLevel.INFO] > 0:
            assert routing_decisions[AlertLevel.INFO]['wechat'] == 0, \
                "INFO alerts incorrectly routed to WeChat"
            assert routing_decisions[AlertLevel.INFO]['phone'] == 0, \
                "INFO alerts incorrectly routed to phone"
    
    @pytest.mark.asyncio
    @given(
        alert=alert_strategy(),
        wechat_configured=st.booleans(),
        phone_configured=st.booleans()
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_property_13_routing_handles_missing_webhooks_gracefully(
        self, 
        alert, 
        wechat_configured, 
        phone_configured
    ):
        """Property 13: Routing should handle missing webhooks gracefully
        
        白皮书依据: 第十三章 13.4 告警规则配置
        
        **Validates: Requirements 5.10**
        
        Property: For any alert, if a required webhook is not configured, 
        the system should not crash but should log a warning.
        """
        wechat_url = "https://wechat.example.com" if wechat_configured else None
        phone_url = "https://phone.example.com" if phone_configured else None
        
        manager = AlertManager(
            wechat_webhook_url=wechat_url,
            phone_webhook_url=phone_url
        )
        
        # Act: Route alert should not raise exception
        # Mock both send methods to avoid actual network requests
        try:
            with patch.object(manager, '_is_work_hours', return_value=True), \
                 patch.object(manager, 'send_wechat_alert', new_callable=AsyncMock) as mock_wechat, \
                 patch.object(manager, '_send_phone_alert', new_callable=AsyncMock) as mock_phone:
                
                await manager.route_alert(alert)
            
            # Property verification: No exception raised
            success = True
        except Exception as e:
            success = False
            pytest.fail(f"Routing raised exception with missing webhooks: {e}")
        
        assert success, "Alert routing should handle missing webhooks gracefully"
    
    @pytest.mark.asyncio
    @given(alert=alert_strategy())
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_property_13_all_alerts_are_logged(self, alert):
        """Property 13: All alerts should be logged regardless of routing
        
        白皮书依据: 第十三章 13.4 告警规则配置
        
        **Validates: Requirements 5.10**
        
        Property: For any alert with any severity level, 
        the alert should always be logged.
        """
        manager = AlertManager(
            wechat_webhook_url="https://wechat.example.com",
            phone_webhook_url="https://phone.example.com"
        )
        
        # Act & Assert: Verify logging happens
        with patch('src.monitoring.alert_manager.logger') as mock_logger, \
             patch.object(manager, 'send_wechat_alert', new_callable=AsyncMock), \
             patch.object(manager, '_send_phone_alert', new_callable=AsyncMock), \
             patch.object(manager, '_is_work_hours', return_value=True):
            
            await manager.route_alert(alert)
            
            # Property verification: Logger was called
            assert mock_logger.info.called or \
                   mock_logger.warning.called or \
                   mock_logger.error.called or \
                   mock_logger.critical.called, \
                f"Alert '{alert.name}' was not logged"
    
    @pytest.mark.asyncio
    @given(
        alert_name=st.text(min_size=1, max_size=50),
        alert_message=st.text(min_size=1, max_size=200)
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_property_13_alert_content_preserved_during_routing(
        self, 
        alert_name, 
        alert_message
    ):
        """Property 13: Alert content should be preserved during routing
        
        白皮书依据: 第十三章 13.4 告警规则配置
        
        **Validates: Requirements 5.10**
        
        Property: For any alert, the name and message should be preserved 
        exactly as provided when routing to channels.
        """
        alert = Alert(
            name=alert_name,
            level=AlertLevel.CRITICAL,
            message=alert_message,
            timestamp=datetime.now()
        )
        
        manager = AlertManager(
            wechat_webhook_url="https://wechat.example.com"
        )
        
        # Act & Assert
        with patch.object(manager, 'send_wechat_alert', new_callable=AsyncMock) as mock_wechat:
            await manager.route_alert(alert)
            
            # Property verification: Alert content preserved
            mock_wechat.assert_called_once()
            routed_alert = mock_wechat.call_args[0][0]
            
            assert routed_alert.name == alert_name, \
                "Alert name was modified during routing"
            assert routed_alert.message == alert_message, \
                "Alert message was modified during routing"
            assert routed_alert.level == AlertLevel.CRITICAL, \
                "Alert level was modified during routing"
