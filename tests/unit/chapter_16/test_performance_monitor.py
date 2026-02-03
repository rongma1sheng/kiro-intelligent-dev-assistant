"""Unit tests for PerformanceMonitor

白皮书依据: 第十六章 16.0 性能优化指南
测试目标: 100% coverage
"""

import pytest
import time
from src.monitoring.performance_monitor import PerformanceMonitor


class TestPerformanceMonitorInit:
    """测试PerformanceMonitor初始化"""
    
    def test_init_default_params(self):
        """测试默认参数初始化"""
        monitor = PerformanceMonitor()
        
        assert monitor.window_size == 1000
        assert monitor.regression_threshold == 0.10
        assert len(monitor.soldier_latencies) == 0
        assert len(monitor.redis_throughputs) == 0
        assert monitor.baseline_soldier_p99 is None
        assert monitor.baseline_redis_throughput is None
    
    def test_init_custom_params(self):
        """测试自定义参数初始化"""
        monitor = PerformanceMonitor(
            window_size=500,
            regression_threshold=0.15
        )
        
        assert monitor.window_size == 500
        assert monitor.regression_threshold == 0.15
    
    def test_init_invalid_window_size(self):
        """测试无效的窗口大小"""
        with pytest.raises(ValueError, match="窗口大小必须 > 0"):
            PerformanceMonitor(window_size=0)
        
        with pytest.raises(ValueError, match="窗口大小必须 > 0"):
            PerformanceMonitor(window_size=-1)
    
    def test_init_invalid_regression_threshold(self):
        """测试无效的回归阈值"""
        with pytest.raises(ValueError, match="回归阈值必须在 \\(0, 1\\) 范围内"):
            PerformanceMonitor(regression_threshold=0)
        
        with pytest.raises(ValueError, match="回归阈值必须在 \\(0, 1\\) 范围内"):
            PerformanceMonitor(regression_threshold=1.0)
        
        with pytest.raises(ValueError, match="回归阈值必须在 \\(0, 1\\) 范围内"):
            PerformanceMonitor(regression_threshold=-0.1)


class TestTrackSoldierLatency:
    """测试Soldier延迟跟踪"""
    
    def test_track_soldier_latency_single(self):
        """测试单个延迟记录"""
        monitor = PerformanceMonitor()
        
        stats = monitor.track_soldier_latency(100.0)
        
        assert stats['p50'] == 100.0
        assert stats['p95'] == 100.0
        assert stats['p99'] == 100.0
        assert stats['mean'] == 100.0
        assert stats['count'] == 1
    
    def test_track_soldier_latency_multiple(self):
        """测试多个延迟记录"""
        monitor = PerformanceMonitor()
        
        latencies = [50, 100, 150, 200, 250]
        for latency in latencies:
            monitor.track_soldier_latency(latency)
        
        stats = monitor.track_soldier_latency(300)
        
        assert stats['count'] == 6
        assert stats['mean'] == pytest.approx(175.0)
        assert stats['p50'] == pytest.approx(175.0, abs=5)  # 允许一定误差
        assert stats['p99'] == pytest.approx(300, abs=5)  # 允许一定误差
    
    def test_track_soldier_latency_negative(self):
        """测试负延迟"""
        monitor = PerformanceMonitor()
        
        with pytest.raises(ValueError, match="延迟时间不能为负数"):
            monitor.track_soldier_latency(-10.0)
    
    def test_track_soldier_latency_exceeds_target(self):
        """测试延迟超过目标（P99 < 150ms）"""
        monitor = PerformanceMonitor()
        
        # 添加一些延迟，使P99超过150ms
        for _ in range(100):
            stats = monitor.track_soldier_latency(160.0)
        
        # 验证P99超过150ms
        assert stats['p99'] > 150
    
    def test_track_soldier_latency_window_size(self):
        """测试窗口大小限制"""
        monitor = PerformanceMonitor(window_size=10)
        
        # 添加15个延迟
        for i in range(15):
            monitor.track_soldier_latency(float(i))
        
        # 应该只保留最后10个
        assert len(monitor.soldier_latencies) == 10
        assert list(monitor.soldier_latencies) == [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0]


