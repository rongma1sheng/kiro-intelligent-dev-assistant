#!/usr/bin/env python3
"""
因子Arena三轨测试系统演示脚本

展示功能:
1. Arena系统初始化
2. 因子提交和测试
3. 三轨测试结果展示
4. 综合评分和认证
5. 统计信息查看
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.evolution.factor_arena import (
    FactorArenaSystem,
    ArenaTestConfig,
    TrackType,
    FactorStatus
)
from src.infra.event_bus import EventBus, Event, EventType, EventPriority
import json
from datetime import datetime


class FactorArenaDemo:
    """因子Arena演示类"""
    
    def __init__(self):
        self.arena_system = None
        self.event_bus = None
        
    async def initialize(self):
        """初始化演示环境"""
        print("🚀 初始化因子Arena三轨测试系统...")
        
        # 创建自定义配置
        config = ArenaTestConfig(
            reality_min_ic=0.04,           # 降低IC要求便于演示
            reality_min_sharpe=1.2,        # 降低夏普要求
            hell_min_survival_rate=0.6,    # 降低存活率要求
            min_markets_passed=2           # 保持跨市场要求
        )
        
        # 初始化Arena系统
        self.arena_system = FactorArenaSystem(config)
        
        # 模拟事件总线
        self.event_bus = EventBus()
        
        # 初始化系统
        await self.arena_system.initialize()
        
        print("✅ Arena系统初始化完成")
        print(f"   - Reality Track: IC > {config.reality_min_ic}, Sharpe > {config.reality_min_sharpe}")
        print(f"   - Hell Track: 存活率 > {config.hell_min_survival_rate}")
        print(f"   - Cross-Market Track: 通过市场数 >= {config.min_markets_passed}")
        print()
    
    async def demo_factor_submission(self):
        """演示因子提交"""
        print("📝 演示因子提交流程...")
        
        # 准备测试因子
        test_factors = [
            {
                'expression': 'momentum_20d',
                'description': '20日动量因子',
                'metadata': {'category': 'momentum', 'lookback': 20}
            },
            {
                'expression': 'mean_reversion_5d',
                'description': '5日均值回归因子',
                'metadata': {'category': 'reversal', 'lookback': 5}
            },
            {
                'expression': 'volatility_factor',
                'description': '波动率因子',
                'metadata': {'category': 'risk', 'lookback': 20}
            }
        ]
        
        task_ids = []
        
        for factor in test_factors:
            print(f"   提交因子: {factor['description']} ({factor['expression']})")
            
            task_id = await self.arena_system.submit_factor_for_testing(
                factor['expression'],
                factor['metadata']
            )
            
            task_ids.append((task_id, factor))
            print(f"   ✅ 任务ID: {task_id}")
        
        print(f"\n📊 已提交 {len(task_ids)} 个因子进行测试")
        return task_ids
    
    async def demo_test_monitoring(self, task_ids):
        """演示测试监控"""
        print("🔍 监控测试进度...")
        
        # 等待测试开始
        await asyncio.sleep(1)
        
        for task_id, factor in task_ids:
            print(f"\n📈 因子: {factor['description']}")
            
            status = await self.arena_system.get_test_status(task_id)
            
            print(f"   状态: {status['status']}")
            print(f"   提交时间: {status['submit_time']}")
            
            if status.get('completion_time'):
                print(f"   完成时间: {status['completion_time']}")
            
            if status.get('error'):
                print(f"   ❌ 错误: {status['error']}")
    
    async def demo_test_execution(self):
        """演示测试执行过程"""
        print("⚡ 演示单个因子的完整测试流程...")
        
        factor_expression = "demo_momentum_factor"
        
        print(f"🧪 测试因子: {factor_expression}")
        
        # Reality Track 测试
        print("\n1️⃣ Reality Track - 真实历史数据测试")
        reality_track = self.arena_system.reality_track
        reality_result = await reality_track.test_factor(factor_expression)
        
        self._display_reality_result(reality_result)
        
        # Hell Track 测试
        print("\n2️⃣ Hell Track - 极端市场环境测试")
        hell_track = self.arena_system.hell_track
        hell_result = await hell_track.test_factor(factor_expression)
        
        self._display_hell_result(hell_result)
        
        # Cross-Market Track 测试
        print("\n3️⃣ Cross-Market Track - 跨市场适应性测试")
        cross_market_track = self.arena_system.cross_market_track
        cross_market_result = await cross_market_track.test_factor(factor_expression)
        
        self._display_cross_market_result(cross_market_result)
        
        # 综合评分
        print("\n🏆 综合评分计算")
        results = [reality_result, hell_result, cross_market_result]
        overall_result = self.arena_system._calculate_overall_score(results)
        
        self._display_overall_result(overall_result)
        
        return overall_result
    
    def _display_reality_result(self, result):
        """显示Reality Track结果"""
        print(f"   📊 IC均值: {result.ic_mean:.4f}")
        print(f"   📊 IC标准差: {result.ic_std:.4f}")
        print(f"   📊 信息比率: {result.ir:.4f}")
        print(f"   📊 夏普比率: {result.sharpe_ratio:.4f}")
        print(f"   📊 最大回撤: {result.max_drawdown:.4f}")
        print(f"   📊 年化收益: {result.annual_return:.4f}")
        print(f"   📊 胜率: {result.win_rate:.4f}")
        
        if result.passed:
            print("   ✅ Reality Track 通过")
        else:
            print("   ❌ Reality Track 未通过")
            
        if result.error_message:
            print(f"   ⚠️  错误: {result.error_message}")
    
    def _display_hell_result(self, result):
        """显示Hell Track结果"""
        print(f"   🔥 存活率: {result.survival_rate:.4f}")
        print(f"   🔥 IC衰减率: {result.ic_decay_rate:.4f}")
        print(f"   🔥 恢复能力: {result.recovery_ability:.4f}")
        print(f"   🔥 压力得分: {result.stress_score:.2f}")
        
        if result.passed:
            print("   ✅ Hell Track 通过")
        else:
            print("   ❌ Hell Track 未通过")
            
        if result.detailed_metrics and 'scenario_results' in result.detailed_metrics:
            print("   📋 各场景表现:")
            for scenario, metrics in result.detailed_metrics['scenario_results'].items():
                print(f"      {scenario}: 存活率={metrics['survival_rate']:.3f}")
    
    def _display_cross_market_result(self, result):
        """显示Cross-Market Track结果"""
        print(f"   🌍 通过市场数: {result.markets_passed}/4")
        print(f"   🌍 适应性评分: {result.adaptability_score:.4f}")
        print(f"   🌍 一致性评分: {result.consistency_score:.4f}")
        
        if result.passed:
            print("   ✅ Cross-Market Track 通过")
        else:
            print("   ❌ Cross-Market Track 未通过")
            
        if result.detailed_metrics and 'market_results' in result.detailed_metrics:
            print("   📋 各市场表现:")
            for market, metrics in result.detailed_metrics['market_results'].items():
                print(f"      {market}: IC={metrics['ic_mean']:.4f}, Sharpe={metrics['sharpe_ratio']:.2f}")
    
    def _display_overall_result(self, overall_result):
        """显示综合评分结果"""
        print(f"   🎯 综合得分: {overall_result['score']:.2f}/100")
        print(f"   🎯 Reality得分: {overall_result['reality_score']:.2f}")
        print(f"   🎯 Hell得分: {overall_result['hell_score']:.2f}")
        print(f"   🎯 Cross-Market得分: {overall_result['cross_market_score']:.2f}")
        
        if overall_result['passed']:
            print("   ✅ 综合测试通过")
        else:
            print("   ❌ 综合测试未通过")
            
        if overall_result['certification_eligible']:
            print("   🏅 符合Z2H基因胶囊认证条件")
        else:
            print("   ⏳ 暂不符合Z2H认证条件")
    
    async def demo_arena_statistics(self):
        """演示Arena统计信息"""
        print("📈 Arena系统统计信息...")
        
        stats = await self.arena_system.get_arena_stats()
        
        print("\n📊 测试统计:")
        test_stats = stats['stats']
        print(f"   总测试因子数: {test_stats['total_factors_tested']}")
        print(f"   通过因子数: {test_stats['factors_passed']}")
        print(f"   失败因子数: {test_stats['factors_failed']}")
        print(f"   认证因子数: {test_stats['factors_certified']}")
        print(f"   平均测试时间: {test_stats['avg_test_time_minutes']:.2f} 分钟")
        
        print("\n📊 通过率统计:")
        print(f"   Reality Track 通过率: {test_stats['reality_pass_rate']:.2%}")
        print(f"   Hell Track 通过率: {test_stats['hell_pass_rate']:.2%}")
        print(f"   Cross-Market Track 通过率: {test_stats['cross_market_pass_rate']:.2%}")
        
        print("\n📊 当前状态:")
        current_status = stats['current_status']
        print(f"   系统运行状态: {'🟢 运行中' if current_status['is_running'] else '🔴 已停止'}")
        print(f"   等待测试因子: {current_status['pending_factors']}")
        print(f"   正在测试因子: {current_status['testing_factors']}")
        print(f"   已完成测试: {current_status['completed_tests']}")
    
    async def demo_performance_analysis(self):
        """演示性能分析"""
        print("⚡ Arena系统性能分析...")
        
        # 测试并发性能
        print("\n🚀 并发测试性能:")
        
        start_time = asyncio.get_event_loop().time()
        
        # 同时提交多个因子
        concurrent_factors = [
            f"perf_test_factor_{i}" for i in range(5)
        ]
        
        tasks = []
        for factor in concurrent_factors:
            task = asyncio.create_task(
                self.arena_system.submit_factor_for_testing(factor)
            )
            tasks.append(task)
        
        task_ids = await asyncio.gather(*tasks)
        
        end_time = asyncio.get_event_loop().time()
        
        print(f"   提交 {len(concurrent_factors)} 个因子耗时: {(end_time - start_time)*1000:.2f} ms")
        print(f"   平均每个因子: {(end_time - start_time)*1000/len(concurrent_factors):.2f} ms")
        
        # 等待一些测试完成
        await asyncio.sleep(2)
        
        # 检查系统负载
        stats = await self.arena_system.get_arena_stats()
        current_status = stats['current_status']
        
        print(f"   当前系统负载:")
        print(f"     - 等待队列: {current_status['pending_factors']} 个因子")
        print(f"     - 测试中: {current_status['testing_factors']} 个因子")
        print(f"     - 并发限制: {self.arena_system.max_concurrent_tests} 个")
    
    async def demo_event_integration(self):
        """演示事件集成"""
        print("🔗 演示事件驱动集成...")
        
        # 模拟外部系统发送因子发现事件
        print("\n📡 模拟遗传算法发现新因子:")
        
        factor_discovered_event = Event(
            event_type=EventType.FACTOR_DISCOVERED,
            source_module="genetic_miner",
            target_module="factor_arena",
            priority=EventPriority.HIGH,
            data={
                'action': 'submit_to_arena',
                'factor_expression': 'genetic_discovered_factor',
                'metadata': {
                    'source': 'genetic_algorithm',
                    'generation': 42,
                    'fitness_score': 0.85,
                    'discovery_time': datetime.now().isoformat()
                }
            }
        )
        
        print(f"   发送事件: {factor_discovered_event.event_type}")
        print(f"   因子表达式: {factor_discovered_event.data['factor_expression']}")
        
        # 处理事件
        await self.arena_system._handle_factor_submission(factor_discovered_event)
        
        print("   ✅ 事件处理完成，因子已加入测试队列")
        
        # 检查因子是否在队列中
        found_factor = False
        for task_info in self.arena_system.testing_factors.values():
            if task_info['factor_expression'] == 'genetic_discovered_factor':
                found_factor = True
                print(f"   📋 因子状态: {task_info['status'].value}")
                print(f"   📋 元数据: {task_info['metadata']}")
                break
        
        if not found_factor:
            print("   ⚠️  因子未在测试队列中找到")
    
    async def run_complete_demo(self):
        """运行完整演示"""
        print("=" * 60)
        print("🏟️  因子Arena三轨测试系统 - 完整演示")
        print("=" * 60)
        
        try:
            # 1. 初始化
            await self.initialize()
            
            # 2. 因子提交演示
            task_ids = await self.demo_factor_submission()
            
            # 3. 测试监控演示
            await self.demo_test_monitoring(task_ids)
            
            # 4. 完整测试流程演示
            overall_result = await self.demo_test_execution()
            
            # 5. 统计信息演示
            await self.demo_arena_statistics()
            
            # 6. 性能分析演示
            await self.demo_performance_analysis()
            
            # 7. 事件集成演示
            await self.demo_event_integration()
            
            print("\n" + "=" * 60)
            print("🎉 演示完成！")
            print("=" * 60)
            
            # 最终统计
            final_stats = await self.arena_system.get_arena_stats()
            print(f"📊 最终统计: 共测试 {final_stats['stats']['total_factors_tested']} 个因子")
            
            if overall_result['certification_eligible']:
                print("🏅 发现了符合Z2H认证条件的优质因子！")
            
        except Exception as e:
            print(f"❌ 演示过程中发生错误: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """主函数"""
    demo = FactorArenaDemo()
    await demo.run_complete_demo()


if __name__ == "__main__":
    # 设置事件循环策略 (Windows兼容)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())