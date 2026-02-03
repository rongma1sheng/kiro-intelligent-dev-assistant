# -*- coding: utf-8 -*-
"""实盘策略加载器单元测试

白皮书依据: 第四章 4.2 斯巴达竞技场
测试任务: Task 13.1

测试覆盖:
- Property 20: Live Strategy Selection from Arena
- Property 21: Arena Parameter Inheritance
- Property 22: Parameter Source Logging
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.evolution.live_strategy_loader import (
    LiveStrategyLoader,
    ParameterInheritanceValidator
)
from src.strategies.data_models import (
    StrategyConfig,
    StrategyMetadata,
    ArenaTestResult
)
from src.strategies.base_strategy import Strategy


class MockStrategy(Strategy):
    """Mock策略类用于测试"""
    
    def __init__(self, name: str, config: StrategyConfig):
        super().__init__(name=name, config=config)
    
    async def generate_signals(self, market_data):
        return []
    
    async def calculate_position_sizes(self, signals, current_positions, available_capital):
        return {}
    
    async def apply_risk_controls(self, positions):
        return positions


class TestLiveStrategyLoader:
    """测试LiveStrategyLoader核心功能"""
    
    @pytest.fixture
    def loader(self):
        """创建LiveStrategyLoader实例"""
        return LiveStrategyLoader()
    
    @pytest.fixture
    def arena_result_tier2(self):
        """创建Tier2的Arena测试结果"""
        return ArenaTestResult(
            strategy_name="TestStrategy",
            test_tier='tier2_small',
            initial_capital=50000.0,
            final_capital=60000.0,
            total_return_pct=20.0,
            sharpe_ratio=1.5,
            max_drawdown_pct=-10.0,
            win_rate=0.55,
            evolved_params={
                'max_position': 0.85,
                'max_single_stock': 0.15,
                'max_industry': 0.40,
                'stop_loss_pct': -0.06,
                'take_profit_pct': 0.10,
                'trading_frequency': 'medium',
                'holding_period_days': 3,
                'liquidity_threshold': 1000000.0,
                'max_order_pct_of_volume': 0.05,
                'trailing_stop_enabled': True
            },
            avg_slippage_pct=0.002,
            avg_impact_cost_pct=0.001,
            test_start_date='2024-01-01',
            test_end_date='2024-12-31'
        )
    
    @pytest.fixture
    def certified_metadata(self, arena_result_tier2):
        """创建已认证的策略元数据"""
        return StrategyMetadata(
            strategy_name="TestStrategy",
            strategy_class="MockStrategy",
            best_tier='tier2_small',
            arena_results={'tier2_small': arena_result_tier2},
            z2h_certified=True,
            z2h_certification_date='2024-12-31'
        )
    
    def test_initialization(self, loader):
        """测试初始化"""
        assert loader is not None
        assert isinstance(loader.load_history, list)
        assert len(loader.load_history) == 0
    
    @pytest.mark.asyncio
    async def test_load_strategy_config_success(self, loader, certified_metadata):
        """测试成功加载策略配置"""
        config = await loader.load_strategy_config_from_arena(
            strategy_metadata=certified_metadata,
            target_tier='tier2_small'
        )
        
        # 验证配置类型
        assert isinstance(config, StrategyConfig)
        
        # 验证配置字段
        assert config.strategy_name == "TestStrategy"
        assert config.capital_tier == 'tier2_small'
        assert config.max_position == 0.85
        assert config.max_single_stock == 0.15
        assert config.max_industry == 0.40
        assert config.stop_loss_pct == -0.06
        assert config.take_profit_pct == 0.10
        assert config.trading_frequency == 'medium'
        assert config.holding_period_days == 3


class TestLiveStrategySelection:
    """Property 20: Live Strategy Selection from Arena
    
    验证从Arena结果选择实盘策略的正确据?
    """
    
    @pytest.fixture
    def loader(self):
        return LiveStrategyLoader()
    
    @pytest.fixture
    def multi_tier_metadata(self):
        """创建包含多个档位Arena结果的元数据"""
        arena_results = {}
        
        for tier, capital in [
            ('tier1_micro', 5000.0),
            ('tier2_small', 50000.0),
            ('tier3_medium', 250000.0),
            ('tier4_large', 750000.0)
        ]:
            arena_results[tier] = ArenaTestResult(
                strategy_name="MultiTierStrategy",
                test_tier=tier,
                initial_capital=capital,
                final_capital=capital * 1.2,
                total_return_pct=20.0,
                sharpe_ratio=1.5,
                max_drawdown_pct=-10.0,
                win_rate=0.55,
                evolved_params={
                    'max_position': 0.85,
                    'max_single_stock': 0.15,
                    'max_industry': 0.40,
                    'stop_loss_pct': -0.06,
                    'take_profit_pct': 0.10,
                    'trading_frequency': 'medium',
                    'holding_period_days': 3
                },
                avg_slippage_pct=0.002,
                avg_impact_cost_pct=0.001,
                test_start_date='2024-01-01',
                test_end_date='2024-12-31'
            )
        
        return StrategyMetadata(
            strategy_name="MultiTierStrategy",
            strategy_class="MockStrategy",
            best_tier='tier2_small',
            arena_results=arena_results,
            z2h_certified=True,
            z2h_certification_date='2024-12-31'
        )
    
    @pytest.mark.asyncio
    async def test_select_tier1_to_tier4(self, loader, multi_tier_metadata):
        """Property 20: 验证Tier1到Tier4使用对应档位的Arena结果"""
        for tier in ['tier1_micro', 'tier2_small', 'tier3_medium', 'tier4_large']:
            config = await loader.load_strategy_config_from_arena(
                strategy_metadata=multi_tier_metadata,
                target_tier=tier
            )
            
            # 验证使用了对应档位的配置
            assert config.capital_tier == tier
    
    @pytest.mark.asyncio
    async def test_select_tier5_uses_tier4(self, loader, multi_tier_metadata):
        """Property 20: 验证Tier5使用Tier4的Arena结果"""
        config = await loader.load_strategy_config_from_arena(
            strategy_metadata=multi_tier_metadata,
            target_tier='tier5_million'
        )
        
        # Tier5应该使用Tier4的参数，但capital_tier可能保持为tier4_large
        assert config is not None
        # 参数应该来自Tier4的Arena结果
        assert config.max_position == 0.85
    
    @pytest.mark.asyncio
    async def test_select_tier6_uses_tier4(self, loader, multi_tier_metadata):
        """Property 20: 验证Tier6使用Tier4的Arena结果"""
        config = await loader.load_strategy_config_from_arena(
            strategy_metadata=multi_tier_metadata,
            target_tier='tier6_ten_million'
        )
        
        # Tier6应该使用Tier4的参数，但capital_tier可能保持为tier4_large
        assert config is not None
        # 参数应该来自Tier4的Arena结果
        assert config.max_position == 0.85
    
    @pytest.mark.asyncio
    async def test_fallback_to_best_tier(self, loader):
        """Property 20: 验证缺少目标档位时降级到最佳档位"""
        # 只有Tier2的Arena结果
        arena_result = ArenaTestResult(
            strategy_name="LimitedStrategy",
            test_tier='tier2_small',
            initial_capital=50000.0,
            final_capital=60000.0,
            total_return_pct=20.0,
            sharpe_ratio=1.5,
            max_drawdown_pct=-10.0,
            win_rate=0.55,
            evolved_params={
                'max_position': 0.85,
                'max_single_stock': 0.15,
                'max_industry': 0.40,
                'stop_loss_pct': -0.06,
                'take_profit_pct': 0.10,
                'trading_frequency': 'medium',
                'holding_period_days': 3
            },
            avg_slippage_pct=0.002,
            avg_impact_cost_pct=0.001,
            test_start_date='2024-01-01',
            test_end_date='2024-12-31'
        )
        
        metadata = StrategyMetadata(
            strategy_name="LimitedStrategy",
            strategy_class="MockStrategy",
            best_tier='tier2_small',
            arena_results={'tier2_small': arena_result},
            z2h_certified=True,
            z2h_certification_date='2024-12-31'
        )
        
        # 请求Tier3，但只有Tier2的结果
        config = await loader.load_strategy_config_from_arena(
            strategy_metadata=metadata,
            target_tier='tier3_medium'
        )
        
        # 应该降级使用Tier2（最佳档位）的参数
        assert config is not None
        assert config.max_position == 0.85


class TestParameterInheritance:
    """Property 21: Arena Parameter Inheritance
    
    验证参数继承的正确据?
    """
    
    @pytest.fixture
    def loader(self):
        return LiveStrategyLoader()
    
    @pytest.fixture
    def arena_result_with_params(self):
        """创建包含完整参数的Arena结果"""
        return ArenaTestResult(
            strategy_name="ParamTestStrategy",
            test_tier='tier2_small',
            initial_capital=50000.0,
            final_capital=60000.0,
            total_return_pct=20.0,
            sharpe_ratio=1.5,
            max_drawdown_pct=-10.0,
            win_rate=0.55,
            evolved_params={
                'max_position': 0.88,
                'max_single_stock': 0.18,
                'max_industry': 0.45,
                'stop_loss_pct': -0.07,
                'take_profit_pct': 0.12,
                'trading_frequency': 'high',
                'holding_period_days': 2,
                'liquidity_threshold': 2000000.0,
                'max_order_pct_of_volume': 0.03,
                'trailing_stop_enabled': False
            },
            avg_slippage_pct=0.002,
            avg_impact_cost_pct=0.001,
            test_start_date='2024-01-01',
            test_end_date='2024-12-31'
        )
    
    @pytest.mark.asyncio
    async def test_all_parameters_inherited(self, loader, arena_result_with_params):
        """Property 21: 验证所有参数都被正确继承"""
        metadata = StrategyMetadata(
            strategy_name="ParamTestStrategy",
            strategy_class="MockStrategy",
            best_tier='tier2_small',
            arena_results={'tier2_small': arena_result_with_params},
            z2h_certified=True,
            z2h_certification_date='2024-12-31'
        )
        
        config = await loader.load_strategy_config_from_arena(
            strategy_metadata=metadata,
            target_tier='tier2_small'
        )
        
        # 验证所有参数都被继承
        assert config.max_position == 0.88
        assert config.max_single_stock == 0.18
        assert config.max_industry == 0.45
        assert config.stop_loss_pct == -0.07
        assert config.take_profit_pct == 0.12
        assert config.trading_frequency == 'high'
        assert config.holding_period_days == 2
    
    @pytest.mark.asyncio
    async def test_parameter_values_exact_match(self, loader, arena_result_with_params):
        """Property 21: 验证参数值精确匹配"""
        metadata = StrategyMetadata(
            strategy_name="ParamTestStrategy",
            strategy_class="MockStrategy",
            best_tier='tier2_small',
            arena_results={'tier2_small': arena_result_with_params},
            z2h_certified=True,
            z2h_certification_date='2024-12-31'
        )
        
        config = await loader.load_strategy_config_from_arena(
            strategy_metadata=metadata,
            target_tier='tier2_small'
        )
        
        # 验证参数值精确匹配（不是近似值）
        evolved_params = arena_result_with_params.evolved_params
        assert config.max_position == evolved_params['max_position']
        assert config.max_single_stock == evolved_params['max_single_stock']
        assert config.max_industry == evolved_params['max_industry']
        assert config.stop_loss_pct == evolved_params['stop_loss_pct']
        assert config.take_profit_pct == evolved_params['take_profit_pct']


class TestParameterSourceLogging:
    """Property 22: Parameter Source Logging
    
    验证参数来源日志记录的完整据?
    """
    
    @pytest.fixture
    def loader(self):
        return LiveStrategyLoader()
    
    @pytest.fixture
    def certified_metadata(self):
        arena_result = ArenaTestResult(
            strategy_name="LogTestStrategy",
            test_tier='tier2_small',
            initial_capital=50000.0,
            final_capital=60000.0,
            total_return_pct=20.0,
            sharpe_ratio=1.5,
            max_drawdown_pct=-10.0,
            win_rate=0.55,
            evolved_params={
                'max_position': 0.85,
                'max_single_stock': 0.15,
                'max_industry': 0.40,
                'stop_loss_pct': -0.06,
                'take_profit_pct': 0.10,
                'trading_frequency': 'medium',
                'holding_period_days': 3
            },
            avg_slippage_pct=0.002,
            avg_impact_cost_pct=0.001,
            test_start_date='2024-01-01',
            test_end_date='2024-12-31'
        )
        
        return StrategyMetadata(
            strategy_name="LogTestStrategy",
            strategy_class="MockStrategy",
            best_tier='tier2_small',
            arena_results={'tier2_small': arena_result},
            z2h_certified=True,
            z2h_certification_date='2024-12-31'
        )
    
    @pytest.mark.asyncio
    async def test_parameter_source_logged(self, loader, certified_metadata):
        """Property 22: 验证参数来源被记录"""
        # 加载配置
        await loader.load_strategy_config_from_arena(
            strategy_metadata=certified_metadata,
            target_tier='tier2_small'
        )
        
        # 验证日志记录
        history = loader.get_load_history()
        assert len(history) == 1
        
        log_entry = history[0]
        assert 'timestamp' in log_entry
        assert log_entry['strategy_name'] == "LogTestStrategy"
        assert log_entry['target_tier'] == 'tier2_small'
        assert log_entry['arena_tier'] == 'tier2_small'
        assert 'parameters' in log_entry
    
    @pytest.mark.asyncio
    async def test_logged_parameters_completeness(self, loader, certified_metadata):
        """Property 22: 验证记录的参数完整性"""
        await loader.load_strategy_config_from_arena(
            strategy_metadata=certified_metadata,
            target_tier='tier2_small'
        )
        
        history = loader.get_load_history()
        log_entry = history[0]
        params = log_entry['parameters']
        
        # 验证记录了所有关键参数
        required_params = [
            'max_position',
            'max_single_stock',
            'max_industry',
            'stop_loss_pct',
            'take_profit_pct',
            'trading_frequency',
            'holding_period_days'
        ]
        
        for param in required_params:
            assert param in params, f"缺少参数: {param}"
    
    @pytest.mark.asyncio
    async def test_multiple_loads_logged(self, loader, certified_metadata):
        """Property 22: 验证多次加载都被记录"""
        # 加载3次
        for _ in range(3):
            await loader.load_strategy_config_from_arena(
                strategy_metadata=certified_metadata,
                target_tier='tier2_small'
            )
        
        # 验证所有加载都被记录
        history = loader.get_load_history()
        assert len(history) == 3
    
    @pytest.mark.asyncio
    async def test_get_load_history_by_strategy(self, loader):
        """Property 22: 验证按策略名查询加载历史"""
        # 加载两个不同的策略
        for strategy_name in ["Strategy1", "Strategy2"]:
            arena_result = ArenaTestResult(
                strategy_name=strategy_name,
                test_tier='tier2_small',
                initial_capital=50000.0,
                final_capital=60000.0,
                total_return_pct=20.0,
                sharpe_ratio=1.5,
                max_drawdown_pct=-10.0,
                win_rate=0.55,
                evolved_params={
                    'max_position': 0.85,
                    'max_single_stock': 0.15,
                    'max_industry': 0.40,
                    'stop_loss_pct': -0.06,
                    'take_profit_pct': 0.10,
                    'trading_frequency': 'medium',
                    'holding_period_days': 3
                },
                avg_slippage_pct=0.002,
                avg_impact_cost_pct=0.001,
                test_start_date='2024-01-01',
                test_end_date='2024-12-31'
            )
            
            metadata = StrategyMetadata(
                strategy_name=strategy_name,
                strategy_class="MockStrategy",
                best_tier='tier2_small',
                arena_results={'tier2_small': arena_result},
                z2h_certified=True,
                z2h_certification_date='2024-12-31'
            )
            
            await loader.load_strategy_config_from_arena(
                strategy_metadata=metadata,
                target_tier='tier2_small'
            )
        
        # 查询Strategy1的历史
        strategy1_history = loader.get_load_history("Strategy1")
        assert len(strategy1_history) == 1
        assert strategy1_history[0]['strategy_name'] == "Strategy1"
        
        # 查询Strategy2的历史
        strategy2_history = loader.get_load_history("Strategy2")
        assert len(strategy2_history) == 1
        assert strategy2_history[0]['strategy_name'] == "Strategy2"


class TestMetadataValidation:
    """测试元数据验证"""
    
    @pytest.fixture
    def loader(self):
        return LiveStrategyLoader()
    
    @pytest.mark.asyncio
    async def test_uncertified_strategy_rejected(self, loader):
        """测试未认证的策略被拒绝"""
        arena_result = ArenaTestResult(
            strategy_name="UncertifiedStrategy",
            test_tier='tier2_small',
            initial_capital=50000.0,
            final_capital=60000.0,
            total_return_pct=20.0,
            sharpe_ratio=1.5,
            max_drawdown_pct=-10.0,
            win_rate=0.55,
            evolved_params={
                'max_position': 0.85,
                'max_single_stock': 0.15,
                'max_industry': 0.40,
                'stop_loss_pct': -0.06,
                'take_profit_pct': 0.10,
                'trading_frequency': 'medium',
                'holding_period_days': 3
            },
            avg_slippage_pct=0.002,
            avg_impact_cost_pct=0.001,
            test_start_date='2024-01-01',
            test_end_date='2024-12-31'
        )
        
        metadata = StrategyMetadata(
            strategy_name="UncertifiedStrategy",
            strategy_class="MockStrategy",
            best_tier='tier2_small',
            arena_results={'tier2_small': arena_result},
            z2h_certified=False,  # 未认证
            z2h_certification_date=None
        )
        
        # 应该抛出异常
        with pytest.raises(ValueError) as exc_info:
            await loader.load_strategy_config_from_arena(
                strategy_metadata=metadata,
                target_tier='tier2_small'
            )
        
        assert "未获得Z2H认证" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_missing_arena_results_rejected(self, loader):
        """测试缺少Arena结果的策略被拒绝"""
        metadata = StrategyMetadata(
            strategy_name="NoArenaStrategy",
            strategy_class="MockStrategy",
            best_tier='tier2_small',
            arena_results={},  # 空的Arena结果
            z2h_certified=True,
            z2h_certification_date='2024-12-31'
        )
        
        with pytest.raises(ValueError) as exc_info:
            await loader.load_strategy_config_from_arena(
                strategy_metadata=metadata,
                target_tier='tier2_small'
            )
        
        assert "缺少Arena测试结果" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_missing_best_tier_rejected(self, loader):
        """测试缺少最佳档位的策略被拒绝"""
        arena_result = ArenaTestResult(
            strategy_name="NoBestTierStrategy",
            test_tier='tier2_small',
            initial_capital=50000.0,
            final_capital=60000.0,
            total_return_pct=20.0,
            sharpe_ratio=1.5,
            max_drawdown_pct=-10.0,
            win_rate=0.55,
            evolved_params={
                'max_position': 0.85,
                'max_single_stock': 0.15,
                'max_industry': 0.40,
                'stop_loss_pct': -0.06,
                'take_profit_pct': 0.10,
                'trading_frequency': 'medium',
                'holding_period_days': 3
            },
            avg_slippage_pct=0.002,
            avg_impact_cost_pct=0.001,
            test_start_date='2024-01-01',
            test_end_date='2024-12-31'
        )
        
        metadata = StrategyMetadata(
            strategy_name="NoBestTierStrategy",
            strategy_class="MockStrategy",
            best_tier=None,  # 缺少最佳档位
            arena_results={'tier2_small': arena_result},
            z2h_certified=True,
            z2h_certification_date='2024-12-31'
        )
        
        with pytest.raises(ValueError) as exc_info:
            await loader.load_strategy_config_from_arena(
                strategy_metadata=metadata,
                target_tier='tier2_small'
            )
        
        assert "未识别最佳档位" in str(exc_info.value)


class TestParameterInheritanceValidator:
    """测试参数继承验证器"""
    
    @pytest.fixture
    def validator(self):
        return ParameterInheritanceValidator()
    
    @pytest.fixture
    def arena_result(self):
        return ArenaTestResult(
            strategy_name="ValidatorTestStrategy",
            test_tier='tier2_small',
            initial_capital=50000.0,
            final_capital=60000.0,
            total_return_pct=20.0,
            sharpe_ratio=1.5,
            max_drawdown_pct=-10.0,
            win_rate=0.55,
            evolved_params={
                'max_position': 0.85,
                'max_single_stock': 0.15,
                'max_industry': 0.40,
                'stop_loss_pct': -0.06,
                'take_profit_pct': 0.10,
                'trading_frequency': 'medium',
                'holding_period_days': 3
            },
            avg_slippage_pct=0.002,
            avg_impact_cost_pct=0.001,
            test_start_date='2024-01-01',
            test_end_date='2024-12-31'
        )
    
    def test_validate_matching_parameters(self, validator, arena_result):
        """测试参数完全匹配的验证"""
        live_config = StrategyConfig(
            strategy_name="ValidatorTestStrategy",
            capital_tier='tier2_small',
            max_position=0.85,
            max_single_stock=0.15,
            max_industry=0.40,
            stop_loss_pct=-0.06,
            take_profit_pct=0.10,
            trailing_stop_enabled=False,
            trading_frequency='medium',
            holding_period_days=3
        )
        
        result = validator.validate_parameter_inheritance(live_config, arena_result)
        
        assert result['valid'] is True
        assert len(result['matched_params']) >= 7
        assert len(result['mismatched_params']) == 0
    
    def test_validate_mismatched_parameters(self, validator, arena_result):
        """测试参数不匹配的验证"""
        live_config = StrategyConfig(
            strategy_name="ValidatorTestStrategy",
            capital_tier='tier2_small',
            max_position=0.90,  # 不匹配
            max_single_stock=0.20,  # 不匹配
            max_industry=0.40,
            stop_loss_pct=-0.06,
            take_profit_pct=0.10,
            trailing_stop_enabled=False,
            trading_frequency='medium',
            holding_period_days=3
        )
        
        result = validator.validate_parameter_inheritance(live_config, arena_result)
        
        assert result['valid'] is False
        assert len(result['mismatched_params']) == 2
        
        # 验证不匹配的参数详情
        mismatched_params = {p['param']: p for p in result['mismatched_params']}
        assert 'max_position' in mismatched_params
        assert mismatched_params['max_position']['live_value'] == 0.90
        assert mismatched_params['max_position']['arena_value'] == 0.85


class TestLoadStrategyForTier:
    """测试为指定档位加载策略实例"""
    
    @pytest.fixture
    def loader(self):
        return LiveStrategyLoader()
    
    @pytest.fixture
    def certified_metadata(self):
        arena_result = ArenaTestResult(
            strategy_name="InstanceTestStrategy",
            test_tier='tier2_small',
            initial_capital=50000.0,
            final_capital=60000.0,
            total_return_pct=20.0,
            sharpe_ratio=1.5,
            max_drawdown_pct=-10.0,
            win_rate=0.55,
            evolved_params={
                'max_position': 0.85,
                'max_single_stock': 0.15,
                'max_industry': 0.40,
                'stop_loss_pct': -0.06,
                'take_profit_pct': 0.10,
                'trading_frequency': 'medium',
                'holding_period_days': 3
            },
            avg_slippage_pct=0.002,
            avg_impact_cost_pct=0.001,
            test_start_date='2024-01-01',
            test_end_date='2024-12-31'
        )
        
        return StrategyMetadata(
            strategy_name="InstanceTestStrategy",
            strategy_class="MockStrategy",
            best_tier='tier2_small',
            arena_results={'tier2_small': arena_result},
            z2h_certified=True,
            z2h_certification_date='2024-12-31'
        )
    
    @pytest.mark.asyncio
    async def test_load_strategy_instance(self, loader, certified_metadata):
        """测试加载策略实例"""
        strategy = await loader.load_strategy_for_tier(
            strategy_metadata=certified_metadata,
            tier='tier2_small',
            strategy_class=MockStrategy
        )
        
        # 验证策略实例
        assert isinstance(strategy, MockStrategy)
        assert strategy.name == "InstanceTestStrategy"
        assert strategy.config.capital_tier == 'tier2_small'
        assert strategy.config.max_position == 0.85
