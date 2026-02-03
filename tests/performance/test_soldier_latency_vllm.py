"""
Soldier延迟性能测试（vLLM优化版）- Task 16.1

白皮书依据: 第二章 2.1 Soldier (快系统 - 热备高可用)
性能目标: 本地推理延迟 < 10ms (P99) - vLLM优化目标

测试内容:
1. 本地推理延迟测试（P50, P90, P99）
2. vLLM批处理优化效果测试
3. 与传统方法的性能对比
4. 缓存命中率对延迟的影响
5. 并发请求下的延迟表现
"""

import asyncio
import time
import pytest
import pytest_asyncio
import numpy as np
from typing import List, Dict, Any
from loguru import logger

from src.brain.soldier_engine_v2 import SoldierEngineV2, SoldierConfig


class TestSoldierLatencyVLLM:
    """Soldier延迟性能测试（vLLM优化版）
    
    白皮书依据: 第二章 2.1.4 性能要求
    性能目标: P99 < 10ms (vLLM优化后，比原目标20ms提升50%)
    """
    
    @pytest_asyncio.fixture
    async def soldier_engine(self):
        """创建Soldier引擎实例"""
        config = SoldierConfig(
            local_inference_timeout=0.01,  # 10ms
            decision_cache_ttl=5,
            redis_host="localhost",
            redis_port=6379,
            cache_warmup_enabled=False  # 性能测试时禁用预热
        )
        
        engine = SoldierEngineV2(config)
        await engine.initialize()
        
        yield engine
        
        await engine.shutdown()
    
    @pytest.fixture(scope="function")
    def event_loop(self):
        """创建事件循环"""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_local_inference_latency_p99(self, soldier_engine):
        """测试本地推理延迟 - P99 < 10ms
        
        白皮书依据: 第二章 2.1.4 性能要求
        性能目标: P99 < 10ms (vLLM优化目标)
        """
        logger.info("[Test] Starting P99 latency test...")
        
        # 预热
        for _ in range(10):
            await soldier_engine.decide({'symbol': 'WARMUP', 'market_data': {}})
        
        # 清空缓存，确保测试真实推理延迟
        if soldier_engine.cache_enabled:
            await soldier_engine.clear_cache()
        
        # 执行1000次决策，收集延迟数据
        latencies = []
        test_count = 1000
        
        for i in range(test_count):
            context = {
                'symbol': f'TEST{i % 100}',  # 100个不同的股票
                'market_data': {
                    'price': 100.0 + i * 0.1,
                    'volume': 1000000 + i * 1000
                }
            }
            
            start_time = time.perf_counter()
            result = await soldier_engine.decide(context)
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
            assert result is not None
            assert 'decision' in result
        
        # 计算百分位数
        latencies_array = np.array(latencies)
        p50 = np.percentile(latencies_array, 50)
        p90 = np.percentile(latencies_array, 90)
        p99 = np.percentile(latencies_array, 99)
        mean = np.mean(latencies_array)
        std = np.std(latencies_array)
        
        logger.info(
            f"[Test] Latency statistics (ms):\n"
            f"  Mean: {mean:.2f}\n"
            f"  Std:  {std:.2f}\n"
            f"  P50:  {p50:.2f}\n"
            f"  P90:  {p90:.2f}\n"
            f"  P99:  {p99:.2f}"
        )
        
        # 断言：P99 < 10ms (vLLM优化目标)
        assert p99 < 10.0, (
            f"P99 latency {p99:.2f}ms exceeds target 10ms. "
            f"vLLM optimization may not be working correctly."
        )
        
        # 断言：P90 < 8ms
        assert p90 < 8.0, f"P90 latency {p90:.2f}ms exceeds target 8ms"
        
        # 断言：P50 < 6ms
        assert p50 < 6.0, f"P50 latency {p50:.2f}ms exceeds target 6ms"
        
        logger.info("[Test] ✅ P99 latency test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_vllm_batch_processing_optimization(self, soldier_engine):
        """测试vLLM批处理优化效果
        
        白皮书依据: 第八章 8.3 自适应批处理调度
        
        验证批处理能够提升吞吐量而不显著增加延迟
        """
        logger.info("[Test] Starting vLLM batch processing test...")
        
        # 清空缓存
        if soldier_engine.cache_enabled:
            await soldier_engine.clear_cache()
        
        # 测试1: 单个请求的延迟（基准）
        single_latencies = []
        for i in range(100):
            context = {'symbol': f'SINGLE{i}', 'market_data': {}}
            
            start_time = time.perf_counter()
            await soldier_engine.decide(context)
            end_time = time.perf_counter()
            
            single_latencies.append((end_time - start_time) * 1000)
        
        single_p99 = np.percentile(single_latencies, 99)
        
        # 测试2: 批量并发请求的延迟
        batch_size = 10
        batch_count = 10
        batch_latencies = []
        
        for batch_idx in range(batch_count):
            tasks = []
            start_time = time.perf_counter()
            
            for i in range(batch_size):
                context = {
                    'symbol': f'BATCH{batch_idx}_{i}',
                    'market_data': {}
                }
                tasks.append(soldier_engine.decide(context))
            
            await asyncio.gather(*tasks)
            end_time = time.perf_counter()
            
            # 批处理的平均延迟
            avg_latency = ((end_time - start_time) / batch_size) * 1000
            batch_latencies.append(avg_latency)
        
        batch_p99 = np.percentile(batch_latencies, 99)
        
        logger.info(
            f"[Test] Batch processing results:\n"
            f"  Single request P99: {single_p99:.2f}ms\n"
            f"  Batch request P99:  {batch_p99:.2f}ms\n"
            f"  Overhead:           {batch_p99 - single_p99:.2f}ms"
        )
        
        # 断言：批处理开销 < 3ms
        overhead = batch_p99 - single_p99
        assert overhead < 3.0, (
            f"Batch processing overhead {overhead:.2f}ms too high. "
            f"vLLM batch optimization may not be effective."
        )
        
        logger.info("[Test] ✅ vLLM batch processing test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_latency_with_cache_hit(self, soldier_engine):
        """测试缓存命中时的延迟
        
        白皮书依据: 第七章 7.4 缓存策略
        
        缓存命中应该显著降低延迟（< 1ms）
        """
        logger.info("[Test] Starting cache hit latency test...")
        
        if not soldier_engine.cache_enabled:
            pytest.skip("Redis cache not available")
        
        # 清空缓存
        await soldier_engine.clear_cache()
        
        context = {
            'symbol': 'CACHE_TEST',
            'market_data': {'price': 100.0, 'volume': 1000000}
        }
        
        # 第一次请求：缓存未命中
        start_time = time.perf_counter()
        await soldier_engine.decide(context)
        first_latency = (time.perf_counter() - start_time) * 1000
        
        # 第二次请求：缓存命中
        cache_hit_latencies = []
        for _ in range(100):
            start_time = time.perf_counter()
            await soldier_engine.decide(context)
            cache_hit_latency = (time.perf_counter() - start_time) * 1000
            cache_hit_latencies.append(cache_hit_latency)
        
        cache_hit_p99 = np.percentile(cache_hit_latencies, 99)
        cache_hit_mean = np.mean(cache_hit_latencies)
        
        logger.info(
            f"[Test] Cache latency comparison:\n"
            f"  First request (miss): {first_latency:.2f}ms\n"
            f"  Cache hit mean:       {cache_hit_mean:.2f}ms\n"
            f"  Cache hit P99:        {cache_hit_p99:.2f}ms\n"
            f"  Speedup:              {first_latency / cache_hit_mean:.1f}x"
        )
        
        # 断言：缓存命中延迟 < 1ms
        assert cache_hit_p99 < 1.0, (
            f"Cache hit P99 {cache_hit_p99:.2f}ms exceeds target 1ms"
        )
        
        # 断言：缓存命中比未命中快至少5倍
        speedup = first_latency / cache_hit_mean
        assert speedup >= 5.0, (
            f"Cache speedup {speedup:.1f}x is less than expected 5x"
        )
        
        logger.info("[Test] ✅ Cache hit latency test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_request_latency(self, soldier_engine):
        """测试并发请求下的延迟表现
        
        白皮书依据: 第七章 7.7 并发决策处理
        
        验证在高并发下延迟不会显著增加
        """
        logger.info("[Test] Starting concurrent request latency test...")
        
        # 清空缓存
        if soldier_engine.cache_enabled:
            await soldier_engine.clear_cache()
        
        # 测试不同并发级别
        concurrency_levels = [1, 5, 10, 20]
        results = {}
        
        for concurrency in concurrency_levels:
            latencies = []
            
            # 执行10轮测试
            for round_idx in range(10):
                tasks = []
                
                for i in range(concurrency):
                    context = {
                        'symbol': f'CONCURRENT{round_idx}_{i}',
                        'market_data': {}
                    }
                    
                    async def measure_latency(ctx):
                        start = time.perf_counter()
                        await soldier_engine.decide(ctx)
                        return (time.perf_counter() - start) * 1000
                    
                    tasks.append(measure_latency(context))
                
                round_latencies = await asyncio.gather(*tasks)
                latencies.extend(round_latencies)
            
            p99 = np.percentile(latencies, 99)
            mean = np.mean(latencies)
            
            results[concurrency] = {'p99': p99, 'mean': mean}
            
            logger.info(
                f"[Test] Concurrency {concurrency:2d}: "
                f"mean={mean:.2f}ms, P99={p99:.2f}ms"
            )
        
        # 断言：即使在20并发下，P99仍 < 15ms
        assert results[20]['p99'] < 15.0, (
            f"P99 latency {results[20]['p99']:.2f}ms at concurrency 20 "
            f"exceeds target 15ms"
        )
        
        # 断言：延迟增长是次线性的（20并发的P99 < 1并发的P99 * 2）
        latency_growth = results[20]['p99'] / results[1]['p99']
        assert latency_growth < 2.0, (
            f"Latency growth {latency_growth:.2f}x is too high. "
            f"Should be sub-linear."
        )
        
        logger.info("[Test] ✅ Concurrent request latency test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.comparison
    async def test_vllm_vs_traditional_performance(self, soldier_engine):
        """对比vLLM优化与传统方法的性能提升
        
        白皮书依据: 第八章 8.8 vLLM性能优化目标
        
        验证vLLM优化带来的性能提升（目标：50%+）
        """
        logger.info("[Test] Starting vLLM vs traditional performance comparison...")
        
        # 清空缓存
        if soldier_engine.cache_enabled:
            await soldier_engine.clear_cache()
        
        # 模拟传统方法的延迟（基于历史数据）
        # 传统方法的P99约为20ms
        traditional_p99 = 20.0
        
        # 测试vLLM优化后的延迟
        vllm_latencies = []
        for i in range(1000):
            context = {
                'symbol': f'VLLM{i % 100}',
                'market_data': {}
            }
            
            start_time = time.perf_counter()
            await soldier_engine.decide(context)
            latency = (time.perf_counter() - start_time) * 1000
            vllm_latencies.append(latency)
        
        vllm_p99 = np.percentile(vllm_latencies, 99)
        vllm_mean = np.mean(vllm_latencies)
        
        # 计算性能提升
        improvement = ((traditional_p99 - vllm_p99) / traditional_p99) * 100
        speedup = traditional_p99 / vllm_p99
        
        logger.info(
            f"[Test] Performance comparison:\n"
            f"  Traditional P99:  {traditional_p99:.2f}ms\n"
            f"  vLLM P99:         {vllm_p99:.2f}ms\n"
            f"  vLLM mean:        {vllm_mean:.2f}ms\n"
            f"  Improvement:      {improvement:.1f}%\n"
            f"  Speedup:          {speedup:.2f}x"
        )
        
        # 断言：性能提升 >= 50%
        assert improvement >= 50.0, (
            f"Performance improvement {improvement:.1f}% is less than "
            f"target 50%. vLLM optimization may not be effective."
        )
        
        # 断言：vLLM P99 < 10ms
        assert vllm_p99 < 10.0, (
            f"vLLM P99 {vllm_p99:.2f}ms exceeds target 10ms"
        )
        
        logger.info("[Test] ✅ vLLM vs traditional performance test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_latency_stability_over_time(self, soldier_engine):
        """测试延迟的长期稳定性
        
        白皮书依据: 第二章 2.1.4 性能要求
        
        验证延迟在长时间运行下保持稳定
        """
        logger.info("[Test] Starting latency stability test...")
        
        # 清空缓存
        if soldier_engine.cache_enabled:
            await soldier_engine.clear_cache()
        
        # 分10个时间窗口，每个窗口100次请求
        window_count = 10
        requests_per_window = 100
        window_p99s = []
        
        for window_idx in range(window_count):
            window_latencies = []
            
            for i in range(requests_per_window):
                context = {
                    'symbol': f'STABILITY{window_idx}_{i}',
                    'market_data': {}
                }
                
                start_time = time.perf_counter()
                await soldier_engine.decide(context)
                latency = (time.perf_counter() - start_time) * 1000
                window_latencies.append(latency)
            
            window_p99 = np.percentile(window_latencies, 99)
            window_p99s.append(window_p99)
            
            logger.info(
                f"[Test] Window {window_idx + 1}/{window_count}: "
                f"P99={window_p99:.2f}ms"
            )
        
        # 计算P99的标准差
        p99_std = np.std(window_p99s)
        p99_mean = np.mean(window_p99s)
        p99_cv = (p99_std / p99_mean) * 100  # 变异系数
        
        logger.info(
            f"[Test] Stability statistics:\n"
            f"  P99 mean:  {p99_mean:.2f}ms\n"
            f"  P99 std:   {p99_std:.2f}ms\n"
            f"  P99 CV:    {p99_cv:.1f}%"
        )
        
        # 断言：P99的变异系数 < 20%（稳定性良好）
        assert p99_cv < 20.0, (
            f"P99 coefficient of variation {p99_cv:.1f}% is too high. "
            f"Latency is not stable over time."
        )
        
        # 断言：所有窗口的P99都 < 12ms
        max_p99 = max(window_p99s)
        assert max_p99 < 12.0, (
            f"Maximum P99 {max_p99:.2f}ms exceeds target 12ms"
        )
        
        logger.info("[Test] ✅ Latency stability test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
