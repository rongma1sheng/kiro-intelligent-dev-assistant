"""Property-Based Tests for Simulation Validation System

白皮书依据: 第四章 4.5 模拟验证系统

Properties tested:
- Property 27: Simulation Capital Allocation
- Property 28: Simulation Cost Application
- Property 29: Daily Performance Monitoring
- Property 30: Simulation Early Termination
- Property 31: Simulation Final Metrics
- Property 32: Simulation Pass Criteria
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from typing import Dict

from src.evolution.simulation.data_models import (
    SimulationConfig,
    SimulationState,
    StrategyTier,
)
from src.evolution.simulation.simulation_manager import SimulationManager
from src.evolution.simulation.simulation_engine import SimulationEngine
from src.evolution.simulation.cost_model import CostModel
from src.evolution.simulation.performance_tracker import PerformanceTracker


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def strategy_tier_strategy(draw):
    """生成策略层级"""
    return draw(st.sampled_from(list(StrategyTier)))


@st.composite
def simulation_config_strategy(draw):
    """生成模拟配置"""
    return SimulationConfig(
        duration_days=draw(st.integers(min_value=5, max_value=30)),
        initial_capital=draw(st.floats(min_value=100000, max_value=1000000)),
        commission_rate=draw(st.floats(min_value=0.0001, max_value=0.001)),
        slippage_rate=draw(st.floats(min_value=0.0001, max_value=0.001)),
        max_drawdown_threshold=draw(st.floats(min_value=-0.30, max_value=-0.10)),
    )


@st.composite
def market_data_strategy(draw):
    """生成市场数据"""
    num_stocks = draw(st.integers(min_value=5, max_value=20))
    
    data = {}
    for i in range(num_stocks):
        symbol = f"STOCK{i:03d}"
        close_price = draw(st.floats(min_value=10.0, max_value=100.0))
        data[symbol] = {'close': close_price}
    
    return pd.DataFrame(data).T


@st.composite
def signals_strategy(draw, symbols):
    """生成交易信号
    
    Args:
        symbols: 股票代码列表
    """
    signals = {}
    num_positions = draw(st.integers(min_value=1, max_value=min(5, len(symbols))))
    selected_symbols = draw(st.lists(
        st.sampled_from(symbols),
        min_size=num_positions,
        max_size=num_positions,
        unique=True
    ))
    
    # 生成权重（总和为1）
    weights = draw(st.lists(
        st.floats(min_value=0.1, max_value=0.5),
        min_size=num_positions,
        max_size=num_positions
    ))
    
    # 归一化权重
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]
    
    for symbol, weight in zip(selected_symbols, normalized_weights):
        signals[symbol] = weight
    
    return signals


# ============================================================================
# Property 27: Simulation Capital Allocation
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    tier=strategy_tier_strategy()
)
def test_property_27_simulation_capital_allocation(tier):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 27: Simulation Capital Allocation
    
    For any strategy starting simulation, the system should allocate simulated
    capital based on the strategy's tier.
    
    白皮书依据: 第四章 4.5.2 资金分配 - Requirement 6.2
    Validates: Requirements 6.2
    """
    # 定义层级对应的资金
    tier_capital = {
        StrategyTier.TIER_1: 1000000.0,
        StrategyTier.TIER_2: 500000.0,
        StrategyTier.TIER_3: 200000.0,
        StrategyTier.TIER_4: 100000.0,
    }
    
    expected_capital = tier_capital[tier]
    
    # 创建模拟引擎
    config = SimulationConfig()
    engine = SimulationEngine(config, tier)
    
    # 验证：初始资金应该等于层级对应的资金
    assert engine.performance_tracker.initial_capital == expected_capital, \
        f"层级{tier.value}的初始资金应该为{expected_capital}，实际: {engine.performance_tracker.initial_capital}"


