"""Property-based tests for liquidity and flow ETF operators (operators 6-10)

白皮书依据: 第四章 4.1.17 - ETF因子挖掘器
测试属性:
- Property 9: ETF Operator Mathematical Correctness (operators 6-10)
- Property 14: Error Handling for Invalid Operator Inputs

验收标准: Requirements 3.6-3.10, 8.1
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
def valid_etf_liquidity_data(draw, min_rows=30, max_rows=100):
    """Generate valid ETF market data for liquidity and flow testing
    
    Args:
        draw: Hypothesis draw function
        min_rows: Minimum number of rows
        max_rows: Maximum number of rows
        
    Returns:
        DataFrame with valid ETF data including liquidity fields
    """
    n_rows = draw(st.integers(min_value=min_rows, max_value=max_rows))
    
    # Generate base NAV values (positive)
    nav_base = draw(st.floats(min_value=10.0, max_value=1000.0))
    nav_values = [nav_base * (1 + draw(st.floats(min_value=-0.1, max_value=0.1))) 
                  for _ in range(n_rows)]
    
    # Generate prices with some premium/discount
    price_values = [nav * (1 + draw(st.floats(min_value=-0.05, max_value=0.05))) 
                    for nav in nav_values]
    
    # Generate bid/ask prices
    bid_prices = [p * (1 - draw(st.floats(min_value=0.0001, max_value=0.01))) 
                  for p in price_values]
    ask_prices = [p * (1 + draw(st.floats(min_value=0.0001, max_value=0.01))) 
                  for p in price_values]
    
    # Generate AUM (Assets Under Management)
    aum_base = draw(st.floats(min_value=1e6, max_value=1e9))
    aum_values = [aum_base * (1 + draw(st.floats(min_value=-0.05, max_value=0.05))) 
                  for _ in range(n_rows)]
    
    # Generate sector flow and returns
    sector_flow_values = [draw(st.floats(min_value=-1e6, max_value=1e6)) 
                          for _ in range(n_rows)]
    sector_returns_values = [draw(st.floats(min_value=-0.05, max_value=0.05)) 
                             for _ in range(n_rows)]
    
    return pd.DataFrame({
        'price': price_values,
        'nav': nav_values,
        'bid_price': bid_prices,
        'ask_price': ask_prices,
        'aum': aum_values,
        'sector_flow': sector_flow_values,
        'sector_returns': sector_returns_values
    })


# ============================================================================
# Property 9: ETF Operator Mathematical Correctness (operators 6-10)
# ============================================================================

class TestProperty9LiquidityFlowOperators:
    """Property 9: ETF Operator Mathematical Correctness (operators 6-10)
    
    白皮书依据: 第四章 4.1.17 - ETF Operators 6-10
    验收标准: Requirements 3.6-3.10
    
    验证流动性和资金流算子的数学正确性:
    6. etf_liquidity_premium
    7. etf_fund_flow
    8. etf_bid_ask_spread_dynamics
    9. etf_nav_convergence_speed
    10. etf_sector_rotation_signal
    """
    
    @given(data=valid_etf_liquidity_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_liquidity_premium_correctness(self, data):
        """测试流动性溢价计算正确性
        
        白皮书依据: 第四章 4.1.17 - etf_liquidity_premium
        公式: correlation(bid_ask_spread, premium_discount)
        """
        operators = ETFOperators()
        
        window = 20
        result = operators.etf_liquidity_premium(data, window=window)
        
        # Calculate manually
        bid_ask_spread = (data['ask_price'] - data['bid_price']) / data['price']
        premium_discount = (data['price'] - data['nav']) / data['nav']
        expected = bid_ask_spread.rolling(window=window).corr(premium_discount)
        
        # Verify correctness
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-10,
            err_msg="Liquidity premium calculation incorrect"
        )
    
    @given(data=valid_etf_liquidity_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_fund_flow_correctness(self, data):
        """测试基金流量计算正确性
        
        白皮书依据: 第四章 4.1.17 - etf_fund_flow
        公式: (AUM_today - AUM_yesterday) / AUM_yesterday
        """
        operators = ETFOperators()
        
        result = operators.etf_fund_flow(data, aum_col='aum')
        
        # Calculate manually
        expected = data['aum'].pct_change()
        
        # Verify correctness
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-10,
            err_msg="Fund flow calculation incorrect"
        )
    
    @given(data=valid_etf_liquidity_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_bid_ask_spread_dynamics_correctness(self, data):
        """测试买卖价差动态计算正确性
        
        白皮书依据: 第四章 4.1.17 - etf_bid_ask_spread_dynamics
        公式: rolling_std(bid_ask_spread, window) / rolling_mean(bid_ask_spread, window)
        """
        operators = ETFOperators()
        
        window = 20
        result = operators.etf_bid_ask_spread_dynamics(data, window=window)
        
        # Calculate manually
        bid_ask_spread = (data['ask_price'] - data['bid_price']) / data['price']
        spread_std = bid_ask_spread.rolling(window=window).std()
        spread_mean = bid_ask_spread.rolling(window=window).mean()
        expected = spread_std / spread_mean
        
        # Verify correctness
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-10,
            err_msg="Bid-ask spread dynamics calculation incorrect"
        )
    
    @given(data=valid_etf_liquidity_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_nav_convergence_speed_correctness(self, data):
        """测试NAV收敛速度计算正确性
        
        白皮书依据: 第四章 4.1.17 - etf_nav_convergence_speed
        公式: rolling_regression(premium_discount, time).slope
        """
        operators = ETFOperators()
        
        window = 20
        result = operators.etf_nav_convergence_speed(data, window=window)
        
        # Verify result properties
        assert len(result) == len(data), "Result length mismatch"
        assert pd.api.types.is_numeric_dtype(result), "Result should be numeric"
        
        # Verify first window-1 values are NaN
        assert result.iloc[:window-1].isna().all(), \
            f"First {window-1} values should be NaN"
    
    @given(data=valid_etf_liquidity_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_sector_rotation_signal_correctness(self, data):
        """测试板块轮动信号计算正确性
        
        白皮书依据: 第四章 4.1.17 - etf_sector_rotation_signal
        公式: correlation(sector_etf_flows, sector_returns)
        """
        operators = ETFOperators()
        
        window = 20
        result = operators.etf_sector_rotation_signal(
            data,
            sector_flow_col='sector_flow',
            sector_returns_col='sector_returns',
            window=window
        )
        
        # Calculate manually
        expected = data['sector_flow'].rolling(window=window).corr(data['sector_returns'])
        
        # Verify correctness
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-10,
            err_msg="Sector rotation signal calculation incorrect"
        )
    
    @given(data=valid_etf_liquidity_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_operators_return_correct_length(self, data):
        """测试所有流动性和资金流算子返回正确长度"""
        operators = ETFOperators()
        
        # Test all 5 liquidity/flow operators
        result1 = operators.etf_liquidity_premium(data, window=20)
        assert len(result1) == len(data), "etf_liquidity_premium length mismatch"
        
        result2 = operators.etf_fund_flow(data, aum_col='aum')
        assert len(result2) == len(data), "etf_fund_flow length mismatch"
        
        result3 = operators.etf_bid_ask_spread_dynamics(data, window=20)
        assert len(result3) == len(data), "etf_bid_ask_spread_dynamics length mismatch"
        
        result4 = operators.etf_nav_convergence_speed(data, window=20)
        assert len(result4) == len(data), "etf_nav_convergence_speed length mismatch"
        
        result5 = operators.etf_sector_rotation_signal(
            data,
            sector_flow_col='sector_flow',
            sector_returns_col='sector_returns',
            window=20
        )
        assert len(result5) == len(data), "etf_sector_rotation_signal length mismatch"
    
    @given(data=valid_etf_liquidity_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_operators_return_numeric_values(self, data):
        """测试所有流动性和资金流算子返回数值类型"""
        operators = ETFOperators()
        
        # Test all 5 liquidity/flow operators
        result1 = operators.etf_liquidity_premium(data, window=20)
        assert pd.api.types.is_numeric_dtype(result1), \
            "etf_liquidity_premium should return numeric values"
        
        result2 = operators.etf_fund_flow(data, aum_col='aum')
        assert pd.api.types.is_numeric_dtype(result2), \
            "etf_fund_flow should return numeric values"
        
        result3 = operators.etf_bid_ask_spread_dynamics(data, window=20)
        assert pd.api.types.is_numeric_dtype(result3), \
            "etf_bid_ask_spread_dynamics should return numeric values"
        
        result4 = operators.etf_nav_convergence_speed(data, window=20)
        assert pd.api.types.is_numeric_dtype(result4), \
            "etf_nav_convergence_speed should return numeric values"
        
        result5 = operators.etf_sector_rotation_signal(
            data,
            sector_flow_col='sector_flow',
            sector_returns_col='sector_returns',
            window=20
        )
        assert pd.api.types.is_numeric_dtype(result5), \
            "etf_sector_rotation_signal should return numeric values"


# ============================================================================
# Property 14: Error Handling for Invalid Operator Inputs
# ============================================================================

class TestProperty14LiquidityFlowErrorHandling:
    """Property 14: Error Handling for Invalid Operator Inputs
    
    白皮书依据: 第四章 4.1 - Error Handling Standards
    验收标准: Requirement 8.1
    
    验证流动性和资金流算子的错误处理:
    1. 空数据处理
    2. 缺失列处理
    3. 过多NaN值处理
    4. 无效数值处理
    """
    
    def test_liquidity_premium_missing_columns(self):
        """测试流动性溢价缺失列错误"""
        operators = ETFOperators()
        
        # Missing 'bid_price' column
        incomplete_data = pd.DataFrame({
            'price': [100.0, 101.0, 102.0],
            'nav': [100.0, 101.0, 102.0],
            'ask_price': [100.5, 101.5, 102.5]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.etf_liquidity_premium(incomplete_data)
    
    def test_fund_flow_missing_columns(self):
        """测试基金流量缺失列错误"""
        operators = ETFOperators()
        
        # Missing 'aum' column
        incomplete_data = pd.DataFrame({
            'price': [100.0, 101.0, 102.0]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.etf_fund_flow(incomplete_data, aum_col='aum')
    
    def test_bid_ask_spread_dynamics_missing_columns(self):
        """测试买卖价差动态缺失列错误"""
        operators = ETFOperators()
        
        # Missing 'ask_price' column
        incomplete_data = pd.DataFrame({
            'price': [100.0, 101.0, 102.0],
            'bid_price': [99.5, 100.5, 101.5]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.etf_bid_ask_spread_dynamics(incomplete_data)
    
    def test_nav_convergence_speed_missing_columns(self):
        """测试NAV收敛速度缺失列错误"""
        operators = ETFOperators()
        
        # Missing 'nav' column
        incomplete_data = pd.DataFrame({
            'price': [100.0, 101.0, 102.0]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.etf_nav_convergence_speed(incomplete_data)
    
    def test_sector_rotation_signal_missing_columns(self):
        """测试板块轮动信号缺失列错误"""
        operators = ETFOperators()
        
        # Missing 'sector_returns' column
        incomplete_data = pd.DataFrame({
            'sector_flow': [1000.0, 2000.0, 3000.0]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.etf_sector_rotation_signal(incomplete_data)
    
    def test_empty_dataframe_raises_error(self):
        """测试空DataFrame抛出错误"""
        operators = ETFOperators()
        
        empty_data = pd.DataFrame()
        
        with pytest.raises(OperatorError, match="Input data is empty"):
            operators.etf_liquidity_premium(empty_data)
        
        with pytest.raises(OperatorError, match="Input data is empty"):
            operators.etf_fund_flow(empty_data)
        
        with pytest.raises(OperatorError, match="Input data is empty"):
            operators.etf_bid_ask_spread_dynamics(empty_data)
    
    @given(data=valid_etf_liquidity_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_operators_handle_valid_data_without_errors(self, data):
        """测试算子在有效数据下不抛出错误"""
        operators = ETFOperators()
        
        # All operators should work without errors on valid data
        try:
            operators.etf_liquidity_premium(data, window=20)
            operators.etf_fund_flow(data, aum_col='aum')
            operators.etf_bid_ask_spread_dynamics(data, window=20)
            operators.etf_nav_convergence_speed(data, window=20)
            operators.etf_sector_rotation_signal(
                data,
                sector_flow_col='sector_flow',
                sector_returns_col='sector_returns',
                window=20
            )
        except Exception as e:
            pytest.fail(f"Operator raised unexpected error on valid data: {e}")


# ============================================================================
# Additional Property Tests
# ============================================================================

class TestAdditionalLiquidityFlowProperties:
    """Additional property tests for liquidity and flow operators"""
    
    @given(data=valid_etf_liquidity_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_liquidity_premium_correlation_range(self, data):
        """测试流动性溢价相关系数范围在[-1, 1]"""
        operators = ETFOperators()
        
        result = operators.etf_liquidity_premium(data, window=20)
        
        # Correlation should be in [-1, 1]
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values >= -1.0).all() and (valid_values <= 1.0).all(), \
                "Liquidity premium (correlation) should be in [-1, 1]"
    
    @given(data=valid_etf_liquidity_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_bid_ask_spread_dynamics_non_negative(self, data):
        """测试买卖价差动态非负（变异系数）"""
        operators = ETFOperators()
        
        result = operators.etf_bid_ask_spread_dynamics(data, window=20)
        
        # Coefficient of variation should be non-negative
        valid_values = result.dropna()
        # Filter out inf values (can occur when mean is very close to 0)
        valid_values = valid_values[~np.isinf(valid_values)]
        
        if len(valid_values) > 0:
            assert (valid_values >= 0).all(), \
                "Bid-ask spread dynamics (CV) should be non-negative"
    
    @given(data=valid_etf_liquidity_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_sector_rotation_signal_correlation_range(self, data):
        """测试板块轮动信号相关系数范围在[-1, 1]"""
        operators = ETFOperators()
        
        result = operators.etf_sector_rotation_signal(
            data,
            sector_flow_col='sector_flow',
            sector_returns_col='sector_returns',
            window=20
        )
        
        # Correlation should be in [-1, 1]
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values >= -1.0).all() and (valid_values <= 1.0).all(), \
                "Sector rotation signal (correlation) should be in [-1, 1]"
    
    @given(data=valid_etf_liquidity_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None)
    def test_operators_are_deterministic(self, data):
        """测试算子是确定性的（相同输入产生相同输出）"""
        operators = ETFOperators()
        
        # Run twice with same data
        result1 = operators.etf_fund_flow(data, aum_col='aum')
        result2 = operators.etf_fund_flow(data, aum_col='aum')
        
        # Should be identical
        pd.testing.assert_series_equal(result1, result2)
