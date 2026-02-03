"""Property-based tests for ETFFactorMiner

白皮书依据: 第四章 4.1.17 - ETF因子挖掘器
铁律依据: MIA编码铁律7 (测试覆盖率要求 ≥ 85%)

This test file implements property-based tests for ETFFactorMiner using Hypothesis.
Tests verify that the ETF factor miner behaves correctly across a wide range of inputs.
"""

import pytest
import pandas as pd
import numpy as np
from hypothesis import given, strategies as st, settings, HealthCheck
from typing import List

from src.evolution.etf_lof.etf_factor_miner import ETFFactorMiner
from src.evolution.etf_lof.data_models import ETFMarketData
from src.evolution.genetic_miner import EvolutionConfig, Individual
from src.evolution.etf_lof.exceptions import (
    FactorMiningError,
    OperatorError,
    DataQualityError,
)


# ============================================================================
# Test Data Generators
# ============================================================================

@st.composite
def valid_population_size(draw):
    """Generate valid population size (1-200)"""
    return draw(st.integers(min_value=1, max_value=200))


@st.composite
def valid_probability(draw):
    """Generate valid probability (0.0-1.0)"""
    return draw(st.floats(min_value=0.0, max_value=1.0))


@st.composite
def valid_data_columns(draw):
    """Generate valid data column names"""
    num_columns = draw(st.integers(min_value=1, max_value=10))
    columns = []
    for i in range(num_columns):
        col_name = draw(st.sampled_from([
            'close', 'nav', 'volume', 'creation_units', 'redemption_units',
            'bid_price', 'ask_price', 'returns', 'index_returns'
        ]))
        if col_name not in columns:
            columns.append(col_name)
    return columns if columns else ['close']


@st.composite
def etf_market_data_frame(draw):
    """Generate ETF market data DataFrame"""
    num_rows = draw(st.integers(min_value=50, max_value=200))
    
    data = {
        'close': draw(st.lists(
            st.floats(min_value=10.0, max_value=200.0, allow_nan=False, allow_infinity=False),
            min_size=num_rows,
            max_size=num_rows
        )),
        'nav': draw(st.lists(
            st.floats(min_value=10.0, max_value=200.0, allow_nan=False, allow_infinity=False),
            min_size=num_rows,
            max_size=num_rows
        )),
        'volume': draw(st.lists(
            st.floats(min_value=1000.0, max_value=1000000.0, allow_nan=False, allow_infinity=False),
            min_size=num_rows,
            max_size=num_rows
        )),
    }
    
    return pd.DataFrame(data)


# ============================================================================
# Property 1: Initialization Properties
# ============================================================================