class TestTrackRedisThroughput:
    """测试Redis吞吐量跟踪"""
    
    def test_track_redis_throughput_single(self):
        """测试单个吞吐量记录"""
        monitor = PerformanceMonitor()
        
        stats = monitor.track_redis_throughput(operations=1000, elapsed_seconds=0.01)
        
        assert stats['current'] == 100000.0
        assert stats['mean'] == 100000.0
        assert stats['min'] == 100000.0
        assert stats['max'] == 100000.0
        assert stats['count'] == 1
    
    def test_track_redis_throughput_multiple(self):
        """测试多个吞吐量记录"""
        monitor = PerformanceMonitor()
        
        monitor.track_redis_throughput(1000, 0.01)  # 100K ops/s
        monitor.track_redis_throughput(2000, 0.01)  # 200K ops/s
        stats = monitor.track_redis_throughput(1500, 0.01)  # 150K ops/s
        
        assert stats['count'] == 3
        assert stats['current'] == 150000.0
        assert stats['mean'] == pytest.approx(150000.0)
        assert stats['min'] == 100000.0
        assert stats['max'] == 200000.0
    
    def test_track_redis_throughput_negative_operations(self):
        """测试负操作数"""
        monitor = PerformanceMonitor()
        
        with pytest.raises(ValueError, match="操作数不能为负数"):
            monitor.track_redis_throughput(-100, 1.0)
    
    def test_track_redis_throughput_zero_elapsed(self):
        """测试零耗时"""
        monitor = PerformanceMonitor()
        
        with pytest.raises(ValueError, match="耗时必须 > 0"):
            monitor.track_redis_throughput(1000, 0)
    
    def test_track_redis_throughput_negative_elapsed(self):
        """测试负耗时"""
        monitor = PerformanceMonitor()
        
        with pytest.raises(ValueError, match="耗时必须 > 0"):
            monitor.track_redis_throughput(1000, -1.0)
    
    def test_track_redis_throughput_below_target(self):
        """测试吞吐量低于目标（> 150K ops/s）"""
        monitor = PerformanceMonitor()
        
        stats = monitor.track_redis_throughput(1000, 0.01)  # 100K ops/s
        
        # 验证吞吐量低于目标
        assert stats['current'] < 150000
    
    def test_track_redis_throughput_window_size(self):
        """测试窗口大小限制"""
        monitor = PerformanceMonitor(window_size=5)
        
        # 添加10个吞吐量记录
        for i in range(10):
            monitor.track_redis_throughput(1000, 0.01)
        
        # 应该只保留最后5个
        assert len(monitor.redis_throughputs) == 5


