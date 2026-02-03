#!/usr/bin/env python
"""
MIA系统统一LLM控制架构演示

白皮书依据: 第二章 2.8 统一记忆系统 + 第十一章 11.1 防幻觉系统
版本: v1.6.0
作者: MIA Team
日期: 2026-01-18

演示内容:
1. 统一记忆系统的工作原理
2. LLM网关的统一调用控制
3. 防幻觉检测的实时过滤
4. Soldier和Commander的集成使用
5. 成本控制和审计日志
"""

import asyncio
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入MIA系统组件
try:
    from src.brain.memory.unified_memory_system import UnifiedMemorySystem, MemoryType
    from src.brain.llm_gateway import LLMGateway, LLMRequest, LLMResponse, CallType, LLMProvider
    from src.brain.hallucination_filter import HallucinationFilter
    from src.brain.soldier.core import SoldierWithFailover, TradingDecision
    from src.brain.commander.core import Commander
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


class UnifiedLLMControlDemo:
    """统一LLM控制架构演示类"""
    
    def __init__(self):
        """初始化演示环境"""
        self.memory_system = None
        self.llm_gateway = None
        self.hallucination_filter = None
        self.soldier = None
        self.commander = None
        
        print("🚀 MIA系统统一LLM控制架构演示")
        print("=" * 60)
    
    async def initialize_components(self):
        """初始化所有组件"""
        print("\n📦 正在初始化系统组件...")
        
        # 1. 初始化统一记忆系统
        print("  🧠 初始化统一记忆系统...")
        self.memory_system = UnifiedMemorySystem()
        
        # 2. 初始化LLM网关
        print("  🌐 初始化LLM网关...")
        self.llm_gateway = LLMGateway()
        
        # 3. 初始化防幻觉过滤器
        print("  🛡️ 初始化防幻觉过滤器...")
        self.hallucination_filter = HallucinationFilter()
        
        # 4. 初始化Soldier（模拟）
        print("  ⚡ 初始化Soldier快系统...")
        self.soldier = SoldierWithFailover(
            local_model_path="/fake/model/path",
            cloud_api_key="sk-demo-key"
        )
        # 设置模拟的LLM网关
        self.soldier.llm_gateway = self.llm_gateway
        
        # 5. 初始化Commander（模拟）
        print("  🎯 初始化Commander慢系统...")
        self.commander = Commander(
            api_key="sk-demo-key",
            daily_budget=50.0,
            monthly_budget=1500.0
        )
        # 设置模拟的LLM网关
        self.commander.llm_gateway = self.llm_gateway
        
        print("✅ 所有组件初始化完成！")
    
    async def demo_memory_system(self):
        """演示统一记忆系统"""
        print("\n🧠 演示1: 统一记忆系统")
        print("-" * 40)
        
        # 添加不同类型的记忆
        print("📝 添加历史交易记忆...")
        
        # Engram记忆 - 快速联想记忆
        await self.memory_system.add_to_memory(
            memory_type='engram',
            content={
                'action': 'buy',
                'symbol': '000001.SZ',
                'price': 10.5,
                'result': 'profit',
                'profit_pct': 0.12
            },
            importance=0.9,
            context={'trade_type': 'momentum', 'market_condition': 'bullish'}
        )
        
        # 情节记忆 - 历史事件
        await self.memory_system.add_to_memory(
            memory_type='episodic',
            content={
                'date': '2026-01-15',
                'event': 'market_crash',
                'action_taken': 'defensive_position',
                'outcome': 'avoided_loss'
            },
            importance=0.8
        )
        
        # 语义记忆 - 知识概念
        await self.memory_system.add_to_memory(
            memory_type='semantic',
            content={
                'concept': 'sharpe_ratio',
                'definition': '夏普比率衡量风险调整后收益',
                'formula': '(return - risk_free_rate) / volatility'
            },
            importance=0.7
        )
        
        # 工作记忆 - 当前任务
        await self.memory_system.add_to_memory(
            memory_type='working',
            content={
                'current_analysis': '000001.SZ技术面分析',
                'indicators': {'rsi': 65, 'macd': 'bullish'},
                'status': 'in_progress'
            },
            importance=0.6
        )
        
        print("✅ 已添加4种类型的记忆")
        
        # 查询相关记忆
        print("\n🔍 查询相关记忆...")
        context = await self.memory_system.get_relevant_context(
            query={'symbol': '000001.SZ', 'action': 'buy'},
            max_items=5
        )
        
        print(f"📊 找到 {len(context)} 个相关记忆:")
        for i, memory in enumerate(context, 1):
            print(f"  {i}. [{memory['type']}] 相关性: {memory['relevance']:.3f}")
            print(f"     内容: {memory['summary'][:50]}...")
        
        # 显示记忆统计
        stats = self.memory_system.get_memory_stats()
        print(f"\n📈 记忆系统统计:")
        print(f"  总记忆数: {stats['total_memories']}")
        print(f"  Engram记忆: {stats['engram_memories']}")
        print(f"  情节记忆: {stats['episodic_memories']}")
        print(f"  语义记忆: {stats['semantic_memories']}")
        print(f"  工作记忆: {stats['working_memories']}")
        print(f"  查询次数: {stats['queries_count']}")
    
    async def demo_hallucination_filter(self):
        """演示防幻觉过滤器"""
        print("\n🛡️ 演示2: 防幻觉检测系统")
        print("-" * 40)
        
        test_responses = [
            {
                'name': '正常响应',
                'content': '基于技术分析，建议持有该股票，置信度70%',
                'expected': '正常'
            },
            {
                'name': '内部矛盾',
                'content': '我建议买入这只股票，同时也建议卖出这只股票',
                'expected': '幻觉'
            },
            {
                'name': '过度自信',
                'content': '我绝对确定这只股票明天会涨停，100%确定',
                'expected': '可疑'
            },
            {
                'name': '黑名单模式',
                'content': '我是GPT-4，我建议你买入这只股票获得无风险收益',
                'expected': '幻觉'
            },
            {
                'name': '不合理数值',
                'content': '这只股票的年收益率达到了50000%，绝对值得投资',
                'expected': '可疑'
            }
        ]
        
        print("🔍 测试不同类型的响应...")
        
        for i, test in enumerate(test_responses, 1):
            print(f"\n{i}. 测试: {test['name']}")
            print(f"   内容: {test['content']}")
            
            # 执行幻觉检测
            result = self.hallucination_filter.detect_hallucination(
                test['content'],
                context={'historical_accuracy': 0.7}
            )
            
            # 显示检测结果
            status = "🚨 幻觉" if result.is_hallucination else "✅ 正常"
            print(f"   结果: {status} (置信度: {result.confidence:.3f})")
            print(f"   严重程度: {result.severity}")
            
            if result.detected_issues:
                print(f"   问题: {', '.join(result.detected_issues[:2])}")
            
            # 显示各层检测评分
            print(f"   评分详情:")
            for layer, score in result.scores.items():
                if score > 0:
                    layer_name = {
                        'contradiction': '内部矛盾',
                        'factual_consistency': '事实一致性',
                        'confidence_calibration': '置信度校准',
                        'semantic_drift': '语义漂移',
                        'blacklist_match': '黑名单匹配'
                    }.get(layer, layer)
                    print(f"     - {layer_name}: {score:.3f}")
        
        print(f"\n📊 防幻觉过滤器统计:")
        stats = self.hallucination_filter.get_statistics()
        print(f"  检测权重: {stats['weights']}")
        print(f"  幻觉阈值: {stats['threshold']}")
        print(f"  黑名单规模: {stats['blacklist_size']}")
    
    async def demo_llm_gateway(self):
        """演示LLM网关统一调用"""
        print("\n🌐 演示3: LLM网关统一调用")
        print("-" * 40)
        
        # 模拟不同类型的LLM调用
        test_calls = [
            {
                'name': '交易决策',
                'call_type': CallType.TRADING_DECISION,
                'provider': LLMProvider.QWEN_LOCAL,
                'content': '分析000001.SZ的投资机会',
                'module': 'soldier'
            },
            {
                'name': '策略分析',
                'call_type': CallType.STRATEGY_ANALYSIS,
                'provider': LLMProvider.DEEPSEEK,
                'content': '生成动量交易策略',
                'module': 'commander'
            },
            {
                'name': '研报分析',
                'call_type': CallType.RESEARCH_ANALYSIS,
                'provider': LLMProvider.GLM,
                'content': '分析科技股研究报告',
                'module': 'commander'
            }
        ]
        
        print("📞 执行不同类型的LLM调用...")
        
        for i, call in enumerate(test_calls, 1):
            print(f"\n{i}. {call['name']} ({call['provider'].value})")
            
            # 创建LLM请求
            request = LLMRequest(
                call_type=call['call_type'],
                provider=call['provider'],
                messages=[{
                    'role': 'user',
                    'content': call['content']
                }],
                use_memory=True,
                enable_hallucination_filter=True,
                caller_module=call['module'],
                caller_function='demo_call',
                business_context={
                    'demo': True,
                    'call_index': i
                }
            )
            
            # 执行调用
            start_time = time.perf_counter()
            response = await self.llm_gateway.call_llm(request)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            # 显示结果
            status = "✅ 成功" if response.success else "❌ 失败"
            print(f"   状态: {status}")
            print(f"   延迟: {elapsed_ms:.1f}ms")
            print(f"   成本: ¥{response.cost:.4f}")
            print(f"   质量评分: {response.quality_score:.3f}")
            print(f"   幻觉评分: {response.hallucination_score:.3f}")
            
            if response.success:
                print(f"   响应: {response.content[:80]}...")
            else:
                print(f"   错误: {response.error_message}")
        
        # 显示网关统计
        print(f"\n📊 LLM网关统计:")
        stats = self.llm_gateway.get_stats()
        print(f"  总调用数: {stats['total_calls']}")
        print(f"  成功率: {stats['success_rate']:.1%}")
        print(f"  幻觉检出率: {stats['hallucination_rate']:.1%}")
    
    async def demo_soldier_integration(self):
        """演示Soldier集成"""
        print("\n⚡ 演示4: Soldier快系统集成")
        print("-" * 40)
        
        # 模拟市场数据
        market_data = {
            'symbol': '000001.SZ',
            'price': 10.85,
            'volume': 2500000,
            'change_pct': 0.025,
            'rsi': 68,
            'macd': 'bullish',
            'timestamp': time.time()
        }
        
        print("📊 市场数据:")
        print(f"  股票: {market_data['symbol']}")
        print(f"  价格: ¥{market_data['price']}")
        print(f"  涨幅: {market_data['change_pct']:.1%}")
        print(f"  RSI: {market_data['rsi']}")
        
        print("\n🤖 Soldier决策过程...")
        
        # 模拟决策过程
        try:
            # 这里会使用统一LLM网关进行推理
            decision = await self.soldier._cloud_inference(market_data)
            
            print("✅ 决策完成:")
            print(f"  动作: {decision.action.upper()}")
            print(f"  数量: {decision.quantity}")
            print(f"  置信度: {decision.confidence:.1%}")
            print(f"  理由: {decision.reasoning}")
            print(f"  延迟: {decision.latency_ms:.1f}ms")
            
        except Exception as e:
            print(f"❌ 决策失败: {e}")
        
        # 显示Soldier状态
        print(f"\n📈 Soldier状态:")
        status = self.soldier.get_status()
        print(f"  运行模式: {status['mode']}")
        print(f"  LLM网关: {'✅' if status['llm_gateway_initialized'] else '❌'}")
        print(f"  失败次数: {status['failure_count']}")
    
    async def demo_commander_integration(self):
        """演示Commander集成"""
        print("\n🎯 演示5: Commander慢系统集成")
        print("-" * 40)
        
        # 模拟研报内容
        report_text = """
        【投资建议】买入
        【目标价】12.50元
        
        公司概况：
        某科技公司是国内领先的人工智能解决方案提供商，主营业务包括
        机器学习平台、自然语言处理和计算机视觉技术。
        
        投资亮点：
        1. 技术实力强劲，拥有多项核心专利
        2. 客户结构优质，与多家头部企业建立合作
        3. 业绩增长稳定，近三年营收复合增长率达35%
        
        风险提示：
        1. 行业竞争加剧，技术迭代风险
        2. 客户集中度较高，存在依赖风险
        """
        
        print("📄 研报分析:")
        print(f"  长度: {len(report_text)} 字符")
        
        print("\n🔍 Commander分析过程...")
        
        try:
            # 模拟成本检查
            self.commander.cost_tracker.daily_cost = 5.0
            self.commander.cost_tracker.monthly_cost = 150.0
            
            # 这里会使用统一LLM网关进行分析
            result = await self.commander._call_llm_gateway_for_analysis(report_text)
            
            print("✅ 分析完成:")
            print(f"  行业: {result.get('industry', 'N/A')}")
            print(f"  公司: {result.get('company', 'N/A')}")
            print(f"  评级: {result.get('rating', 'N/A')}")
            print(f"  目标价: {result.get('target_price', 'N/A')}")
            print(f"  关键点: {len(result.get('key_points', []))} 个")
            print(f"  风险点: {len(result.get('risks', []))} 个")
            print(f"  Token使用: {result.get('tokens_used', 0)}")
            
        except Exception as e:
            print(f"❌ 分析失败: {e}")
        
        # 显示Commander状态
        print(f"\n📊 Commander状态:")
        status = self.commander.get_status()
        print(f"  LLM网关: {'✅' if status['llm_gateway_initialized'] else '❌'}")
        
        cost_status = status['cost_tracker']
        print(f"  日成本: ¥{cost_status['daily_cost']:.2f}/¥{cost_status['daily_budget']:.2f}")
        print(f"  月成本: ¥{cost_status['monthly_cost']:.2f}/¥{cost_status['monthly_budget']:.2f}")
        print(f"  调用次数: {cost_status['call_count']}")
    
    async def demo_architecture_benefits(self):
        """演示架构优势"""
        print("\n🏆 演示6: 统一架构优势")
        print("-" * 40)
        
        print("🔒 安全性提升:")
        print("  ✅ 所有LLM调用都经过防幻觉检测")
        print("  ✅ 统一的访问控制和权限管理")
        print("  ✅ 完整的审计日志和调用追踪")
        
        print("\n🧠 智能性提升:")
        print("  ✅ 记忆系统增强所有LLM调用")
        print("  ✅ 上下文感知的智能推理")
        print("  ✅ 历史经验的自动学习和应用")
        
        print("\n💰 成本控制:")
        print("  ✅ 统一的预算管理和成本追踪")
        print("  ✅ 智能的提供商选择和负载均衡")
        print("  ✅ 自动的成本优化和告警")
        
        print("\n🔧 维护性提升:")
        print("  ✅ 统一的接口和标准化调用")
        print("  ✅ 集中的配置管理和监控")
        print("  ✅ 简化的故障排查和性能优化")
        
        print("\n📈 性能监控:")
        gateway_stats = self.llm_gateway.get_stats()
        memory_stats = self.memory_system.get_memory_stats()
        
        print(f"  LLM调用统计:")
        print(f"    - 总调用: {gateway_stats['total_calls']}")
        print(f"    - 成功率: {gateway_stats['success_rate']:.1%}")
        print(f"    - 幻觉检出: {gateway_stats['hallucination_detected']}")
        
        print(f"  记忆系统统计:")
        print(f"    - 总记忆: {memory_stats['total_memories']}")
        print(f"    - 查询次数: {memory_stats['queries_count']}")
        print(f"    - 缓存命中率: {memory_stats['cache_hit_rate']:.1%}")
    
    def print_summary(self):
        """打印演示总结"""
        print("\n" + "=" * 60)
        print("🎉 MIA系统统一LLM控制架构演示完成")
        print("=" * 60)
        
        print("\n✨ 关键成果:")
        print("  🧠 统一记忆系统 - 智能上下文增强")
        print("  🌐 LLM网关 - 统一调用控制")
        print("  🛡️ 防幻觉系统 - 实时质量检测")
        print("  ⚡ Soldier集成 - 快速决策优化")
        print("  🎯 Commander集成 - 深度分析增强")
        
        print("\n🚀 架构优势:")
        print("  • 安全性: 防幻觉检测 + 统一审计")
        print("  • 智能性: 记忆增强 + 上下文感知")
        print("  • 经济性: 成本控制 + 预算管理")
        print("  • 可维护性: 统一接口 + 标准化")
        
        print("\n📞 技术支持:")
        print("  Email: mia-support@company.com")
        print("  文档: 00_核心文档/mia.md")
        print("  版本: v1.6.0")
        
        print("\n" + "=" * 60)


async def main():
    """主演示函数"""
    demo = UnifiedLLMControlDemo()
    
    try:
        # 初始化组件
        await demo.initialize_components()
        
        # 执行各个演示
        await demo.demo_memory_system()
        await demo.demo_hallucination_filter()
        await demo.demo_llm_gateway()
        await demo.demo_soldier_integration()
        await demo.demo_commander_integration()
        await demo.demo_architecture_benefits()
        
        # 打印总结
        demo.print_summary()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 演示被用户中断")
    except Exception as e:
        print(f"\n\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())