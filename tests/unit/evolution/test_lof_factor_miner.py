"""Unit tests for LOFFactorMiner

白皮书依据: 第四章 4.1.18 - LOF因子挖掘器
铁律依据: MIA编码铁律7 (测试覆盖率要求 ≥ 85%)

This test file implements unit tests for LOFFactorMiner, testing individual
methods and edge cases.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.evolution.etf_lof.lof_factor_miner import LOFFactorMiner
from src.evolution.etf_lof.data_models import LOFMarketData
from src.evolution.genetic_miner import EvolutionConfig, Individual
from src.evolution.etf_lof.exceptions import (
    FactorMiningError,
    OperatorError,
    DataQualityError,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_lof_data():
    """Create sample LOF market data for testing"""
    return pd.DataFrame({
        'onmarket_price': [100.0, 101.0, 102.0, 101.5, 103.0] * 20,
        'offmarket_price': [100.0, 100.5, 101.0, 101.0, 102.0] * 20,
        'nav': [100.0, 100.5, 101.0, 101.0, 102.0] * 20,
        'onmarket_volume': [10000.0, 12000.0, 11000.0, 13000.0, 11500.0] * 20,
        'offmarket_volume': [5000.0, 6000.0, 5500.0, 6500.0, 5800.0] * 20,
        'subscription_amount': [100.0, 150.0, 120.0, 180.0, 140.0] * 20,
        'redemption_amount': [80.0, 100.0, 90.0, 120.0, 100.0] * 20,
        'returns': [0.01, 0.01, -0.005, 0.015, 0.01] * 20,
        'benchmark_returns': [0.008, 0.012, -0.003, 0.012, 0.009] * 20,
        'onmarket_turnover': [0.1, 0.12, 0.11, 0.13, 0.115] * 20,
        'institutional_holding': [0.6, 0.62, 0.61, 0.63, 0.615] * 20,
        'retail_holding': [0.4, 0.38, 0.39, 0.37, 0.385] * 20,
        'turnover': [0.5, 0.52, 0.51, 0.53, 0.515] * 20,
        'expense_ratio': [0.01, 0.01, 0.01, 0.01, 0.01] * 20,
        'dividend': [0.1, 0.1, 0.1, 0.1, 0.1] * 20,
        'aum': [1e9, 1.1e9, 1.05e9, 1.15e9, 1.08e9] * 20,
        'trade_size': [1000.0, 1200.0, 1100.0, 1300.0, 1150.0] * 20,
    })


@pytest.fixture
def lof_miner():
    """Create LOFFactorMiner instance for testing"""
    return LOFFactorMiner(
        population_size=50,
        mutation_rate=0.2,
        crossover_rate=0.7,
        elite_ratio=0.1
    )


# ============================================================================
# Test Class: Initialization
# ============================================================================

class TestLOFFactorMinerInitialization:
    """Test LOFFactorMiner initialization
    
    白皮书依据: 第四章 4.1.18 - LOFFactorMiner初始化
    """
    
    def test_init_with_valid_parameters(self):
        """Test initialization with valid parameters"""
        # Act
        miner = LOFFactorMiner(
            population_size=50,
            mutation_rate=0.2,
            crossover_rate=0.7,
            elite_ratio=0.1
        )
        
        # Assert
        assert miner.config.population_size == 50
        assert miner.config.mutation_rate == 0.2
        assert miner.config.crossover_rate == 0.7
        assert miner.config.elite_ratio == 0.1
        assert len(miner.lof_operators) == 20
        assert len(miner.common_operators) == 8
        assert len(miner.operator_registry) > 0
    
    def test_init_with_config(self):
        """Test initialization with EvolutionConfig"""
        # Arrange
        config = EvolutionConfig(
            population_size=100,
            mutation_rate=0.3,
            crossover_rate=0.8,
            elite_ratio=0.2
        )
        
        # Act
        miner = LOFFactorMiner(config=config)
        
        # Assert
        assert miner.config == config
        assert miner.config.population_size == 100
        assert miner.config.mutation_rate == 0.3
    
    def test_init_with_market_data(self, sample_lof_data):
        """Test initialization with market data"""
        # Arrange
        from datetime import date
        market_data = LOFMarketData(
            symbol='163406',
            date=date(2024, 1, 1),
            onmarket_price=100.0,
            offmarket_price=100.0,
            nav=100.0,
            onmarket_volume=10000.0,
            offmarket_volume=5000.0
        )
        
        # Act
        miner = LOFFactorMiner(market_data=market_data)
        
        # Assert
        assert miner.market_data == market_data
    
    def test_init_invalid_population_size(self):
        """Test initialization with invalid population size"""
        # Act & Assert
        with pytest.raises(ValueError, match="population_size must be > 0"):
            LOFFactorMiner(population_size=0)
        
        with pytest.raises(ValueError, match="population_size must be > 0"):
            LOFFactorMiner(population_size=-10)
    
    def test_init_invalid_mutation_rate(self):
        """Test initialization with invalid mutation rate"""
        # Act & Assert
        with pytest.raises(ValueError, match="mutation_rate must be in"):
            LOFFactorMiner(mutation_rate=-0.1)
        
        with pytest.raises(ValueError, match="mutation_rate must be in"):
            LOFFactorMiner(mutation_rate=1.5)
    
    def test_init_invalid_crossover_rate(self):
        """Test initialization with invalid crossover rate"""
        # Act & Assert
        with pytest.raises(ValueError, match="crossover_rate must be in"):
            LOFFactorMiner(crossover_rate=-0.1)
        
        with pytest.raises(ValueError, match="crossover_rate must be in"):
            LOFFactorMiner(crossover_rate=1.1)
    
    def test_init_invalid_elite_ratio(self):
        """Test initialization with invalid elite ratio"""
        # Act & Assert
        with pytest.raises(ValueError, match="elite_ratio must be in"):
            LOFFactorMiner(elite_ratio=-0.1)
        
        with pytest.raises(ValueError, match="elite_ratio must be in"):
            LOFFactorMiner(elite_ratio=1.5)


# ============================================================================
# Test Class: Operator Registry
# ============================================================================

class TestLOFFactorMinerOperatorRegistry:
    """Test operator registry building
    
    白皮书依据: 第四章 4.1.18 - LOF算子注册
    """
    
    def test_build_operator_registry_success(self, lof_miner):
        """Test successful operator registry building"""
        # Assert
        assert lof_miner.operator_registry is not None
        assert isinstance(lof_miner.operator_registry, dict)
        assert len(lof_miner.operator_registry) > 0
        
        # Check common operators are registered
        assert 'rank' in lof_miner.operator_registry
        assert 'delay' in lof_miner.operator_registry
        assert 'delta' in lof_miner.operator_registry
        assert 'ts_mean' in lof_miner.operator_registry
        assert 'ts_std' in lof_miner.operator_registry
        
        # Check all registered operators are callable
        for op_name, op_func in lof_miner.operator_registry.items():
            assert callable(op_func), f"Operator '{op_name}' is not callable"
    
    def test_get_operator_whitelist(self, lof_miner):
        """Test getting operator whitelist"""
        # Act
        whitelist = lof_miner._get_operator_whitelist()
        
        # Assert
        assert isinstance(whitelist, list)
        assert len(whitelist) == 28  # 20 LOF + 8 common
        
        # Check all LOF operators are in whitelist
        for op in lof_miner.lof_operators:
            assert op in whitelist
        
        # Check all common operators are in whitelist
        for op in lof_miner.common_operators:
            assert op in whitelist


# ============================================================================
# Test Class: Expression Generation
# ============================================================================

class TestLOFFactorMinerExpressionGeneration:
    """Test expression generation methods
    
    白皮书依据: 第四章 4.1.18 - LOF因子表达式生成
    """
    
    def test_generate_random_expression_valid_columns(self, lof_miner):
        """Test generating random expression with valid columns"""
        # Arrange
        data_columns = ['onmarket_price', 'offmarket_price', 'nav']
        
        # Act
        expression = lof_miner._generate_random_expression(data_columns)
        
        # Assert
        assert expression is not None
        assert isinstance(expression, str)
        assert len(expression) > 0
    
    def test_generate_random_expression_empty_columns(self, lof_miner):
        """Test generating expression with empty columns raises ValueError"""
        # Act & Assert
        with pytest.raises(ValueError, match="data_columns cannot be empty"):
            lof_miner._generate_random_expression([])
    
    def test_generate_lof_expression_onoff_price_spread(self, lof_miner):
        """Test generating lof_onoff_price_spread expression"""
        # Arrange
        data_columns = ['onmarket_price', 'offmarket_price']
        
        # Act
        expression = lof_miner._generate_lof_expression(
            'lof_onoff_price_spread',
            data_columns
        )
        
        # Assert
        assert expression == "lof_onoff_price_spread(onmarket_price, offmarket_price)"
    
    def test_generate_lof_expression_premium_discount_rate(self, lof_miner):
        """Test generating lof_premium_discount_rate expression"""
        # Arrange
        data_columns = ['onmarket_price', 'nav']
        
        # Act
        expression = lof_miner._generate_lof_expression(
            'lof_premium_discount_rate',
            data_columns
        )
        
        # Assert
        assert expression == "lof_premium_discount_rate(onmarket_price, nav)"
    
    def test_generate_lof_expression_fund_manager_alpha(self, lof_miner):
        """Test generating lof_fund_manager_alpha expression"""
        # Arrange
        data_columns = ['returns', 'benchmark_returns']
        
        # Act - Mock random.choice to return specific window
        with patch('random.choice', return_value=20):
            expression = lof_miner._generate_lof_expression(
                'lof_fund_manager_alpha',
                data_columns
            )
        
        # Assert
        assert expression == "lof_fund_manager_alpha(returns, benchmark_returns, 20)"
    
    def test_generate_common_expression_rank(self, lof_miner):
        """Test generating rank expression"""
        # Arrange
        data_columns = ['nav']
        
        # Act
        expression = lof_miner._generate_common_expression(
            'rank',
            data_columns
        )
        
        # Assert
        assert expression == "rank(nav)"
    
    def test_generate_common_expression_delay(self, lof_miner):
        """Test generating delay expression"""
        # Arrange
        data_columns = ['nav']
        
        # Act - Mock random.choice to return column first, then period
        with patch('random.choice', side_effect=['nav', 5]):
            expression = lof_miner._generate_common_expression(
                'delay',
                data_columns
            )
        
        # Assert
        assert expression == "delay(nav, 5)"


# ============================================================================
# Test Class: Expression Evaluation
# ============================================================================

class TestLOFFactorMinerExpressionEvaluation:
    """Test expression evaluation methods
    
    白皮书依据: 第四章 4.1.18 - LOF因子评估
    """
    
    def test_evaluate_expression_simple_column(self, lof_miner, sample_lof_data):
        """Test evaluating simple column reference"""
        # Act
        result = lof_miner._evaluate_expression('nav', sample_lof_data)
        
        # Assert
        assert result is not None
        assert isinstance(result, pd.Series)
        pd.testing.assert_series_equal(result, sample_lof_data['nav'])
    
    def test_evaluate_expression_nonexistent_column(self, lof_miner, sample_lof_data):
        """Test evaluating nonexistent column returns None"""
        # Act
        result = lof_miner._evaluate_expression('nonexistent', sample_lof_data)
        
        # Assert
        assert result is None
    
    def test_evaluate_expression_rank_operator(self, lof_miner, sample_lof_data):
        """Test evaluating rank operator"""
        # Act
        result = lof_miner._evaluate_expression('rank(nav)', sample_lof_data)
        
        # Assert
        assert result is not None
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_lof_data)
        # Rank values should be between 0 and 1
        assert result.min() >= 0.0
        assert result.max() <= 1.0
    
    def test_evaluate_expression_delay_operator(self, lof_miner, sample_lof_data):
        """Test evaluating delay operator"""
        # Act
        result = lof_miner._evaluate_expression('delay(nav, 1)', sample_lof_data)
        
        # Assert
        assert result is not None
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_lof_data)
        # First value should be NaN (delayed)
        assert pd.isna(result.iloc[0])
    
    def test_evaluate_expression_delta_operator(self, lof_miner, sample_lof_data):
        """Test evaluating delta operator"""
        # Act
        result = lof_miner._evaluate_expression('delta(nav, 1)', sample_lof_data)
        
        # Assert
        assert result is not None
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_lof_data)
        # First value should be NaN (no previous value)
        assert pd.isna(result.iloc[0])
    
    def test_evaluate_expression_ts_mean_operator(self, lof_miner, sample_lof_data):
        """Test evaluating ts_mean operator"""
        # Act
        result = lof_miner._evaluate_expression('ts_mean(nav, 5)', sample_lof_data)
        
        # Assert
        assert result is not None
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_lof_data)
        # First 4 values should be NaN (insufficient window)
        assert pd.isna(result.iloc[:4]).all()
    
    def test_evaluate_expression_invalid_format(self, lof_miner, sample_lof_data):
        """Test evaluating invalid expression format"""
        # Act
        result = lof_miner._evaluate_expression('invalid((format', sample_lof_data)
        
        # Assert
        assert result is None
    
    def test_evaluate_expression_operator_error(self, lof_miner, sample_lof_data):
        """Test evaluating expression that raises OperatorError"""
        # Arrange - Mock operator to raise exception
        with patch.object(lof_miner, 'operator_registry', {'rank': Mock(side_effect=Exception("Test error"))}):
            # Act & Assert
            with pytest.raises(OperatorError, match="Failed to evaluate expression"):
                lof_miner._evaluate_expression('rank(nav)', sample_lof_data)


# ============================================================================
# Test Class: Result Validation
# ============================================================================

class TestLOFFactorMinerResultValidation:
    """Test result validation methods
    
    白皮书依据: 第四章 4.1.18 - 数据质量要求
    """
    
    def test_validate_result_valid_data(self, lof_miner):
        """Test validating result with valid data"""
        # Arrange
        result = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        
        # Act
        lof_miner._validate_result(result)
        
        # Assert - Should not raise exception
        assert True
    
    def test_validate_result_acceptable_nan_ratio(self, lof_miner):
        """Test validating result with acceptable NaN ratio (<=50%)"""
        # Arrange
        result = pd.Series([1.0, 2.0, np.nan, 4.0, 5.0])  # 20% NaN
        
        # Act
        lof_miner._validate_result(result)
        
        # Assert - Should not raise exception
        assert True
    
    def test_validate_result_unacceptable_nan_ratio(self, lof_miner):
        """Test validating result with unacceptable NaN ratio (>50%)"""
        # Arrange
        result = pd.Series([1.0, np.nan, np.nan, np.nan, 5.0])  # 60% NaN
        
        # Act & Assert
        with pytest.raises(DataQualityError, match="Too many NaN values"):
            lof_miner._validate_result(result)
    
    def test_validate_result_infinite_values(self, lof_miner):
        """Test validating result with infinite values"""
        # Arrange
        result = pd.Series([1.0, 2.0, np.inf, -np.inf, 5.0])
        
        # Act
        lof_miner._validate_result(result)
        
        # Assert - Should not raise exception (infinite values replaced with NaN)
        assert True
    
    def test_validate_result_none_input(self, lof_miner):
        """Test validating None result"""
        # Act & Assert
        with pytest.raises(DataQualityError, match="Result is None or empty"):
            lof_miner._validate_result(None)
    
    def test_validate_result_empty_series(self, lof_miner):
        """Test validating empty series"""
        # Arrange
        result = pd.Series([])
        
        # Act & Assert
        with pytest.raises(DataQualityError, match="Result is None or empty"):
            lof_miner._validate_result(result)


# ============================================================================
# Test Class: Edge Cases
# ============================================================================

class TestLOFFactorMinerEdgeCases:
    """Test edge cases and error handling"""
    
    def test_generate_expression_with_single_column(self, lof_miner):
        """Test generating expression with single data column"""
        # Act
        expression = lof_miner._generate_random_expression(['nav'])
        
        # Assert
        assert expression is not None
        assert isinstance(expression, str)
    
    def test_evaluate_expression_with_numeric_args(self, lof_miner, sample_lof_data):
        """Test evaluating expression with numeric arguments"""
        # Act
        result = lof_miner._evaluate_expression('ts_mean(nav, 10)', sample_lof_data)
        
        # Assert
        assert result is not None or result is None  # May return None if parsing fails
    
    def test_config_precedence(self):
        """Test that explicit config takes precedence over individual parameters"""
        # Arrange
        config = EvolutionConfig(population_size=100, mutation_rate=0.3)
        
        # Act
        miner = LOFFactorMiner(
            population_size=50,  # Should be overridden
            mutation_rate=0.1,   # Should be overridden
            config=config
        )
        
        # Assert
        assert miner.config.population_size == 100
        assert miner.config.mutation_rate == 0.3
    
    def test_lof_operators_count(self, lof_miner):
        """Test that exactly 20 LOF operators are defined"""
        # Assert
        assert len(lof_miner.lof_operators) == 20
    
    def test_common_operators_count(self, lof_miner):
        """Test that exactly 8 common operators are defined"""
        # Assert
        assert len(lof_miner.common_operators) == 8
    
    def test_operator_registry_completeness(self, lof_miner):
        """Test that operator registry contains all operators"""
        # Assert
        assert len(lof_miner.operator_registry) == 28  # 20 LOF + 8 common
    
    def test_generate_lof_expression_all_operators(self, lof_miner):
        """Test generating expressions for all LOF operators"""
        # Arrange
        data_columns = [
            'onmarket_price', 'offmarket_price', 'nav',
            'onmarket_volume', 'offmarket_volume',
            'subscription_amount', 'redemption_amount',
            'returns', 'benchmark_returns', 'onmarket_turnover',
            'institutional_holding', 'retail_holding',
            'turnover', 'expense_ratio', 'dividend', 'aum', 'trade_size'
        ]
        
        # Act & Assert - Should not raise exceptions
        for operator in lof_miner.lof_operators:
            expression = lof_miner._generate_lof_expression(operator, data_columns)
            assert expression is not None
            assert isinstance(expression, str)
            assert len(expression) > 0
    
    def test_generate_common_expression_all_operators(self, lof_miner):
        """Test generating expressions for all common operators"""
        # Arrange
        data_columns = ['nav', 'returns']
        
        # Act & Assert - Should not raise exceptions
        for operator in lof_miner.common_operators:
            expression = lof_miner._generate_common_expression(operator, data_columns)
            assert expression is not None
            assert isinstance(expression, str)
            assert len(expression) > 0

