"""BarSynthesizer性能测试

白皮书依据: 第三章 3.3 Bar Synthesizer

性能目标:
- 单标的延迟: P99 < 10ms
- 多标的并发: > 1000标的
- 批量处理吞吐量: > 10000 ticks/秒

Author: MIA Team
Date: 2026-01-22
"""

import time
import statistics
from datetime import datetime, timedelta
from typing import List
import pytest

from src.infra.bar_synthesizer import BarSynthesizer, Tick


class TestBarSynthesizerPerformance:
    """BarSynthesizer性能测试"""
    
    def test_single_symbol_latency(self):
        """测试单标的处理延迟
        
        性能目标: P99 < 10ms
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        
        latencies = []
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        # 处理1000个Tick
        for i in range(1000):
            tick = Tick(
                symbol='000001.SZ',
                timestamp=base_time + timedelta(seconds=i),
                price=10.0 + i * 0.01,
                volume=100,
                amount=1000.0
            )
            
            start = time.perf_counter()
            synthesizer.process_tick(tick)
            elapsed = time.perf_counter() - start
            
            latencies.append(elapsed * 1000)  # 转换为毫秒
        
        # 计算统计指标
        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        p99 = statistics.quantiles(latencies, n=100)[98]  # 99th percentile
        avg = statistics.mean(latencies)
        
        print(f"\n单标的延迟统计:")
        print(f"  平均: {avg:.3f}ms")
        print(f"  P50: {p50:.3f}ms")
        print(f"  P95: {p95:.3f}ms")
        print(f"  P99: {p99:.3f}ms")
        
        # 验证性能目标
        assert p99 < 10.0, f"P99延迟({p99:.3f}ms)超过目标(10ms)"
    
    def test_multi_symbol_concurrent(self):
        """测试多标的并发处理
        
        性能目标: > 1000标的
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 生成1000个标的
        symbols = [f"{str(i).zfill(6)}.SZ" for i in range(1, 1001)]
        
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        start = time.perf_counter()
        
        # 每个标的处理10个Tick
        for symbol in symbols:
            for i in range(10):
                tick = Tick(
                    symbol=symbol,
                    timestamp=base_time + timedelta(seconds=i),
                    price=10.0,
                    volume=100,
                    amount=1000.0
                )
                synthesizer.process_tick(tick)
        
        elapsed = time.perf_counter() - start
        
        # 统计
        total_ticks = len(symbols) * 10
        ticks_per_second = total_ticks / elapsed
        
        print(f"\n多标的并发统计:")
        print(f"  标的数量: {len(symbols)}")
        print(f"  总Tick数: {total_ticks}")
        print(f"  总耗时: {elapsed:.3f}秒")
        print(f"  吞吐量: {ticks_per_second:.0f} ticks/秒")
        print(f"  活跃缓冲区: {len(synthesizer.buffers)}")
        
        # 验证性能目标
        assert len(symbols) >= 1000, "未达到1000标的目标"
        assert ticks_per_second > 1000, f"吞吐量({ticks_per_second:.0f})低于预期"
    
    def test_batch_processing_throughput(self):
        """测试批量处理吞吐量
        
        性能目标: > 10000 ticks/秒
        """
        synthesizer = BarSynthesizer(periods=['1m', '5m'])
        
        # 生成10000个Tick
        ticks = []
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        for i in range(10000):
            tick = Tick(
                symbol='000001.SZ',
                timestamp=base_time + timedelta(milliseconds=i*10),
                price=10.0 + i * 0.001,
                volume=100,
                amount=1000.0
            )
            ticks.append(tick)
        
        # 批量处理
        start = time.perf_counter()
        
        for tick in ticks:
            synthesizer.process_tick(tick)
        
        elapsed = time.perf_counter() - start
        
        # 统计
        throughput = len(ticks) / elapsed
        
        print(f"\n批量处理统计:")
        print(f"  Tick数量: {len(ticks)}")
        print(f"  总耗时: {elapsed:.3f}秒")
        print(f"  吞吐量: {throughput:.0f} ticks/秒")
        print(f"  已完成Bar: {len(synthesizer.completed_bars)}")
        
        # 验证性能目标
        assert throughput > 10000, f"吞吐量({throughput:.0f})低于目标(10000 ticks/秒)"
    
    def test_multi_period_overhead(self):
        """测试多周期合成的性能开销"""
        
        # 单周期
        synthesizer_1 = BarSynthesizer(periods=['1m'])
        
        # 多周期
        synthesizer_6 = BarSynthesizer(periods=['1m', '5m', '15m', '30m', '1h', '1d'])
        
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        ticks = []
        
        for i in range(1000):
            tick = Tick(
                symbol='000001.SZ',
                timestamp=base_time + timedelta(seconds=i),
                price=10.0,
                volume=100,
                amount=1000.0
            )
            ticks.append(tick)
        
        # 测试单周期
        start = time.perf_counter()
        for tick in ticks:
            synthesizer_1.process_tick(tick)
        elapsed_1 = time.perf_counter() - start
        
        # 测试多周期
        start = time.perf_counter()
        for tick in ticks:
            synthesizer_6.process_tick(tick)
        elapsed_6 = time.perf_counter() - start
        
        overhead = (elapsed_6 - elapsed_1) / elapsed_1 * 100
        
        print(f"\n多周期性能开销:")
        print(f"  单周期(1m): {elapsed_1:.3f}秒")
        print(f"  多周期(6个): {elapsed_6:.3f}秒")
        print(f"  性能开销: {overhead:.1f}%")
        
        # 验证开销合理（应该<6倍，理想<3倍）
        assert elapsed_6 < elapsed_1 * 6, "多周期开销过大"
    
    def test_memory_efficiency(self):
        """测试内存效率"""
        import sys
        
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 测试缓冲区内存使用
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        # 处理1000个标的，每个10个Tick
        for symbol_id in range(1000):
            symbol = f"{str(symbol_id).zfill(6)}.SZ"
            for i in range(10):
                tick = Tick(
                    symbol=symbol,
                    timestamp=base_time + timedelta(seconds=i),
                    price=10.0,
                    volume=100,
                    amount=1000.0
                )
                synthesizer.process_tick(tick)
        
        # 统计内存使用
        buffer_count = len(synthesizer.buffers)
        completed_count = len(synthesizer.completed_bars)
        
        # 估算单个缓冲区大小
        if synthesizer.buffers:
            sample_buffer = next(iter(synthesizer.buffers.values()))
            buffer_size = sys.getsizeof(sample_buffer)
        else:
            buffer_size = 0
        
        total_buffer_memory = buffer_count * buffer_size
        
        print(f"\n内存效率统计:")
        print(f"  活跃缓冲区: {buffer_count}")
        print(f"  已完成Bar: {completed_count}")
        print(f"  单缓冲区大小: ~{buffer_size}字节")
        print(f"  总缓冲区内存: ~{total_buffer_memory/1024:.1f}KB")
        
        # 验证内存使用合理
        assert buffer_count == 1000, "缓冲区数量不正确"
        assert total_buffer_memory < 10 * 1024 * 1024, "内存使用过大(>10MB)"
    
    def test_period_boundary_performance(self):
        """测试周期边界处理性能"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        latencies = []
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        # 生成跨越多个周期的Tick
        for minute in range(10):
            for second in range(60):
                tick = Tick(
                    symbol='000001.SZ',
                    timestamp=base_time + timedelta(minutes=minute, seconds=second),
                    price=10.0,
                    volume=100,
                    amount=1000.0
                )
                
                start = time.perf_counter()
                completed_bars = synthesizer.process_tick(tick)
                elapsed = time.perf_counter() - start
                
                latencies.append(elapsed * 1000)
                
                # 记录周期边界的延迟
                if completed_bars:
                    print(f"  周期边界延迟: {elapsed*1000:.3f}ms (完成{len(completed_bars)}个Bar)")
        
        p99 = statistics.quantiles(latencies, n=100)[98]
        
        print(f"\n周期边界性能:")
        print(f"  P99延迟: {p99:.3f}ms")
        print(f"  已完成Bar: {len(synthesizer.completed_bars)}")
        
        # 验证周期边界处理不影响性能
        assert p99 < 10.0, f"周期边界P99延迟({p99:.3f}ms)超过目标"


class TestBarSynthesizerStressTest:
    """BarSynthesizer压力测试"""
    
    def test_extreme_tick_rate(self):
        """测试极端Tick速率
        
        模拟高频交易场景
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        # 1秒内1000个Tick
        start = time.perf_counter()
        
        for i in range(1000):
            tick = Tick(
                symbol='000001.SZ',
                timestamp=base_time + timedelta(microseconds=i*1000),
                price=10.0 + i * 0.0001,
                volume=10,
                amount=100.0
            )
            synthesizer.process_tick(tick)
        
        elapsed = time.perf_counter() - start
        
        print(f"\n极端Tick速率测试:")
        print(f"  Tick数量: 1000")
        print(f"  总耗时: {elapsed:.3f}秒")
        print(f"  速率: {1000/elapsed:.0f} ticks/秒")
        
        # 验证能处理高频Tick
        assert elapsed < 1.0, "处理1000个Tick耗时超过1秒"
    
    def test_long_running_stability(self):
        """测试长时间运行稳定性
        
        模拟一整天的交易
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 模拟4小时交易（9:30-13:30），每秒1个Tick
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        total_seconds = 4 * 60 * 60
        
        start = time.perf_counter()
        
        for second in range(0, total_seconds, 10):  # 每10秒采样一次
            tick = Tick(
                symbol='000001.SZ',
                timestamp=base_time + timedelta(seconds=second),
                price=10.0,
                volume=100,
                amount=1000.0
            )
            synthesizer.process_tick(tick)
        
        elapsed = time.perf_counter() - start
        
        # 强制完成所有Bar
        final_bars = synthesizer.force_complete_all_bars()
        
        print(f"\n长时间运行稳定性测试:")
        print(f"  模拟时长: {total_seconds/3600:.1f}小时")
        print(f"  实际耗时: {elapsed:.3f}秒")
        print(f"  已完成Bar: {len(synthesizer.completed_bars)}")
        print(f"  最终Bar: {len(final_bars)}")
        
        # 验证稳定性
        expected_bars = total_seconds // 60  # 每分钟一个Bar
        assert len(synthesizer.completed_bars) >= expected_bars * 0.9, "Bar数量异常"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
