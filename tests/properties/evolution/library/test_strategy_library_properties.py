"""Property-Based Tests for Strategy Library Management System

白皮书依据: 第四章 4.4 策略库管理系统

Properties tested:
- Property 19: Z2H-Only Query Results
- Property 20: Strategy Type Filtering
- Property 21: Performance Metric Filtering
- Property 22: Market Regime Filtering
- Property 23: Performance Degradation Status Update
- Property 24: Time-Based Decay Detection
- Property 25: Deprecated Strategy Capital Restriction
- Property 26: Lifecycle State Transitions
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, HealthCheck
from typing import List

from src.evolution.library.data_models import (
    StrategyType,
    MarketRegime,
    LifecycleState,
    StrategyMetadata,
    StrategyRecord,
)
from src.evolution.library.strategy_library import StrategyLibrary
from src.evolution.library.strategy_query_engine import StrategyQueryEngine
from src.evolution.library.lifecycle_manager import LifecycleManager


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def strategy_id_strategy(draw):
    """生成策略ID"""
    prefix = draw(st.sampled_from(['STR', 'FAC', 'ARB']))
    number = draw(st.integers(min_value=1, max_value=9999))
    return f"{prefix}{number:04d}"


@st.composite
def strategy_name_strategy(draw):
    """生成策略名称"""
    names = [
        '动量突破策略', '均值回归策略', '趋势跟踪策略', '套利策略',
        '市场中性策略', '统计套利策略', '多因子策略', '因子组合策略'
    ]
    return draw(st.sampled_from(names))


@st.composite
def strategy_metadata_strategy(draw, z2h_certified=None, lifecycle_state=None):
    """生成策略元数据
    
    Args:
        z2h_certified: 如果指定，生成指定Z2H认证状态的策略
        lifecycle_state: 如果指定，生成指定生命周期状态的策略
    """
    strategy_id = draw(strategy_id_strategy())
    strategy_name = draw(strategy_name_strategy())
    strategy_type = draw(st.sampled_from(list(StrategyType)))
    
    # Z2H认证
    if z2h_certified is None:
        z2h_certified = draw(st.booleans())
    
    z2h_level = None
    z2h_date = None
    if z2h_certified:
        z2h_level = draw(st.sampled_from(['PLATINUM', 'GOLD', 'SILVER']))
        z2h_date = datetime.now() - timedelta(days=draw(st.integers(min_value=1, max_value=365)))
    
    # 性能指标
    sharpe_ratio = draw(st.floats(min_value=0.5, max_value=4.0))
    max_drawdown = draw(st.floats(min_value=-0.30, max_value=-0.05))
    annual_return = draw(st.floats(min_value=0.05, max_value=1.0))
    win_rate = draw(st.floats(min_value=0.40, max_value=0.80))
    profit_factor = draw(st.floats(min_value=1.0, max_value=3.0))
    
    # Arena评分
    arena_score = draw(st.floats(min_value=0.5, max_value=1.0))
    
    # 适用市场状态
    num_regimes = draw(st.integers(min_value=1, max_value=3))
    suitable_regimes = draw(st.lists(
        st.sampled_from(list(MarketRegime)),
        min_size=num_regimes,
        max_size=num_regimes,
        unique=True
    ))
    
    # 生命周期状态
    if lifecycle_state is None:
        lifecycle_state = draw(st.sampled_from(list(LifecycleState)))
    
    # IC监控
    recent_ic = draw(st.floats(min_value=0.01, max_value=0.10))
    ic_below_threshold_days = draw(st.integers(min_value=0, max_value=60))
    
    return StrategyMetadata(
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        strategy_type=strategy_type,
        description=f"{strategy_name}的描述",
        z2h_certified=z2h_certified,
        z2h_certification_level=z2h_level,
        z2h_certification_date=z2h_date,
        source_factors=['factor_1', 'factor_2'],
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        annual_return=annual_return,
        win_rate=win_rate,
        profit_factor=profit_factor,
        arena_score=arena_score,
        arena_test_date=datetime.now() - timedelta(days=30),
        simulation_passed=z2h_certified,
        simulation_metrics={'sharpe': sharpe_ratio, 'dd': max_drawdown},
        simulation_end_date=datetime.now() - timedelta(days=15) if z2h_certified else None,
        suitable_regimes=suitable_regimes,
        lifecycle_state=lifecycle_state,
        recent_ic=recent_ic,
        ic_below_threshold_days=ic_below_threshold_days,
    )


# ============================================================================
# Property 19: Z2H-Only Query Results
# ============================================================================

@st.composite
def unique_strategies_strategy(draw):
    """生成两组策略ID不重复的策略列表
    
    Returns:
        Tuple[List[StrategyMetadata], List[StrategyMetadata]]: (Z2H认证策略列表, 非Z2H认证策略列表)
    """
    # 生成所有唯一的策略ID
    num_z2h = draw(st.integers(min_value=1, max_value=5))
    num_non_z2h = draw(st.integers(min_value=1, max_value=5))
    total_strategies = num_z2h + num_non_z2h
    
    # 生成唯一的策略ID列表
    all_ids = []
    for i in range(total_strategies):
        prefix = draw(st.sampled_from(['STR', 'FAC', 'ARB']))
        number = 1000 + i  # 确保唯一性
        all_ids.append(f"{prefix}{number:04d}")
    
    # 分配ID给Z2H和非Z2H策略
    z2h_ids = all_ids[:num_z2h]
    non_z2h_ids = all_ids[num_z2h:]
    
    # 生成Z2H认证策略
    z2h_strategies = []
    for strategy_id in z2h_ids:
        metadata = draw(strategy_metadata_strategy(z2h_certified=True))
        metadata.strategy_id = strategy_id  # 覆盖生成的ID
        z2h_strategies.append(metadata)
    
    # 生成非Z2H认证策略
    non_z2h_strategies = []
    for strategy_id in non_z2h_ids:
        metadata = draw(strategy_metadata_strategy(z2h_certified=False))
        metadata.strategy_id = strategy_id  # 覆盖生成的ID
        non_z2h_strategies.append(metadata)
    
    return z2h_strategies, non_z2h_strategies


@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    strategies_tuple=unique_strategies_strategy()
)
def test_property_19_z2h_only_query_results(strategies_tuple):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 19: Z2H-Only Query Results
    
    For any query with z2h_only=True, the system should return only Z2H-certified
    strategies and exclude all non-certified strategies.
    
    白皮书依据: 第四章 4.4.6 策略查询 - Requirement 5.1
    Validates: Requirements 5.1
    """
    z2h_strategies, non_z2h_strategies = strategies_tuple
    
    # 创建查询引擎
    query_engine = StrategyQueryEngine()
    
    # 合并所有策略
    all_strategies = z2h_strategies + non_z2h_strategies
    
    # 查询Z2H认证策略
    results = query_engine.query(all_strategies, z2h_only=True)
    
    # 验证：所有返回的策略都是Z2H认证的
    assert all(s.z2h_certified for s in results), \
        "查询结果中存在非Z2H认证策略"
    
    # 验证：所有Z2H认证策略都被返回
    z2h_ids = {s.strategy_id for s in z2h_strategies}
    result_ids = {s.strategy_id for s in results}
    assert z2h_ids == result_ids, \
        f"Z2H认证策略未完全返回: 期望{z2h_ids}, 实际{result_ids}"
    
    # 验证：没有非Z2H认证策略被返回
    non_z2h_ids = {s.strategy_id for s in non_z2h_strategies}
    assert result_ids.isdisjoint(non_z2h_ids), \
        "查询结果中包含非Z2H认证策略"


