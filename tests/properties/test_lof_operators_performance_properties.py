"""Property-based tests for LOF performance operators (operators 11-20)

白皮书依据: 第四章 4.1.18 - LOF基金因子挖掘器
测试范围: LOF性能算子（11-20）

Property Tests:
- Property 10: LOF Operator Mathematical Correctness (operators 11-20)
- Property 14: Error Handling for Invalid Operator Inputs
- Property 15: Data Quality Threshold Enforcement
"""

import pytest
import pandas as pd
import numpy as np
from hypothesis import given, strategies as st, settings, HealthCheck

from src.evolution.etf_lof.lof_operators import LOFOperators
from src.evolution.etf_lof.exceptions import OperatorError, DataQualityError


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def operators():
    """创建LOFOperators实例"""
    return LOFOperators(data_quality_threshold=0.8)


# ============================================================================
# Data Generators
# ============================================================================

def generate_sector_weights():
    """生成行业权重字典（权重和为1）"""
    sectors = ['tech', 'finance', 'consumer', 'healthcare', 'energy']
    num_sectors = np.random.randint(2, len(sectors) + 1)
    selected_sectors = np.random.choice(sectors, num_sectors, replace=False)
    
    # 生成随机权重并归一化
    weights = np.random.random(num_sectors)
    weights = weights / weights.sum()
    
    return dict(zip(selected_sectors, weights))


@st.composite
def lof_performance_data(draw, min_rows=70, max_rows=100):
    """Generate LOF performance data for testing"""
    n_rows = draw(st.integers(min_value=min_rows, max_value=max_rows))
    
    return pd.DataFrame({
        'sector_weights': [generate_sector_weights() for _ in range(n_rows)],
        'turnover': [draw(st.floats(0.0, 1.0)) for _ in range(n_rows)],
        'returns': [draw(st.floats(-0.1, 0.1)) for _ in range(n_rows)],
        'expense_ratio': [draw(st.floats(0.001, 0.03)) for _ in range(n_rows)],
        'dividend': [draw(st.floats(0.0, 1.0)) for _ in range(n_rows)],
        'nav': [draw(st.floats(5.0, 20.0)) for _ in range(n_rows)],
        'redemption_amount': [draw(st.floats(1000, 100000)) for _ in range(n_rows)],
        'aum': [draw(st.floats(500000, 10000000)) for _ in range(n_rows)],
        'benchmark_returns': [draw(st.floats(-0.1, 0.1)) for _ in range(n_rows)],
        'peer_returns': [draw(st.floats(-0.1, 0.1)) for _ in range(n_rows)],
        'volume': [draw(st.floats(10000, 1000000)) for _ in range(n_rows)],
        'trade_size': [draw(st.floats(100, 50000)) for _ in range(n_rows)],
    })



# ============================================================================
# Property 10: LOF Operator Mathematical Correctness (operators 11-20)
# ============================================================================