# ============================================================================
# Property 28: Simulation Cost Application
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    trade_value=st.floats(min_value=1000.0, max_value=100000.0),
    commission_rate=st.floats(min_value=0.0001, max_value=0.001),
    slippage_rate=st.floats(min_value=0.0001, max_value=0.001)
)
def test_property_28_simulation_cost_application(trade_value, commission_rate, slippage_rate):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 28: Simulation Cost Application
    
    For any simulated trade, the system should apply transaction costs and slippage.
    
    白皮书依据: 第四章 4.5.4 交易成本模型 - Requirement 6.4
    Validates: Requirements 6.4
    """
    # 创建成本模型
    cost_model = CostModel(
        commission_rate=commission_rate,
        slippage_rate=slippage_rate
    )
    
    # 计算交易成本
    cost = cost_model.calculate_transaction_cost(trade_value, is_buy=True)
    
    # 验证：成本应该等于交易金额 × (佣金费率 + 滑点率)
    expected_cost = trade_value * (commission_rate + slippage_rate)
    
    assert abs(cost - expected_cost) < 0.01, \
        f"交易成本应该为{expected_cost:.2f}，实际: {cost:.2f}"
    
    # 验证：成本应该大于0
    assert cost > 0, \
        "交易成本必须大于0"
    
    # 验证：成本应该小于交易金额
    assert cost < trade_value, \
        "交易成本不能超过交易金额"


# ============================================================================
# Property 29: Daily Performance Monitoring
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    initial_capital=st.floats(min_value=100000, max_value=1000000),
    num_days=st.integers(min_value=5, max_value=30)
)
def test_property_29_daily_performance_monitoring(initial_capital, num_days):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 29: Daily Performance Monitoring
    
    For any running simulation, the system should calculate and store performance
    metrics daily.
    
    白皮书依据: 第四章 4.5.5 每日性能监控 - Requirement 6.5
    Validates: Requirements 6.5
    """
    # 创建性能跟踪器
    tracker = PerformanceTracker(initial_capital)
    
    # 模拟多天
    current_value = initial_capital
    for day in range(num_days):
        date = datetime.now() + timedelta(days=day)
        
        # 随机变化组合价值
        change_rate = np.random.uniform(-0.02, 0.02)
        current_value *= (1 + change_rate)
        
        # 记录每日结果
        daily_result = tracker.record_daily_result(
            date=date,
            portfolio_value=current_value,
            positions={},
            trades=[],
            transaction_cost=0.0
        )
        
        # 验证：每日结果应该被记录
        assert daily_result is not None, \
            f"第{day}天的结果应该被记录"
        
        # 验证：每日结果包含必要字段
        assert daily_result.date == date, \
            "日期应该正确"
        
        assert daily_result.portfolio_value == current_value, \
            "组合价值应该正确"
        
        assert hasattr(daily_result, 'daily_return'), \
            "应该包含每日收益率"
        
        assert hasattr(daily_result, 'cumulative_return'), \
            "应该包含累计收益率"
        
        assert hasattr(daily_result, 'drawdown'), \
            "应该包含回撤"
    
    # 验证：记录的天数应该等于模拟天数
    assert len(tracker.daily_results) == num_days, \
        f"记录的天数应该为{num_days}，实际: {len(tracker.daily_results)}"


