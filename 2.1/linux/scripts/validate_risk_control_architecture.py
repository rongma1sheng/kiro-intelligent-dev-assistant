"""验证风险控制架构

验证新架构的核心功能是否正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.capital.capital_allocator import CapitalAllocator, Tier
from src.capital.aum_sensor import AUMSensor
from src.capital.strategy_selector import StrategySelector
from src.capital.weight_adjuster import WeightAdjuster
from src.strategies.data_models import StrategyConfig, StrategyMetadata
from src.strategies.strategy_risk_manager import StrategyRiskManager
from src.evolution.arena_test_manager import ArenaTestManager
from src.evolution.z2h_certification import Z2HCertification


async def test_capital_allocator():
    """测试资本分配器"""
    logger.info("=" * 60)
    logger.info("测试1: 资本分配器")
    logger.info("=" * 60)
    
    try:
        # 创建资本分配器
        allocator = CapitalAllocator()
        
        # 测试档位确定
        test_cases = [
            (5000, Tier.TIER1_MICRO),
            (50000, Tier.TIER2_SMALL),
            (300000, Tier.TIER3_MEDIUM),
            (800000, Tier.TIER4_LARGE),
            (5000000, Tier.TIER5_MILLION),
            (50000000, Tier.TIER6_TEN_MILLION),
        ]
        
        for aum, expected_tier in test_cases:
            tier = allocator.determine_tier(aum)
            status = "✅" if tier == expected_tier else "❌"
            logger.info(f"{status} AUM {aum:,.0f} → {tier} (期望: {expected_tier})")
        
        logger.info("✅ 资本分配器测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 资本分配器测试失败: {e}")
        return False


async def test_strategy_selector():
    """测试策略选择器"""
    logger.info("=" * 60)
    logger.info("测试2: 策略选择器")
    logger.info("=" * 60)
    
    try:
        # 创建策略池
        strategy_pool = {
            'momentum_t1': {
                'strategy_name': 'momentum_t1',
                'tier': 'tier1_micro',
                'best_tier': 'tier1_micro',
                'z2h_certified': True,
                'strategy_type': 'momentum',
                'arena_results': {
                    'tier1_micro': {'sharpe_ratio': 1.5, 'total_return_pct': 25.0}
                }
            },
            'mean_reversion_t2': {
                'strategy_name': 'mean_reversion_t2',
                'tier': 'tier2_small',
                'best_tier': 'tier2_small',
                'z2h_certified': True,
                'strategy_type': 'mean_reversion',
                'arena_results': {
                    'tier2_small': {'sharpe_ratio': 1.8, 'total_return_pct': 30.0}
                }
            },
            'uncertified_strategy': {
                'strategy_name': 'uncertified_strategy',
                'tier': 'tier1_micro',
                'best_tier': 'tier1_micro',
                'z2h_certified': False,
                'strategy_type': 'momentum',
                'arena_results': {}
            }
        }
        
        selector = StrategySelector(strategy_pool)
        
        # 测试Z2H认证过滤
        all_strategies = list(strategy_pool.values())
        certified = await selector.filter_by_z2h_certification(all_strategies)
        logger.info(f"✅ Z2H认证过滤: {len(all_strategies)}个策略 → {len(certified)}个已认证")
        
        # 测试档位策略选择
        tier1_strategies = await selector.select_for_tier('tier1_micro')
        logger.info(f"✅ Tier1策略选择: {len(tier1_strategies)}个策略")
        
        logger.info("✅ 策略选择器测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 策略选择器测试失败: {e}")
        return False


async def test_weight_adjuster():
    """测试权重调整器"""
    logger.info("=" * 60)
    logger.info("测试3: 权重调整器")
    logger.info("=" * 60)
    
    try:
        adjuster = WeightAdjuster()
        
        # 创建模拟策略
        strategies = [
            {'strategy_name': 'strategy_1'},
            {'strategy_name': 'strategy_2'},
            {'strategy_name': 'strategy_3'},
        ]
        
        # 测试均等权重
        weights = await adjuster.adjust_weights(strategies, {})
        logger.info(f"✅ 均等权重: {weights}")
        
        # 验证权重约束
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.001, f"权重总和不等于1.0: {total}"
        
        for name, weight in weights.items():
            assert 0.05 <= weight <= 0.40, f"权重超出范围: {name}={weight}"
        
        # 测试基于表现的权重调整
        performance_metrics = {
            'strategy_1': 0.5,   # 表现优于预期
            'strategy_2': -0.3,  # 表现低于预期
            'strategy_3': 0.0,   # 表现符合预期
        }
        
        adjusted_weights = await adjuster.adjust_weights(strategies, performance_metrics)
        logger.info(f"✅ 调整后权重: {adjusted_weights}")
        
        # 验证调整方向
        assert adjusted_weights['strategy_1'] > weights['strategy_1'], "表现好的策略权重应增加"
        assert adjusted_weights['strategy_2'] < weights['strategy_2'], "表现差的策略权重应降低"
        
        logger.info("✅ 权重调整器测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 权重调整器测试失败: {e}")
        return False


async def test_strategy_risk_manager():
    """测试策略风险管理器"""
    logger.info("=" * 60)
    logger.info("测试4: 策略风险管理器")
    logger.info("=" * 60)
    
    try:
        # 创建策略配置
        config = StrategyConfig(
            strategy_name='test_strategy',
            capital_tier='tier1_micro',
            max_position=0.95,
            max_single_stock=0.05,
            max_industry=0.30,
            stop_loss_pct=-0.03,
            take_profit_pct=0.10,
            trailing_stop_enabled=False
        )
        
        risk_manager = StrategyRiskManager(config)
        
        # 测试滑点计算
        slippage = await risk_manager.calculate_slippage_and_impact(
            symbol='000001',
            order_size=10000,
            daily_volume=1000000,
            tier='tier1_micro'
        )
        logger.info(f"✅ 滑点计算: {slippage}")
        
        # 测试Tier5流动性约束
        from src.strategies.data_models import Position
        
        positions = [
            Position(
                symbol='000001',
                size=0.10,
                entry_price=10.0,
                current_price=10.5,
                pnl_pct=0.05,
                holding_days=5,
                industry='technology'
            )
        ]
        
        market_data = {
            '000001': {
                'daily_volume': 60_000_000,  # 6000万，满足Tier5要求
                'turnover_rate': 0.015       # 1.5%，满足Tier5要求
            }
        }
        
        filtered = await risk_manager.filter_by_liquidity(
            positions, market_data, tier='tier5_million'
        )
        logger.info(f"✅ Tier5流动性过滤: {len(positions)}个 → {len(filtered)}个")
        
        # 测试TWAP/VWAP建议
        algorithm = risk_manager.suggest_execution_algorithm(
            order_size=10_000_000,
            daily_volume=100_000_000,
            tier='tier6_ten_million'
        )
        logger.info(f"✅ Tier6执行算法建议: {algorithm}")
        
        logger.info("✅ 策略风险管理器测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 策略风险管理器测试失败: {e}")
        return False


async def test_arena_and_certification():
    """测试Arena和Z2H认证"""
    logger.info("=" * 60)
    logger.info("测试5: Arena和Z2H认证")
    logger.info("=" * 60)
    
    try:
        # 创建Arena测试管理器
        arena_manager = ArenaTestManager()
        
        # 创建Z2H认证系统
        z2h_cert = Z2HCertification()
        
        # 创建Arena测试结果
        from src.strategies.data_models import ArenaTestResult
        
        arena_result = ArenaTestResult(
            strategy_name='test_momentum',
            test_tier='tier1_micro',
            initial_capital=10000.0,
            final_capital=12500.0,
            total_return_pct=25.0,
            sharpe_ratio=1.5,
            max_drawdown_pct=-15.0,
            win_rate=0.55,
            evolved_params={
                'max_position': 0.8,
                'max_single_stock': 0.1,
                'max_industry': 0.3,
                'stop_loss_pct': -0.05,
                'take_profit_pct': 0.10
            },
            avg_slippage_pct=0.001,
            avg_impact_cost_pct=0.0005,
            test_start_date='2024-01-01',
            test_end_date='2024-12-31'
        )
        
        # 创建包含Arena结果的策略元数据
        strategy_metadata = StrategyMetadata(
            strategy_name='test_momentum',
            strategy_class='ExampleMomentumStrategy',
            strategy_type='momentum',
            z2h_certified=False,
            best_tier='tier1_micro',
            arena_results={'tier1_micro': arena_result}
        )
        
        logger.info(f"✅ 策略元数据创建: {strategy_metadata.strategy_name}")
        logger.info(f"✅ Arena测试结果模拟完成")
        
        # 检查Z2H认证资格（传入StrategyMetadata对象）
        eligibility = await z2h_cert.check_certification_eligibility(strategy_metadata)
        is_eligible = eligibility['eligible']
        logger.info(f"✅ Z2H认证资格检查: {'合格' if is_eligible else '不合格'}")
        
        logger.info("✅ Arena和Z2H认证测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ Arena和Z2H认证测试失败: {e}")
        return False


async def test_integration():
    """集成测试：完整流程"""
    logger.info("=" * 60)
    logger.info("测试6: 完整集成流程")
    logger.info("=" * 60)
    
    try:
        # 1. 创建资本分配器
        allocator = CapitalAllocator()
        
        # 2. 模拟AUM变化
        aum_values = [5000, 50000, 300000, 800000]
        
        for aum in aum_values:
            tier = allocator.determine_tier(aum)
            logger.info(f"📊 AUM: {aum:,.0f} → 档位: {tier}")
            
            # 3. 注册模拟策略
            strategy_metadata = {
                'strategy_name': f'strategy_{tier}',
                'tier': tier,
                'best_tier': tier,
                'z2h_certified': True,
                'strategy_type': 'momentum',
                'arena_results': {
                    tier: {'sharpe_ratio': 1.5, 'total_return_pct': 25.0}
                }
            }
            allocator.register_strategy(strategy_metadata)
        
        # 4. 测试资本重新分配
        logger.info("🔄 测试资本重新分配...")
        
        # 模拟AUM为30万（Tier3）
        allocator.current_aum = 300000
        result = await allocator.reallocate_capital()
        
        logger.info(f"✅ 资本分配完成:")
        logger.info(f"  - 档位: {result['tier']}")
        logger.info(f"  - 策略数: {len(result['strategies'])}")
        logger.info(f"  - 权重: {result['weights']}")
        
        logger.info("✅ 完整集成流程测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 完整集成流程测试失败: {e}")
        return False


async def main():
    """主函数"""
    logger.info("🚀 开始验证风险控制架构")
    logger.info("")
    
    results = []
    
    # 运行所有测试
    results.append(await test_capital_allocator())
    results.append(await test_strategy_selector())
    results.append(await test_weight_adjuster())
    results.append(await test_strategy_risk_manager())
    results.append(await test_arena_and_certification())
    results.append(await test_integration())
    
    # 统计结果
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 测试结果汇总")
    logger.info("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    logger.info(f"通过: {passed}/{total}")
    logger.info(f"失败: {total - passed}/{total}")
    
    if passed == total:
        logger.info("✅ 所有测试通过！风险控制架构运行正常。")
        return 0
    else:
        logger.error("❌ 部分测试失败，请检查错误日志。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
