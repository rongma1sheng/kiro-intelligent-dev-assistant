"""
Commander延迟性能测试（vLLM优化版）- Task 16.2

白皮书依据: 第二章 2.2 Commander (慢系统 - 策略分析)
性能目标: 策略分析延迟 < 200ms (P95) - vLLM优化目标

测试内容:
1. 策略分析延迟测试（P50, P90, P95）
2. vLLM批处理优化效果测试
3. 与传统方法的性能对比
4. 缓存命中率对延迟的影响
5. 并发请求下的延迟表现
6. 市场状态识别性能测试
"""

import asyncio
import time
import pytest
import pytest_asyncio
import numpy as np
from typing import List, Dict, Any
from loguru import logger

from src.brain.commander_engine_v2 import CommanderEngineV2
from src.brain.llm_gateway import LLMGateway
from src.brain.hallucination_filter import HallucinationFilter


class TestCommanderLatencyVLLM:
    """Commander延迟性能测试（vLLM优化版）
    
    白皮书依据: 第二章 2.2 Commander引擎
    性能目标: P95 < 200ms (vLLM优化后，比原目标500ms提升60%)
    """
    
    @pytest_asyncio.fixture
    async def commander_engine(self):
        """创建Commander引擎实例"""
        llm_gateway = LLMGateway()
        hallucination_filter = HallucinationFilter()
        
        engine = CommanderEngineV2(
            llm_gateway=llm_gateway,
            hallucination_filter=hallucination_filter
        )
        
        await engine.initialize()
        
        yield engine
        
        # 清理资源（Commander没有专门的shutdown方法）
        pass
    
    @pytest.fixture(scope="function")
    def event_loop(self):
        """创建事件循环"""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_strategy_analysis_latency_p95(self, commander_engine):
        """测试策略分析延迟 - P95 < 200ms
        
        白皮书依据: 第二章 2.2 Commander性能要求
        性能目标: P95 < 200ms (vLLM优化目标)
        """
        logger.info("[Test] Starting P95 latency test for Commander...")
        
        # 预热
        for _ in range(5):
            await commander_engine.analyze_strategy({
                'symbol': 'WARMUP',
                'market_data': {'price': 100.0, 'volume': 1000000}
            })
        
        # 清空缓存
        if hasattr(commander_engine, 'analysis_cache'):
            commander_engine.analysis_cache.clear()
        
        # 执行500次策略分析，收集延迟数据
        latencies = []
        test_count = 500
        
        for i in range(test_count):
            market_data = {
                'symbol': f'TEST{i % 50}',  # 50个不同的股票
                'market_data': {
                    'price': 100.0 + i * 0.5,
                    'volume': 1000000 + i * 5000,
                    'ma5': 99.0 + i * 0.4,
                    'ma20': 98.0 + i * 0.3,
                    'volatility': 0.02 + (i % 10) * 0.001
                }
            }
            
            start_time = time.perf_counter()
            result = await commander_engine.analyze_strategy(market_data)
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
            assert result is not None
            assert 'recommendation' in result or 'strategy' in result
        
        # 计算百分位数
        latencies_array = np.array(latencies)
        p50 = np.percentile(latencies_array, 50)
        p90 = np.percentile(latencies_array, 90)
        p95 = np.percentile(latencies_array, 95)
        p99 = np.percentile(latencies_array, 99)
        mean = np.mean(latencies_array)
        std = np.std(latencies_array)
        
        logger.info(
            f"[Test] Commander latency statistics (ms):\n"
            f"  Mean: {mean:.2f}\n"
            f"  Std:  {std:.2f}\n"
            f"  P50:  {p50:.2f}\n"
            f"  P90:  {p90:.2f}\n"
            f"  P95:  {p95:.2f}\n"
            f"  P99:  {p99:.2f}"
        )
        
        # 断言：P95 < 200ms (vLLM优化目标)
        assert p95 < 200.0, (
            f"P95 latency {p95:.2f}ms exceeds target 200ms. "
            f"vLLM optimization may not be working correctly."
        )
        
        # 断言：P90 < 180ms
        assert p90 < 180.0, f"P90 latency {p90:.2f}ms exceeds target 180ms"
        
        # 断言：P50 < 150ms
        assert p50 < 150.0, f"P50 latency {p50:.2f}ms exceeds target 150ms"
        
        logger.info("[Test] ✅ P95 latency test passed for Commander")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_vllm_batch_processing_optimization(self, commander_engine):
        """测试vLLM批处理优化效果
        
        白皮书依据: 第八章 8.3 自适应批处理调度
        
        验证批处理能够提升吞吐量而不显著增加延迟
        """
        logger.info("[Test] Starting vLLM batch processing test for Commander...")
        
        # 清空缓存
        if hasattr(commander_engine, 'analysis_cache'):
            commander_engine.analysis_cache.clear()
        
        # 测试1: 单个请求的延迟（基准）
        single_latencies = []
        for i in range(50):
            market_data = {
                'symbol': f'SINGLE{i}',
                'market_data': {'price': 100.0, 'volume': 1000000}
            }
            
            start_time = time.perf_counter()
            await commander_engine.analyze_strategy(market_data)
            end_time = time.perf_counter()
            
            single_latencies.append((end_time - start_time) * 1000)
        
        single_p95 = np.percentile(single_latencies, 95)
        
        # 测试2: 批量并发请求的延迟
        batch_size = 5
        batch_count = 10
        batch_latencies = []
        
        for batch_idx in range(batch_count):
            tasks = []
            start_time = time.perf_counter()
            
            for i in range(batch_size):
                market_data = {
                    'symbol': f'BATCH{batch_idx}_{i}',
                    'market_data': {'price': 100.0, 'volume': 1000000}
                }
                tasks.append(commander_engine.analyze_strategy(market_data))
            
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
        
        # 断言：批处理开销 < 30ms
        overhead = batch_p95 - single_p95
        assert overhead < 30.0, (
            f"Batch processing overhead {overhead:.2f}ms too high. "
            f"vLLM batch optimization may not be effective."
        )
        
        logger.info("[Test] ✅ vLLM batch processing test passed for Commander")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_latency_with_cache_hit(self, commander_engine):
        """测试缓存命中时的延迟
        
        白皮书依据: 第七章 7.4 缓存策略
        
        缓存命中应该显著降低延迟（< 10ms）
        """
        logger.info("[Test] Starting cache hit latency test for Commander...")
        
        if not hasattr(commander_engine, 'analysis_cache'):
            pytest.skip("Cache not available")
        
        # 清空缓存
        commander_engine.analysis_cache.clear()
        
        market_data = {
            'symbol': 'CACHE_TEST',
            'market_data': {
                'price': 100.0,
                'volume': 1000000,
                'ma5': 99.0,
                'ma20': 98.0
            }
        }
        
        # 第一次请求：缓存未命中
        start_time = time.perf_counter()
        await commander_engine.analyze_strategy(market_data)
        first_latency = (time.perf_counter() - start_time) * 1000
        
        # 第二次请求：缓存命中
        cache_hit_latencies = []
        for _ in range(50):
            start_time = time.perf_counter()
            await commander_engine.analyze_strategy(market_data)
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
        
        # 断言：缓存命中比未命中快至少10倍
        speedup = first_latency / cache_hit_mean
        assert speedup >= 10.0, (
            f"Cache speedup {speedup:.1f}x is less than expected 10x"
        )
        
        logger.info("[Test] ✅ Cache hit latency test passed for Commander")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_request_latency(self, commander_engine):
        """测试并发请求下的延迟表现
        
        白皮书依据: 第七章 7.7 并发决策处理
        
        验证在高并发下延迟不会显著增加
        """
        logger.info("[Test] Starting concurrent request latency test for Commander...")
        
        # 清空缓存
        if hasattr(commander_engine, 'analysis_cache'):
            commander_engine.analysis_cache.clear()
        
        # 测试不同并发级别
        concurrency_levels = [1, 3, 5, 10]
        results = {}
        
        for concurrency in concurrency_levels:
            latencies = []
            
            # 执行5轮测试
            for round_idx in range(5):
                tasks = []
                
                for i in range(concurrency):
                    market_data = {
                        'symbol': f'CONCURRENT{round_idx}_{i}',
                        'market_data': {'price': 100.0, 'volume': 1000000}
                    }
                    
                    async def measure_latency(md):
                        start = time.perf_counter()
                        await commander_engine.analyze_strategy(md)
                        return (time.perf_counter() - start) * 1000
                    
                    tasks.append(measure_latency(market_data))
                
                round_latencies = await asyncio.gather(*tasks)
                latencies.extend(round_latencies)
            
            p95 = np.percentile(latencies, 95)
            mean = np.mean(latencies)
            
            results[concurrency] = {'p95': p95, 'mean': mean}
            
            logger.info(
                f"[Test] Concurrency {concurrency:2d}: "
                f"mean={mean:.2f}ms, P95={p95:.2f}ms"
            )
        
        # 断言：即使在10并发下，P95仍 < 300ms
        assert results[10]['p95'] < 300.0, (
            f"P95 latency {results[10]['p95']:.2f}ms at concurrency 10 "
            f"exceeds target 300ms"
        )
        
        # 断言：延迟增长是次线性的（10并发的P95 < 1并发的P95 * 2）
        latency_growth = results[10]['p95'] / results[1]['p95']
        assert latency_growth < 2.0, (
            f"Latency growth {latency_growth:.2f}x is too high. "
            f"Should be sub-linear."
        )
        
        logger.info("[Test] ✅ Concurrent request latency test passed for Commander")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.comparison
    async def test_vllm_vs_traditional_performance(self, commander_engine):
        """对比vLLM优化与传统方法的性能提升
        
        白皮书依据: 第八章 8.8 vLLM性能优化目标
        
        验证vLLM优化带来的性能提升（目标：60%+）
        """
        logger.info("[Test] Starting vLLM vs traditional performance comparison for Commander...")
        
        # 清空缓存
        if hasattr(commander_engine, 'analysis_cache'):
            commander_engine.analysis_cache.clear()
        
        # 模拟传统方法的延迟（基于历史数据）
        # 传统方法的P95约为500ms
        traditional_p95 = 500.0
        
        # 测试vLLM优化后的延迟
        vllm_latencies = []
        for i in range(500):
            market_data = {
                'symbol': f'VLLM{i % 50}',
                'market_data': {'price': 100.0, 'volume': 1000000}
            }
            
            start_time = time.perf_counter()
            await commander_engine.analyze_strategy(market_data)
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
        
        # 断言：性能提升 >= 60%
        assert improvement >= 60.0, (
            f"Performance improvement {improvement:.1f}% is less than "
            f"target 60%. vLLM optimization may not be effective."
        )
        
        # 断言：vLLM P95 < 200ms
        assert vllm_p95 < 200.0, (
            f"vLLM P95 {vllm_p95:.2f}ms exceeds target 200ms"
        )
        
        logger.info("[Test] ✅ vLLM vs traditional performance test passed for Commander")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_market_regime_identification_latency(self, commander_engine):
        """测试市场状态识别的延迟
        
        白皮书依据: 第二章 2.2 Commander市场状态识别
        
        验证市场状态识别不会显著增加延迟
        """
        logger.info("[Test] Starting market regime identification latency test...")
        
        # 清空缓存
        if hasattr(commander_engine, 'analysis_cache'):
            commander_engine.analysis_cache.clear()
        
        # 测试不同市场状态
        market_regimes = [
            {'name': 'bull', 'price_trend': 1.05, 'volatility': 0.01},
            {'name': 'bear', 'price_trend': 0.95, 'volatility': 0.01},
            {'name': 'volatile', 'price_trend': 1.00, 'volatility': 0.05},
            {'name': 'sideways', 'price_trend': 1.00, 'volatility': 0.01}
        ]
        
        regime_latencies = {}
        
        for regime in market_regimes:
            latencies = []
            
            for i in range(100):
                market_data = {
                    'symbol': f'REGIME_{regime["name"]}_{i}',
                    'market_data': {
                        'price': 100.0 * regime['price_trend'],
                        'volume': 1000000,
                        'volatility': regime['volatility']
                    }
                }
                
                start_time = time.perf_counter()
                await commander_engine.analyze_strategy(market_data)
                latency = (time.perf_counter() - start_time) * 1000
                latencies.append(latency)
            
            p95 = np.percentile(latencies, 95)
            mean = np.mean(latencies)
            
            regime_latencies[regime['name']] = {'p95': p95, 'mean': mean}
            
            logger.info(
                f"[Test] Regime {regime['name']:10s}: "
                f"mean={mean:.2f}ms, P95={p95:.2f}ms"
            )
        
        # 断言：所有市场状态的P95都 < 220ms
        for regime_name, stats in regime_latencies.items():
            assert stats['p95'] < 220.0, (
                f"Regime {regime_name} P95 {stats['p95']:.2f}ms exceeds target 220ms"
            )
        
        # 断言：不同市场状态的延迟差异 < 50ms
        p95_values = [stats['p95'] for stats in regime_latencies.values()]
        max_diff = max(p95_values) - min(p95_values)
        assert max_diff < 50.0, (
            f"Market regime latency difference {max_diff:.2f}ms is too high"
        )
        
        logger.info("[Test] ✅ Market regime identification latency test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
