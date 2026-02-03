"""Property-Based Tests for Performance Monitoring and Decay Detection

白皮书依据: 第四章 4.6 性能监控与衰减检测

Properties tested:
- Property 38: Daily Factor Monitoring
- Property 39: IC Threshold Warning
- Property 40: Consecutive Day Decay Detection
- Property 41: Decay Severity Response
- Property 42: Retired Factor Conversion
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, HealthCheck, assume

from src.evolution.monitoring.data_models import (
    DecaySeverity,
    DecayAction,
)
from src.evolution.monitoring.performance_monitor import PerformanceMonitor
from src.evolution.monitoring.decay_detector import DecayDetector


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def factor_id_strategy(draw):
    """生成因子ID"""
    return f"FACTOR_{draw(st.integers(min_value=1, max_value=1000))}"


@st.composite
def ic_value_strategy(draw):
    """生成IC值"""
    return draw(st.floats(min_value=-1.0, max_value=1.0))


@st.composite
def ir_value_strategy(draw):
    """生成IR值"""
    return draw(st.floats(min_value=-10.0, max_value=10.0))


@st.composite
def sharpe_ratio_strategy(draw):
    """生成夏普比率"""
    return draw(st.floats(min_value=-5.0, max_value=5.0))


# ============================================================================
# Property 38: Daily Factor Monitoring
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    factor_id=factor_id_strategy(),
    num_days=st.integers(min_value=1, max_value=30),
    ic=ic_value_strategy(),
    ir=ir_value_strategy()
)
def test_property_38_daily_factor_monitoring(factor_id, num_days, ic, ir):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 38: Daily Factor Monitoring
    
    For any active factor, the system should monitor its IC and IR daily.
    
    白皮书依据: 第四章 4.6.1 每日因子监控 - Requirement 8.1
    Validates: Requirements 8.1
    """
    # 创建性能监控器
    monitor = PerformanceMonitor()
    
    # 模拟多天监控
    for day in range(num_days):
        date = datetime.now() + timedelta(days=day)
        
        # 记录因子性能
        record = monitor.record_factor_performance(
            factor_id=factor_id,
            date=date,
            ic=ic,
            ir=ir
        )
        
        # 验证：记录应该被创建
        assert record is not None, \
            f"第{day}天的记录应该被创建"
        
        # 验证：记录包含正确的数据
        assert record.factor_id == factor_id, \
            "因子ID应该正确"
        
        assert record.date == date, \
            "日期应该正确"
        
        assert record.ic == ic, \
            "IC应该正确"
        
        assert record.ir == ir, \
            "IR应该正确"
    
    # 验证：所有记录都应该被存储
    records = monitor.get_factor_records(factor_id)
    assert len(records) == num_days, \
        f"应该有{num_days}条记录，实际: {len(records)}"


# ============================================================================
# Property 39: IC Threshold Warning
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    factor_id=factor_id_strategy(),
    ic=st.floats(min_value=-1.0, max_value=0.029),  # 低于阈值0.03
    ir=ir_value_strategy()
)
def test_property_39_ic_threshold_warning(factor_id, ic, ir):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 39: IC Threshold Warning
    
    For any factor with IC < 0.03, the system should log a decay warning.
    
    白皮书依据: 第四章 4.6.2 IC阈值警告 - Requirement 8.2
    Validates: Requirements 8.2
    """
    # 创建性能监控器
    monitor = PerformanceMonitor(ic_warning_threshold=0.03)
    
    # 记录因子性能
    record = monitor.record_factor_performance(
        factor_id=factor_id,
        date=datetime.now(),
        ic=ic,
        ir=ir
    )
    
    # 验证：应该触发警告
    assert record.is_warning, \
        f"IC={ic:.4f} < 0.03时应该触发警告"
    
    # 验证：监控器应该检测到警告
    assert monitor.has_warning(factor_id), \
        "监控器应该检测到警告"


# ============================================================================
# Property 40: Consecutive Day Decay Detection
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    factor_id=factor_id_strategy(),
    consecutive_days=st.integers(min_value=30, max_value=60)
)
def test_property_40_consecutive_day_decay_detection(factor_id, consecutive_days):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 40: Consecutive Day Decay Detection
    
    For any factor with IC < 0.03 for 30 consecutive days, the system should
    mark it as decaying.
    
    白皮书依据: 第四章 4.6.3 连续天数衰减检测 - Requirement 8.3
    Validates: Requirements 8.3
    """
    # 创建性能监控器和衰减检测器
    monitor = PerformanceMonitor(ic_warning_threshold=0.03)
    detector = DecayDetector(
        performance_monitor=monitor,
        ic_threshold=0.03,
        severe_decay_days=30
    )
    
    # 模拟连续低IC天数
    for day in range(consecutive_days):
        date = datetime.now() + timedelta(days=day)
        
        # 记录低IC性能
        monitor.record_factor_performance(
            factor_id=factor_id,
            date=date,
            ic=0.02,  # 低于阈值0.03
            ir=0.5
        )
    
    # 检测衰减
    result = detector.detect_decay(factor_id)
    
    # 验证：应该标记为衰减
    assert result.is_decaying, \
        f"连续{consecutive_days}天IC<0.03时应该标记为衰减"
    
    # 验证：连续天数应该正确
    assert result.consecutive_low_ic_days == consecutive_days, \
        f"连续天数应该为{consecutive_days}，实际: {result.consecutive_low_ic_days}"
    
    # 验证：严重程度应该为SEVERE
    assert result.severity == DecaySeverity.SEVERE, \
        f"连续{consecutive_days}天应该为SEVERE，实际: {result.severity.value}"


