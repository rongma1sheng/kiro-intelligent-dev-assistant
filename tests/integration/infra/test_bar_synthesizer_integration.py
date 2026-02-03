"""BarSynthesizer集成测试

白皮书依据: 第三章 3.3 Bar Synthesizer

集成测试覆盖:
- Tick数据源集成
- 多标的并发处理
- Bar质量验证
- 性能指标验证
- 数据流完整性

Author: MIA Team
Date: 2026-01-25
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from typing import List
from collections import defaultdict

from src.infra.bar_synthesizer import (
    BarSynthesizer, 
    Tick, 
    Bar, 
    BarBuffer,
    get_bar_synthesizer
)
from src.infra.path_manager import PathManager


class TestTickDataSourceIntegration:
    """测试Tick数据源集成
    
    白皮书依据: 第三章 3.3 Bar Synthesizer - Tick数据源集成
    """
    
    def test_single_symbol_tick_stream(self):
        """测试单标的Tick流处理
        
        验证:
        - Tick流正常接收
        - Bar正确生成
        - 数据完整性
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 模拟Tick数据流 - 跨越3分钟
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        ticks = []
        
        for minute in range(3):
            for second in range(60):
                tick = Tick(
                    symbol="000001",
                    timestamp=base_time + timedelta(minutes=minute, seconds=second),
                    price=10.0 + minute * 0.1 + second * 0.001,
                    volume=100,
                    amount=1000.0
                )
                ticks.append(tick)
        
        # 处理Tick流
        completed_bars = []
        for tick in ticks:
            bars = synthesizer.process_tick(tick)
            completed_bars.extend(bars)
        
        # 验证生成了2个完整的Bar（第3分钟的Bar还未完成）
        assert len(completed_bars) == 2
        
        # 验证Bar数据完整性
        for bar in completed_bars:
            assert bar.symbol == "000001"
            assert bar.period == "1m"
            assert bar.open > 0
            assert bar.high >= bar.low
            assert bar.high >= bar.open
            assert bar.high >= bar.close
            assert bar.low <= bar.open
            assert bar.low <= bar.close
            assert bar.volume == 6000  # 60秒 * 100
            assert bar.tick_count == 60
    
    def test_multiple_symbols_tick_stream(self):
        """测试多标的Tick流处理
        
        验证:
        - 多标的并发处理
        - Bar独立生成
        - 无数据混淆
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        
        symbols = ["000001", "000002", "000003"]
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        # 为每个标的生成Tick数据 - 跨越2分钟
        all_ticks = []
        for symbol in symbols:
            for minute in range(2):
                for second in range(60):
                    tick = Tick(
                        symbol=symbol,
                        timestamp=base_time + timedelta(minutes=minute, seconds=second),
                        price=10.0 + float(symbol[-1]) + minute * 0.1,
                        volume=100,
                        amount=1000.0
                    )
                    all_ticks.append(tick)
        
        # 按时间排序（模拟真实Tick流）
        all_ticks.sort(key=lambda t: t.timestamp)
        
        # 处理Tick流
        completed_bars = []
        for tick in all_ticks:
            bars = synthesizer.process_tick(tick)
            completed_bars.extend(bars)
        
        # 验证每个标的都生成了1个Bar
        bars_by_symbol = defaultdict(list)
        for bar in completed_bars:
            bars_by_symbol[bar.symbol].append(bar)
        
        assert len(bars_by_symbol) == 3
        for symbol in symbols:
            assert len(bars_by_symbol[symbol]) == 1
            assert bars_by_symbol[symbol][0].symbol == symbol
    
    def test_tick_data_validation(self):
        """测试Tick数据验证
        
        验证:
        - 无效Tick被拒绝
        - 错误信息清晰
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        # 测试无效价格
        invalid_tick = Tick("000001", base_time, -10.0, 100, 1000.0)
        with pytest.raises(ValueError, match="无效的价格"):
            synthesizer.process_tick(invalid_tick)
        
        # 测试无效成交量
        invalid_tick = Tick("000001", base_time, 10.0, -100, 1000.0)
        with pytest.raises(ValueError, match="无效的成交量"):
            synthesizer.process_tick(invalid_tick)