class TestProperty10LOFPerformanceOperatorCorrectness:
    """Property 10: LOF性能算子数学正确性测试（算子11-20）
    
    白皮书依据: 第四章 4.1.18
    验证需求: Requirements 4.11-4.20, 8.2
    """
    
    @given(data=lof_performance_data(min_rows=70, max_rows=100))
    @settings(max_examples=100, deadline=None, suppress_health_check=[
        HealthCheck.large_base_example,
        HealthCheck.data_too_large
    ])
    def test_sector_allocation_shift_calculation(self, data):
        """测试行业配置变化计算正确性"""
        operators = LOFOperators()
        result = operators.lof_sector_allocation_shift(data, window=60)
        
        # 验证返回类型
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        
        # 验证非NaN值在合理范围（变化率通常在[-1, 1]）
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert valid_values.abs().max() < 10  # 允许极端情况
    
    @given(data=lof_performance_data(min_rows=70, max_rows=100))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large])
    def test_turnover_rate_calculation(self, data):
        """测试换手率计算正确性"""
        operators = LOFOperators()
        result = operators.lof_turnover_rate(data, window=60)
        
        # 验证返回类型
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        
        # 验证非NaN值在[0, 1]范围
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values >= 0).all()
            assert (valid_values <= 1).all()
    
    @given(data=lof_performance_data(min_rows=70, max_rows=100))
    @settings(max_examples=50, deadline=None, suppress_health_check=[
        HealthCheck.large_base_example,
        HealthCheck.data_too_large,
        HealthCheck.too_slow
    ])
    def test_performance_persistence_range(self, data):
        """测试业绩持续性在[-1, 1]范围"""
        # 扩展数据到260行以满足window=252的要求
        if len(data) < 260:
            # 复制数据以达到所需长度
            repeats = (260 // len(data)) + 1
            data = pd.concat([data] * repeats, ignore_index=True).iloc[:260]
        
        operators = LOFOperators()
        result = operators.lof_performance_persistence(data, window=252)
        
        # 验证返回类型
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        
        # 验证自相关系数在[-1, 1]范围
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values >= -1).all()
            assert (valid_values <= 1).all()
    
    @given(data=lof_performance_data(min_rows=70, max_rows=100))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large])
    def test_expense_ratio_impact_reduces_returns(self, data):
        """测试费率影响降低收益"""
        operators = LOFOperators()
        result = operators.lof_expense_ratio_impact(data)
        
        # 验证返回类型
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        
        # 验证净收益 < 总收益（费率为正时）
        returns = data['returns']
        assert (result <= returns).all()

    
    @given(data=lof_performance_data(min_rows=70, max_rows=100))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large])
    def test_dividend_yield_signal_range(self, data):
        """测试分红收益率在合理范围"""
        operators = LOFOperators()
        result = operators.lof_dividend_yield_signal(data)
        
        # 验证返回类型
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        
        # 验证分红收益率 >= 0
        assert (result >= 0).all()
        
        # 验证分红收益率 <= 分红/最小净值（理论最大值）
        max_yield = data['dividend'].max() / data['nav'].min()
        assert (result <= max_yield * 1.01).all()  # 允许小误差
    
    @given(data=lof_performance_data(min_rows=70, max_rows=100))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large])
    def test_nav_momentum_calculation(self, data):
        """测试净值动量计算正确性"""
        operators = LOFOperators()
        result = operators.lof_nav_momentum(data, window=20)
        
        # 验证返回类型
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        
        # 验证动量 = (nav[t] - nav[t-20]) / nav[t-20]
        nav = data['nav']
        expected = nav.pct_change(periods=20)
        pd.testing.assert_series_equal(result, expected, check_names=False)
    
    @given(data=lof_performance_data(min_rows=70, max_rows=100))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large])
    def test_redemption_pressure_range(self, data):
        """测试赎回压力在合理范围"""
        operators = LOFOperators()
        result = operators.lof_redemption_pressure(data, window=20)
        
        # 验证返回类型
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        
        # 验证赎回压力 >= 0
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values >= 0).all()
            
            # 验证赎回压力 <= 1（赎回不能超过总资产）
            assert (valid_values <= 1).all()
    
    @given(data=lof_performance_data(min_rows=70, max_rows=100))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large])
    def test_benchmark_tracking_quality_non_negative(self, data):
        """测试基准跟踪质量非负"""
        operators = LOFOperators()
        result = operators.lof_benchmark_tracking_quality(data, window=60)
        
        # 验证返回类型
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        
        # 验证跟踪误差 >= 0（标准差非负）
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values >= 0).all()
    
    @given(data=lof_performance_data(min_rows=70, max_rows=100))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large])
    def test_market_impact_cost_range(self, data):
        """测试市场冲击成本在合理范围"""
        operators = LOFOperators()
        result = operators.lof_market_impact_cost(data, window=20)
        
        # 验证返回类型
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        
        # 验证市场冲击 >= 0
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values >= 0).all()
            
            # 验证市场冲击 <= 1（交易规模不应超过成交量）
            assert (valid_values <= 1).all()
    
    @given(data=lof_performance_data(min_rows=70, max_rows=100))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large])
    def test_cross_sectional_momentum_calculation(self, data):
        """测试横截面动量计算正确性"""
        operators = LOFOperators()
        result = operators.lof_cross_sectional_momentum(data, window=20)
        
        # 验证返回类型
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        
        # 验证横截面动量 = (returns - peer_returns)的滚动均值
        relative_returns = data['returns'] - data['peer_returns']
        expected = relative_returns.rolling(window=20).mean()
        pd.testing.assert_series_equal(result, expected, check_names=False)



# ============================================================================
# Property 14: Error Handling for Invalid Operator Inputs
# ============================================================================