class TestDetectPerformanceRegression:
    """测试性能回归检测"""
    
    def test_detect_regression_soldier_latency_no_regression(self):
        """测试Soldier延迟无回归"""
        monitor = PerformanceMonitor(regression_threshold=0.10)
        
        # 设置基线
        monitor.set_baseline(soldier_p99=100.0)
        
        # 添加延迟数据（P99 = 105ms，退化5%）
        for _ in range(100):
            monitor.track_soldier_latency(105.0)
        
        result = monitor.detect_performance_regression('soldier_latency')
        
        assert result['has_regression'] is False
        assert result['current_value'] == 105.0
        assert result['baseline_value'] == 100.0
        assert result['degradation_pct'] == pytest.approx(0.05)
    
    def test_detect_regression_soldier_latency_has_regression(self):
        """测试Soldier延迟有回归"""
        monitor = PerformanceMonitor(regression_threshold=0.10)
        
        # 设置基线
        monitor.set_baseline(soldier_p99=100.0)
        
        # 添加延迟数据（P99 = 120ms，退化20%）
        for _ in range(100):
            monitor.track_soldier_latency(120.0)
        
        result = monitor.detect_performance_regression('soldier_latency')
        
        assert result['has_regression'] is True
        assert result['current_value'] == 120.0
        assert result['baseline_value'] == 100.0
        assert result['degradation_pct'] == pytest.approx(0.20)
    
    def test_detect_regression_redis_throughput_no_regression(self):
        """测试Redis吞吐量无回归"""
        monitor = PerformanceMonitor(regression_threshold=0.10)
        
        # 设置基线
        monitor.set_baseline(redis_throughput=100000.0)
        
        # 添加吞吐量数据（平均 95K ops/s，退化5%）
        for _ in range(10):
            monitor.track_redis_throughput(950, 0.01)
        
        result = monitor.detect_performance_regression('redis_throughput')
        
        assert result['has_regression'] is False
        assert result['current_value'] == pytest.approx(95000.0)
        assert result['baseline_value'] == 100000.0
        assert result['degradation_pct'] == pytest.approx(0.05)
    
    def test_detect_regression_redis_throughput_has_regression(self):
        """测试Redis吞吐量有回归"""
        monitor = PerformanceMonitor(regression_threshold=0.10)
        
        # 设置基线
        monitor.set_baseline(redis_throughput=100000.0)
        
        # 添加吞吐量数据（平均 80K ops/s，退化20%）
        for _ in range(10):
            monitor.track_redis_throughput(800, 0.01)
        
        result = monitor.detect_performance_regression('redis_throughput')
        
        assert result['has_regression'] is True
        assert result['current_value'] == pytest.approx(80000.0)
        assert result['baseline_value'] == 100000.0
        assert result['degradation_pct'] == pytest.approx(0.20)
    
    def test_detect_regression_invalid_metric_type(self):
        """测试无效的指标类型"""
        monitor = PerformanceMonitor()
        
        with pytest.raises(ValueError, match="无效的指标类型"):
            monitor.detect_performance_regression('invalid_metric')
    
    def test_detect_regression_no_baseline_soldier(self):
        """测试Soldier延迟基线未设置"""
        monitor = PerformanceMonitor()
        
        monitor.track_soldier_latency(100.0)
        
        with pytest.raises(ValueError, match="Soldier延迟基线未设置"):
            monitor.detect_performance_regression('soldier_latency')
    
    def test_detect_regression_no_baseline_redis(self):
        """测试Redis吞吐量基线未设置"""
        monitor = PerformanceMonitor()
        
        monitor.track_redis_throughput(1000, 0.01)
        
        with pytest.raises(ValueError, match="Redis吞吐量基线未设置"):
            monitor.detect_performance_regression('redis_throughput')
    
    def test_detect_regression_no_data_soldier(self):
        """测试Soldier延迟数据为空"""
        monitor = PerformanceMonitor()
        
        monitor.set_baseline(soldier_p99=100.0)
        
        with pytest.raises(ValueError, match="Soldier延迟数据为空"):
            monitor.detect_performance_regression('soldier_latency')
    
    def test_detect_regression_no_data_redis(self):
        """测试Redis吞吐量数据为空"""
        monitor = PerformanceMonitor()
        
        monitor.set_baseline(redis_throughput=100000.0)
        
        with pytest.raises(ValueError, match="Redis吞吐量数据为空"):
            monitor.detect_performance_regression('redis_throughput')


