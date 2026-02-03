"""Unit tests for AlertManager

白皮书依据: 第十三章 13.4 告警规则配置
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from src.monitoring.alert_manager import (
    AlertManager,
    Alert,
    AlertLevel
)


class TestAlertLevel:
    """Test AlertLevel enum"""
    
    def test_alert_levels_defined(self):
        """Test all alert levels are defined"""
        assert AlertLevel.EMERGENCY.value == "emergency"
        assert AlertLevel.CRITICAL.value == "critical"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.INFO.value == "info"
    
    def test_alert_level_count(self):
        """Test correct number of alert levels"""
        assert len(AlertLevel) == 4


class TestAlert:
    """Test Alert dataclass"""
    
    def test_alert_creation(self):
        """Test creating an alert"""
        timestamp = datetime.now()
        alert = Alert(
            name="TestAlert",
            level=AlertLevel.WARNING,
            message="Test message",
            timestamp=timestamp
        )
        
        assert alert.name == "TestAlert"
        assert alert.level == AlertLevel.WARNING
        assert alert.message == "Test message"
        assert alert.timestamp == timestamp
        assert alert.labels is None
        assert alert.annotations is None
    
    def test_alert_with_labels_and_annotations(self):
        """Test alert with labels and annotations"""
        timestamp = datetime.now()
        labels = {"severity": "high", "component": "redis"}
        annotations = {"summary": "Redis down", "description": "Connection failed"}
        
        alert = Alert(
            name="RedisDown",
            level=AlertLevel.CRITICAL,
            message="Redis connection failed",
            timestamp=timestamp,
            labels=labels,
            annotations=annotations
        )
        
        assert alert.labels == labels
        assert alert.annotations == annotations


class TestAlertManagerInit:
    """Test AlertManager initialization"""
    
    def test_init_default_params(self):
        """Test initialization with default parameters"""
        manager = AlertManager()
        
        assert manager.wechat_webhook_url is None
        assert manager.phone_webhook_url is None
        assert manager.work_hours_start == 9
        assert manager.work_hours_end == 18
        assert manager.alert_rules == []
    
    def test_init_custom_params(self):
        """Test initialization with custom parameters"""
        manager = AlertManager(
            wechat_webhook_url="https://wechat.example.com/webhook",
            phone_webhook_url="https://phone.example.com/webhook",
            work_hours_start=8,
            work_hours_end=20
        )
        
        assert manager.wechat_webhook_url == "https://wechat.example.com/webhook"
        assert manager.phone_webhook_url == "https://phone.example.com/webhook"
        assert manager.work_hours_start == 8
        assert manager.work_hours_end == 20
    
    def test_init_invalid_work_hours_start(self):
        """Test initialization with invalid work_hours_start"""
        with pytest.raises(ValueError, match="work_hours_start must be 0-23"):
            AlertManager(work_hours_start=-1)
        
        with pytest.raises(ValueError, match="work_hours_start must be 0-23"):
            AlertManager(work_hours_start=24)
    
    def test_init_invalid_work_hours_end(self):
        """Test initialization with invalid work_hours_end"""
        with pytest.raises(ValueError, match="work_hours_end must be 0-23"):
            AlertManager(work_hours_end=-1)
        
        with pytest.raises(ValueError, match="work_hours_end must be 0-23"):
            AlertManager(work_hours_end=24)
    
    def test_init_work_hours_start_greater_than_end(self):
        """Test initialization with work_hours_start >= work_hours_end"""
        with pytest.raises(ValueError, match="work_hours_start.*must be <.*work_hours_end"):
            AlertManager(work_hours_start=18, work_hours_end=9)
        
        with pytest.raises(ValueError, match="work_hours_start.*must be <.*work_hours_end"):
            AlertManager(work_hours_start=12, work_hours_end=12)


class TestConfigureAlerts:
    """Test configure_alerts method"""
    
    def test_configure_alerts(self):
        """Test configuring alert rules"""
        manager = AlertManager()
        manager.configure_alerts()
        
        assert len(manager.alert_rules) == 7
        
        # Check alert names
        alert_names = [rule["alert"] for rule in manager.alert_rules]
        assert "RedisDown" in alert_names
        assert "SoldierDegraded" in alert_names
        assert "GPUOverheating" in alert_names
        assert "HighMemoryUsage" in alert_names
        assert "LowDiskSpace" in alert_names
        assert "DailyLossExceeded" in alert_names
        assert "CriticalLoss" in alert_names
    
    def test_redis_down_alert_rule(self):
        """Test RedisDown alert rule configuration"""
        manager = AlertManager()
        manager.configure_alerts()
        
        redis_rule = next(
            rule for rule in manager.alert_rules
            if rule["alert"] == "RedisDown"
        )
        
        assert redis_rule["expr"] == "redis_connection_failures >= 3"
        assert redis_rule["for"] == "1m"
        assert redis_rule["labels"]["severity"] == "critical"
        assert "Redis连接失败" in redis_rule["annotations"]["summary"]
    
    def test_soldier_degraded_alert_rule(self):
        """Test SoldierDegraded alert rule configuration"""
        manager = AlertManager()
        manager.configure_alerts()
        
        soldier_rule = next(
            rule for rule in manager.alert_rules
            if rule["alert"] == "SoldierDegraded"
        )
        
        assert soldier_rule["expr"] == "soldier_mode_status == 1"
        assert soldier_rule["for"] == "10m"
        assert soldier_rule["labels"]["severity"] == "warning"
    
    def test_critical_loss_alert_rule(self):
        """Test CriticalLoss alert rule configuration"""
        manager = AlertManager()
        manager.configure_alerts()
        
        loss_rule = next(
            rule for rule in manager.alert_rules
            if rule["alert"] == "CriticalLoss"
        )
        
        assert loss_rule["expr"] == "portfolio_daily_pnl_percent < -10"
        assert loss_rule["for"] == "1m"
        assert loss_rule["labels"]["severity"] == "emergency"


class TestIsWorkHours:
    """Test _is_work_hours method"""
    
    def test_is_work_hours_during_work_time(self):
        """Test work hours check during work time"""
        manager = AlertManager(work_hours_start=9, work_hours_end=18)
        
        with patch('src.monitoring.alert_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value.hour = 12
            assert manager._is_work_hours() is True
    
    def test_is_work_hours_before_work_time(self):
        """Test work hours check before work time"""
        manager = AlertManager(work_hours_start=9, work_hours_end=18)
        
        with patch('src.monitoring.alert_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value.hour = 7
            assert manager._is_work_hours() is False
    
    def test_is_work_hours_after_work_time(self):
        """Test work hours check after work time"""
        manager = AlertManager(work_hours_start=9, work_hours_end=18)
        
        with patch('src.monitoring.alert_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value.hour = 20
            assert manager._is_work_hours() is False
    
    def test_is_work_hours_at_start_boundary(self):
        """Test work hours check at start boundary"""
        manager = AlertManager(work_hours_start=9, work_hours_end=18)
        
        with patch('src.monitoring.alert_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value.hour = 9
            assert manager._is_work_hours() is True
    
    def test_is_work_hours_at_end_boundary(self):
        """Test work hours check at end boundary"""
        manager = AlertManager(work_hours_start=9, work_hours_end=18)
        
        with patch('src.monitoring.alert_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value.hour = 18
            assert manager._is_work_hours() is False


class TestRouteAlert:
    """Test route_alert method"""
    
    @pytest.mark.asyncio
    async def test_route_emergency_alert(self):
        """Test routing emergency alert"""
        manager = AlertManager(
            wechat_webhook_url="https://wechat.example.com",
            phone_webhook_url="https://phone.example.com"
        )
        
        alert = Alert(
            name="CriticalLoss",
            level=AlertLevel.EMERGENCY,
            message="Daily loss > 10%",
            timestamp=datetime.now()
        )
        
        with patch.object(manager, 'send_wechat_alert', new_callable=AsyncMock) as mock_wechat, \
             patch.object(manager, '_send_phone_alert', new_callable=AsyncMock) as mock_phone:
            
            await manager.route_alert(alert)
            
            mock_wechat.assert_called_once_with(alert)
            mock_phone.assert_called_once_with(alert)
    
    @pytest.mark.asyncio
    async def test_route_critical_alert(self):
        """Test routing critical alert"""
        manager = AlertManager(wechat_webhook_url="https://wechat.example.com")
        
        alert = Alert(
            name="RedisDown",
            level=AlertLevel.CRITICAL,
            message="Redis connection failed",
            timestamp=datetime.now()
        )
        
        with patch.object(manager, 'send_wechat_alert', new_callable=AsyncMock) as mock_wechat, \
             patch.object(manager, '_send_phone_alert', new_callable=AsyncMock) as mock_phone:
            
            await manager.route_alert(alert)
            
            mock_wechat.assert_called_once_with(alert)
            mock_phone.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_route_warning_alert_during_work_hours(self):
        """Test routing warning alert during work hours"""
        manager = AlertManager(wechat_webhook_url="https://wechat.example.com")
        
        alert = Alert(
            name="HighMemory",
            level=AlertLevel.WARNING,
            message="Memory > 90%",
            timestamp=datetime.now()
        )
        
        with patch.object(manager, 'send_wechat_alert', new_callable=AsyncMock) as mock_wechat, \
             patch.object(manager, '_is_work_hours', return_value=True):
            
            await manager.route_alert(alert)
            
            mock_wechat.assert_called_once_with(alert)
    
    @pytest.mark.asyncio
    async def test_route_warning_alert_outside_work_hours(self):
        """Test routing warning alert outside work hours"""
        manager = AlertManager(wechat_webhook_url="https://wechat.example.com")
        
        alert = Alert(
            name="HighMemory",
            level=AlertLevel.WARNING,
            message="Memory > 90%",
            timestamp=datetime.now()
        )
        
        with patch.object(manager, 'send_wechat_alert', new_callable=AsyncMock) as mock_wechat, \
             patch.object(manager, '_is_work_hours', return_value=False):
            
            await manager.route_alert(alert)
            
            mock_wechat.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_route_info_alert(self):
        """Test routing info alert (log only)"""
        manager = AlertManager(wechat_webhook_url="https://wechat.example.com")
        
        alert = Alert(
            name="SystemInfo",
            level=AlertLevel.INFO,
            message="System running normally",
            timestamp=datetime.now()
        )
        
        with patch.object(manager, 'send_wechat_alert', new_callable=AsyncMock) as mock_wechat:
            await manager.route_alert(alert)
            
            mock_wechat.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_route_alert_invalid_level(self):
        """Test routing alert with invalid level"""
        manager = AlertManager()
        
        alert = Alert(
            name="TestAlert",
            level="invalid",  # Invalid level
            message="Test",
            timestamp=datetime.now()
        )
        
        with pytest.raises(ValueError, match="Invalid alert level"):
            await manager.route_alert(alert)


class TestSendWechatAlert:
    """Test send_wechat_alert method"""
    
    @pytest.mark.asyncio
    async def test_send_wechat_alert_success(self):
        """Test sending WeChat alert successfully"""
        manager = AlertManager(wechat_webhook_url="https://wechat.example.com")
        
        alert = Alert(
            name="TestAlert",
            level=AlertLevel.CRITICAL,
            message="Test message",
            timestamp=datetime.now()
        )
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            await manager.send_wechat_alert(alert)
            
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://wechat.example.com"
    
    @pytest.mark.asyncio
    async def test_send_wechat_alert_with_labels(self):
        """Test sending WeChat alert with labels"""
        manager = AlertManager(wechat_webhook_url="https://wechat.example.com")
        
        alert = Alert(
            name="TestAlert",
            level=AlertLevel.CRITICAL,
            message="Test message",
            timestamp=datetime.now(),
            labels={"severity": "high", "component": "redis"}
        )
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            await manager.send_wechat_alert(alert)
            
            # Check that labels are included in message
            call_args = mock_post.call_args
            message = call_args[1]["json"]
            assert "标签" in message["markdown"]["content"]
    
    @pytest.mark.asyncio
    async def test_send_wechat_alert_with_annotations(self):
        """Test sending WeChat alert with annotations"""
        manager = AlertManager(wechat_webhook_url="https://wechat.example.com")
        
        alert = Alert(
            name="TestAlert",
            level=AlertLevel.CRITICAL,
            message="Test message",
            timestamp=datetime.now(),
            annotations={"summary": "Test summary", "description": "Test description"}
        )
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            await manager.send_wechat_alert(alert)
            
            # Check that annotations are included in message
            call_args = mock_post.call_args
            message = call_args[1]["json"]
            assert "详情" in message["markdown"]["content"]
    
    @pytest.mark.asyncio
    async def test_send_wechat_alert_not_configured(self):
        """Test sending WeChat alert when webhook not configured"""
        manager = AlertManager()  # No webhook URL
        
        alert = Alert(
            name="TestAlert",
            level=AlertLevel.CRITICAL,
            message="Test message",
            timestamp=datetime.now()
        )
        
        # Should not raise exception, just log warning
        await manager.send_wechat_alert(alert)
    
    @pytest.mark.asyncio
    async def test_send_wechat_alert_http_error(self):
        """Test sending WeChat alert with HTTP error"""
        manager = AlertManager(wechat_webhook_url="https://wechat.example.com")
        
        alert = Alert(
            name="TestAlert",
            level=AlertLevel.CRITICAL,
            message="Test message",
            timestamp=datetime.now()
        )
        
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(RuntimeError, match="WeChat webhook returned status 500"):
                await manager.send_wechat_alert(alert)
    
    @pytest.mark.asyncio
    async def test_send_wechat_alert_timeout(self):
        """Test sending WeChat alert with timeout"""
        manager = AlertManager(wechat_webhook_url="https://wechat.example.com")
        
        alert = Alert(
            name="TestAlert",
            level=AlertLevel.CRITICAL,
            message="Test message",
            timestamp=datetime.now()
        )
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(RuntimeError, match="WeChat webhook timeout"):
                await manager.send_wechat_alert(alert)
    
    @pytest.mark.asyncio
    async def test_send_wechat_alert_client_error(self):
        """Test sending WeChat alert with client error"""
        manager = AlertManager(wechat_webhook_url="https://wechat.example.com")
        
        alert = Alert(
            name="TestAlert",
            level=AlertLevel.CRITICAL,
            message="Test message",
            timestamp=datetime.now()
        )
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = aiohttp.ClientError("Connection failed")
            
            with pytest.raises(aiohttp.ClientError):
                await manager.send_wechat_alert(alert)


class TestSendPhoneAlert:
    """Test _send_phone_alert method"""
    
    @pytest.mark.asyncio
    async def test_send_phone_alert_success(self):
        """Test sending phone alert successfully"""
        manager = AlertManager(phone_webhook_url="https://phone.example.com")
        
        alert = Alert(
            name="CriticalLoss",
            level=AlertLevel.EMERGENCY,
            message="Daily loss > 10%",
            timestamp=datetime.now()
        )
        
        mock_response = AsyncMock()
        mock_response.status = 200
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            await manager._send_phone_alert(alert)
            
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://phone.example.com"
            
            # Check message format (should be text, not markdown)
            message = call_args[1]["json"]
            assert message["msgtype"] == "text"
            assert "🚨" in message["text"]["content"]
    
    @pytest.mark.asyncio
    async def test_send_phone_alert_not_configured(self):
        """Test sending phone alert when webhook not configured"""
        manager = AlertManager()  # No phone webhook URL
        
        alert = Alert(
            name="CriticalLoss",
            level=AlertLevel.EMERGENCY,
            message="Daily loss > 10%",
            timestamp=datetime.now()
        )
        
        # Should not raise exception, just log warning
        await manager._send_phone_alert(alert)
    
    @pytest.mark.asyncio
    async def test_send_phone_alert_timeout(self):
        """Test sending phone alert with timeout"""
        manager = AlertManager(phone_webhook_url="https://phone.example.com")
        
        alert = Alert(
            name="CriticalLoss",
            level=AlertLevel.EMERGENCY,
            message="Daily loss > 10%",
            timestamp=datetime.now()
        )
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError()
            
            # Should not raise exception, just log error
            await manager._send_phone_alert(alert)


class TestGetAlertRules:
    """Test get_alert_rules and get_alert_rule_by_name methods"""
    
    def test_get_alert_rules(self):
        """Test getting all alert rules"""
        manager = AlertManager()
        manager.configure_alerts()
        
        rules = manager.get_alert_rules()
        
        assert len(rules) == 7
        assert isinstance(rules, list)
        
        # Verify it's a copy, not the original
        rules.append({"alert": "NewRule"})
        assert len(manager.alert_rules) == 7
    
    def test_get_alert_rule_by_name_found(self):
        """Test getting alert rule by name when it exists"""
        manager = AlertManager()
        manager.configure_alerts()
        
        rule = manager.get_alert_rule_by_name("RedisDown")
        
        assert rule is not None
        assert rule["alert"] == "RedisDown"
        assert rule["expr"] == "redis_connection_failures >= 3"
    
    def test_get_alert_rule_by_name_not_found(self):
        """Test getting alert rule by name when it doesn't exist"""
        manager = AlertManager()
        manager.configure_alerts()
        
        rule = manager.get_alert_rule_by_name("NonExistentRule")
        
        assert rule is None
    
    def test_get_alert_rule_by_name_returns_copy(self):
        """Test that get_alert_rule_by_name returns a copy"""
        manager = AlertManager()
        manager.configure_alerts()
        
        rule = manager.get_alert_rule_by_name("RedisDown")
        rule["alert"] = "ModifiedName"
        
        # Original should be unchanged
        original_rule = manager.get_alert_rule_by_name("RedisDown")
        assert original_rule["alert"] == "RedisDown"


