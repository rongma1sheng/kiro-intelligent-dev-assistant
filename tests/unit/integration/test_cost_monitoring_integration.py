"""Unit tests for Cost Monitoring Integration

白皮书依据: 第十八章 18.2 成本监控与追踪, 第十二章 12.3 成本追踪与监控集成
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.integration.cost_monitoring_integration import (
    CostMonitoringIntegration,
    CostMonitoringStatus,
    get_cost_monitoring_integration,
    track_api_cost
)
from src.monitoring.cost_tracker import CostTracker
from src.monitoring.cost_predictor import CostPredictor
from src.monitoring.prometheus_collector import PrometheusMetricsCollector, MetricType
from src.infra.cross_chapter_event_bus import (
    CrossChapterEventBus,
    CrossChapterEventType,
    CrossChapterEvent
)
from src.infra.event_bus import EventBus, EventPriority


class TestCostMonitoringIntegration:
    """测试成本监控集成类"""
    
    @pytest.fixture
    def mock_cost_tracker(self):
        """创建模拟成本追踪器"""
        tracker = Mock(spec=CostTracker)
        tracker.daily_budget = 50.0
        tracker.monthly_budget = 1500.0
        tracker.track_api_call = Mock(return_value=0.05)
        tracker.get_budget_status = Mock(return_value={
            'daily_cost': 25.0,
            'daily_budget': 50.0,
            'daily_utilization': 0.5,
            'is_daily_exceeded': False,
            'monthly_cost': 500.0,
            'monthly_budget': 1500.0,
            'monthly_utilization': 0.33,
            'is_monthly_exceeded': False
        })
        tracker.get_cost_breakdown = Mock(return_value={
            'soldier': 10.0,
            'commander': 15.0
        })
        return tracker
    
    @pytest.fixture
    def mock_prometheus_collector(self):
        """创建模拟Prometheus采集器"""
        collector = Mock(spec=PrometheusMetricsCollector)
        collector.register_custom_metric = Mock(return_value=True)
        
        # 创建模拟指标对象
        mock_metric = Mock()
        mock_metric.set = Mock()
        mock_metric.labels = Mock(return_value=mock_metric)
        mock_metric.inc = Mock()
        
        collector.get_metric = Mock(return_value=mock_metric)
        
        return collector
    
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
    def integration(self, mock_cost_tracker, mock_prometheus_collector, mock_event_bus):
        """创建集成实例"""
        return CostMonitoringIntegration(
            cost_tracker=mock_cost_tracker,
            prometheus_collector=mock_prometheus_collector,
            event_bus=mock_event_bus,
            sync_interval=60
        )
    
    def test_initialization(self, integration, mock_cost_tracker, mock_prometheus_collector):
        """测试初始化"""
        assert integration.cost_tracker == mock_cost_tracker
        assert integration.prometheus_collector == mock_prometheus_collector
        assert integration.sync_interval == 60
        assert integration.cost_predictor is not None
        
        # 验证指标注册
        assert mock_prometheus_collector.register_custom_metric.call_count >= 8
    
    def test_initialization_invalid_params(self, mock_prometheus_collector, mock_event_bus):
        """测试无效参数初始化"""
        with pytest.raises(ValueError, match="cost_tracker不能为None"):
            CostMonitoringIntegration(
                cost_tracker=None,
                prometheus_collector=mock_prometheus_collector,
                event_bus=mock_event_bus
            )
        
        with pytest.raises(ValueError, match="prometheus_collector不能为None"):
            CostMonitoringIntegration(
                cost_tracker=Mock(),
                prometheus_collector=None,
                event_bus=mock_event_bus
            )
        
        with pytest.raises(ValueError, match="同步间隔必须 >= 1秒"):
            CostMonitoringIntegration(
                cost_tracker=Mock(),
                prometheus_collector=mock_prometheus_collector,
                event_bus=mock_event_bus,
                sync_interval=0
            )
    
    @pytest.mark.asyncio
    async def test_initialize(self, integration):
        """测试初始化方法"""
        await integration.initialize()
        
        assert integration.stats['start_time'] is not None
    
    @pytest.mark.asyncio
    async def test_initialize_without_event_bus(self, mock_cost_tracker, mock_prometheus_collector):
        """测试无事件总线的初始化"""
        integration = CostMonitoringIntegration(
            cost_tracker=mock_cost_tracker,
            prometheus_collector=mock_prometheus_collector,
            event_bus=None
        )
        
        with patch('src.infra.cross_chapter_event_bus.get_cross_chapter_event_bus') as mock_get:
            mock_bus = Mock(spec=CrossChapterEventBus)
            mock_get.return_value = mock_bus
            
            await integration.initialize()
            
            assert integration.event_bus == mock_bus
            mock_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_track_and_publish(self, integration):
        """测试追踪并发布"""
        await integration.initialize()
        
        cost = await integration.track_and_publish(
            service='soldier',
            model='deepseek-chat',
            input_tokens=1000,
            output_tokens=500
        )
        
        # 验证成本追踪
        integration.cost_tracker.track_api_call.assert_called_once_with(
            service='soldier',
            model='deepseek-chat',
            input_tokens=1000,
            output_tokens=500
        )
        
        # 验证统计信息
        assert integration.stats['total_tracked'] == 1
        
        # 验证Prometheus指标更新
        assert integration.prometheus_collector.get_metric.called
    
    @pytest.mark.asyncio
    async def test_sync_cost_metrics(self, integration):
        """测试同步成本指标"""
        await integration.initialize()
        
        # Mock成本预测器
        integration.cost_predictor.predict_monthly_cost = Mock(return_value={
            'predicted_monthly': 1200.0,
            'budget_monthly': 1500.0,
            'budget_utilization': 0.8
        })
        
        await integration.sync_cost_metrics()
        
        # 验证统计信息
        assert integration.stats['total_synced'] == 1
        
        # 验证指标更新
        assert integration.prometheus_collector.get_metric.called
    
    @pytest.mark.asyncio
    async def test_check_budget_limits_daily_exceeded(self, integration):
        """测试检查预算限制 - 日预算超限"""
        await integration.initialize()
        
        # Mock预算状态 - 日预算超限
        integration.cost_tracker.get_budget_status = Mock(return_value={
            'daily_cost': 60.0,
            'daily_budget': 50.0,
            'daily_utilization': 1.2,
            'is_daily_exceeded': True,
            'monthly_cost': 500.0,
            'monthly_budget': 1500.0,
            'monthly_utilization': 0.33,
            'is_monthly_exceeded': False
        })
        
        await integration._check_budget_limits()
        
        # 验证事件发布
        integration.event_bus.publish.assert_called()
        published_event = integration.event_bus.publish.call_args[0][0]
        assert published_event.event_type == CrossChapterEventType.COST_LIMIT_EXCEEDED
        assert published_event.source_chapter == 18
        assert published_event.target_chapter == 13
        assert published_event.data['limit_type'] == 'daily'
    
    @pytest.mark.asyncio
    async def test_check_budget_limits_monthly_exceeded(self, integration):
        """测试检查预算限制 - 月预算超限"""
        await integration.initialize()
        
        # Mock预算状态 - 月预算超限
        integration.cost_tracker.get_budget_status = Mock(return_value={
            'daily_cost': 40.0,
            'daily_budget': 50.0,
            'daily_utilization': 0.8,
            'is_daily_exceeded': False,
            'monthly_cost': 1600.0,
            'monthly_budget': 1500.0,
            'monthly_utilization': 1.07,
            'is_monthly_exceeded': True
        })
        
        await integration._check_budget_limits()
        
        # 验证事件发布
        integration.event_bus.publish.assert_called()
        published_event = integration.event_bus.publish.call_args[0][0]
        assert published_event.event_type == CrossChapterEventType.COST_LIMIT_EXCEEDED
        assert published_event.data['limit_type'] == 'monthly'
    
    @pytest.mark.asyncio
    async def test_check_budget_limits_prediction_exceeded(self, integration):
        """测试检查预算限制 - 预测超限"""
        await integration.initialize()
        
        # Mock预算状态 - 未超限
        integration.cost_tracker.get_budget_status = Mock(return_value={
            'daily_cost': 40.0,
            'daily_budget': 50.0,
            'daily_utilization': 0.8,
            'is_daily_exceeded': False,
            'monthly_cost': 1200.0,
            'monthly_budget': 1500.0,
            'monthly_utilization': 0.8,
            'is_monthly_exceeded': False
        })
        
        # Mock预测超限
        integration.cost_predictor.alert_if_over_budget = Mock(return_value={
            'type': 'budget_exceeded',
            'predicted_monthly': 1600.0,
            'budget_monthly': 1500.0,
            'excess_amount': 100.0,
            'budget_utilization': 1.07,
            'message': '预测月成本超预算'
        })
        
        await integration._check_budget_limits()
        
        # 验证事件发布
        integration.event_bus.publish.assert_called()
        published_event = integration.event_bus.publish.call_args[0][0]
        assert published_event.event_type == CrossChapterEventType.COST_BUDGET_WARNING
    
    @pytest.mark.asyncio
    async def test_publish_cost_limit_exceeded_event(self, integration):
        """测试发布成本限制超限事件"""
        await integration.initialize()
        
        await integration._publish_cost_limit_exceeded_event(
            limit_type='daily',
            current_cost=60.0,
            budget=50.0,
            utilization=1.2
        )
        
        # 验证事件发布
        integration.event_bus.publish.assert_called_once()
        published_event = integration.event_bus.publish.call_args[0][0]
        
        assert published_event.event_type == CrossChapterEventType.COST_LIMIT_EXCEEDED
        assert published_event.source_chapter == 18
        assert published_event.target_chapter == 13
        assert published_event.priority == EventPriority.HIGH
        assert published_event.data['limit_type'] == 'daily'
        assert published_event.data['current_cost'] == 60.0
        assert published_event.data['budget'] == 50.0
        assert published_event.data['utilization'] == 1.2
        assert published_event.data['excess_amount'] == 10.0
        
        # 验证统计信息
        assert integration.stats['events_published'] == 1
        assert integration.stats['budget_alerts'] == 1
    
    @pytest.mark.asyncio
    async def test_publish_cost_budget_warning_event(self, integration):
        """测试发布成本预算警告事件"""
        await integration.initialize()
        
        alert = {
            'predicted_monthly': 1600.0,
            'budget_monthly': 1500.0,
            'excess_amount': 100.0,
            'budget_utilization': 1.07,
            'message': '预测月成本超预算'
        }
        
        await integration._publish_cost_budget_warning_event(alert)
        
        # 验证事件发布
        integration.event_bus.publish.assert_called_once()
        published_event = integration.event_bus.publish.call_args[0][0]
        
        assert published_event.event_type == CrossChapterEventType.COST_BUDGET_WARNING
        assert published_event.source_chapter == 18
        assert published_event.target_chapter == 13
        assert published_event.priority == EventPriority.NORMAL
        assert published_event.data['predicted_monthly'] == 1600.0
        assert published_event.data['message'] == '预测月成本超预算'
        
        # 验证统计信息
        assert integration.stats['events_published'] == 1
    
    @pytest.mark.asyncio
    async def test_publish_event_without_event_bus(self, mock_cost_tracker, mock_prometheus_collector):
        """测试无事件总线时发布事件"""
        integration = CostMonitoringIntegration(
            cost_tracker=mock_cost_tracker,
            prometheus_collector=mock_prometheus_collector,
            event_bus=None
        )
        await integration.initialize()
        
        # 设置event_bus为None
        integration.event_bus = None
        
        # 应该不抛出异常，只是记录警告
        await integration._publish_cost_limit_exceeded_event(
            limit_type='daily',
            current_cost=60.0,
            budget=50.0,
            utilization=1.2
        )
        
        # 验证统计信息未更新
        assert integration.stats['events_published'] == 0
    
    @pytest.mark.asyncio
    async def test_get_monitoring_status(self, integration):
        """测试获取监控状态"""
        await integration.initialize()
        
        # Mock预测结果
        integration.cost_predictor.predict_monthly_cost = Mock(return_value={
            'predicted_monthly': 1200.0,
            'budget_monthly': 1500.0,
            'budget_utilization': 0.8
        })
        
        status = await integration.get_monitoring_status()
        
        assert isinstance(status, CostMonitoringStatus)
        assert status.daily_cost == 25.0
        assert status.monthly_cost == 500.0
        assert status.predicted_monthly == 1200.0
        assert status.daily_budget_utilization == 0.5
        assert status.monthly_budget_utilization == 0.33
        assert status.is_daily_exceeded is False
        assert status.is_monthly_exceeded is False
        assert status.timestamp is not None
    
    def test_get_stats(self, integration):
        """测试获取统计信息"""
        integration.stats['start_time'] = datetime.now()
        integration.stats['total_tracked'] = 100
        integration.stats['total_synced'] = 50
        integration.stats['events_published'] = 5
        integration.stats['budget_alerts'] = 2
        
        stats = integration.get_stats()
        
        assert stats['total_tracked'] == 100
        assert stats['total_synced'] == 50
        assert stats['events_published'] == 5
        assert stats['budget_alerts'] == 2
        assert 'uptime_seconds' in stats
        assert 'tracking_rate' in stats
        assert 'sync_rate' in stats
    
    @pytest.mark.asyncio
    async def test_register_cost_metrics(self, integration):
        """测试注册成本指标"""
        # 验证所有成本指标都已注册
        calls = integration.prometheus_collector.register_custom_metric.call_args_list
        
        metric_names = [call[1]['name'] for call in calls]
        
        assert 'mia_cost_daily_total' in metric_names
        assert 'mia_cost_monthly_total' in metric_names
        assert 'mia_cost_predicted_monthly' in metric_names
        assert 'mia_cost_by_service' in metric_names
        assert 'mia_cost_daily_budget_utilization' in metric_names
        assert 'mia_cost_monthly_budget_utilization' in metric_names
        assert 'mia_cost_api_calls_total' in metric_names
        assert 'mia_cost_budget_exceeded' in metric_names
    
    @pytest.mark.asyncio
    async def test_sync_cost_metrics_updates_all_metrics(self, integration):
        """测试同步成本指标更新所有指标"""
        await integration.initialize()
        
        # Mock预测结果
        integration.cost_predictor.predict_monthly_cost = Mock(return_value={
            'predicted_monthly': 1200.0
        })
        
        await integration.sync_cost_metrics()
        
        # 验证所有指标都被更新（7个get_metric调用）
        assert integration.prometheus_collector.get_metric.call_count >= 7
    
    @pytest.mark.asyncio
    async def test_track_and_publish_updates_prometheus_counter(self, integration):
        """测试追踪并发布更新Prometheus计数器"""
        await integration.initialize()
        
        mock_metric = Mock()
        mock_metric.labels = Mock(return_value=mock_metric)
        mock_metric.inc = Mock()
        
        integration.prometheus_collector.get_metric = Mock(return_value=mock_metric)
        
        await integration.track_and_publish(
            service='soldier',
            model='deepseek-chat',
            input_tokens=1000,
            output_tokens=500
        )
        
        # 验证计数器增加
        mock_metric.labels.assert_called_with(service='soldier', model='deepseek-chat')
        mock_metric.inc.assert_called_once()


class TestGlobalFunctions:
    """测试全局函数"""
    
    @pytest.mark.asyncio
    async def test_get_cost_monitoring_integration(self):
        """测试获取全局集成实例"""
        # 重置全局实例
        import src.integration.cost_monitoring_integration as module
        module._global_cost_monitoring_integration = None
        
        mock_tracker = Mock(spec=CostTracker)
        mock_collector = Mock(spec=PrometheusMetricsCollector)
        mock_collector.register_custom_metric = Mock(return_value=True)
        mock_collector.get_metric = Mock(return_value=Mock())
        
        mock_bus = Mock(spec=CrossChapterEventBus)
        
        integration = await get_cost_monitoring_integration(
            cost_tracker=mock_tracker,
            prometheus_collector=mock_collector,
            event_bus=mock_bus
        )
        
        assert integration is not None
        assert integration.cost_tracker == mock_tracker
        assert integration.prometheus_collector == mock_collector
        assert integration.event_bus == mock_bus
        
        # 再次调用应该返回同一实例
        integration2 = await get_cost_monitoring_integration()
        assert integration2 is integration
    
    @pytest.mark.asyncio
    async def test_get_cost_monitoring_integration_without_params(self):
        """测试无参数获取全局集成实例"""
        # 重置全局实例
        import src.integration.cost_monitoring_integration as module
        module._global_cost_monitoring_integration = None
        
        with pytest.raises(ValueError, match="首次调用必须提供cost_tracker和prometheus_collector"):
            await get_cost_monitoring_integration()
    
    @pytest.mark.asyncio
    async def test_track_api_cost(self):
        """测试全局API成本追踪函数"""
        # 重置全局实例
        import src.integration.cost_monitoring_integration as module
        module._global_cost_monitoring_integration = None
        
        with patch('src.integration.cost_monitoring_integration.get_cost_monitoring_integration') as mock_get:
            mock_integration = Mock(spec=CostMonitoringIntegration)
            mock_integration.track_and_publish = AsyncMock(return_value=0.05)
            mock_get.return_value = mock_integration
            
            cost = await track_api_cost(
                service='soldier',
                model='deepseek-chat',
                input_tokens=1000,
                output_tokens=500
            )
            
            assert cost == 0.05
            mock_integration.track_and_publish.assert_called_once_with(
                service='soldier',
                model='deepseek-chat',
                input_tokens=1000,
                output_tokens=500
            )