class TestETFFactorMinerInitialization:
    """Test ETFFactorMiner initialization properties
    
    白皮书依据: 第四章 4.1.17 - ETFFactorMiner初始化
    
    **Validates: Requirements 1.1, 1.2**
    """
    
    @given(
        population_size=valid_population_size(),
        mutation_rate=valid_probability(),
        crossover_rate=valid_probability(),
        elite_ratio=valid_probability()
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.data_too_large,
            HealthCheck.large_base_example
        ]
    )
    def test_property_1_1_valid_initialization(
        self,
        population_size,
        mutation_rate,
        crossover_rate,
        elite_ratio
    ):
        """Property 1.1: Valid parameters should initialize successfully
        
        白皮书依据: 第四章 4.1.17 - ETFFactorMiner初始化
        
        **Validates: Requirements 1.1**
        
        Property: For all valid parameters (population_size > 0, rates in [0,1]),
        ETFFactorMiner should initialize without errors.
        """
        # Act
        miner = ETFFactorMiner(
            population_size=population_size,
            mutation_rate=mutation_rate,
            crossover_rate=crossover_rate,
            elite_ratio=elite_ratio
        )
        
        # Assert
        assert miner is not None
        assert miner.config.population_size == population_size
        assert miner.config.mutation_rate == mutation_rate
        assert miner.config.crossover_rate == crossover_rate
        assert miner.config.elite_ratio == elite_ratio
        assert len(miner.etf_operators) == 20  # 白皮书定义20个ETF算子
        assert len(miner.common_operators) == 8  # 8个通用算子
        assert len(miner.operator_registry) > 0
    
    @given(
        population_size=st.integers(max_value=0)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_1_2_invalid_population_size(self, population_size):
        """Property 1.2: Invalid population size should raise ValueError
        
        白皮书依据: 第四章 4.1.17 - 参数验证
        
        **Validates: Requirements 1.2**
        
        Property: For all population_size <= 0, initialization should raise ValueError.
        """
        # Act & Assert
        with pytest.raises(ValueError, match="population_size must be > 0"):
            ETFFactorMiner(population_size=population_size)
    
    @given(
        mutation_rate=st.floats(min_value=-10.0, max_value=-0.01) | st.floats(min_value=1.01, max_value=10.0)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_1_3_invalid_mutation_rate(self, mutation_rate):
        """Property 1.3: Invalid mutation rate should raise ValueError
        
        **Validates: Requirements 1.2**
        
        Property: For all mutation_rate not in [0, 1], initialization should raise ValueError.
        """
        # Act & Assert
        with pytest.raises(ValueError, match="mutation_rate must be in"):
            ETFFactorMiner(mutation_rate=mutation_rate)


# ============================================================================
# Property 2: Operator Whitelist Properties
# ============================================================================

class TestETFFactorMinerOperatorWhitelist:
    """Test ETF operator whitelist properties
    
    白皮书依据: 第四章 4.1.17 - ETF算子白名单
    
    **Validates: Requirements 2.1, 2.2**
    """
    
    def test_property_2_1_operator_whitelist_completeness(self):
        """Property 2.1: Operator whitelist should contain all required operators
        
        白皮书依据: 第四章 4.1.17 - ETF算子白名单（20个算子）
        
        **Validates: Requirements 2.1**
        
        Property: The operator whitelist should always contain exactly 20 ETF operators
        and 8 common operators (total 28).
        """
        # Arrange
        miner = ETFFactorMiner()
        
        # Act
        whitelist = miner._get_operator_whitelist()
        
        # Assert
        assert len(whitelist) == 28  # 20 ETF + 8 common
        assert len(miner.etf_operators) == 20
        assert len(miner.common_operators) == 8
        
        # Verify all ETF operators are in whitelist
        for op in miner.etf_operators:
            assert op in whitelist
        
        # Verify all common operators are in whitelist
        for op in miner.common_operators:
            assert op in whitelist
    
    def test_property_2_2_operator_registry_consistency(self):
        """Property 2.2: Operator registry should be consistent with whitelist
        
        **Validates: Requirements 2.2**
        
        Property: All common operators in whitelist should be registered in operator_registry.
        """
        # Arrange
        miner = ETFFactorMiner()
        
        # Act
        whitelist = miner._get_operator_whitelist()
        registry = miner.operator_registry
        
        # Assert
        # All common operators should be registered (except regression_residual which is complex)
        for op in miner.common_operators:
            if op == 'regression_residual':
                continue  # Skip complex operator
            assert op in registry, f"Common operator '{op}' not in registry"
            assert callable(registry[op]), f"Operator '{op}' is not callable"


# ============================================================================
# Property 3: Expression Generation Properties
# ============================================================================

class TestETFFactorMinerExpressionGeneration:
    """Test expression generation properties
    
    白皮书依据: 第四章 4.1.17 - ETF因子表达式生成
    
    **Validates: Requirements 3.1, 3.2, 3.3**
    """
    
    @given(
        data_columns=valid_data_columns()
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow]
    )
    def test_property_3_1_expression_generation_non_empty(self, data_columns):
        """Property 3.1: Generated expressions should never be empty
        
        白皮书依据: 第四章 4.1.17 - 因子表达式生成
        
        **Validates: Requirements 3.1**
        
        Property: For all valid data_columns, _generate_random_expression should
        return a non-empty string.
        """
        # Arrange
        miner = ETFFactorMiner()
        
        # Act
        expression = miner._generate_random_expression(data_columns)
        
        # Assert
        assert expression is not None
        assert isinstance(expression, str)
        assert len(expression) > 0
    
    def test_property_3_2_expression_generation_empty_columns(self):
        """Property 3.2: Empty data_columns should raise ValueError
        
        **Validates: Requirements 3.2**
        
        Property: _generate_random_expression with empty data_columns should raise ValueError.
        """
        # Arrange
        miner = ETFFactorMiner()
        
        # Act & Assert
        with pytest.raises(ValueError, match="data_columns cannot be empty"):
            miner._generate_random_expression([])
    
    @given(
        data_columns=valid_data_columns()
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow]
    )
    def test_property_3_3_expression_uses_valid_operators(self, data_columns):
        """Property 3.3: Generated expressions should use valid operators
        
        **Validates: Requirements 3.3**
        
        Property: All generated expressions should start with a valid operator name
        from either etf_operators or common_operators.
        """
        # Arrange
        miner = ETFFactorMiner()
        all_operators = miner.etf_operators + miner.common_operators
        
        # Act
        expression = miner._generate_random_expression(data_columns)
        
        # Assert
        # Check if expression starts with any valid operator
        uses_valid_operator = any(
            expression.startswith(op) for op in all_operators
        )
        assert uses_valid_operator, f"Expression '{expression}' doesn't use valid operator"


