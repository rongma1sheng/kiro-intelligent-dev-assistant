#!/usr/bin/env python
"""
Soldier引擎 v2.0 演示脚本

展示功能:
1. 多模式运行 (本地/云端/离线)
2. 快速决策推理 (< 20ms)
3. 自动故障切换和恢复
4. 事件驱动通信
5. 决策缓存和性能优化
6. 健康监控和统计
"""

import asyncio
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.brain.soldier_engine_v2 import (
    SoldierEngineV2,
    SoldierConfig,
    SoldierMode,
    SoldierDecision
)
from src.infra.event_bus import EventBus, Event, EventType, EventPriority
from src.brain.llm_gateway import LLMGateway
from src.brain.hallucination_filter import HallucinationFilter


class SoldierEngineDemo:
    """Soldier引擎演示类"""
    
    def __init__(self):
        self.soldier_engine = None
        self.event_bus = None
        
    async def initialize(self):
        """初始化演示环境"""
        print("🚀 初始化Soldier引擎 v2.0...")
        
        # 创建配置
        config = SoldierConfig(
            local_inference_timeout=0.015,  # 15ms本地推理超时
            cloud_timeout=2.0,              # 2秒云端超时
            failure_threshold=2,            # 2次失败后切换
            decision_cache_ttl=3,           # 3秒决策缓存
            recovery_check_interval=10.0    # 10秒恢复检查
        )
        
        # 初始化组件
        llm_gateway = LLMGateway()
        hallucination_filter = HallucinationFilter()
        
        # 创建Soldier引擎
        self.soldier_engine = SoldierEngineV2(config, llm_gateway, hallucination_filter)
        
        # 初始化事件总线
        self.event_bus = EventBus()
        
        # 初始化Soldier引擎
        await self.soldier_engine.initialize()
        
        print("✅ Soldier引擎初始化完成")
        print(f"   - 模式: {self.soldier_engine.mode.value}")
        print(f"   - 状态: {self.soldier_engine.state}")
        print(f"   - 本地推理超时: {config.local_inference_timeout*1000:.0f}ms")
        print(f"   - 云端推理超时: {config.cloud_timeout}s")
        print()
    
    async def demo_normal_mode_decisions(self):
        """演示正常模式决策"""
        print("🧠 演示正常模式 (本地推理) 决策...")
        
        # 确保在正常模式
        self.soldier_engine.mode = SoldierMode.NORMAL
        
        test_stocks = [
            {"symbol": "AAPL", "close": 150.0, "volume": 1000000, "ma20": 145.0},
            {"symbol": "TSLA", "close": 200.0, "volume": 2000000, "ma20": 205.0},
            {"symbol": "NVDA", "close": 300.0, "volume": 1500000, "ma20": 295.0}
        ]
        
        decisions = []
        total_time = 0
        
        for stock in test_stocks:
            print(f"\n📊 分析股票: {stock['symbol']}")
            print(f"   价格: ${stock['close']:.2f}")
            print(f"   成交量: {stock['volume']:,}")
            
            start_time = time.perf_counter()
            
            try:
                result = await self.soldier_engine.make_decision(
                    stock['symbol'], 
                    stock
                )
                
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000
                total_time += latency_ms
                
                decision = result['decision']
                decisions.append((stock['symbol'], decision, latency_ms))
                
                print(f"   🎯 决策: {decision['action'].upper()}")
                print(f"   🎯 置信度: {decision['confidence']:.2%}")
                print(f"   🎯 信号强度: {decision['signal_strength']:.2%}")
                print(f"   🎯 风险等级: {decision['risk_level']}")
                print(f"   ⚡ 延迟: {latency_ms:.2f}ms")
                print(f"   🔧 模式: {decision['source_mode']}")
                
                if latency_ms < 20:
                    print("   ✅ 延迟达标 (< 20ms)")
                else:
                    print("   ⚠️  延迟超标 (> 20ms)")
                    
            except Exception as e:
                print(f"   ❌ 决策失败: {e}")
        
        avg_latency = total_time / len(test_stocks) if test_stocks else 0
        print(f"\n📈 正常模式性能统计:")
        print(f"   平均延迟: {avg_latency:.2f}ms")
        print(f"   总决策数: {len(decisions)}")
        
        return decisions
    
    async def demo_mode_switching(self):
        """演示模式切换"""
        print("🔄 演示自动模式切换...")
        
        # 模拟本地推理故障
        print("\n⚠️  模拟本地推理故障...")
        
        original_local_inference = self.soldier_engine._local_inference
        
        async def failing_local_inference(*args, **kwargs):
            raise Exception("模拟本地推理故障")
        
        # 替换本地推理方法
        self.soldier_engine._local_inference = failing_local_inference
        
        try:
            print("   尝试本地推理决策...")
            result = await self.soldier_engine.make_decision("AAPL", {"close": 150.0})
            
            print(f"   🔄 自动切换到: {self.soldier_engine.mode.value}")
            print(f"   🎯 决策结果: {result['decision']['action']}")
            print(f"   🔧 决策模式: {result['decision']['source_mode']}")
            print(f"   📊 失败计数: {self.soldier_engine.failure_count}")
            
        except Exception as e:
            print(f"   ❌ 切换失败: {e}")
        
        # 恢复原始方法
        self.soldier_engine._local_inference = original_local_inference
        
        # 演示恢复检查
        print("\n🔧 演示模式恢复...")
        await self.soldier_engine._try_recover_to_normal_mode()
        print(f"   当前模式: {self.soldier_engine.mode.value}")
    
    async def demo_decision_caching(self):
        """演示决策缓存"""
        print("💾 演示决策缓存机制...")
        
        symbol = "AAPL"
        market_data = {"close": 150.0, "volume": 1000000}
        
        print(f"\n📊 测试股票: {symbol}")
        print(f"   市场数据: {market_data}")
        
        # 第一次决策 (无缓存)
        print("\n1️⃣ 第一次决策 (无缓存):")
        start_time = time.perf_counter()
        result1 = await self.soldier_engine.make_decision(symbol, market_data)
        latency1 = (time.perf_counter() - start_time) * 1000
        
        print(f"   决策: {result1['decision']['action']}")
        print(f"   延迟: {latency1:.2f}ms")
        print(f"   缓存命中: {self.soldier_engine.stats['cache_hits']}")
        
        # 第二次相同决策 (应该命中缓存)
        print("\n2️⃣ 第二次相同决策 (应该命中缓存):")
        start_time = time.perf_counter()
        result2 = await self.soldier_engine.make_decision(symbol, market_data)
        latency2 = (time.perf_counter() - start_time) * 1000
        
        print(f"   决策: {result2['decision']['action']}")
        print(f"   延迟: {latency2:.2f}ms")
        print(f"   缓存命中: {self.soldier_engine.stats['cache_hits']}")
        
        if latency2 < latency1:
            print("   ✅ 缓存生效，延迟降低")
        else:
            print("   ⚠️  缓存可能未生效")
        
        # 等待缓存过期
        print(f"\n⏳ 等待缓存过期 ({self.soldier_engine.config.decision_cache_ttl}秒)...")
        await asyncio.sleep(self.soldier_engine.config.decision_cache_ttl + 0.5)
        
        # 第三次决策 (缓存过期)
        print("\n3️⃣ 缓存过期后的决策:")
        start_time = time.perf_counter()
        result3 = await self.soldier_engine.make_decision(symbol, market_data)
        latency3 = (time.perf_counter() - start_time) * 1000
        
        print(f"   决策: {result3['decision']['action']}")
        print(f"   延迟: {latency3:.2f}ms")
        print(f"   缓存命中: {self.soldier_engine.stats['cache_hits']}")
    
    async def demo_offline_mode(self):
        """演示离线模式"""
        print("📴 演示离线模式决策...")
        
        # 切换到离线模式
        self.soldier_engine.mode = SoldierMode.OFFLINE
        
        test_scenarios = [
            {
                "name": "看涨场景",
                "data": {"close": 150.0, "ma20": 145.0, "volume": 1200000, "avg_volume": 1000000}
            },
            {
                "name": "看跌场景", 
                "data": {"close": 140.0, "ma20": 145.0, "volume": 800000, "avg_volume": 1000000}
            },
            {
                "name": "震荡场景",
                "data": {"close": 145.0, "ma20": 145.0, "volume": 1000000, "avg_volume": 1000000}
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n📊 {scenario['name']}:")
            data = scenario['data']
            print(f"   价格: ${data['close']:.2f} (MA20: ${data['ma20']:.2f})")
            print(f"   成交量: {data['volume']:,} (平均: {data['avg_volume']:,})")
            
            result = await self.soldier_engine.make_decision("TEST", data)
            decision = result['decision']
            
            print(f"   🎯 离线决策: {decision['action'].upper()}")
            print(f"   🎯 置信度: {decision['confidence']:.2%}")
            print(f"   🎯 推理: {decision['reasoning']}")
            print(f"   ⚡ 延迟: {decision['latency_ms']:.2f}ms")
    
    async def demo_event_integration(self):
        """演示事件集成"""
        print("🔗 演示事件驱动集成...")
        
        # 模拟市场数据更新事件
        print("\n📡 模拟市场数据更新:")
        market_event = Event(
            event_type=EventType.MARKET_DATA_RECEIVED,
            source_module="market_data",
            target_module="soldier",
            priority=EventPriority.NORMAL,
            data={
                'symbol': 'AAPL',
                'market_data': {
                    'close': 155.0,
                    'volume': 1500000,
                    'timestamp': datetime.now().isoformat()
                }
            }
        )
        
        await self.soldier_engine._handle_market_data_update(market_event)
        print("   ✅ 市场数据已更新到短期记忆")
        
        # 检查短期记忆
        memory_key = "memory:AAPL"
        if memory_key in self.soldier_engine.short_term_memory:
            memory = self.soldier_engine.short_term_memory[memory_key]
            print(f"   📋 记忆内容: {memory['market_data']}")
        
        # 模拟Commander分析事件
        print("\n🧠 模拟Commander策略分析:")
        commander_event = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            source_module="commander",
            target_module="soldier",
            priority=EventPriority.NORMAL,
            data={
                'action': 'strategy_analysis_completed',
                'correlation_id': 'demo_123',
                'analysis_result': {
                    'strategy': 'momentum_following',
                    'confidence': 0.85,
                    'recommendation': 'buy',
                    'reasoning': 'Strong upward momentum detected'
                }
            }
        )
        
        await self.soldier_engine._handle_commander_analysis(commander_event)
        print("   ✅ Commander分析结果已接收")
        
        # 检查外部分析
        analysis_key = "commander:demo_123"
        if analysis_key in self.soldier_engine.external_analysis:
            analysis = self.soldier_engine.external_analysis[analysis_key]
            print(f"   📋 分析结果: {analysis}")
    
    async def demo_performance_monitoring(self):
        """演示性能监控"""
        print("📊 演示性能监控和统计...")
        
        # 执行多次决策以生成统计数据
        print("\n🔄 执行批量决策以生成统计数据...")
        
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
        latencies = []
        
        for i, symbol in enumerate(symbols):
            market_data = {
                "close": 100.0 + i * 10,
                "volume": 1000000 + i * 100000,
                "ma20": 95.0 + i * 10
            }
            
            start_time = time.perf_counter()
            result = await self.soldier_engine.make_decision(symbol, market_data)
            latency = (time.perf_counter() - start_time) * 1000
            latencies.append(latency)
            
            print(f"   {symbol}: {result['decision']['action']} ({latency:.2f}ms)")
        
        # 获取状态和统计
        status = await self.soldier_engine.get_status()
        
        print(f"\n📈 性能统计:")
        print(f"   总决策数: {status['stats']['total_decisions']}")
        print(f"   本地决策: {status['stats']['local_decisions']}")
        print(f"   云端决策: {status['stats']['cloud_decisions']}")
        print(f"   缓存命中: {status['stats']['cache_hits']}")
        print(f"   平均延迟: {status['stats']['avg_latency_ms']:.2f}ms")
        print(f"   P99延迟: {status['stats']['p99_latency_ms']:.2f}ms")
        print(f"   成功率: {status['stats']['success_rate']:.2%}")
        print(f"   模式切换: {status['stats']['mode_switches']}")
        
        print(f"\n💾 系统状态:")
        print(f"   当前模式: {status['mode']}")
        print(f"   运行状态: {status['state']}")
        print(f"   失败计数: {status['failure_count']}")
        print(f"   缓存大小: {status['cache_size']}")
        print(f"   内存大小: {status['memory_size']}")
        print(f"   Redis连接: {'✅' if status['redis_connected'] else '❌'}")
    
    async def demo_stress_test(self):
        """演示压力测试"""
        print("🔥 演示并发压力测试...")
        
        concurrent_requests = 10
        symbols = [f"STOCK_{i:03d}" for i in range(concurrent_requests)]
        
        print(f"\n⚡ 并发执行 {concurrent_requests} 个决策请求...")
        
        async def make_concurrent_decision(symbol):
            market_data = {
                "close": 100.0 + hash(symbol) % 100,
                "volume": 1000000 + hash(symbol) % 500000
            }
            
            start_time = time.perf_counter()
            result = await self.soldier_engine.make_decision(symbol, market_data)
            latency = (time.perf_counter() - start_time) * 1000
            
            return symbol, result['decision']['action'], latency
        
        # 并发执行
        start_time = time.perf_counter()
        tasks = [make_concurrent_decision(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        total_time = (time.perf_counter() - start_time) * 1000
        
        # 分析结果
        latencies = [result[2] for result in results]
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        print(f"\n📊 压力测试结果:")
        print(f"   并发请求数: {concurrent_requests}")
        print(f"   总耗时: {total_time:.2f}ms")
        print(f"   平均延迟: {avg_latency:.2f}ms")
        print(f"   最大延迟: {max_latency:.2f}ms")
        print(f"   最小延迟: {min_latency:.2f}ms")
        print(f"   吞吐量: {concurrent_requests / (total_time / 1000):.2f} 决策/秒")
        
        # 显示部分结果
        print(f"\n📋 部分决策结果:")
        for symbol, action, latency in results[:5]:
            print(f"   {symbol}: {action} ({latency:.2f}ms)")
    
    async def run_complete_demo(self):
        """运行完整演示"""
        print("=" * 60)
        print("🧠 Soldier引擎 v2.0 - 完整演示")
        print("=" * 60)
        
        try:
            # 1. 初始化
            await self.initialize()
            
            # 2. 正常模式决策演示
            await self.demo_normal_mode_decisions()
            
            # 3. 模式切换演示
            await self.demo_mode_switching()
            
            # 4. 决策缓存演示
            await self.demo_decision_caching()
            
            # 5. 离线模式演示
            await self.demo_offline_mode()
            
            # 6. 事件集成演示
            await self.demo_event_integration()
            
            # 7. 性能监控演示
            await self.demo_performance_monitoring()
            
            # 8. 压力测试演示
            await self.demo_stress_test()
            
            print("\n" + "=" * 60)
            print("🎉 演示完成！")
            print("=" * 60)
            
            # 最终状态
            final_status = await self.soldier_engine.get_status()
            print(f"📊 最终统计: 共执行 {final_status['stats']['total_decisions']} 次决策")
            print(f"⚡ 平均延迟: {final_status['stats']['avg_latency_ms']:.2f}ms")
            print(f"🎯 成功率: {final_status['stats']['success_rate']:.2%}")
            
            if final_status['stats']['avg_latency_ms'] < 20:
                print("✅ 性能要求达标 (< 20ms)")
            else:
                print("⚠️  性能要求未达标 (> 20ms)")
            
        except Exception as e:
            print(f"❌ 演示过程中发生错误: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """主函数"""
    demo = SoldierEngineDemo()
    await demo.run_complete_demo()


if __name__ == "__main__":
    # 设置事件循环策略 (Windows兼容)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())