class TestProperty14LOFPerformanceErrorHandling:
    """Property 14: LOF性能算子错误处理测试
    
    白皮书依据: 第四章 4.1.18
    验证需求: Requirements 8.1, 8.2
    """
    
    def test_sector_allocation_shift_missing_column(self, operators):
        """测试行业配置变化缺失列错误"""
        data = pd.DataFrame({'wrong_col': [1, 2, 3]})
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.lof_sector_allocation_shift(data)
    
    def test_sector_allocation_shift_invalid_window(self, operators):
        """测试行业配置变化无效窗口错误"""
        data = pd.DataFrame({
            'sector_weights': [generate_sector_weights() for _ in range(100)]
        })
        
        with pytest.raises(ValueError, match="window must be > 0"):
            operators.lof_sector_allocation_shift(data, window=0)
        
        with pytest.raises(ValueError, match="window must be > 0"):
            operators.lof_sector_allocation_shift(data, window=-10)
    
    def test_turnover_rate_empty_data(self, operators):
        """测试换手率空数据错误"""
        data = pd.DataFrame({'turnover': []})
        
        with pytest.raises(OperatorError, match="Input data is empty"):
            operators.lof_turnover_rate(data)
    
    def test_performance_persistence_invalid_window(self, operators):
        """测试业绩持续性无效窗口错误"""
        data = pd.DataFrame({'returns': [0.01] * 300})
        
        with pytest.raises(ValueError, match="window must be > 1"):
            operators.lof_performance_persistence(data, window=1)
        
        with pytest.raises(ValueError, match="window must be > 1"):
            operators.lof_performance_persistence(data, window=0)
    
    def test_expense_ratio_impact_missing_columns(self, operators):
        """测试费率影响缺失列错误"""
        data = pd.DataFrame({'returns': [0.01, 0.02]})
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.lof_expense_ratio_impact(data)
    
    def test_dividend_yield_signal_missing_columns(self, operators):
        """测试分红收益率缺失列错误"""
        data = pd.DataFrame({'dividend': [0.1, 0.2]})
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.lof_dividend_yield_signal(data)
    
    def test_nav_momentum_invalid_window(self, operators):
        """测试净值动量无效窗口错误"""
        data = pd.DataFrame({'nav': [10.0] * 50})
        
        with pytest.raises(ValueError, match="window must be > 0"):
            operators.lof_nav_momentum(data, window=-5)
    
    def test_redemption_pressure_missing_columns(self, operators):
        """测试赎回压力缺失列错误"""
        data = pd.DataFrame({'redemption_amount': [1000, 2000]})
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.lof_redemption_pressure(data)
    
    def test_benchmark_tracking_quality_invalid_window(self, operators):
        """测试基准跟踪质量无效窗口错误"""
        data = pd.DataFrame({
            'returns': [0.01] * 100,
            'benchmark_returns': [0.008] * 100
        })
        
        with pytest.raises(ValueError, match="window must be > 1"):
            operators.lof_benchmark_tracking_quality(data, window=1)
    
    def test_market_impact_cost_empty_data(self, operators):
        """测试市场冲击成本空数据错误"""
        data = pd.DataFrame({'volume': [], 'trade_size': []})
        
        with pytest.raises(OperatorError, match="Input data is empty"):
            operators.lof_market_impact_cost(data)
    
    def test_cross_sectional_momentum_missing_columns(self, operators):
        """测试横截面动量缺失列错误"""
        data = pd.DataFrame({'returns': [0.01, 0.02]})
        
        with pytest.raises(OperatorError, match="Missing required columns"):
            operators.lof_cross_sectional_momentum(data)



# ============================================================================
# Property 15: Data Quality Threshold Enforcement
# ============================================================================

class TestProperty15LOFPerformanceDataQuality:
    """Property 15: LOF性能算子数据质量阈值测试
    
    白皮书依据: 第四章 4.1.18
    验证需求: Requirements 8.4
    """
    
    def test_sector_allocation_shift_low_quality_data(self):
        """测试行业配置变化低质量数据错误"""
        operators = LOFOperators(data_quality_threshold=0.8)
        
        # 创建50%为NaN的数据（低于80%阈值）
        data = pd.DataFrame({
            'sector_weights': [generate_sector_weights() if i % 2 == 0 else np.nan 
                              for i in range(100)]
        })
        
        with pytest.raises(DataQualityError, match="too many NaN values"):
            operators.lof_sector_allocation_shift(data)
    
    def test_turnover_rate_low_quality_data(self):
        """测试换手率低质量数据错误"""
        operators = LOFOperators(data_quality_threshold=0.8)
        
        # 创建70%为NaN的数据（低于80%阈值）
        data = pd.DataFrame({
            'turnover': [0.1 if i % 10 < 3 else np.nan for i in range(100)]
        })
        
        with pytest.raises(DataQualityError, match="too many NaN values"):
            operators.lof_turnover_rate(data)
    
    def test_performance_persistence_low_quality_data(self):
        """测试业绩持续性低质量数据错误"""
        operators = LOFOperators(data_quality_threshold=0.8)
        
        # 创建60%为NaN的数据（低于80%阈值）
        data = pd.DataFrame({
            'returns': [0.01 if i % 5 < 2 else np.nan for i in range(300)]
        })
        
        with pytest.raises(DataQualityError, match="too many NaN values"):
            operators.lof_performance_persistence(data)
    
    def test_nav_momentum_low_quality_data(self):
        """测试净值动量低质量数据错误"""
        operators = LOFOperators(data_quality_threshold=0.8)
        
        # 创建50%为NaN的数据（低于80%阈值）
        data = pd.DataFrame({
            'nav': [10.0 if i % 2 == 0 else np.nan for i in range(100)]
        })
        
        with pytest.raises(DataQualityError, match="too many NaN values"):
            operators.lof_nav_momentum(data)


