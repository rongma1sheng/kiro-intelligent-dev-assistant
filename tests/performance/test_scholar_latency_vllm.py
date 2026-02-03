"""
Scholar延迟性能测试（vLLM优化版）- Task 16.3

白皮书依据: 第二章 2.3 Scholar (研究系统 - 因子挖掘)
性能目标: 因子研究延迟 < 1s (P95) - vLLM优化目标

测试内容:
1. 因子研究延迟测试（P50, P90, P95）
2. vLLM批处理优化效果测试
3. 与传统方法的性能对比
4. 缓存命中率对延迟的影响
5. 并发请求下的延迟表现
6. IC/IR计算性能测试
"""

import asyncio
import time
import pytest
import pytest_asyncio
import numpy as np
from typing import List, Dict, Any
from loguru import logger

from src.brain.scholar_engine_v2 import ScholarEngineV2
from src.brain.llm_gateway import LLMGateway
from src.brain.hallucination_filter import HallucinationFilter


class TestScholarLatencyVLLM:
    """Scholar延迟性能测试（vLLM优化版）
    
    白皮书依据: 第二章 2.3 Scholar引擎
    性能目标: P95 < 1s (vLLM优化后，比原目标2s提升50%)
    """
    
    @pytest_asyncio.fixture
    async def scholar_engine(self):
        """创建Scholar引擎实例"""
        llm_gateway = LLMGateway()
        hallucination_filter = HallucinationFilter()
        
        engine = ScholarEngineV2(
            llm_gateway=llm_gateway,
            hallucination_filter=hallucination_filter,
            cache_ttl=3600.0  # 1小时缓存
        )
        
        await engine.initialize()
        
        yield engine
        
        # 清理资源
        pass
    
    @pytest.fixture(scope="function")
    def event_loop(self):
        """创建事件循环"""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_factor_research_latency_p95(self, scholar_engine):
        """测试因子研究延迟 - P95 < 1s
        
        白皮书依据: 第二章 2.3 Scholar性能要求
        性能目标: P95 < 1s (vLLM优化目标)
        """
        logger.info("[Test] Starting P95 latency test for Scholar...")
        
        # 预热
        for _ in range(3):
            await scholar_engine.research_factor('momentum_warmup')
        
        # 清空缓存
        if hasattr(scholar_engine, 'research_cache'):
            scholar_engine.research_cache.clear()
        
        # 执行200次因子研究，收集延迟数据
        latencies = []
        test_count = 200
        
        for i in range(test_count):
            factor_expression = f'momentum_{i % 20}'  # 20个不同的因子
            
            start_time = time.perf_counter()
            result = await scholar_engine.research_factor(factor_expression)
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
            assert result is not None
        
        # 计算百分位数
        latencies_array = np.array(latencies)
        p50 = np.percentile(latencies_array, 50)
        p90 = np.percentile(latencies_array, 90)
        p95 = np.percentile(latencies_array, 95)
        p99 = np.percentile(latencies_array, 99)
        mean = np.mean(latencies_array)
        std = np.std(latencies_array)
        
        logger.info(
            f"[Test] Scholar latency statistics (ms):\n"
            f"  Mean: {mean:.2f}\n"
            f"  Std:  {std:.2f}\n"
            f"  P50:  {p50:.2f}\n"
            f"  P90:  {p90:.2f}\n"
            f"  P95:  {p95:.2f}\n"
            f"  P99:  {p99:.2f}"
        )
        
        # 断言：P95 < 1000ms (vLLM优化目标)
        assert p95 < 1000.0, (
            f"P95 latency {p95:.2f}ms exceeds target 1000ms. "
            f"vLLM optimization may not be working correctly."
        )
        
        # 断言：P90 < 900ms
        assert p90 < 900.0, f"P90 latency {p90:.2f}ms exceeds target 900ms"
        
        # 断言：P50 < 700ms
        assert p50 < 700.0, f"P50 latency {p50:.2f}ms exceeds target 700ms"
        
        logger.info("[Test] ✅ P95 latency test passed for Scholar")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_vllm_batch_processing_optimization(self, scholar_engine):
        """测试vLLM批处理优化效果
        
        白皮书依据: 第八章 8.3 自适应批处理调度
        
        验证批处理能够提升吞吐量而不显著增加延迟
        """
        logger.info("[Test] Starting vLLM batch processing test for Scholar...")
        
        # 清空缓存
        if hasattr(scholar_engine, 'research_cache'):
            scholar_engine.research_cache.clear()
        
        # 测试1: 单个请求的延迟（基准）
        single_latencies = []
        for i in range(30):
            factor_expression = f'single_{i}'
            
            start_time = time.perf_counter()
            await scholar_engine.research_factor(factor_expression)
            end_time = time.perf_counter()
            
            single_latencies.append((end_time - start_time) * 1000)
        
        single_p95 = np.percentile(single_latencies, 95)
        
        # 测试2: 批量并发请求的延迟
        batch_size = 3
        batch_count = 10
        batch_latencies = []
        
        for batch_idx in range(batch_count):
            tasks = []
            start_time = time.perf_counter()
            
            for i in range(batch_size):
                factor_expression = f'batch_{batch_idx}_{i}'
                tasks.append(scholar_engine.research_factor(factor_expression))
            
            await asyncio.gather(*tasks)
            end_time = time.perf_counter()
            
            # 批处理的平均延迟
            avg_latency = ((end_time - start_time) / batch_size) * 1000
            batch_latencies.append(avg_latency)
        
        batch_p95 = np.percentile(batch_latencies, 95)
        
        logger.info(
            f"[Test] Batch processing results:\n"
            f"  Single request P95: {single_p95:.2f}ms\n"
            f"  Batch request P95:  {batch_p95:.2f}ms\n"
            f"  Overhead:           {batch_p95 - single_p95:.2f}ms"
        )
        
        # 断言：批处理开销 < 100ms
        overhead = batch_p95 - single_p95
        assert overhead < 100.0, (
            f"Batch processing overhead {overhead:.2f}ms too high. "
            f"vLLM batch optimization may not be effective."
        )
        
        logger.info("[Test] ✅ vLLM batch processing test passed for Scholar")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_latency_with_cache_hit(self, scholar_engine):
        """测试缓存命中时的延迟
        
        白皮书依据: 第七章 7.4 缓存策略
        
        缓存命中应该显著降低延迟（< 10ms）
        """
        logger.info("[Test] Starting cache hit latency test for Scholar...")
        
        if not hasattr(scholar_engine, 'research_cache'):
            pytest.skip("Cache not available")
        
        # 清空缓存
        scholar_engine.research_cache.clear()
        
        factor_expression = 'cache_test_momentum'
        
        # 第一次请求：缓存未命中
        start_time = time.perf_counter()
        await scholar_engine.research_factor(factor_expression)
        first_latency = (time.perf_counter() - start_time) * 1000
        
        # 第二次请求：缓存命中
        cache_hit_latencies = []
        for _ in range(30):
            start_time = time.perf_counter()
            await scholar_engine.research_factor(factor_expression)
            cache_hit_latency = (time.perf_counter() - start_time) * 1000
            cache_hit_latencies.append(cache_hit_latency)
        
        cache_hit_p95 = np.percentile(cache_hit_latencies, 95)
        cache_hit_mean = np.mean(cache_hit_latencies)
        
        logger.info(
            f"[Test] Cache latency comparison:\n"
            f"  First request (miss): {first_latency:.2f}ms\n"
            f"  Cache hit mean:       {cache_hit_mean:.2f}ms\n"
            f"  Cache hit P95:        {cache_hit_p95:.2f}ms\n"
            f"  Speedup:              {first_latency / cache_hit_mean:.1f}x"
        )
        
        # 断言：缓存命中延迟 < 10ms
        assert cache_hit_p95 < 10.0, (
            f"Cache hit P95 {cache_hit_p95:.2f}ms exceeds target 10ms"
        )
        
        # 断言：缓存命中比未命中快至少20倍
        speedup = first_latency / cache_hit_mean
        assert speedup >= 20.0, (
            f"Cache speedup {speedup:.1f}x is less than expected 20x"
        )
        
        logger.info("[Test] ✅ Cache hit latency test passed for Scholar")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_request_latency(self, scholar_engine):
        """测试并发请求下的延迟表现
        
        白皮书依据: 第七章 7.7 并发决策处理
        
        验证在高并发下延迟不会显著增加
        """
        logger.info("[Test] Starting concurrent request latency test for Scholar...")
        
        # 清空缓存
        if hasattr(scholar_engine, 'research_cache'):
            scholar_engine.research_cache.clear()
        
        # 测试不同并发级别
        concurrency_levels = [1, 2, 3, 5]
        results = {}
        
        for concurrency in concurrency_levels:
            latencies = []
            
            # 执行3轮测试
            for round_idx in range(3):
                tasks = []
                
                for i in range(concurrency):
                    factor_expression = f'concurrent_{round_idx}_{i}'
                    
                    async def measure_latency(fe):
                        start = time.perf_counter()
                        await scholar_engine.research_factor(fe)
                        return (time.perf_counter() - start) * 1000
                    
                    tasks.append(measure_latency(factor_expression))
                
                round_latencies = await asyncio.gather(*tasks)
                latencies.extend(round_latencies)
            
            p95 = np.percentile(latencies, 95)
            mean = np.mean(latencies)
            
            results[concurrency] = {'p95': p95, 'mean': mean}
            
            logger.info(
                f"[Test] Concurrency {concurrency:2d}: "
                f"mean={mean:.2f}ms, P95={p95:.2f}ms"
            )
        
        # 断言：即使在5并发下，P95仍 < 1500ms
        assert results[5]['p95'] < 1500.0, (
            f"P95 latency {results[5]['p95']:.2f}ms at concurrency 5 "
            f"exceeds target 1500ms"
        )
        
        # 断言：延迟增长是次线性的（5并发的P95 < 1并发的P95 * 2）
        latency_growth = results[5]['p95'] / results[1]['p95']
        assert latency_growth < 2.0, (
            f"Latency growth {latency_growth:.2f}x is too high. "
            f"Should be sub-linear."
        )
        
        logger.info("[Test] ✅ Concurrent request latency test passed for Scholar")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.comparison
    async def test_vllm_vs_traditional_performance(self, scholar_engine):
        """对比vLLM优化与传统方法的性能提升
        
        白皮书依据: 第八章 8.8 vLLM性能优化目标
        
        验证vLLM优化带来的性能提升（目标：50%+）
        """
        logger.info("[Test] Starting vLLM vs traditional performance comparison for Scholar...")
        
        # 清空缓存
        if hasattr(scholar_engine, 'research_cache'):
            scholar_engine.research_cache.clear()
        
        # 模拟传统方法的延迟（基于历史数据）
        # 传统方法的P95约为2000ms
        traditional_p95 = 2000.0
        
        # 测试vLLM优化后的延迟
        vllm_latencies = []
        for i in range(200):
            factor_expression = f'vllm_{i % 20}'
            
            start_time = time.perf_counter()
            await scholar_engine.research_factor(factor_expression)
            latency = (time.perf_counter() - start_time) * 1000
            vllm_latencies.append(latency)
        
        vllm_p95 = np.percentile(vllm_latencies, 95)
        vllm_mean = np.mean(vllm_latencies)
        
        # 计算性能提升
        improvement = ((traditional_p95 - vllm_p95) / traditional_p95) * 100
        speedup = traditional_p95 / vllm_p95
        
        logger.info(
            f"[Test] Performance comparison:\n"
            f"  Traditional P95:  {traditional_p95:.2f}ms\n"
            f"  vLLM P95:         {vllm_p95:.2f}ms\n"
            f"  vLLM mean:        {vllm_mean:.2f}ms\n"
            f"  Improvement:      {improvement:.1f}%\n"
            f"  Speedup:          {speedup:.2f}x"
        )
        
        # 断言：性能提升 >= 50%
        assert improvement >= 50.0, (
            f"Performance improvement {improvement:.1f}% is less than "
            f"target 50%. vLLM optimization may not be effective."
        )
        
        # 断言：vLLM P95 < 1000ms
        assert vllm_p95 < 1000.0, (
            f"vLLM P95 {vllm_p95:.2f}ms exceeds target 1000ms"
        )
        
        logger.info("[Test] ✅ vLLM vs traditional performance test passed for Scholar")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_ic_ir_calculation_latency(self, scholar_engine):
        """测试IC/IR计算的延迟
        
        白皮书依据: 第二章 2.3 Scholar IC/IR计算
        
        验证IC/IR计算不会显著增加延迟
        """
        logger.info("[Test] Starting IC/IR calculation latency test...")
        
        # 清空缓存
        if hasattr(scholar_engine, 'research_cache'):
            scholar_engine.research_cache.clear()
        
        # 准备测试数据
        factor_values = np.random.randn(252, 100)  # 252天，100只股票
        returns = np.random.randn(252, 100)
        
        latencies = []
        
        for i in range(100):
            factor_data = {
                'factor_name': f'ic_test_{i}',
                'factor_values': factor_values[:, i].tolist(),
                'returns': returns[:, i].tolist()
            }
            
            start_time = time.perf_counter()
            result = await scholar_engine.calculate_ic_ir(factor_data)
            latency = (time.perf_counter() - start_time) * 1000
            latencies.append(latency)
            
            assert result is not None
        
        p95 = np.percentile(latencies, 95)
        mean = np.mean(latencies)
        
        logger.info(
            f"[Test] IC/IR calculation latency:\n"
            f"  Mean: {mean:.2f}ms\n"
            f"  P95:  {p95:.2f}ms"
        )
        
        # 断言：IC/IR计算P95 < 50ms
        assert p95 < 50.0, (
            f"IC/IR calculation P95 {p95:.2f}ms exceeds target 50ms"
        )
        
        logger.info("[Test] ✅ IC/IR calculation latency test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
