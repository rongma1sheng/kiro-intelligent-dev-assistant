"""Unit Tests: Monitoring and Reliability Integration

白皮书依据: 第十二章 12.1 监控与可靠性集成

测试目标:
- 监控与可靠性系统集成
- 健康检查结果同步到Prometheus
- 跨章节事件发布
- Redis自动恢复
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.integration.monitoring_reliability_integration import (
    MonitoringReliabilityIntegration,
    create_monitoring_reliability_integration
)
from src.monitoring.prometheus_collector import PrometheusMetricsCollector
from src.core.health_checker import (
    HealthChecker,
    HealthCheckResult,
    ComponentHealth,
    ComponentStatus,
    OverallStatus
)
from src.infra.cross_chapter_event_bus import CrossChapterEventBus, CrossChapterEventType
from src.infra.event_bus import EventBus


class TestMonitoringReliabilityIntegration:
    """监控与可靠性集成测试"""
    
    @pytest.fixture
    async def event_bus(self):
        """创建事件总线"""
        bus = EventBus()
        await bus.initialize()
        yield bus
        await bus.shutdown()
    
    @pytest.fixture
    async def cross_chapter_bus(self, event_bus):
        """创建跨章节事件总线"""
        bus = CrossChapterEventBus(event_bus)
        await bus.initialize()
        return bus
    
    @pytest.fixture
    def prometheus_collector(self):
        """创建Prometheus采集器（Mock）"""
        collector = Mock(spec=PrometheusMetricsCollector)
        collector.register_custom_metric = Mock(return_value=True)
        collector.get_metric = Mock(return_value=Mock(set=Mock(), inc=Mock(), labels=Mock(return_value=Mock(set=Mock()))))
        return collector
    
    @pytest.fixture
    def health_checker(self):
        """创建健康检查器（Mock）"""
        checker = Mock(spec=HealthChecker)
        checker.check_interval = 30
        checker.run_health_check = Mock()
        checker.attempt_redis_recovery = Mock(return_value=True)
        return checker
    
    @pytest.fixture
    async def integration(self, prometheus_collector, health_checker, cross_chapter_bus):
        """创建集成器"""
        integration = MonitoringReliabilityIntegration(
            prometheus_collector=prometheus_collector,
            health_checker=health_checker,
            cross_chapter_bus=cross_chapter_bus
        )
        return integration
    
    @pytest.mark.asyncio
    async def test_initialization(self, integration):
        """测试初始化"""
        assert integration.prometheus_collector is not None
        assert integration.health_checker is not None
        assert integration.cross_chapter_bus is not None
        assert integration.running is False
        assert integration.stats['health_checks_performed'] == 0
    
    @pytest.mark.asyncio
    async def test_start_stop(self, integration):
        """测试启动和停止"""
        await integration.start()
        assert integration.running is True
        assert integration.stats['start_time'] is not None
        
        await integration.stop()
        assert integration.running is False
    
    @pytest.mark.asyncio
    async def test_update_health_metrics(self, integration, prometheus_collector):
        """测试更新健康指标"""
        # 创建健康检查结果
        health_result = HealthCheckResult(
            overall_status=OverallStatus.HEALTHY,
            components={
                'redis': ComponentHealth(
                    status=ComponentStatus.HEALTHY,
                    message="Redis正常",
                    metrics={}
                )
            },
            timestamp=datetime.now()
        )
        
        # 更新指标
        await integration._update_health_metrics(health_result)
        
        # 验证指标被更新
        assert prometheus_collector.get_metric.called
    
    @pytest.mark.asyncio
    async def test_handle_redis_failure_with_recovery(self, integration, health_checker, cross_chapter_bus):
        """测试Redis失败并成功恢复"""
        redis_health = ComponentHealth(
            status=ComponentStatus.UNHEALTHY,
            message="Redis连接失败",
            metrics={}
        )
        
        # 模拟恢复成功
        health_checker.attempt_redis_recovery.return_value = True
        
        # 处理Redis失败
        await integration._handle_redis_failure(redis_health)
        
        # 验证恢复被尝试
        assert health_checker.attempt_redis_recovery.called
        assert integration.stats['redis_recoveries_attempted'] == 1
        assert integration.stats['redis_recoveries_succeeded'] == 1
    
    @pytest.mark.asyncio
    async def test_handle_redis_failure_without_recovery(self, integration, health_checker, cross_chapter_bus):
        """测试Redis失败且恢复失败"""
        redis_health = ComponentHealth(
            status=ComponentStatus.UNHEALTHY,
            message="Redis连接失败",
            metrics={}
        )
        
        # 模拟恢复失败
        health_checker.attempt_redis_recovery.return_value = False
        
        # 订阅事件
        received_events = []
        
        async def handler(event):
            received_events.append(event)
        
        await cross_chapter_bus.subscribe(
            CrossChapterEventType.HEALTH_CHECK_FAILED,
            handler
        )
        
        # 处理Redis失败
        await integration._handle_redis_failure(redis_health)
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        # 验证事件被发布
        assert integration.stats['redis_recoveries_attempted'] == 1
        assert integration.stats['redis_recoveries_succeeded'] == 0
        assert integration.stats['events_published'] == 1
        assert len(received_events) == 1
    
    @pytest.mark.asyncio
    async def test_publish_health_check_failed_event(self, integration, cross_chapter_bus):
        """测试发布健康检查失败事件"""
        health_result = HealthCheckResult(
            overall_status=OverallStatus.CRITICAL,
            components={
                'redis': ComponentHealth(
                    status=ComponentStatus.UNHEALTHY,
                    message="Redis失败",
                    metrics={}
                ),
                'gpu': ComponentHealth(
                    status=ComponentStatus.UNHEALTHY,
                    message="GPU失败",
                    metrics={}
                )
            },
            timestamp=datetime.now()
        )
        
        # 订阅事件
        received_events = []
        
        async def handler(event):
            received_events.append(event)
        
        await cross_chapter_bus.subscribe(
            CrossChapterEventType.HEALTH_CHECK_FAILED,
            handler
        )
        
        # 发布事件
        await integration._publish_health_check_failed_event(health_result)
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        # 验证事件
        assert len(received_events) == 1
        event = received_events[0]
        assert event.event_type == CrossChapterEventType.HEALTH_CHECK_FAILED
        assert event.source_chapter == 10
        assert event.target_chapter == 13
        assert 'redis' in event.data['failed_components']
        assert 'gpu' in event.data['failed_components']
    
    @pytest.mark.asyncio
    async def test_publish_performance_degradation_event(self, integration, cross_chapter_bus):
        """测试发布性能下降事件"""
        health_result = HealthCheckResult(
            overall_status=OverallStatus.DEGRADED,
            components={
                'memory': ComponentHealth(
                    status=ComponentStatus.DEGRADED,
                    message="内存使用偏高",
                    metrics={}
                )
            },
            timestamp=datetime.now()
        )
        
        # 订阅事件
        received_events = []
        
        async def handler(event):
            received_events.append(event)
        
        await cross_chapter_bus.subscribe(
            CrossChapterEventType.PERFORMANCE_DEGRADATION,
            handler
        )
        
        # 发布事件
        await integration._publish_performance_degradation_event(health_result)
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        # 验证事件
        assert len(received_events) == 1
        event = received_events[0]
        assert event.event_type == CrossChapterEventType.PERFORMANCE_DEGRADATION
        assert 'memory' in event.data['degraded_components']
    
    @pytest.mark.asyncio
    async def test_health_status_conversion(self, integration):
        """测试健康状态转换"""
        assert integration._health_status_to_value(OverallStatus.HEALTHY) == 0.0
        assert integration._health_status_to_value(OverallStatus.DEGRADED) == 1.0
        assert integration._health_status_to_value(OverallStatus.UNHEALTHY) == 2.0
        assert integration._health_status_to_value(OverallStatus.CRITICAL) == 3.0
    
    @pytest.mark.asyncio
    async def test_component_status_conversion(self, integration):
        """测试组件状态转换"""
        assert integration._component_status_to_value(ComponentStatus.HEALTHY) == 0.0
        assert integration._component_status_to_value(ComponentStatus.DEGRADED) == 1.0
        assert integration._component_status_to_value(ComponentStatus.UNHEALTHY) == 2.0
    
    @pytest.mark.asyncio
    async def test_get_stats(self, integration):
        """测试获取统计信息"""
        integration.stats['start_time'] = datetime.now()
        integration.stats['redis_recoveries_attempted'] = 10
        integration.stats['redis_recoveries_succeeded'] = 8
        
        stats = integration.get_stats()
        
        assert 'uptime_seconds' in stats
        assert stats['redis_recovery_success_rate'] == 0.8


class TestCreateIntegration:
    """测试创建集成器函数"""
    
    @pytest.mark.asyncio
    async def test_create_monitoring_reliability_integration(self):
        """测试创建集成器"""
        # 创建Mock对象
        prometheus_collector = Mock(spec=PrometheusMetricsCollector)
        prometheus_collector.register_custom_metric = Mock(return_value=True)
        prometheus_collector.get_metric = Mock(return_value=Mock(set=Mock(), inc=Mock()))
        
        health_checker = Mock(spec=HealthChecker)
        health_checker.check_interval = 30
        
        event_bus = EventBus()
        await event_bus.initialize()
        
        cross_chapter_bus = CrossChapterEventBus(event_bus)
        await cross_chapter_bus.initialize()
        
        # 创建集成器
        integration = await create_monitoring_reliability_integration(
            prometheus_collector=prometheus_collector,
            health_checker=health_checker,
            cross_chapter_bus=cross_chapter_bus
        )
        
        # 验证
        assert integration is not None
        assert integration.running is True
        
        # 清理
        await integration.stop()
        await event_bus.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