# ============================================================================
# Additional Properties
# ============================================================================

class TestAdditionalProperties:
    """额外的属性测试"""
    
    def test_all_performance_operators_registered(self, operators):
        """测试所有性能算子已注册"""
        expected_operators = [
            'lof_sector_allocation_shift',
            'lof_turnover_rate',
            'lof_performance_persistence',
            'lof_expense_ratio_impact',
            'lof_dividend_yield_signal',
            'lof_nav_momentum',
            'lof_redemption_pressure',
            'lof_benchmark_tracking_quality',
            'lof_market_impact_cost',
            'lof_cross_sectional_momentum',
        ]
        
        available_operators = operators.list_operators()
        
        for op in expected_operators:
            assert op in available_operators, f"算子 {op} 未注册"
    
    def test_expense_ratio_impact_consistency(self, operators):
        """测试费率影响的一致性"""
        data = pd.DataFrame({
            'returns': [0.01, 0.02, 0.015, 0.018, 0.012],
            'expense_ratio': [0.015] * 5  # 1.5% annual
        })
        
        result = operators.lof_expense_ratio_impact(data)
        
        # 验证每日费率扣除一致
        daily_expense = 0.015 / 252
        expected = data['returns'] - daily_expense
        
        pd.testing.assert_series_equal(result, expected, check_names=False)
    
    def test_dividend_yield_zero_dividend(self, operators):
        """测试零分红情况"""
        data = pd.DataFrame({
            'dividend': [0.0, 0.0, 0.0],
            'nav': [10.0, 10.5, 11.0]
        })
        
        result = operators.lof_dividend_yield_signal(data)
        
        # 验证零分红时收益率为0
        assert (result == 0.0).all()
    
    def test_redemption_pressure_zero_redemption(self, operators):
        """测试零赎回情况"""
        data = pd.DataFrame({
            'redemption_amount': [0.0] * 50,
            'aum': [1000000.0] * 50
        })
        
        result = operators.lof_redemption_pressure(data, window=20)
        
        # 验证零赎回时压力为0
        valid_values = result.dropna()
        assert (valid_values == 0.0).all()
    
    def test_benchmark_tracking_quality_perfect_tracking(self, operators):
        """测试完美跟踪情况"""
        # 完美跟踪：收益率完全相同
        returns = [0.01, 0.02, 0.015, 0.018, 0.012] * 20
        data = pd.DataFrame({
            'returns': returns,
            'benchmark_returns': returns  # 完全相同
        })
        
        result = operators.lof_benchmark_tracking_quality(data, window=60)
        
        # 验证完美跟踪时跟踪误差为0
        valid_values = result.dropna()
        assert (valid_values == 0.0).all()
    
    def test_market_impact_cost_zero_trade(self, operators):
        """测试零交易情况"""
        data = pd.DataFrame({
            'volume': [100000.0] * 50,
            'trade_size': [0.0] * 50
        })
        
        result = operators.lof_market_impact_cost(data, window=20)
        
        # 验证零交易时冲击为0
        valid_values = result.dropna()
        assert (valid_values == 0.0).all()
    
    def test_cross_sectional_momentum_equal_performance(self, operators):
        """测试相同表现情况"""
        # 与同类基金表现相同
        returns = [0.01, 0.02, 0.015, 0.018, 0.012] * 20
        data = pd.DataFrame({
            'returns': returns,
            'peer_returns': returns  # 完全相同
        })
        
        result = operators.lof_cross_sectional_momentum(data, window=20)
        
        # 验证相同表现时横截面动量为0
        valid_values = result.dropna()
        assert np.allclose(valid_values, 0.0, atol=1e-10)