class TestAlertManagerIntegration:
    """Integration tests for AlertManager"""
    
    @pytest.mark.asyncio
    async def test_full_alert_workflow(self):
        """Test complete alert workflow from configuration to routing"""
        manager = AlertManager(
            wechat_webhook_url="https://wechat.example.com",
            phone_webhook_url="https://phone.example.com"
        )
        
        # Configure alerts
        manager.configure_alerts()
        assert len(manager.alert_rules) == 7
        
        # Create and route emergency alert
        alert = Alert(
            name="CriticalLoss",
            level=AlertLevel.EMERGENCY,
            message="Daily loss > 10%",
            timestamp=datetime.now(),
            labels={"severity": "emergency"},
            annotations={"summary": "Critical loss", "description": "Immediate action required"}
        )
        
        with patch.object(manager, 'send_wechat_alert', new_callable=AsyncMock) as mock_wechat, \
             patch.object(manager, '_send_phone_alert', new_callable=AsyncMock) as mock_phone:
            
            await manager.route_alert(alert)
            
            mock_wechat.assert_called_once()
            mock_phone.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multiple_alerts_routing(self):
        """Test routing multiple alerts with different levels"""
        manager = AlertManager(wechat_webhook_url="https://wechat.example.com")
        
        alerts = [
            Alert("Info1", AlertLevel.INFO, "Info message", datetime.now()),
            Alert("Warning1", AlertLevel.WARNING, "Warning message", datetime.now()),
            Alert("Critical1", AlertLevel.CRITICAL, "Critical message", datetime.now()),
        ]
        
        with patch.object(manager, 'send_wechat_alert', new_callable=AsyncMock) as mock_wechat, \
             patch.object(manager, '_is_work_hours', return_value=True):
            
            for alert in alerts:
                await manager.route_alert(alert)
            
            # INFO should not send WeChat, WARNING and CRITICAL should
            assert mock_wechat.call_count == 2