# ============================================================================
# Property 20: Strategy Type Filtering
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    strategies=st.lists(
        strategy_metadata_strategy(),
        min_size=5,
        max_size=15
    ),
    target_types=st.lists(
        st.sampled_from(list(StrategyType)),
        min_size=1,
        max_size=3,
        unique=True
    )
)
def test_property_20_strategy_type_filtering(strategies, target_types):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 20: Strategy Type Filtering
    
    For any query with strategy_types filter, the system should return only
    strategies matching the specified types.
    
    白皮书依据: 第四章 4.4.6 策略查询 - Requirement 5.2
    Validates: Requirements 5.2
    """
    # 创建查询引擎
    query_engine = StrategyQueryEngine()
    
    # 按类型过滤
    results = query_engine.filter_by_type(strategies, target_types)
    
    # 验证：所有返回的策略类型都在目标类型中
    assert all(s.strategy_type in target_types for s in results), \
        "查询结果中存在不匹配的策略类型"
    
    # 验证：所有匹配类型的策略都被返回
    expected_ids = {s.strategy_id for s in strategies if s.strategy_type in target_types}
    result_ids = {s.strategy_id for s in results}
    assert expected_ids == result_ids, \
        f"类型匹配的策略未完全返回: 期望{len(expected_ids)}, 实际{len(result_ids)}"


# ============================================================================
# Property 21: Performance Metric Filtering
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    strategies=st.lists(
        strategy_metadata_strategy(),
        min_size=5,
        max_size=15
    ),
    min_sharpe=st.floats(min_value=1.0, max_value=2.5),
    max_drawdown=st.floats(min_value=-0.20, max_value=-0.10)
)
def test_property_21_performance_metric_filtering(strategies, min_sharpe, max_drawdown):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 21: Performance Metric Filtering
    
    For any query with performance metric filters (Sharpe ratio, drawdown),
    the system should return only strategies meeting the criteria.
    
    白皮书依据: 第四章 4.4.6 策略查询 - Requirement 5.3
    Validates: Requirements 5.3
    """
    # 创建查询引擎
    query_engine = StrategyQueryEngine()
    
    # 按性能指标过滤
    results = query_engine.query(
        strategies,
        min_sharpe=min_sharpe,
        max_drawdown=max_drawdown
    )
    
    # 验证：所有返回的策略夏普比率 >= min_sharpe
    assert all(s.sharpe_ratio >= min_sharpe for s in results), \
        f"查询结果中存在夏普比率低于{min_sharpe}的策略"
    
    # 验证：所有返回的策略回撤 >= max_drawdown（回撤是负数，越大越好）
    assert all(s.max_drawdown >= max_drawdown for s in results), \
        f"查询结果中存在回撤超过{max_drawdown}的策略"
    
    # 验证：所有符合条件的策略都被返回
    expected_ids = {
        s.strategy_id for s in strategies
        if s.sharpe_ratio >= min_sharpe and s.max_drawdown >= max_drawdown
    }
    result_ids = {s.strategy_id for s in results}
    assert expected_ids == result_ids, \
        f"符合条件的策略未完全返回: 期望{len(expected_ids)}, 实际{len(result_ids)}"


