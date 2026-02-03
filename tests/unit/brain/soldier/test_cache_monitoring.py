"""
缓存监控和告警测试 - Task 20.6

白皮书依据: 第十六章 监控系统

测试目标:
- 测试统计数据准确性
- 测试告警触发
- 测试清理策略
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from src.brain.soldier_engine_v2 import SoldierEngineV2, SoldierConfig
from src.infra.event_bus import Event, EventType, EventPriority


class TestCacheStatistics:
    """测试缓存统计数据准确性"""
    
    @pytest.mark.asyncio
    async def test_cache_stats_accuracy(self):
        """测试缓存统计数据的准确性"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 模拟一些缓存操作
        context = {
            'symbol': '000001',
            'market_data': {'price': 100.0, 'volume': 1000000}
        }
        
        # 10次miss
        for _ in range(10):
            await soldier._get_cached_decision(context)
        
        # 5次hit
        mock_redis.get = AsyncMock(return_value='{"decision": "test"}')
        for _ in range(5):
            await soldier._get_cached_decision(context)
        
        # 获取统计
        stats = await soldier.get_cache_stats()
        
        # 验证统计准确性
        assert stats['cache_hits'] == 5
        assert stats['cache_misses'] == 10
        assert stats['total_requests'] == 15
        assert stats['hit_rate'] == pytest.approx(5/15, 0.01)
    
    @pytest.mark.asyncio
    async def test_cache_stats_with_errors(self):
        """测试包含错误的缓存统计"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # Mock Redis with errors
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        context = {
            'symbol': '000001',
            'market_data': {'price': 100.0, 'volume': 1000000}
        }
        
        # 触发5次错误
        for _ in range(5):
            await soldier._get_cached_decision(context)
        
        # 验证错误计数
        assert soldier.stats['cache_errors'] == 5
    
    @pytest.mark.asyncio
    async def test_cache_stats_reset(self):
        """测试统计数据重置"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # 设置一些统计数据
        soldier.stats['cache_hits'] = 100
        soldier.stats['cache_misses'] = 50
        soldier.stats['cache_errors'] = 10
        
        # 重置统计
        soldier.stats['cache_hits'] = 0
        soldier.stats['cache_misses'] = 0
        soldier.stats['cache_errors'] = 0
        
        # 验证重置
        assert soldier.stats['cache_hits'] == 0
        assert soldier.stats['cache_misses'] == 0
        assert soldier.stats['cache_errors'] == 0


class TestCacheAlerts:
    """测试缓存告警触发"""
    
    @pytest.mark.asyncio
    async def test_low_hit_rate_alert(self):
        """测试低命中率告警"""
        config = SoldierConfig(
            cache_alert_enabled=True,
            cache_alert_hit_rate_threshold=0.5
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, []))
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # Mock event bus
        mock_event_bus = AsyncMock()
        soldier.event_bus = mock_event_bus
        
        # 设置低命中率 (30%)
        soldier.stats['cache_hits'] = 30
        soldier.stats['cache_misses'] = 70
        
        # 检查告警
        alert_result = await soldier.check_cache_alerts()
        
        # 验证告警触发
        assert alert_result['alert_enabled'] is True
        assert alert_result['alert_level'] == 'warning'
        assert len(alert_result['alerts']) > 0
        assert any(a['type'] == 'low_hit_rate' for a in alert_result['alerts'])
        
        # 验证事件发送
        assert mock_event_bus.publish.called
    
    @pytest.mark.asyncio
    async def test_high_error_rate_alert(self):
        """测试高错误率告警"""
        config = SoldierConfig(
            cache_alert_enabled=True,
            cache_alert_error_rate_threshold=0.1
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, []))
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # Mock event bus
        mock_event_bus = AsyncMock()
        soldier.event_bus = mock_event_bus
        
        # 设置高错误率 (20%)
        soldier.stats['cache_hits'] = 40
        soldier.stats['cache_misses'] = 40
        soldier.stats['cache_errors'] = 20
        
        # 检查告警
        alert_result = await soldier.check_cache_alerts()
        
        # 验证告警触发
        assert alert_result['alert_enabled'] is True
        assert alert_result['alert_level'] == 'critical'
        assert len(alert_result['alerts']) > 0
        assert any(a['type'] == 'high_error_rate' for a in alert_result['alerts'])
    
    @pytest.mark.asyncio
    async def test_unhealthy_cache_alert(self):
        """测试缓存不健康告警"""
        config = SoldierConfig(
            cache_alert_enabled=True,
            cache_hit_rate_target=0.8
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, []))
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # Mock event bus
        mock_event_bus = AsyncMock()
        soldier.event_bus = mock_event_bus
        
        # 设置低命中率导致不健康
        soldier.stats['cache_hits'] = 30
        soldier.stats['cache_misses'] = 70
        
        # 检查告警
        alert_result = await soldier.check_cache_alerts()
        
        # 验证告警包含健康检查失败
        assert alert_result['alert_enabled'] is True
        assert len(alert_result['alerts']) >= 2  # low_hit_rate + unhealthy
        assert any(a['type'] == 'unhealthy' for a in alert_result['alerts'])
    
    @pytest.mark.asyncio
    async def test_alert_disabled(self):
        """测试禁用告警"""
        config = SoldierConfig(cache_alert_enabled=False)
        soldier = SoldierEngineV2(config)
        
        # 设置低命中率
        soldier.stats['cache_hits'] = 10
        soldier.stats['cache_misses'] = 90
        
        # 检查告警
        alert_result = await soldier.check_cache_alerts()
        
        # 验证告警未启用
        assert alert_result['alert_enabled'] is False
    
    @pytest.mark.asyncio
    async def test_alert_interval(self):
        """测试告警间隔控制"""
        config = SoldierConfig(
            cache_alert_enabled=True,
            cache_alert_hit_rate_threshold=0.5,
            cache_alert_check_interval=60.0  # 60秒间隔
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, []))
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # Mock event bus
        mock_event_bus = AsyncMock()
        soldier.event_bus = mock_event_bus
        
        # 设置低命中率
        soldier.stats['cache_hits'] = 30
        soldier.stats['cache_misses'] = 70
        
        # 第一次检查 - 应该发送告警
        alert_result1 = await soldier.check_cache_alerts()
        assert alert_result1['alert_count'] == 1
        assert mock_event_bus.publish.call_count == 1
        
        # 立即第二次检查 - 不应该发送告警(间隔未到)
        alert_result2 = await soldier.check_cache_alerts()
        assert alert_result2['alert_count'] == 1  # 计数不变
        assert mock_event_bus.publish.call_count == 1  # 未再次调用
        
        # 模拟时间过去
        soldier.last_alert_time = datetime.now() - timedelta(seconds=61)
        
        # 第三次检查 - 应该发送告警(间隔已到)
        alert_result3 = await soldier.check_cache_alerts()
        assert alert_result3['alert_count'] == 2
        assert mock_event_bus.publish.call_count == 2
    
    @pytest.mark.asyncio
    async def test_alert_event_format(self):
        """测试告警事件格式"""
        config = SoldierConfig(
            cache_alert_enabled=True,
            cache_alert_hit_rate_threshold=0.5
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, []))
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # Mock event bus
        mock_event_bus = AsyncMock()
        soldier.event_bus = mock_event_bus
        
        # 设置低命中率
        soldier.stats['cache_hits'] = 30
        soldier.stats['cache_misses'] = 70
        
        # 检查告警
        await soldier.check_cache_alerts()
        
        # 验证事件格式
        assert mock_event_bus.publish.called
        event = mock_event_bus.publish.call_args[0][0]
        
        assert event.event_type == EventType.SYSTEM_ALERT
        assert 'source' in event.data
        assert event.data['source'] == 'soldier_v2'
        assert 'component' in event.data
        assert event.data['component'] == 'cache'
        assert 'level' in event.data
        assert 'alerts' in event.data
        assert 'stats' in event.data


