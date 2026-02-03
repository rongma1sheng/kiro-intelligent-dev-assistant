"""Integration Tests for Cross-Chapter Flows

白皮书依据: 第十二章 12.1-12.10 跨章节集成

测试跨章节事件流:
1. 健康检查 → 告警 → 应急响应流程
2. 成本限制 → 熔断器 → 告警流程
3. 风险检测 → 应急响应流程
4. 性能回归 → 告警流程
"""

import pytest
import asyncio
from datetime import datetime

from src.infra.cross_chapter_event_bus import (
    CrossChapterEventBus,
    CrossChapterEventType,
    CrossChapterEvent
)
from src.infra.event_bus import EventBus, EventPriority


class TestHealthCheckAlertEmergencyFlow:
    """测试健康检查 → 告警 → 应急响应流程
    
    白皮书依据: 第十二章 12.1 监控与可靠性集成
    """
    
    @pytest.mark.asyncio
    async def test_health_check_failed_event_flow(self):
        """测试健康检查失败事件流
        
        白皮书依据: 第十章 10.2 健康检查, 第十二章 12.1
        """
        # 创建真实的事件总线
        base_bus = EventBus()
        await base_bus.initialize()
        
        cross_bus = CrossChapterEventBus(base_bus)
        await cross_bus.initialize()
        
        # 订阅HEALTH_CHECK_FAILED事件
        received_events = []
        
        async def alert_handler(event):
            received_events.append(event)
        
        await cross_bus.subscribe(
            event_type=CrossChapterEventType.HEALTH_CHECK_FAILED,
            handler_func=alert_handler,
            handler_id="alert_system"
        )
        
        # 发布健康检查失败事件
        event = CrossChapterEvent(
            event_type=CrossChapterEventType.HEALTH_CHECK_FAILED,
            source_chapter=10,
            target_chapter=13,
            data={
                'component': 'redis',
                'status': 'unhealthy',
                'message': 'Redis connection failed'
            },
            priority=EventPriority.HIGH
        )
        
        success = await cross_bus.publish(event)
        
        # 等待异步处理
        await asyncio.sleep(0.3)
        
        # 验证：事件发布成功
        assert success is True
        
        # 验证：告警系统接收到事件
        assert len(received_events) > 0
        assert received_events[0].data['component'] == 'redis'
        assert received_events[0].data['status'] == 'unhealthy'
        
        await base_bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_health_check_recovery_flow(self):
        """测试健康检查恢复流程
        
        白皮书依据: 第十章 10.2 Redis恢复
        """
        # 创建真实的事件总线
        base_bus = EventBus()
        await base_bus.initialize()
        
        cross_bus = CrossChapterEventBus(base_bus)
        await cross_bus.initialize()
        
        # 订阅HEALTH_CHECK_RECOVERED事件
        received_events = []
        
        async def recovery_handler(event):
            received_events.append(event)
        
        await cross_bus.subscribe(
            event_type=CrossChapterEventType.HEALTH_CHECK_RECOVERED,
            handler_func=recovery_handler,
            handler_id="recovery_monitor"
        )
        
        # 发布恢复事件
        event = CrossChapterEvent(
            event_type=CrossChapterEventType.HEALTH_CHECK_RECOVERED,
            source_chapter=10,
            target_chapter=13,
            data={
                'component': 'redis',
                'timestamp': datetime.now().isoformat()
            },
            priority=EventPriority.NORMAL
        )
        
        success = await cross_bus.publish(event)
        
        # 等待异步处理
        await asyncio.sleep(0.3)
        
        # 验证：恢复事件被发布
        assert success is True
        
        # 验证：监控系统接收到恢复事件
        assert len(received_events) > 0
        assert received_events[0].data['component'] == 'redis'
        
        await base_bus.shutdown()