class TestAlertManagerMissingCoverage:
    """补充测试以达到100%覆盖率"""
    
    @pytest.mark.asyncio
    async def test_route_alert_with_invalid_alert_level_type(self):
        """测试使用无效的AlertLevel类型（覆盖line 264）"""
        manager = AlertManager(
            wechat_webhook_url="https://wechat.example.com"
        )
        
        # 创建一个带有无效level的alert（通过修改枚举值）
        alert = Alert(
            name="test_alert",
            level=AlertLevel.INFO,
            message="test message",
            timestamp=datetime.now()
        )
        
        # 手动修改level为非AlertLevel类型来触发ValueError
        alert.level = "invalid_level"
        
        with pytest.raises(ValueError, match="Invalid alert level"):
            await manager.route_alert(alert)
    
    @pytest.mark.asyncio
    async def test_send_phone_alert_http_error_status(self):
        """测试phone alert HTTP错误状态（覆盖lines 376-377）"""
        manager = AlertManager(
            phone_webhook_url="https://phone.example.com"
        )
        
        alert = Alert(
            name="test_alert",
            level=AlertLevel.EMERGENCY,
            message="test message",
            timestamp=datetime.now()
        )
        
        # Mock aiohttp.ClientSession.post to return error status
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # 不应抛出异常，只记录错误
            await manager._send_phone_alert(alert)
    
    @pytest.mark.asyncio
    async def test_send_phone_alert_timeout_error(self):
        """测试phone alert超时错误（覆盖line 385）"""
        manager = AlertManager(
            phone_webhook_url="https://phone.example.com"
        )
        
        alert = Alert(
            name="test_alert",
            level=AlertLevel.EMERGENCY,
            message="test message",
            timestamp=datetime.now()
        )
        
        # Mock aiohttp.ClientSession.post to raise TimeoutError
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError()
            
            # 不应抛出异常，只记录错误
            await manager._send_phone_alert(alert)
    
    @pytest.mark.asyncio
    async def test_send_phone_alert_client_error(self):
        """测试phone alert客户端错误（覆盖line 386）"""
        manager = AlertManager(
            phone_webhook_url="https://phone.example.com"
        )
        
        alert = Alert(
            name="test_alert",
            level=AlertLevel.EMERGENCY,
            message="test message",
            timestamp=datetime.now()
        )
        
        # Mock aiohttp.ClientSession.post to raise ClientError
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = aiohttp.ClientError("Connection failed")
            
            # 不应抛出异常，只记录错误
            await manager._send_phone_alert(alert)
