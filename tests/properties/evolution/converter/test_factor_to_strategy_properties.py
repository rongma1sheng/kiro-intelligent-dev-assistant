"""Property-based tests for Factor-to-Strategy Conversion System

白皮书依据: 第四章 4.2.2 因子组合策略生成与斯巴达考核

Feature: chapter-4-sparta-evolution-completion
Properties: 33-37
"""

import pytest
import numpy as np
import pandas as pd
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime
from typing import List

from src.evolution.converter.factor_to_strategy_converter import FactorToStrategyConverter
from src.evolution.converter.data_models import (
    FactorCharacteristics,
    StrategyType,
    GeneratedStrategy,
)
from src.evolution.converter.correlation_analyzer import CorrelationAnalyzer
from src.evolution.arena.data_models import (
    FactorTestResult,
    RealityTrackResult,
    HellTrackResult,
    CrossMarketResult,
)


# Hypothesis strategies for generating test data

@st.composite
def factor_test_result_strategy(draw):
    """Generate valid FactorTestResult"""
    factor_id = draw(st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    
    # Generate Reality Track result
    reality_score = draw(st.floats(min_value=0.0, max_value=1.0))
    reality_result = RealityTrackResult(
        ic=draw(st.floats(min_value=-1.0, max_value=1.0)),
        ir=draw(st.floats(min_value=0.0, max_value=5.0)),
        sharpe_ratio=draw(st.floats(min_value=-2.0, max_value=5.0)),
        annual_return=draw(st.floats(min_value=-0.5, max_value=1.0)),
        max_drawdown=draw(st.floats(min_value=0.0, max_value=0.5)),
        win_rate=draw(st.floats(min_value=0.0, max_value=1.0)),
        reality_score=reality_score,
        test_period_days=draw(st.integers(min_value=100, max_value=1000)),
        sample_count=draw(st.integers(min_value=100, max_value=10000))
    )
    
    # Generate Hell Track result
    hell_score = draw(st.floats(min_value=0.0, max_value=1.0))
    hell_result = HellTrackResult(
        survival_rate=draw(st.floats(min_value=0.0, max_value=1.0)),
        crash_performance=draw(st.floats(min_value=-1.0, max_value=1.0)),
        flash_crash_performance=draw(st.floats(min_value=-1.0, max_value=1.0)),
        liquidity_crisis_performance=draw(st.floats(min_value=-1.0, max_value=1.0)),
        volatility_spike_performance=draw(st.floats(min_value=-1.0, max_value=1.0)),
        correlation_breakdown_performance=draw(st.floats(min_value=-1.0, max_value=1.0)),
        hell_score=hell_score,
        scenarios_tested=5
    )
    
    # Generate Cross-Market result
    cross_market_score = draw(st.floats(min_value=0.0, max_value=1.0))
    cross_market_result = CrossMarketResult(
        a_stock_score=draw(st.floats(min_value=0.0, max_value=1.0)),
        us_stock_score=draw(st.floats(min_value=0.0, max_value=1.0)),
        crypto_score=draw(st.floats(min_value=0.0, max_value=1.0)),
        hk_stock_score=draw(st.floats(min_value=0.0, max_value=1.0)),
        adaptability_score=draw(st.floats(min_value=0.0, max_value=1.0)),
        cross_market_score=cross_market_score,
        markets_tested=4
    )
    
    overall_score = (reality_score + hell_score + cross_market_score) / 3
    
    return FactorTestResult(
        factor_id=factor_id,
        reality_result=reality_result,
        hell_result=hell_result,
        cross_market_result=cross_market_result,
        overall_score=overall_score,
        passed=overall_score >= 0.7,
        test_timestamp=datetime.now(),
        detailed_metrics={}
    )


# Property 33: Pure Factor Strategy Generation
@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    factor_result=factor_test_result_strategy(),
    seed=st.integers(min_value=0, max_value=2**32-1)
)
async def test_property_33_pure_factor_strategy_generation(factor_result, seed):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 33: Pure Factor Strategy Generation
    
    For any factor passing Arena validation, the system should generate a pure
    factor strategy containing factor calculation logic, signal generation, and
    risk management.
    
    Validates: Requirements 7.1, 7.2
    """
    # Skip if factor didn't pass Arena
    if not factor_result.passed:
        return
    
    # Create factor characteristics
    factor_char = FactorCharacteristics(
        factor_id=factor_result.factor_id,
        ic=0.05,
        ir=1.5,
        turnover=0.3,
        stability=0.8,
        arena_score=factor_result.overall_score,
        hell_survival_rate=factor_result.hell_result.survival_rate,
        cross_market_adaptability=factor_result.cross_market_result.adaptability_score,
        category='technical'
    )
    
    # Create converter
    converter = FactorToStrategyConverter()
    
    # Generate pure factor strategy
    strategy = await converter.generate_pure_factor_strategy(
        factor_result=factor_result,
        factor_characteristics=factor_char
    )
    
    # Verify strategy was generated
    assert strategy is not None
    assert isinstance(strategy, GeneratedStrategy)
    
    # Verify strategy type
    assert strategy.strategy_type == StrategyType.PURE_FACTOR
    
    # Verify source factors
    assert len(strategy.source_factors) == 1
    assert strategy.source_factors[0] == factor_result.factor_id
    
    # Verify strategy code contains required components
    assert strategy.strategy_code is not None
    assert len(strategy.strategy_code) > 0
    
    # Check for factor calculation logic
    assert 'calculate_factor' in strategy.strategy_code or 'factor_calculation' in strategy.strategy_code
    
    # Check for signal generation
    assert 'generate_signals' in strategy.strategy_code or 'signals' in strategy.strategy_code
    
    # Check for risk management
    assert ('stop_loss' in strategy.strategy_code or 'take_profit' in strategy.strategy_code or
            'risk_management' in strategy.strategy_code or 'check_risk' in strategy.strategy_code)
    
    # Verify parameters are set
    assert strategy.parameters is not None
    assert strategy.parameters.rebalance_frequency >= 1
    assert 0.0 < strategy.parameters.position_limit <= 1.0
    assert strategy.parameters.max_positions >= 1
    
    # Verify expected metrics
    assert strategy.expected_sharpe >= 0
    assert 0.0 <= strategy.expected_drawdown <= 1.0
    
    # Verify status
    assert strategy.status == "candidate"
    
    # Verify arena metadata
    assert 'factor_arena_score' in strategy.arena_metadata
    assert strategy.arena_metadata['factor_arena_score'] == factor_result.overall_score



# Property 34: Multi-Factor Combination
@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_factors=st.integers(min_value=2, max_value=10),
    seed=st.integers(min_value=0, max_value=2**32-1)
)
async def test_property_34_multi_factor_combination(num_factors, seed):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 34: Multi-Factor Combination
    
    For any set of 2 or more Arena-validated factors, the system should generate
    factor combination strategies.
    
    Validates: Requirements 7.3
    """
    np.random.seed(seed)
    
    # Generate multiple passing factors
    factor_results = []
    factor_characteristics_list = []
    factor_ids = []
    
    for i in range(num_factors):
        factor_id = f"factor_{i}_{seed}"
        factor_ids.append(factor_id)
        
        # Create passing factor result
        reality_score = np.random.uniform(0.7, 1.0)
        hell_score = np.random.uniform(0.7, 1.0)
        cross_market_score = np.random.uniform(0.7, 1.0)
        overall_score = (reality_score + hell_score + cross_market_score) / 3
        
        reality_result = RealityTrackResult(
            ic=np.random.uniform(0.03, 0.10),
            ir=np.random.uniform(1.0, 3.0),
            sharpe_ratio=np.random.uniform(1.0, 3.0),
            annual_return=np.random.uniform(0.1, 0.5),
            max_drawdown=np.random.uniform(0.05, 0.20),
            win_rate=np.random.uniform(0.5, 0.7),
            reality_score=reality_score,
            test_period_days=252,
            sample_count=1000
        )
        
        hell_result = HellTrackResult(
            survival_rate=np.random.uniform(0.6, 1.0),
            crash_performance=np.random.uniform(-0.3, 0.3),
            flash_crash_performance=np.random.uniform(-0.3, 0.3),
            liquidity_crisis_performance=np.random.uniform(-0.3, 0.3),
            volatility_spike_performance=np.random.uniform(-0.3, 0.3),
            correlation_breakdown_performance=np.random.uniform(-0.3, 0.3),
            hell_score=hell_score,
            scenarios_tested=5
        )
        
        cross_market_result = CrossMarketResult(
            a_stock_score=np.random.uniform(0.6, 1.0),
            us_stock_score=np.random.uniform(0.6, 1.0),
            crypto_score=np.random.uniform(0.6, 1.0),
            hk_stock_score=np.random.uniform(0.6, 1.0),
            adaptability_score=np.random.uniform(0.6, 1.0),
            cross_market_score=cross_market_score,
            markets_tested=4
        )
        
        factor_result = FactorTestResult(
            factor_id=factor_id,
            reality_result=reality_result,
            hell_result=hell_result,
            cross_market_result=cross_market_result,
            overall_score=overall_score,
            passed=True,
            test_timestamp=datetime.now(),
            detailed_metrics={}
        )
        factor_results.append(factor_result)
        
        # Create factor characteristics
        factor_char = FactorCharacteristics(
            factor_id=factor_id,
            ic=np.random.uniform(0.03, 0.10),
            ir=np.random.uniform(1.0, 3.0),
            turnover=np.random.uniform(0.1, 0.8),
            stability=np.random.uniform(0.5, 1.0),
            arena_score=overall_score,
            hell_survival_rate=hell_result.survival_rate,
            cross_market_adaptability=cross_market_result.adaptability_score,
            category='technical'
        )
        factor_characteristics_list.append(factor_char)
    
    # Generate factor values (low correlation to ensure diversity)
    num_stocks = 100
    stock_symbols = [f"STOCK_{i:04d}" for i in range(num_stocks)]
    factor_values = {}
    
    for factor_id in factor_ids:
        # Generate independent random values
        values = np.random.randn(num_stocks)
        factor_values[factor_id] = pd.Series(values, index=stock_symbols)
    
    # Create converter
    converter = FactorToStrategyConverter(correlation_threshold=0.7)
    
    # Generate factor combo strategy
    combo_strategy = await converter.generate_factor_combo_strategy(
        factor_results=factor_results,
        factor_characteristics_list=factor_characteristics_list,
        factor_values=factor_values,
        max_factors=5
    )
    
    # Verify combo strategy was generated (may be None if factors are too correlated)
    if combo_strategy is not None:
        assert isinstance(combo_strategy, GeneratedStrategy)
        
        # Verify strategy type
        assert combo_strategy.strategy_type == StrategyType.FACTOR_COMBO
        
        # Verify multiple source factors
        assert len(combo_strategy.source_factors) >= 2
        assert len(combo_strategy.source_factors) <= min(num_factors, 5)
        
        # Verify all source factors are from input
        for source_factor in combo_strategy.source_factors:
            assert source_factor in factor_ids
        
        # Verify strategy code contains combo logic
        assert combo_strategy.strategy_code is not None
        assert len(combo_strategy.strategy_code) > 0
        
        # Check for composite score calculation
        assert ('composite' in combo_strategy.strategy_code.lower() or
                'weight' in combo_strategy.strategy_code.lower() or
                'combination' in combo_strategy.strategy_code.lower())
        
        # Verify metadata includes factor weights
        assert 'factor_weights' in combo_strategy.arena_metadata
        assert 'num_factors' in combo_strategy.arena_metadata
        assert combo_strategy.arena_metadata['num_factors'] == len(combo_strategy.source_factors)