# ============================================================================
# Property 22: Market Regime Filtering
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    strategies=st.lists(
        strategy_metadata_strategy(),
        min_size=5,
        max_size=15
    ),
    target_regimes=st.lists(
        st.sampled_from(list(MarketRegime)),
        min_size=1,
        max_size=2,
        unique=True
    )
)
def test_property_22_market_regime_filtering(strategies, target_regimes):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 22: Market Regime Filtering
    
    For any query with market regime filter, the system should return only
    strategies suitable for the specified regimes.
    
    白皮书依据: 第四章 4.4.6 策略查询 - Requirement 5.4
    Validates: Requirements 5.4
    """
    # 创建查询引擎
    query_engine = StrategyQueryEngine()
    
    # 按市场状态过滤
    results = query_engine.filter_by_regime(strategies, target_regimes)
    
    # 验证：所有返回的策略至少适用于一个目标市场状态
    for strategy in results:
        assert any(regime in strategy.suitable_regimes for regime in target_regimes), \
            f"策略{strategy.strategy_id}不适用于任何目标市场状态"
    
    # 验证：所有适用的策略都被返回
    expected_ids = {
        s.strategy_id for s in strategies
        if any(regime in s.suitable_regimes for regime in target_regimes)
    }
    result_ids = {s.strategy_id for s in results}
    assert expected_ids == result_ids, \
        f"适用的策略未完全返回: 期望{len(expected_ids)}, 实际{len(result_ids)}"


# ============================================================================
# Property 23: Performance Degradation Status Update
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    metadata=strategy_metadata_strategy(lifecycle_state=LifecycleState.ACTIVE),
    degraded_ic=st.floats(min_value=0.01, max_value=0.029),  # 低于0.03阈值
    degraded_sharpe=st.floats(min_value=0.5, max_value=0.99)  # 低于1.0阈值
)
def test_property_23_performance_degradation_status_update(metadata, degraded_ic, degraded_sharpe):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 23: Performance Degradation Status Update
    
    For any ACTIVE strategy with degraded performance (IC < 0.03 or Sharpe < 1.0),
    the system should update its status to MONITORING.
    
    白皮书依据: 第四章 4.4.3 生命周期管理 - Requirement 5.5
    Validates: Requirements 5.5
    """
    # 创建生命周期管理器
    lifecycle_manager = LifecycleManager()
    
    # 确保初始状态是ACTIVE
    assert metadata.lifecycle_state == LifecycleState.ACTIVE
    
    # 更新生命周期状态（性能下降）
    new_state = lifecycle_manager.update_lifecycle_state(
        metadata,
        recent_ic=degraded_ic,
        recent_sharpe=degraded_sharpe
    )
    
    # 验证：状态应该变为MONITORING
    assert new_state == LifecycleState.MONITORING, \
        f"性能下降后状态应该变为MONITORING，实际: {new_state.value}"
    
    assert metadata.lifecycle_state == LifecycleState.MONITORING, \
        "元数据中的状态应该更新为MONITORING"