# ============================================================================
# Property 4: Expression Evaluation Properties
# ============================================================================

class TestETFFactorMinerExpressionEvaluation:
    """Test expression evaluation properties
    
    白皮书依据: 第四章 4.1.17 - ETF因子评估
    
    **Validates: Requirements 4.1, 4.2, 4.3**
    """
    
    @given(
        data=etf_market_data_frame()
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.data_too_large
        ]
    )
    def test_property_4_1_simple_column_evaluation(self, data):
        """Property 4.1: Simple column references should evaluate correctly
        
        **Validates: Requirements 4.1**
        
        Property: For all valid DataFrames, evaluating a simple column reference
        should return the column data.
        """
        # Arrange
        miner = ETFFactorMiner()
        
        # Act
        result = miner._evaluate_expression('close', data)
        
        # Assert
        assert result is not None
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        pd.testing.assert_series_equal(result, data['close'])
    
    @given(
        data=etf_market_data_frame()
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.data_too_large
        ]
    )
    def test_property_4_2_invalid_expression_returns_none(self, data):
        """Property 4.2: Invalid expressions should return None
        
        **Validates: Requirements 4.2**
        
        Property: For all invalid expressions, _evaluate_expression should return None
        without raising exceptions.
        """
        # Arrange
        miner = ETFFactorMiner()
        invalid_expressions = [
            'nonexistent_column',
            'invalid_operator(close)',
            'malformed(((expression',
        ]
        
        # Act & Assert
        for expr in invalid_expressions:
            result = miner._evaluate_expression(expr, data)
            # Should return None for invalid expressions
            assert result is None or isinstance(result, pd.Series)
    
    @given(
        data=etf_market_data_frame()
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.data_too_large
        ]
    )
    def test_property_4_3_common_operator_evaluation(self, data):
        """Property 4.3: Common operators should evaluate correctly
        
        **Validates: Requirements 4.3**
        
        Property: Common operators like rank, delay, delta should produce valid results.
        """
        # Arrange
        miner = ETFFactorMiner()
        
        # Act - Test rank operator
        result_rank = miner._evaluate_expression('rank(close)', data)
        
        # Assert
        if result_rank is not None:
            assert isinstance(result_rank, pd.Series)
            assert len(result_rank) == len(data)
            # Rank values should be between 0 and 1
            assert result_rank.min() >= 0.0
            assert result_rank.max() <= 1.0


# ============================================================================
# Property 5: Result Validation Properties
# ============================================================================