class TestSetBaseline:
    """测试设置基线"""
    
    def test_set_baseline_soldier_only(self):
        """测试仅设置Soldier基线"""
        monitor = PerformanceMonitor()
        
        monitor.set_baseline(soldier_p99=100.0)
        
        assert monitor.baseline_soldier_p99 == 100.0
        assert monitor.baseline_redis_throughput is None
    
    def test_set_baseline_redis_only(self):
        """测试仅设置Redis基线"""
        monitor = PerformanceMonitor()
        
        monitor.set_baseline(redis_throughput=150000.0)
        
        assert monitor.baseline_soldier_p99 is None
        assert monitor.baseline_redis_throughput == 150000.0
    
    def test_set_baseline_both(self):
        """测试同时设置两个基线"""
        monitor = PerformanceMonitor()
        
        monitor.set_baseline(soldier_p99=100.0, redis_throughput=150000.0)
        
        assert monitor.baseline_soldier_p99 == 100.0
        assert monitor.baseline_redis_throughput == 150000.0
    
    def test_set_baseline_invalid_soldier(self):
        """测试无效的Soldier基线"""
        monitor = PerformanceMonitor()
        
        with pytest.raises(ValueError, match="Soldier延迟基线必须 > 0"):
            monitor.set_baseline(soldier_p99=0)
        
        with pytest.raises(ValueError, match="Soldier延迟基线必须 > 0"):
            monitor.set_baseline(soldier_p99=-10.0)
    
    def test_set_baseline_invalid_redis(self):
        """测试无效的Redis基线"""
        monitor = PerformanceMonitor()
        
        with pytest.raises(ValueError, match="Redis吞吐量基线必须 > 0"):
            monitor.set_baseline(redis_throughput=0)
        
        with pytest.raises(ValueError, match="Redis吞吐量基线必须 > 0"):
            monitor.set_baseline(redis_throughput=-1000.0)


class TestGetPerformanceSummary:
    """测试获取性能摘要"""
    
    def test_get_performance_summary_empty(self):
        """测试空数据摘要"""
        monitor = PerformanceMonitor()
        
        summary = monitor.get_performance_summary()
        
        assert summary['soldier_latency'] is None
        assert summary['redis_throughput'] is None
        assert summary['baselines']['soldier_p99'] is None
        assert summary['baselines']['redis_throughput'] is None
        assert summary['sample_counts']['soldier'] == 0
        assert summary['sample_counts']['redis'] == 0
    
    def test_get_performance_summary_with_data(self):
        """测试有数据的摘要"""
        monitor = PerformanceMonitor()
        
        # 添加数据
        monitor.track_soldier_latency(100.0)
        monitor.track_soldier_latency(150.0)
        monitor.track_redis_throughput(1000, 0.01)
        
        # 设置基线
        monitor.set_baseline(soldier_p99=120.0, redis_throughput=100000.0)
        
        summary = monitor.get_performance_summary()
        
        assert summary['soldier_latency'] is not None
        assert summary['soldier_latency']['count'] == 2
        assert summary['redis_throughput'] is not None
        assert summary['redis_throughput']['count'] == 1
        assert summary['baselines']['soldier_p99'] == 120.0
        assert summary['baselines']['redis_throughput'] == 100000.0
        assert summary['sample_counts']['soldier'] == 2
        assert summary['sample_counts']['redis'] == 1


class TestCalculateLatencyStats:
    """测试延迟统计计算"""
    
    def test_calculate_latency_stats_empty(self):
        """测试空延迟列表"""
        monitor = PerformanceMonitor()
        
        stats = monitor._calculate_latency_stats([])
        
        assert stats['p50'] == 0.0
        assert stats['p95'] == 0.0
        assert stats['p99'] == 0.0
        assert stats['mean'] == 0.0
        assert stats['count'] == 0
    
    def test_calculate_latency_stats_single(self):
        """测试单个延迟"""
        monitor = PerformanceMonitor()
        
        stats = monitor._calculate_latency_stats([100.0])
        
        assert stats['p50'] == 100.0
        assert stats['p95'] == 100.0
        assert stats['p99'] == 100.0
        assert stats['mean'] == 100.0
        assert stats['count'] == 1
    
    def test_calculate_latency_stats_multiple(self):
        """测试多个延迟"""
        monitor = PerformanceMonitor()
        
        latencies = list(range(1, 101))  # 1-100
        stats = monitor._calculate_latency_stats(latencies)
        
        assert stats['p50'] == pytest.approx(50.5, abs=1)  # 允许一定误差
        assert stats['p95'] == pytest.approx(95.5, abs=1)
        assert stats['p99'] == pytest.approx(99.5, abs=1)
        assert stats['mean'] == pytest.approx(50.5)
        assert stats['count'] == 100


