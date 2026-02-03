"""
因子性能监控器属性测试 (Factor Performance Monitor Property Tests)

白皮书依据: 第四章 4.2.4 因子生命周期管理
测试框架: pytest + hypothesis

Property 24: Factor Performance Monitoring Continuity
Property 25: Factor Correlation Matrix Symmetry
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from src.evolution.arena.factor_performance_monitor import (
    FactorPerformanceMonitor,
    PerformanceMetrics,
    FactorDecayStatus,
    RiskFactor,
    DegradationSeverity
)


# ========== Test Strategies ==========

@st.composite
def factor_values_strategy(draw, min_size: int = 50, max_size: int = 200):
    """生成因子值序列策略"""
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    values = draw(st.lists(
        st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
        min_size=size,
        max_size=size
    ))
    dates = pd.date_range(start='2020-01-01', periods=size, freq='D')
    return pd.Series(values, index=dates)


@st.composite
def returns_strategy(draw, min_size: int = 50, max_size: int = 200):
    """生成收益率序列策略"""
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    values = draw(st.lists(
        st.floats(min_value=-0.1, max_value=0.1, allow_nan=False, allow_infinity=False),
        min_size=size,
        max_size=size
    ))
    dates = pd.date_range(start='2020-01-01', periods=size, freq='D')
    return pd.Series(values, index=dates)


@st.composite
def aligned_factor_returns_strategy(draw, min_size: int = 50, max_size: int = 200):
    """生成对齐的因子值和收益率序列策略"""
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    dates = pd.date_range(start='2020-01-01', periods=size, freq='D')
    
    factor_values = draw(st.lists(
        st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
        min_size=size,
        max_size=size
    ))
    
    returns = draw(st.lists(
        st.floats(min_value=-0.1, max_value=0.1, allow_nan=False, allow_infinity=False),
        min_size=size,
        max_size=size
    ))
    
    return (
        pd.Series(factor_values, index=dates),
        pd.Series(returns, index=dates)
    )


@st.composite
def rolling_ic_strategy(draw):
    """生成滚动IC字典策略"""
    periods = [1, 5, 10, 20]
    ic_dict = {}
    for period in periods:
        ic_dict[period] = draw(st.floats(
            min_value=-1.0, max_value=1.0,
            allow_nan=False, allow_infinity=False
        ))
    return ic_dict


@st.composite
def health_score_inputs_strategy(draw):
    """生成健康评分输入策略"""
    factor_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))))
    rolling_ic = draw(rolling_ic_strategy())
    ir = draw(st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False))
    sharpe_ratio = draw(st.floats(min_value=-3.0, max_value=5.0, allow_nan=False, allow_infinity=False))
    turnover_rate = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    return {
        'factor_id': factor_id,
        'rolling_ic': rolling_ic,
        'ir': ir,
        'sharpe_ratio': sharpe_ratio,
        'turnover_rate': turnover_rate
    }


@st.composite
def multiple_factors_strategy(draw, min_factors: int = 3, max_factors: int = 10):
    """生成多因子值字典策略"""
    num_factors = draw(st.integers(min_value=min_factors, max_value=max_factors))
    size = draw(st.integers(min_value=50, max_value=100))
    dates = pd.date_range(start='2020-01-01', periods=size, freq='D')
    
    factor_dict = {}
    for i in range(num_factors):
        factor_id = f"factor_{i}"
        # 确保至少有一些非零值以避免NaN相关性
        values = draw(st.lists(
            st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
            min_size=size,
            max_size=size
        ))
        # 确保不是全零
        if all(v == 0 for v in values):
            values[0] = 1.0
            values[-1] = -1.0
        factor_dict[factor_id] = pd.Series(values, index=dates)
    
    return factor_dict


# ========== Property 24: Factor Performance Monitoring Continuity ==========

class TestProperty24FactorPerformanceMonitoringContinuity:
    """Property 24: 因子性能监控连续性
    
    **Validates: Requirements 7.1**
    
    验证因子性能监控的连续性和一致性:
    1. 滚动IC计算覆盖所有指定周期
    2. 健康评分始终在[0, 1]范围内
    3. 性能指标记录完整
    4. 监控结果可追溯
    """
    
    @given(data=aligned_factor_returns_strategy(min_size=50, max_size=150))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_rolling_ic_covers_all_periods(self, data):
        """测试滚动IC覆盖所有指定周期
        
        **Validates: Requirements 7.1**
        """
        monitor = FactorPerformanceMonitor()
        factor_values, returns = data
        
        periods = [1, 5, 10, 20]
        rolling_ic = monitor.calculate_rolling_ic(factor_values, returns, periods)
        
        # 验证所有周期都有IC值
        for period in periods:
            assert period in rolling_ic, f"缺少{period}日IC"
            assert isinstance(rolling_ic[period], float), f"{period}日IC类型错误"
            assert -1 <= rolling_ic[period] <= 1 or rolling_ic[period] == 0.0, \
                f"{period}日IC超出范围: {rolling_ic[period]}"
    
    @given(inputs=health_score_inputs_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_health_score_in_valid_range(self, inputs):
        """测试健康评分始终在[0, 1]范围内
        
        **Validates: Requirements 7.1, 7.2**
        """
        monitor = FactorPerformanceMonitor()
        health_score = monitor.calculate_health_score(
            factor_id=inputs['factor_id'],
            rolling_ic=inputs['rolling_ic'],
            ir=inputs['ir'],
            sharpe_ratio=inputs['sharpe_ratio'],
            turnover_rate=inputs['turnover_rate']
        )
        
        assert 0 <= health_score <= 1, f"健康评分超出范围: {health_score}"
    
    @given(data=aligned_factor_returns_strategy(min_size=50, max_size=100))
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_monitor_factor_returns_complete_metrics(self, data):
        """测试因子监控返回完整的性能指标
        
        **Validates: Requirements 7.1**
        """
        monitor = FactorPerformanceMonitor()
        factor_values, returns = data
        factor_id = "test_factor"
        
        metrics = await monitor.monitor_factor(
            factor_id=factor_id,
            factor_values=factor_values,
            returns=returns
        )
        
        # 验证返回的指标完整
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.factor_id == factor_id
        assert isinstance(metrics.timestamp, datetime)
        assert isinstance(metrics.rolling_ic, dict)
        assert isinstance(metrics.ir, float)
        assert isinstance(metrics.sharpe_ratio, float)
        assert isinstance(metrics.turnover_rate, float)
        assert 0 <= metrics.health_score <= 1
        assert 0 <= metrics.ic_decay_rate <= 1
    
    @given(data=aligned_factor_returns_strategy(min_size=50, max_size=100))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_performance_history_recorded(self, data):
        """测试性能历史记录正确
        
        **Validates: Requirements 7.1**
        """
        monitor = FactorPerformanceMonitor()
        factor_values, returns = data
        factor_id = "test_factor_history"
        
        # 多次监控
        for _ in range(3):
            await monitor.monitor_factor(
                factor_id=factor_id,
                factor_values=factor_values,
                returns=returns
            )
        
        # 验证历史记录
        history = monitor.get_performance_history(factor_id)
        assert len(history) == 3, f"历史记录数量错误: {len(history)}"
        
        # 验证时间戳递增
        for i in range(1, len(history)):
            assert history[i].timestamp >= history[i-1].timestamp
    
    @given(
        factor_values=factor_values_strategy(min_size=50, max_size=100),
        previous_values=factor_values_strategy(min_size=50, max_size=100)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_turnover_rate_in_valid_range(self, factor_values, previous_values):
        """测试换手率始终在[0, 1]范围内
        
        **Validates: Requirements 7.1**
        """
        monitor = FactorPerformanceMonitor()
        # 确保索引对齐
        common_dates = factor_values.index.intersection(previous_values.index)
        assume(len(common_dates) >= 10)
        
        factor_aligned = factor_values.loc[common_dates]
        previous_aligned = previous_values.loc[common_dates]
        
        turnover_rate = monitor.calculate_turnover_rate(factor_aligned, previous_aligned)
        
        assert 0 <= turnover_rate <= 1, f"换手率超出范围: {turnover_rate}"


# ========== Property 25: Factor Correlation Matrix Symmetry ==========

class TestProperty25FactorCorrelationMatrixSymmetry:
    """Property 25: 因子相关性矩阵对称性
    
    **Validates: Requirements 7.3, 7.6**
    
    验证因子相关性矩阵的数学性质:
    1. 矩阵对称性: corr(A, B) = corr(B, A)
    2. 对角线为1: corr(A, A) = 1
    3. 值域范围: -1 <= corr <= 1
    4. 冗余检测一致性
    """
    
    @given(factor_dict=multiple_factors_strategy(min_factors=3, max_factors=8))
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_correlation_matrix_symmetry(self, factor_dict):
        """测试相关性矩阵对称性
        
        **Validates: Requirements 7.3, 7.6**
        """
        monitor = FactorPerformanceMonitor()
        corr_matrix = monitor.update_correlation_matrix(factor_dict)
        
        # 验证对称性
        factors = list(factor_dict.keys())
        for i, factor1 in enumerate(factors):
            for factor2 in factors[i+1:]:
                corr_12 = corr_matrix.loc[factor1, factor2]
                corr_21 = corr_matrix.loc[factor2, factor1]
                
                # 处理NaN情况（常数序列会产生NaN）
                if pd.isna(corr_12) and pd.isna(corr_21):
                    continue
                
                # 允许浮点误差
                assert abs(corr_12 - corr_21) < 1e-10, \
                    f"相关性矩阵不对称: corr({factor1}, {factor2})={corr_12}, " \
                    f"corr({factor2}, {factor1})={corr_21}"
    
    @given(factor_dict=multiple_factors_strategy(min_factors=3, max_factors=8))
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_correlation_matrix_diagonal_is_one(self, factor_dict):
        """测试相关性矩阵对角线为1
        
        **Validates: Requirements 7.3, 7.6**
        """
        monitor = FactorPerformanceMonitor()
        corr_matrix = monitor.update_correlation_matrix(factor_dict)
        
        # 验证对角线
        for factor in factor_dict.keys():
            diag_value = corr_matrix.loc[factor, factor]
            
            # 处理NaN情况（常数序列会产生NaN）
            if pd.isna(diag_value):
                continue
            
            assert abs(diag_value - 1.0) < 1e-10, \
                f"对角线值不为1: corr({factor}, {factor})={diag_value}"
    
    @given(factor_dict=multiple_factors_strategy(min_factors=3, max_factors=8))
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_correlation_values_in_valid_range(self, factor_dict):
        """测试相关性值在[-1, 1]范围内
        
        **Validates: Requirements 7.3, 7.6**
        """
        monitor = FactorPerformanceMonitor()
        corr_matrix = monitor.update_correlation_matrix(factor_dict)
        
        # 验证值域
        for factor1 in factor_dict.keys():
            for factor2 in factor_dict.keys():
                corr_value = corr_matrix.loc[factor1, factor2]
                
                # 处理NaN情况
                if pd.isna(corr_value):
                    continue
                
                assert -1 <= corr_value <= 1, \
                    f"相关性值超出范围: corr({factor1}, {factor2})={corr_value}"
    
    @given(factor_dict=multiple_factors_strategy(min_factors=3, max_factors=8))
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_redundant_detection_consistency(self, factor_dict):
        """测试冗余检测一致性
        
        **Validates: Requirements 7.3, 7.6**
        """
        monitor = FactorPerformanceMonitor()
        monitor.update_correlation_matrix(factor_dict)
        
        # 使用不同阈值检测冗余
        redundant_90 = monitor.detect_redundant_factors(threshold=0.9)
        redundant_95 = monitor.detect_redundant_factors(threshold=0.95)
        
        # 高阈值检测到的冗余对应该是低阈值的子集
        redundant_90_pairs = set((f1, f2) for f1, f2, _ in redundant_90)
        redundant_95_pairs = set((f1, f2) for f1, f2, _ in redundant_95)
        
        assert redundant_95_pairs.issubset(redundant_90_pairs), \
            "高阈值冗余对不是低阈值的子集"


# ========== Additional Property Tests ==========

class TestDegradationDetection:
    """因子衰减检测测试
    
    **Validates: Requirements 7.2**
    """
    
    @given(
        health_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        ic_decay_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_degradation_severity_consistency(self, health_score, ic_decay_rate):
        """测试衰减严重程度判定一致性
        
        **Validates: Requirements 7.2**
        """
        monitor = FactorPerformanceMonitor()
        factor_id = "test_factor"
        
        decay_status = monitor.detect_degradation(
            factor_id=factor_id,
            health_score=health_score,
            ic_decay_rate=ic_decay_rate
        )
        
        # 验证返回类型
        assert isinstance(decay_status, FactorDecayStatus)
        assert decay_status.factor_id == factor_id
        assert decay_status.health_score == health_score
        assert decay_status.ic_decay_rate == ic_decay_rate
        
        # 验证严重程度判定逻辑
        if health_score < 0.3:
            assert decay_status.severity == DegradationSeverity.SEVERE
            assert decay_status.is_decaying is True
        elif health_score < 0.5 or ic_decay_rate > 0.6:
            assert decay_status.severity == DegradationSeverity.MODERATE
            assert decay_status.is_decaying is True
        elif health_score < 0.7:
            assert decay_status.severity == DegradationSeverity.MILD
            assert decay_status.is_decaying is True
        else:
            assert decay_status.severity == DegradationSeverity.NONE
            assert decay_status.is_decaying is False
    
    @given(
        baseline_ic=st.floats(min_value=0.01, max_value=0.5, allow_nan=False),
        current_ic=st.floats(min_value=0.0, max_value=0.5, allow_nan=False)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_ic_decay_rate_calculation(self, baseline_ic, current_ic):
        """测试IC衰减率计算正确性
        
        **Validates: Requirements 7.2**
        """
        monitor = FactorPerformanceMonitor()
        factor_id = "test_factor"
        monitor.set_baseline_ic(factor_id, baseline_ic)
        
        decay_rate = monitor.calculate_ic_decay_rate(factor_id, current_ic)
        
        # 验证衰减率范围
        assert 0 <= decay_rate <= 1, f"衰减率超出范围: {decay_rate}"
        
        # 验证衰减率计算逻辑
        expected_decay = (abs(baseline_ic) - abs(current_ic)) / abs(baseline_ic)
        expected_decay = max(0, min(1, expected_decay))
        
        assert abs(decay_rate - expected_decay) < 1e-10, \
            f"衰减率计算错误: expected={expected_decay}, actual={decay_rate}"


class TestRiskFactorConversion:
    """风险因子转换测试
    
    **Validates: Requirements 7.5**
    """
    
    @given(data=aligned_factor_returns_strategy(min_size=50, max_size=100))
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_risk_factor_conversion_completeness(self, data):
        """测试风险因子转换完整性
        
        **Validates: Requirements 7.5**
        """
        monitor = FactorPerformanceMonitor()
        factor_values, returns = data
        factor_id = "failed_factor"
        current_price = 100.0
        
        risk_factor = await monitor.convert_to_risk_factor(
            factor_id=factor_id,
            factor_values=factor_values,
            returns=returns,
            current_price=current_price
        )
        
        # 验证风险因子完整性
        assert isinstance(risk_factor, RiskFactor)
        assert risk_factor.original_factor_id == factor_id
        assert risk_factor.risk_type == "factor_decay"
        assert 0 <= risk_factor.risk_value <= 1
        assert 0 <= risk_factor.confidence <= 1
        assert isinstance(risk_factor.exit_levels, dict)
        assert "immediate_exit" in risk_factor.exit_levels
        assert "warning_level" in risk_factor.exit_levels
        assert "stop_loss" in risk_factor.exit_levels
        assert isinstance(risk_factor.created_at, datetime)
    
    @given(data=aligned_factor_returns_strategy(min_size=50, max_size=100))
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_exit_levels_ordering(self, data):
        """测试退出价格水平排序正确
        
        **Validates: Requirements 7.5**
        """
        monitor = FactorPerformanceMonitor()
        factor_values, returns = data
        factor_id = "failed_factor"
        current_price = 100.0
        
        risk_factor = await monitor.convert_to_risk_factor(
            factor_id=factor_id,
            factor_values=factor_values,
            returns=returns,
            current_price=current_price
        )
        
        exit_levels = risk_factor.exit_levels
        
        # 验证退出水平排序: stop_loss < immediate_exit < warning_level < current_price
        assert exit_levels["stop_loss"] <= exit_levels["immediate_exit"], \
            "止损价应低于立即退出价"
        assert exit_levels["immediate_exit"] <= exit_levels["warning_level"], \
            "立即退出价应低于警告价"
        assert exit_levels["warning_level"] <= current_price, \
            "警告价应低于当前价"
    
    @given(data=aligned_factor_returns_strategy(min_size=50, max_size=100))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_risk_factor_registration(self, data):
        """测试风险因子注册正确
        
        **Validates: Requirements 7.5**
        """
        monitor = FactorPerformanceMonitor()
        factor_values, returns = data
        factor_id = "failed_factor_reg"
        current_price = 100.0
        
        risk_factor = await monitor.convert_to_risk_factor(
            factor_id=factor_id,
            factor_values=factor_values,
            returns=returns,
            current_price=current_price
        )
        
        # 验证风险因子已注册
        retrieved = monitor.get_risk_factor(factor_id)
        assert retrieved is not None
        assert retrieved.original_factor_id == factor_id
        assert retrieved.risk_value == risk_factor.risk_value


# ========== Edge Case Tests ==========

class TestEdgeCases:
    """边界情况测试"""
    
    @pytest.fixture
    def monitor(self):
        """创建性能监控器实例"""
        return FactorPerformanceMonitor()
    
    def test_empty_factor_values_raises_error(self, monitor):
        """测试空因子值序列抛出错误"""
        empty_series = pd.Series([], dtype=float)
        returns = pd.Series([0.01, 0.02, 0.03])
        
        with pytest.raises(ValueError, match="不能为空"):
            monitor.calculate_rolling_ic(empty_series, returns)
    
    def test_empty_returns_raises_error(self, monitor):
        """测试空收益率序列抛出错误"""
        factor_values = pd.Series([1.0, 2.0, 3.0])
        empty_returns = pd.Series([], dtype=float)
        
        with pytest.raises(ValueError, match="不能为空"):
            monitor.calculate_rolling_ic(factor_values, empty_returns)
    
    def test_invalid_health_score_raises_error(self, monitor):
        """测试无效健康评分抛出错误"""
        with pytest.raises(ValueError, match="健康评分必须在"):
            monitor.detect_degradation("test", health_score=1.5, ic_decay_rate=0.5)
        
        with pytest.raises(ValueError, match="健康评分必须在"):
            monitor.detect_degradation("test", health_score=-0.1, ic_decay_rate=0.5)
    
    def test_invalid_ic_decay_rate_raises_error(self, monitor):
        """测试无效IC衰减率抛出错误"""
        with pytest.raises(ValueError, match="IC衰减率必须在"):
            monitor.detect_degradation("test", health_score=0.5, ic_decay_rate=1.5)
        
        with pytest.raises(ValueError, match="IC衰减率必须在"):
            monitor.detect_degradation("test", health_score=0.5, ic_decay_rate=-0.1)
    
    def test_empty_factor_dict_raises_error(self, monitor):
        """测试空因子字典抛出错误"""
        with pytest.raises(ValueError, match="不能为空"):
            monitor.update_correlation_matrix({})
    
    def test_no_correlation_matrix_returns_empty_redundant(self, monitor):
        """测试未初始化相关性矩阵返回空冗余列表"""
        redundant = monitor.detect_redundant_factors()
        assert redundant == []
    
    def test_baseline_ic_not_set_returns_zero_decay(self, monitor):
        """测试未设置基准IC返回零衰减率"""
        decay_rate = monitor.calculate_ic_decay_rate("unknown_factor", 0.05)
        assert decay_rate == 0.0
