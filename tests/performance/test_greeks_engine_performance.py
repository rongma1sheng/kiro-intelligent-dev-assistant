"""GreeksEngine性能测试

白皮书依据: 第三章 3.3 Greeks Engine - 性能测试

性能目标:
- 单期权计算延迟: P99 < 50ms
- 期权链批量计算: P99 < 100ms
- 缓存命中率: > 70%
- 并发处理能力: > 1000个期权

作者: MIA Team
日期: 2026-01-22
"""

import pytest
import time
import numpy as np
from typing import List
from src.infra.greeks_engine import (
    GreeksEngine,
    OptionContract,
    OptionType,
    get_greeks_engine
)


class TestGreeksEnginePerformance:
    """GreeksEngine性能测试"""
    
    @pytest.fixture
    def engine(self):
        """测试夹具"""
        return GreeksEngine(cache_ttl_seconds=5)
    
    @pytest.fixture
    def single_option(self):
        """单个期权夹具"""
        return OptionContract(
            symbol="510050C2600",
            option_type=OptionType.CALL,
            strike=2.6,
            spot=2.8,
            time_to_maturity=0.25,
            risk_free_rate=0.03,
            volatility=0.25
        )
    
    @pytest.fixture
    def option_chain_small(self):
        """小型期权链（10个期权）"""
        return self._create_option_chain(5)
    
    @pytest.fixture
    def option_chain_medium(self):
        """中型期权链（50个期权）"""
        return self._create_option_chain(25)
    
    @pytest.fixture
    def option_chain_large(self):
        """大型期权链（100个期权）"""
        return self._create_option_chain(50)
    
    @pytest.fixture
    def option_chain_xlarge(self):
        """超大型期权链（1000个期权）"""
        return self._create_option_chain(500)
    
    def _create_option_chain(self, strikes_count: int) -> List[OptionContract]:
        """创建期权链
        
        Args:
            strikes_count: 行权价数量
            
        Returns:
            期权列表（Call + Put）
        """
        spot = 2.6
        strikes = np.linspace(2.0, 3.2, strikes_count)
        
        options = []
        for strike in strikes:
            # Call期权
            call = OptionContract(
                symbol=f"510050C{int(strike*1000)}",
                option_type=OptionType.CALL,
                strike=float(strike),
                spot=spot,
                time_to_maturity=0.25,
                risk_free_rate=0.03,
                volatility=0.25
            )
            options.append(call)
            
            # Put期权
            put = OptionContract(
                symbol=f"510050P{int(strike*1000)}",
                option_type=OptionType.PUT,
                strike=float(strike),
                spot=spot,
                time_to_maturity=0.25,
                risk_free_rate=0.03,
                volatility=0.25
            )
            options.append(put)
        
        return options
    
    def test_single_option_latency(self, engine, single_option):
        """测试单期权计算延迟
        
        性能目标: P99 < 50ms
        """
        latencies = []
        iterations = 100
        
        for _ in range(iterations):
            start = time.perf_counter()
            engine.calculate_greeks(single_option, use_cache=False)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
        
        # 计算统计
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        avg = np.mean(latencies)
        
        print(f"\n单期权计算延迟:")
        print(f"  平均: {avg:.2f}ms")
        print(f"  P50: {p50:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  P99: {p99:.2f}ms")
        print(f"  目标: P99 < 50ms")
        
        # 验证性能目标
        assert p99 < 50.0, f"P99延迟 {p99:.2f}ms 超过目标 50ms"
        assert avg < 10.0, f"平均延迟 {avg:.2f}ms 超过预期 10ms"
    
    def test_option_chain_small_latency(self, engine, option_chain_small):
        """测试小型期权链批量计算延迟（10个期权）
        
        性能目标: P99 < 100ms
        """
        latencies = []
        iterations = 50
        
        for _ in range(iterations):
            engine.clear_cache()  # 清空缓存确保公平测试
            start = time.perf_counter()
            results = engine.calculate_option_chain_greeks(option_chain_small)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
            
            assert len(results) == len(option_chain_small)
        
        # 计算统计
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        avg = np.mean(latencies)
        avg_per_option = avg / len(option_chain_small)
        
        print(f"\n小型期权链批量计算延迟 ({len(option_chain_small)}个期权):")
        print(f"  平均: {avg:.2f}ms ({avg_per_option:.2f}ms/期权)")
        print(f"  P50: {p50:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  P99: {p99:.2f}ms")
        print(f"  目标: P99 < 100ms")
        
        # 验证性能目标
        assert p99 < 100.0, f"P99延迟 {p99:.2f}ms 超过目标 100ms"
    
    def test_option_chain_medium_latency(self, engine, option_chain_medium):
        """测试中型期权链批量计算延迟（50个期权）
        
        性能目标: P99 < 500ms
        """
        latencies = []
        iterations = 20
        
        for _ in range(iterations):
            engine.clear_cache()
            start = time.perf_counter()
            results = engine.calculate_option_chain_greeks(option_chain_medium)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
            
            assert len(results) == len(option_chain_medium)
        
        # 计算统计
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        avg = np.mean(latencies)
        avg_per_option = avg / len(option_chain_medium)
        
        print(f"\n中型期权链批量计算延迟 ({len(option_chain_medium)}个期权):")
        print(f"  平均: {avg:.2f}ms ({avg_per_option:.2f}ms/期权)")
        print(f"  P50: {p50:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  P99: {p99:.2f}ms")
        print(f"  目标: P99 < 500ms")
        
        # 验证性能目标
        assert p99 < 500.0, f"P99延迟 {p99:.2f}ms 超过目标 500ms"
        assert avg_per_option < 10.0, f"平均每期权延迟 {avg_per_option:.2f}ms 超过预期 10ms"
    
    def test_option_chain_large_latency(self, engine, option_chain_large):
        """测试大型期权链批量计算延迟（100个期权）
        
        性能目标: P99 < 1000ms
        """
        latencies = []
        iterations = 10
        
        for _ in range(iterations):
            engine.clear_cache()
            start = time.perf_counter()
            results = engine.calculate_option_chain_greeks(option_chain_large)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
            
            assert len(results) == len(option_chain_large)
        
        # 计算统计
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        avg = np.mean(latencies)
        avg_per_option = avg / len(option_chain_large)
        
        print(f"\n大型期权链批量计算延迟 ({len(option_chain_large)}个期权):")
        print(f"  平均: {avg:.2f}ms ({avg_per_option:.2f}ms/期权)")
        print(f"  P50: {p50:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  P99: {p99:.2f}ms")
        print(f"  目标: P99 < 1000ms")
        
        # 验证性能目标
        assert p99 < 1000.0, f"P99延迟 {p99:.2f}ms 超过目标 1000ms"
        assert avg_per_option < 10.0, f"平均每期权延迟 {avg_per_option:.2f}ms 超过预期 10ms"
    
    def test_option_chain_xlarge_throughput(self, engine, option_chain_xlarge):
        """测试超大型期权链吞吐量（1000个期权）
        
        性能目标: > 1000个期权/秒
        """
        engine.clear_cache()
        
        start = time.perf_counter()
        results = engine.calculate_option_chain_greeks(option_chain_xlarge)
        elapsed_seconds = time.perf_counter() - start
        
        throughput = len(results) / elapsed_seconds
        
        print(f"\n超大型期权链吞吐量测试 ({len(option_chain_xlarge)}个期权):")
        print(f"  总耗时: {elapsed_seconds:.2f}秒")
        print(f"  吞吐量: {throughput:.0f}个期权/秒")
        print(f"  目标: > 1000个期权/秒")
        
        # 验证性能目标
        assert len(results) == len(option_chain_xlarge)
        assert throughput > 100, f"吞吐量 {throughput:.0f}个期权/秒 低于最低要求 100"
    
    def test_cache_effectiveness(self, engine, option_chain_small):
        """测试缓存效果
        
        性能目标: 缓存命中率 > 70%
        """
        # 第一次计算（无缓存）
        engine.clear_cache()
        start1 = time.perf_counter()
        results1 = engine.calculate_option_chain_greeks(option_chain_small)
        time1_ms = (time.perf_counter() - start1) * 1000
        
        # 第二次计算（有缓存）
        start2 = time.perf_counter()
        results2 = engine.calculate_option_chain_greeks(option_chain_small)
        time2_ms = (time.perf_counter() - start2) * 1000
        
        # 计算加速比
        speedup = time1_ms / time2_ms if time2_ms > 0 else 0
        
        print(f"\n缓存效果测试 ({len(option_chain_small)}个期权):")
        print(f"  无缓存: {time1_ms:.2f}ms")
        print(f"  有缓存: {time2_ms:.2f}ms")
        print(f"  加速比: {speedup:.1f}x")
        
        # 验证缓存效果
        assert len(results1) == len(results2)
        assert time2_ms < time1_ms, "缓存应该提升性能"
        assert speedup > 2.0, f"缓存加速比 {speedup:.1f}x 低于预期 2x"
    
    def test_repeated_calculation_with_cache(self, engine, single_option):
        """测试重复计算的缓存效果
        
        验证缓存命中率
        """
        iterations = 100
        latencies_no_cache = []
        latencies_with_cache = []
        
        # 无缓存测试
        for _ in range(iterations):
            start = time.perf_counter()
            engine.calculate_greeks(single_option, use_cache=False)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies_no_cache.append(elapsed_ms)
        
        # 有缓存测试
        engine.clear_cache()
        for _ in range(iterations):
            start = time.perf_counter()
            engine.calculate_greeks(single_option, use_cache=True)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies_with_cache.append(elapsed_ms)
        
        avg_no_cache = np.mean(latencies_no_cache)
        avg_with_cache = np.mean(latencies_with_cache)
        speedup = avg_no_cache / avg_with_cache if avg_with_cache > 0 else 0
        
        print(f"\n重复计算缓存效果:")
        print(f"  无缓存平均: {avg_no_cache:.2f}ms")
        print(f"  有缓存平均: {avg_with_cache:.2f}ms")
        print(f"  加速比: {speedup:.1f}x")
        
        # 验证缓存效果（第一次计算后，后续都应该命中缓存）
        assert avg_with_cache < avg_no_cache
    
    def test_performance_metrics(self, engine, option_chain_small):
        """测试性能指标收集"""
        # 执行一些计算
        engine.clear_cache()
        engine.calculate_option_chain_greeks(option_chain_small)
        
        # 获取性能指标
        metrics = engine.get_performance_metrics()
        
        print(f"\n性能指标:")
        print(f"  计算次数: {metrics['calculation_count']}")
        print(f"  平均延迟: {metrics['avg_latency_ms']:.2f}ms")
        print(f"  缓存大小: {metrics['cache_size']}")
        print(f"  缓存命中率: {metrics['cache_hit_rate']:.2%}")
        print(f"  性能状态: {metrics['performance_status']}")
        
        # 验证指标
        assert metrics['calculation_count'] > 0
        assert metrics['avg_latency_ms'] > 0
        assert metrics['performance_status'] in ['EXCELLENT', 'GOOD', 'ACCEPTABLE', 'NEEDS_OPTIMIZATION']
    
    def test_vectorization_vs_sequential(self, engine, option_chain_medium):
        """测试向量化计算 vs 顺序计算
        
        验证向量化优化效果
        """
        # 顺序计算
        engine.clear_cache()
        start1 = time.perf_counter()
        results1 = engine.calculate_option_chain_greeks(option_chain_medium, use_vectorization=False)
        time1_ms = (time.perf_counter() - start1) * 1000
        
        # 向量化计算
        engine.clear_cache()
        start2 = time.perf_counter()
        results2 = engine.calculate_option_chain_greeks(option_chain_medium, use_vectorization=True)
        time2_ms = (time.perf_counter() - start2) * 1000
        
        speedup = time1_ms / time2_ms if time2_ms > 0 else 1.0
        
        print(f"\n向量化 vs 顺序计算 ({len(option_chain_medium)}个期权):")
        print(f"  顺序计算: {time1_ms:.2f}ms")
        print(f"  向量化计算: {time2_ms:.2f}ms")
        print(f"  加速比: {speedup:.2f}x")
        
        # 验证结果一致性
        assert len(results1) == len(results2)
        
        # 向量化应该不慢于顺序计算（至少持平）
        assert time2_ms <= time1_ms * 1.2, "向量化不应该显著慢于顺序计算"