class TestCalculateThroughputStats:
    """测试吞吐量统计计算"""
    
    def test_calculate_throughput_stats_empty(self):
        """测试空吞吐量列表"""
        monitor = PerformanceMonitor()
        
        stats = monitor._calculate_throughput_stats([])
        
        assert stats['current'] == 0.0
        assert stats['mean'] == 0.0
        assert stats['min'] == 0.0
        assert stats['max'] == 0.0
        assert stats['count'] == 0
    
    def test_calculate_throughput_stats_single(self):
        """测试单个吞吐量"""
        monitor = PerformanceMonitor()
        
        stats = monitor._calculate_throughput_stats([100000.0])
        
        assert stats['current'] == 100000.0
        assert stats['mean'] == 100000.0
        assert stats['min'] == 100000.0
        assert stats['max'] == 100000.0
        assert stats['count'] == 1
    
    def test_calculate_throughput_stats_multiple(self):
        """测试多个吞吐量"""
        monitor = PerformanceMonitor()
        
        throughputs = [100000.0, 150000.0, 200000.0]
        stats = monitor._calculate_throughput_stats(throughputs)
        
        assert stats['current'] == 200000.0
        assert stats['mean'] == pytest.approx(150000.0)
        assert stats['min'] == 100000.0
        assert stats['max'] == 200000.0
        assert stats['count'] == 3


class TestCalculatePercentile:
    """测试百分位数计算"""
    
    def test_calculate_percentile_empty(self):
        """测试空列表"""
        monitor = PerformanceMonitor()
        
        result = monitor._calculate_percentile([], 50)
        
        assert result == 0.0
    
    def test_calculate_percentile_single(self):
        """测试单个值"""
        monitor = PerformanceMonitor()
        
        result = monitor._calculate_percentile([100.0], 50)
        
        assert result == 100.0
    
    def test_calculate_percentile_multiple(self):
        """测试多个值"""
        monitor = PerformanceMonitor()
        
        values = list(range(1, 101))  # 1-100
        
        p50 = monitor._calculate_percentile(values, 50)
        p95 = monitor._calculate_percentile(values, 95)
        p99 = monitor._calculate_percentile(values, 99)
        
        assert p50 == pytest.approx(50.5, abs=1)
        assert p95 == pytest.approx(95.5, abs=1)
        assert p99 == pytest.approx(99.5, abs=1)
    
    def test_calculate_percentile_boundary_values(self):
        """测试边界百分位数（0%和100%）"""
        monitor = PerformanceMonitor()
        
        values = [10, 20, 30, 40, 50]
        
        # 测试0%百分位数（最小值）
        p0 = monitor._calculate_percentile(values, 0)
        assert p0 == 10
        
        # 测试100%百分位数（最大值）
        p100 = monitor._calculate_percentile(values, 100)
        assert p100 == 50


class TestResetAndClear:
    """测试重置和清除"""
    
    def test_reset(self):
        """测试重置监控数据"""
        monitor = PerformanceMonitor()
        
        # 添加数据
        monitor.track_soldier_latency(100.0)
        monitor.track_redis_throughput(1000, 0.01)
        
        monitor.reset()
        
        assert len(monitor.soldier_latencies) == 0
        assert len(monitor.redis_throughputs) == 0
    
    def test_clear_baselines(self):
        """测试清除基线"""
        monitor = PerformanceMonitor()
        
        # 设置基线
        monitor.set_baseline(soldier_p99=100.0, redis_throughput=150000.0)
        
        monitor.clear_baselines()
        
        assert monitor.baseline_soldier_p99 is None
        assert monitor.baseline_redis_throughput is None
