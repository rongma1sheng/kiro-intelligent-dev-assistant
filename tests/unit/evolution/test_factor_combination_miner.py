"""因子组合与交互因子挖掘器单元测试

白皮书依据: 第四章 4.1.15 因子组合与交互因子挖掘器
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evolution.factor_combination import (
    FactorCombinationInteractionMiner,
    FactorCombinationConfig,
    factor_interaction_term,
    nonlinear_factor_combination,
    conditional_factor_exposure,
    factor_timing_signal,
    multi_factor_synergy,
    factor_neutralization
)
from src.evolution.genetic_miner import EvolutionConfig


@pytest.fixture
def sample_data():
    """生成测试数据"""
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=150, freq='D')
    
    # 生成6只股票的价格数据
    data = pd.DataFrame({
        'stock_A': 100 + np.cumsum(np.random.randn(150) * 2),
        'stock_B': 100 + np.cumsum(np.random.randn(150) * 2),
        'stock_C': 100 + np.cumsum(np.random.randn(150) * 2),
        'stock_D': 100 + np.cumsum(np.random.randn(150) * 2),
        'stock_E': 100 + np.cumsum(np.random.randn(150) * 2),
        'stock_F': 100 + np.cumsum(np.random.randn(150) * 2)
    }, index=dates)
    
    return data


@pytest.fixture
def sample_returns(sample_data):
    """生成收益率数据"""
    returns = sample_data.pct_change().mean(axis=1)
    return returns.fillna(0)


@pytest.fixture
def sample_factors(sample_data):
    """生成测试因子"""
    # 创建几个简单的因子
    factors = {
        'momentum': sample_data.pct_change(10).mean(axis=1).fillna(0),
        'volatility': sample_data.pct_change().rolling(20).std().mean(axis=1).fillna(0),
        'volume': pd.Series(np.random.rand(len(sample_data)) * 1000, index=sample_data.index)
    }
    return factors


@pytest.fixture
def miner():
    """创建挖掘器实例"""
    config = EvolutionConfig(population_size=10, max_generations=5)
    combination_config = FactorCombinationConfig(
        interaction_window=30,
        timing_window=60,
        synergy_window=45
    )
    return FactorCombinationInteractionMiner(
        config=config,
        combination_config=combination_config
    )


class TestFactorCombinationConfig:
    """测试因子组合配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = FactorCombinationConfig()
        
        assert config.interaction_window == 60
        assert config.timing_window == 120
        assert config.synergy_window == 90
        assert config.correlation_threshold == 0.3
        assert config.max_factors == 5
        assert config.neutralization_method == 'orthogonal'
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = FactorCombinationConfig(
            interaction_window=30,
            timing_window=90,
            max_factors=10
        )
        
        assert config.interaction_window == 30
        assert config.timing_window == 90
        assert config.max_factors == 10