class TestCostLimitCircuitBreakerAlertFlow:
    """测试成本限制 → 熔断器 → 告警流程
    
    白皮书依据: 第十二章 12.3 成本追踪与监控集成
    """
    
    @pytest.mark.asyncio
    async def test_daily_budget_exceeded_triggers_alert(self):
        """测试日预算超限触发告警
        
        白皮书依据: 第十八章 18.2 成本监控
        """
        # 创建真实的事件总线
        base_bus = EventBus()
        await base_bus.initialize()
        
        cross_bus = CrossChapterEventBus(base_bus)
        await cross_bus.initialize()
        
        # 订阅COST_LIMIT_EXCEEDED事件
        received_events = []
        
        async def alert_handler(event):
            received_events.append(event)
        
        await cross_bus.subscribe(
            event_type=CrossChapterEventType.COST_LIMIT_EXCEEDED,
            handler_func=alert_handler,
            handler_id="cost_alert_system"
        )
        
        # 发布成本超限事件
        event = CrossChapterEvent(
            event_type=CrossChapterEventType.COST_LIMIT_EXCEEDED,
            source_chapter=18,
            target_chapter=13,
            data={
                'limit_type': 'daily',
                'current_cost': 150.0,
                'budget': 100.0,
                'utilization': 1.5,
                'excess_amount': 50.0,
                'timestamp': datetime.now().isoformat()
            },
            priority=EventPriority.HIGH
        )
        
        success = await cross_bus.publish(event)
        
        # 等待异步处理
        await asyncio.sleep(0.3)
        
        # 验证：事件发布成功
        assert success is True
        
        # 验证：告警系统接收到事件
        assert len(received_events) > 0
        cost_event = received_events[0]
        assert cost_event.data['limit_type'] == 'daily'
        assert cost_event.data['current_cost'] > cost_event.data['budget']
        
        await base_bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_monthly_budget_warning_flow(self):
        """测试月预算警告流程
        
        白皮书依据: 第十八章 18.2 成本预测
        """
        # 创建真实的事件总线
        base_bus = EventBus()
        await base_bus.initialize()
        
        cross_bus = CrossChapterEventBus(base_bus)
        await cross_bus.initialize()
        
        # 订阅COST_BUDGET_WARNING事件
        received_events = []
        
        async def warning_handler(event):
            received_events.append(event)
        
        await cross_bus.subscribe(
            event_type=CrossChapterEventType.COST_BUDGET_WARNING,
            handler_func=warning_handler,
            handler_id="cost_warning_system"
        )
        
        # 发布预算警告事件
        event = CrossChapterEvent(
            event_type=CrossChapterEventType.COST_BUDGET_WARNING,
            source_chapter=18,
            target_chapter=13,
            data={
                'predicted_monthly': 1200.0,
                'budget_monthly': 1000.0,
                'excess_amount': 200.0,
                'budget_utilization': 1.2,
                'message': '预测月成本将超出预算',
                'timestamp': datetime.now().isoformat()
            },
            priority=EventPriority.NORMAL
        )
        
        success = await cross_bus.publish(event)
        
        # 等待异步处理
        await asyncio.sleep(0.3)
        
        # 验证：事件发布成功
        assert success is True
        
        # 验证：警告系统接收到事件
        assert len(received_events) > 0
        warning_event = received_events[0]
        assert warning_event.data['predicted_monthly'] > warning_event.data['budget_monthly']
        
        await base_bus.shutdown()