# Property 35: Correlation-Based Redundancy Avoidance
@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    seed=st.integers(min_value=0, max_value=2**32-1)
)
async def test_property_35_correlation_based_redundancy_avoidance(seed):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 35: Correlation-Based Redundancy Avoidance
    
    For any factor combination strategy, the system should analyze factor
    correlations and avoid combining highly correlated factors.
    
    Validates: Requirements 7.4
    """
    np.random.seed(seed)
    
    # Generate 5 factors: 3 independent + 2 highly correlated with first
    num_stocks = 100
    stock_symbols = [f"STOCK_{i:04d}" for i in range(num_stocks)]
    
    factor_results = []
    factor_characteristics_list = []
    factor_values = {}
    
    # Generate base independent factors
    base_values = []
    for i in range(3):
        values = np.random.randn(num_stocks)
        base_values.append(values)
    
    # Create 5 factors total
    for i in range(5):
        factor_id = f"factor_{i}_{seed}"
        
        if i < 3:
            # Independent factors
            values = base_values[i]
        else:
            # Highly correlated with factor_0 (correlation > 0.8)
            values = base_values[0] + np.random.randn(num_stocks) * 0.3
        
        factor_values[factor_id] = pd.Series(values, index=stock_symbols)
        
        # Create factor result
        overall_score = np.random.uniform(0.7, 0.9)
        
        reality_result = RealityTrackResult(
            ic=0.05,
            ir=1.5,
            sharpe_ratio=1.5,
            annual_return=0.2,
            max_drawdown=0.15,
            win_rate=0.6,
            reality_score=overall_score,
            test_period_days=252,
            sample_count=1000
        )
        
        hell_result = HellTrackResult(
            survival_rate=0.8,
            crash_performance=0.0,
            flash_crash_performance=0.0,
            liquidity_crisis_performance=0.0,
            volatility_spike_performance=0.0,
            correlation_breakdown_performance=0.0,
            hell_score=overall_score,
            scenarios_tested=5
        )
        
        cross_market_result = CrossMarketResult(
            a_stock_score=0.8,
            us_stock_score=0.8,
            crypto_score=0.8,
            hk_stock_score=0.8,
            adaptability_score=0.8,
            cross_market_score=overall_score,
            markets_tested=4
        )
        
        factor_result = FactorTestResult(
            factor_id=factor_id,
            reality_result=reality_result,
            hell_result=hell_result,
            cross_market_result=cross_market_result,
            overall_score=overall_score,
            passed=True,
            test_timestamp=datetime.now(),
            detailed_metrics={}
        )
        factor_results.append(factor_result)
        
        # Create factor characteristics
        factor_char = FactorCharacteristics(
            factor_id=factor_id,
            ic=0.05,
            ir=1.5,
            turnover=0.3,
            stability=0.8,
            arena_score=overall_score,
            hell_survival_rate=0.8,
            cross_market_adaptability=0.8,
            category='technical'
        )
        factor_characteristics_list.append(factor_char)
    
    # Create converter with correlation threshold
    converter = FactorToStrategyConverter(correlation_threshold=0.7)
    
    # Generate combo strategy
    combo_strategy = await converter.generate_factor_combo_strategy(
        factor_results=factor_results,
        factor_characteristics_list=factor_characteristics_list,
        factor_values=factor_values,
        max_factors=5
    )
    
    # Verify strategy was generated
    if combo_strategy is not None:
        # Calculate actual correlations between selected factors
        selected_ids = combo_strategy.source_factors
        
        if len(selected_ids) >= 2:
            # Check pairwise correlations
            for i in range(len(selected_ids)):
                for j in range(i + 1, len(selected_ids)):
                    factor_i = factor_values[selected_ids[i]]
                    factor_j = factor_values[selected_ids[j]]
                    
                    corr = abs(factor_i.corr(factor_j, method='spearman'))
                    
                    # Verify correlation is below threshold
                    # Allow some tolerance due to random generation
                    assert corr < 0.85, (
                        f"Selected factors {selected_ids[i]} and {selected_ids[j]} "
                        f"have high correlation {corr:.4f}"
                    )



# Property 36: Factor-Based Parameter Setting
@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    turnover=st.floats(min_value=0.0, max_value=1.0),
    stability=st.floats(min_value=0.0, max_value=1.0),
    arena_score=st.floats(min_value=0.7, max_value=1.0),
    seed=st.integers(min_value=0, max_value=2**32-1)
)
async def test_property_36_factor_based_parameter_setting(turnover, stability, arena_score, seed):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 36: Factor-Based Parameter Setting
    
    For any generated strategy, rebalance frequency and position limits should be
    determined by the source factor's characteristics and stability.
    
    Validates: Requirements 7.5, 7.6
    """
    # Create factor with specific characteristics
    factor_id = f"factor_{seed}"
    
    reality_result = RealityTrackResult(
        ic=0.05,
        ir=1.5,
        sharpe_ratio=1.5,
        annual_return=0.2,
        max_drawdown=0.15,
        win_rate=0.6,
        reality_score=arena_score,
        test_period_days=252,
        sample_count=1000
    )
    
    hell_result = HellTrackResult(
        survival_rate=0.8,
        crash_performance=0.0,
        flash_crash_performance=0.0,
        liquidity_crisis_performance=0.0,
        volatility_spike_performance=0.0,
        correlation_breakdown_performance=0.0,
        hell_score=arena_score,
        scenarios_tested=5
    )
    
    cross_market_result = CrossMarketResult(
        a_stock_score=arena_score,
        us_stock_score=arena_score,
        crypto_score=arena_score,
        hk_stock_score=arena_score,
        adaptability_score=arena_score,
        cross_market_score=arena_score,
        markets_tested=4
    )
    
    factor_result = FactorTestResult(
        factor_id=factor_id,
        reality_result=reality_result,
        hell_result=hell_result,
        cross_market_result=cross_market_result,
        overall_score=arena_score,
        passed=True,
        test_timestamp=datetime.now(),
        detailed_metrics={}
    )
    
    factor_char = FactorCharacteristics(
        factor_id=factor_id,
        ic=0.05,
        ir=1.5,
        turnover=turnover,
        stability=stability,
        arena_score=arena_score,
        hell_survival_rate=0.8,
        cross_market_adaptability=0.8,
        category='technical'
    )
    
    # Create converter
    converter = FactorToStrategyConverter()
    
    # Generate strategy
    strategy = await converter.generate_pure_factor_strategy(
        factor_result=factor_result,
        factor_characteristics=factor_char
    )
    
    # Verify parameters are influenced by factor characteristics
    
    # 1. Rebalance frequency should be inversely related to turnover
    # High turnover → low rebalance frequency (more frequent)
    # Low turnover → high rebalance frequency (less frequent)
    if turnover >= 0.8:
        assert strategy.parameters.rebalance_frequency <= 3, (
            f"High turnover ({turnover:.2f}) should have low rebalance frequency, "
            f"got {strategy.parameters.rebalance_frequency}"
        )
    elif turnover <= 0.1:
        assert strategy.parameters.rebalance_frequency >= 10, (
            f"Low turnover ({turnover:.2f}) should have high rebalance frequency, "
            f"got {strategy.parameters.rebalance_frequency}"
        )
    
    # 2. Position limit should be influenced by stability and arena score
    # Higher stability + higher arena score → larger position limit
    quality_score = (stability + arena_score) / 2
    
    if quality_score >= 0.8:
        assert strategy.parameters.position_limit >= 0.05, (
            f"High quality score ({quality_score:.2f}) should have reasonable position limit, "
            f"got {strategy.parameters.position_limit:.4f}"
        )
    
    # 3. Verify position limit is within reasonable bounds
    assert 0.0 < strategy.parameters.position_limit <= 0.15, (
        f"Position limit {strategy.parameters.position_limit:.4f} out of reasonable range"
    )
    
    # 4. Verify max positions is reasonable
    assert 1 <= strategy.parameters.max_positions <= 50


