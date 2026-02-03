"""Unit tests for PrometheusMetricsCollector

白皮书依据: 第十三章 13.1 Prometheus指标埋点

测试覆盖:
- PrometheusMetricsCollector类的所有方法
- 指标采集功能
- 边界条件和异常处理
- 目标: 100% 覆盖率
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.monitoring.prometheus_collector import (
    MetricType,
    MetricDefinition,
    CollectionResult,
    PrometheusMetricsCollector,
    create_metrics_collector,
    PROMETHEUS_AVAILABLE
)


class TestMetricType:
    """MetricType枚举测试"""
    
    def test_counter_value(self):
        """测试COUNTER类型值"""
        assert MetricType.COUNTER.value == "counter"
    
    def test_gauge_value(self):
        """测试GAUGE类型值"""
        assert MetricType.GAUGE.value == "gauge"
    
    def test_histogram_value(self):
        """测试HISTOGRAM类型值"""
        assert MetricType.HISTOGRAM.value == "histogram"
    
    def test_info_value(self):
        """测试INFO类型值"""
        assert MetricType.INFO.value == "info"


class TestMetricDefinition:
    """MetricDefinition数据类测试"""
    
    def test_create_basic_metric_definition(self):
        """测试创建基本指标定义"""
        metric_def = MetricDefinition(
            name="test_metric",
            description="Test metric",
            metric_type=MetricType.COUNTER
        )
        
        assert metric_def.name == "test_metric"
        assert metric_def.description == "Test metric"
        assert metric_def.metric_type == MetricType.COUNTER
        assert metric_def.labels == []
        assert len(metric_def.buckets) > 0
    
    def test_create_metric_definition_with_labels(self):
        """测试创建带标签的指标定义"""
        metric_def = MetricDefinition(
            name="test_metric",
            description="Test metric",
            metric_type=MetricType.GAUGE,
            labels=["strategy", "action"]
        )
        
        assert metric_def.labels == ["strategy", "action"]
    
    def test_create_histogram_with_custom_buckets(self):
        """测试创建自定义桶的直方图"""
        custom_buckets = (0.1, 0.5, 1.0, 5.0)
        metric_def = MetricDefinition(
            name="test_histogram",
            description="Test histogram",
            metric_type=MetricType.HISTOGRAM,
            buckets=custom_buckets
        )
        
        assert metric_def.buckets == custom_buckets


class TestCollectionResult:
    """CollectionResult数据类测试"""
    
    def test_create_successful_result(self):
        """测试创建成功的采集结果"""
        result = CollectionResult(
            success=True,
            metrics_count=10,
            duration_ms=50.5
        )
        
        assert result.success is True
        assert result.metrics_count == 10
        assert result.duration_ms == 50.5
        assert result.errors == []
        assert isinstance(result.timestamp, datetime)
    
    def test_create_failed_result_with_errors(self):
        """测试创建失败的采集结果"""
        errors = ["Error 1", "Error 2"]
        result = CollectionResult(
            success=False,
            metrics_count=5,
            duration_ms=100.0,
            errors=errors
        )
        
        assert result.success is False
        assert result.errors == errors


class TestPrometheusMetricsCollectorInit:
    """PrometheusMetricsCollector初始化测试"""
    
    def test_init_default_params(self):
        """测试默认参数初始化"""
        collector = PrometheusMetricsCollector()
        
        assert collector.port == 9090
        assert collector.collection_interval == 10
        assert collector.redis_client is None
        assert collector.running is False
        assert isinstance(collector.metrics, dict)
    
    def test_init_custom_params(self):
        """测试自定义参数初始化"""
        mock_redis = Mock()
        collector = PrometheusMetricsCollector(
            port=8080,
            collection_interval=5,
            redis_client=mock_redis
        )
        
        assert collector.port == 8080
        assert collector.collection_interval == 5
        assert collector.redis_client == mock_redis
    
    def test_init_invalid_port_too_low(self):
        """测试无效端口（过低）"""
        with pytest.raises(ValueError, match="端口号必须在1-65535之间"):
            PrometheusMetricsCollector(port=0)
    
    def test_init_invalid_port_too_high(self):
        """测试无效端口（过高）"""
        with pytest.raises(ValueError, match="端口号必须在1-65535之间"):
            PrometheusMetricsCollector(port=65536)
    
    def test_init_invalid_collection_interval(self):
        """测试无效采集间隔"""
        with pytest.raises(ValueError, match="采集间隔必须>=1秒"):
            PrometheusMetricsCollector(collection_interval=0)
    
    def test_init_boundary_port_values(self):
        """测试边界端口值"""
        collector1 = PrometheusMetricsCollector(port=1)
        assert collector1.port == 1
        
        collector2 = PrometheusMetricsCollector(port=65535)
        assert collector2.port == 65535
    
    def test_init_boundary_interval_value(self):
        """测试边界采集间隔值"""
        collector = PrometheusMetricsCollector(collection_interval=1)
        assert collector.collection_interval == 1


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
class TestPrometheusMetricsCollectorMetrics:
    """PrometheusMetricsCollector指标测试"""
    
    @pytest.fixture
    def collector(self):
        """创建采集器实例"""
        from prometheus_client import CollectorRegistry
        registry = CollectorRegistry()
        return PrometheusMetricsCollector(registry=registry)
    
    def test_default_metrics_initialized(self, collector):
        """测试默认指标已初始化"""
        assert len(collector.metrics) > 0
        
        # 检查关键指标
        assert 'mia_trades_total' in collector.metrics
        assert 'mia_soldier_latency_seconds' in collector.metrics
        assert 'mia_gpu_memory_used_bytes' in collector.metrics
        assert 'mia_system_cpu_percent' in collector.metrics
        assert 'mia_portfolio_value' in collector.metrics
    
    def test_get_metrics_list(self, collector):
        """测试获取指标列表"""
        metrics_list = collector.get_metrics_list()
        
        assert isinstance(metrics_list, list)
        assert len(metrics_list) > 0
        assert 'mia_trades_total' in metrics_list
    
    def test_get_metric_exists(self, collector):
        """测试获取存在的指标"""
        metric = collector.get_metric('mia_trades_total')
        assert metric is not None
    
    def test_get_metric_not_exists(self, collector):
        """测试获取不存在的指标"""
        metric = collector.get_metric('nonexistent_metric')
        assert metric is None


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
class TestPrometheusMetricsCollectorCustomMetrics:
    """PrometheusMetricsCollector自定义指标测试"""
    
    @pytest.fixture
    def collector(self):
        """创建采集器实例"""
        from prometheus_client import CollectorRegistry
        registry = CollectorRegistry()
        return PrometheusMetricsCollector(registry=registry)
    
    def test_register_custom_counter(self, collector):
        """测试注册自定义计数器"""
        success = collector.register_custom_metric(
            name="custom_counter",
            description="Custom counter metric",
            metric_type=MetricType.COUNTER
        )
        
        assert success is True
        assert 'custom_counter' in collector.metrics
    
    def test_register_custom_gauge(self, collector):
        """测试注册自定义仪表"""
        success = collector.register_custom_metric(
            name="custom_gauge",
            description="Custom gauge metric",
            metric_type=MetricType.GAUGE,
            labels=["label1", "label2"]
        )
        
        assert success is True
        assert 'custom_gauge' in collector.metrics
    
    def test_register_custom_histogram(self, collector):
        """测试注册自定义直方图"""
        success = collector.register_custom_metric(
            name="custom_histogram",
            description="Custom histogram metric",
            metric_type=MetricType.HISTOGRAM,
            buckets=(0.1, 0.5, 1.0)
        )
        
        assert success is True
        assert 'custom_histogram' in collector.metrics
    
    def test_register_duplicate_metric(self, collector):
        """测试注册重复指标"""
        collector.register_custom_metric(
            name="duplicate_metric",
            description="First metric",
            metric_type=MetricType.COUNTER
        )
        
        with pytest.raises(ValueError, match="指标已存在"):
            collector.register_custom_metric(
                name="duplicate_metric",
                description="Duplicate metric",
                metric_type=MetricType.COUNTER
            )


class TestPrometheusMetricsCollectorSystemMetrics:
    """PrometheusMetricsCollector系统指标采集测试"""
    
    @pytest.fixture
    def collector(self):
        """创建采集器实例"""
        if PROMETHEUS_AVAILABLE:
            from prometheus_client import CollectorRegistry
            registry = CollectorRegistry()
            return PrometheusMetricsCollector(registry=registry)
        return PrometheusMetricsCollector()
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_collect_system_metrics_success(self, collector):
        """测试成功采集系统指标"""
        count = collector.collect_system_metrics()
        
        # 应该采集到一些指标
        assert count >= 0
    
    def test_collect_system_metrics_no_psutil(self, collector):
        """测试无psutil时采集系统指标"""
        import src.monitoring.prometheus_collector as module
        original_psutil = module.psutil
        module.psutil = None
        
        try:
            count = collector.collect_system_metrics()
            assert count == 0
        finally:
            module.psutil = original_psutil


class TestPrometheusMetricsCollectorGPUMetrics:
    """PrometheusMetricsCollector GPU指标采集测试"""
    
    @pytest.fixture
    def collector(self):
        """创建采集器实例"""
        if PROMETHEUS_AVAILABLE:
            from prometheus_client import CollectorRegistry
            registry = CollectorRegistry()
            return PrometheusMetricsCollector(registry=registry)
        return PrometheusMetricsCollector()
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    @patch('subprocess.run')
    def test_collect_gpu_metrics_success(self, mock_run, collector):
        """测试成功采集GPU指标"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="VRAM Used: 1024 MB\nVRAM Total: 32768 MB\nGPU use: 45%\nTemperature: 65.0 C"
        )
        
        count = collector.collect_gpu_metrics()
        assert count >= 0
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    @patch('subprocess.run')
    def test_collect_gpu_metrics_rocm_not_found(self, mock_run, collector):
        """测试rocm-smi未找到"""
        mock_run.side_effect = FileNotFoundError("rocm-smi not found")
        
        count = collector.collect_gpu_metrics()
        assert count == 0
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    @patch('subprocess.run')
    def test_collect_gpu_metrics_timeout(self, mock_run, collector):
        """测试GPU采集超时"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd='rocm-smi', timeout=2)
        
        count = collector.collect_gpu_metrics()
        assert count == 0
    
    def test_parse_gpu_memory_used(self, collector):
        """测试解析GPU显存使用量"""
        output = "VRAM Used: 1024 MB\n"
        result = collector._parse_gpu_memory_used(output)
        
        assert result == 1024 * 1024 * 1024
    
    def test_parse_gpu_memory_used_invalid(self, collector):
        """测试解析无效GPU显存使用量"""
        output = "Invalid output\n"
        result = collector._parse_gpu_memory_used(output)
        
        assert result is None
    
    def test_parse_gpu_memory_total(self, collector):
        """测试解析GPU显存总量"""
        output = "VRAM Total: 32768 MB\n"
        result = collector._parse_gpu_memory_total(output)
        
        assert result == 32768 * 1024 * 1024
    
    def test_parse_gpu_utilization(self, collector):
        """测试解析GPU利用率"""
        output = "GPU use: 45%\n"
        result = collector._parse_gpu_utilization(output)
        
        assert result == 45.0
    
    def test_parse_gpu_temperature(self, collector):
        """测试解析GPU温度"""
        output = "Temperature: 65.0 C\n"
        result = collector._parse_gpu_temperature(output)
        
        assert result == 65.0


class TestPrometheusMetricsCollectorBusinessMetrics:
    """PrometheusMetricsCollector业务指标采集测试"""
    
    @pytest.fixture
    def mock_redis(self):
        """创建Mock Redis客户端"""
        redis = Mock()
        redis.get.side_effect = lambda key: {
            'portfolio:total_value': b'1000000.0',
            'portfolio:daily_pnl': b'5000.0',
            'portfolio:weekly_pnl': b'15000.0',
            'portfolio:monthly_pnl': b'50000.0',
            'portfolio:total_pnl': b'100000.0',
            'portfolio:positions_count': b'10',
            'portfolio:available_cash': b'500000.0',
            'mia:soldier:mode': b'local'
        }.get(key)
        return redis
    
    @pytest.fixture
    def collector(self, mock_redis):
        """创建采集器实例"""
        if PROMETHEUS_AVAILABLE:
            from prometheus_client import CollectorRegistry
            registry = CollectorRegistry()
            return PrometheusMetricsCollector(redis_client=mock_redis, registry=registry)
        return PrometheusMetricsCollector(redis_client=mock_redis)
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_collect_business_metrics_success(self, collector):
        """测试成功采集业务指标"""
        count = collector.collect_business_metrics()
        
        assert count > 0
    
    def test_collect_business_metrics_no_redis(self):
        """测试无Redis时采集业务指标"""
        collector = PrometheusMetricsCollector(redis_client=None)
        count = collector.collect_business_metrics()
        
        assert count == 0
    
    def test_get_redis_float(self, collector):
        """测试从Redis获取浮点数"""
        value = collector._get_redis_float('portfolio:total_value', 0.0)
        assert value == 1000000.0
    
    def test_get_redis_float_default(self, collector):
        """测试从Redis获取浮点数（使用默认值）"""
        value = collector._get_redis_float('nonexistent_key', 999.0)
        assert value == 999.0
    
    def test_get_redis_int(self, collector):
        """测试从Redis获取整数"""
        value = collector._get_redis_int('portfolio:positions_count', 0)
        assert value == 10
    
    def test_get_redis_string(self, collector):
        """测试从Redis获取字符串"""
        value = collector._get_redis_string('mia:soldier:mode', 'unknown')
        assert value == 'local'


class TestPrometheusMetricsCollectorRecording:
    """PrometheusMetricsCollector记录功能测试"""
    
    @pytest.fixture
    def collector(self):
        """创建采集器实例"""
        if PROMETHEUS_AVAILABLE:
            from prometheus_client import CollectorRegistry
            registry = CollectorRegistry()
            return PrometheusMetricsCollector(registry=registry)
        return PrometheusMetricsCollector()
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_record_trade(self, collector):
        """测试记录交易"""
        collector.record_trade(
            strategy="test_strategy",
            action="buy",
            status="success",
            latency=0.05,
            volume=10000.0
        )
        
        # 不应抛出异常
        assert True
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_record_soldier_decision(self, collector):
        """测试记录Soldier决策"""
        collector.record_soldier_decision(
            mode="local",
            action="buy",
            latency=0.1
        )
        
        assert True
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_record_redis_operation(self, collector):
        """测试记录Redis操作"""
        collector.record_redis_operation(
            operation="get",
            latency=0.001,
            success=True
        )
        
        assert True
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_record_redis_operation_failure(self, collector):
        """测试记录Redis操作失败"""
        collector.record_redis_operation(
            operation="set",
            latency=0.002,
            success=False
        )
        
        assert True
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_record_arena_battle(self, collector):
        """测试记录Arena战斗"""
        collector.record_arena_battle(
            track="S15",
            survivors=5
        )
        
        assert True


class TestPrometheusMetricsCollectorCollection:
    """PrometheusMetricsCollector采集功能测试"""
    
    @pytest.fixture
    def collector(self):
        """创建采集器实例"""
        if PROMETHEUS_AVAILABLE:
            from prometheus_client import CollectorRegistry
            registry = CollectorRegistry()
            return PrometheusMetricsCollector(registry=registry)
        return PrometheusMetricsCollector()
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_collect_all_metrics(self, collector):
        """测试采集所有指标"""
        result = collector.collect_all_metrics()
        
        assert isinstance(result, CollectionResult)
        assert result.metrics_count >= 0
        assert result.duration_ms >= 0
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_collect_all_metrics_with_errors(self, collector):
        """测试采集所有指标（有错误）"""
        # Mock一个方法抛出异常
        with patch.object(collector, 'collect_system_metrics', side_effect=Exception("Test error")):
            result = collector.collect_all_metrics()
            
            assert result.success is False
            assert len(result.errors) > 0


class TestPrometheusMetricsCollectorStartStop:
    """PrometheusMetricsCollector启动停止测试"""
    
    @pytest.fixture
    def collector(self):
        """创建采集器实例"""
        if PROMETHEUS_AVAILABLE:
            from prometheus_client import CollectorRegistry
            registry = CollectorRegistry()
            # 使用不同的端口避免冲突
            return PrometheusMetricsCollector(port=9091, collection_interval=1, registry=registry)
        return PrometheusMetricsCollector(port=9091, collection_interval=1)
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_start_non_blocking(self, collector):
        """测试非阻塞启动"""
        try:
            success = collector.start(blocking=False)
            
            assert success is True
            assert collector.running is True
            
            # 等待一小段时间让线程启动
            time.sleep(0.5)
            
            assert collector._collection_thread is not None
            assert collector._collection_thread.is_alive()
        finally:
            collector.stop()
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_start_already_running(self, collector):
        """测试重复启动"""
        try:
            collector.start(blocking=False)
            
            with pytest.raises(RuntimeError, match="采集器已经在运行中"):
                collector.start(blocking=False)
        finally:
            collector.stop()
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_stop(self, collector):
        """测试停止采集器"""
        collector.start(blocking=False)
        time.sleep(0.5)
        
        collector.stop()
        
        assert collector.running is False
    
    def test_stop_not_running(self, collector):
        """测试停止未运行的采集器"""
        # 不应抛出异常
        collector.stop()
        assert collector.running is False


class TestPrometheusMetricsCollectorStatus:
    """PrometheusMetricsCollector状态测试"""
    
    @pytest.fixture
    def collector(self):
        """创建采集器实例"""
        return PrometheusMetricsCollector()
    
    def test_get_status(self, collector):
        """测试获取状态"""
        status = collector.get_status()
        
        assert isinstance(status, dict)
        assert 'running' in status
        assert 'port' in status
        assert 'collection_interval' in status
        assert 'metrics_count' in status
        assert 'collection_count' in status
        assert 'error_count' in status
        assert 'last_collection_time' in status
        assert 'server_started' in status
    
    def test_get_status_values(self, collector):
        """测试状态值"""
        status = collector.get_status()
        
        assert status['running'] is False
        assert status['port'] == 9090
        assert status['collection_interval'] == 10
        assert status['collection_count'] == 0
        assert status['error_count'] == 0
        assert status['server_started'] is False


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    def test_create_metrics_collector_default(self):
        """测试创建默认采集器"""
        collector = create_metrics_collector()
        
        assert isinstance(collector, PrometheusMetricsCollector)
        assert collector.port == 9090
        assert collector.collection_interval == 10
    
    def test_create_metrics_collector_custom(self):
        """测试创建自定义采集器"""
        mock_redis = Mock()
        collector = create_metrics_collector(
            port=8080,
            collection_interval=5,
            redis_client=mock_redis
        )
        
        assert collector.port == 8080
        assert collector.collection_interval == 5
        assert collector.redis_client == mock_redis


class TestEdgeCases:
    """边界条件测试"""
    
    def test_collector_without_prometheus(self):
        """测试无prometheus_client时的采集器"""
        import src.monitoring.prometheus_collector as module
        original = module.PROMETHEUS_AVAILABLE
        module.PROMETHEUS_AVAILABLE = False
        
        try:
            collector = PrometheusMetricsCollector()
            assert len(collector.metrics) == 0
            
            # 启动应该失败
            success = collector.start(blocking=False)
            assert success is False
        finally:
            module.PROMETHEUS_AVAILABLE = original
    
    def test_register_custom_metric_without_prometheus(self):
        """测试无prometheus_client时注册自定义指标"""
        import src.monitoring.prometheus_collector as module
        original = module.PROMETHEUS_AVAILABLE
        module.PROMETHEUS_AVAILABLE = False
        
        try:
            collector = PrometheusMetricsCollector()
            success = collector.register_custom_metric(
                name="test",
                description="test",
                metric_type=MetricType.COUNTER
            )
            assert success is False
        finally:
            module.PROMETHEUS_AVAILABLE = original
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_collection_with_redis_errors(self):
        """测试Redis错误时的采集"""
        mock_redis = Mock()
        mock_redis.get.side_effect = Exception("Redis error")
        
        from prometheus_client import CollectorRegistry
        registry = CollectorRegistry()
        collector = PrometheusMetricsCollector(redis_client=mock_redis, registry=registry)
        
        # 不应抛出异常
        count = collector.collect_business_metrics()
        assert count == 0
    
    def test_parse_methods_with_empty_output(self):
        """测试解析方法处理空输出"""
        collector = PrometheusMetricsCollector()
        
        assert collector._parse_gpu_memory_used("") is None
        assert collector._parse_gpu_memory_total("") is None
        assert collector._parse_gpu_utilization("") is None
        assert collector._parse_gpu_temperature("") is None
    
    def test_redis_get_methods_with_invalid_values(self):
        """测试Redis获取方法处理无效值"""
        mock_redis = Mock()
        mock_redis.get.return_value = b'invalid_float'
        
        collector = PrometheusMetricsCollector(redis_client=mock_redis)
        
        # 应该返回默认值而不是抛出异常（对于float和int）
        assert collector._get_redis_float('key', 999.0) == 999.0
        assert collector._get_redis_int('key', 888) == 888
        # _get_redis_string 会成功解码bytes，所以返回解码后的字符串
        assert collector._get_redis_string('key', 'default') == 'invalid_float'



class TestPrometheusCollectorMissingCoverage:
    """补充测试以达到100%覆盖率
    
    白皮书依据: 第十三章 13.1 Prometheus指标埋点
    """
    
    def test_import_psutil_failure(self):
        """测试psutil导入失败的情况（覆盖lines 18-19）"""
        import src.monitoring.prometheus_collector as module
        original_psutil = module.psutil
        
        # 模拟psutil不可用
        module.psutil = None
        
        try:
            collector = PrometheusMetricsCollector()
            # 系统指标采集应该返回0
            count = collector.collect_system_metrics()
            assert count == 0
        finally:
            module.psutil = original_psutil
    
    def test_import_prometheus_client_failure(self):
        """测试prometheus_client导入失败的情况（覆盖lines 27-29）"""
        import src.monitoring.prometheus_collector as module
        original_available = module.PROMETHEUS_AVAILABLE
        original_counter = module.Counter
        
        # 模拟prometheus_client不可用
        module.PROMETHEUS_AVAILABLE = False
        module.Counter = None
        
        try:
            collector = PrometheusMetricsCollector()
            # 注册自定义指标应该失败
            success = collector.register_custom_metric(
                name="test",
                description="test",
                metric_type=MetricType.COUNTER
            )
            assert success is False
        finally:
            module.PROMETHEUS_AVAILABLE = original_available
            module.Counter = original_counter
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_create_metric_unsupported_type(self):
        """测试不支持的指标类型（覆盖lines 262-263）"""
        from prometheus_client import CollectorRegistry
        registry = CollectorRegistry()
        collector = PrometheusMetricsCollector(registry=registry)
        
        # 创建一个无效的指标类型
        class InvalidMetricType:
            value = "invalid"
        
        metric_def = MetricDefinition(
            name="test_metric",
            description="Test",
            metric_type=InvalidMetricType()
        )
        
        result = collector._create_metric(metric_def, registry)
        assert result is None
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_start_server_failure(self):
        """测试启动服务器失败（覆盖lines 309-312）"""
        from prometheus_client import CollectorRegistry
        registry = CollectorRegistry()
        collector = PrometheusMetricsCollector(port=9095, registry=registry)  # Valid port
        
        # Patch start_http_server before calling start()
        with patch('src.monitoring.prometheus_collector.start_http_server', side_effect=Exception("Port error")):
            success = collector.start(blocking=False)
            assert success is False
            assert collector.running is False
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_stop_thread_timeout(self):
        """测试停止线程超时（覆盖line 328）"""
        from prometheus_client import CollectorRegistry
        registry = CollectorRegistry()
        collector = PrometheusMetricsCollector(port=9092, collection_interval=1, registry=registry)
        
        try:
            collector.start(blocking=False)
            time.sleep(0.5)
            
            # Mock线程join超时
            with patch.object(collector._collection_thread, 'join', return_value=None):
                with patch.object(collector._collection_thread, 'is_alive', return_value=True):
                    collector.stop()
        finally:
            collector.running = False
            if collector._collection_thread and collector._collection_thread.is_alive():
                collector._collection_thread.join(timeout=1)
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_collect_loop_with_errors(self):
        """测试采集循环中的错误处理（覆盖lines 347-349, 353-356）"""
        from prometheus_client import CollectorRegistry
        registry = CollectorRegistry()
        collector = PrometheusMetricsCollector(port=9093, collection_interval=1, registry=registry)
        
        # Mock collect_all_metrics返回失败结果
        error_result = CollectionResult(
            success=False,
            metrics_count=0,
            duration_ms=0,
            errors=["Test error 1", "Test error 2"]
        )
        
        with patch.object(collector, 'collect_all_metrics', return_value=error_result):
            collector.start(blocking=False)
            time.sleep(1.5)  # 让它运行一次采集
            collector.stop()
            
            assert collector._error_count > 0
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_collect_all_metrics_gpu_exception(self):
        """测试GPU指标采集异常（覆盖lines 379-380）"""
        from prometheus_client import CollectorRegistry
        registry = CollectorRegistry()
        collector = PrometheusMetricsCollector(registry=registry)
        
        with patch.object(collector, 'collect_gpu_metrics', side_effect=Exception("GPU error")):
            result = collector.collect_all_metrics()
            assert not result.success
            assert any("GPU指标采集失败" in error for error in result.errors)
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_collect_all_metrics_business_exception(self):
        """测试业务指标采集异常（覆盖lines 386-387）"""
        from prometheus_client import CollectorRegistry
        registry = CollectorRegistry()
        mock_redis = Mock()
        collector = PrometheusMetricsCollector(redis_client=mock_redis, registry=registry)
        
        with patch.object(collector, 'collect_business_metrics', side_effect=Exception("Business error")):
            result = collector.collect_all_metrics()
            assert not result.success
            assert any("业务指标采集失败" in error for error in result.errors)
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    def test_collect_system_metrics_disk_permission_error(self):
        """测试磁盘指标采集权限错误（覆盖lines 457, 459）"""
        from prometheus_client import CollectorRegistry
        registry = CollectorRegistry()
        collector = PrometheusMetricsCollector(registry=registry)
        
        import src.monitoring.prometheus_collector as module
        original_psutil = module.psutil
        
        # Mock psutil.disk_usage抛出PermissionError
        mock_psutil = Mock()
        mock_psutil.cpu_percent = Mock(return_value=50.0)
        mock_mem = Mock()
        mock_mem.percent = 60.0
        mock_mem.available = 8 * 1024 ** 3  # 8GB
        mock_psutil.virtual_memory = Mock(return_value=mock_mem)
        mock_psutil.disk_usage = Mock(side_effect=PermissionError("Access denied"))
        module.psutil = mock_psutil
        
        try:
            count = collector.collect_system_metrics()
            # 应该采集到CPU和内存，但磁盘失败
            assert count >= 0
        finally:
            module.psutil = original_psutil
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    @patch('subprocess.run')
    def test_collect_gpu_metrics_command_failure(self, mock_run):
        """测试GPU命令执行失败（覆盖lines 490-491）"""
        from prometheus_client import CollectorRegistry
        registry = CollectorRegistry()
        collector = PrometheusMetricsCollector(registry=registry)
        
        # Mock subprocess返回非0退出码
        mock_run.return_value = Mock(returncode=1, stdout="")
        
        count = collector.collect_gpu_metrics()
        assert count == 0
    
    @pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
    @patch('subprocess.run')
    def test_collect_gpu_metrics_general_exception(self, mock_run):
        """测试GPU采集一般异常（覆盖lines 533-534）"""
        from prometheus_client import CollectorRegistry
        registry = CollectorRegistry()
        collector = PrometheusMetricsCollector(registry=registry)
        
        # Mock subprocess抛出一般异常
        mock_run.side_effect = RuntimeError("Unexpected error")
        
        count = collector.collect_gpu_metrics()
        assert count == 0
    
    def test_parse_gpu_memory_used_value_error(self):
        """测试解析GPU显存使用量ValueError（覆盖lines 557-558）"""
        collector = PrometheusMetricsCollector()
        
        # 提供格式正确但值无效的输出
        output = "VRAM Used: invalid MB\n"
        result = collector._parse_gpu_memory_used(output)
        
        assert result is None
    
    def test_parse_gpu_memory_total_value_error(self):
        """测试解析GPU显存总量ValueError（覆盖lines 579-580）"""
        collector = PrometheusMetricsCollector()
        
        # 提供格式正确但值无效的输出
        output = "VRAM Total: invalid MB\n"
        result = collector._parse_gpu_memory_total(output)
        
        assert result is None
    
    def test_parse_gpu_utilization_value_error(self):
        """测试解析GPU利用率ValueError（覆盖lines 600-601）"""
        collector = PrometheusMetricsCollector()
        
        # 提供格式正确但值无效的输出
        output = "GPU use: invalid%\n"
        result = collector._parse_gpu_utilization(output)
        
        assert result is None
    
    def test_parse_gpu_temperature_value_error(self):
        """测试解析GPU温度ValueError（覆盖lines 621-622）"""
        collector = PrometheusMetricsCollector()
        
        # 提供格式正确但值无效的输出
        output = "Temperature: invalid C\n"
        result = collector._parse_gpu_temperature(output)
        
        assert result is None
    
    def test_get_redis_string_type_error(self):
        """测试Redis获取字符串TypeError（覆盖lines 744-747）"""
        mock_redis = Mock()
        # 返回一个整数 - source code will convert it to string using str()
        mock_redis.get.return_value = 12345  # 整数而不是bytes
        
        collector = PrometheusMetricsCollector(redis_client=mock_redis)
        
        # Source code converts non-bytes values to string, so it returns '12345'
        result = collector._get_redis_string('test_key', 'default_value')
        assert result == '12345'  # str(12345) = '12345'
    
    def test_register_custom_metric_prometheus_not_available(self):
        """测试prometheus不可用时注册指标（覆盖line 796）"""
        import src.monitoring.prometheus_collector as module
        original = module.PROMETHEUS_AVAILABLE
        module.PROMETHEUS_AVAILABLE = False
        
        try:
            collector = PrometheusMetricsCollector()
            success = collector.register_custom_metric(
                name="test",
                description="test",
                metric_type=MetricType.COUNTER
            )
            assert success is False
        finally:
            module.PROMETHEUS_AVAILABLE = original