# ============================================================================
# Property 41: Decay Severity Response
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    factor_id=factor_id_strategy(),
    severity_type=st.sampled_from(['mild', 'moderate', 'severe'])
)
def test_property_41_decay_severity_response(factor_id, severity_type):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 41: Decay Severity Response
    
    For any factor showing mild decay, the system should reduce its weight by 30%;
    for moderate decay, pause and retest; for severe decay, retire immediately.
    
    白皮书依据: 第四章 4.6.4 衰减响应动作 - Requirements 8.4, 8.5, 8.6
    Validates: Requirements 8.4, 8.5, 8.6
    """
    # 创建性能监控器和衰减检测器
    monitor = PerformanceMonitor(ic_warning_threshold=0.03)
    detector = DecayDetector(
        performance_monitor=monitor,
        ic_threshold=0.03,
        mild_decay_days=7,
        moderate_decay_days=15,
        severe_decay_days=30
    )
    
    # 根据严重程度类型模拟不同天数
    if severity_type == 'mild':
        num_days = 10  # 7-14天
        expected_action = DecayAction.REDUCE_WEIGHT
    elif severity_type == 'moderate':
        num_days = 20  # 15-29天
        expected_action = DecayAction.PAUSE_AND_RETEST
    else:  # severe
        num_days = 35  # >=30天
        expected_action = DecayAction.RETIRE_IMMEDIATELY
    
    # 模拟连续低IC天数
    for day in range(num_days):
        date = datetime.now() + timedelta(days=day)
        monitor.record_factor_performance(
            factor_id=factor_id,
            date=date,
            ic=0.02,  # 低于阈值0.03
            ir=0.5
        )
    
    # 检测衰减
    result = detector.detect_decay(factor_id)
    
    # 验证：推荐动作应该正确
    assert result.recommended_action == expected_action, \
        f"{severity_type}衰减应该推荐{expected_action.value}，" \
        f"实际: {result.recommended_action.value}"
    
    # 验证：如果是轻度衰减，测试权重降低
    if severity_type == 'mild':
        current_weight = 1.0
        new_weight = detector.apply_weight_reduction(
            factor_id=factor_id,
            current_weight=current_weight,
            reduction_ratio=0.3
        )
        
        # 验证：权重应该降低30%
        expected_weight = current_weight * 0.7
        assert abs(new_weight - expected_weight) < 0.001, \
            f"权重应该降低30%，期望: {expected_weight:.4f}，实际: {new_weight:.4f}"


# ============================================================================
# Property 42: Retired Factor Conversion
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    factor_id=factor_id_strategy()
)
def test_property_42_retired_factor_conversion(factor_id):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 42: Retired Factor Conversion
    
    For any retired factor, the system should convert it to a risk factor for
    generating sell signals.
    
    白皮书依据: 第四章 4.6.7 退役因子转换 - Requirement 8.7
    Validates: Requirements 8.7
    """
    # 创建性能监控器和衰减检测器
    monitor = PerformanceMonitor()
    detector = DecayDetector(performance_monitor=monitor)
    
    # 转换为风险因子
    risk_factor_id = detector.convert_to_risk_factor(factor_id)
    
    # 验证：风险因子ID应该包含原因子ID
    assert factor_id in risk_factor_id, \
        f"风险因子ID应该包含原因子ID，" \
        f"factor_id={factor_id}, risk_factor_id={risk_factor_id}"
    
    # 验证：风险因子ID应该有RISK前缀
    assert risk_factor_id.startswith("RISK_"), \
        f"风险因子ID应该以RISK_开头，实际: {risk_factor_id}"
    
    # 验证：转换应该是确定性的
    risk_factor_id_2 = detector.convert_to_risk_factor(factor_id)
    assert risk_factor_id == risk_factor_id_2, \
        "相同因子的转换结果应该一致"