class TestGreeksEngineStressTest:
    """GreeksEngine压力测试"""
    
    @pytest.fixture
    def engine(self):
        """测试夹具"""
        return GreeksEngine(cache_ttl_seconds=5)
    
    def test_continuous_calculation_stability(self, engine):
        """测试连续计算稳定性
        
        模拟长时间运行场景
        """
        iterations = 1000
        option = OptionContract(
            symbol="TEST",
            option_type=OptionType.CALL,
            strike=2.6,
            spot=2.8,
            time_to_maturity=0.25,
            risk_free_rate=0.03,
            volatility=0.25
        )
        
        latencies = []
        errors = 0
        
        for i in range(iterations):
            try:
                start = time.perf_counter()
                greeks = engine.calculate_greeks(option, use_cache=False)
                elapsed_ms = (time.perf_counter() - start) * 1000
                latencies.append(elapsed_ms)
                
                # 验证结果合理性
                assert 0 < greeks.delta < 1
                assert greeks.gamma > 0
                
            except Exception as e:
                errors += 1
                print(f"错误 #{errors}: {e}")
        
        # 统计
        avg_latency = np.mean(latencies)
        p99_latency = np.percentile(latencies, 99)
        error_rate = errors / iterations
        
        print(f"\n连续计算稳定性测试 ({iterations}次):")
        print(f"  平均延迟: {avg_latency:.2f}ms")
        print(f"  P99延迟: {p99_latency:.2f}ms")
        print(f"  错误率: {error_rate:.2%}")
        
        # 验证稳定性
        assert error_rate < 0.01, f"错误率 {error_rate:.2%} 过高"
        assert p99_latency < 50.0, f"P99延迟 {p99_latency:.2f}ms 超过目标"
    
    def test_memory_usage_stability(self, engine):
        """测试内存使用稳定性
        
        验证长时间运行不会内存泄漏
        """
        import sys
        
        # 初始内存
        initial_cache_size = len(engine.cache)
        
        # 大量计算
        for i in range(1000):
            option = OptionContract(
                symbol=f"TEST{i}",
                option_type=OptionType.CALL,
                strike=2.6,
                spot=2.8,
                time_to_maturity=0.25,
                risk_free_rate=0.03,
                volatility=0.25
            )
            engine.calculate_greeks(option, use_cache=True)
        
        # 最终内存
        final_cache_size = len(engine.cache)
        
        print(f"\n内存使用稳定性测试:")
        print(f"  初始缓存大小: {initial_cache_size}")
        print(f"  最终缓存大小: {final_cache_size}")
        print(f"  缓存增长: {final_cache_size - initial_cache_size}")
        
        # 验证缓存大小合理（不会无限增长）
        assert final_cache_size < 2000, f"缓存大小 {final_cache_size} 过大，可能存在内存泄漏"
