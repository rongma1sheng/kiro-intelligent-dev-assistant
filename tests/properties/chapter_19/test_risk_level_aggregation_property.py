"""Property 24: Risk Level Aggregation

白皮书依据: 第十九章 19.1 风险识别与评估

**Validates: Requirements 11.1**

Property: 整体风险等级应该是所有单项风险等级的最大值

This property ensures that the overall risk level correctly aggregates
individual risk levels by taking the maximum severity.
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.risk.risk_identification_system import (
    RiskIdentificationSystem,
    RiskLevel
)


# Strategy for generating risk levels
risk_level_strategy = st.sampled_from([
    RiskLevel.LOW,
    RiskLevel.MEDIUM,
    RiskLevel.HIGH,
    RiskLevel.CRITICAL
])


@settings(max_examples=100)
@given(
    market_volatility=st.floats(min_value=0.01, max_value=0.20),
    daily_pnl_ratio=st.floats(min_value=-0.20, max_value=0.20),
    redis_health=st.floats(min_value=0.50, max_value=1.0),
    gpu_health=st.floats(min_value=0.50, max_value=1.0)
)
def test_risk_level_aggregation_property(
    market_volatility: float,
    daily_pnl_ratio: float,
    redis_health: float,
    gpu_health: float
):
    """Property 24: 整体风险等级是所有单项风险的最大值
    
    白皮书依据: 第十九章 19.1 风险识别与评估
    
    Property: overall_risk_level = max(all_individual_risk_levels)
    
    This ensures that:
    1. Overall risk is never lower than any individual risk
    2. Overall risk equals the highest individual risk
    3. Risk aggregation is consistent and monotonic
    """
    # Create fresh system instance for this test
    system = RiskIdentificationSystem(
        market_volatility_threshold=0.05,
        daily_loss_threshold=0.10,
        liquidity_threshold=0.20,
        system_health_threshold=0.80
    )
    
    # Trigger various risk events
    individual_risk_levels = []
    
    # Market risk
    market_event = system.monitor_market_risk(
        volatility=market_volatility,
        daily_pnl_ratio=daily_pnl_ratio
    )
    if market_event:
        individual_risk_levels.append(market_event.risk_level)
    
    # System risk
    system_event = system.monitor_system_risk(
        redis_health=redis_health,
        gpu_health=gpu_health,
        network_health=0.90
    )
    if system_event:
        individual_risk_levels.append(system_event.risk_level)
    
    # Get overall risk level
    overall_risk = system.get_overall_risk_level()
    
    # Property: Overall risk should be the maximum of individual risks
    if individual_risk_levels:
        # Define risk level ordering
        risk_order = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3
        }
        
        # Find maximum individual risk
        max_individual_risk = max(individual_risk_levels, key=lambda r: risk_order[r])
        
        # Overall risk should equal the maximum individual risk
        assert overall_risk == max_individual_risk, (
            f"Overall risk {overall_risk} should equal max individual risk {max_individual_risk}. "
            f"Individual risks: {individual_risk_levels}"
        )
    else:
        # No risk events, overall risk should be LOW
        assert overall_risk == RiskLevel.LOW, (
            f"Overall risk should be LOW when no risk events, got {overall_risk}"
        )


@settings(max_examples=100)
@given(
    num_events=st.integers(min_value=1, max_value=10)
)
def test_risk_level_aggregation_monotonicity(num_events: int):
    """Property 24: 风险等级聚合的单调性
    
    白皮书依据: 第十九章 19.1 风险识别与评估
    
    Property: Adding more risk events never decreases overall risk level
    
    This ensures that:
    1. Risk aggregation is monotonic
    2. More risks = higher or equal overall risk
    3. System correctly tracks cumulative risk
    """
    # Create fresh system instance
    system = RiskIdentificationSystem()
    
    # Track overall risk as we add events
    previous_risk = system.get_overall_risk_level()
    
    risk_order = {
        RiskLevel.LOW: 0,
        RiskLevel.MEDIUM: 1,
        RiskLevel.HIGH: 2,
        RiskLevel.CRITICAL: 3
    }
    
    # Add multiple risk events
    for i in range(num_events):
        # Trigger a market risk event with increasing severity
        volatility = 0.05 + (i * 0.01)  # Increasing volatility
        system.monitor_market_risk(
            volatility=min(volatility, 0.20),
            daily_pnl_ratio=0.01
        )
        
        # Get new overall risk
        current_risk = system.get_overall_risk_level()
        
        # Property: Risk should never decrease
        assert risk_order[current_risk] >= risk_order[previous_risk], (
            f"Risk decreased from {previous_risk} to {current_risk} after adding event {i+1}"
        )
        
        previous_risk = current_risk


def test_risk_level_aggregation_critical_dominates():
    """Property 24: CRITICAL风险总是主导整体风险等级
    
    白皮书依据: 第十九章 19.1 风险识别与评估
    
    Property: If any individual risk is CRITICAL, overall risk must be CRITICAL
    
    This ensures that:
    1. Critical risks are never masked by lower risks
    2. Emergency response is triggered for critical situations
    3. Risk aggregation prioritizes safety
    """
    system = RiskIdentificationSystem()
    
    # Trigger a CRITICAL market risk (daily loss > 10%)
    system.monitor_market_risk(
        volatility=0.03,
        daily_pnl_ratio=-0.15  # 15% loss
    )
    
    # Trigger some lower-level risks
    system.monitor_system_risk(
        redis_health=0.75,  # MEDIUM risk
        gpu_health=0.90,
        network_health=0.85
    )
    
    # Overall risk must be CRITICAL
    overall_risk = system.get_overall_risk_level()
    assert overall_risk == RiskLevel.CRITICAL, (
        f"Overall risk should be CRITICAL when any individual risk is CRITICAL, got {overall_risk}"
    )


def test_risk_level_aggregation_empty_events():
    """Property 24: 无风险事件时整体风险为LOW
    
    白皮书依据: 第十九章 19.1 风险识别与评估
    
    Property: When no risk events exist, overall risk should be LOW
    
    This ensures that:
    1. Default state is safe
    2. System starts in low-risk mode
    3. Risk aggregation handles empty case correctly
    """
    system = RiskIdentificationSystem()
    
    # No risk events triggered
    overall_risk = system.get_overall_risk_level()
    
    # Overall risk should be LOW
    assert overall_risk == RiskLevel.LOW, (
        f"Overall risk should be LOW when no events, got {overall_risk}"
    )
