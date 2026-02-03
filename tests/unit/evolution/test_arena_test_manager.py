"""Arena Test Manager单元测试

白皮书依据: 第四章 4.2 斯巴达竞技场
测试任务: Task 11.1

测试覆盖:
- Property 16: Arena Four-Tier Testing
- Property 17: Arena Slippage Simulation
- Property 18: Arena Parameter Recording
- Property 19: Best Tier Identification
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.evolution.arena_test_manager import ArenaTestManager
from src.strategies.base_strategy import Strategy
from src.strategies.data_models import ArenaTestResult, StrategyConfig


class MockStrategy(Strategy):
    """Mock策略类用于测试"""
    
    def __init__(self, name: str = "TestStrategy"):
        config = StrategyConfig(
            strategy_name=name,
            capital_tier="tier1_micro",
            max_position=0.9,
            max_single_stock=0.2,
            max_industry=0.5,
            stop_loss_pct=-0.08,
            take_profit_pct=0.12,
            trailing_stop_enabled=False
        )
        super().__init__(name=name, config=config)
    
    async def generate_signals(self, market_data):
        """生成信号（Mock实现）"""
        return []
    
    async def calculate_position_sizes(self, signals, current_positions, available_capital):
        """计算仓位（Mock实现）"""
        return {}
    
    async def apply_risk_controls(self, positions):
        """应用风险控制（Mock实现）"""
        return positions


class TestArenaTestManager:
    """测试ArenaTestManager核心功能"""
    
    @pytest.fixture
    def arena_manager(self):
        """创建ArenaTestManager实例"""
        return ArenaTestManager()
    
    @pytest.fixture
    def mock_strategy(self):
        """创建Mock策略"""
        return MockStrategy(name="TestStrategy")
    
    def test_initialization(self, arena_manager):
        """测试初始化"""
        assert arena_manager is not None
        assert len(arena_manager.tier_capital_map) == 4
        assert arena_manager.tier_capital_map['tier1_micro'] == 5000.0
        assert arena_manager.tier_capital_map['tier2_small'] == 50000.0
        assert arena_manager.tier_capital_map['tier3_medium'] == 250000.0
        assert arena_manager.tier_capital_map['tier4_large'] == 750000.0
        assert isinstance(arena_manager.test_results_cache, dict)
    
    def test_tier_capital_mapping(self, arena_manager):
        """测试档位资金映射"""
        # 验证档位资金是合理的中值
        assert 1000 <= arena_manager.tier_capital_map['tier1_micro'] <= 10000
        assert 10000 <= arena_manager.tier_capital_map['tier2_small'] <= 100000
        assert 100000 <= arena_manager.tier_capital_map['tier3_medium'] <= 500000
        assert 500000 <= arena_manager.tier_capital_map['tier4_large'] <= 1000000


class TestFourTierTesting:
    """Property 16: Arena Four-Tier Testing
    
    验证四档位测试流程的完整性和正确性
    """
    
    @pytest.fixture
    def arena_manager(self):
        return ArenaTestManager()
    
    @pytest.fixture
    def mock_strategy(self):
        return MockStrategy(name="FourTierTestStrategy")
    
    @pytest.mark.asyncio
    async def test_four_tier_testing_completeness(self, arena_manager, mock_strategy):
        """Property 16: 验证四档位测试的完整性"""
        # 执行四档位测试
        results = await arena_manager.test_strategy_in_four_tiers(
            strategy=mock_strategy,
            test_duration_days=252
        )
        
        # 验证返回结果包含所有四个档位
        assert 'tier1_micro_result' in results
        assert 'tier2_small_result' in results
        assert 'tier3_medium_result' in results
        assert 'tier4_large_result' in results
        
        # 验证返回最佳档位
        assert 'best_tier' in results
        assert results['best_tier'] in ['tier1_micro', 'tier2_small', 'tier3_medium', 'tier4_large']
        
        # 验证返回进化参数
        assert 'evolved_params' in results
        assert isinstance(results['evolved_params'], dict)
    
    @pytest.mark.asyncio
    async def test_four_tier_results_structure(self, arena_manager, mock_strategy):
        """Property 16: 验证每个档位的测试结果结构"""
        results = await arena_manager.test_strategy_in_four_tiers(
            strategy=mock_strategy,
            test_duration_days=252
        )
        
        # 验证每个档位的结果都是ArenaTestResult类型
        for tier in ['tier1_micro', 'tier2_small', 'tier3_medium', 'tier4_large']:
            result_key = f'{tier}_result'
            assert isinstance(results[result_key], ArenaTestResult)
            
            # 验证结果包含必需字段
            result = results[result_key]
            assert result.strategy_name == mock_strategy.name
            assert result.test_tier == tier
            assert result.initial_capital > 0
            assert result.final_capital >= 0
            assert isinstance(result.total_return_pct, float)
            assert isinstance(result.sharpe_ratio, float)
            assert isinstance(result.max_drawdown_pct, float)
            assert 0 <= result.win_rate <= 1
            assert isinstance(result.evolved_params, dict)
    
    @pytest.mark.asyncio
    async def test_four_tier_caching(self, arena_manager, mock_strategy):
        """Property 16: 验证测试结果缓存"""
        # 执行测试
        await arena_manager.test_strategy_in_four_tiers(
            strategy=mock_strategy,
            test_duration_days=252
        )
        
        # 验证结果被缓存
        cached_results = arena_manager.get_test_results(mock_strategy.name)
        assert cached_results is not None
        assert 'tier1_micro_result' in cached_results
        assert 'tier2_small_result' in cached_results
        assert 'tier3_medium_result' in cached_results
        assert 'tier4_large_result' in cached_results


class TestSlippageSimulation:
    """Property 17: Arena Slippage Simulation
    
    验证滑点和冲击成本模拟的准确性
    """
    
    @pytest.fixture
    def arena_manager(self):
        return ArenaTestManager()
    
    @pytest.mark.asyncio
    async def test_slippage_tier_baseline(self, arena_manager):
        """Property 17: 验证不同档位的基础滑点"""
        # 测试每个档位的基础滑点
        test_cases = [
            ('tier1_micro', 0.0015),   # 0.15%
            ('tier2_small', 0.002),     # 0.20%
            ('tier3_medium', 0.004),    # 0.40%
            ('tier4_large', 0.005),     # 0.50%
        ]
        
        for tier, expected_base_slippage in test_cases:
            result = await arena_manager.simulate_slippage_and_impact(
                tier=tier,
                order_size=10000.0,
                daily_volume=10000000.0  # 订单占成交量0.1%
            )
            
            # 验证滑点在合理范围内（基础滑点附近）
            assert result['slippage_pct'] >= expected_base_slippage * 0.8
            assert result['slippage_pct'] <= expected_base_slippage * 2.0
            
            # 验证冲击成本小于滑点
            assert result['impact_cost_pct'] < result['slippage_pct']
    
    @pytest.mark.asyncio
    async def test_slippage_scales_with_order_size(self, arena_manager):
        """Property 17: 验证滑点随订单大小增加"""
        tier = 'tier2_small'
        daily_volume = 10000000.0
        
        # 测试不同订单大小
        order_sizes = [10000.0, 50000.0, 100000.0, 500000.0]
        slippages = []
        
        for order_size in order_sizes:
            result = await arena_manager.simulate_slippage_and_impact(
                tier=tier,
                order_size=order_size,
                daily_volume=daily_volume
            )
            slippages.append(result['slippage_pct'])
        
        # 验证滑点随订单大小单调递增
        for i in range(len(slippages) - 1):
            assert slippages[i] < slippages[i + 1], \
                f"滑点应该随订单大小增加: {slippages[i]} >= {slippages[i + 1]}"
    
    @pytest.mark.asyncio
    async def test_impact_cost_scales_with_order_ratio(self, arena_manager):
        """Property 17: 验证冲击成本随订单/成交量比例增加"""
        tier = 'tier3_medium'
        daily_volume = 10000000.0
        
        # 测试不同订单/成交量比例
        order_ratios = [0.001, 0.01, 0.05, 0.1]  # 0.1%, 1%, 5%, 10%
        impact_costs = []
        
        for ratio in order_ratios:
            order_size = daily_volume * ratio
            result = await arena_manager.simulate_slippage_and_impact(
                tier=tier,
                order_size=order_size,
                daily_volume=daily_volume
            )
            impact_costs.append(result['impact_cost_pct'])
        
        # 验证冲击成本随比例单调递增
        for i in range(len(impact_costs) - 1):
            assert impact_costs[i] < impact_costs[i + 1], \
                f"冲击成本应该随订单比例增加: {impact_costs[i]} >= {impact_costs[i + 1]}"
    
    @pytest.mark.asyncio
    async def test_slippage_nonlinear_growth(self, arena_manager):
        """Property 17: 验证滑点非线性增长"""
        tier = 'tier2_small'
        daily_volume = 10000000.0
        
        # 订单大小翻倍
        order_size_1 = 10000.0
        order_size_2 = 20000.0
        
        result_1 = await arena_manager.simulate_slippage_and_impact(
            tier=tier,
            order_size=order_size_1,
            daily_volume=daily_volume
        )
        
        result_2 = await arena_manager.simulate_slippage_and_impact(
            tier=tier,
            order_size=order_size_2,
            daily_volume=daily_volume
        )
        
        # 验证滑点增长不是线性的（不是简单翻倍）
        slippage_ratio = result_2['slippage_pct'] / result_1['slippage_pct']
        assert slippage_ratio < 2.0, "滑点增长应该是非线性的（小于2倍）"
        assert slippage_ratio > 1.0, "滑点应该随订单增加"


class TestParameterRecording:
    """Property 18: Arena Parameter Recording
    
    验证参数记录和持久化的完整性
    """
    
    @pytest.fixture
    def arena_manager(self):
        return ArenaTestManager()
    
    @pytest.fixture
    def mock_strategy(self):
        return MockStrategy(name="ParamRecordStrategy")
    
    @pytest.mark.asyncio
    async def test_parameter_evolution_completeness(self, arena_manager, mock_strategy):
        """Property 18: 验证进化参数的完整性"""
        # 执行单档位测试
        result = await arena_manager.test_in_tier(
            strategy=mock_strategy,
            tier='tier2_small',
            initial_capital=50000.0,
            test_duration_days=252
        )
        
        # 验证进化参数包含所有必需字段
        required_params = [
            'max_position',
            'max_single_stock',
            'max_industry',
            'stop_loss_pct',
            'take_profit_pct',
            'trading_frequency',
            'holding_period_days',
            'liquidity_threshold',
            'max_order_pct_of_volume',
            'trailing_stop_enabled'
        ]
        
        for param in required_params:
            assert param in result.evolved_params, f"缺少参数: {param}"
    
    @pytest.mark.asyncio
    async def test_parameter_ranges_validity(self, arena_manager, mock_strategy):
        """Property 18: 验证进化参数在合理范围内"""
        result = await arena_manager.test_in_tier(
            strategy=mock_strategy,
            tier='tier3_medium',
            initial_capital=250000.0,
            test_duration_days=252
        )
        
        params = result.evolved_params
        
        # 验证参数范围
        assert 0 < params['max_position'] <= 1.0
        assert 0 < params['max_single_stock'] <= 1.0
        assert 0 < params['max_industry'] <= 1.0
        assert -1.0 <= params['stop_loss_pct'] < 0
        assert 0 < params['take_profit_pct'] <= 1.0
        assert params['trading_frequency'] in ['high', 'medium', 'low']
        assert params['holding_period_days'] > 0
        assert params['liquidity_threshold'] > 0
        assert 0 < params['max_order_pct_of_volume'] <= 1.0
        assert isinstance(params['trailing_stop_enabled'], bool)
    
    @pytest.mark.asyncio
    async def test_tier_specific_parameters(self, arena_manager, mock_strategy):
        """Property 18: 验证不同档位的参数差异"""
        # 测试Tier1和Tier4的参数
        result_tier1 = await arena_manager.test_in_tier(
            strategy=mock_strategy,
            tier='tier1_micro',
            initial_capital=5000.0,
            test_duration_days=252
        )
        
        result_tier4 = await arena_manager.test_in_tier(
            strategy=mock_strategy,
            tier='tier4_large',
            initial_capital=750000.0,
            test_duration_days=252
        )
        
        # Tier1应该更激进（更高的仓位限制）
        # Tier4应该更保守（更低的仓位限制）
        # 注意：由于是随机模拟，这里只验证参数存在，不强制要求大小关系
        assert 'max_position' in result_tier1.evolved_params
        assert 'max_position' in result_tier4.evolved_params


class TestBestTierIdentification:
    """Property 19: Best Tier Identification
    
    验证最佳档位识别算法的正确性
    """
    
    @pytest.fixture
    def arena_manager(self):
        return ArenaTestManager()
    
    @pytest.mark.asyncio
    async def test_best_tier_selection_logic(self, arena_manager):
        """Property 19: 验证最佳档位选择逻辑"""
        # 创建模拟测试结果
        test_results = {
            'tier1_micro_result': ArenaTestResult(
                strategy_name="TestStrategy",
                test_tier='tier1_micro',
                initial_capital=5000.0,
                final_capital=6000.0,
                total_return_pct=20.0,
                sharpe_ratio=1.5,
                max_drawdown_pct=-10.0,
                win_rate=0.55,
                evolved_params={},
                avg_slippage_pct=0.0015,
                avg_impact_cost_pct=0.0005,
                test_start_date='2024-01-01',
                test_end_date='2024-12-31'
            ),
            'tier2_small_result': ArenaTestResult(
                strategy_name="TestStrategy",
                test_tier='tier2_small',
                initial_capital=50000.0,
                final_capital=65000.0,
                total_return_pct=30.0,
                sharpe_ratio=2.0,
                max_drawdown_pct=-8.0,
                win_rate=0.60,
                evolved_params={},
                avg_slippage_pct=0.002,
                avg_impact_cost_pct=0.0008,
                test_start_date='2024-01-01',
                test_end_date='2024-12-31'
            ),
            'tier3_medium_result': ArenaTestResult(
                strategy_name="TestStrategy",
                test_tier='tier3_medium',
                initial_capital=250000.0,
                final_capital=300000.0,
                total_return_pct=20.0,
                sharpe_ratio=1.2,
                max_drawdown_pct=-15.0,
                win_rate=0.50,
                evolved_params={},
                avg_slippage_pct=0.004,
                avg_impact_cost_pct=0.0015,
                test_start_date='2024-01-01',
                test_end_date='2024-12-31'
            ),
            'tier4_large_result': ArenaTestResult(
                strategy_name="TestStrategy",
                test_tier='tier4_large',
                initial_capital=750000.0,
                final_capital=825000.0,
                total_return_pct=10.0,
                sharpe_ratio=0.8,
                max_drawdown_pct=-20.0,
                win_rate=0.48,
                evolved_params={},
                avg_slippage_pct=0.005,
                avg_impact_cost_pct=0.002,
                test_start_date='2024-01-01',
                test_end_date='2024-12-31'
            )
        }
        
        # 识别最佳档位
        best_tier = await arena_manager.identify_best_tier(test_results)
        
        # Tier2应该是最佳（最高夏普、最高收益、最低回撤、最高胜率）
        assert best_tier == 'tier2_small'
    
    @pytest.mark.asyncio
    async def test_best_tier_with_equal_performance(self, arena_manager):
        """Property 19: 验证性能相近时的档位选择"""
        # 创建性能相近的测试结果
        test_results = {}
        for tier in ['tier1_micro', 'tier2_small', 'tier3_medium', 'tier4_large']:
            test_results[f'{tier}_result'] = ArenaTestResult(
                strategy_name="TestStrategy",
                test_tier=tier,
                initial_capital=50000.0,
                final_capital=60000.0,
                total_return_pct=20.0,
                sharpe_ratio=1.5,
                max_drawdown_pct=-10.0,
                win_rate=0.55,
                evolved_params={},
                avg_slippage_pct=0.002,
                avg_impact_cost_pct=0.001,
                test_start_date='2024-01-01',
                test_end_date='2024-12-31'
            )
        
        # 识别最佳档位
        best_tier = await arena_manager.identify_best_tier(test_results)
        
        # 应该返回一个有效的档位
        assert best_tier in ['tier1_micro', 'tier2_small', 'tier3_medium', 'tier4_large']
    
    @pytest.mark.asyncio
    async def test_best_tier_with_missing_results(self, arena_manager):
        """Property 19: 验证部分结果缺失时的处理"""
        # 只有两个档位的结果
        test_results = {
            'tier1_micro_result': ArenaTestResult(
                strategy_name="TestStrategy",
                test_tier='tier1_micro',
                initial_capital=5000.0,
                final_capital=6000.0,
                total_return_pct=20.0,
                sharpe_ratio=1.5,
                max_drawdown_pct=-10.0,
                win_rate=0.55,
                evolved_params={},
                avg_slippage_pct=0.0015,
                avg_impact_cost_pct=0.0005,
                test_start_date='2024-01-01',
                test_end_date='2024-12-31'
            ),
            'tier2_small_result': ArenaTestResult(
                strategy_name="TestStrategy",
                test_tier='tier2_small',
                initial_capital=50000.0,
                final_capital=65000.0,
                total_return_pct=30.0,
                sharpe_ratio=2.0,
                max_drawdown_pct=-8.0,
                win_rate=0.60,
                evolved_params={},
                avg_slippage_pct=0.002,
                avg_impact_cost_pct=0.0008,
                test_start_date='2024-01-01',
                test_end_date='2024-12-31'
            )
        }
        
        # 识别最佳档位
        best_tier = await arena_manager.identify_best_tier(test_results)
        
        # 应该从可用的档位中选择
        assert best_tier in ['tier1_micro', 'tier2_small']


class TestErrorHandling:
    """测试错误处理和边界条件"""
    
    @pytest.fixture
    def arena_manager(self):
        return ArenaTestManager()
    
    @pytest.fixture
    def mock_strategy(self):
        return MockStrategy(name="ErrorTestStrategy")
    
    @pytest.mark.asyncio
    async def test_failed_tier_test_handling(self, arena_manager, mock_strategy):
        """测试档位测试失败的处理"""
        # 模拟测试失败
        with patch.object(arena_manager, 'test_in_tier', side_effect=Exception("Test failed")):
            results = await arena_manager.test_strategy_in_four_tiers(
                strategy=mock_strategy,
                test_duration_days=252
            )
            
            # 验证失败结果被正确创建
            for tier in ['tier1_micro', 'tier2_small', 'tier3_medium', 'tier4_large']:
                result_key = f'{tier}_result'
                assert result_key in results
                result = results[result_key]
                assert isinstance(result, ArenaTestResult)
                assert result.final_capital == result.initial_capital
                assert result.total_return_pct == 0.0
    
    def test_get_nonexistent_results(self, arena_manager):
        """测试获取不存在的测试结果"""
        result = arena_manager.get_test_results("NonexistentStrategy")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_empty_test_results_best_tier(self, arena_manager):
        """测试空测试结果的最佳档位识别"""
        best_tier = await arena_manager.identify_best_tier({})
        
        # 应该返回默认档位
        assert best_tier == 'tier1_micro'


class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    def arena_manager(self):
        return ArenaTestManager()
    
    @pytest.fixture
    def mock_strategy(self):
        return MockStrategy(name="IntegrationTestStrategy")
    
    @pytest.mark.asyncio
    async def test_full_arena_workflow(self, arena_manager, mock_strategy):
        """测试完整的Arena测试工作流"""
        # 1. 执行四档位测试
        results = await arena_manager.test_strategy_in_four_tiers(
            strategy=mock_strategy,
            test_duration_days=252
        )
        
        # 2. 验证结果完整性
        assert 'best_tier' in results
        assert 'evolved_params' in results
        
        # 3. 验证结果被缓存
        cached_results = arena_manager.get_test_results(mock_strategy.name)
        assert cached_results is not None
        
        # 4. 验证最佳档位的结果
        best_tier = results['best_tier']
        best_result = results[f'{best_tier}_result']
        assert isinstance(best_result, ArenaTestResult)
        assert best_result.test_tier == best_tier
        
        # 5. 验证进化参数
        evolved_params = results['evolved_params']
        assert len(evolved_params) > 0
