"""Property-based tests for core LOF operators (operators 1-5)

白皮书依据: 第四章 4.1.18 - LOF基金因子挖掘器
测试属性:
- Property 8: LOF Onmarket/Offmarket Spread Calculation Correctness
- Property 10: LOF Operator Mathematical Correctness (operators 1-5)
- Property 14: Error Handling for Invalid Operator Inputs

验收标准: Requirements 4.1-4.5, 8.1, 8.2
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import pandas as pd
import numpy as np
from datetime import date, timedelta

from src.evolution.etf_lof.lof_operators import LOFOperators
from src.evolution.etf_lof.exceptions import OperatorError, DataQualityError


# ============================================================================
# Test Data Generators
# ============================================================================

@st.composite
def valid_lof_data(draw, min_rows=30, max_rows=100):
    """Generate valid LOF market data for testing
    
    Args:
        draw: Hypothesis draw function
        min_rows: Minimum number of rows
        max_rows: Maximum number of rows
        
    Returns:
        DataFrame with valid LOF data
    """
    n_rows = draw(st.integers(min_value=min_rows, max_value=max_rows))
    
    # Generate base NAV
    nav_base = draw(st.floats(min_value=1.0, max_value=10.0))
    offmarket_nav = [nav_base * (1 + draw(st.floats(min_value=-0.05, max_value=0.05))) 
                     for _ in range(n_rows)]
    
    # Generate onmarket price (with premium/discount)
    onmarket_price = [nav * (1 + draw(st.floats(min_value=-0.03, max_value=0.03))) 
                      for nav in offmarket_nav]
    
    # Generate volume
    onmarket_volume = [draw(st.floats(min_value=10000.0, max_value=1000000.0)) 
                       for _ in range(n_rows)]
    
    # Generate redemption amount
    redemption_amount = [draw(st.floats(min_value=5000.0, max_value=500000.0)) 
                         for _ in range(n_rows)]
    
    return pd.DataFrame({
        'onmarket_price': onmarket_price,
        'offmarket_nav': offmarket_nav,
        'onmarket_volume': onmarket_volume,
        'redemption_amount': redemption_amount
    })


# ============================================================================
# Property 8: LOF Onmarket/Offmarket Spread Calculation Correctness
# ============================================================================

class TestProperty8SpreadCorrectness:
    """Property 8: LOF Onmarket/Offmarket Spread Calculation Correctness
    
    白皮书依据: 第四章 4.1.18 - lof_onoff_price_spread
    验收标准: Requirement 4.1
    
    验证LOF场内外价差计算的正确性
    """
    
    @given(data=valid_lof_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_spread_formula_correctness(self, data):
        """测试场内外价差公式正确性
        
        白皮书依据: 第四章 4.1.18 - lof_onoff_price_spread
        公式: (onmarket_price - offmarket_nav) / offmarket_nav
        """
        operators = LOFOperators()
        
        result = operators.lof_onoff_price_spread(data)
        
        # Calculate manually
        expected = (data['onmarket_price'] - data['offmarket_nav']) / data['offmarket_nav']
        
        # Verify correctness
        np.testing.assert_allclose(
            result.values,
            expected.values,
            rtol=1e-10,
            err_msg="LOF spread calculation incorrect"
        )
    
    @given(data=valid_lof_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_spread_sign_correctness(self, data):
        """测试场内外价差符号正确性
        
        场内价格 > 场外净值 => 正价差（溢价）
        场内价格 < 场外净值 => 负价差（折价）
        """
        operators = LOFOperators()
        
        result = operators.lof_onoff_price_spread(data)
        
        # Verify sign correctness
        for i in range(len(data)):
            if data['onmarket_price'].iloc[i] > data['offmarket_nav'].iloc[i]:
                assert result.iloc[i] > 0, f"Expected positive spread at index {i}"
            elif data['onmarket_price'].iloc[i] < data['offmarket_nav'].iloc[i]:
                assert result.iloc[i] < 0, f"Expected negative spread at index {i}"
    
    @given(data=valid_lof_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_spread_zero_when_equal(self, data):
        """测试场内外价格相等时价差为零"""
        operators = LOFOperators()
        
        # Set onmarket price equal to offmarket nav
        data_equal = data.copy()
        data_equal['onmarket_price'] = data_equal['offmarket_nav']
        
        result = operators.lof_onoff_price_spread(data_equal)
        
        # Verify spread is zero
        np.testing.assert_allclose(
            result.values,
            np.zeros(len(data_equal)),
            atol=1e-10,
            err_msg="Spread should be zero when prices are equal"
        )


# ============================================================================
# Property 10: LOF Operator Mathematical Correctness (operators 1-5)
# ============================================================================

class TestProperty10OperatorMathematicalCorrectness:
    """Property 10: LOF Operator Mathematical Correctness (operators 1-5)
    
    白皮书依据: 第四章 4.1.18 - LOF Operators 1-5
    验收标准: Requirements 4.1-4.5
    
    验证LOF核心算子的数学正确性
    """
    
    @given(data=valid_lof_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_transfer_arbitrage_opportunity_logic(self, data):
        """测试转托管套利机会逻辑正确性
        
        白皮书依据: 第四章 4.1.18 - lof_transfer_arbitrage_opportunity
        """
        operators = LOFOperators()
        
        transaction_cost = 0.01  # 1%
        result = operators.lof_transfer_arbitrage_opportunity(data, transaction_cost=transaction_cost)
        
        # Calculate spread
        spread = operators.lof_onoff_price_spread(data)
        
        # Verify arbitrage opportunity logic
        for i in range(len(data)):
            if np.abs(spread.iloc[i]) > transaction_cost:
                assert result.iloc[i] == 1.0, f"Expected arbitrage opportunity at index {i}"
            else:
                assert result.iloc[i] == 0.0, f"Expected no arbitrage opportunity at index {i}"
    
    @given(data=valid_lof_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_premium_discount_rate_correctness(self, data):
        """测试折溢价率计算正确性
        
        白皮书依据: 第四章 4.1.18 - lof_premium_discount_rate
        """
        operators = LOFOperators()
        
        window = 10
        result = operators.lof_premium_discount_rate(data, window=window)
        
        # Calculate manually
        spread = operators.lof_onoff_price_spread(data)
        expected = spread.rolling(window=window).mean()
        
        # Verify correctness
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-10,
            err_msg="Premium discount rate calculation incorrect"
        )
    
    @given(data=valid_lof_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_onmarket_liquidity_correctness(self, data):
        """测试场内流动性计算正确性
        
        白皮书依据: 第四章 4.1.18 - lof_onmarket_liquidity
        """
        operators = LOFOperators()
        
        window = 10
        result = operators.lof_onmarket_liquidity(data, window=window)
        
        # Calculate manually
        expected = data['onmarket_volume'].rolling(window=window).mean()
        
        # Verify correctness
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-10,
            err_msg="Onmarket liquidity calculation incorrect"
        )
    
    @given(data=valid_lof_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_offmarket_liquidity_correctness(self, data):
        """测试场外流动性计算正确性
        
        白皮书依据: 第四章 4.1.18 - lof_offmarket_liquidity
        """
        operators = LOFOperators()
        
        window = 10
        result = operators.lof_offmarket_liquidity(data, window=window)
        
        # Calculate manually
        expected = data['redemption_amount'].rolling(window=window).mean()
        
        # Verify correctness
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-10,
            err_msg="Offmarket liquidity calculation incorrect"
        )
    
    @given(data=valid_lof_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_operators_return_correct_length(self, data):
        """测试所有核心算子返回正确长度"""
        operators = LOFOperators()
        
        # Test all 5 core operators
        result1 = operators.lof_onoff_price_spread(data)
        assert len(result1) == len(data), "lof_onoff_price_spread length mismatch"
        
        result2 = operators.lof_transfer_arbitrage_opportunity(data)
        assert len(result2) == len(data), "lof_transfer_arbitrage_opportunity length mismatch"
        
        result3 = operators.lof_premium_discount_rate(data, window=10)
        assert len(result3) == len(data), "lof_premium_discount_rate length mismatch"
        
        result4 = operators.lof_onmarket_liquidity(data, window=10)
        assert len(result4) == len(data), "lof_onmarket_liquidity length mismatch"
        
        result5 = operators.lof_offmarket_liquidity(data, window=10)
        assert len(result5) == len(data), "lof_offmarket_liquidity length mismatch"
    
    @given(data=valid_lof_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_operators_return_numeric_values(self, data):
        """测试所有核心算子返回数值类型"""
        operators = LOFOperators()
        
        # Test all 5 core operators
        result1 = operators.lof_onoff_price_spread(data)
        assert pd.api.types.is_numeric_dtype(result1), \
            "lof_onoff_price_spread should return numeric values"
        
        result2 = operators.lof_transfer_arbitrage_opportunity(data)
        assert pd.api.types.is_numeric_dtype(result2), \
            "lof_transfer_arbitrage_opportunity should return numeric values"
        
        result3 = operators.lof_premium_discount_rate(data, window=10)
        assert pd.api.types.is_numeric_dtype(result3), \
            "lof_premium_discount_rate should return numeric values"
        
        result4 = operators.lof_onmarket_liquidity(data, window=10)
        assert pd.api.types.is_numeric_dtype(result4), \
            "lof_onmarket_liquidity should return numeric values"
        
        result5 = operators.lof_offmarket_liquidity(data, window=10)
        assert pd.api.types.is_numeric_dtype(result5), \
            "lof_offmarket_liquidity should return numeric values"



# ============================================================================
# Property 14: Error Handling for Invalid Operator Inputs
# ============================================================================

class TestProperty14ErrorHandling:
    """Property 14: Error Handling for Invalid Operator Inputs
    
    白皮书依据: 第四章 4.1 - Error Handling Standards
    验收标准: Requirement 8.1
    
    验证LOF算子的错误处理
    """
    
    def test_empty_dataframe_raises_error(self):
        """测试空数据框抛出错误"""
        operators = LOFOperators()
        
        empty_data = pd.DataFrame()
        
        with pytest.raises(OperatorError, match="Input data is empty"):
            operators.lof_onoff_price_spread(empty_data)
    
    def test_missing_required_columns_raises_error(self):
        """测试缺失必需列抛出错误"""
        operators = LOFOperators()
        
        # Missing 'offmarket_nav' column
        incomplete_data = pd.DataFrame({
            'onmarket_price': [1.0, 1.1, 1.2]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.lof_onoff_price_spread(incomplete_data)
    
    def test_excessive_nan_values_raises_error(self):
        """测试过多NaN值抛出错误"""
        operators = LOFOperators()
        
        # Create data with >20% NaN values
        data_with_nans = pd.DataFrame({
            'onmarket_price': [1.0, np.nan, np.nan, 1.3, 1.4],
            'offmarket_nav': [1.0, 1.0, 1.1, 1.2, 1.3]
        })
        
        with pytest.raises(DataQualityError, match="too many NaN values"):
            operators.lof_onoff_price_spread(data_with_nans)
    
    def test_transfer_arbitrage_missing_columns(self):
        """测试转托管套利缺失列错误"""
        operators = LOFOperators()
        
        # Missing 'offmarket_nav' column
        incomplete_data = pd.DataFrame({
            'onmarket_price': [1.0, 1.1, 1.2]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.lof_transfer_arbitrage_opportunity(incomplete_data)
    
    def test_premium_discount_rate_missing_columns(self):
        """测试折溢价率缺失列错误"""
        operators = LOFOperators()
        
        # Missing 'onmarket_price' column
        incomplete_data = pd.DataFrame({
            'offmarket_nav': [1.0, 1.1, 1.2]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.lof_premium_discount_rate(incomplete_data)
    
    def test_onmarket_liquidity_missing_columns(self):
        """测试场内流动性缺失列错误"""
        operators = LOFOperators()
        
        # Missing 'onmarket_volume' column
        incomplete_data = pd.DataFrame({
            'onmarket_price': [1.0, 1.1, 1.2]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.lof_onmarket_liquidity(incomplete_data)
    
    def test_offmarket_liquidity_missing_columns(self):
        """测试场外流动性缺失列错误"""
        operators = LOFOperators()
        
        # Missing 'redemption_amount' column
        incomplete_data = pd.DataFrame({
            'onmarket_price': [1.0, 1.1, 1.2]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.lof_offmarket_liquidity(incomplete_data)
    
    def test_invalid_window_parameter(self):
        """测试无效window参数"""
        operators = LOFOperators()
        
        data = pd.DataFrame({
            'onmarket_price': [1.0, 1.1, 1.2],
            'offmarket_nav': [1.0, 1.0, 1.1]
        })
        
        with pytest.raises(ValueError, match="window must be > 0"):
            operators.lof_premium_discount_rate(data, window=0)
        
        with pytest.raises(ValueError, match="window must be > 0"):
            operators.lof_premium_discount_rate(data, window=-5)
    
    @given(data=valid_lof_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_operators_handle_valid_data_without_errors(self, data):
        """测试算子在有效数据下不抛出错误"""
        operators = LOFOperators()
        
        # All operators should work without errors on valid data
        try:
            operators.lof_onoff_price_spread(data)
            operators.lof_transfer_arbitrage_opportunity(data)
            operators.lof_premium_discount_rate(data, window=10)
            operators.lof_onmarket_liquidity(data, window=10)
            operators.lof_offmarket_liquidity(data, window=10)
        except Exception as e:
            pytest.fail(f"Operator raised unexpected error on valid data: {e}")



# ============================================================================
# Additional Property Tests
# ============================================================================

class TestAdditionalProperties:
    """Additional property tests for core LOF operators"""
    
    @given(data=valid_lof_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_operators_are_deterministic(self, data):
        """测试算子是确定性的（相同输入产生相同输出）"""
        operators = LOFOperators()
        
        # Run twice with same data
        result1 = operators.lof_onoff_price_spread(data)
        result2 = operators.lof_onoff_price_spread(data)
        
        # Should be identical
        pd.testing.assert_series_equal(result1, result2)
    
    @given(data=valid_lof_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_arbitrage_opportunity_is_binary(self, data):
        """测试套利机会是二值的（0或1）"""
        operators = LOFOperators()
        
        result = operators.lof_transfer_arbitrage_opportunity(data)
        
        # Should only contain 0.0 or 1.0
        unique_values = result.unique()
        assert all(v in [0.0, 1.0] for v in unique_values), \
            f"Arbitrage opportunity should be binary, got {unique_values}"
    
    @given(data=valid_lof_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_liquidity_is_non_negative(self, data):
        """测试流动性指标非负"""
        operators = LOFOperators()
        
        # Onmarket liquidity should be non-negative
        result1 = operators.lof_onmarket_liquidity(data, window=10)
        valid_values1 = result1.dropna()
        if len(valid_values1) > 0:
            assert (valid_values1 >= 0).all(), "Onmarket liquidity should be non-negative"
        
        # Offmarket liquidity should be non-negative
        result2 = operators.lof_offmarket_liquidity(data, window=10)
        valid_values2 = result2.dropna()
        if len(valid_values2) > 0:
            assert (valid_values2 >= 0).all(), "Offmarket liquidity should be non-negative"
    
    @given(data=valid_lof_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_spread_symmetry(self, data):
        """测试价差对称性
        
        如果场内溢价x%，则场外折价应该约为-x%
        """
        operators = LOFOperators()
        
        # Calculate spread from onmarket perspective
        spread_onmarket = operators.lof_onoff_price_spread(data)
        
        # Calculate spread from offmarket perspective (inverse)
        data_inverse = data.copy()
        data_inverse['onmarket_price'], data_inverse['offmarket_nav'] = \
            data['offmarket_nav'], data['onmarket_price']
        spread_offmarket = operators.lof_onoff_price_spread(data_inverse)
        
        # Spreads should have opposite signs (approximately)
        for i in range(len(data)):
            if not np.isnan(spread_onmarket.iloc[i]) and not np.isnan(spread_offmarket.iloc[i]):
                # If onmarket is premium, offmarket should be discount
                if spread_onmarket.iloc[i] > 0.01:
                    assert spread_offmarket.iloc[i] < 0, \
                        f"Spread symmetry violated at index {i}"
                elif spread_onmarket.iloc[i] < -0.01:
                    assert spread_offmarket.iloc[i] > 0, \
                        f"Spread symmetry violated at index {i}"
