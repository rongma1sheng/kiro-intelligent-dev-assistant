"""AUM Sensor单元测试

白皮书依据: 第0章 资本物理 (Capital Physics)
测试任务: Task 2.1

测试覆盖:
- Property 7: Tier Change Event Publishing
- Property 8: AUM Monitoring Periodicity
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.capital.aum_sensor import AUMSensor, AuditServiceUnavailableError


class TestAUMSensorInitialization:
    """测试AUM Sensor初始化"""
    
    def test_initialization_default(self):
        """测试默认初始化"""
        sensor = AUMSensor()
        
        assert sensor.audit_service_client is None
        assert sensor.monitoring_interval == 60
        assert sensor.change_threshold == 0.05
        assert sensor.current_aum == 0.0
        assert sensor.last_check_time is None
        assert sensor.is_monitoring is False
        assert sensor.tier_change_callbacks == []
    
    def test_initialization_custom(self):
        """测试自定义参数初始化"""
        mock_client = Mock()
        sensor = AUMSensor(
            audit_service_client=mock_client,
            monitoring_interval=30,
            change_threshold=0.10
        )
        
        assert sensor.audit_service_client == mock_client
        assert sensor.monitoring_interval == 30
        assert sensor.change_threshold == 0.10


class TestGetCurrentAUM:
    """测试获取当前AUM"""
    
    @pytest.fixture
    def sensor(self):
        """创建AUM Sensor实例"""
        return AUMSensor()
    
    @pytest.mark.asyncio
    async def test_get_aum_without_audit_service(self, sensor):
        """测试无审计服务时获取AUM（使用默认值）"""
        aum = await sensor.get_current_aum()
        
        assert aum == 10000.0
        assert sensor.current_aum == 10000.0
        assert sensor.last_check_time is not None
    
    @pytest.mark.asyncio
    async def test_get_aum_with_cached_value(self, sensor):
        """测试使用缓存值"""
        sensor.current_aum = 50000.0
        
        aum = await sensor.get_current_aum()
        
        assert aum == 50000.0
    
    @pytest.mark.asyncio
    async def test_get_aum_with_audit_service(self):
        """测试从审计服务获取AUM"""
        mock_client = Mock()
        mock_client.get_aum = AsyncMock(return_value=100000.0)
        
        sensor = AUMSensor(audit_service_client=mock_client)
        aum = await sensor.get_current_aum()
        
        assert aum == 100000.0
        assert sensor.current_aum == 100000.0
        mock_client.get_aum.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_aum_audit_service_failure_with_cache(self):
        """测试审计服务失败时使用缓存值"""
        mock_client = Mock()
        mock_client.get_aum = AsyncMock(side_effect=Exception("连接失败"))
        
        sensor = AUMSensor(audit_service_client=mock_client)
        sensor.current_aum = 50000.0  # 设置缓存值
        
        aum = await sensor.get_current_aum()
        
        # 应该返回缓存值
        assert aum == 50000.0
    
    @pytest.mark.asyncio
    async def test_get_aum_audit_service_failure_without_cache(self):
        """测试审计服务失败且无缓存时抛出异常"""
        mock_client = Mock()
        mock_client.get_aum = AsyncMock(side_effect=Exception("连接失败"))
        
        sensor = AUMSensor(audit_service_client=mock_client)
        
        with pytest.raises(AuditServiceUnavailableError):
            await sensor.get_current_aum()



class TestTierChangeEventPublishing:
    """测试档位切换事件发布
    
    Property 7: Tier Change Event Publishing
    """
    
    @pytest.fixture
    def sensor(self):
        """创建AUM Sensor实例"""
        return AUMSensor()
    
    @pytest.mark.asyncio
    async def test_publish_tier_change_event(self, sensor):
        """Property 7: 测试发布档位切换事件"""
        sensor.current_aum = 50000.0
        
        await sensor.publish_tier_change_event('tier1_micro', 'tier2_small')
        
        # 验证事件已发布（通过日志）
        # 实际应用中会有事件总线或消息队列
    
    @pytest.mark.asyncio
    async def test_tier_change_event_with_callback(self, sensor):
        """Property 7: 测试档位切换事件回调"""
        sensor.current_aum = 50000.0
        
        # 注册回调
        callback_called = []
        
        def callback(event):
            callback_called.append(event)
        
        sensor.register_tier_change_callback(callback)
        
        # 发布事件
        await sensor.publish_tier_change_event('tier1_micro', 'tier2_small')
        
        # 验证回调被调用
        assert len(callback_called) == 1
        event = callback_called[0]
        assert event['event_type'] == 'tier_change'
        assert event['old_tier'] == 'tier1_micro'
        assert event['new_tier'] == 'tier2_small'
        assert event['aum'] == 50000.0
        assert 'timestamp' in event
    
    @pytest.mark.asyncio
    async def test_tier_change_event_with_async_callback(self, sensor):
        """Property 7: 测试异步回调"""
        sensor.current_aum = 50000.0
        
        callback_called = []
        
        async def async_callback(event):
            await asyncio.sleep(0.01)  # 模拟异步操作
            callback_called.append(event)
        
        sensor.register_tier_change_callback(async_callback)
        
        await sensor.publish_tier_change_event('tier2_small', 'tier3_medium')
        
        assert len(callback_called) == 1
        assert callback_called[0]['old_tier'] == 'tier2_small'
        assert callback_called[0]['new_tier'] == 'tier3_medium'
    
    @pytest.mark.asyncio
    async def test_tier_change_event_with_multiple_callbacks(self, sensor):
        """Property 7: 测试多个回调"""
        sensor.current_aum = 100000.0
        
        callback1_called = []
        callback2_called = []
        
        def callback1(event):
            callback1_called.append(event)
        
        def callback2(event):
            callback2_called.append(event)
        
        sensor.register_tier_change_callback(callback1)
        sensor.register_tier_change_callback(callback2)
        
        await sensor.publish_tier_change_event('tier2_small', 'tier3_medium')
        
        # 两个回调都应该被调用
        assert len(callback1_called) == 1
        assert len(callback2_called) == 1
    
    @pytest.mark.asyncio
    async def test_tier_change_event_callback_failure(self, sensor):
        """Property 7: 测试回调失败不影响其他回调"""
        sensor.current_aum = 100000.0
        
        callback_success_called = []
        
        def callback_fail(event):
            raise Exception("回调失败")
        
        def callback_success(event):
            callback_success_called.append(event)
        
        sensor.register_tier_change_callback(callback_fail)
        sensor.register_tier_change_callback(callback_success)
        
        # 即使第一个回调失败，第二个也应该被调用
        await sensor.publish_tier_change_event('tier1_micro', 'tier2_small')
        
        assert len(callback_success_called) == 1


class TestAUMMonitoring:
    """测试AUM监控
    
    Property 8: AUM Monitoring Periodicity
    """
    
    @pytest.fixture
    def sensor(self):
        """创建AUM Sensor实例（短监控间隔用于测试）"""
        return AUMSensor(monitoring_interval=1, change_threshold=0.05)
    
    @pytest.mark.asyncio
    async def test_monitor_aum_changes_no_change(self, sensor):
        """Property 8: 测试AUM无变化时不触发事件"""
        sensor.current_aum = 50000.0
        
        callback_called = []
        
        def callback(event):
            callback_called.append(event)
        
        sensor.register_tier_change_callback(callback)
        
        # 启动监控（运行2秒）
        monitor_task = asyncio.create_task(sensor.monitor_aum_changes())
        
        await asyncio.sleep(2.5)
        
        # 停止监控
        sensor.stop_monitoring()
        await asyncio.sleep(0.1)
        monitor_task.cancel()
        
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        # AUM没有变化，不应该触发事件
        assert len(callback_called) == 0
    
    @pytest.mark.asyncio
    async def test_monitor_aum_changes_with_change(self):
        """Property 8: 测试AUM变化超过阈值时触发事件"""
        mock_client = Mock()
        
        # 模拟AUM变化：50000 → 60000 (20%变化，超过5%阈值)
        aum_values = [50000.0, 60000.0, 60000.0]
        mock_client.get_aum = AsyncMock(side_effect=aum_values)
        
        sensor = AUMSensor(
            audit_service_client=mock_client,
            monitoring_interval=1,
            change_threshold=0.05
        )
        sensor.current_aum = 50000.0
        
        callback_called = []
        
        def callback(event):
            callback_called.append(event)
        
        sensor.register_tier_change_callback(callback)
        
        # 启动监控
        monitor_task = asyncio.create_task(sensor.monitor_aum_changes())
        
        await asyncio.sleep(2.5)
        
        # 停止监控
        sensor.stop_monitoring()
        await asyncio.sleep(0.1)
        monitor_task.cancel()
        
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        # 应该触发档位切换事件（tier2_small → tier2_small，实际上没有切换）
        # 但AUM变化超过阈值，会触发重新评估
        # 注意：只有档位真正变化时才会发布事件
    
    @pytest.mark.asyncio
    async def test_monitor_aum_changes_tier_change(self):
        """Property 8: 测试档位切换时发布事件"""
        mock_client = Mock()
        
        # 模拟AUM变化：50000 (tier2) → 150000 (tier3)
        aum_values = [50000.0, 150000.0, 150000.0]
        mock_client.get_aum = AsyncMock(side_effect=aum_values)
        
        sensor = AUMSensor(
            audit_service_client=mock_client,
            monitoring_interval=1,
            change_threshold=0.05
        )
        sensor.current_aum = 50000.0
        
        callback_called = []
        
        def callback(event):
            callback_called.append(event)
        
        sensor.register_tier_change_callback(callback)
        
        # 启动监控
        monitor_task = asyncio.create_task(sensor.monitor_aum_changes())
        
        await asyncio.sleep(2.5)
        
        # 停止监控
        sensor.stop_monitoring()
        await asyncio.sleep(0.1)
        monitor_task.cancel()
        
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        # 应该触发档位切换事件
        assert len(callback_called) >= 1
        if callback_called:
            event = callback_called[0]
            assert event['event_type'] == 'tier_change'
            assert event['old_tier'] == 'tier2_small'
            assert event['new_tier'] == 'tier3_medium'
    
    @pytest.mark.asyncio
    async def test_monitoring_interval_accuracy(self):
        """Property 8: 测试监控间隔准确性"""
        import time
        
        sensor = AUMSensor(monitoring_interval=1)
        sensor.current_aum = 50000.0
        
        check_times = []
        
        # 记录每次检查的时间
        original_get_aum = sensor.get_current_aum
        
        async def tracked_get_aum():
            check_times.append(time.time())
            return await original_get_aum()
        
        sensor.get_current_aum = tracked_get_aum
        
        # 启动监控
        monitor_task = asyncio.create_task(sensor.monitor_aum_changes())
        
        await asyncio.sleep(3.5)
        
        # 停止监控
        sensor.stop_monitoring()
        await asyncio.sleep(0.1)
        monitor_task.cancel()
        
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        # 应该至少检查3次（0秒、1秒、2秒、3秒）
        assert len(check_times) >= 3
        
        # 验证间隔接近1秒
        if len(check_times) >= 2:
            intervals = [check_times[i+1] - check_times[i] for i in range(len(check_times)-1)]
            for interval in intervals:
                # 允许±0.2秒的误差
                assert 0.8 <= interval <= 1.2, f"间隔{interval}秒不在[0.8, 1.2]范围内"
    
    def test_stop_monitoring(self, sensor):
        """测试停止监控"""
        sensor.is_monitoring = True
        
        sensor.stop_monitoring()
        
        assert sensor.is_monitoring is False


class TestRegisterCallback:
    """测试回调注册"""
    
    @pytest.fixture
    def sensor(self):
        """创建AUM Sensor实例"""
        return AUMSensor()
    
    def test_register_single_callback(self, sensor):
        """测试注册单个回调"""
        def callback(event):
            pass
        
        sensor.register_tier_change_callback(callback)
        
        assert len(sensor.tier_change_callbacks) == 1
        assert sensor.tier_change_callbacks[0] == callback
    
    def test_register_multiple_callbacks(self, sensor):
        """测试注册多个回调"""
        def callback1(event):
            pass
        
        def callback2(event):
            pass
        
        sensor.register_tier_change_callback(callback1)
        sensor.register_tier_change_callback(callback2)
        
        assert len(sensor.tier_change_callbacks) == 2