class TestMultiPeriodConcurrentProcessing:
    """测试多周期并发处理
    
    白皮书依据: 第三章 3.3 Bar Synthesizer - 多周期并发合成
    """
    
    def test_concurrent_period_synthesis(self):
        """测试多周期并发合成
        
        验证:
        - 多周期同时合成
        - 各周期独立正确
        - 周期对齐正确
        """
        synthesizer = BarSynthesizer(periods=['1m', '5m', '15m'])
        
        # 生成16分钟的Tick数据
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        ticks = []
        
        for minute in range(16):
            for second in range(60):
                tick = Tick(
                    symbol="000001",
                    timestamp=base_time + timedelta(minutes=minute, seconds=second),
                    price=10.0 + minute * 0.01,
                    volume=100,
                    amount=1000.0
                )
                ticks.append(tick)
        
        # 处理Tick流
        completed_bars = []
        for tick in ticks:
            bars = synthesizer.process_tick(tick)
            completed_bars.extend(bars)
        
        # 按周期分组
        bars_by_period = defaultdict(list)
        for bar in completed_bars:
            bars_by_period[bar.period].append(bar)
        
        # 验证各周期Bar数量
        assert len(bars_by_period['1m']) == 15  # 15个完整的1分钟Bar
        assert len(bars_by_period['5m']) == 3   # 3个完整的5分钟Bar
        assert len(bars_by_period['15m']) == 1  # 1个完整的15分钟Bar
    
    def test_period_alignment(self):
        """测试周期对齐
        
        验证:
        - 周期开始时间对齐
        - 周期边界正确
        """
        synthesizer = BarSynthesizer(periods=['5m'])
        
        # 生成从9:32开始的Tick数据（非整5分钟）
        base_time = datetime(2024, 1, 1, 9, 32, 0)
        ticks = []
        
        for minute in range(6):
            for second in range(60):
                tick = Tick(
                    symbol="000001",
                    timestamp=base_time + timedelta(minutes=minute, seconds=second),
                    price=10.0,
                    volume=100,
                    amount=1000.0
                )
                ticks.append(tick)
        
        # 处理Tick流
        completed_bars = []
        for tick in ticks:
            bars = synthesizer.process_tick(tick)
            completed_bars.extend(bars)
        
        # 验证第一个Bar的开始时间应该是9:30（向下对齐到5分钟边界）
        assert len(completed_bars) >= 1
        first_bar = completed_bars[0]
        assert first_bar.timestamp.minute % 5 == 0


