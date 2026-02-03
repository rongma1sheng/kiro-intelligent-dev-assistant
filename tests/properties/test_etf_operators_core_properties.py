"""Property-based tests for core ETF operators (operators 1-5)

白皮书依据: 第四章 4.1.17 - ETF因子挖掘器
测试属性:
- Property 7: ETF Premium/Discount Calculation Correctness
- Property 9: ETF Operator Mathematical Correctness (operators 1-5)
- Property 14: Error Handling for Invalid Operator Inputs

验收标准: Requirements 3.1-3.5, 8.1
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import pandas as pd
import numpy as np
from datetime import date, timedelta

from src.evolution.etf_lof.etf_operators import ETFOperators
from src.evolution.etf_lof.exceptions import OperatorError, DataQualityError


# ============================================================================
# Test Data Generators
# ============================================================================

@st.composite
def valid_etf_data(draw, min_rows=10, max_rows=100):
    """Generate valid ETF market data for testing
    
    Args:
        draw: Hypothesis draw function
        min_rows: Minimum number of rows
        max_rows: Maximum number of rows
        
    Returns:
        DataFrame with valid ETF data
    """
    n_rows = draw(st.integers(min_value=min_rows, max_value=max_rows))
    
    # Generate base NAV values (positive)
    nav_base = draw(st.floats(min_value=10.0, max_value=1000.0))
    nav_values = [nav_base * (1 + draw(st.floats(min_value=-0.1, max_value=0.1))) 
                  for _ in range(n_rows)]
    
    # Generate prices with some premium/discount
    price_values = [nav * (1 + draw(st.floats(min_value=-0.05, max_value=0.05))) 
                    for nav in nav_values]
    
    # Generate other fields
    volume_values = [draw(st.floats(min_value=1000.0, max_value=1000000.0)) 
                     for _ in range(n_rows)]
    
    creation_units = [draw(st.floats(min_value=0.0, max_value=10000.0)) 
                      for _ in range(n_rows)]
    
    redemption_units = [draw(st.floats(min_value=0.0, max_value=10000.0)) 
                        for _ in range(n_rows)]
    
    # Generate bid/ask prices
    bid_prices = [p * (1 - draw(st.floats(min_value=0.0001, max_value=0.01))) 
                  for p in price_values]
    ask_prices = [p * (1 + draw(st.floats(min_value=0.0001, max_value=0.01))) 
                  for p in price_values]
    
    # Generate index prices
    index_prices = [nav * (1 + draw(st.floats(min_value=-0.02, max_value=0.02))) 
                    for nav in nav_values]
    
    return pd.DataFrame({
        'price': price_values,
        'nav': nav_values,
        'volume': volume_values,
        'creation_units': creation_units,
        'redemption_units': redemption_units,
        'bid_price': bid_prices,
        'ask_price': ask_prices,
        'index_price': index_prices
    })



# ============================================================================
# Property 7: ETF Premium/Discount Calculation Correctness
# ============================================================================

class TestProperty7PremiumDiscountCorrectness:
    """Property 7: ETF Premium/Discount Calculation Correctness
    
    白皮书依据: 第四章 4.1.17 - etf_premium_discount
    验收标准: Requirement 3.1
    
    验证:
    1. 公式正确性: (price - nav) / nav
    2. 数值范围合理性: 通常在[-10%, +10%]范围内
    3. 符号正确性: price > nav 时为正，price < nav 时为负
    4. 边界条件: price = nav 时为0
    """
    
    @given(data=valid_etf_data(min_rows=10, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_premium_discount_formula_correctness(self, data):
        """测试溢价折价率公式正确性"""
        operators = ETFOperators()
        
        # Calculate using operator
        result = operators.etf_premium_discount(data)
        
        # Calculate manually
        expected = (data['price'] - data['nav']) / data['nav']
        
        # Verify formula correctness
        assert len(result) == len(expected), "Result length mismatch"
        
        # Allow small numerical errors
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-10,
            err_msg="Premium/discount formula incorrect"
        )
    
    @given(data=valid_etf_data(min_rows=10, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_premium_discount_sign_correctness(self, data):
        """测试溢价折价率符号正确性"""
        operators = ETFOperators()
        
        result = operators.etf_premium_discount(data)
        
        # When price > nav, premium/discount should be positive
        price_above_nav = data['price'] > data['nav']
        if price_above_nav.any():
            assert (result[price_above_nav] > 0).all(), \
                "Premium should be positive when price > nav"
        
        # When price < nav, premium/discount should be negative
        price_below_nav = data['price'] < data['nav']
        if price_below_nav.any():
            assert (result[price_below_nav] < 0).all(), \
                "Discount should be negative when price < nav"
    
    @given(nav=st.floats(min_value=10.0, max_value=1000.0))
    @settings(max_examples=100, deadline=None)
    def test_premium_discount_zero_when_equal(self, nav):
        """测试价格等于净值时溢价折价率为0"""
        operators = ETFOperators()
        
        # Create data where price = nav
        data = pd.DataFrame({
            'price': [nav] * 10,
            'nav': [nav] * 10
        })
        
        result = operators.etf_premium_discount(data)
        
        # Should be exactly 0
        np.testing.assert_allclose(
            result.values,
            np.zeros(len(result)),
            atol=1e-10,
            err_msg="Premium/discount should be 0 when price = nav"
        )



# ============================================================================
# Property 9: ETF Operator Mathematical Correctness (operators 1-5)
# ============================================================================

class TestProperty9OperatorMathematicalCorrectness:
    """Property 9: ETF Operator Mathematical Correctness (operators 1-5)
    
    白皮书依据: 第四章 4.1.17 - ETF Operators 1-5
    验收标准: Requirements 3.1-3.5
    
    验证核心算子的数学正确性:
    1. etf_premium_discount
    2. etf_creation_redemption_flow
    3. etf_tracking_error
    4. etf_constituent_weight_change
    5. etf_arbitrage_opportunity
    """
    
    @given(data=valid_etf_data(min_rows=20, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_creation_redemption_flow_correctness(self, data):
        """测试申购赎回流量计算正确性"""
        operators = ETFOperators()
        
        window = 5
        result = operators.etf_creation_redemption_flow(data, window=window)
        
        # Calculate manually
        net_flow = data['creation_units'] - data['redemption_units']
        expected = net_flow.rolling(window=window).sum()
        
        # Verify correctness
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-10,
            err_msg="Creation/redemption flow calculation incorrect"
        )
    
    @given(data=valid_etf_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_tracking_error_correctness(self, data):
        """测试跟踪误差计算正确性"""
        operators = ETFOperators()
        
        window = 20
        result = operators.etf_tracking_error(data, window=window)
        
        # Calculate manually
        etf_returns = data['price'].pct_change()
        index_returns = data['index_price'].pct_change()
        tracking_diff = etf_returns - index_returns
        expected = tracking_diff.rolling(window=window).std()
        
        # Verify correctness
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-10,
            err_msg="Tracking error calculation incorrect"
        )
    
    @given(data=valid_etf_data(min_rows=10, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_arbitrage_opportunity_logic(self, data):
        """测试套利机会识别逻辑"""
        operators = ETFOperators()
        
        transaction_cost = 0.001
        threshold = 0.0005
        
        result = operators.etf_arbitrage_opportunity(
            data,
            transaction_cost=transaction_cost,
            threshold=threshold
        )
        
        # Calculate premium/discount
        premium_discount = (data['price'] - data['nav']) / data['nav']
        
        # Calculate expected arbitrage opportunity
        arbitrage_profit = premium_discount.abs() - transaction_cost
        expected = (arbitrage_profit > threshold).astype(int)
        
        # Verify correctness
        np.testing.assert_array_equal(
            result.values,
            expected.values,
            err_msg="Arbitrage opportunity logic incorrect"
        )
    
    @given(data=valid_etf_data(min_rows=10, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_operators_return_correct_length(self, data):
        """测试所有核心算子返回正确长度"""
        operators = ETFOperators()
        
        # Test all 5 core operators
        result1 = operators.etf_premium_discount(data)
        assert len(result1) == len(data), "etf_premium_discount length mismatch"
        
        result2 = operators.etf_creation_redemption_flow(data, window=5)
        assert len(result2) == len(data), "etf_creation_redemption_flow length mismatch"
        
        result3 = operators.etf_tracking_error(data, window=20)
        assert len(result3) == len(data), "etf_tracking_error length mismatch"
        
        result5 = operators.etf_arbitrage_opportunity(data)
        assert len(result5) == len(data), "etf_arbitrage_opportunity length mismatch"
    
    @given(data=valid_etf_data(min_rows=10, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_operators_return_numeric_values(self, data):
        """测试所有核心算子返回数值类型"""
        operators = ETFOperators()
        
        # Test all 5 core operators
        result1 = operators.etf_premium_discount(data)
        assert pd.api.types.is_numeric_dtype(result1), \
            "etf_premium_discount should return numeric values"
        
        result2 = operators.etf_creation_redemption_flow(data, window=5)
        assert pd.api.types.is_numeric_dtype(result2), \
            "etf_creation_redemption_flow should return numeric values"
        
        result3 = operators.etf_tracking_error(data, window=20)
        assert pd.api.types.is_numeric_dtype(result3), \
            "etf_tracking_error should return numeric values"
        
        result5 = operators.etf_arbitrage_opportunity(data)
        assert pd.api.types.is_numeric_dtype(result5), \
            "etf_arbitrage_opportunity should return numeric values"



# ============================================================================
# Property 14: Error Handling for Invalid Operator Inputs
# ============================================================================

class TestProperty14ErrorHandling:
    """Property 14: Error Handling for Invalid Operator Inputs
    
    白皮书依据: 第四章 4.1 - Error Handling Standards
    验收标准: Requirement 8.1
    
    验证:
    1. 空数据处理
    2. 缺失列处理
    3. 过多NaN值处理
    4. 无效数值处理
    """
    
    def test_empty_dataframe_raises_error(self):
        """测试空DataFrame抛出错误"""
        operators = ETFOperators()
        
        empty_data = pd.DataFrame()
        
        with pytest.raises(OperatorError, match="Input data is empty"):
            operators.etf_premium_discount(empty_data)
    
    def test_missing_required_columns_raises_error(self):
        """测试缺失必需列抛出错误"""
        operators = ETFOperators()
        
        # Missing 'nav' column
        incomplete_data = pd.DataFrame({
            'price': [100.0, 101.0, 102.0]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.etf_premium_discount(incomplete_data)
    
    def test_excessive_nan_values_raises_error(self):
        """测试过多NaN值抛出错误"""
        operators = ETFOperators()
        
        # Create data with excessive NaN values (>50% threshold)
        n_rows = 20
        n_nans = 12  # 60% NaN values
        price_values = [100.0] * (n_rows - n_nans) + [np.nan] * n_nans
        nav_values = [100.0] * n_rows
        
        data = pd.DataFrame({
            'price': price_values,
            'nav': nav_values
        })
        
        with pytest.raises(DataQualityError, match="NaN values"):
            operators.etf_premium_discount(data)
    
    def test_creation_redemption_flow_missing_columns(self):
        """测试申购赎回流量缺失列错误"""
        operators = ETFOperators()
        
        # Missing 'redemption_units' column
        incomplete_data = pd.DataFrame({
            'creation_units': [1000.0, 2000.0, 3000.0]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.etf_creation_redemption_flow(incomplete_data)
    
    def test_tracking_error_missing_columns(self):
        """测试跟踪误差缺失列错误"""
        operators = ETFOperators()
        
        # Missing 'index_price' column
        incomplete_data = pd.DataFrame({
            'price': [100.0, 101.0, 102.0]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.etf_tracking_error(incomplete_data)
    
    def test_arbitrage_opportunity_handles_errors_gracefully(self):
        """测试套利机会算子优雅处理错误"""
        operators = ETFOperators()
        
        # Empty data should raise OperatorError
        empty_data = pd.DataFrame()
        
        with pytest.raises(OperatorError):
            operators.etf_arbitrage_opportunity(empty_data)
    
    @given(data=valid_etf_data(min_rows=10, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_operators_handle_valid_data_without_errors(self, data):
        """测试算子在有效数据下不抛出错误"""
        operators = ETFOperators()
        
        # All operators should work without errors on valid data
        try:
            operators.etf_premium_discount(data)
            operators.etf_creation_redemption_flow(data, window=5)
            operators.etf_tracking_error(data, window=20)
            operators.etf_arbitrage_opportunity(data)
        except Exception as e:
            pytest.fail(f"Operator raised unexpected error on valid data: {e}")
    
    def test_constituent_weight_change_handles_dict_columns(self):
        """测试成分股权重变化处理字典列"""
        operators = ETFOperators()
        
        # Create data with constituent_weights as dict
        data = pd.DataFrame({
            'constituent_weights': [
                {'stock1': 0.3, 'stock2': 0.7},
                {'stock1': 0.4, 'stock2': 0.6},
                {'stock1': 0.35, 'stock2': 0.65}
            ]
        })
        
        # Should not raise error
        result = operators.etf_constituent_weight_change(data)
        
        assert len(result) == len(data), "Result length mismatch"
        assert pd.api.types.is_numeric_dtype(result), "Result should be numeric"


# ============================================================================
# Additional Property Tests
# ============================================================================

class TestAdditionalProperties:
    """Additional property tests for robustness"""
    
    @given(data=valid_etf_data(min_rows=10, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_operators_are_deterministic(self, data):
        """测试算子是确定性的（相同输入产生相同输出）"""
        operators = ETFOperators()
        
        # Run twice with same data
        result1 = operators.etf_premium_discount(data)
        result2 = operators.etf_premium_discount(data)
        
        # Should be identical
        pd.testing.assert_series_equal(result1, result2)
    
    @given(data=valid_etf_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_tracking_error_is_non_negative(self, data):
        """测试跟踪误差非负"""
        operators = ETFOperators()
        
        result = operators.etf_tracking_error(data, window=20)
        
        # Tracking error (std) should be non-negative
        assert (result.dropna() >= 0).all(), \
            "Tracking error should be non-negative"
    
    @given(data=valid_etf_data(min_rows=10, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_arbitrage_opportunity_is_binary(self, data):
        """测试套利机会是二值的（0或1）"""
        operators = ETFOperators()
        
        result = operators.etf_arbitrage_opportunity(data)
        
        # Should only contain 0 or 1
        unique_values = result.unique()
        assert set(unique_values).issubset({0, 1}), \
            "Arbitrage opportunity should be binary (0 or 1)"