class TestRiskDetectionEmergencyResponseFlow:
    """测试风险检测 → 应急响应流程
    
    白皮书依据: 第十二章 12.4 风险管理与应急响应集成
    """
    
    @pytest.mark.asyncio
    async def test_high_market_risk_triggers_emergency_response(self):
        """测试高市场风险触发应急响应
        
        白皮书依据: 第十九章 19.1 风险识别, 19.3 应急响应
        """
        # 创建真实的事件总线
        base_bus = EventBus()
        await base_bus.initialize()
        
        cross_bus = CrossChapterEventBus(base_bus)
        await cross_bus.initialize()
        
        # 订阅RISK_LEVEL_CHANGED事件
        received_events = []
        
        async def risk_handler(event):
            received_events.append(event)
        
        await cross_bus.subscribe(
            event_type=CrossChapterEventType.RISK_LEVEL_CHANGED,
            handler_func=risk_handler,
            handler_id="risk_monitor"
        )
        
        # 发布风险等级变化事件
        event = CrossChapterEvent(
            event_type=CrossChapterEventType.RISK_LEVEL_CHANGED,
            source_chapter=19,
            target_chapter=13,
            data={
                'risk_type': 'market_risk',
                'risk_level': 'HIGH',
                'alert_level': 'DANGER',
                'description': '市场波动率过高',
                'metrics': {'volatility': 0.45, 'daily_pnl_ratio': -0.08},
                'timestamp': datetime.now().isoformat()
            },
            priority=EventPriority.HIGH
        )
        
        success = await cross_bus.publish(event)
        
        # 等待异步处理
        await asyncio.sleep(0.3)
        
        # 验证：事件发布成功
        assert success is True
        
        # 验证：监控系统接收到事件
        assert len(received_events) > 0
        risk_event = received_events[0]
        assert risk_event.data['risk_type'] == 'market_risk'
        assert risk_event.data['risk_level'] in ['HIGH', 'CRITICAL']
        
        await base_bus.shutdown()
    
    @pytest.mark.asyncio
    async def test_doomsday_switch_event_flow(self):
        """测试末日开关事件流
        
        白皮书依据: 第十二章 12.3 末日开关, 第十九章 19.3 应急响应
        """
        # 创建真实的事件总线
        base_bus = EventBus()
        await base_bus.initialize()
        
        cross_bus = CrossChapterEventBus(base_bus)
        await cross_bus.initialize()
        
        # 订阅DOOMSDAY_TRIGGERED事件
        received_events = []
        
        async def doomsday_handler(event):
            received_events.append(event)
        
        await cross_bus.subscribe(
            event_type=CrossChapterEventType.DOOMSDAY_TRIGGERED,
            handler_func=doomsday_handler,
            handler_id="doomsday_monitor"
        )
        
        # 发布末日开关触发事件
        event = CrossChapterEvent(
            event_type=CrossChapterEventType.DOOMSDAY_TRIGGERED,
            source_chapter=12,
            target_chapter=13,
            data={
                'reason': '极高风险: 市场崩盘',
                'triggers_fired': ['market_crash', 'high_volatility'],
                'timestamp': datetime.now().isoformat()
            },
            priority=EventPriority.CRITICAL
        )
        
        success = await cross_bus.publish(event)
        
        # 等待异步处理
        await asyncio.sleep(0.3)
        
        # 验证：事件发布成功
        assert success is True
        
        # 验证：监控系统接收到事件
        assert len(received_events) > 0
        doomsday_event = received_events[0]
        assert 'reason' in doomsday_event.data
        assert 'triggers_fired' in doomsday_event.data
        
        await base_bus.shutdown()


class TestPerformanceRegressionAlertFlow:
    """测试性能回归 → 告警流程
    
    白皮书依据: 第十二章 12.1 监控与可靠性集成
    """
    
    @pytest.mark.asyncio
    async def test_performance_regression_triggers_alert(self):
        """测试性能回归触发告警
        
        白皮书依据: 第十六章 16.2 性能监控
        """
        # 创建真实的事件总线
        base_bus = EventBus()
        await base_bus.initialize()
        
        cross_bus = CrossChapterEventBus(base_bus)
        await cross_bus.initialize()
        
        # 订阅PERFORMANCE_REGRESSION_DETECTED事件
        received_events = []
        
        async def regression_handler(event):
            received_events.append(event)
        
        await cross_bus.subscribe(
            event_type=CrossChapterEventType.PERFORMANCE_REGRESSION_DETECTED,
            handler_func=regression_handler,
            handler_id="regression_monitor"
        )
        
        # 模拟性能回归事件
        regression_event = CrossChapterEvent(
            event_type=CrossChapterEventType.PERFORMANCE_REGRESSION_DETECTED,
            source_chapter=16,
            target_chapter=13,
            data={
                'metric_name': 'soldier_latency_p99',
                'baseline_value': 120.0,
                'current_value': 180.0,
                'degradation_percent': 50.0,
                'threshold_percent': 10.0,
                'timestamp': datetime.now().isoformat()
            },
            priority=EventPriority.HIGH
        )
        
        # 发布事件
        success = await cross_bus.publish(regression_event)
        
        # 等待异步处理
        await asyncio.sleep(0.3)
        
        # 验证：事件发布成功
        assert success is True
        
        # 验证：监控系统接收到事件
        assert len(received_events) > 0
        alert_event = received_events[0]
        assert alert_event.data['metric_name'] == 'soldier_latency_p99'
        assert alert_event.data['degradation_percent'] > alert_event.data['threshold_percent']
        
        await base_bus.shutdown()