class TestCacheCleanup:
    """测试缓存清理策略"""
    
    @pytest.mark.asyncio
    async def test_clear_cache_basic(self):
        """测试基本缓存清理"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        
        # Mock scan返回一些键
        mock_redis.scan = AsyncMock(side_effect=[
            (100, ['key1', 'key2', 'key3']),
            (0, ['key4', 'key5'])
        ])
        mock_redis.delete = AsyncMock(return_value=5)
        
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 清理缓存
        result = await soldier.clear_cache()
        
        # 验证清理成功
        assert result is True
        assert mock_redis.delete.called
    
    @pytest.mark.asyncio
    async def test_clear_cache_disabled(self):
        """测试缓存禁用时的清理"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        soldier.cache_enabled = False
        
        # 清理缓存
        result = await soldier.clear_cache()
        
        # 验证返回False
        assert result is False
    
    @pytest.mark.asyncio
    async def test_clear_cache_error_handling(self):
        """测试清理缓存时的错误处理"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # Mock Redis with error
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(side_effect=Exception("Redis error"))
        
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 清理缓存
        result = await soldier.clear_cache()
        
        # 验证错误处理
        assert result is False


class TestCacheMonitoringIntegration:
    """测试缓存监控集成"""
    
    @pytest.mark.asyncio
    async def test_full_monitoring_workflow(self):
        """测试完整的监控工作流程"""
        config = SoldierConfig(
            cache_alert_enabled=True,
            cache_alert_hit_rate_threshold=0.5
        )
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, ['key1', 'key2']))
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # Mock event bus
        mock_event_bus = AsyncMock()
        soldier.event_bus = mock_event_bus
        
        # 1. 设置统计数据
        soldier.stats['cache_hits'] = 30
        soldier.stats['cache_misses'] = 70
        
        # 2. 获取统计
        stats = await soldier.get_cache_stats()
        assert stats['hit_rate'] == 0.3
        
        # 3. 获取健康状态
        health = await soldier.get_cache_health()
        assert health['is_healthy'] is False
        
        # 4. 检查告警
        alerts = await soldier.check_cache_alerts()
        assert alerts['alert_level'] == 'warning'
        
        # 5. 清理缓存
        result = await soldier.clear_cache()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_monitoring_performance(self):
        """测试监控性能"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.scan = AsyncMock(return_value=(0, []))
        soldier.redis_client = mock_redis
        soldier.cache_enabled = True
        
        # 设置统计数据
        soldier.stats['cache_hits'] = 80
        soldier.stats['cache_misses'] = 20
        
        # 测试监控调用性能
        import time
        
        start = time.perf_counter()
        stats = await soldier.get_cache_stats()
        stats_time = time.perf_counter() - start
        
        start = time.perf_counter()
        health = await soldier.get_cache_health()
        health_time = time.perf_counter() - start
        
        start = time.perf_counter()
        alerts = await soldier.check_cache_alerts()
        alerts_time = time.perf_counter() - start
        
        # 验证性能 - 监控调用应该很快
        assert stats_time < 0.01  # < 10ms
        assert health_time < 0.05  # < 50ms
        assert alerts_time < 0.1  # < 100ms
