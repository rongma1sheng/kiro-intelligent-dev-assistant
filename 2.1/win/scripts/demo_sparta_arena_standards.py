#!/usr/bin/env python
"""
MIA系统斯巴达Arena压力测试标准演示脚本

版本: v1.6.0
作者: MIA Team
日期: 2026-01-18

演示内容:
1. 双轨压力测试系统 (Reality Track + Hell Track)
2. 多场景压力测试
3. 综合评分算法
4. 通过标准验证
5. 策略抗压能力评估
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.evolution.sparta_arena_standards import (
    SpartaArenaStandards,
    TrackType,
    MarketScenario
)
from src.base.models import Strategy


def print_header(title: str):
    """打印标题"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_section(title: str):
    """打印章节标题"""
    print(f"\n📋 {title}")
    print("-" * 60)


def print_config_details(arena_standards: SpartaArenaStandards):
    """展示配置详情"""
    print_section("斯巴达Arena配置详情")
    
    print("🎯 Reality Track (真实历史数据轨道):")
    reality_configs = arena_standards.test_configs[TrackType.REALITY]
    for scenario, config in reality_configs.items():
        print(f"  • {scenario.value:20} | 测试天数: {config.test_duration_days:3d} | "
              f"最大回撤: {config.max_drawdown_threshold:.1%} | "
              f"最低夏普: {config.min_sharpe_threshold:.1f} | "
              f"生存率: {config.survival_rate_threshold:.1%}")
    
    print("\n🔥 Hell Track (极端场景模拟轨道):")
    hell_configs = arena_standards.test_configs[TrackType.HELL]
    for scenario, config in hell_configs.items():
        print(f"  • {scenario.value:20} | 测试天数: {config.test_duration_days:3d} | "
              f"最大回撤: {config.max_drawdown_threshold:.1%} | "
              f"最低夏普: {config.min_sharpe_threshold:.1f} | "
              f"压力倍数: {config.stress_multiplier:.1f}x")
    
    print("\n⚖️ 评分权重体系:")
    weights = arena_standards.scoring_weights
    print(f"  • 基础指标权重: {weights['basic_metrics']:.0%}")
    print(f"  • 压力指标权重: {weights['stress_metrics']:.0%}")
    print(f"  • 稳定性指标权重: {weights['stability_metrics']:.0%}")
    
    print("\n🎖️ 通过标准:")
    reality_std = arena_standards.pass_standards['reality_track']
    hell_std = arena_standards.pass_standards['hell_track']
    print(f"  Reality Track - 最低总分: {reality_std['min_overall_score']:.0%}, "
          f"最低生存率: {reality_std['min_survival_rate']:.0%}")
    print(f"  Hell Track    - 最低总分: {hell_std['min_overall_score']:.0%}, "
          f"最低生存率: {hell_std['min_survival_rate']:.0%}")


async def demo_reality_track_test(arena_standards: SpartaArenaStandards):
    """演示Reality Track测试"""
    print_section("Reality Track 真实历史数据测试")
    
    # 创建测试策略
    strategy = Strategy(
        strategy_id="demo_momentum_001",
        name="演示动量策略",
        type="momentum",
        description="基于价格动量的演示策略"
    )
    
    print(f"🎯 测试策略: {strategy.name} ({strategy.type})")
    print("📊 开始Reality Track测试...")
    
    # 运行Reality Track测试
    reality_results = await arena_standards.run_arena_test(
        strategy, TrackType.REALITY
    )
    
    print(f"\n✅ Reality Track测试完成，共测试 {len(reality_results)} 个场景")
    
    # 展示各场景结果
    for scenario, result in reality_results.items():
        status = "✅ 通过" if result.passed else "❌ 失败"
        print(f"\n📈 {scenario.value} {status}")
        print(f"   总收益: {result.total_return:+.1%} | 夏普比率: {result.sharpe_ratio:.2f} | "
              f"最大回撤: {result.max_drawdown:.1%}")
        print(f"   生存率: {result.survival_rate:.1%} | 恢复因子: {result.recovery_factor:.2f} | "
              f"抗压能力: {result.stress_resistance:.2f}")
        print(f"   通过评分: {result.pass_score:.1%}")
        
        if result.failure_reasons:
            print(f"   失败原因: {', '.join(result.failure_reasons[:2])}")
    
    return reality_results


