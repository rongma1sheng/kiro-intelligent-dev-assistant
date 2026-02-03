"""Property Test: Performance Regression Detection

白皮书依据: 第十六章 16.3 性能回归检测

Property 19: Performance Regression Detection
验证需求: Requirements 11.5

测试目标:
- 回归检测阈值 > 10%
- 误报率低（< 5%）
- 检测延迟短（< 100样本）
"""

import pytest
import statistics
import random
from typing import List
from hypothesis import given, strategies as st, settings, HealthCheck
from src.monitoring.performance_monitor import PerformanceMonitor


class TestPerformanceRegressionProperty:
    """Property 19: 性能回归检测属性测试
    
    白皮书依据: 第十六章 16.3 性能回归检测
    验证需求: Requirements 11.5
    
    测试属性:
    1. 回归检测阈值 > 10%
    2. 误报率低（< 5%）
    3. 真阳性率高（> 95%）
    4. 检测延迟短
    """
    
    def setup_method(self):
        """测试前置设置"""
        self.monitor = PerformanceMonitor(window_size=100, regression_threshold=0.10)
    
    def test_regression_detection_threshold(self):
        """Property 19: 性能回归检测阈值 > 10%
        
        **Validates: Requirements 11.5**
        
        白皮书依据: 第十六章 16.3 性能回归检测
        
        属性: ∀ degradation > 10%, detect_regression() = True
        """
        # 建立基线：Soldier延迟100ms
        for i in range(100):
            self.monitor.track_soldier_latency(100.0)
        
        summary = self.monitor.get_performance_summary()
        self.monitor.set_baseline(soldier_p99=summary['soldier_latency']['p99'])
        
        # 重置监控数据
        self.monitor.reset()
        
        # 测试场景1：性能下降9%（不应触发）
        for i in range(100):
            self.monitor.track_soldier_latency(109.0)  # 9%增长
        
        regression = self.monitor.detect_performance_regression('soldier_latency')
        assert not regression['has_regression'], "9%下降不应触发回归告警"
        
        # 重置监控数据
        self.monitor.reset()
        
        # 测试场景2：性能下降11%（应该触发）
        for i in range(100):
            self.monitor.track_soldier_latency(111.0)  # 11%增长
        
        regression = self.monitor.detect_performance_regression('soldier_latency')
        assert regression['has_regression'], "11%下降应该触发回归告警"
        assert regression['degradation_pct'] > 0.10, \
            f"回归幅度应 > 10%: {regression['degradation_pct']:.1%}"
    
    def test_false_positive_rate(self):
        """测试回归检测误报率 < 5%
        
        验证性能稳定时误报率低
        """
        false_positives = 0
        total_tests = 100
        
        for test_run in range(total_tests):
            monitor = PerformanceMonitor(window_size=50, regression_threshold=0.10)
            
            # 建立基线
            for i in range(50):
                monitor.track_soldier_latency(100.0)
            
            summary = monitor.get_performance_summary()
            monitor.set_baseline(soldier_p99=summary['soldier_latency']['p99'])
            
            # 重置监控数据
            monitor.reset()
            
            # 性能保持稳定（±5%随机波动）
            random.seed(test_run)
            for i in range(50):
                latency = 100.0 * (1 + random.uniform(-0.05, 0.05))
                monitor.track_soldier_latency(latency)
            
            # 检测回归
            regression = monitor.detect_performance_regression('soldier_latency')
            if regression['has_regression']:
                false_positives += 1
        
        # 计算误报率
        false_positive_rate = false_positives / total_tests
        
        # 验证误报率 < 5%
        assert false_positive_rate < 0.05, \
            f"误报率过高: {false_positive_rate:.1%} > 5%"
    
    def test_true_positive_rate(self):
        """测试回归检测真阳性率 > 95%
        
        验证真实回归时检测率高
        """
        true_positives = 0
        total_tests = 100
        
        for test_run in range(total_tests):
            monitor = PerformanceMonitor(window_size=50, regression_threshold=0.10)
            
            # 建立基线
            for i in range(50):
                monitor.track_soldier_latency(100.0)
            
            summary = monitor.get_performance_summary()
            monitor.set_baseline(soldier_p99=summary['soldier_latency']['p99'])
            
            # 重置监控数据
            monitor.reset()
            
            # 性能明显下降（20%）
            for i in range(50):
                monitor.track_soldier_latency(120.0)  # 20%增长
            
            # 检测回归
            regression = monitor.detect_performance_regression('soldier_latency')
            if regression['has_regression']:
                true_positives += 1
        
        # 计算真阳性率
        true_positive_rate = true_positives / total_tests
        
        # 验证真阳性率 > 95%
        assert true_positive_rate > 0.95, \
            f"检测率过低: {true_positive_rate:.1%} < 95%"
    
    def test_both_metrics_independent(self):
        """测试同时检测Soldier和Redis回归
        
        验证能独立检测两个指标的回归
        """
        # 建立基线
        for i in range(100):
            self.monitor.track_soldier_latency(100.0)
            self.monitor.track_redis_throughput(10000, 0.05)  # 200K ops/s
        
        summary = self.monitor.get_performance_summary()
        self.monitor.set_baseline(
            soldier_p99=summary['soldier_latency']['p99'],
            redis_throughput=summary['redis_throughput']['mean']
        )
        
        # 重置监控数据
        self.monitor.reset()
        
        # 场景1：只有Soldier回归
        for i in range(100):
            self.monitor.track_soldier_latency(120.0)  # 20%增长
            self.monitor.track_redis_throughput(10000, 0.05)  # 保持不变
        
        soldier_regression = self.monitor.detect_performance_regression('soldier_latency')
        redis_regression = self.monitor.detect_performance_regression('redis_throughput')
        
        assert soldier_regression['has_regression'], "应该检测到Soldier回归"
        assert not redis_regression['has_regression'], "不应检测到Redis回归"


