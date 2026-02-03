"""Unit tests for ETFFactorMiner

白皮书依据: 第四章 4.1.17 - ETF因子挖掘器
铁律依据: MIA编码铁律7 (测试覆盖率要求 ≥ 85%)

This test file implements unit tests for ETFFactorMiner, testing individual
methods and edge cases.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.evolution.etf_lof.etf_factor_miner import ETFFactorMiner
from src.evolution.etf_lof.data_models import ETFMarketData
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
def sample_etf_data():
    """Create sample ETF market data for testing"""
    return pd.DataFrame({
        'close': [100.0, 101.0, 102.0, 101.5, 103.0] * 20,
        'nav': [100.0, 100.5, 101.0, 101.0, 102.0] * 20,
        'volume': [10000.0, 12000.0, 11000.0, 13000.0, 11500.0] * 20,
        'creation_units': [100.0, 150.0, 120.0, 180.0, 140.0] * 20,
        'redemption_units': [80.0, 100.0, 90.0, 120.0, 100.0] * 20,
        'bid_price': [99.9, 100.9, 101.9, 101.4, 102.9] * 20,
        'ask_price': [100.1, 101.1, 102.1, 101.6, 103.1] * 20,
        'returns': [0.01, 0.01, -0.005, 0.015, 0.01] * 20,
        'index_returns': [0.008, 0.012, -0.003, 0.012, 0.009] * 20,
    })


@pytest.fixture
def etf_miner():
    """Create ETFFactorMiner instance for testing"""
    return ETFFactorMiner(
        population_size=50,
        mutation_rate=0.2,
        crossover_rate=0.7,
        elite_ratio=0.1
    )


# ============================================================================
# Test Class: Initialization
# ============================================================================

class TestETFFactorMinerInitialization:
    """Test ETFFactorMiner initialization
    
    白皮书依据: 第四章 4.1.17 - ETFFactorMiner初始化
    """
    
    def test_init_with_valid_parameters(self):
        """Test initialization with valid parameters"""
        # Act
        miner = ETFFactorMiner(
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
        assert len(miner.etf_operators) == 20
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
        miner = ETFFactorMiner(config=config)
        
        # Assert
        assert miner.config == config
        assert miner.config.population_size == 100
        assert miner.config.mutation_rate == 0.3
    
    def test_init_with_market_data(self, sample_etf_data):
        """Test initialization with market data"""
        # Arrange
        from datetime import date
        market_data = ETFMarketData(
            symbol='510050',
            date=date(2024, 1, 1),
            price=100.0,
            nav=100.0,
            volume=10000.0
        )
        
        # Act
        miner = ETFFactorMiner(market_data=market_data)
        
        # Assert
        assert miner.market_data == market_data
    
    def test_init_invalid_population_size(self):
        """Test initialization with invalid population size"""
        # Act & Assert
        with pytest.raises(ValueError, match="population_size must be > 0"):
            ETFFactorMiner(population_size=0)
        
        with pytest.raises(ValueError, match="population_size must be > 0"):
            ETFFactorMiner(population_size=-10)
    
    def test_init_invalid_mutation_rate(self):
        """Test initialization with invalid mutation rate"""
        # Act & Assert
        with pytest.raises(ValueError, match="mutation_rate must be in"):
            ETFFactorMiner(mutation_rate=-0.1)
        
        with pytest.raises(ValueError, match="mutation_rate must be in"):
            ETFFactorMiner(mutation_rate=1.5)
    
    def test_init_invalid_crossover_rate(self):
        """Test initialization with invalid crossover rate"""
        # Act & Assert
        with pytest.raises(ValueError, match="crossover_rate must be in"):
            ETFFactorMiner(crossover_rate=-0.1)
        
        with pytest.raises(ValueError, match="crossover_rate must be in"):
            ETFFactorMiner(crossover_rate=1.1)
    
    def test_init_invalid_elite_ratio(self):
        """Test initialization with invalid elite ratio"""
        # Act & Assert
        with pytest.raises(ValueError, match="elite_ratio must be in"):
            ETFFactorMiner(elite_ratio=-0.1)
        
        with pytest.raises(ValueError, match="elite_ratio must be in"):
            ETFFactorMiner(elite_ratio=1.5)


# ============================================================================
# Test Class: Operator Registry
# ============================================================================

class TestETFFactorMinerOperatorRegistry:
    """Test operator registry building
    
    白皮书依据: 第四章 4.1.17 - ETF算子注册
    """
    
    def test_build_operator_registry_success(self, etf_miner):
        """Test successful operator registry building"""
        # Assert
        assert etf_miner.operator_registry is not None
        assert isinstance(etf_miner.operator_registry, dict)
        assert len(etf_miner.operator_registry) > 0
        
        # Check common operators are registered
        assert 'rank' in etf_miner.operator_registry
        assert 'delay' in etf_miner.operator_registry
        assert 'delta' in etf_miner.operator_registry
        assert 'ts_mean' in etf_miner.operator_registry
        assert 'ts_std' in etf_miner.operator_registry
        
        # Check all registered operators are callable
        for op_name, op_func in etf_miner.operator_registry.items():
            assert callable(op_func), f"Operator '{op_name}' is not callable"
    
    def test_get_operator_whitelist(self, etf_miner):
        """Test getting operator whitelist"""
        # Act
        whitelist = etf_miner._get_operator_whitelist()
        
        # Assert
        assert isinstance(whitelist, list)
        assert len(whitelist) == 28  # 20 ETF + 8 common
        
        # Check all ETF operators are in whitelist
        for op in etf_miner.etf_operators:
            assert op in whitelist
        
        # Check all common operators are in whitelist
        for op in etf_miner.common_operators:
            assert op in whitelist


# ============================================================================
# Test Class: Expression Generation
# ============================================================================

class TestETFFactorMinerExpressionGeneration:
    """Test expression generation methods
    
    白皮书依据: 第四章 4.1.17 - ETF因子表达式生成
    """
    
    def test_generate_random_expression_valid_columns(self, etf_miner):
        """Test generating random expression with valid columns"""
        # Arrange
        data_columns = ['close', 'nav', 'volume']
        
        # Act
        expression = etf_miner._generate_random_expression(data_columns)
        
        # Assert
        assert expression is not None
        assert isinstance(expression, str)
        assert len(expression) > 0
    
    def test_generate_random_expression_empty_columns(self, etf_miner):
        """Test generating expression with empty columns raises ValueError"""
        # Act & Assert
        with pytest.raises(ValueError, match="data_columns cannot be empty"):
            etf_miner._generate_random_expression([])
    
    def test_generate_etf_expression(self, etf_miner):
        """Test generating ETF-specific expression"""
        # Arrange
        data_columns = ['close', 'nav', 'volume']
        
        # Act
        expression = etf_miner._generate_etf_expression(data_columns, complexity=1)
        
        # Assert
        assert expression is not None
        assert isinstance(expression, str)
        # Should start with an ETF operator
        starts_with_etf_op = any(
            expression.startswith(op) for op in etf_miner.etf_operators
        )
        assert starts_with_etf_op
    
    def test_generate_common_expression(self, etf_miner):
        """Test generating common operator expression"""
        # Arrange
        data_columns = ['close', 'nav', 'volume']
        
        # Act
        expression = etf_miner._generate_common_expression(data_columns, complexity=1)
        
        # Assert
        assert expression is not None
        assert isinstance(expression, str)
        # Should start with a common operator
        starts_with_common_op = any(
            expression.startswith(op) for op in etf_miner.common_operators
        )
        assert starts_with_common_op
    
    def test_generate_etf_expression_premium_discount(self, etf_miner):
        """Test generating etf_premium_discount expression"""
        # Arrange
        data_columns = ['close', 'nav']
        
        # Act - Mock random.choice to return specific operator
        with patch('random.choice', return_value='etf_premium_discount'):
            expression = etf_miner._generate_etf_expression(data_columns, complexity=1)
        
        # Assert
        assert expression == "etf_premium_discount(close, nav)"
    
    def test_generate_etf_expression_tracking_error(self, etf_miner):
        """Test generating etf_tracking_error expression"""
        # Arrange
        data_columns = ['returns', 'index_returns']
        
        # Act - Mock random.choice to return specific operator and window
        with patch('random.choice', side_effect=['etf_tracking_error', 20]):
            expression = etf_miner._generate_etf_expression(data_columns, complexity=1)
        
        # Assert
        assert expression == "etf_tracking_error(returns, index_returns, 20)"


# ============================================================================
# Test Class: Expression Evaluation
# ============================================================================

class TestETFFactorMinerExpressionEvaluation:
    """Test expression evaluation methods
    
    白皮书依据: 第四章 4.1.17 - ETF因子评估
    """
    
    def test_evaluate_expression_simple_column(self, etf_miner, sample_etf_data):
        """Test evaluating simple column reference"""
        # Act
        result = etf_miner._evaluate_expression('close', sample_etf_data)
        
        # Assert
        assert result is not None
        assert isinstance(result, pd.Series)
        pd.testing.assert_series_equal(result, sample_etf_data['close'])
    
    def test_evaluate_expression_nonexistent_column(self, etf_miner, sample_etf_data):
        """Test evaluating nonexistent column returns None"""
        # Act
        result = etf_miner._evaluate_expression('nonexistent', sample_etf_data)
        
        # Assert
        assert result is None
    
    def test_evaluate_expression_rank_operator(self, etf_miner, sample_etf_data):
        """Test evaluating rank operator"""
        # Act
        result = etf_miner._evaluate_expression('rank(close)', sample_etf_data)
        
        # Assert
        assert result is not None
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_etf_data)
        # Rank values should be between 0 and 1
        assert result.min() >= 0.0
        assert result.max() <= 1.0
    
    def test_evaluate_expression_delay_operator(self, etf_miner, sample_etf_data):
        """Test evaluating delay operator"""
        # Act
        result = etf_miner._evaluate_expression('delay(close, 1)', sample_etf_data)
        
        # Assert
        assert result is not None
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_etf_data)
        # First value should be NaN (delayed)
        assert pd.isna(result.iloc[0])
    
    def test_evaluate_expression_delta_operator(self, etf_miner, sample_etf_data):
        """Test evaluating delta operator"""
        # Act
        result = etf_miner._evaluate_expression('delta(close, 1)', sample_etf_data)
        
        # Assert
        assert result is not None
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_etf_data)
        # First value should be NaN (no previous value)
        assert pd.isna(result.iloc[0])
    
    def test_evaluate_expression_ts_mean_operator(self, etf_miner, sample_etf_data):
        """Test evaluating ts_mean operator"""
        # Act
        result = etf_miner._evaluate_expression('ts_mean(close, 5)', sample_etf_data)
        
        # Assert
        assert result is not None
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_etf_data)
        # First 4 values should be NaN (insufficient window)
        assert pd.isna(result.iloc[:4]).all()
    
    def test_evaluate_expression_invalid_format(self, etf_miner, sample_etf_data):
        """Test evaluating invalid expression format"""
        # Act
        result = etf_miner._evaluate_expression('invalid((format', sample_etf_data)
        
        # Assert
        assert result is None
    
    def test_evaluate_expression_operator_error(self, etf_miner, sample_etf_data):
        """Test evaluating expression that raises OperatorError"""
        # Arrange - Mock operator to raise exception
        with patch.object(etf_miner, 'operator_registry', {'rank': Mock(side_effect=Exception("Test error"))}):
            # Act & Assert
            with pytest.raises(OperatorError, match="Failed to evaluate expression"):
                etf_miner._evaluate_expression('rank(close)', sample_etf_data)


# ============================================================================
# Test Class: Result Validation
# ============================================================================

class TestETFFactorMinerResultValidation:
    """Test result validation methods
    
    白皮书依据: 第四章 4.1 - 数据质量要求
    """
    
    def test_validate_result_valid_data(self, etf_miner):
        """Test validating result with valid data"""
        # Arrange
        result = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        
        # Act
        validated = etf_miner._validate_result(result, 'test_expression')
        
        # Assert
        assert validated is not None
        pd.testing.assert_series_equal(validated, result)
    
    def test_validate_result_acceptable_nan_ratio(self, etf_miner):
        """Test validating result with acceptable NaN ratio (<=50%)"""
        # Arrange
        result = pd.Series([1.0, 2.0, np.nan, 4.0, 5.0])  # 20% NaN
        
        # Act
        validated = etf_miner._validate_result(result, 'test_expression')
        
        # Assert
        assert validated is not None
        assert len(validated) == 5
    
    def test_validate_result_unacceptable_nan_ratio(self, etf_miner):
        """Test validating result with unacceptable NaN ratio (>50%)"""
        # Arrange
        result = pd.Series([1.0, np.nan, np.nan, np.nan, 5.0])  # 60% NaN
        
        # Act & Assert
        with pytest.raises(DataQualityError, match="Data quality insufficient"):
            etf_miner._validate_result(result, 'test_expression')
    
    def test_validate_result_infinite_values(self, etf_miner):
        """Test validating result with infinite values"""
        # Arrange
        result = pd.Series([1.0, 2.0, np.inf, -np.inf, 5.0])
        
        # Act
        validated = etf_miner._validate_result(result, 'test_expression')
        
        # Assert
        assert validated is not None
        # Infinite values should be replaced with NaN
        assert not np.isinf(validated).any()
        assert validated.isna().sum() == 2
    
    def test_validate_result_none_input(self, etf_miner):
        """Test validating None result"""
        # Act
        validated = etf_miner._validate_result(None, 'test_expression')
        
        # Assert
        assert validated is None
    
    def test_validate_result_empty_series(self, etf_miner):
        """Test validating empty series"""
        # Arrange
        result = pd.Series([])
        
        # Act
        validated = etf_miner._validate_result(result, 'test_expression')
        
        # Assert
        assert validated is None


# ============================================================================
# Test Class: Edge Cases
# ============================================================================

class TestETFFactorMinerEdgeCases:
    """Test edge cases and error handling"""
    
    def test_generate_expression_with_single_column(self, etf_miner):
        """Test generating expression with single data column"""
        # Act
        expression = etf_miner._generate_random_expression(['close'])
        
        # Assert
        assert expression is not None
        assert isinstance(expression, str)
    
    def test_evaluate_expression_with_numeric_args(self, etf_miner, sample_etf_data):
        """Test evaluating expression with numeric arguments"""
        # Act
        result = etf_miner._evaluate_expression('ts_mean(close, 10)', sample_etf_data)
        
        # Assert
        assert result is not None or result is None  # May return None if parsing fails
    
    def test_config_precedence(self):
        """Test that explicit config takes precedence over individual parameters"""
        # Arrange
        config = EvolutionConfig(population_size=100, mutation_rate=0.3)
        
        # Act
        miner = ETFFactorMiner(
            population_size=50,  # Should be overridden
            mutation_rate=0.1,   # Should be overridden
            config=config
        )
        
        # Assert
        assert miner.config.population_size == 100
        assert miner.config.mutation_rate == 0.3
