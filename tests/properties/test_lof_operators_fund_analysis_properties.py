"""Property-based tests for fund analysis LOF operators (operators 6-10)

白皮书依据: 第四章 4.1.18 - LOF基金因子挖掘器
测试属性:
- Property 10: LOF Operator Mathematical Correctness (operators 6-10)
- Property 14: Error Handling for Invalid Operator Inputs

验收标准: Requirements 4.6-4.10, 8.1, 8.2
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
import pandas as pd
import numpy as np
from datetime import date, timedelta

from src.evolution.etf_lof.lof_operators import LOFOperators
from src.evolution.etf_lof.exceptions import OperatorError, DataQualityError


# ============================================================================
# Test Data Generators
# ============================================================================

@st.composite
def valid_fund_analysis_data(draw, min_rows=30, max_rows=100):
    """Generate valid LOF fund analysis data for testing
    
    Args:
        draw: Hypothesis draw function
        min_rows: Minimum number of rows
        max_rows: Maximum number of rows
        
    Returns:
        DataFrame with valid LOF fund analysis data
    """
    n_rows = draw(st.integers(min_value=min_rows, max_value=max_rows))
    
    # Generate onmarket volume
    onmarket_volume = [draw(st.floats(min_value=10000.0, max_value=1000000.0)) 
                       for _ in range(n_rows)]
    
    # Generate redemption amount
    redemption_amount = [draw(st.floats(min_value=5000.0, max_value=500000.0)) 
                         for _ in range(n_rows)]
    
    # Generate institutional and retail holdings
    institutional_holding = [draw(st.floats(min_value=10.0, max_value=90.0)) 
                            for _ in range(n_rows)]
    retail_holding = [100.0 - inst for inst in institutional_holding]
    
    # Generate returns and benchmark returns
    returns = [draw(st.floats(min_value=-0.05, max_value=0.05)) 
              for _ in range(n_rows)]
    benchmark_returns = [draw(st.floats(min_value=-0.04, max_value=0.04)) 
                        for _ in range(n_rows)]
    
    # Generate holdings (dictionary type)
    holdings = []
    for _ in range(n_rows):
        n_stocks = draw(st.integers(min_value=3, max_value=10))
        weights = [draw(st.floats(min_value=0.05, max_value=0.4)) 
                  for _ in range(n_stocks)]
        # Normalize weights to sum to 1.0
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        holdings_dict = {f'stock{i}': normalized_weights[i] 
                        for i in range(n_stocks)}
        holdings.append(holdings_dict)
    
    return pd.DataFrame({
        'onmarket_volume': onmarket_volume,
        'redemption_amount': redemption_amount,
        'institutional_holding': institutional_holding,
        'retail_holding': retail_holding,
        'returns': returns,
        'benchmark_returns': benchmark_returns,
        'holdings': holdings
    })


# ============================================================================
# Property 10: LOF Operator Mathematical Correctness (operators 6-10)
# ============================================================================

class TestProperty10FundAnalysisCorrectness:
    """Property 10: LOF Operator Mathematical Correctness (operators 6-10)
    
    白皮书依据: 第四章 4.1.18 - LOF Operators 6-10
    验收标准: Requirements 4.6-4.10
    
    验证LOF基金分析算子的数学正确性
    """
    
    @given(data=valid_fund_analysis_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_liquidity_stratification_correctness(self, data):
        """测试流动性分层计算正确性
        
        白皮书依据: 第四章 4.1.18 - lof_liquidity_stratification
        公式: onmarket_liquidity / offmarket_liquidity
        """
        operators = LOFOperators()
        
        window = 10
        result = operators.lof_liquidity_stratification(data, window=window)
        
        # Calculate manually
        onmarket_liq = data['onmarket_volume'].rolling(window=window).mean()
        offmarket_liq = data['redemption_amount'].rolling(window=window).mean()
        expected = onmarket_liq / (offmarket_liq + 1e-8)
        
        # Verify correctness
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-6,
            err_msg="Liquidity stratification calculation incorrect"
        )
    
    @given(data=valid_fund_analysis_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_investor_structure_correctness(self, data):
        """测试投资者结构计算正确性
        
        白皮书依据: 第四章 4.1.18 - lof_investor_structure
        公式: institutional_holding / (institutional_holding + retail_holding)
        """
        operators = LOFOperators()
        
        result = operators.lof_investor_structure(data)
        
        # Calculate manually
        total = data['institutional_holding'] + data['retail_holding']
        expected = data['institutional_holding'] / (total + 1e-8)
        
        # Verify correctness
        np.testing.assert_allclose(
            result.values,
            expected.values,
            rtol=1e-10,
            err_msg="Investor structure calculation incorrect"
        )
    
    @given(data=valid_fund_analysis_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_investor_structure_range(self, data):
        """测试投资者结构在[0, 1]范围内"""
        operators = LOFOperators()
        
        result = operators.lof_investor_structure(data)
        
        # Should be in [0, 1] range
        assert (result >= 0).all(), "Investor structure should be >= 0"
        assert (result <= 1).all(), "Investor structure should be <= 1"
    
    @given(data=valid_fund_analysis_data(min_rows=60, max_rows=100))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_fund_manager_alpha_correctness(self, data):
        """测试基金经理Alpha计算正确性
        
        白皮书依据: 第四章 4.1.18 - lof_fund_manager_alpha
        公式: rolling_mean(returns - benchmark_returns)
        """
        operators = LOFOperators()
        
        window = 30
        result = operators.lof_fund_manager_alpha(data, window=window)
        
        # Calculate manually
        excess_returns = data['returns'] - data['benchmark_returns']
        expected = excess_returns.rolling(window=window).mean()
        
        # Verify correctness
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-10,
            err_msg="Fund manager alpha calculation incorrect"
        )
    
    @given(data=valid_fund_analysis_data(min_rows=60, max_rows=100))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_fund_manager_style_correctness(self, data):
        """测试基金经理风格计算正确性
        
        白皮书依据: 第四章 4.1.18 - lof_fund_manager_style
        公式: pct_change(holding_concentration, window)
        """
        operators = LOFOperators()
        
        window = 20
        result = operators.lof_fund_manager_style(data, window=window)
        
        # Calculate manually
        concentration = operators.lof_holding_concentration(data)
        expected = concentration.pct_change(periods=window)
        
        # Verify correctness
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-10,
            err_msg="Fund manager style calculation incorrect"
        )
    
    @given(data=valid_fund_analysis_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_holding_concentration_correctness(self, data):
        """测试持仓集中度计算正确性
        
        白皮书依据: 第四章 4.1.18 - lof_holding_concentration
        公式: HHI = sum(weight^2)
        """
        operators = LOFOperators()
        
        result = operators.lof_holding_concentration(data)
        
        # Calculate manually for each row
        for i in range(len(data)):
            holdings_dict = data['holdings'].iloc[i]
            if isinstance(holdings_dict, dict) and len(holdings_dict) > 0:
                expected_hhi = sum(w ** 2 for w in holdings_dict.values())
                np.testing.assert_allclose(
                    result.iloc[i],
                    expected_hhi,
                    rtol=1e-10,
                    err_msg=f"HHI calculation incorrect at index {i}"
                )
    
    @given(data=valid_fund_analysis_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_holding_concentration_range(self, data):
        """测试持仓集中度在合理范围内
        
        HHI范围: [1/n, 1]，其中n是持仓数量
        """
        operators = LOFOperators()
        
        result = operators.lof_holding_concentration(data)
        
        # HHI should be in (0, 1] range
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values > 0).all(), "HHI should be > 0"
            assert (valid_values <= 1).all(), "HHI should be <= 1"
    
    @given(data=valid_fund_analysis_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_operators_return_correct_length(self, data):
        """测试所有基金分析算子返回正确长度"""
        operators = LOFOperators()
        
        # Test all 5 fund analysis operators
        result1 = operators.lof_liquidity_stratification(data, window=10)
        assert len(result1) == len(data), "lof_liquidity_stratification length mismatch"
        
        result2 = operators.lof_investor_structure(data)
        assert len(result2) == len(data), "lof_investor_structure length mismatch"
        
        result3 = operators.lof_fund_manager_alpha(data, window=20)
        assert len(result3) == len(data), "lof_fund_manager_alpha length mismatch"
        
        result4 = operators.lof_fund_manager_style(data, window=10)
        assert len(result4) == len(data), "lof_fund_manager_style length mismatch"
        
        result5 = operators.lof_holding_concentration(data)
        assert len(result5) == len(data), "lof_holding_concentration length mismatch"
    
    @given(data=valid_fund_analysis_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_operators_return_numeric_values(self, data):
        """测试所有基金分析算子返回数值类型"""
        operators = LOFOperators()
        
        # Test all 5 fund analysis operators
        result1 = operators.lof_liquidity_stratification(data, window=10)
        assert pd.api.types.is_numeric_dtype(result1), \
            "lof_liquidity_stratification should return numeric values"
        
        result2 = operators.lof_investor_structure(data)
        assert pd.api.types.is_numeric_dtype(result2), \
            "lof_investor_structure should return numeric values"
        
        result3 = operators.lof_fund_manager_alpha(data, window=20)
        assert pd.api.types.is_numeric_dtype(result3), \
            "lof_fund_manager_alpha should return numeric values"
        
        result4 = operators.lof_fund_manager_style(data, window=10)
        assert pd.api.types.is_numeric_dtype(result4), \
            "lof_fund_manager_style should return numeric values"
        
        result5 = operators.lof_holding_concentration(data)
        assert pd.api.types.is_numeric_dtype(result5), \
            "lof_holding_concentration should return numeric values"


# ============================================================================
# Property 14: Error Handling for Invalid Operator Inputs
# ============================================================================

class TestProperty14ErrorHandling:
    """Property 14: Error Handling for Invalid Operator Inputs
    
    白皮书依据: 第四章 4.1 - Error Handling Standards
    验收标准: Requirement 8.1
    
    验证LOF基金分析算子的错误处理
    """
    
    def test_liquidity_stratification_empty_data(self):
        """测试流动性分层空数据错误"""
        operators = LOFOperators()
        
        empty_data = pd.DataFrame()
        
        with pytest.raises(OperatorError, match="Input data is empty"):
            operators.lof_liquidity_stratification(empty_data)
    
    def test_liquidity_stratification_missing_columns(self):
        """测试流动性分层缺失列错误"""
        operators = LOFOperators()
        
        # Missing 'redemption_amount' column
        incomplete_data = pd.DataFrame({
            'onmarket_volume': [100000, 120000, 110000]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.lof_liquidity_stratification(incomplete_data)
    
    def test_investor_structure_empty_data(self):
        """测试投资者结构空数据错误"""
        operators = LOFOperators()
        
        empty_data = pd.DataFrame()
        
        with pytest.raises(OperatorError, match="Input data is empty"):
            operators.lof_investor_structure(empty_data)
    
    def test_investor_structure_missing_columns(self):
        """测试投资者结构缺失列错误"""
        operators = LOFOperators()
        
        # Missing 'retail_holding' column
        incomplete_data = pd.DataFrame({
            'institutional_holding': [60, 65, 70]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.lof_investor_structure(incomplete_data)
    
    def test_fund_manager_alpha_empty_data(self):
        """测试基金经理Alpha空数据错误"""
        operators = LOFOperators()
        
        empty_data = pd.DataFrame()
        
        with pytest.raises(OperatorError, match="Input data is empty"):
            operators.lof_fund_manager_alpha(empty_data)
    
    def test_fund_manager_alpha_missing_columns(self):
        """测试基金经理Alpha缺失列错误"""
        operators = LOFOperators()
        
        # Missing 'benchmark_returns' column
        incomplete_data = pd.DataFrame({
            'returns': [0.01, 0.02, 0.015]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.lof_fund_manager_alpha(incomplete_data)
    
    def test_fund_manager_style_empty_data(self):
        """测试基金经理风格空数据错误"""
        operators = LOFOperators()
        
        empty_data = pd.DataFrame()
        
        with pytest.raises(OperatorError, match="Input data is empty"):
            operators.lof_fund_manager_style(empty_data)
    
    def test_fund_manager_style_missing_columns(self):
        """测试基金经理风格缺失列错误"""
        operators = LOFOperators()
        
        # Missing 'holdings' column
        incomplete_data = pd.DataFrame({
            'returns': [0.01, 0.02, 0.015]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.lof_fund_manager_style(incomplete_data)
    
    def test_holding_concentration_empty_data(self):
        """测试持仓集中度空数据错误"""
        operators = LOFOperators()
        
        empty_data = pd.DataFrame()
        
        with pytest.raises(OperatorError, match="Input data is empty"):
            operators.lof_holding_concentration(empty_data)
    
    def test_holding_concentration_missing_columns(self):
        """测试持仓集中度缺失列错误"""
        operators = LOFOperators()
        
        # Missing 'holdings' column
        incomplete_data = pd.DataFrame({
            'returns': [0.01, 0.02, 0.015]
        })
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.lof_holding_concentration(incomplete_data)
    
    def test_invalid_window_parameter(self):
        """测试无效window参数"""
        operators = LOFOperators()
        
        data = pd.DataFrame({
            'onmarket_volume': [100000, 120000, 110000],
            'redemption_amount': [50000, 60000, 55000]
        })
        
        with pytest.raises(ValueError, match="window must be > 0"):
            operators.lof_liquidity_stratification(data, window=0)
        
        with pytest.raises(ValueError, match="window must be > 0"):
            operators.lof_liquidity_stratification(data, window=-5)
    
    def test_excessive_nan_values_raises_error(self):
        """测试过多NaN值抛出错误"""
        operators = LOFOperators()
        
        # Create data with >20% NaN values
        data_with_nans = pd.DataFrame({
            'onmarket_volume': [100000, np.nan, np.nan, 130000, 115000],
            'redemption_amount': [50000, 60000, 55000, 70000, 58000]
        })
        
        with pytest.raises(DataQualityError, match="too many NaN values"):
            operators.lof_liquidity_stratification(data_with_nans, window=3)
    
    @given(data=valid_fund_analysis_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_operators_handle_valid_data_without_errors(self, data):
        """测试算子在有效数据下不抛出错误"""
        operators = LOFOperators()
        
        # All operators should work without errors on valid data
        try:
            operators.lof_liquidity_stratification(data, window=10)
            operators.lof_investor_structure(data)
            operators.lof_fund_manager_alpha(data, window=20)
            operators.lof_fund_manager_style(data, window=10)
            operators.lof_holding_concentration(data)
        except Exception as e:
            pytest.fail(f"Operator raised unexpected error on valid data: {e}")


# ============================================================================
# Additional Property Tests
# ============================================================================

class TestAdditionalProperties:
    """Additional property tests for fund analysis LOF operators"""
    
    @given(data=valid_fund_analysis_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_operators_are_deterministic(self, data):
        """测试算子是确定性的（相同输入产生相同输出）"""
        operators = LOFOperators()
        
        # Run twice with same data
        result1 = operators.lof_investor_structure(data)
        result2 = operators.lof_investor_structure(data)
        
        # Should be identical
        pd.testing.assert_series_equal(result1, result2)
    
    @given(data=valid_fund_analysis_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_liquidity_stratification_is_positive(self, data):
        """测试流动性分层指标为正值"""
        operators = LOFOperators()
        
        result = operators.lof_liquidity_stratification(data, window=10)
        
        # Should be positive (ratio of two positive values)
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values > 0).all(), "Liquidity stratification should be positive"
    
    @given(data=valid_fund_analysis_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_holding_concentration_increases_with_fewer_holdings(self, data):
        """测试持仓集中度随持仓数量减少而增加
        
        HHI性质: 持仓越集中，HHI越大
        """
        operators = LOFOperators()
        
        # Create two scenarios: concentrated vs diversified
        concentrated_data = pd.DataFrame({
            'holdings': [
                {'stock1': 0.8, 'stock2': 0.2},  # Very concentrated
                {'stock1': 0.7, 'stock2': 0.3}
            ]
        })
        
        diversified_data = pd.DataFrame({
            'holdings': [
                {'stock1': 0.25, 'stock2': 0.25, 'stock3': 0.25, 'stock4': 0.25},  # Diversified
                {'stock1': 0.2, 'stock2': 0.2, 'stock3': 0.2, 'stock4': 0.2, 'stock5': 0.2}
            ]
        })
        
        concentrated_hhi = operators.lof_holding_concentration(concentrated_data)
        diversified_hhi = operators.lof_holding_concentration(diversified_data)
        
        # Concentrated portfolio should have higher HHI
        assert concentrated_hhi.mean() > diversified_hhi.mean(), \
            "Concentrated portfolio should have higher HHI"
    
    @given(data=valid_fund_analysis_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_hhi_equals_one_for_single_holding(self, data):
        """测试单一持仓的HHI等于1"""
        operators = LOFOperators()
        
        # Create data with single holding (100% weight)
        single_holding_data = pd.DataFrame({
            'holdings': [
                {'stock1': 1.0},
                {'stock2': 1.0}
            ]
        })
        
        result = operators.lof_holding_concentration(single_holding_data)
        
        # HHI should be 1.0 for single holding
        np.testing.assert_allclose(
            result.values,
            np.ones(len(single_holding_data)),
            rtol=1e-10,
            err_msg="HHI should be 1.0 for single holding"
        )
    
    @given(data=valid_fund_analysis_data(min_rows=60, max_rows=100))
    @settings(max_examples=50, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_alpha_calculation_consistency(self, data):
        """测试Alpha计算一致性
        
        验证Alpha计算结果与手动计算一致
        """
        operators = LOFOperators()
        
        window = 20
        result = operators.lof_fund_manager_alpha(data, window=window)
        
        # Calculate manually
        excess_returns = data['returns'] - data['benchmark_returns']
        expected = excess_returns.rolling(window=window).mean()
        
        # Verify consistency
        np.testing.assert_allclose(
            result.dropna().values,
            expected.dropna().values,
            rtol=1e-10,
            err_msg="Alpha calculation should match manual calculation"
        )
    
    @given(data=valid_fund_analysis_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_holding_concentration_handles_empty_dict(self, data):
        """测试持仓集中度处理空字典"""
        operators = LOFOperators()
        
        # Create data with empty holdings dict
        empty_holdings_data = pd.DataFrame({
            'holdings': [{}, {'stock1': 1.0}]
        })
        
        result = operators.lof_holding_concentration(empty_holdings_data)
        
        # First row should be NaN, second should be 1.0
        assert np.isnan(result.iloc[0]), "Empty holdings should return NaN"
        np.testing.assert_allclose(result.iloc[1], 1.0, rtol=1e-10)
    
    @given(data=valid_fund_analysis_data(min_rows=30, max_rows=50))
    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.large_base_example, 
                                    HealthCheck.data_too_large,
                                    HealthCheck.too_slow])
    def test_holding_concentration_handles_non_dict(self, data):
        """测试持仓集中度处理非字典类型"""
        operators = LOFOperators()
        
        # Create data with non-dict holdings
        non_dict_holdings_data = pd.DataFrame({
            'holdings': ["not_a_dict", {'stock1': 1.0}]
        })
        
        result = operators.lof_holding_concentration(non_dict_holdings_data)
        
        # First row should be NaN, second should be 1.0
        assert np.isnan(result.iloc[0]), "Non-dict holdings should return NaN"
        np.testing.assert_allclose(result.iloc[1], 1.0, rtol=1e-10)