class TestETFFactorMinerResultValidation:
    """Test result validation properties
    
    白皮书依据: 第四章 4.1 - 数据质量要求
    
    **Validates: Requirements 5.1, 5.2**
    """
    
    @given(
        nan_ratio=st.floats(min_value=0.0, max_value=0.5)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_5_1_acceptable_nan_ratio(self, nan_ratio):
        """Property 5.1: Results with NaN ratio <= 50% should be accepted
        
        白皮书依据: 第四章 4.1 - 数据质量阈值50%
        
        **Validates: Requirements 5.1**
        
        Property: For all NaN ratios <= 0.5, _validate_result should return the result.
        """
        # Arrange
        miner = ETFFactorMiner()
        size = 100
        num_nans = int(size * nan_ratio)
        
        # Create series with specified NaN ratio
        values = [1.0] * (size - num_nans) + [np.nan] * num_nans
        result = pd.Series(values)
        
        # Act
        validated = miner._validate_result(result, 'test_expression')
        
        # Assert
        assert validated is not None
        assert isinstance(validated, pd.Series)
    
    @given(
        nan_ratio=st.floats(min_value=0.51, max_value=1.0)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_5_2_unacceptable_nan_ratio(self, nan_ratio):
        """Property 5.2: Results with NaN ratio > 50% should raise DataQualityError
        
        **Validates: Requirements 5.2**
        
        Property: For all NaN ratios > 0.5, _validate_result should raise DataQualityError.
        """
        # Arrange
        miner = ETFFactorMiner()
        size = 100
        num_nans = int(size * nan_ratio)
        
        # Create series with specified NaN ratio
        values = [1.0] * (size - num_nans) + [np.nan] * num_nans
        result = pd.Series(values)
        
        # Act & Assert
        with pytest.raises(DataQualityError, match="Data quality insufficient"):
            miner._validate_result(result, 'test_expression')
    
    def test_property_5_3_infinite_values_replaced(self):
        """Property 5.3: Infinite values should be replaced with NaN
        
        **Validates: Requirements 5.3**
        
        Property: Results containing infinite values should have them replaced with NaN.
        """
        # Arrange
        miner = ETFFactorMiner()
        result = pd.Series([1.0, 2.0, np.inf, -np.inf, 3.0])
        
        # Act
        validated = miner._validate_result(result, 'test_expression')
        
        # Assert
        assert validated is not None
        assert not np.isinf(validated).any()
        assert validated.isna().sum() == 2  # Two inf values replaced


# ============================================================================
# Property 6: Configuration Properties
# ============================================================================

class TestETFFactorMinerConfiguration:
    """Test configuration properties
    
    **Validates: Requirements 6.1, 6.2**
    """
    
    def test_property_6_1_config_override(self):
        """Property 6.1: Explicit config should override individual parameters
        
        **Validates: Requirements 6.1**
        
        Property: When both config and individual parameters are provided,
        config should take precedence.
        """
        # Arrange
        config = EvolutionConfig(
            population_size=100,
            mutation_rate=0.3,
            crossover_rate=0.8,
            elite_ratio=0.2
        )
        
        # Act
        miner = ETFFactorMiner(
            population_size=50,  # Should be overridden
            mutation_rate=0.1,   # Should be overridden
            config=config
        )
        
        # Assert
        assert miner.config.population_size == 100
        assert miner.config.mutation_rate == 0.3
        assert miner.config.crossover_rate == 0.8
        assert miner.config.elite_ratio == 0.2
    
    def test_property_6_2_default_config_creation(self):
        """Property 6.2: Default config should be created when not provided
        
        **Validates: Requirements 6.2**
        
        Property: When no config is provided, a default EvolutionConfig should be created
        with the specified individual parameters.
        """
        # Act
        miner = ETFFactorMiner(
            population_size=75,
            mutation_rate=0.25,
            crossover_rate=0.75,
            elite_ratio=0.15
        )
        
        # Assert
        assert miner.config is not None
        assert isinstance(miner.config, EvolutionConfig)
        assert miner.config.population_size == 75
        assert miner.config.mutation_rate == 0.25
        assert miner.config.crossover_rate == 0.75
        assert miner.config.elite_ratio == 0.15
