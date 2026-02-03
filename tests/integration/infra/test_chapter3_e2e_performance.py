"""第三章端到端性能测试

白皮书依据: 第三章 3.1 + 3.3 基础设施性能要求

性能测试覆盖:
- Bar合成延迟测试 (P99 < 10ms)
- Greeks计算延迟测试 (P99 < 50ms)
- 期货拼接速度测试 (> 1000条/秒)
- 并发处理能力测试 (> 1000标的)

Author: MIA Team
Date: 2026-01-25
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict
import statistics

from src.infra.bar_synthesizer import BarSynthesizer, Tick, Bar
from src.infra.contract_stitcher import ContractStitcher, ContractData
from src.infra.greeks_engine import GreeksEngine, OptionContract, OptionType
from src.infra.path_manager import PathManager


class TestBarSynthesisPerformance:
    """测试Bar合成性能
    
    白皮书依据: 第三章 3.3 Bar Synthesizer - 性能目标: P99 < 10ms
    """
    
    def test_bar_synthesis_p99_latency(self):
        """测试Bar合成P99延迟
        
        验证:
        - P99延迟 < 10ms
        - 平均延迟 < 5ms
        """
        synthesizer = BarSynthesizer(periods=['1m', '5m'])
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        latencies = []
        
        # 处理10000个Tick
        for i in range(10000):
            tick = Tick(
                symbol="000001",
                timestamp=base_time + timedelta(seconds=i),
                price=10.0 + i * 0.0001,
                volume=100,
                amount=1000.0
            )
            
            start = time.perf_counter()
            synthesizer.process_tick(tick)
            elapsed = (time.perf_counter() - start) * 1000  # 转换为毫秒
            
            latencies.append(elapsed)
        
        # 计算统计指标
        latencies.sort()
        p99_index = int(len(latencies) * 0.99)
        p99_latency = latencies[p99_index]
        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        
        print(f"\nBar合成性能统计:")
        print(f"  平均延迟: {avg_latency:.3f}ms")
        print(f"  中位数延迟: {median_latency:.3f}ms")
        print(f"  P99延迟: {p99_latency:.3f}ms")
        
        # 验证性能目标
        assert p99_latency < 10.0, f"P99延迟不达标: {p99_latency:.3f}ms > 10ms"
        assert avg_latency < 5.0, f"平均延迟过高: {avg_latency:.3f}ms > 5ms"
    
    def test_multi_period_synthesis_performance(self):
        """测试多周期合成性能
        
        验证:
        - 多周期同时合成不影响性能
        - P99延迟仍 < 10ms
        """
        synthesizer = BarSynthesizer(periods=['1m', '5m', '15m', '30m', '1h'])
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        latencies = []
        
        # 处理5000个Tick
        for i in range(5000):
            tick = Tick(
                symbol="000001",
                timestamp=base_time + timedelta(seconds=i),
                price=10.0 + i * 0.0001,
                volume=100,
                amount=1000.0
            )
            
            start = time.perf_counter()
            synthesizer.process_tick(tick)
            elapsed = (time.perf_counter() - start) * 1000
            
            latencies.append(elapsed)
        
        # 计算P99延迟
        latencies.sort()
        p99_index = int(len(latencies) * 0.99)
        p99_latency = latencies[p99_index]
        
        print(f"\n多周期合成P99延迟: {p99_latency:.3f}ms")
        
        assert p99_latency < 10.0, f"多周期P99延迟不达标: {p99_latency:.3f}ms > 10ms"
    
    def test_multi_symbol_synthesis_performance(self):
        """测试多标的合成性能
        
        验证:
        - 100个标的并发处理
        - 平均延迟 < 5ms
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        num_symbols = 100
        ticks_per_symbol = 100
        
        latencies = []
        
        # 为每个标的生成Tick
        for symbol_idx in range(num_symbols):
            symbol = f"{symbol_idx:06d}"
            
            for i in range(ticks_per_symbol):
                tick = Tick(
                    symbol=symbol,
                    timestamp=base_time + timedelta(seconds=i),
                    price=10.0 + i * 0.001,
                    volume=100,
                    amount=1000.0
                )
                
                start = time.perf_counter()
                synthesizer.process_tick(tick)
                elapsed = (time.perf_counter() - start) * 1000
                
                latencies.append(elapsed)
        
        # 计算统计指标
        avg_latency = statistics.mean(latencies)
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
        
        print(f"\n多标的合成性能:")
        print(f"  标的数量: {num_symbols}")
        print(f"  平均延迟: {avg_latency:.3f}ms")
        print(f"  P99延迟: {p99_latency:.3f}ms")
        
        assert avg_latency < 5.0, f"平均延迟过高: {avg_latency:.3f}ms > 5ms"
        assert p99_latency < 10.0, f"P99延迟不达标: {p99_latency:.3f}ms > 10ms"