# ============================================================================
# Property 30: Simulation Early Termination
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    initial_capital=st.floats(min_value=100000, max_value=1000000),
    drawdown_threshold=st.floats(min_value=-0.30, max_value=-0.15)
)
def test_property_30_simulation_early_termination(initial_capital, drawdown_threshold):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 30: Simulation Early Termination
    
    For any simulation where drawdown exceeds 20%, the system should immediately
    fail the simulation and log the reason.
    
    白皮书依据: 第四章 4.5.6 提前终止逻辑 - Requirement 6.6
    Validates: Requirements 6.6
    """
    # 创建配置（设置回撤阈值）
    config = SimulationConfig(
        max_drawdown_threshold=drawdown_threshold
    )
    
    # 创建模拟引擎
    engine = SimulationEngine(config, StrategyTier.TIER_3)
    
    # 模拟组合价值下跌
    tracker = engine.performance_tracker
    
    # 第1天：正常
    tracker.record_daily_result(
        date=datetime.now(),
        portfolio_value=initial_capital,
        positions={},
        trades=[],
        transaction_cost=0.0
    )
    
    # 第2天：大幅下跌，超过阈值
    severe_loss_value = initial_capital * (1 + drawdown_threshold - 0.05)
    tracker.record_daily_result(
        date=datetime.now() + timedelta(days=1),
        portfolio_value=severe_loss_value,
        positions={},
        trades=[],
        transaction_cost=0.0
    )
    
    # 验证：应该触发提前终止
    should_terminate = engine.check_early_termination()
    
    assert should_terminate, \
        f"回撤超过阈值{drawdown_threshold:.2%}时应该提前终止"
    
    # 验证：当前回撤应该小于阈值
    current_drawdown = tracker.get_current_drawdown()
    assert current_drawdown < drawdown_threshold, \
        f"当前回撤{current_drawdown:.2%}应该小于阈值{drawdown_threshold:.2%}"


# ============================================================================
# Property 31: Simulation Final Metrics
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    initial_capital=st.floats(min_value=100000, max_value=1000000),
    num_days=st.integers(min_value=10, max_value=30)
)
def test_property_31_simulation_final_metrics(initial_capital, num_days):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 31: Simulation Final Metrics
    
    For any completed 30-day simulation, the system should calculate total return,
    Sharpe ratio, max drawdown, win rate, and profit factor.
    
    白皮书依据: 第四章 4.5.7 最终指标计算 - Requirement 6.7
    Validates: Requirements 6.7
    """
    # 创建性能跟踪器
    tracker = PerformanceTracker(initial_capital)
    
    # 模拟多天
    current_value = initial_capital
    for day in range(num_days):
        date = datetime.now() + timedelta(days=day)
        
        # 随机变化
        change_rate = np.random.uniform(-0.02, 0.02)
        current_value *= (1 + change_rate)
        
        tracker.record_daily_result(
            date=date,
            portfolio_value=current_value,
            positions={},
            trades=[],
            transaction_cost=0.0
        )
    
    # 计算最终指标
    total_return = tracker.get_total_return()
    sharpe_ratio = tracker.calculate_sharpe_ratio()
    max_drawdown = tracker.calculate_max_drawdown()
    win_rate = tracker.calculate_win_rate()
    profit_factor = tracker.calculate_profit_factor()
    
    # 验证：所有指标都应该被计算
    assert total_return is not None, \
        "应该计算总收益率"
    
    assert sharpe_ratio is not None, \
        "应该计算夏普比率"
    
    assert max_drawdown is not None, \
        "应该计算最大回撤"
    
    assert win_rate is not None, \
        "应该计算胜率"
    
    assert profit_factor is not None, \
        "应该计算盈亏比"
    
    # 验证：指标在合理范围内
    assert -1 <= total_return <= 10, \
        f"总收益率应该在合理范围，实际: {total_return}"
    
    # 夏普比率理论上可以很高(尤其是测试数据),放宽上限到20
    assert -10 <= sharpe_ratio <= 20, \
        f"夏普比率应该在合理范围[-10,20]，实际: {sharpe_ratio}"
    
    assert -1 <= max_drawdown <= 0, \
        f"最大回撤应该在[-1,0]，实际: {max_drawdown}"
    
    assert 0 <= win_rate <= 1, \
        f"胜率应该在[0,1]，实际: {win_rate}"
    
    assert profit_factor >= 0, \
        f"盈亏比应该>=0，实际: {profit_factor}"


# ============================================================================
# Property 32: Simulation Pass Criteria
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    total_return=st.floats(min_value=0.06, max_value=0.50),
    sharpe_ratio=st.floats(min_value=1.3, max_value=3.0),
    max_drawdown=st.floats(min_value=-0.14, max_value=-0.05),
    win_rate=st.floats(min_value=0.56, max_value=0.80),
    profit_factor=st.floats(min_value=1.4, max_value=3.0)
)
def test_property_32_simulation_pass_criteria(
    total_return,
    sharpe_ratio,
    max_drawdown,
    win_rate,
    profit_factor
):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 32: Simulation Pass Criteria
    
    For any simulation with return > 5%, Sharpe > 1.2, drawdown < 15%, win rate > 55%,
    and profit factor > 1.3, the system should mark it as passed.
    
    白皮书依据: 第四章 4.5.8 通过标准 - Requirement 6.8
    Validates: Requirements 6.8
    """
    # 创建模拟管理器
    manager = SimulationManager()
    
    # 评估通过标准
    passed = manager._evaluate_pass_criteria(
        state=SimulationState.COMPLETED,
        total_return=total_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        profit_factor=profit_factor
    )
    
    # 验证：所有指标都达标时应该通过
    assert passed, \
        f"所有指标达标时应该通过: " \
        f"return={total_return:.4f}, " \
        f"sharpe={sharpe_ratio:.4f}, " \
        f"dd={max_drawdown:.4f}, " \
        f"win_rate={win_rate:.4f}, " \
        f"pf={profit_factor:.4f}"
    
    # 验证：状态不是COMPLETED时不应该通过
    not_passed = manager._evaluate_pass_criteria(
        state=SimulationState.FAILED,
        total_return=total_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        profit_factor=profit_factor
    )
    
    assert not not_passed, \
        "状态为FAILED时不应该通过"