async def demo_hell_track_test(arena_standards: SpartaArenaStandards):
    """演示Hell Track测试"""
    print_section("Hell Track 极端场景模拟测试")
    
    # 创建测试策略
    strategy = Strategy(
        strategy_id="demo_robust_001",
        name="演示抗压策略",
        type="mean_reversion",
        description="具有抗压能力的均值回归策略"
    )
    
    print(f"🎯 测试策略: {strategy.name} ({strategy.type})")
    print("🔥 开始Hell Track极端压力测试...")
    
    # 运行Hell Track测试
    hell_results = await arena_standards.run_arena_test(
        strategy, TrackType.HELL
    )
    
    print(f"\n✅ Hell Track测试完成，共测试 {len(hell_results)} 个极端场景")
    
    # 展示各场景结果
    for scenario, result in hell_results.items():
        status = "✅ 通过" if result.passed else "❌ 失败"
        print(f"\n🔥 {scenario.value} {status}")
        print(f"   总收益: {result.total_return:+.1%} | 夏普比率: {result.sharpe_ratio:.2f} | "
              f"最大回撤: {result.max_drawdown:.1%}")
        print(f"   生存率: {result.survival_rate:.1%} | 恢复因子: {result.recovery_factor:.2f} | "
              f"抗压能力: {result.stress_resistance:.2f}")
        print(f"   通过评分: {result.pass_score:.1%}")
        
        if result.failure_reasons:
            print(f"   失败原因: {', '.join(result.failure_reasons[:2])}")
    
    return hell_results


def demo_combined_scoring(arena_standards: SpartaArenaStandards, reality_results, hell_results):
    """演示综合评分"""
    print_section("Arena综合评分算法")
    
    print("🏆 计算双轨综合评分...")
    
    # 计算综合评分
    combined_result = arena_standards.calculate_combined_arena_score(
        reality_results, hell_results
    )
    
    print(f"\n📊 综合评分结果:")
    print(f"   综合评分: {combined_result['combined_score']:.1%}")
    print(f"   综合评级: {combined_result['grade']}")
    print(f"   是否通过: {'✅ 通过' if combined_result['combined_passed'] else '❌ 失败'}")
    
    print(f"\n📈 Reality Track统计:")
    reality_stats = combined_result['reality_track']
    print(f"   平均评分: {reality_stats['avg_score']:.1%}")
    print(f"   通过场景: {reality_stats['pass_count']}/{reality_stats['total_scenarios']}")
    print(f"   通过率: {reality_stats['pass_rate']:.1%}")
    
    print(f"\n🔥 Hell Track统计:")
    hell_stats = combined_result['hell_track']
    print(f"   平均评分: {hell_stats['avg_score']:.1%}")
    print(f"   通过场景: {hell_stats['pass_count']}/{hell_stats['total_scenarios']}")
    print(f"   通过率: {hell_stats['pass_rate']:.1%}")
    
    print(f"\n🎯 总体统计:")
    summary = combined_result['summary']
    print(f"   总测试场景: {summary['total_scenarios']}")
    print(f"   总通过场景: {summary['total_passed']}")
    print(f"   总体通过率: {summary['overall_pass_rate']:.1%}")
    
    return combined_result


