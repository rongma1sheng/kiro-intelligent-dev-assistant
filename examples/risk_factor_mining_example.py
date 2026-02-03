"""专业风险因子挖掘系统 - 使用示例

白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统

本示例展示如何使用风险因子挖掘系统进行风险检测和监控。
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List

from src.evolution.risk_mining import (
    RiskFactorRegistry,
    FlowRiskFactorMiner,
    MicrostructureRiskFactorMiner,
    PortfolioRiskFactorMiner,
    RiskFactor
)
from src.infra.event_bus import EventBus


async def example_1_single_stock_risk_detection():
    """示例1: 单只股票风险检测
    
    场景: 检测单只股票的资金流和微结构风险
    """
    print("=" * 60)
    print("示例1: 单只股票风险检测")
    print("=" * 60)
    
    # 1. 初始化系统
    event_bus = EventBus()
    await event_bus.initialize()
    
    registry = RiskFactorRegistry(event_bus)
    flow_miner = FlowRiskFactorMiner()
    micro_miner = MicrostructureRiskFactorMiner()
    
    # 2. 注册挖掘器
    registry.register_miner(flow_miner)
    registry.register_miner(micro_miner)
    
    print(f"✓ 已注册 {len(registry.miners)} 个挖掘器")
    
    # 3. 准备测试数据
    symbol = '000001'
    
    # Level-2数据（模拟主力资金撤退场景）
    level2_data = {
        'net_inflow_history': [-600_000_000] * 5,  # 连续5天大额流出
        'volume': 1_000_000,
        'avg_volume_20d': 5_000_000,
        'large_orders': [
            {'amount': 1_500_000, 'direction': 'sell', 'time': datetime.now()},
            {'amount': 1_200_000, 'direction': 'sell', 'time': datetime.now()},
        ],
        'net_inflow_ma3': [-100_000_000, 50_000_000, 80_000_000]
    }
    
    # 订单簿数据（模拟流动性枯竭场景）
    orderbook = {
        'bid_volume': 500_000,
        'avg_bid_volume_20d': 2_000_000,
        'ask_volume': 2_000_000,
        'bid_ask_spread': 0.05,
        'avg_spread_20d': 0.01,
        'lower_depth': 300_000,
        'upper_depth': 1_500_000
    }
    
    # 4. 挖掘风险因子
    print(f"\n正在检测 {symbol} 的风险...")
    
    flow_factor = flow_miner.mine_flow_risk(symbol, level2_data)
    micro_factor = micro_miner.mine_microstructure_risk(symbol, orderbook)
    
    # 5. 处理检测结果
    if flow_factor:
        await registry.add_factor(flow_factor)
        print(f"\n⚠️  检测到资金流风险:")
        print(f"   类型: {flow_factor.metadata.get('risk_type', 'unknown')}")
        print(f"   风险值: {flow_factor.risk_value:.2f}")
        print(f"   置信度: {flow_factor.confidence:.2f}")
    else:
        print(f"\n✓ 未检测到资金流风险")
    
    if micro_factor:
        await registry.add_factor(micro_factor)
        print(f"\n⚠️  检测到微结构风险:")
        print(f"   类型: {micro_factor.metadata.get('risk_type', 'unknown')}")
        print(f"   风险值: {micro_factor.risk_value:.2f}")
        print(f"   置信度: {micro_factor.confidence:.2f}")
    else:
        print(f"\n✓ 未检测到微结构风险")
    
    # 6. 查询历史因子
    all_factors = await registry.collect_factors(symbol)
    print(f"\n总共检测到 {len(all_factors)} 个风险因子")
    
    # 7. 获取统计信息
    stats = registry.get_stats()
    print(f"\n系统统计:")
    print(f"  已注册挖掘器: {stats['miners_registered']}")
    print(f"  总因子数: {stats['total_factors']}")
    print(f"  跟踪标的数: {stats['symbols_tracked']}")
    
    # 8. 清理
    await event_bus.shutdown()
    print("\n✓ 示例1完成\n")


async def example_2_portfolio_risk_monitoring():
    """示例2: 投资组合风险监控
    
    场景: 监控投资组合的相关性、VaR和集中度风险
    """
    print("=" * 60)
    print("示例2: 投资组合风险监控")
    print("=" * 60)
    
    # 1. 初始化系统
    event_bus = EventBus()
    await event_bus.initialize()
    
    registry = RiskFactorRegistry(event_bus)
    portfolio_miner = PortfolioRiskFactorMiner()
    
    registry.register_miner(portfolio_miner)
    
    print(f"✓ 已注册组合风险挖掘器")
    
    # 2. 准备组合数据
    portfolio = {
        '000001': 0.4,  # 40%权重
        '000002': 0.3,  # 30%权重
        '000003': 0.3   # 30%权重
    }
    
    print(f"\n投资组合:")
    for symbol, weight in portfolio.items():
        print(f"  {symbol}: {weight*100:.1f}%")
    
    # 3. 生成模拟收益率数据
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    
    # 生成高相关性的收益率（模拟相关性收敛场景）
    base_returns = np.random.randn(100) * 0.02
    returns_data = pd.DataFrame({
        '000001': base_returns + np.random.randn(100) * 0.001,
        '000002': base_returns + np.random.randn(100) * 0.001,
        '000003': base_returns + np.random.randn(100) * 0.001
    }, index=dates)
    
    print(f"\n收益率数据: {len(returns_data)} 天")
    
    # 4. 挖掘组合风险
    print(f"\n正在检测组合风险...")
    
    factors = await portfolio_miner.mine_portfolio_risk(
        portfolio, returns_data
    )
    
    # 5. 处理检测结果
    if factors:
        print(f"\n⚠️  检测到 {len(factors)} 个组合风险:")
        for i, factor in enumerate(factors, 1):
            await registry.add_factor(factor)
            print(f"\n  风险 {i}:")
            print(f"    类型: {factor.metadata.get('risk_type', 'unknown')}")
            print(f"    标的: {factor.symbol}")
            print(f"    风险值: {factor.risk_value:.2f}")
            print(f"    置信度: {factor.confidence:.2f}")
            
            # 显示详细信息
            if 'correlation' in factor.metadata:
                print(f"    相关性: {factor.metadata['correlation']:.2f}")
            if 'var' in factor.metadata:
                print(f"    VaR: {factor.metadata['var']:.4f}")
    else:
        print(f"\n✓ 未检测到组合风险")
    
    # 6. 查询各标的的风险因子
    print(f"\n各标的风险因子统计:")
    for symbol in portfolio.keys():
        factors = await registry.collect_factors(symbol)
        print(f"  {symbol}: {len(factors)} 个因子")
    
    # 7. 清理
    await event_bus.shutdown()
    print("\n✓ 示例2完成\n")


async def example_3_multi_stock_concurrent_detection():
    """示例3: 多只股票并发检测
    
    场景: 同时检测多只股票的风险，展示并发能力
    """
    print("=" * 60)
    print("示例3: 多只股票并发检测")
    print("=" * 60)
    
    # 1. 初始化系统
    event_bus = EventBus()
    await event_bus.initialize()
    
    registry = RiskFactorRegistry(event_bus)
    flow_miner = FlowRiskFactorMiner()
    micro_miner = MicrostructureRiskFactorMiner()
    
    registry.register_miner(flow_miner)
    registry.register_miner(micro_miner)
    
    # 2. 准备多只股票的数据
    symbols = ['000001', '000002', '000003', '000004', '000005']
    
    print(f"✓ 准备检测 {len(symbols)} 只股票")
    
    # 3. 并发检测
    start_time = datetime.now()
    
    for symbol in symbols:
        # 准备数据
        level2_data = {
            'net_inflow_history': [np.random.randint(-1000000000, 1000000000) for _ in range(5)],
            'volume': np.random.randint(1000000, 10000000),
            'avg_volume_20d': 5_000_000,
            'large_orders': [],
            'net_inflow_ma3': [np.random.randint(-100000000, 100000000) for _ in range(3)]
        }
        
        orderbook = {
            'bid_volume': np.random.randint(500000, 2000000),
            'avg_bid_volume_20d': 2_000_000,
            'ask_volume': np.random.randint(500000, 2000000),
            'bid_ask_spread': np.random.uniform(0.01, 0.05),
            'avg_spread_20d': 0.01,
            'lower_depth': np.random.randint(300000, 1000000),
            'upper_depth': np.random.randint(300000, 1000000)
        }
        
        # 检测风险
        flow_factor = flow_miner.mine_flow_risk(symbol, level2_data)
        micro_factor = micro_miner.mine_microstructure_risk(symbol, orderbook)
        
        # 添加到注册中心
        if flow_factor:
            await registry.add_factor(flow_factor)
        if micro_factor:
            await registry.add_factor(micro_factor)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # 4. 统计结果
    print(f"\n检测完成，耗时: {elapsed:.3f}秒")
    print(f"平均每只股票: {elapsed/len(symbols)*1000:.2f}ms")
    
    print(f"\n检测结果:")
    for symbol in symbols:
        factors = await registry.collect_factors(symbol)
        if factors:
            print(f"  {symbol}: 检测到 {len(factors)} 个风险因子")
            for factor in factors:
                print(f"    - {factor.factor_type}: {factor.risk_value:.2f}")
        else:
            print(f"  {symbol}: 无风险")
    
    # 5. 系统统计
    stats = registry.get_stats()
    print(f"\n系统统计:")
    print(f"  总因子数: {stats['total_factors']}")
    print(f"  跟踪标的数: {stats['symbols_tracked']}")
    print(f"  查询次数: {stats['queries_executed']}")
    
    # 6. 清理
    await event_bus.shutdown()
    print("\n✓ 示例3完成\n")


async def example_4_risk_factor_query():
    """示例4: 风险因子查询
    
    场景: 展示各种查询方式
    """
    print("=" * 60)
    print("示例4: 风险因子查询")
    print("=" * 60)
    
    # 1. 初始化系统
    event_bus = EventBus()
    await event_bus.initialize()
    
    registry = RiskFactorRegistry(event_bus)
    
    # 2. 添加一些测试因子
    symbol = '000001'
    
    print(f"✓ 添加测试因子...")
    
    for i in range(10):
        factor = RiskFactor(
            factor_type='flow' if i % 2 == 0 else 'microstructure',
            symbol=symbol,
            risk_value=0.5 + i * 0.05,
            confidence=0.9,
            timestamp=datetime.now() + timedelta(seconds=i),
            metadata={'index': i}
        )
        await registry.add_factor(factor)
    
    print(f"✓ 已添加 10 个测试因子")
    
    # 3. 查询所有因子
    print(f"\n查询1: 获取所有因子")
    all_factors = await registry.collect_factors(symbol)
    print(f"  结果: {len(all_factors)} 个因子")
    
    # 4. 按类型查询
    print(f"\n查询2: 只获取资金流因子")
    flow_factors = await registry.collect_factors(symbol, factor_type='flow')
    print(f"  结果: {len(flow_factors)} 个因子")
    
    print(f"\n查询3: 只获取微结构因子")
    micro_factors = await registry.collect_factors(symbol, factor_type='microstructure')
    print(f"  结果: {len(micro_factors)} 个因子")
    
    # 5. 限制数量查询
    print(f"\n查询4: 只获取最近3个因子")
    recent_factors = await registry.collect_factors(symbol, limit=3)
    print(f"  结果: {len(recent_factors)} 个因子")
    for i, factor in enumerate(recent_factors, 1):
        print(f"    {i}. {factor.factor_type}: {factor.risk_value:.2f}")
    
    # 6. 获取最新因子
    print(f"\n查询5: 获取最新的资金流因子")
    latest_flow = await registry.get_latest_factor(symbol, 'flow')
    if latest_flow:
        print(f"  结果: 风险值 {latest_flow.risk_value:.2f}")
    
    print(f"\n查询6: 获取最新的微结构因子")
    latest_micro = await registry.get_latest_factor(symbol, 'microstructure')
    if latest_micro:
        print(f"  结果: 风险值 {latest_micro.risk_value:.2f}")
    
    # 7. 清理因子
    print(f"\n清理: 清除所有因子")
    cleared = registry.clear_factors(symbol)
    print(f"  已清除 {cleared} 个因子")
    
    # 验证清除
    remaining = await registry.collect_factors(symbol)
    print(f"  剩余: {len(remaining)} 个因子")
    
    # 8. 清理
    await event_bus.shutdown()
    print("\n✓ 示例4完成\n")


async def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("专业风险因子挖掘系统 - 使用示例")
    print("=" * 60 + "\n")
    
    # 运行所有示例
    await example_1_single_stock_risk_detection()
    await example_2_portfolio_risk_monitoring()
    await example_3_multi_stock_concurrent_detection()
    await example_4_risk_factor_query()
    
    print("=" * 60)
    print("所有示例运行完成！")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