class TestEndToEndCrossChapterIntegration:
    """端到端跨章节集成测试
    
    白皮书依据: 第十二章 12.1-12.10 跨章节集成
    """
    
    @pytest.mark.asyncio
    async def test_complete_integration_flow(self):
        """测试完整的集成流程
        
        白皮书依据: 第十二章 12.1-12.10
        """
        # 创建真实的事件总线
        base_bus = EventBus()
        await base_bus.initialize()
        
        cross_bus = CrossChapterEventBus(base_bus)
        await cross_bus.initialize()
        
        # 统计接收到的事件
        event_counts = {
            CrossChapterEventType.HEALTH_CHECK_FAILED: 0,
            CrossChapterEventType.COST_LIMIT_EXCEEDED: 0,
            CrossChapterEventType.RISK_LEVEL_CHANGED: 0,
            CrossChapterEventType.PERFORMANCE_REGRESSION_DETECTED: 0
        }
        
        async def event_counter(event):
            event_type = event.event_type
            event_counts[event_type] += 1
        
        # 订阅所有事件类型
        for event_type in event_counts.keys():
            await cross_bus.subscribe(
                event_type=event_type,
                handler_func=event_counter,
                handler_id=f"counter_{event_type.value}"
            )
        
        # 1. 发布健康检查失败事件
        await cross_bus.publish(CrossChapterEvent(
            event_type=CrossChapterEventType.HEALTH_CHECK_FAILED,
            source_chapter=10,
            target_chapter=13,
            data={'component': 'redis', 'status': 'unhealthy'},
            priority=EventPriority.HIGH
        ))
        
        # 2. 发布成本超限事件
        await cross_bus.publish(CrossChapterEvent(
            event_type=CrossChapterEventType.COST_LIMIT_EXCEEDED,
            source_chapter=18,
            target_chapter=13,
            data={'limit_type': 'daily', 'current_cost': 150.0, 'budget': 100.0},
            priority=EventPriority.HIGH
        ))
        
        # 3. 发布风险等级变化事件
        await cross_bus.publish(CrossChapterEvent(
            event_type=CrossChapterEventType.RISK_LEVEL_CHANGED,
            source_chapter=19,
            target_chapter=13,
            data={'risk_type': 'market_risk', 'risk_level': 'HIGH'},
            priority=EventPriority.HIGH
        ))
        
        # 4. 发布性能回归事件
        await cross_bus.publish(CrossChapterEvent(
            event_type=CrossChapterEventType.PERFORMANCE_REGRESSION_DETECTED,
            source_chapter=16,
            target_chapter=13,
            data={'metric_name': 'soldier_latency_p99', 'degradation_percent': 50.0},
            priority=EventPriority.HIGH
        ))
        
        # 等待异步处理
        await asyncio.sleep(0.5)
        
        # 验证：所有事件都被接收
        assert event_counts[CrossChapterEventType.HEALTH_CHECK_FAILED] >= 1
        assert event_counts[CrossChapterEventType.COST_LIMIT_EXCEEDED] >= 1
        assert event_counts[CrossChapterEventType.RISK_LEVEL_CHANGED] >= 1
        assert event_counts[CrossChapterEventType.PERFORMANCE_REGRESSION_DETECTED] >= 1
        
        # 验证：事件总线统计正确
        assert cross_bus.stats['events_published'] >= 4
        
        await base_bus.shutdown()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
