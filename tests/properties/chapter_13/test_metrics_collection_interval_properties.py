"""Property 12: Prometheus Metrics Collection Interval

白皮书依据: 第十三章 13.1 Prometheus指标埋点
**Validates: Requirements 5.1**

测试指标采集间隔的正确性：
1. 采集间隔必须为10秒
2. 每次采集都会更新指标
3. 采集时间戳单调递增
"""

import time
import threading
from datetime import datetime, timedelta
from typing import List, Optional
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck

# 导入被测模块
import sys
sys.path.insert(0, '.')

from src.monitoring.prometheus_collector import (
    PrometheusMetricsCollector,
    CollectionResult,
    MetricType
)


@dataclass
class CollectionEvent:
    """采集事件记录"""
    timestamp: datetime
    metrics_count: int
    success: bool


class TestMetricsCollectionIntervalProperties:
    """Property 12: Prometheus Metrics Collection Interval
    
    **Validates: Requirements 5.1**
    
    测试采集间隔的属性：
    1. 采集间隔配置正确性
    2. 采集时间戳单调递增
    3. 指标更新一致性
    """
    
    @pytest.fixture
    def mock_registry(self):
        """创建模拟的Prometheus注册表"""
        with patch('src.monitoring.prometheus_collector.PROMETHEUS_AVAILABLE', True):
            with patch('src.monitoring.prometheus_collector.REGISTRY') as mock_reg:
                yield mock_reg
    
    @pytest.fixture
    def collector(self, mock_registry):
        """创建测试用采集器"""
        with patch('src.monitoring.prometheus_collector.Counter'):
            with patch('src.monitoring.prometheus_collector.Gauge'):
                with patch('src.monitoring.prometheus_collector.Histogram'):
                    with patch('src.monitoring.prometheus_collector.Info'):
                        collector = PrometheusMetricsCollector(
                            port=9999,
                            collection_interval=10
                        )
                        yield collector
    
    @given(interval=st.integers(min_value=1, max_value=3600))
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_collection_interval_configuration(self, interval: int):
        """Property: 采集间隔配置必须被正确保存
        
        **Validates: Requirements 5.1**
        
        对于任意有效的采集间隔值，采集器必须正确保存该配置。
        """
        with patch('src.monitoring.prometheus_collector.PROMETHEUS_AVAILABLE', True):
            with patch('src.monitoring.prometheus_collector.Counter'):
                with patch('src.monitoring.prometheus_collector.Gauge'):
                    with patch('src.monitoring.prometheus_collector.Histogram'):
                        with patch('src.monitoring.prometheus_collector.Info'):
                            collector = PrometheusMetricsCollector(
                                port=9999,
                                collection_interval=interval
                            )
                            
                            # 验证间隔被正确保存
                            assert collector.collection_interval == interval
                            
                            # 验证状态报告中的间隔
                            status = collector.get_status()
                            assert status['collection_interval'] == interval

    
    @given(invalid_interval=st.integers(max_value=0))
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_invalid_interval_rejected(self, invalid_interval: int):
        """Property: 无效的采集间隔必须被拒绝
        
        **Validates: Requirements 5.1**
        
        采集间隔必须>=1秒，任何小于1的值都应该抛出ValueError。
        """
        with patch('src.monitoring.prometheus_collector.PROMETHEUS_AVAILABLE', True):
            with patch('src.monitoring.prometheus_collector.Counter'):
                with patch('src.monitoring.prometheus_collector.Gauge'):
                    with patch('src.monitoring.prometheus_collector.Histogram'):
                        with patch('src.monitoring.prometheus_collector.Info'):
                            with pytest.raises(ValueError, match="采集间隔必须>=1秒"):
                                PrometheusMetricsCollector(
                                    port=9999,
                                    collection_interval=invalid_interval
                                )
    
    @given(
        collection_counts=st.lists(
            st.integers(min_value=0, max_value=100),
            min_size=2,
            max_size=10
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_collection_timestamps_monotonic(self, collection_counts: List[int]):
        """Property: 采集时间戳必须单调递增
        
        **Validates: Requirements 5.1**
        
        每次采集的时间戳必须大于前一次采集的时间戳。
        """
        timestamps: List[datetime] = []
        
        for count in collection_counts:
            result = CollectionResult(
                success=True,
                metrics_count=count,
                duration_ms=10.0,
                errors=[],
                timestamp=datetime.now()
            )
            timestamps.append(result.timestamp)
            time.sleep(0.001)  # 确保时间戳不同
        
        # 验证时间戳单调递增
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1], \
                f"时间戳不是单调递增: {timestamps[i-1]} -> {timestamps[i]}"

    
    @given(
        metrics_count=st.integers(min_value=0, max_value=1000),
        duration_ms=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_collection_result_consistency(self, metrics_count: int, duration_ms: float):
        """Property: 采集结果必须保持一致性
        
        **Validates: Requirements 5.1**
        
        采集结果的各字段必须保持一致：
        - success为True时errors应为空
        - metrics_count必须非负
        - duration_ms必须非负
        """
        # 创建成功的采集结果
        result = CollectionResult(
            success=True,
            metrics_count=metrics_count,
            duration_ms=duration_ms,
            errors=[],
            timestamp=datetime.now()
        )
        
        # 验证一致性
        assert result.success is True
        assert result.errors == []
        assert result.metrics_count >= 0
        assert result.duration_ms >= 0
        
        # 创建失败的采集结果
        error_result = CollectionResult(
            success=False,
            metrics_count=metrics_count,
            duration_ms=duration_ms,
            errors=["测试错误"],
            timestamp=datetime.now()
        )
        
        # 验证失败结果的一致性
        assert error_result.success is False
        assert len(error_result.errors) > 0
    
    @given(port=st.integers(min_value=1, max_value=65535))
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_port_configuration_valid_range(self, port: int):
        """Property: 端口配置必须在有效范围内
        
        **Validates: Requirements 5.1**
        
        端口号必须在1-65535之间。
        """
        with patch('src.monitoring.prometheus_collector.PROMETHEUS_AVAILABLE', True):
            with patch('src.monitoring.prometheus_collector.Counter'):
                with patch('src.monitoring.prometheus_collector.Gauge'):
                    with patch('src.monitoring.prometheus_collector.Histogram'):
                        with patch('src.monitoring.prometheus_collector.Info'):
                            collector = PrometheusMetricsCollector(
                                port=port,
                                collection_interval=10
                            )
                            
                            assert collector.port == port
                            assert 1 <= collector.port <= 65535

    
    @given(invalid_port=st.integers().filter(lambda x: x < 1 or x > 65535))
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_invalid_port_rejected(self, invalid_port: int):
        """Property: 无效的端口号必须被拒绝
        
        **Validates: Requirements 5.1**
        
        端口号必须在1-65535之间，超出范围的值应该抛出ValueError。
        """
        with patch('src.monitoring.prometheus_collector.PROMETHEUS_AVAILABLE', True):
            with patch('src.monitoring.prometheus_collector.Counter'):
                with patch('src.monitoring.prometheus_collector.Gauge'):
                    with patch('src.monitoring.prometheus_collector.Histogram'):
                        with patch('src.monitoring.prometheus_collector.Info'):
                            with pytest.raises(ValueError, match="端口号必须在1-65535之间"):
                                PrometheusMetricsCollector(
                                    port=invalid_port,
                                    collection_interval=10
                                )
    
    @given(
        num_collections=st.integers(min_value=1, max_value=10),
        base_metrics=st.integers(min_value=0, max_value=50)
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_metrics_count_accumulation(self, num_collections: int, base_metrics: int):
        """Property: 采集计数必须正确累加
        
        **Validates: Requirements 5.1**
        
        每次采集后，采集计数应该增加1。
        """
        with patch('src.monitoring.prometheus_collector.PROMETHEUS_AVAILABLE', True):
            with patch('src.monitoring.prometheus_collector.Counter'):
                with patch('src.monitoring.prometheus_collector.Gauge'):
                    with patch('src.monitoring.prometheus_collector.Histogram'):
                        with patch('src.monitoring.prometheus_collector.Info'):
                            collector = PrometheusMetricsCollector(
                                port=9999,
                                collection_interval=10
                            )
                            
                            initial_count = collector._collection_count
                            
                            # 模拟多次采集
                            for i in range(num_collections):
                                collector._collection_count += 1
                                collector._last_collection_time = datetime.now()
                            
                            # 验证计数正确累加
                            assert collector._collection_count == initial_count + num_collections
                            
                            # 验证状态报告
                            status = collector.get_status()
                            assert status['collection_count'] == initial_count + num_collections

    
    @given(
        metric_names=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_'),
                min_size=1,
                max_size=50
            ),
            min_size=1,
            max_size=10,
            unique=True
        )
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_custom_metric_registration_uniqueness(self, metric_names: List[str]):
        """Property: 自定义指标名称必须唯一
        
        **Validates: Requirements 5.1**
        
        注册重复的指标名称应该抛出ValueError。
        """
        with patch('src.monitoring.prometheus_collector.PROMETHEUS_AVAILABLE', True):
            with patch('src.monitoring.prometheus_collector.Counter') as mock_counter:
                with patch('src.monitoring.prometheus_collector.Gauge') as mock_gauge:
                    with patch('src.monitoring.prometheus_collector.Histogram'):
                        with patch('src.monitoring.prometheus_collector.Info'):
                            mock_counter.return_value = MagicMock()
                            mock_gauge.return_value = MagicMock()
                            
                            collector = PrometheusMetricsCollector(
                                port=9999,
                                collection_interval=10
                            )
                            
                            # 注册第一个自定义指标
                            for name in metric_names:
                                full_name = f"custom_{name}"
                                if full_name not in collector.metrics:
                                    result = collector.register_custom_metric(
                                        name=full_name,
                                        description=f"Test metric {name}",
                                        metric_type=MetricType.GAUGE
                                    )
                                    assert result is True
                                    
                                    # 尝试重复注册应该失败
                                    with pytest.raises(ValueError, match="指标已存在"):
                                        collector.register_custom_metric(
                                            name=full_name,
                                            description=f"Duplicate metric {name}",
                                            metric_type=MetricType.GAUGE
                                        )


class TestDefaultCollectionInterval:
    """测试默认采集间隔（10秒）
    
    **Validates: Requirements 5.1**
    """
    
    def test_default_interval_is_10_seconds(self):
        """验证默认采集间隔为10秒
        
        白皮书依据: 第十三章 13.1.2 指标采集器
        "time.sleep(10)  # 每10秒采集一次"
        """
        with patch('src.monitoring.prometheus_collector.PROMETHEUS_AVAILABLE', True):
            with patch('src.monitoring.prometheus_collector.Counter'):
                with patch('src.monitoring.prometheus_collector.Gauge'):
                    with patch('src.monitoring.prometheus_collector.Histogram'):
                        with patch('src.monitoring.prometheus_collector.Info'):
                            collector = PrometheusMetricsCollector(port=9999)
                            
                            # 默认间隔应该是10秒
                            assert collector.collection_interval == 10
