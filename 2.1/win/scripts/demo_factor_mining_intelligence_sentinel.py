#!/usr/bin/env python
"""
MIA系统因子挖掘智能哨兵演示脚本

白皮书依据: 第二章 2.6 FactorMining Intelligence Sentinel
版本: v1.6.0
作者: MIA Team
日期: 2026-01-18

演示功能:
1. 智能哨兵初始化和配置
2. 模拟学术论文发现和分析
3. 自动因子实现和验证
4. 手动发现输入和处理
5. 发现统计和查询
6. 因子库集成展示
"""

import asyncio
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
from typing import Dict, Any

# 添加项目根目录到路径
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.evolution.factor_mining_intelligence_sentinel import (
    FactorMiningIntelligenceSentinel,
    FactorDiscovery,
    DiscoveryType,
    FactorCategory,
    ValidationStatus
)
from src.brain.llm_gateway import LLMGateway


class FactorMiningIntelligenceSentinelDemo:
    """因子挖掘智能哨兵演示类"""
    
    def __init__(self):
        """初始化演示"""
        self.temp_dir = tempfile.mkdtemp()
        self.sentinel = None
        print("🚀 MIA因子挖掘智能哨兵演示系统")
        print("=" * 60)
        print("核心理念: 让MIA在因子挖掘领域永远保持前沿")
        print("=" * 60)
    
    def __del__(self):
        """清理临时目录"""
        if hasattr(self, 'temp_dir') and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    async def initialize_sentinel(self):
        """初始化智能哨兵"""
        print("\n📡 初始化因子挖掘智能哨兵...")
        
        # 创建LLM网关实例
        llm_gateway = LLMGateway()
        
        # 创建哨兵实例
        self.sentinel = FactorMiningIntelligenceSentinel(
            llm_gateway=llm_gateway,
            discovery_storage_path=self.temp_dir
        )
        
        # 设置事件处理器
        await self.sentinel.setup_event_handlers()
        
        print(f"✅ 哨兵初始化完成")
        print(f"   📁 存储路径: {self.temp_dir}")
        print(f"   🔍 监控源数量: {len(self.sentinel.monitoring_sources)}")
        print(f"   🧠 模型配置: {len(self.sentinel.model_configs)} 个")
        
        # 显示监控源配置
        print("\n🎯 监控源配置:")
        for source_name, config in self.sentinel.monitoring_sources.items():
            priority = config.get('priority', 'unknown')
            interval = config.get('check_interval', 0) // 3600
            print(f"   • {source_name}: 优先级={priority}, 检查间隔={interval}小时")
        
        # 显示模型配置
        print("\n🤖 AI模型配置:")
        for model_name, config in self.sentinel.model_configs.items():
            model = config['model']
            role = config['role']
            print(f"   • {model_name}: {model} - {role}")
    
    async def demonstrate_academic_discovery(self):
        """演示学术论文发现"""
        print("\n📚 学术论文发现演示...")
        
        # 模拟发现学术论文
        mock_papers = [
            {
                'title': 'ESG Momentum: Sustainable Alpha in Factor Investing',
                'abstract': 'We investigate the relationship between ESG momentum and stock returns, finding significant alpha generation potential through sustainable factor construction...',
                'authors': ['Chen, L.', 'Wang, M.', 'Liu, J.'],
                'published': '2026-01-18',
                'url': 'https://arxiv.org/abs/2601.12345',
                'category': FactorCategory.SENTIMENT
            },
            {
                'title': 'Cross-Asset Momentum Spillovers in Alternative Data',
                'abstract': 'Using satellite imagery and social media sentiment, we construct cross-asset momentum factors that capture spillover effects between equity and commodity markets...',
                'authors': ['Smith, A.', 'Johnson, B.'],
                'published': '2026-01-17',
                'url': 'https://arxiv.org/abs/2601.12346',
                'category': FactorCategory.ALTERNATIVE
            },
            {
                'title': 'High-Frequency Technical Patterns with Deep Learning',
                'abstract': 'We apply transformer networks to identify high-frequency technical patterns that predict short-term price movements with superior accuracy...',
                'authors': ['Zhang, K.', 'Brown, R.'],
                'published': '2026-01-16',
                'url': 'https://arxiv.org/abs/2601.12347',
                'category': FactorCategory.TECHNICAL
            }
        ]
        
        print(f"🔍 扫描到 {len(mock_papers)} 篇相关论文:")
        
        for i, paper in enumerate(mock_papers, 1):
            print(f"\n   📄 论文 {i}: {paper['title']}")
            print(f"      作者: {', '.join(paper['authors'])}")
            print(f"      发布: {paper['published']}")
            print(f"      摘要: {paper['abstract'][:100]}...")
            
            # 创建发现记录
            discovery = FactorDiscovery(
                discovery_id="",
                discovery_type=DiscoveryType.ACADEMIC_PAPER,
                factor_category=paper['category'],
                title=paper['title'],
                description=f"基于论文《{paper['title']}》的因子发现",
                source=paper['url'],
                discovered_at=datetime.now(),
                discoverer='system',
                theoretical_basis=paper['abstract'],
                expected_alpha=np.random.uniform(0.02, 0.08),
                tags=['academic', 'arxiv', '2026'],
                confidence_score=np.random.uniform(0.7, 0.95)
            )
            
            # 处理发现
            await self.sentinel._process_new_discovery(discovery)
            
            print(f"      ✅ 发现已记录 (ID: {discovery.discovery_id})")
            print(f"      📊 置信度: {discovery.confidence_score:.2f}")
            print(f"      🎯 预期Alpha: {discovery.expected_alpha:.3f}")
    
    async def demonstrate_alternative_data_discovery(self):
        """演示替代数据发现"""
        print("\n🛰️ 替代数据源发现演示...")
        
        # 模拟替代数据源发现
        mock_data_sources = [
            {
                'name': 'Corporate Earnings Call Sentiment Analysis',
                'description': '基于自然语言处理的企业财报电话会议情绪分析，实时捕捉管理层信心变化',
                'data_type': 'text_sentiment',
                'update_frequency': 'quarterly',
                'coverage': 'S&P 500 + A股主要公司',
                'potential_alpha': 0.045,
                'complexity': 'medium'
            },
            {
                'name': 'Supply Chain Disruption Satellite Monitor',
                'description': '利用卫星图像监控全球供应链关键节点，预测供应链中断对股价的影响',
                'data_type': 'satellite_imagery',
                'update_frequency': 'daily',
                'coverage': 'Global Manufacturing Hubs',
                'potential_alpha': 0.035,
                'complexity': 'high'
            },
            {
                'name': 'Social Media Brand Sentiment Tracker',
                'description': '跟踪社交媒体上品牌提及和情绪变化，预测消费者行为对股价的影响',
                'data_type': 'social_media',
                'update_frequency': 'real-time',
                'coverage': 'Consumer Brands',
                'potential_alpha': 0.028,
                'complexity': 'low'
            }
        ]
        
        print(f"🔍 发现 {len(mock_data_sources)} 个新的替代数据源:")
        
        for i, data_source in enumerate(mock_data_sources, 1):
            print(f"\n   📡 数据源 {i}: {data_source['name']}")
            print(f"      描述: {data_source['description']}")
            print(f"      类型: {data_source['data_type']}")
            print(f"      更新频率: {data_source['update_frequency']}")
            print(f"      覆盖范围: {data_source['coverage']}")
            print(f"      预期Alpha: {data_source['potential_alpha']:.3f}")
            print(f"      实现复杂度: {data_source['complexity']}")
            
            # 创建发现记录
            discovery = FactorDiscovery(
                discovery_id="",
                discovery_type=DiscoveryType.ALTERNATIVE_DATA,
                factor_category=FactorCategory.ALTERNATIVE,
                title=f"新数据源: {data_source['name']}",
                description=data_source['description'],
                source="内部数据发现系统",
                discovered_at=datetime.now(),
                discoverer='system',
                theoretical_basis="替代数据与股票收益的相关性分析",
                expected_alpha=data_source['potential_alpha'],
                data_requirements=[data_source['data_type']],
                implementation_complexity=data_source['complexity'],
                tags=['alternative_data', 'new_source', data_source['data_type']],
                confidence_score=0.75
            )
            
            # 处理发现
            await self.sentinel._process_new_discovery(discovery)
            
            print(f"      ✅ 数据源已记录 (ID: {discovery.discovery_id})")
    
    async def demonstrate_market_anomaly_detection(self):
        """演示市场异象发现"""
        print("\n🔍 市场异象发现演示...")
        
        # 模拟市场异象发现
        mock_anomalies = [
            {
                'pattern': 'Post-Earnings Announcement Drift Enhancement',
                'description': '在高VIX环境下，小盘股的盈利公告后漂移效应显著增强，持续期延长至5-7个交易日',
                'strength': 0.042,
                'persistence': '5-7 trading days',
                'conditions': ['small_cap', 'high_vix', 'earnings_surprise > 5%'],
                'market_regime': 'high_volatility'
            },
            {
                'pattern': 'Cross-Sectional Reversal in Tech Stocks',
                'description': '科技股在月末最后3个交易日出现显著的截面反转效应，与机构再平衡相关',
                'strength': 0.038,
                'persistence': '3 days',
                'conditions': ['tech_sector', 'month_end', 'institutional_rebalancing'],
                'market_regime': 'normal'
            },
            {
                'pattern': 'Commodity-Equity Momentum Spillover',
                'description': '大宗商品动量信号对相关行业股票具有2日滞后的预测能力，在通胀预期上升期间更强',
                'strength': 0.031,
                'persistence': '2-day lag',
                'conditions': ['commodity_momentum', 'related_sectors', 'inflation_expectations'],
                'market_regime': 'inflationary'
            }
        ]
        
        print(f"🎯 检测到 {len(mock_anomalies)} 个市场异象:")
        
        for i, anomaly in enumerate(mock_anomalies, 1):
            print(f"\n   🔍 异象 {i}: {anomaly['pattern']}")
            print(f"      描述: {anomaly['description']}")
            print(f"      信号强度: {anomaly['strength']:.3f}")
            print(f"      持续期: {anomaly['persistence']}")
            print(f"      触发条件: {', '.join(anomaly['conditions'])}")
            print(f"      市场环境: {anomaly['market_regime']}")
            
            # 创建发现记录
            discovery = FactorDiscovery(
                discovery_id="",
                discovery_type=DiscoveryType.MARKET_ANOMALY,
                factor_category=FactorCategory.TECHNICAL,
                title=f"市场异象: {anomaly['pattern']}",
                description=anomaly['description'],
                source="内部市场分析系统",
                discovered_at=datetime.now(),
                discoverer='system',
                theoretical_basis="行为金融学和市场微观结构理论",
                expected_alpha=anomaly['strength'],
                risk_factors=['market_regime_change', 'liquidity_risk'],
                tags=['market_anomaly', 'behavioral', anomaly['market_regime']],
                confidence_score=0.8
            )
            
            # 处理发现
            await self.sentinel._process_new_discovery(discovery)
            
            print(f"      ✅ 异象已记录 (ID: {discovery.discovery_id})")
    
    async def demonstrate_manual_discovery_input(self):
        """演示手动发现输入"""
        print("\n✋ 手动发现输入演示...")
        
        # 模拟研究员手动输入的发现
        manual_discoveries = [
            {
                'title': '基于ESG评级变化的动量因子',
                'description': '当公司ESG评级发生显著提升时，其股价在随后1-3个月内表现出持续的正向动量效应',
                'theoretical_basis': '基于ESG投资理念的资金流入和估值重估理论，结合行为金融学中的锚定效应',
                'category': FactorCategory.SENTIMENT,
                'expected_alpha': 0.055,
                'data_requirements': ['esg_ratings', 'rating_changes', 'price_data', 'volume_data']
            },
            {
                'title': '供应链网络中心性因子',
                'description': '在供应链网络中处于中心位置的公司，在供应链冲击事件中表现出更强的韧性和超额收益',
                'theoretical_basis': '网络理论和供应链管理理论，中心性节点具有更强的议价能力和风险分散能力',
                'category': FactorCategory.FUNDAMENTAL,
                'expected_alpha': 0.041,
                'data_requirements': ['supply_chain_data', 'network_topology', 'financial_data']
            }
        ]
        
        print(f"📝 研究员手动输入 {len(manual_discoveries)} 个发现:")
        
        for i, manual_discovery in enumerate(manual_discoveries, 1):
            print(f"\n   ✍️ 手动发现 {i}: {manual_discovery['title']}")
            print(f"      描述: {manual_discovery['description']}")
            print(f"      理论基础: {manual_discovery['theoretical_basis'][:80]}...")
            print(f"      因子类别: {manual_discovery['category'].value}")
            print(f"      预期Alpha: {manual_discovery['expected_alpha']:.3f}")
            print(f"      数据需求: {', '.join(manual_discovery['data_requirements'])}")
            
            # 手动输入发现
            discovery_id = await self.sentinel.manual_discovery_input(
                title=manual_discovery['title'],
                description=manual_discovery['description'],
                theoretical_basis=manual_discovery['theoretical_basis'],
                factor_category=manual_discovery['category'],
                expected_alpha=manual_discovery['expected_alpha'],
                data_requirements=manual_discovery['data_requirements']
            )
            
            print(f"      ✅ 手动发现已记录 (ID: {discovery_id})")
    
    async def demonstrate_factor_implementation(self):
        """演示因子自动实现"""
        print("\n🔧 因子自动实现演示...")
        
        # 选择一个高置信度的发现进行实现
        high_confidence_discoveries = [
            d for d in self.sentinel.discoveries.values() 
            if d.confidence_score >= 0.8 and d.status == ValidationStatus.DISCOVERED
        ]
        
        if not high_confidence_discoveries:
            print("   ⚠️ 没有找到高置信度的待实现发现")
            return
        
        discovery = high_confidence_discoveries[0]
        print(f"🎯 选择实现发现: {discovery.title}")
        print(f"   置信度: {discovery.confidence_score:.2f}")
        print(f"   因子类别: {discovery.factor_category.value}")
        
        # 自动实现因子
        print("\n🤖 使用DeepSeek-R1自动生成因子代码...")
        implementation = await self.sentinel._generate_factor_code_with_deepseek(discovery)
        
        if implementation:
            print(f"✅ 因子代码生成成功:")
            print(f"   因子名称: {implementation.factor_name}")
            print(f"   因子公式: {implementation.factor_formula}")
            print(f"   代码质量评分: {implementation.code_quality_score:.2f}")
            print(f"   依赖库: {', '.join(implementation.dependencies)}")
            
            print(f"\n📝 生成的Python代码:")
            print("   " + "="*50)
            for line in implementation.python_code.split('\n'):
                if line.strip():
                    print(f"   {line}")
            print("   " + "="*50)
            
            # 运行回测验证
            print(f"\n📊 运行因子回测验证...")
            validation_results = await self.sentinel._run_factor_backtest(implementation)
            
            # 更新实现性能指标
            implementation.ic_mean = validation_results['ic_mean']
            implementation.ic_std = validation_results['ic_std']
            implementation.ir_ratio = validation_results['ir_ratio']
            implementation.turnover = validation_results['turnover']
            
            print(f"✅ 回测验证完成:")
            print(f"   IC均值: {implementation.ic_mean:.4f}")
            print(f"   IC标准差: {implementation.ic_std:.4f}")
            print(f"   IR比率: {implementation.ir_ratio:.4f}")
            print(f"   换手率: {implementation.turnover:.2f}")
            print(f"   夏普比率: {validation_results['sharpe_ratio']:.2f}")
            print(f"   最大回撤: {validation_results['max_drawdown']:.2%}")
            print(f"   胜率: {validation_results['win_rate']:.2%}")
            
            # 判断是否通过验证
            if implementation.ic_mean > 0.02 and implementation.ir_ratio > 0.5:
                print(f"\n🎉 因子验证通过! 提交到Arena测试队列...")
                discovery.status = ValidationStatus.VALIDATED
                
                # 提交到Arena测试队列
                await self.sentinel._integrate_validated_factor(discovery, implementation)
                
                print(f"✅ 因子已提交到Arena测试队列")
                print(f"   状态: {discovery.status.value}")
                print(f"   下一步: Arena三轨测试 → 策略生成 → 斯巴达考核 → 模拟盘验证 → Z2H认证 → 策略库")
            else:
                print(f"\n❌ 因子验证未通过")
                print(f"   IC均值 {implementation.ic_mean:.4f} {'✅' if implementation.ic_mean > 0.02 else '❌'} (要求 > 0.02)")
                print(f"   IR比率 {implementation.ir_ratio:.4f} {'✅' if implementation.ir_ratio > 0.5 else '❌'} (要求 > 0.5)")
        else:
            print("❌ 因子代码生成失败")
    
    def demonstrate_discovery_statistics(self):
        """演示发现统计"""
        print("\n📊 发现统计分析...")
        
        stats = self.sentinel.get_discovery_statistics()
        
        print(f"📈 总体统计:")
        print(f"   总发现数: {stats['total_discoveries']}")
        
        print(f"\n🏷️ 按发现类型分布:")
        for discovery_type, count in stats['by_type'].items():
            print(f"   • {discovery_type}: {count}")
        
        print(f"\n📂 按因子类别分布:")
        for category, count in stats['by_category'].items():
            print(f"   • {category}: {count}")
        
        print(f"\n👥 按发现者分布:")
        for discoverer, count in stats['by_discoverer'].items():
            print(f"   • {discoverer}: {count}")
        
        print(f"\n🔄 按状态分布:")
        for status, count in stats['by_status'].items():
            print(f"   • {status}: {count}")
        
        if stats['recent_discoveries']:
            print(f"\n🕒 最近发现 (最近7天):")
            for discovery in stats['recent_discoveries'][:5]:
                print(f"   • {discovery['title']}")
                print(f"     时间: {discovery['discovered_at'][:19]}")
                print(f"     置信度: {discovery['confidence_score']:.2f}")
                print(f"     状态: {discovery['status']}")
        
        if stats['top_performers']:
            print(f"\n🏆 顶级表现者 (已验证因子):")
            for performer in stats['top_performers']:
                print(f"   • {performer['title']}")
                print(f"     预期Alpha: {performer['expected_alpha']:.3f}")
                print(f"     置信度: {performer['confidence_score']:.2f}")
                print(f"     类别: {performer['category']}")
    
    async def demonstrate_discovery_query(self):
        """演示发现查询"""
        print("\n🔍 发现详情查询演示...")
        
        if not self.sentinel.discoveries:
            print("   ⚠️ 没有发现记录可供查询")
            return
        
        # 选择一个发现进行详情查询
        discovery_id = list(self.sentinel.discoveries.keys())[0]
        discovery = self.sentinel.discoveries[discovery_id]
        
        print(f"🎯 查询发现详情: {discovery.title}")
        
        details = await self.sentinel.get_discovery_details(discovery_id)
        
        if details:
            print(f"✅ 发现详情:")
            print(f"   ID: {details['discovery_id']}")
            print(f"   标题: {details['title']}")
            print(f"   类型: {details['discovery_type']}")
            print(f"   类别: {details['factor_category']}")
            print(f"   来源: {details['source']}")
            print(f"   发现时间: {details['discovered_at'][:19]}")
            print(f"   发现者: {details['discoverer']}")
            print(f"   预期Alpha: {details.get('expected_alpha', 'N/A')}")
            print(f"   置信度: {details['confidence_score']:.2f}")
            print(f"   状态: {details['status']}")
            print(f"   标签: {', '.join(details['tags'])}")
            
            if 'implementation' in details:
                impl = details['implementation']
                print(f"\n🔧 实现信息:")
                print(f"   因子ID: {impl['factor_id']}")
                print(f"   因子名称: {impl['factor_name']}")
                print(f"   因子公式: {impl['factor_formula']}")
                if impl.get('ic_mean'):
                    print(f"   IC均值: {impl['ic_mean']:.4f}")
                    print(f"   IR比率: {impl['ir_ratio']:.4f}")
        else:
            print("❌ 未找到发现详情")
    
    def demonstrate_factor_library_status(self):
        """演示Arena测试队列状态"""
        print("\n📚 Arena测试队列状态展示...")
        
        # 检查待Arena测试因子索引文件
        index_file = Path(self.temp_dir) / "pending_arena_factors_index.json"
        
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            print(f"📖 Arena测试队列:")
            print(f"   待测试因子数量: {len(index_data)}")
            
            if index_data:
                print(f"\n📋 待Arena测试因子列表:")
                for i, factor in enumerate(index_data, 1):
                    print(f"   {i}. {factor['factor_name']}")
                    print(f"      类别: {factor['category']}")
                    print(f"      IC均值: {factor.get('ic_mean', 'N/A')}")
                    print(f"      IR比率: {factor.get('ir_ratio', 'N/A')}")
                    print(f"      提交时间: {factor['submitted_to_arena_at'][:19]}")
                    print(f"      当前状态: {factor['status']}")
                    print(f"      下一步: {factor['next_step']}")
                    print(f"      文件路径: {factor['file_path']}")
        else:
            print("   📝 Arena测试队列为空，尚无待测试因子")
        
        # 检查待测试因子文件
        pending_factors_dir = Path(self.temp_dir) / "pending_arena_factors"
        if pending_factors_dir.exists():
            factor_files = list(pending_factors_dir.glob("*.py"))
            print(f"\n📁 待Arena测试因子文件:")
            print(f"   文件数量: {len(factor_files)}")
            
            for factor_file in factor_files[:3]:  # 显示前3个
                print(f"   • {factor_file.name}")
                # 显示文件前几行
                with open(factor_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:8]
                    for line in lines:
                        if line.strip():
                            print(f"     {line.rstrip()}")
                    if len(lines) >= 8:
                        print(f"     ...")
        
        print(f"\n💡 说明:")
        print(f"   • 因子挖掘智能哨兵负责发现和初步验证因子")
        print(f"   • 验证通过的因子提交到Arena测试队列")
        print(f"   • 完整流程: Arena三轨测试 → 策略生成 → 斯巴达考核 → 模拟盘验证 → Z2H认证 → 策略库")
        print(f"   • 只有通过完整验证流程的策略才能进入最终策略库")
    
    async def run_complete_demo(self):
        """运行完整演示"""
        try:
            # 1. 初始化哨兵
            await self.initialize_sentinel()
            
            # 2. 学术论文发现
            await self.demonstrate_academic_discovery()
            
            # 3. 替代数据发现
            await self.demonstrate_alternative_data_discovery()
            
            # 4. 市场异象发现
            await self.demonstrate_market_anomaly_detection()
            
            # 5. 手动发现输入
            await self.demonstrate_manual_discovery_input()
            
            # 6. 因子自动实现
            await self.demonstrate_factor_implementation()
            
            # 7. 发现统计
            self.demonstrate_discovery_statistics()
            
            # 8. 发现查询
            await self.demonstrate_discovery_query()
            
            # 9. Arena测试队列状态
            self.demonstrate_factor_library_status()
            
            print("\n🎉 因子挖掘智能哨兵演示完成!")
            print("=" * 60)
            print("💡 核心价值:")
            print("   • 自动跟踪前沿研究，永不落后")
            print("   • 智能发现新数据源，拓展Alpha空间")
            print("   • 自动实现和验证，提高研发效率")
            print("   • 完整记录发现过程，积累知识资产")
            print("   • 人机协作发现，结合专业判断")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ 演示过程中发生错误: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """主函数"""
    demo = FactorMiningIntelligenceSentinelDemo()
    await demo.run_complete_demo()


if __name__ == "__main__":
    asyncio.run(main())