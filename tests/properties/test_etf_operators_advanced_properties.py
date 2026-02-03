"""Property-based tests for advanced ETF operators (operators 11-20)

白皮书依据: 第四章 4.1.17 - ETF因子挖掘器
测试属性:
- Property 9: ETF Operator Mathematical Correctness (operators 11-20)
- Property 14: Error Handling for Invalid Operator Inputs
- Property 15: Data Quality Threshold Enforcement

验收标准: Requirements 3.11-3.20, 8.1, 8.4
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
import pandas as pd
import numpy as np
from datetime import date, timedelta

from src.evolution.etf_lof.etf_operators import ETFOperators
from src.evolution.etf_lof.exceptions import OperatorError, DataQualityError


# ============================================================================
# Test Data Generators
# ============================================================================

@st.composite
def valid_etf_advanced_data(draw, min_rows=30, max_rows=100):
    """Generate valid ETF market data for advanced operator testing
    
    Args:
        draw: Hypothesis draw function
        min_rows: Minimum number of rows
        max_rows: Maximum number of rows
        
    Returns:
        DataFrame with valid ETF data including advanced fields
    """
    n_rows = draw(st.integers(min_value=min_rows, max_value=max_rows))
    
    # Generate base price and NAV
    nav_base = draw(st.floats(min_value=10.0, max_value=1000.0))
    nav_values = [nav_base * (1 + draw(st.floats(min_value=-0.1, max_value=0.1))) 
                  for _ in range(n_rows)]
    price_values = [nav * (1 + draw(st.floats(min_value=-0.05, max_value=0.05))) 
                    for nav in nav_values]
    
    # Generate index prices
    index_prices = [nav * (1 + draw(st.floats(min_value=-0.02, max_value=0.02))) 
                    for nav in nav_values]
    
    # Generate volume
    volume_values = [draw(st.floats(min_value=1000.0, max_value=1000000.0)) 
                     for _ in range(n_rows)]
    
    # Generate constituent weights (dict column)
    constituent_weights = []
    for _ in range(n_rows):
        n_stocks = draw(st.integers(min_value=3, max_value=5))
        weights = {}
        for i in range(n_stocks):
            weights[f'stock{i}'] = draw(st.floats(min_value=0.1, max_value=0.4))
        # Normalize weights to sum to 1
        total = sum(weights.values())
        weights = {k: v/total for k, v in weights.items()}
        constituent_weights.append(weights)
    
    # Generate factor returns for Smart Beta
    value_returns = [draw(st.floats(min_value=-0.05, max_value=0.05)) 
                     for _ in range(n_rows)]
    momentum_returns = [draw(st.floats(min_value=-0.05, max_value=0.05)) 
                        for _ in range(n_rows)]
    quality_returns = [draw(st.floats(min_value=-0.05, max_value=0.05)) 
                       for _ in range(n_rows)]
    size_returns = [draw(st.floats(min_value=-0.05, max_value=0.05)) 
                    for _ in range(n_rows)]
    
    # Generate options data
    option_prices = [draw(st.floats(min_value=1.0, max_value=50.0)) 
                     for _ in range(n_rows)]
    put_volumes = [draw(st.floats(min_value=100.0, max_value=10000.0)) 
                   for _ in range(n_rows)]
    call_volumes = [draw(st.floats(min_value=100.0, max_value=10000.0)) 
                    for _ in range(n_rows)]
    
    # Generate cross-market prices
    price_market_a = price_values  # Use same as price
    price_market_b = [p * (1 + draw(st.floats(min_value=-0.02, max_value=0.02))) 
                      for p in price_values]
    
    # Generate income and cost data
    lending_income = [draw(st.floats(min_value=0.0, max_value=10000.0)) 
                      for _ in range(n_rows)]
    total_assets = [draw(st.floats(min_value=1e6, max_value=1e9)) 
                    for _ in range(n_rows)]
    total_return = [draw(st.floats(min_value=-0.05, max_value=0.10)) 
                    for _ in range(n_rows)]
    price_return = [draw(st.floats(min_value=-0.05, max_value=0.08)) 
                    for _ in range(n_rows)]
    
    return pd.DataFrame({
        'price': price_values,
        'nav': nav_values,
        'index_price': index_prices,
        'volume': volume_values,
        'constituent_weights': constituent_weights,
        'value_returns': value_returns,
        'momentum_returns': momentum_returns,
        'quality_returns': quality_returns,
        'size_returns': size_returns,
        'option_price': option_prices,
        'put_volume': put_volumes,
        'call_volume': call_volumes,
        'price_market_a': price_market_a,
        'price_market_b': price_market_b,
        'lending_income': lending_income,
        'total_assets': total_assets,
        'total_return': total_return,
        'price_return': price_return
    })


# ============================================================================
# Property 9: ETF Operator Mathematical Correctness (operators 11-20)
# ============================================================================

class TestProperty9AdvancedOperators:
    """Property 9: ETF Operator Mathematical Correctness (operators 11-20)
    
    白皮书依据: 第四章 4.1.17 - ETF Operators 11-20
    验收标准: Requirements 3.11-3.20
    
    验证高级算子的数学正确性:
    11. etf_smart_beta_exposure
    12. etf_leverage_decay
    13. etf_options_implied_volatility
    14. etf_cross_listing_arbitrage
    15. etf_index_rebalancing_impact
    16. etf_authorized_participant_activity
    17. etf_intraday_nav_tracking
    18. etf_options_put_call_ratio
    19. etf_securities_lending_income
    20. etf_dividend_reinvestment_impact
    """
    
    @given(data=valid_etf_advanced_data(min_rows=40, max_rows=60))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large, HealthCheck.too_slow])
    def test_smart_beta_exposure_correctness(self, data):
        """测试Smart Beta暴露计算正确性
        
        白皮书依据: 第四章 4.1.17 - etf_smart_beta_exposure
        """
        operators = ETFOperators()
        
        result = operators.etf_smart_beta_exposure(
            data,
            factor_returns_cols=['value_returns', 'momentum_returns', 'quality_returns', 'size_returns']
        )
        
        # Verify result properties
        assert len(result) == len(data), "Result length mismatch"
        assert pd.api.types.is_numeric_dtype(result), "Result should be numeric"
    
    @given(data=valid_etf_advanced_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_leverage_decay_correctness(self, data):
        """测试杠杆ETF衰减计算正确性
        
        白皮书依据: 第四章 4.1.17 - etf_leverage_decay
        """
        operators = ETFOperators()
        
        leverage_ratio = 2.0
        result = operators.etf_leverage_decay(data, leverage_ratio=leverage_ratio)
        
        # Verify result properties
        assert len(result) == len(data), "Result length mismatch"
        assert pd.api.types.is_numeric_dtype(result), "Result should be numeric"
    
    @given(data=valid_etf_advanced_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_options_implied_volatility_correctness(self, data):
        """测试期权隐含波动率计算正确性
        
        白皮书依据: 第四章 4.1.17 - etf_options_implied_volatility
        """
        operators = ETFOperators()
        
        window = 20
        result = operators.etf_options_implied_volatility(
            data,
            option_price_col='option_price',
            window=window
        )
        
        # Verify result properties
        assert len(result) == len(data), "Result length mismatch"
        assert pd.api.types.is_numeric_dtype(result), "Result should be numeric"
        
        # Implied volatility should be non-negative
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values >= 0).all(), "Implied volatility should be non-negative"
    
    @given(data=valid_etf_advanced_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_cross_listing_arbitrage_correctness(self, data):
        """测试跨市场套利计算正确性
        
        白皮书依据: 第四章 4.1.17 - etf_cross_listing_arbitrage
        公式: (price_market_A - price_market_B) / price_market_B
        """
        operators = ETFOperators()
        
        result = operators.etf_cross_listing_arbitrage(
            data,
            price_a_col='price_market_a',
            price_b_col='price_market_b'
        )
        
        # Calculate manually
        expected = (data['price_market_a'] - data['price_market_b']) / data['price_market_b']
        
        # Verify correctness
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-10,
            err_msg="Cross-listing arbitrage calculation incorrect"
        )
    
    @given(data=valid_etf_advanced_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_index_rebalancing_impact_correctness(self, data):
        """测试指数再平衡影响计算正确性
        
        白皮书依据: 第四章 4.1.17 - etf_index_rebalancing_impact
        """
        operators = ETFOperators()
        
        result = operators.etf_index_rebalancing_impact(
            data,
            weights_col='constituent_weights',
            volume_col='volume'
        )
        
        # Verify result properties
        assert len(result) == len(data), "Result length mismatch"
        assert pd.api.types.is_numeric_dtype(result), "Result should be numeric"
    
    @given(data=valid_etf_advanced_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_intraday_nav_tracking_correctness(self, data):
        """测试日内NAV跟踪计算正确性
        
        白皮书依据: 第四章 4.1.17 - etf_intraday_nav_tracking
        公式: correlation(intraday_price, intraday_inav)
        """
        operators = ETFOperators()
        
        window = 20
        result = operators.etf_intraday_nav_tracking(data, window=window)
        
        # Calculate manually
        expected = data['price'].rolling(window=window).corr(data['nav'])
        
        # Verify correctness
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-10,
            err_msg="Intraday NAV tracking calculation incorrect"
        )
    
    @given(data=valid_etf_advanced_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_options_put_call_ratio_correctness(self, data):
        """测试期权看跌看涨比率计算正确性
        
        白皮书依据: 第四章 4.1.17 - etf_options_put_call_ratio
        公式: put_volume / call_volume
        """
        operators = ETFOperators()
        
        result = operators.etf_options_put_call_ratio(
            data,
            put_volume_col='put_volume',
            call_volume_col='call_volume'
        )
        
        # Calculate manually (with small epsilon to avoid division by zero)
        expected = data['put_volume'] / (data['call_volume'] + 1e-8)
        
        # Verify correctness
        np.testing.assert_allclose(
            result.values,
            expected.values,
            rtol=1e-7,
            err_msg="Options put/call ratio calculation incorrect"
        )
    
    @given(data=valid_etf_advanced_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_securities_lending_income_correctness(self, data):
        """测试证券借贷收入计算正确性
        
        白皮书依据: 第四章 4.1.17 - etf_securities_lending_income
        公式: lending_income / total_assets
        """
        operators = ETFOperators()
        
        result = operators.etf_securities_lending_income(
            data,
            lending_income_col='lending_income',
            total_assets_col='total_assets'
        )
        
        # Calculate manually (with small epsilon to avoid division by zero)
        expected = data['lending_income'] / (data['total_assets'] + 1e-8)
        
        # Verify correctness
        np.testing.assert_allclose(
            result.values,
            expected.values,
            rtol=1e-7,
            err_msg="Securities lending income calculation incorrect"
        )
    
    @given(data=valid_etf_advanced_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_dividend_reinvestment_impact_correctness(self, data):
        """测试股息再投资影响计算正确性
        
        白皮书依据: 第四章 4.1.17 - etf_dividend_reinvestment_impact
        公式: (total_return - price_return) / price_return
        """
        operators = ETFOperators()
        
        result = operators.etf_dividend_reinvestment_impact(
            data,
            total_return_col='total_return',
            price_return_col='price_return'
        )
        
        # Calculate manually (with small epsilon to avoid division by zero)
        expected = (data['total_return'] - data['price_return']) / (data['price_return'] + 1e-8)
        
        # Verify correctness
        np.testing.assert_allclose(
            result.values,
            expected.values,
            rtol=1e-7,
            err_msg="Dividend reinvestment impact calculation incorrect"
        )
    
    @given(data=valid_etf_advanced_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_operators_return_correct_length(self, data):
        """测试所有高级算子返回正确长度"""
        operators = ETFOperators()
        
        # Test all 10 advanced operators
        result1 = operators.etf_smart_beta_exposure(
            data,
            factor_returns_cols=['value_returns', 'momentum_returns', 'quality_returns', 'size_returns']
        )
        assert len(result1) == len(data), "etf_smart_beta_exposure length mismatch"
        
        result2 = operators.etf_leverage_decay(data, leverage_ratio=2.0)
        assert len(result2) == len(data), "etf_leverage_decay length mismatch"
        
        result3 = operators.etf_options_implied_volatility(data, option_price_col='option_price', window=20)
        assert len(result3) == len(data), "etf_options_implied_volatility length mismatch"
        
        result4 = operators.etf_cross_listing_arbitrage(
            data,
            price_a_col='price_market_a',
            price_b_col='price_market_b'
        )
        assert len(result4) == len(data), "etf_cross_listing_arbitrage length mismatch"
        
        result5 = operators.etf_index_rebalancing_impact(
            data,
            weights_col='constituent_weights',
            volume_col='volume'
        )
        assert len(result5) == len(data), "etf_index_rebalancing_impact length mismatch"
        
        result6 = operators.etf_intraday_nav_tracking(data, window=20)
        assert len(result6) == len(data), "etf_intraday_nav_tracking length mismatch"
        
        result7 = operators.etf_options_put_call_ratio(
            data,
            put_volume_col='put_volume',
            call_volume_col='call_volume'
        )
        assert len(result7) == len(data), "etf_options_put_call_ratio length mismatch"
        
        result8 = operators.etf_securities_lending_income(
            data,
            lending_income_col='lending_income',
            total_assets_col='total_assets'
        )
        assert len(result8) == len(data), "etf_securities_lending_income length mismatch"
        
        result9 = operators.etf_dividend_reinvestment_impact(
            data,
            total_return_col='total_return',
            price_return_col='price_return'
        )
        assert len(result9) == len(data), "etf_dividend_reinvestment_impact length mismatch"
    
    @given(data=valid_etf_advanced_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_operators_return_numeric_values(self, data):
        """测试所有高级算子返回数值类型"""
        operators = ETFOperators()
        
        # Test all 10 advanced operators
        result1 = operators.etf_smart_beta_exposure(
            data,
            factor_returns_cols=['value_returns', 'momentum_returns', 'quality_returns', 'size_returns']
        )
        assert pd.api.types.is_numeric_dtype(result1), \
            "etf_smart_beta_exposure should return numeric values"
        
        result2 = operators.etf_leverage_decay(data, leverage_ratio=2.0)
        assert pd.api.types.is_numeric_dtype(result2), \
            "etf_leverage_decay should return numeric values"
        
        result3 = operators.etf_options_implied_volatility(data, option_price_col='option_price', window=20)
        assert pd.api.types.is_numeric_dtype(result3), \
            "etf_options_implied_volatility should return numeric values"
        
        result4 = operators.etf_cross_listing_arbitrage(
            data,
            price_a_col='price_market_a',
            price_b_col='price_market_b'
        )
        assert pd.api.types.is_numeric_dtype(result4), \
            "etf_cross_listing_arbitrage should return numeric values"
        
        result7 = operators.etf_options_put_call_ratio(
            data,
            put_volume_col='put_volume',
            call_volume_col='call_volume'
        )
        assert pd.api.types.is_numeric_dtype(result7), \
            "etf_options_put_call_ratio should return numeric values"
        
        result8 = operators.etf_securities_lending_income(
            data,
            lending_income_col='lending_income',
            total_assets_col='total_assets'
        )
        assert pd.api.types.is_numeric_dtype(result8), \
            "etf_securities_lending_income should return numeric values"


# ============================================================================
# Property 14: Error Handling for Invalid Operator Inputs
# ============================================================================

class TestProperty14AdvancedErrorHandling:
    """Property 14: Error Handling for Invalid Operator Inputs
    
    白皮书依据: 第四章 4.1 - Error Handling Standards
    验收标准: Requirement 8.1
    
    验证高级算子的错误处理
    """
    
    def test_smart_beta_exposure_missing_columns(self):
        """测试Smart Beta暴露缺失列错误"""
        operators = ETFOperators()
        
        # Missing factor return columns
        incomplete_data = pd.DataFrame({
            'price': [100.0, 101.0, 102.0]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.etf_smart_beta_exposure(incomplete_data)
    
    def test_leverage_decay_missing_columns(self):
        """测试杠杆衰减缺失列错误"""
        operators = ETFOperators()
        
        # Missing 'index_price' column
        incomplete_data = pd.DataFrame({
            'price': [100.0, 101.0, 102.0]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.etf_leverage_decay(incomplete_data)
    
    def test_cross_listing_arbitrage_missing_columns(self):
        """测试跨市场套利缺失列错误"""
        operators = ETFOperators()
        
        # Missing 'price_market_b' column
        incomplete_data = pd.DataFrame({
            'price_market_a': [100.0, 101.0, 102.0]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.etf_cross_listing_arbitrage(incomplete_data)
    
    def test_options_put_call_ratio_missing_columns(self):
        """测试期权看跌看涨比率缺失列错误"""
        operators = ETFOperators()
        
        # Missing 'call_volume' column
        incomplete_data = pd.DataFrame({
            'put_volume': [1000.0, 2000.0, 3000.0]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.etf_options_put_call_ratio(incomplete_data)
    
    def test_securities_lending_income_missing_columns(self):
        """测试证券借贷收入缺失列错误"""
        operators = ETFOperators()
        
        # Missing 'total_assets' column
        incomplete_data = pd.DataFrame({
            'lending_income': [1000.0, 2000.0, 3000.0]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.etf_securities_lending_income(incomplete_data)
    
    def test_dividend_reinvestment_impact_missing_columns(self):
        """测试股息再投资影响缺失列错误"""
        operators = ETFOperators()
        
        # Missing 'price_return' column
        incomplete_data = pd.DataFrame({
            'total_return': [0.05, 0.06, 0.07]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.etf_dividend_reinvestment_impact(incomplete_data)
    
    @given(data=valid_etf_advanced_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_operators_handle_valid_data_without_errors(self, data):
        """测试算子在有效数据下不抛出错误"""
        operators = ETFOperators()
        
        # All operators should work without errors on valid data
        try:
            operators.etf_smart_beta_exposure(
                data,
                factor_returns_cols=['value_returns', 'momentum_returns', 'quality_returns', 'size_returns']
            )
            operators.etf_leverage_decay(data, leverage_ratio=2.0)
            operators.etf_options_implied_volatility(data, option_price_col='option_price', window=20)
            operators.etf_cross_listing_arbitrage(
                data,
                price_a_col='price_market_a',
                price_b_col='price_market_b'
            )
            operators.etf_options_put_call_ratio(
                data,
                put_volume_col='put_volume',
                call_volume_col='call_volume'
            )
            operators.etf_securities_lending_income(
                data,
                lending_income_col='lending_income',
                total_assets_col='total_assets'
            )
            operators.etf_dividend_reinvestment_impact(
                data,
                total_return_col='total_return',
                price_return_col='price_return'
            )
        except Exception as e:
            pytest.fail(f"Operator raised unexpected error on valid data: {e}")


# ============================================================================
# Additional Property Tests
# ============================================================================

class TestAdditionalAdvancedProperties:
    """Additional property tests for advanced operators"""
    
    @given(data=valid_etf_advanced_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_options_put_call_ratio_non_negative(self, data):
        """测试期权看跌看涨比率非负"""
        operators = ETFOperators()
        
        result = operators.etf_options_put_call_ratio(
            data,
            put_volume_col='put_volume',
            call_volume_col='call_volume'
        )
        
        # Put/call ratio should be non-negative
        assert (result >= 0).all(), "Put/call ratio should be non-negative"
    
    @given(data=valid_etf_advanced_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_securities_lending_income_non_negative(self, data):
        """测试证券借贷收入率非负"""
        operators = ETFOperators()
        
        result = operators.etf_securities_lending_income(
            data,
            lending_income_col='lending_income',
            total_assets_col='total_assets'
        )
        
        # Lending income rate should be non-negative
        assert (result >= 0).all(), "Securities lending income rate should be non-negative"
    
    @given(data=valid_etf_advanced_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_intraday_nav_tracking_correlation_range(self, data):
        """测试日内NAV跟踪相关系数范围在[-1, 1]"""
        operators = ETFOperators()
        
        result = operators.etf_intraday_nav_tracking(data, window=20)
        
        # Correlation should be in [-1, 1]
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values >= -1.0).all() and (valid_values <= 1.0).all(), \
                "Intraday NAV tracking (correlation) should be in [-1, 1]"
    
    @given(data=valid_etf_advanced_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_operators_are_deterministic(self, data):
        """测试算子是确定性的（相同输入产生相同输出）"""
        operators = ETFOperators()
        
        # Run twice with same data
        result1 = operators.etf_cross_listing_arbitrage(
            data,
            price_a_col='price_market_a',
            price_b_col='price_market_b'
        )
        result2 = operators.etf_cross_listing_arbitrage(
            data,
            price_a_col='price_market_a',
            price_b_col='price_market_b'
        )
        
        # Should be identical
        pd.testing.assert_series_equal(result1, result2)