class TestPerformanceRegressionEdgeCases:
    """性能回归检测边界情况测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.monitor = PerformanceMonitor(window_size=100, regression_threshold=0.10)
    
    def test_no_baseline_error(self):
        """测试无基线时的回归检测"""
        # 添加数据但不设置基线
        for i in range(100):
            self.monitor.track_soldier_latency(100.0)
        
        # 无基线时应该抛出异常
        with pytest.raises(ValueError, match="Soldier延迟基线未设置"):
            self.monitor.detect_performance_regression('soldier_latency')
    
    def test_empty_data_error(self):
        """测试数据为空时的回归检测"""
        # 设置基线但不添加数据
        self.monitor.set_baseline(soldier_p99=100.0)
        
        # 数据为空时应该抛出异常
        with pytest.raises(ValueError, match="Soldier延迟数据为空"):
            self.monitor.detect_performance_regression('soldier_latency')
    
    def test_invalid_metric_type(self):
        """测试无效的指标类型"""
        # 添加数据
        for i in range(100):
            self.monitor.track_soldier_latency(100.0)
        
        summary = self.monitor.get_performance_summary()
        self.monitor.set_baseline(soldier_p99=summary['soldier_latency']['p99'])
        
        # 使用无效的指标类型
        with pytest.raises(ValueError, match="无效的指标类型"):
            self.monitor.detect_performance_regression('invalid_metric')
    
    def test_performance_improvement(self):
        """测试性能提升（不应触发回归）"""
        # 建立基线
        for i in range(100):
            self.monitor.track_soldier_latency(100.0)
        
        summary = self.monitor.get_performance_summary()
        self.monitor.set_baseline(soldier_p99=summary['soldier_latency']['p99'])
        
        # 重置监控数据
        self.monitor.reset()
        
        # 性能大幅提升（50%）
        for i in range(100):
            self.monitor.track_soldier_latency(50.0)  # 50%减少
        
        regression = self.monitor.detect_performance_regression('soldier_latency')
        assert not regression['has_regression'], "性能提升不应触发回归告警"
    
    def test_gradual_degradation(self):
        """测试渐进式性能下降"""
        # 建立基线
        for i in range(100):
            self.monitor.track_soldier_latency(100.0)
        
        summary = self.monitor.get_performance_summary()
        self.monitor.set_baseline(soldier_p99=summary['soldier_latency']['p99'])
        
        # 重置监控数据
        self.monitor.reset()
        
        # 渐进式下降（每10个样本增加2%）
        current_latency = 100.0
        for batch in range(10):
            current_latency *= 1.02  # 每批增加2%
            for i in range(10):
                self.monitor.track_soldier_latency(current_latency)
        
        # 总共下降约22%，应该能检测到
        regression = self.monitor.detect_performance_regression('soldier_latency')
        assert regression['has_regression'], "应该检测到渐进式性能下降"
        assert regression['degradation_pct'] > 0.10, "回归幅度应 > 10%"
    
    def test_spike_recovery(self):
        """测试性能尖峰后恢复
        
        注意：P99计算使用线性插值。对于100个样本，P99位置在索引98.01，
        会插值第98和第99个样本。因此2个异常样本（2%）会直接影响P99。
        
        本测试使用1个异常样本（1%），确保P99不受影响。
        """
        # 建立基线
        for i in range(100):
            self.monitor.track_soldier_latency(100.0)
        
        summary = self.monitor.get_performance_summary()
        self.monitor.set_baseline(soldier_p99=summary['soldier_latency']['p99'])
        
        # 重置监控数据
        self.monitor.reset()
        
        # 短暂尖峰（1个样本，占1%）
        self.monitor.track_soldier_latency(200.0)  # 100%增长
        
        # 恢复正常（99个样本）
        for i in range(99):
            self.monitor.track_soldier_latency(100.0)
        
        # 由于只有1%的样本异常，P99不会受到影响
        # P99位置在第99个样本（索引98.01），排序后是正常值100ms
        regression = self.monitor.detect_performance_regression('soldier_latency')
        assert not regression['has_regression'], \
            f"短暂尖峰（1%样本）不应触发回归，但检测到 {regression['degradation_pct']:.1%} 退化"


class TestPerformanceRegressionCustomThreshold:
    """自定义回归阈值测试"""
    
    def test_custom_threshold_5_percent(self):
        """测试5%自定义阈值"""
        monitor = PerformanceMonitor(window_size=100, regression_threshold=0.05)
        
        # 建立基线
        for i in range(100):
            monitor.track_soldier_latency(100.0)
        
        summary = monitor.get_performance_summary()
        monitor.set_baseline(soldier_p99=summary['soldier_latency']['p99'])
        
        # 重置监控数据
        monitor.reset()
        
        # 性能下降6%（应该触发）
        for i in range(100):
            monitor.track_soldier_latency(106.0)
        
        regression = monitor.detect_performance_regression('soldier_latency')
        assert regression['has_regression'], "6%下降应该触发5%阈值的回归告警"
    
    def test_custom_threshold_20_percent(self):
        """测试20%自定义阈值"""
        monitor = PerformanceMonitor(window_size=100, regression_threshold=0.20)
        
        # 建立基线
        for i in range(100):
            monitor.track_soldier_latency(100.0)
        
        summary = monitor.get_performance_summary()
        monitor.set_baseline(soldier_p99=summary['soldier_latency']['p99'])
        
        # 重置监控数据
        monitor.reset()
        
        # 性能下降15%（不应触发）
        for i in range(100):
            monitor.track_soldier_latency(115.0)
        
        regression = monitor.detect_performance_regression('soldier_latency')
        assert not regression['has_regression'], "15%下降不应触发20%阈值的回归告警"
        
        # 重置监控数据
        monitor.reset()
        
        # 性能下降25%（应该触发）
        for i in range(100):
            monitor.track_soldier_latency(125.0)
        
        regression = monitor.detect_performance_regression('soldier_latency')
        assert regression['has_regression'], "25%下降应该触发20%阈值的回归告警"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
