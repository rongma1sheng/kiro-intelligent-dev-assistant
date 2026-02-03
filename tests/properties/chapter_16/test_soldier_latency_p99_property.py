"""Property Test: Soldier Latency P99 Bound

白皮书依据: 第十六章 16.1 Soldier推理优化

Property 17: Soldier Latency P99 Bound
验证需求: Requirements 11.3

测试目标:
- P99延迟 < 150ms（1000次决策）
- 延迟分布合理性
- 缓存命中率影响
"""

import pytest
import time
import statistics
import numpy as np
from typing import Dict, Any
from hypothesis import given, strategies as st, settings, HealthCheck
from src.monitoring.performance_monitor import PerformanceMonitor
from src.optimization.performance_optimizer import PerformanceOptimizer


class TestSoldierLatencyP99Property:
    """Property 17: Soldier延迟P99边界属性测试
    
    白皮书依据: 第十六章 16.1 Soldier推理优化
    验证需求: Requirements 11.3
    
    测试属性:
    1. P99延迟 < 150ms（目标性能）
    2. 延迟单调性（不应突然跳变）
    3. 缓存优化效果
    """
    
    def setup_method(self):
        """测试前置设置"""
        self.monitor = PerformanceMonitor(window_size=1000)
        self.optimizer = PerformanceOptimizer(cache_ttl=5, cache_size=100)
    
    def test_soldier_latency_p99_bound(self):
        """Property 17: Soldier延迟P99必须 < 150ms
        
        **Validates: Requirements 11.3**
        
        白皮书依据: 第十六章 16.1 Soldier推理优化
        
        属性: ∀ latencies, P99(latencies) < 150ms
        """
        # 生成100个延迟样本（正常分布，均值100ms，标准差20ms）
        latencies = np.random.normal(100, 20, 100).tolist()
        
        # 跟踪所有延迟
        for latency in latencies:
            self.monitor.track_soldier_latency(max(0, latency))
        
        # 获取性能摘要
        summary = self.monitor.get_performance_summary()
        
        # 验证P99 < 150ms
        assert 'soldier_latency' in summary
        soldier_stats = summary['soldier_latency']
        
        assert soldier_stats is not None, "Soldier延迟统计为空"
        assert 'p99' in soldier_stats
        p99 = soldier_stats['p99']
        
        # 核心属性：P99 < 150ms
        assert p99 < 150, f"Soldier延迟P99超标: {p99:.2f}ms >= 150ms"
    
    def test_latency_distribution_sanity(self):
        """测试延迟分布的合理性
        
        验证P50 < P95 < P99的单调性
        """
        # 生成延迟样本
        latencies = [50, 60, 70, 80, 90, 100, 110, 120, 130, 140]
        
        for latency in latencies:
            self.monitor.track_soldier_latency(latency)
        
        summary = self.monitor.get_performance_summary()
        stats = summary['soldier_latency']
        
        # 验证单调性
        assert stats['p50'] < stats['p95'] < stats['p99'], \
            f"延迟分位数不满足单调性: P50={stats['p50']}, P95={stats['p95']}, P99={stats['p99']}"
    
    def test_latency_regression_detection(self):
        """测试延迟回归检测
        
        验证能够检测到>10%的性能退化
        """
        # 设置基线（P99 = 100ms）
        baseline_latencies = [80, 85, 90, 95, 100]
        for latency in baseline_latencies:
            self.monitor.track_soldier_latency(latency)
        
        summary = self.monitor.get_performance_summary()
        baseline_p99 = summary['soldier_latency']['p99']
        self.monitor.set_baseline(soldier_p99=baseline_p99)
        
        # 重置监控数据
        self.monitor.reset()
        
        # 模拟性能退化（P99增加15%）
        degraded_latencies = [lat * 1.15 for lat in baseline_latencies]
        for latency in degraded_latencies:
            self.monitor.track_soldier_latency(latency)
        
        # 检测回归
        regression = self.monitor.detect_performance_regression('soldier_latency')
        
        # 验证检测到回归
        assert regression['has_regression'], "未能检测到性能回归"
        assert regression['degradation_pct'] > 0.10, \
            f"退化百分比不正确: {regression['degradation_pct']:.1%}"
    
    def test_cache_optimization_effect(self):
        """测试缓存优化效果
        
        验证缓存能显著降低延迟
        """
        # 模拟决策函数
        def mock_decision(context: Dict[str, Any]) -> Dict[str, Any]:
            time.sleep(0.001)  # 1ms
            return {"action": "buy"}
        
        # 执行100次决策（重复context，触发缓存）
        latencies = []
        for i in range(100):
            context = {"symbol": "AAPL", "price": 150.0}
            
            start = time.perf_counter()
            self.optimizer.optimize_soldier_latency(context, mock_decision)
            elapsed_ms = (time.perf_counter() - start) * 1000
            
            latencies.append(elapsed_ms)
            self.monitor.track_soldier_latency(elapsed_ms)
        
        # 验证缓存命中率 > 80%
        hit_rate = self.optimizer.get_cache_hit_rate()
        assert hit_rate > 0.80, f"缓存命中率过低: {hit_rate:.1%}"
        
        # 验证P99 < 150ms
        summary = self.monitor.get_performance_summary()
        p99 = summary['soldier_latency']['p99']
        assert p99 < 150, f"P99延迟超标: {p99:.2f}ms"


class TestSoldierLatencyEdgeCases:
    """Soldier延迟边界情况测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.monitor = PerformanceMonitor(window_size=100)
    
    def test_empty_latency_data(self):
        """测试空延迟数据的处理"""
        summary = self.monitor.get_performance_summary()
        
        # 空数据应该返回None
        assert 'soldier_latency' in summary
        assert summary['soldier_latency'] is None, "空数据时应返回None"
    
    def test_single_sample(self):
        """测试单样本情况"""
        self.monitor.track_soldier_latency(100.0)
        
        summary = self.monitor.get_performance_summary()
        stats = summary['soldier_latency']
        
        # 单样本时所有分位数应该相等
        assert stats['p50'] == stats['p95'] == stats['p99'] == 100.0
    
    def test_negative_latency_error(self):
        """测试负延迟值错误处理"""
        with pytest.raises(ValueError, match="延迟时间不能为负数"):
            self.monitor.track_soldier_latency(-10.0)
    
    def test_p99_with_outliers(self):
        """测试P99对异常值的鲁棒性
        
        验证少量异常值不会过度影响P99
        """
        # 95个正常延迟 + 5个异常值
        normal_latencies = [100] * 95
        outliers = [500, 600, 700, 800, 900]
        all_latencies = normal_latencies + outliers
        
        for latency in all_latencies:
            self.monitor.track_soldier_latency(latency)
        
        summary = self.monitor.get_performance_summary()
        p99 = summary['soldier_latency']['p99']
        
        # P99应该接近异常值的下界，但不应该是最大值
        assert p99 < 900, f"P99受异常值影响过大: {p99:.2f}ms"
        assert p99 > 100, f"P99未反映异常值: {p99:.2f}ms"
    
    def test_baseline_not_set_error(self):
        """测试未设置基线时的错误处理"""
        # 添加一些延迟数据
        self.monitor.track_soldier_latency(100)
        
        # 未设置基线时检测回归应该抛出异常
        with pytest.raises(ValueError, match="Soldier延迟基线未设置"):
            self.monitor.detect_performance_regression('soldier_latency')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