def demo_grade_system():
    """演示评级体系"""
    print_section("Arena评级体系说明")
    
    grade_system = [
        ("A+", "≥85%", "卓越表现", "顶级策略，可大规模配置"),
        ("A",  "≥75%", "优秀表现", "优质策略，可标准配置"),
        ("B+", "≥65%", "良好表现", "合格策略，可适度配置"),
        ("B",  "≥55%", "一般表现", "基础策略，需谨慎配置"),
        ("C+", "≥45%", "勉强通过", "边缘策略，需密切监控"),
        ("C",  "≥35%", "表现不佳", "问题策略，需要改进"),
        ("D",  "<35%", "严重不足", "失败策略，不建议使用")
    ]
    
    print("🏆 Arena评级标准:")
    print("   评级 | 评分范围 | 表现等级 | 配置建议")
    print("   " + "-" * 55)
    for grade, score_range, performance, suggestion in grade_system:
        print(f"   {grade:4} | {score_range:8} | {performance:8} | {suggestion}")
    
    print("\n💡 评级说明:")
    print("   • Reality Track权重70%，Hell Track权重30%")
    print("   • 基础指标40% + 压力指标40% + 稳定性指标20%")
    print("   • 必须同时满足各轨道最低要求才能通过")


def demo_stress_metrics_explanation():
    """演示压力测试指标说明"""
    print_section("压力测试指标详解")
    
    metrics = [
        ("生存率", "survival_rate", "未爆仓的时间比例", "≥85% (Reality) / ≥60% (Hell)"),
        ("恢复因子", "recovery_factor", "从最大回撤恢复的能力", "≥0.5 (Reality) / ≥0.2 (Hell)"),
        ("抗压能力", "stress_resistance", "极端情况下的表现", "≥0.6 (Reality) / ≥0.3 (Hell)"),
        ("适应速度", "adaptation_speed", "对市场变化的反应速度", "≥0.4 (通用标准)")
    ]
    
    print("📊 压力测试核心指标:")
    print("   指标名称   | 英文名称          | 含义说明                 | 通过标准")
    print("   " + "-" * 75)
    for name, eng_name, description, standard in metrics:
        print(f"   {name:8} | {eng_name:17} | {description:20} | {standard}")
    
    print("\n🔍 指标计算方法:")
    print("   • 生存率: 资产净值>50%的时间比例")
    print("   • 恢复因子: (期末净值-最低净值) / |最大回撤|")
    print("   • 抗压能力: 1 - (极端日平均亏损 / 极端阈值)")
    print("   • 适应速度: 1 - |收益序列自相关系数|")


async def demo_scenario_data_generation(arena_standards: SpartaArenaStandards):
    """演示场景数据生成"""
    print_section("测试场景数据生成演示")
    
    print("📊 Reality Track数据特征:")
    
    # 生成不同Reality场景的数据
    reality_scenarios = [
        MarketScenario.BULL_MARKET,
        MarketScenario.BEAR_MARKET,
        MarketScenario.SIDEWAYS_MARKET
    ]
    
    for scenario in reality_scenarios:
        config = arena_standards.test_configs[TrackType.REALITY][scenario]
        data = await arena_standards._generate_reality_data(scenario, config)
        
        total_return = (data['close'].iloc[-1] / data['close'].iloc[0]) - 1
        volatility = data['returns'].std() * np.sqrt(252)
        max_daily_return = data['returns'].max()
        min_daily_return = data['returns'].min()
        
        print(f"\n   {scenario.value}:")
        print(f"     总收益: {total_return:+.1%} | 年化波动率: {volatility:.1%}")
        print(f"     最大单日涨幅: {max_daily_return:+.1%} | 最大单日跌幅: {min_daily_return:+.1%}")
    
    print("\n🔥 Hell Track数据特征:")
    
    # 生成Hell场景数据
    hell_scenarios = [
        MarketScenario.FLASH_CRASH,
        MarketScenario.BLACK_SWAN
    ]
    
    for scenario in hell_scenarios:
        config = arena_standards.test_configs[TrackType.HELL][scenario]
        data = await arena_standards._generate_hell_data(scenario, config)
        
        total_return = (data['close'].iloc[-1] / data['close'].iloc[0]) - 1
        volatility = data['returns'].std() * np.sqrt(252)
        max_daily_return = data['returns'].max()
        min_daily_return = data['returns'].min()
        extreme_days = np.sum(np.abs(data['returns']) > 0.05)
        
        print(f"\n   {scenario.value}:")
        print(f"     总收益: {total_return:+.1%} | 年化波动率: {volatility:.1%}")
        print(f"     最大单日涨幅: {max_daily_return:+.1%} | 最大单日跌幅: {min_daily_return:+.1%}")
        print(f"     极端波动天数: {extreme_days} (>5%)")