# ============================================================================
# Property 24: Time-Based Decay Detection
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    metadata=strategy_metadata_strategy(lifecycle_state=LifecycleState.MONITORING),
    low_ic=st.floats(min_value=0.01, max_value=0.029)
)
def test_property_24_time_based_decay_detection(metadata, low_ic):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 24: Time-Based Decay Detection
    
    For any MONITORING strategy with IC < 0.03 for 30 consecutive days,
    the system should mark it as DEPRECATED.
    
    白皮书依据: 第四章 4.4.3 生命周期管理 - Requirement 5.6
    Validates: Requirements 5.6
    """
    # 创建生命周期管理器
    lifecycle_manager = LifecycleManager()
    
    # 设置初始状态为MONITORING
    metadata.lifecycle_state = LifecycleState.MONITORING
    metadata.ic_below_threshold_days = 0
    
    # 模拟30天IC低于阈值
    for day in range(30):
        new_state = lifecycle_manager.update_lifecycle_state(
            metadata,
            recent_ic=low_ic
        )
    
    # 验证：IC低于阈值的天数应该达到30天
    assert metadata.ic_below_threshold_days >= 30, \
        f"IC低于阈值的天数应该>=30，实际: {metadata.ic_below_threshold_days}"
    
    # 验证：状态应该变为DEPRECATED
    assert new_state == LifecycleState.DEPRECATED, \
        f"IC连续30天低于阈值后状态应该变为DEPRECATED，实际: {new_state.value}"


# ============================================================================
# Property 25: Deprecated Strategy Capital Restriction
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    deprecated_metadata=strategy_metadata_strategy(lifecycle_state=LifecycleState.DEPRECATED),
    retired_metadata=strategy_metadata_strategy(lifecycle_state=LifecycleState.RETIRED)
)
def test_property_25_deprecated_strategy_capital_restriction(deprecated_metadata, retired_metadata):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 25: Deprecated Strategy Capital Restriction
    
    For any strategy in DEPRECATED or RETIRED state, the system should prevent
    new capital allocation.
    
    白皮书依据: 第四章 4.4.3 生命周期管理 - Requirement 5.7
    Validates: Requirements 5.7
    """
    # 创建生命周期管理器
    lifecycle_manager = LifecycleManager()
    
    # 验证：DEPRECATED策略不能分配新资金
    assert not lifecycle_manager.can_allocate_capital(deprecated_metadata), \
        "DEPRECATED策略不应该允许分配新资金"
    
    # 验证：RETIRED策略不能分配新资金
    assert not lifecycle_manager.can_allocate_capital(retired_metadata), \
        "RETIRED策略不应该允许分配新资金"
    
    # 验证：资金分配乘数为0
    assert lifecycle_manager.get_capital_multiplier(deprecated_metadata) == 0.0, \
        "DEPRECATED策略的资金分配乘数应该为0"
    
    assert lifecycle_manager.get_capital_multiplier(retired_metadata) == 0.0, \
        "RETIRED策略的资金分配乘数应该为0"


# ============================================================================
# Property 26: Lifecycle State Transitions
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    metadata=strategy_metadata_strategy(lifecycle_state=LifecycleState.ACTIVE)
)
def test_property_26_lifecycle_state_transitions(metadata):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 26: Lifecycle State Transitions
    
    For any strategy, lifecycle state transitions should follow the valid path:
    ACTIVE → MONITORING → DEPRECATED → RETIRED
    
    白皮书依据: 第四章 4.4.3 生命周期管理 - Requirement 5.9
    Validates: Requirements 5.9
    """
    # 创建生命周期管理器
    lifecycle_manager = LifecycleManager()
    
    # 初始状态：ACTIVE
    assert metadata.lifecycle_state == LifecycleState.ACTIVE
    
    # 转换1: ACTIVE → MONITORING（性能下降）
    new_state = lifecycle_manager.update_lifecycle_state(
        metadata,
        recent_ic=0.02,  # 低于0.03
        recent_sharpe=0.8  # 低于1.0
    )
    assert new_state == LifecycleState.MONITORING, \
        "ACTIVE状态在性能下降后应该转换为MONITORING"
    
    # 转换2: MONITORING → DEPRECATED（IC连续30天低于阈值）
    metadata.ic_below_threshold_days = 30
    new_state = lifecycle_manager.update_lifecycle_state(
        metadata,
        recent_ic=0.02
    )
    assert new_state == LifecycleState.DEPRECATED, \
        "MONITORING状态在IC连续30天低于阈值后应该转换为DEPRECATED"
    
    # 转换3: DEPRECATED → RETIRED（严重衰减）
    metadata.ic_below_threshold_days = 60
    new_state = lifecycle_manager.update_lifecycle_state(
        metadata,
        recent_ic=0.01,
        recent_sharpe=0.3
    )
    assert new_state == LifecycleState.RETIRED, \
        "DEPRECATED状态在严重衰减后应该转换为RETIRED"