class TestBarQualityValidation:
    """测试Bar质量验证
    
    白皮书依据: 第三章 3.3 Bar Synthesizer - Bar质量检查
    """
    
    def test_valid_bar_validation(self):
        """测试有效Bar验证
        
        验证:
        - 有效Bar通过验证
        - 无错误信息
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 创建有效Bar
        valid_bar = Bar(
            symbol="000001",
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            period="1m",
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            volume=1000,
            amount=10000.0,
            tick_count=60
        )
        
        is_valid, errors = synthesizer.validate_bar(valid_bar)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_invalid_hloc_consistency(self):
        """测试HLOC一致性验证
        
        验证:
        - 检测到HLOC不一致
        - 错误信息准确
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 创建HLOC不一致的Bar（high < low）
        invalid_bar = Bar(
            symbol="000001",
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            period="1m",
            open=10.0,
            high=9.5,  # high < low，不合理
            low=9.8,
            close=10.2,
            volume=1000,
            amount=10000.0,
            tick_count=60
        )
        
        is_valid, errors = synthesizer.validate_bar(invalid_bar)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("最高价" in err and "最低价" in err for err in errors)
    
    def test_invalid_price_values(self):
        """测试无效价格值验证
        
        验证:
        - 检测到负价格
        - 检测到零价格
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 创建负价格的Bar
        invalid_bar = Bar(
            symbol="000001",
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            period="1m",
            open=-10.0,  # 负价格
            high=10.5,
            low=9.8,
            close=10.2,
            volume=1000,
            amount=10000.0,
            tick_count=60
        )
        
        is_valid, errors = synthesizer.validate_bar(invalid_bar)
        
        assert is_valid is False
        assert any("价格必须大于0" in err for err in errors)


class TestPerformanceMetrics:
    """测试性能指标
    
    白皮书依据: 第三章 3.3 Bar Synthesizer - 性能目标: P99 < 10ms
    """
    
    def test_single_tick_processing_latency(self):
        """测试单Tick处理延迟
        
        验证:
        - P99延迟 < 10ms
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        latencies = []
        
        # 处理1000个Tick
        for i in range(1000):
            tick = Tick(
                symbol="000001",
                timestamp=base_time + timedelta(seconds=i),
                price=10.0 + i * 0.001,
                volume=100,
                amount=1000.0
            )
            
            start = time.perf_counter()
            synthesizer.process_tick(tick)
            elapsed = (time.perf_counter() - start) * 1000  # 转换为毫秒
            
            latencies.append(elapsed)
        
        # 计算P99延迟
        latencies.sort()
        p99_index = int(len(latencies) * 0.99)
        p99_latency = latencies[p99_index]
        
        assert p99_latency < 10.0, f"P99延迟过高: {p99_latency:.3f}ms > 10ms"
    
    def test_multi_symbol_concurrent_processing(self):
        """测试多标的并发处理性能
        
        验证:
        - 支持>1000标的并发
        - 总体延迟可接受
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        # 生成1000个标的的Tick数据
        num_symbols = 1000
        ticks = []
        
        for i in range(num_symbols):
            symbol = f"{i:06d}"
            tick = Tick(
                symbol=symbol,
                timestamp=base_time,
                price=10.0 + i * 0.001,
                volume=100,
                amount=1000.0
            )
            ticks.append(tick)
        
        # 处理所有Tick
        start = time.perf_counter()
        for tick in ticks:
            synthesizer.process_tick(tick)
        elapsed = (time.perf_counter() - start) * 1000
        
        # 验证总体处理时间
        avg_latency = elapsed / num_symbols
        assert avg_latency < 1.0, f"平均延迟过高: {avg_latency:.3f}ms"
        
        # 验证缓冲区数量
        assert len(synthesizer.buffers) == num_symbols
    
    def test_batch_processing_throughput(self):
        """测试批量处理吞吐量
        
        验证:
        - 批量处理效率
        - 吞吐量满足要求
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        # 生成10000个Tick
        num_ticks = 10000
        ticks = []
        
        for i in range(num_ticks):
            tick = Tick(
                symbol="000001",
                timestamp=base_time + timedelta(seconds=i % 60, minutes=i // 60),
                price=10.0 + i * 0.0001,
                volume=100,
                amount=1000.0
            )
            ticks.append(tick)
        
        # 批量处理
        start = time.perf_counter()
        for tick in ticks:
            synthesizer.process_tick(tick)
        elapsed = time.perf_counter() - start
        
        # 计算吞吐量（Tick/秒）
        throughput = num_ticks / elapsed
        
        # 验证吞吐量 > 10000 Tick/秒
        assert throughput > 10000, f"吞吐量不足: {throughput:.0f} Tick/s"


class TestDataFlowIntegrity:
    """测试数据流完整性
    
    白皮书依据: 第三章 3.3 Bar Synthesizer - 数据流完整性
    """
    
    def test_tick_to_bar_data_integrity(self):
        """测试Tick到Bar数据完整性
        
        验证:
        - 成交量累加正确
        - 成交额累加正确
        - Tick计数正确
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        # 生成2分钟的Tick数据
        total_volume = 0
        total_amount = 0.0
        tick_count = 0
        
        ticks = []
        for minute in range(2):
            for second in range(60):
                volume = 100 + second
                amount = 1000.0 + second * 10
                
                tick = Tick(
                    symbol="000001",
                    timestamp=base_time + timedelta(minutes=minute, seconds=second),
                    price=10.0,
                    volume=volume,
                    amount=amount
                )
                ticks.append(tick)
                
                if minute == 0:  # 只统计第一分钟
                    total_volume += volume
                    total_amount += amount
                    tick_count += 1
        
        # 处理Tick流
        completed_bars = []
        for tick in ticks:
            bars = synthesizer.process_tick(tick)
            completed_bars.extend(bars)
        
        # 验证第一个Bar的数据完整性
        assert len(completed_bars) >= 1
        first_bar = completed_bars[0]
        
        assert first_bar.volume == total_volume
        assert abs(first_bar.amount - total_amount) < 0.01
        assert first_bar.tick_count == tick_count
    
    def test_bar_completion_timing(self):
        """测试Bar完成时机
        
        验证:
        - Bar在周期结束时完成
        - 不会提前完成
        - 不会延迟完成
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        completed_bars = []
        
        # 第一分钟的Tick（9:30:00 - 9:30:59）
        for second in range(60):
            tick = Tick(
                symbol="000001",
                timestamp=base_time + timedelta(seconds=second),
                price=10.0,
                volume=100,
                amount=1000.0
            )
            bars = synthesizer.process_tick(tick)
            completed_bars.extend(bars)
        
        # 第一分钟内不应该有完成的Bar
        assert len(completed_bars) == 0
        
        # 第二分钟的第一个Tick（9:31:00）
        tick = Tick(
            symbol="000001",
            timestamp=base_time + timedelta(minutes=1),
            price=10.0,
            volume=100,
            amount=1000.0
        )
        bars = synthesizer.process_tick(tick)
        completed_bars.extend(bars)
        
        # 现在应该有1个完成的Bar
        assert len(completed_bars) == 1
        assert completed_bars[0].timestamp == base_time
    
    def test_force_complete_all_bars(self):
        """测试强制完成所有Bar
        
        验证:
        - 未完成的Bar被强制完成
        - 缓冲区被清空
        """
        synthesizer = BarSynthesizer(periods=['1m', '5m'])
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        # 生成1.5分钟的Tick数据（会有未完成的Bar）
        for second in range(90):
            tick = Tick(
                symbol="000001",
                timestamp=base_time + timedelta(seconds=second),
                price=10.0,
                volume=100,
                amount=1000.0
            )
            synthesizer.process_tick(tick)
        
        # 验证有活跃缓冲区
        assert len(synthesizer.buffers) > 0
        
        # 强制完成所有Bar
        forced_bars = synthesizer.force_complete_all_bars()
        
        # 验证Bar被完成
        assert len(forced_bars) > 0
        
        # 验证缓冲区被清空
        assert len(synthesizer.buffers) == 0


class TestStatisticsAndMonitoring:
    """测试统计和监控
    
    白皮书依据: 第三章 3.3 Bar Synthesizer - 统计监控
    """
    
    def test_statistics_collection(self):
        """测试统计信息收集
        
        验证:
        - 统计信息准确
        - 包含所有关键指标
        """
        synthesizer = BarSynthesizer(periods=['1m', '5m'])
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        # 生成多标的Tick数据
        symbols = ["000001", "000002"]
        for symbol in symbols:
            for minute in range(6):
                for second in range(60):
                    tick = Tick(
                        symbol=symbol,
                        timestamp=base_time + timedelta(minutes=minute, seconds=second),
                        price=10.0,
                        volume=100,
                        amount=1000.0
                    )
                    synthesizer.process_tick(tick)
        
        # 获取统计信息
        stats = synthesizer.get_statistics()
        
        # 验证统计信息
        assert 'active_buffers' in stats
        assert 'completed_bars' in stats
        assert 'period_stats' in stats
        assert 'symbol_stats' in stats
        assert 'supported_periods' in stats
        
        # 验证统计数据
        assert stats['active_buffers'] > 0
        assert stats['completed_bars'] > 0
        assert len(stats['period_stats']) > 0
        assert len(stats['symbol_stats']) == 2


class TestEdgeCasesAndErrorHandling:
    """测试边界条件和错误处理
    
    白皮书依据: 第三章 3.3 Bar Synthesizer - 错误处理
    """
    
    def test_unsupported_period(self):
        """测试不支持的周期
        
        验证:
        - 拒绝不支持的周期
        - 错误信息清晰
        """
        with pytest.raises(ValueError, match="不支持的周期"):
            BarSynthesizer(periods=['2m'])  # 2m不在支持列表中
    
    def test_empty_period_list(self):
        """测试空周期列表
        
        验证:
        - 使用默认周期列表
        """
        synthesizer = BarSynthesizer(periods=None)
        
        # 应该使用所有支持的周期
        assert len(synthesizer.supported_periods) > 0
        assert '1m' in synthesizer.supported_periods
    
    def test_concurrent_access_thread_safety(self):
        """测试并发访问线程安全
        
        验证:
        - 多线程并发访问
        - 无竞态条件
        - 数据一致性
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        results = []
        errors = []
        
        def process_ticks(symbol: str, start_second: int):
            try:
                for i in range(100):
                    tick = Tick(
                        symbol=symbol,
                        timestamp=base_time + timedelta(seconds=start_second + i),
                        price=10.0,
                        volume=100,
                        amount=1000.0
                    )
                    bars = synthesizer.process_tick(tick)
                    results.extend(bars)
            except Exception as e:
                errors.append(e)
        
        # 创建多个线程并发处理
        threads = []
        for i in range(5):
            symbol = f"00000{i}"
            thread = threading.Thread(target=process_ticks, args=(symbol, i * 100))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证无错误
        assert len(errors) == 0
        
        # 验证有结果
        assert len(results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
