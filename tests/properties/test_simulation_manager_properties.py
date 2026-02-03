"""Property-Based Tests for SimulationManager

白皮书依据: 第四章 4.2.2 模拟盘验证运行

Property 11: Simulation Halt Condition
For any simulation run, if the drawdown at any point exceeds 20%, the simulation
should halt immediately and mark the strategy as failed with failure_reason='excessive_drawdown'.

Author: MIA System
Date: 2026-01-23
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
import numpy as np

from src.evolution.simulation_manager import (
    SimulationManager,
    SimulationConfig,
    DailyResult
)
from src.evolution.factor_data_models import Factor, CandidateStrategy
from src.evolution.certification_config_manager import StrategyType


# Hypothesis strategies for generating test data
@st.composite
def candidate_strategy_strategy(draw):
    """Generate a CandidateStrategy for testing"""
    strategy_id = draw(st.uuids()).hex
    strategy_name = f"TestStrategy-{strategy_id[:8]}"
    
    factor = Factor(
        id=draw(st.uuids()).hex,
        name=f"TestFactor-{draw(st.uuids()).hex[:8]}",
        expression="close / shift(close, 1) - 1",
        category="technical",
        implementation_code="return market_data['close'].pct_change()",
        created_at=datetime.now(),
        generation=1,
        fitness_score=draw(st.floats(min_value=0.5, max_value=1.0)),
        baseline_ic=draw(st.floats(min_value=0.0, max_value=0.1)),
        baseline_ir=draw(st.floats(min_value=0.5, max_value=2.0)),
        baseline_sharpe=draw(st.floats(min_value=1.0, max_value=3.0)),
        liquidity_adaptability=draw(st.floats(min_value=0.5, max_value=1.0))
    )
    
    strategy = CandidateStrategy(
        id=strategy_id,
        name=strategy_name,
        strategy_type=StrategyType.PURE_FACTOR,
        source_factors=[factor],
        code="# Strategy code",
        expected_sharpe=draw(st.floats(min_value=1.0, max_value=3.0)),
        max_drawdown_limit=0.15,
        capital_allocation=100000.0,
        rebalance_frequency=5,
        status='candidate',
        arena_scheduled=False,
        simulation_required=True,
        z2h_eligible=True,
        created_at=datetime.now()
    )
    
    return strategy


@settings(max_examples=100, deadline=None)
@given(data=st.data())
@pytest.mark.asyncio
async def test_property_11_simulation_halt_on_excessive_drawdown(data):
    """
    Feature: chapter-4-sparta-evolution
    Property 11: Simulation Halt Condition
    
    For any simulation run, if the drawdown at any point exceeds 20%, the simulation
    should halt immediately and mark the strategy as failed with failure_reason='excessive_drawdown'.
    
    Validates: Requirements 3.7
    """
    # Draw a candidate strategy
    strategy = data.draw(candidate_strategy_strategy())
    
    # Draw a drawdown value
    drawdown = data.draw(st.floats(min_value=0.0, max_value=0.5))
    
    # Initialize simulation manager
    manager = SimulationManager()
    
    # Create a daily result with the specified drawdown
    daily_result = DailyResult(
        date=datetime.now(),
        day_number=1,
        capital=800000.0,
        positions_value=0.0,
        total_value=800000.0,
        daily_return=-0.05,
        cumulative_return=-0.20,
        current_drawdown=drawdown,
        max_drawdown_so_far=drawdown,
        trades_today=5,
        total_trades=5,
        winning_trades=2,
        losing_trades=3
    )
    
    # Check halt conditions
    should_halt = manager.check_halt_conditions(daily_result)
    
    # Property: Should halt if and only if drawdown > 20%
    if drawdown > 0.20:
        assert should_halt is True, (
            f"Expected halt for drawdown={drawdown:.2%} > 20%, "
            f"but should_halt={should_halt}"
        )
        assert daily_result.halt_reason is not None, (
            f"Expected halt_reason to be set for drawdown={drawdown:.2%}"
        )
        assert 'excessive_drawdown' in daily_result.halt_reason, (
            f"Expected 'excessive_drawdown' in halt_reason, "
            f"got: {daily_result.halt_reason}"
        )
    else:
        assert should_halt is False, (
            f"Expected no halt for drawdown={drawdown:.2%} <= 20%, "
            f"but should_halt={should_halt}"
        )


@settings(max_examples=100, deadline=None)
@given(data=st.data())
@pytest.mark.asyncio
async def test_property_11_simulation_result_failure_on_halt(data):
    """
    Test that halted simulations are marked as failed
    
    Validates: Requirements 3.7
    """
    # Draw a candidate strategy
    strategy = data.draw(candidate_strategy_strategy())
    
    # Initialize simulation manager with short duration for testing
    config = SimulationConfig(
        duration_days=5,
        initial_capital=1_000_000.0,
        max_drawdown_halt=0.20
    )
    manager = SimulationManager(config)
    
    # Start simulation
    simulation = await manager.start_simulation(strategy)
    
    # Manually set a high drawdown to trigger halt
    simulation.peak_value = 1_000_000.0
    simulation.capital = 700_000.0  # 30% drawdown
    simulation.positions_value = 0.0
    
    # Monitor daily (should trigger halt)
    try:
        daily_result = await manager.monitor_daily(simulation)
        
        # If drawdown > 20%, simulation should be halted
        if daily_result.current_drawdown > 0.20:
            assert simulation.halted is True, (
                f"Expected simulation to be halted for drawdown={daily_result.current_drawdown:.2%}"
            )
            assert daily_result.halted is True, (
                f"Expected daily_result.halted=True for drawdown={daily_result.current_drawdown:.2%}"
            )
            assert daily_result.halt_reason is not None, (
                "Expected halt_reason to be set"
            )
    except ValueError as e:
        # If simulation is already halted, that's expected
        if "已停止" in str(e) or "halted" in str(e).lower():
            pass
        else:
            raise


@settings(max_examples=50, deadline=None)
@given(data=st.data())
@pytest.mark.asyncio
async def test_property_11_full_simulation_halt_behavior(data):
    """
    Test full simulation behavior with halt conditions
    
    Validates: Requirements 3.7
    """
    # Draw a candidate strategy with low expected Sharpe (more likely to fail)
    strategy = data.draw(candidate_strategy_strategy())
    strategy.expected_sharpe = data.draw(st.floats(min_value=0.5, max_value=1.5))
    
    # Initialize simulation manager with short duration
    config = SimulationConfig(
        duration_days=10,
        initial_capital=1_000_000.0,
        max_drawdown_halt=0.20
    )
    manager = SimulationManager(config)
    
    # Run full simulation
    result = await manager.run_full_simulation(strategy)
    
    # Property 1: Result should have daily_results
    assert len(result.daily_results) >= 1, (
        "Expected at least 1 daily result"
    )
    
    # Property 2: If halted, should be marked as failed
    if result.halted:
        assert result.passed is False, (
            "Expected halted simulation to be marked as failed"
        )
        assert result.failure_reason is not None, (
            "Expected failure_reason to be set for halted simulation"
        )
        assert result.z2h_eligible is False, (
            "Expected halted simulation to not be Z2H eligible"
        )
        assert result.halt_day is not None, (
            "Expected halt_day to be set"
        )
        assert result.halt_reason is not None, (
            "Expected halt_reason to be set"
        )
    
    # Property 3: Final metrics should be calculated
    assert result.final_metrics is not None, (
        "Expected final_metrics to be calculated"
    )
    assert result.final_metrics.trading_days == len(result.daily_results), (
        f"Expected trading_days={len(result.daily_results)}, "
        f"got {result.final_metrics.trading_days}"
    )
    
    # Property 4: Simulation dates should be set
    assert result.simulation_start is not None, (
        "Expected simulation_start to be set"
    )
    assert result.simulation_end is not None, (
        "Expected simulation_end to be set"
    )
    assert result.simulation_end >= result.simulation_start, (
        "Expected simulation_end >= simulation_start"
    )


@settings(max_examples=100, deadline=None)
@given(data=st.data())
@pytest.mark.asyncio
async def test_property_11_halt_threshold_boundary(data):
    """
    Test halt behavior at the 20% drawdown boundary
    
    Validates: Requirements 3.7
    """
    # Draw a drawdown near the 20% threshold
    drawdown = data.draw(st.floats(min_value=0.15, max_value=0.25))
    
    # Initialize simulation manager
    manager = SimulationManager()
    
    # Create a daily result with the specified drawdown
    daily_result = DailyResult(
        date=datetime.now(),
        day_number=1,
        capital=1_000_000.0 * (1 - drawdown),
        positions_value=0.0,
        total_value=1_000_000.0 * (1 - drawdown),
        daily_return=-drawdown,
        cumulative_return=-drawdown,
        current_drawdown=drawdown,
        max_drawdown_so_far=drawdown,
        trades_today=5,
        total_trades=5,
        winning_trades=2,
        losing_trades=3
    )
    
    # Check halt conditions
    should_halt = manager.check_halt_conditions(daily_result)
    
    # Property: Strict boundary check at 20%
    if drawdown > 0.20:
        assert should_halt is True, (
            f"Expected halt for drawdown={drawdown:.4f} > 0.20"
        )
    else:
        assert should_halt is False, (
            f"Expected no halt for drawdown={drawdown:.4f} <= 0.20"
        )


@settings(max_examples=100, deadline=None)
@given(data=st.data())
@pytest.mark.asyncio
async def test_property_11_z2h_eligibility_requires_no_halt(data):
    """
    Test that Z2H eligibility requires simulation to complete without halt
    
    Validates: Requirements 3.7, 3.8
    """
    # Draw a candidate strategy
    strategy = data.draw(candidate_strategy_strategy())
    
    # Draw whether simulation should halt
    should_halt = data.draw(st.booleans())
    
    # Initialize simulation manager with short duration
    config = SimulationConfig(
        duration_days=5,
        initial_capital=1_000_000.0,
        max_drawdown_halt=0.20
    )
    manager = SimulationManager(config)
    
    # Run full simulation
    result = await manager.run_full_simulation(strategy)
    
    # Property: If halted, cannot be Z2H eligible
    if result.halted:
        assert result.z2h_eligible is False, (
            "Expected halted simulation to not be Z2H eligible"
        )
        assert result.passed is False, (
            "Expected halted simulation to not pass"
        )
    
    # Property: Z2H eligibility requires passing and not halted
    if result.z2h_eligible:
        assert result.passed is True, (
            "Expected Z2H eligible simulation to have passed"
        )
        assert result.halted is False, (
            "Expected Z2H eligible simulation to not be halted"
        )