class TestFactorCombinationOperators:
    """测试因子组合算子"""
    
    def test_factor_interaction_term_multiply(self, sample_factors):
        """测试因子交互项-乘法"""
        factor1 = sample_factors['momentum']
        factor2 = sample_factors['volatility']
        
        result = factor_interaction_term(factor1, factor2, method='multiply')
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(factor1)
        assert not result.isna().all()
    
    def test_factor_interaction_term_add(self, sample_factors):
        """测试因子交互项-加法"""
        factor1 = sample_factors['momentum']
        factor2 = sample_factors['volatility']
        
        result = factor_interaction_term(factor1, factor2, method='add')
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(factor1)
    
    def test_factor_interaction_term_empty(self):
        """测试空因子交互"""
        empty_factor = pd.Series(dtype='float64')
        result = factor_interaction_term(empty_factor, empty_factor)
        
        assert isinstance(result, pd.Series)
        assert len(result) == 0
    
    def test_nonlinear_factor_combination_polynomial(self, sample_factors):
        """测试非线性因子组合-多项式"""
        result = nonlinear_factor_combination(
            sample_factors,
            method='polynomial',
            degree=2
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) > 0
        assert not result.isna().all()
    
    def test_nonlinear_factor_combination_exponential(self, sample_factors):
        """测试非线性因子组合-指数"""
        result = nonlinear_factor_combination(
            sample_factors,
            method='exponential'
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) > 0
    
    def test_nonlinear_factor_combination_empty(self):
        """测试空因子组合"""
        empty_factors = {}
        result = nonlinear_factor_combination(empty_factors)
        
        assert isinstance(result, pd.Series)
        assert len(result) == 0
    
    def test_conditional_factor_exposure(self, sample_factors):
        """测试条件因子暴露"""
        factor = sample_factors['momentum']
        condition = sample_factors['volatility']
        
        result = conditional_factor_exposure(factor, condition, threshold=0.0)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(factor)
        assert not result.isna().all()
    
    def test_factor_timing_signal(self, sample_factors, sample_returns):
        """测试因子择时信号"""
        factor = sample_factors['momentum']
        
        result = factor_timing_signal(factor, sample_returns, window=60)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(factor)
        assert not result.isna().all()
    
    def test_multi_factor_synergy(self, sample_factors):
        """测试多因子协同"""
        result = multi_factor_synergy(sample_factors, window=45)
        
        assert isinstance(result, pd.Series)
        assert len(result) > 0
        assert not result.isna().all()
    
    def test_factor_neutralization_orthogonal(self, sample_factors):
        """测试因子中性化-正交方法"""
        factor = sample_factors['momentum']
        neutralize_factors = {
            'volatility': sample_factors['volatility']
        }
        
        result = factor_neutralization(
            factor,
            neutralize_factors,
            method='orthogonal'
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(factor)
        assert not result.isna().all()
    
    def test_factor_neutralization_regression(self, sample_factors):
        """测试因子中性化-回归方法"""
        factor = sample_factors['momentum']
        neutralize_factors = {
            'volatility': sample_factors['volatility']
        }
        
        result = factor_neutralization(
            factor,
            neutralize_factors,
            method='regression'
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(factor)


class TestFactorCombinationInteractionMiner:
    """测试因子组合与交互因子挖掘器"""
    
    def test_initialization(self, miner):
        """测试初始化"""
        assert miner is not None
        assert isinstance(miner.combination_config, FactorCombinationConfig)
        assert hasattr(miner, 'combination_operators')
        assert len(miner.combination_operators) == 6
    
    def test_operator_registration(self, miner):
        """测试算子注册"""
        expected_operators = [
            'factor_interaction_term',
            'nonlinear_factor_combination',
            'conditional_factor_exposure',
            'factor_timing_signal',
            'multi_factor_synergy',
            'factor_neutralization'
        ]
        
        for op in expected_operators:
            assert op in miner.combination_operators
            assert op in miner.operator_whitelist
    
    @pytest.mark.asyncio
    async def test_mine_factors(
        self, miner, sample_data, sample_returns, sample_factors
    ):
        """测试因子挖掘"""
        factors = await miner.mine_factors(
            data=sample_data,
            returns=sample_returns,
            existing_factors=sample_factors,
            generations=2
        )
        
        assert isinstance(factors, list)
        # 可能没有找到有效因子,但不应该报错
    
    def test_calculate_combination_factor_interaction(
        self, miner, sample_factors
    ):
        """测试计算交互因子"""
        factor = miner.calculate_combination_factor(
            'factor_interaction_term',
            {
                'momentum': sample_factors['momentum'],
                'volatility': sample_factors['volatility']
            },
            method='multiply'
        )
        
        assert isinstance(factor, pd.Series)
        assert len(factor) > 0
    
    def test_calculate_combination_factor_nonlinear(
        self, miner, sample_factors
    ):
        """测试计算非线性组合因子"""
        factor = miner.calculate_combination_factor(
            'nonlinear_factor_combination',
            sample_factors,
            method='polynomial',
            degree=2
        )
        
        assert isinstance(factor, pd.Series)
        assert len(factor) > 0
    
    def test_calculate_combination_factor_unknown(self, miner, sample_factors):
        """测试未知算子"""
        factor = miner.calculate_combination_factor(
            'unknown_operator',
            sample_factors
        )
        
        assert isinstance(factor, pd.Series)
        assert len(factor) == 0
    
    def test_generate_interaction_factors(self, miner, sample_factors):
        """测试生成交互因子"""
        interactions = miner.generate_interaction_factors(
            sample_factors,
            max_combinations=5
        )
        
        assert isinstance(interactions, dict)
        assert len(interactions) > 0
        
        # 检查每个交互因子
        for name, factor in interactions.items():
            assert isinstance(factor, pd.Series)
            assert len(factor) > 0
            assert '_x_' in name
    
    def test_generate_nonlinear_combinations(self, miner, sample_factors):
        """测试生成非线性组合"""
        combinations = miner.generate_nonlinear_combinations(
            sample_factors,
            methods=['polynomial', 'exponential'],
            max_combinations=3
        )
        
        assert isinstance(combinations, dict)
        assert len(combinations) > 0
        
        for name, factor in combinations.items():
            assert isinstance(factor, pd.Series)
            assert 'nonlinear_' in name
    
    def test_generate_conditional_factors(self, miner, sample_factors):
        """测试生成条件因子"""
        conditional = miner.generate_conditional_factors(
            sample_factors,
            max_combinations=3
        )
        
        assert isinstance(conditional, dict)
        assert len(conditional) > 0
        
        for name, factor in conditional.items():
            assert isinstance(factor, pd.Series)
            assert '_cond_' in name
    
    def test_generate_timing_signals(
        self, miner, sample_factors, sample_returns
    ):
        """测试生成择时信号"""
        signals = miner.generate_timing_signals(sample_factors, sample_returns)
        
        assert isinstance(signals, dict)
        assert len(signals) > 0
        
        for name, signal in signals.items():
            assert isinstance(signal, pd.Series)
            assert '_timing' in name
    
    def test_generate_neutralized_factors(self, miner, sample_factors):
        """测试生成中性化因子"""
        neutralized = miner.generate_neutralized_factors(sample_factors)
        
        assert isinstance(neutralized, dict)
        assert len(neutralized) > 0
        
        for name, factor in neutralized.items():
            assert isinstance(factor, pd.Series)
            assert '_neutralized' in name
    
    def test_analyze_factor_synergy(self, miner, sample_factors):
        """测试分析因子协同"""
        synergy = miner.analyze_factor_synergy(sample_factors)
        
        assert isinstance(synergy, pd.Series)
        assert len(synergy) > 0
    
    def test_generate_all_combinations(
        self, miner, sample_factors, sample_returns
    ):
        """测试生成所有组合"""
        all_combinations = miner.generate_all_combinations(
            sample_factors,
            sample_returns,
            max_per_type=3
        )
        
        assert isinstance(all_combinations, dict)
        assert len(all_combinations) > 0
        
        # 应该包含多种类型的组合
        has_interaction = any('_x_' in name for name in all_combinations.keys())
        has_nonlinear = any('nonlinear_' in name for name in all_combinations.keys())
        has_timing = any('_timing' in name for name in all_combinations.keys())
        
        assert has_interaction or has_nonlinear or has_timing


class TestFactorCombinationEdgeCases:
    """测试因子组合边界情况"""
    
    def test_single_factor(self):
        """测试单个因子"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        factor = pd.Series(np.random.randn(100), index=dates)
        
        factors = {'factor1': factor}
        
        result = nonlinear_factor_combination(factors, method='polynomial')
        assert isinstance(result, pd.Series)
        assert len(result) == len(factor)
    
    def test_misaligned_factors(self):
        """测试不对齐的因子"""
        dates1 = pd.date_range(start='2023-01-01', periods=100, freq='D')
        dates2 = pd.date_range(start='2023-01-15', periods=100, freq='D')
        
        factor1 = pd.Series(np.random.randn(100), index=dates1)
        factor2 = pd.Series(np.random.randn(100), index=dates2)
        
        result = factor_interaction_term(factor1, factor2)
        assert isinstance(result, pd.Series)
        # 应该只包含公共索引
        assert len(result) < 100
    
    def test_nan_values(self):
        """测试包含NaN的因子"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        factor1 = pd.Series(np.random.randn(100), index=dates)
        factor2 = pd.Series(np.random.randn(100), index=dates)
        
        # 添加一些NaN
        factor1.iloc[10:20] = np.nan
        factor2.iloc[15:25] = np.nan
        
        result = factor_interaction_term(factor1, factor2)
        assert isinstance(result, pd.Series)
        assert not result.isna().all()
    
    def test_zero_variance_factor(self):
        """测试零方差因子"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        factor1 = pd.Series([1.0] * 100, index=dates)
        factor2 = pd.Series(np.random.randn(100), index=dates)
        
        result = factor_interaction_term(factor1, factor2)
        assert isinstance(result, pd.Series)
        assert len(result) == 100


class TestFactorCombinationPerformance:
    """测试因子组合性能"""
    
    def test_large_factor_set_performance(self):
        """测试大因子集性能"""
        import time
        
        # 生成10个因子
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=250, freq='D')
        factors = {
            f'factor_{i}': pd.Series(np.random.randn(250), index=dates)
            for i in range(10)
        }
        
        start_time = time.time()
        result = multi_factor_synergy(factors, window=60)
        elapsed = time.time() - start_time
        
        assert isinstance(result, pd.Series)
        assert elapsed < 5.0  # 应该在5秒内完成
    
    def test_interaction_generation_performance(self, miner):
        """测试交互因子生成性能"""
        import time
        
        # 生成5个因子
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
        factors = {
            f'factor_{i}': pd.Series(np.random.randn(200), index=dates)
            for i in range(5)
        }
        
        start_time = time.time()
        interactions = miner.generate_interaction_factors(factors, max_combinations=10)
        elapsed = time.time() - start_time
        
        assert isinstance(interactions, dict)
        assert elapsed < 3.0  # 应该在3秒内完成


class TestFactorCombinationIntegration:
    """测试因子组合集成功能"""
    
    def test_full_workflow(
        self, miner, sample_factors, sample_returns
    ):
        """测试完整工作流程"""
        # 1. 生成交互因子
        interactions = miner.generate_interaction_factors(
            sample_factors, max_combinations=3
        )
        assert isinstance(interactions, dict)
        
        # 2. 生成非线性组合
        nonlinear = miner.generate_nonlinear_combinations(
            sample_factors, max_combinations=2
        )
        assert isinstance(nonlinear, dict)
        
        # 3. 生成择时信号
        timing = miner.generate_timing_signals(sample_factors, sample_returns)
        assert isinstance(timing, dict)
        
        # 4. 分析协同效应
        synergy = miner.analyze_factor_synergy(sample_factors)
        assert isinstance(synergy, pd.Series)
    
    def test_combination_consistency(self, miner, sample_factors):
        """测试组合因子一致性"""
        # 计算两次应该得到相同结果
        factor1 = miner.calculate_combination_factor(
            'factor_interaction_term',
            {
                'momentum': sample_factors['momentum'],
                'volatility': sample_factors['volatility']
            },
            method='multiply'
        )
        
        factor2 = miner.calculate_combination_factor(
            'factor_interaction_term',
            {
                'momentum': sample_factors['momentum'],
                'volatility': sample_factors['volatility']
            },
            method='multiply'
        )
        
        pd.testing.assert_series_equal(factor1, factor2)
    
    def test_empty_existing_factors(self, miner, sample_data, sample_returns):
        """测试空的已有因子"""
        # 应该能处理空的已有因子字典
        @pytest.mark.asyncio
        async def run_test():
            factors = await miner.mine_factors(
                data=sample_data,
                returns=sample_returns,
                existing_factors={},
                generations=1
            )
            assert isinstance(factors, list)
        
        import asyncio
        asyncio.run(run_test())


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