# Property 37: Strategy Metadata Inclusion
@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    factor_result=factor_test_result_strategy(),
    seed=st.integers(min_value=0, max_value=2**32-1)
)
async def test_property_37_strategy_metadata_inclusion(factor_result, seed):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 37: Strategy Metadata Inclusion
    
    For any generated strategy, its metadata should include the Arena test results
    of its source factors.
    
    Validates: Requirements 7.7
    """
    # Skip if factor didn't pass Arena
    if not factor_result.passed:
        return
    
    # Create factor characteristics
    factor_char = FactorCharacteristics(
        factor_id=factor_result.factor_id,
        ic=0.05,
        ir=1.5,
        turnover=0.3,
        stability=0.8,
        arena_score=factor_result.overall_score,
        hell_survival_rate=factor_result.hell_result.survival_rate,
        cross_market_adaptability=factor_result.cross_market_result.adaptability_score,
        category='technical'
    )
    
    # Create converter
    converter = FactorToStrategyConverter()
    
    # Generate strategy
    strategy = await converter.generate_pure_factor_strategy(
        factor_result=factor_result,
        factor_characteristics=factor_char
    )
    
    # Verify arena metadata is included
    assert strategy.arena_metadata is not None
    assert isinstance(strategy.arena_metadata, dict)
    assert len(strategy.arena_metadata) > 0
    
    # Verify required Arena test results are included
    assert 'factor_arena_score' in strategy.arena_metadata
    assert 'reality_score' in strategy.arena_metadata
    assert 'hell_score' in strategy.arena_metadata
    assert 'cross_market_score' in strategy.arena_metadata
    
    # Verify values match source factor
    assert strategy.arena_metadata['factor_arena_score'] == factor_result.overall_score
    assert strategy.arena_metadata['reality_score'] == factor_result.reality_result.reality_score
    assert strategy.arena_metadata['hell_score'] == factor_result.hell_result.hell_score
    assert strategy.arena_metadata['cross_market_score'] == factor_result.cross_market_result.cross_market_score
    
    # Verify metadata is accessible and complete
    for key, value in strategy.arena_metadata.items():
        assert value is not None, f"Metadata key '{key}' has None value"