def demo_performance_comparison():
    """演示性能对比"""
    print_section("Arena vs 传统回测对比")
    
    comparison_data = [
        ("测试维度", "传统回测", "Arena双轨测试"),
        ("测试场景", "单一历史数据", "9个多样化场景"),
        ("压力测试", "无", "5个极端场景"),
        ("评估指标", "收益+夏普+回撤", "15+个综合指标"),
        ("通过标准", "固定阈值", "相对+绝对双重标准"),
        ("抗压评估", "无", "生存率+恢复因子"),
        ("适应性", "无", "市场适应速度"),
        ("评级体系", "无", "A+到D七级评级"),
        ("风险识别", "有限", "全面压力测试")
    ]
    
    print("📊 Arena双轨测试 vs 传统回测:")
    print("   " + "-" * 65)
    for dimension, traditional, arena in comparison_data:
        print(f"   {dimension:8} | {traditional:15} | {arena}")
    
    print("\n🎯 Arena系统优势:")
    advantages = [
        "全面性: 覆盖牛熊震荡+5种极端场景",
        "科学性: 15+个维度综合评估策略表现",
        "实用性: 差异化标准，精准识别策略特点",
        "前瞻性: 极端压力测试，提前识别风险",
        "标准化: 统一评级体系，便于策略对比"
    ]
    
    for i, advantage in enumerate(advantages, 1):
        print(f"   {i}. {advantage}")


async def main():
    """主演示函数"""
    print_header("MIA系统斯巴达Arena压力测试标准演示")
    
    print("🎯 核心理念: 双轨压力测试，全面评估策略在不同市场环境下的表现")
    print("📊 测试轨道: Reality Track (真实历史) + Hell Track (极端模拟)")
    print("🏆 评估体系: 基础指标 + 压力指标 + 稳定性指标")
    
    # 初始化Arena标准
    print("\n🚀 初始化斯巴达Arena测试标准...")
    arena_standards = SpartaArenaStandards()
    
    # 1. 展示配置详情
    print_config_details(arena_standards)
    
    # 2. 演示场景数据生成
    await demo_scenario_data_generation(arena_standards)
    
    # 3. 演示Reality Track测试
    reality_results = await demo_reality_track_test(arena_standards)
    
    # 4. 演示Hell Track测试
    hell_results = await demo_hell_track_test(arena_standards)
    
    # 5. 演示综合评分
    combined_result = demo_combined_scoring(arena_standards, reality_results, hell_results)
    
    # 6. 演示评级体系
    demo_grade_system()
    
    # 7. 演示压力测试指标
    demo_stress_metrics_explanation()
    
    # 8. 演示性能对比
    demo_performance_comparison()
    
    # 总结
    print_section("演示总结")
    
    print("✅ 斯巴达Arena压力测试标准演示完成!")
    print("\n🎯 核心特色:")
    print("   • 双轨测试: Reality + Hell 全面覆盖")
    print("   • 多场景: 9个场景涵盖各种市场环境")
    print("   • 科学评估: 15+指标综合评分")
    print("   • 差异化标准: Reality严格，Hell宽松")
    print("   • 统一评级: A+到D七级评级体系")
    
    print("\n📊 测试结果概览:")
    if 'combined_result' in locals():
        print(f"   • 综合评级: {combined_result['grade']}")
        print(f"   • 综合评分: {combined_result['combined_score']:.1%}")
        print(f"   • Reality通过率: {combined_result['reality_track']['pass_rate']:.1%}")
        print(f"   • Hell通过率: {combined_result['hell_track']['pass_rate']:.1%}")
    
    print("\n🚀 下一步: 集成到四档资金验证体系，实现策略全生命周期管理!")


if __name__ == "__main__":
    asyncio.run(main())