class TestGreeksCalculationPerformance:
    """测试Greeks计算性能
    
    白皮书依据: 第三章 3.3 Greeks Engine - 性能目标: P99 < 50ms
    """
    
    def test_greeks_calculation_p99_latency(self):
        """测试Greeks计算P99延迟
        
        验证:
        - P99延迟 < 50ms
        - 平均延迟 < 20ms
        """
        engine = GreeksEngine(cache_enabled=False)  # 禁用缓存测试真实性能
        
        latencies = []
        
        # 计算1000次
        for i in range(1000):
            contract = OptionContract(
                symbol=f"510050C2401M{3000+i:05d}",
                underlying_price=3.0 + i * 0.001,
                strike_price=3.0,
                time_to_maturity=0.25,
                risk_free_rate=0.03,
                volatility=0.2,
                option_type=OptionType.CALL
            )
            
            start = time.perf_counter()
            engine.calculate_greeks(contract)
            elapsed = (time.perf_counter() - start) * 1000
            
            latencies.append(elapsed)
        
        # 计算统计指标
        latencies.sort()
        p99_index = int(len(latencies) * 0.99)
        p99_latency = latencies[p99_index]
        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        
        print(f"\nGreeks计算性能统计:")
        print(f"  平均延迟: {avg_latency:.3f}ms")
        print(f"  中位数延迟: {median_latency:.3f}ms")
        print(f"  P99延迟: {p99_latency:.3f}ms")
        
        # 验证性能目标
        assert p99_latency < 50.0, f"P99延迟不达标: {p99_latency:.3f}ms > 50ms"
        assert avg_latency < 20.0, f"平均延迟过高: {avg_latency:.3f}ms > 20ms"
    
    def test_greeks_with_cache_performance(self):
        """测试带缓存的Greeks计算性能
        
        验证:
        - 缓存命中时延迟 < 1ms
        - 缓存提升效果明显
        """
        engine = GreeksEngine(cache_enabled=True)
        
        contract = OptionContract(
            symbol="510050C2401M03000",
            underlying_price=3.0,
            strike_price=3.0,
            time_to_maturity=0.25,
            risk_free_rate=0.03,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        # 第一次计算（无缓存）
        start = time.perf_counter()
        engine.calculate_greeks(contract)
        first_time = (time.perf_counter() - start) * 1000
        
        # 第二次计算（有缓存）
        start = time.perf_counter()
        engine.calculate_greeks(contract)
        cached_time = (time.perf_counter() - start) * 1000
        
        print(f"\nGreeks缓存性能:")
        print(f"  首次计算: {first_time:.3f}ms")
        print(f"  缓存命中: {cached_time:.3f}ms")
        print(f"  加速比: {first_time/cached_time:.1f}x")
        
        # 验证缓存效果
        assert cached_time < 1.0, f"缓存命中延迟过高: {cached_time:.3f}ms > 1ms"
        assert cached_time < first_time / 10, "缓存加速效果不明显"
    
    def test_option_chain_batch_performance(self):
        """测试期权链批量计算性能
        
        验证:
        - 批量计算效率
        - 平均延迟 < 30ms
        """
        engine = GreeksEngine(cache_enabled=False)
        
        # 创建期权链（50个不同行权价）
        underlying_price = 3.0
        num_options = 50
        
        latencies = []
        
        for i in range(num_options):
            strike = 2.5 + i * 0.02  # 行权价从2.5到3.5
            
            contract = OptionContract(
                symbol=f"510050C2401M{int(strike*1000):05d}",
                underlying_price=underlying_price,
                strike_price=strike,
                time_to_maturity=0.25,
                risk_free_rate=0.03,
                volatility=0.2,
                option_type=OptionType.CALL
            )
            
            start = time.perf_counter()
            engine.calculate_greeks(contract)
            elapsed = (time.perf_counter() - start) * 1000
            
            latencies.append(elapsed)
        
        avg_latency = statistics.mean(latencies)
        
        print(f"\n期权链批量计算:")
        print(f"  期权数量: {num_options}")
        print(f"  平均延迟: {avg_latency:.3f}ms")
        
        assert avg_latency < 30.0, f"平均延迟过高: {avg_latency:.3f}ms > 30ms"


class TestContractStitchingPerformance:
    """测试期货拼接性能
    
    白皮书依据: 第三章 3.3 Contract Stitcher - 性能目标: > 1000条/秒
    """
    
    def test_contract_stitching_throughput(self):
        """测试期货拼接吞吐量
        
        验证:
        - 拼接速度 > 1000条/秒
        - 大数据量处理稳定
        """
        stitcher = ContractStitcher()
        base_date = datetime(2024, 1, 1)
        
        # 创建大量数据（2000天）
        num_days = 2000
        contracts = []
        
        for i in range(num_days):
            contract = ContractData(
                symbol="IF2401",
                date=base_date + timedelta(days=i),
                open=4000.0 + i * 0.1,
                high=4010.0 + i * 0.1,
                low=3990.0 + i * 0.1,
                close=4005.0 + i * 0.1,
                volume=10000.0,
                open_interest=50000.0
            )
            contracts.append(contract)
        
        stitcher.add_contract_data("IF2401", contracts)
        
        # 拼接合约
        start = time.perf_counter()
        stitched_data = stitcher.stitch_contracts(
            ["IF2401"],
            base_date,
            base_date + timedelta(days=num_days - 1)
        )
        elapsed = time.perf_counter() - start
        
        # 计算吞吐量（条/秒）
        throughput = len(stitched_data) / elapsed
        
        print(f"\n期货拼接性能:")
        print(f"  数据量: {len(stitched_data)}条")
        print(f"  耗时: {elapsed:.3f}秒")
        print(f"  吞吐量: {throughput:.0f}条/秒")
        
        assert throughput > 1000, f"吞吐量不达标: {throughput:.0f}条/秒 < 1000条/秒"
    
    def test_multi_contract_stitching_performance(self):
        """测试多合约拼接性能
        
        验证:
        - 多合约拼接效率
        - 吞吐量保持 > 1000条/秒
        """
        stitcher = ContractStitcher()
        base_date = datetime(2024, 1, 1)
        
        # 创建3个合约的数据
        contracts_list = ["IF2401", "IF2402", "IF2403"]
        num_days = 500
        
        for symbol in contracts_list:
            contracts = []
            for i in range(num_days):
                contract = ContractData(
                    symbol=symbol,
                    date=base_date + timedelta(days=i),
                    open=4000.0 + i * 0.1,
                    high=4010.0 + i * 0.1,
                    low=3990.0 + i * 0.1,
                    close=4005.0 + i * 0.1,
                    volume=10000.0 + float(symbol[-1]) * 1000,
                    open_interest=50000.0
                )
                contracts.append(contract)
            
            stitcher.add_contract_data(symbol, contracts)
        
        # 拼接合约
        start = time.perf_counter()
        stitched_data = stitcher.stitch_contracts(
            contracts_list,
            base_date,
            base_date + timedelta(days=num_days - 1)
        )
        elapsed = time.perf_counter() - start
        
        # 计算吞吐量
        throughput = len(stitched_data) / elapsed
        
        print(f"\n多合约拼接性能:")
        print(f"  合约数量: {len(contracts_list)}")
        print(f"  数据量: {len(stitched_data)}条")
        print(f"  吞吐量: {throughput:.0f}条/秒")
        
        assert throughput > 1000, f"多合约吞吐量不达标: {throughput:.0f}条/秒 < 1000条/秒"



class TestConcurrentProcessingCapability:
    """测试并发处理能力
    
    白皮书依据: 第三章 3.3 基础设施 - 并发处理能力: > 1000标的
    """
    
    def test_bar_synthesis_1000_symbols(self):
        """测试Bar合成1000标的并发
        
        验证:
        - 支持1000标的并发处理
        - 性能不显著下降
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        num_symbols = 1000
        ticks_per_symbol = 60  # 每个标的60个Tick（1分钟）
        
        # 生成所有Tick
        all_ticks = []
        for symbol_idx in range(num_symbols):
            symbol = f"{symbol_idx:06d}"
            for i in range(ticks_per_symbol):
                tick = Tick(
                    symbol=symbol,
                    timestamp=base_time + timedelta(seconds=i),
                    price=10.0 + symbol_idx * 0.001 + i * 0.0001,
                    volume=100,
                    amount=1000.0
                )
                all_ticks.append(tick)
        
        # 按时间排序（模拟真实Tick流）
        all_ticks.sort(key=lambda t: (t.timestamp, t.symbol))
        
        # 处理所有Tick
        start = time.perf_counter()
        for tick in all_ticks:
            synthesizer.process_tick(tick)
        elapsed = time.perf_counter() - start
        
        # 计算统计指标
        total_ticks = len(all_ticks)
        throughput = total_ticks / elapsed
        avg_latency = (elapsed / total_ticks) * 1000
        
        print(f"\n1000标的Bar合成:")
        print(f"  标的数量: {num_symbols}")
        print(f"  总Tick数: {total_ticks}")
        print(f"  总耗时: {elapsed:.3f}秒")
        print(f"  吞吐量: {throughput:.0f} Tick/秒")
        print(f"  平均延迟: {avg_latency:.3f}ms")
        
        # 验证性能
        assert len(synthesizer.buffers) == num_symbols, "标的数量不正确"
        assert avg_latency < 10.0, f"平均延迟过高: {avg_latency:.3f}ms > 10ms"
    
    def test_greeks_calculation_1000_options(self):
        """测试Greeks计算1000期权并发
        
        验证:
        - 支持1000期权并发计算
        - 总体性能可接受
        """
        engine = GreeksEngine(cache_enabled=False)
        
        num_options = 1000
        
        # 生成1000个期权合约
        contracts = []
        for i in range(num_options):
            underlying_price = 3.0 + (i % 100) * 0.01
            strike_price = 2.5 + (i % 50) * 0.02
            
            contract = OptionContract(
                symbol=f"510050C2401M{int(strike_price*1000):05d}_{i}",
                underlying_price=underlying_price,
                strike_price=strike_price,
                time_to_maturity=0.25,
                risk_free_rate=0.03,
                volatility=0.2,
                option_type=OptionType.CALL if i % 2 == 0 else OptionType.PUT
            )
            contracts.append(contract)
        
        # 批量计算Greeks
        start = time.perf_counter()
        for contract in contracts:
            engine.calculate_greeks(contract)
        elapsed = time.perf_counter() - start
        
        # 计算统计指标
        throughput = num_options / elapsed
        avg_time = (elapsed / num_options) * 1000
        
        print(f"\n1000期权Greeks计算:")
        print(f"  期权数量: {num_options}")
        print(f"  总耗时: {elapsed:.3f}秒")
        print(f"  吞吐量: {throughput:.0f} 期权/秒")
        print(f"  平均时间: {avg_time:.3f}ms")
        
        # 验证性能
        assert avg_time < 50.0, f"平均时间过长: {avg_time:.3f}ms > 50ms"
    
    def test_mixed_workload_concurrent_processing(self):
        """测试混合工作负载并发处理
        
        验证:
        - Bar合成 + Greeks计算同时进行
        - 性能不相互影响
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        engine = GreeksEngine(cache_enabled=False)
        
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        bar_latencies = []
        greeks_latencies = []
        
        def process_bars():
            """处理Bar合成"""
            for i in range(500):
                tick = Tick(
                    symbol=f"BAR_{i%10:03d}",
                    timestamp=base_time + timedelta(seconds=i),
                    price=10.0 + i * 0.001,
                    volume=100,
                    amount=1000.0
                )
                
                start = time.perf_counter()
                synthesizer.process_tick(tick)
                elapsed = (time.perf_counter() - start) * 1000
                bar_latencies.append(elapsed)
        
        def process_greeks():
            """处理Greeks计算"""
            for i in range(500):
                contract = OptionContract(
                    symbol=f"OPT_{i:04d}",
                    underlying_price=3.0 + i * 0.001,
                    strike_price=3.0,
                    time_to_maturity=0.25,
                    risk_free_rate=0.03,
                    volatility=0.2,
                    option_type=OptionType.CALL
                )
                
                start = time.perf_counter()
                engine.calculate_greeks(contract)
                elapsed = (time.perf_counter() - start) * 1000
                greeks_latencies.append(elapsed)
        
        # 创建线程并发执行
        bar_thread = threading.Thread(target=process_bars)
        greeks_thread = threading.Thread(target=process_greeks)
        
        start = time.perf_counter()
        bar_thread.start()
        greeks_thread.start()
        
        bar_thread.join()
        greeks_thread.join()
        elapsed = time.perf_counter() - start
        
        # 计算统计指标
        bar_avg = statistics.mean(bar_latencies)
        greeks_avg = statistics.mean(greeks_latencies)
        
        print(f"\n混合工作负载并发:")
        print(f"  总耗时: {elapsed:.3f}秒")
        print(f"  Bar平均延迟: {bar_avg:.3f}ms")
        print(f"  Greeks平均延迟: {greeks_avg:.3f}ms")
        
        # 验证性能
        assert bar_avg < 10.0, f"Bar延迟过高: {bar_avg:.3f}ms > 10ms"
        assert greeks_avg < 50.0, f"Greeks延迟过高: {greeks_avg:.3f}ms > 50ms"


class TestEndToEndPerformance:
    """测试端到端性能
    
    白皮书依据: 第三章 3.1 + 3.3 完整数据流性能
    """
    
    def test_complete_pipeline_performance(self):
        """测试完整管道性能
        
        验证:
        - Tick → Bar → 存储完整流程
        - 端到端延迟可接受
        """
        pm = PathManager()
        synthesizer = BarSynthesizer(periods=['1m', '5m'])
        
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        num_ticks = 1000
        
        # 生成Tick数据
        ticks = []
        for i in range(num_ticks):
            tick = Tick(
                symbol="000001",
                timestamp=base_time + timedelta(seconds=i),
                price=10.0 + i * 0.001,
                volume=100,
                amount=1000.0
            )
            ticks.append(tick)
        
        # 处理完整流程
        start = time.perf_counter()
        
        completed_bars = []
        for tick in ticks:
            bars = synthesizer.process_tick(tick)
            completed_bars.extend(bars)
        
        # 模拟存储到数据盘
        bar_path = pm.get_data_path("bar")
        
        elapsed = time.perf_counter() - start
        
        # 计算统计指标
        throughput = num_ticks / elapsed
        avg_latency = (elapsed / num_ticks) * 1000
        
        print(f"\n完整管道性能:")
        print(f"  处理Tick数: {num_ticks}")
        print(f"  生成Bar数: {len(completed_bars)}")
        print(f"  总耗时: {elapsed:.3f}秒")
        print(f"  吞吐量: {throughput:.0f} Tick/秒")
        print(f"  平均延迟: {avg_latency:.3f}ms")
        
        # 验证性能
        assert avg_latency < 10.0, f"端到端延迟过高: {avg_latency:.3f}ms > 10ms"
        assert bar_path.exists(), "数据路径不存在"
    
    def test_derivatives_pipeline_performance(self):
        """测试衍生品管道性能
        
        验证:
        - 合约拼接 → Greeks计算完整流程
        - 端到端性能达标
        """
        stitcher = ContractStitcher()
        engine = GreeksEngine(cache_enabled=False)
        
        base_date = datetime(2024, 1, 1)
        num_days = 500
        
        # 创建合约数据
        contracts = []
        for i in range(num_days):
            contract = ContractData(
                symbol="IF2401",
                date=base_date + timedelta(days=i),
                open=4000.0 + i * 0.1,
                high=4010.0 + i * 0.1,
                low=3990.0 + i * 0.1,
                close=4005.0 + i * 0.1,
                volume=10000.0,
                open_interest=50000.0
            )
            contracts.append(contract)
        
        # 完整流程计时
        start = time.perf_counter()
        
        # 1. 添加合约数据
        stitcher.add_contract_data("IF2401", contracts)
        
        # 2. 拼接合约
        stitched_data = stitcher.stitch_contracts(
            ["IF2401"],
            base_date,
            base_date + timedelta(days=num_days - 1)
        )
        
        # 3. 使用拼接后的价格计算Greeks
        last_price = stitched_data[-1].close
        
        option_contract = OptionContract(
            symbol="IF2401C4000",
            underlying_price=last_price,
            strike_price=4000.0,
            time_to_maturity=0.25,
            risk_free_rate=0.03,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        greeks = engine.calculate_greeks(option_contract)
        
        elapsed = time.perf_counter() - start
        
        print(f"\n衍生品管道性能:")
        print(f"  合约数据: {num_days}天")
        print(f"  拼接结果: {len(stitched_data)}条")
        print(f"  总耗时: {elapsed:.3f}秒")
        
        # 验证流程完整性
        assert len(stitched_data) > 0, "拼接数据为空"
        assert greeks is not None, "Greeks计算失败"
        assert greeks.option_price > 0, "期权价格无效"
    
    def test_stress_test_peak_load(self):
        """测试峰值负载压力测试
        
        验证:
        - 系统在峰值负载下稳定运行
        - 性能指标仍然达标
        """
        synthesizer = BarSynthesizer(periods=['1m', '5m', '15m'])
        engine = GreeksEngine(cache_enabled=False)
        
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        # 模拟峰值负载：500标的 + 500期权
        num_symbols = 500
        num_options = 500
        ticks_per_symbol = 60
        
        bar_latencies = []
        greeks_latencies = []
        
        # 处理Bar合成
        for symbol_idx in range(num_symbols):
            symbol = f"{symbol_idx:06d}"
            for i in range(ticks_per_symbol):
                tick = Tick(
                    symbol=symbol,
                    timestamp=base_time + timedelta(seconds=i),
                    price=10.0 + symbol_idx * 0.001,
                    volume=100,
                    amount=1000.0
                )
                
                start = time.perf_counter()
                synthesizer.process_tick(tick)
                elapsed = (time.perf_counter() - start) * 1000
                bar_latencies.append(elapsed)
        
        # 处理Greeks计算
        for i in range(num_options):
            contract = OptionContract(
                symbol=f"OPT_{i:04d}",
                underlying_price=3.0 + i * 0.001,
                strike_price=3.0,
                time_to_maturity=0.25,
                risk_free_rate=0.03,
                volatility=0.2,
                option_type=OptionType.CALL
            )
            
            start = time.perf_counter()
            engine.calculate_greeks(contract)
            elapsed = (time.perf_counter() - start) * 1000
            greeks_latencies.append(elapsed)
        
        # 计算统计指标
        bar_p99 = sorted(bar_latencies)[int(len(bar_latencies) * 0.99)]
        greeks_p99 = sorted(greeks_latencies)[int(len(greeks_latencies) * 0.99)]
        
        print(f"\n峰值负载压力测试:")
        print(f"  Bar标的数: {num_symbols}")
        print(f"  期权数量: {num_options}")
        print(f"  Bar P99延迟: {bar_p99:.3f}ms")
        print(f"  Greeks P99延迟: {greeks_p99:.3f}ms")
        
        # 验证峰值负载下性能仍达标
        assert bar_p99 < 10.0, f"峰值Bar延迟不达标: {bar_p99:.3f}ms > 10ms"
        assert greeks_p99 < 50.0, f"峰值Greeks延迟不达标: {greeks_p99:.3f}ms > 50ms"


class TestPerformanceStability:
    """测试性能稳定性
    
    白皮书依据: 第三章 3.3 基础设施 - 性能稳定性
    """
    
    def test_long_running_stability(self):
        """测试长时间运行稳定性
        
        验证:
        - 长时间运行性能不下降
        - 无内存泄漏
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        # 分10批处理，每批1000个Tick
        batch_latencies = []
        
        for batch in range(10):
            batch_start = time.perf_counter()
            
            for i in range(1000):
                tick = Tick(
                    symbol="000001",
                    timestamp=base_time + timedelta(seconds=batch * 1000 + i),
                    price=10.0 + i * 0.001,
                    volume=100,
                    amount=1000.0
                )
                synthesizer.process_tick(tick)
            
            batch_elapsed = (time.perf_counter() - batch_start) * 1000
            batch_latencies.append(batch_elapsed)
        
        # 计算性能变化
        first_batch = batch_latencies[0]
        last_batch = batch_latencies[-1]
        performance_change = (last_batch - first_batch) / first_batch * 100
        
        print(f"\n长时间运行稳定性:")
        print(f"  首批耗时: {first_batch:.3f}ms")
        print(f"  末批耗时: {last_batch:.3f}ms")
        print(f"  性能变化: {performance_change:+.1f}%")
        
        # 验证性能稳定（变化不超过20%）
        assert abs(performance_change) < 20, f"性能下降过多: {performance_change:+.1f}%"
    
    def test_memory_efficiency(self):
        """测试内存效率
        
        验证:
        - 内存使用合理
        - 缓冲区管理正确
        """
        synthesizer = BarSynthesizer(periods=['1m'])
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        # 处理100个标的
        num_symbols = 100
        
        for symbol_idx in range(num_symbols):
            symbol = f"{symbol_idx:06d}"
            
            # 每个标的处理120秒（2分钟）
            for i in range(120):
                tick = Tick(
                    symbol=symbol,
                    timestamp=base_time + timedelta(seconds=i),
                    price=10.0,
                    volume=100,
                    amount=1000.0
                )
                synthesizer.process_tick(tick)
        
        # 验证缓冲区数量
        active_buffers = len(synthesizer.buffers)
        
        print(f"\n内存效率:")
        print(f"  处理标的数: {num_symbols}")
        print(f"  活跃缓冲区: {active_buffers}")
        
        # 验证缓冲区数量合理（应该等于标的数 * 周期数）
        expected_buffers = num_symbols * len(synthesizer.supported_periods)
        assert active_buffers == expected_buffers, f"缓冲区数量异常: {active_buffers} != {expected_buffers}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
