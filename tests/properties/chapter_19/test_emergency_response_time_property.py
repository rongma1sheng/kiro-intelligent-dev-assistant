"""Property 22: Emergency Response Time Bounds

白皮书依据: 第十九章 19.3 应急响应流程

**Validates: Requirements 11.3**

Property: 应急响应时间必须满足SLA要求
- WARNING (P2): 30分钟内响应
- DANGER (P1): 5分钟内响应
- CRITICAL (P0): 立即响应

This property ensures that emergency response times meet the defined SLA
for each alert level.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta

from src.risk.emergency_response_system import (
    EmergencyResponseSystem,
    AlertLevel
)


# Strategy for generating alert levels
alert_level_strategy = st.sampled_from([
    AlertLevel.WARNING,
    AlertLevel.DANGER,
    AlertLevel.CRITICAL
])

# Strategy for generating non-empty descriptions (excluding whitespace-only strings)
description_strategy = st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != "")


@settings(max_examples=100)
@given(
    alert_level=alert_level_strategy,
    description=description_strategy
)
def test_emergency_response_time_sla_property(
    alert_level: AlertLevel,
    description: str
):
    """Property 22: 应急响应时间满足SLA
    
    白皮书依据: 第十九章 19.3.1 应急响应分级
    
    Property: response_time <= SLA[alert_level]
    
    SLA Requirements:
    - WARNING: 30 minutes (1800 seconds)
    - DANGER: 5 minutes (300 seconds)
    - CRITICAL: 0 seconds (immediate)
    
    This ensures that:
    1. Response times meet defined SLA
    2. Higher severity alerts get faster response
    3. System can handle emergency situations promptly
    """
    # Create fresh system instance
    system = EmergencyResponseSystem()
    
    # Record start time
    start_time = datetime.now()
    
    # Trigger alert
    procedure = system.trigger_alert(
        alert_level=alert_level,
        description=description
    )
    
    # Record end time
    end_time = datetime.now()
    
    # Calculate response time
    response_time = (end_time - start_time).total_seconds()
    
    # Get SLA for this alert level
    sla = system.get_response_time_sla(alert_level)
    
    # Property: Response time should meet SLA
    # For CRITICAL (SLA=0), allow up to 1 second tolerance since actual execution takes time
    if alert_level == AlertLevel.CRITICAL:
        assert response_time < 1.0, (
            f"CRITICAL response time {response_time:.3f}s should be < 1s"
        )
    else:
        assert response_time <= sla, (
            f"Response time {response_time:.3f}s exceeds SLA {sla}s for {alert_level.value}"
        )
    
    # Verify procedure was created
    assert procedure is not None
    assert procedure.alert_level == alert_level
    assert procedure.description == description


def test_emergency_response_sla_ordering():
    """Property 22: SLA时间按严重程度递减
    
    白皮书依据: 第十九章 19.3.1 应急响应分级
    
    Property: SLA[CRITICAL] < SLA[DANGER] < SLA[WARNING]
    
    This ensures that:
    1. More severe alerts have stricter SLA
    2. SLA ordering is consistent with severity
    3. Emergency response prioritizes critical situations
    """
    system = EmergencyResponseSystem()
    
    # Get SLA for each level
    sla_warning = system.get_response_time_sla(AlertLevel.WARNING)
    sla_danger = system.get_response_time_sla(AlertLevel.DANGER)
    sla_critical = system.get_response_time_sla(AlertLevel.CRITICAL)
    
    # Property: SLA should decrease with severity
    assert sla_critical < sla_danger, (
        f"CRITICAL SLA ({sla_critical}s) should be < DANGER SLA ({sla_danger}s)"
    )
    assert sla_danger < sla_warning, (
        f"DANGER SLA ({sla_danger}s) should be < WARNING SLA ({sla_warning}s)"
    )
    
    # Verify specific SLA values from whitepaper
    assert sla_warning == 30 * 60, f"WARNING SLA should be 30 minutes, got {sla_warning}s"
    assert sla_danger == 5 * 60, f"DANGER SLA should be 5 minutes, got {sla_danger}s"
    assert sla_critical == 0, f"CRITICAL SLA should be immediate (0s), got {sla_critical}s"


@settings(max_examples=50)
@given(
    num_alerts=st.integers(min_value=1, max_value=20)
)
def test_emergency_response_time_consistency(num_alerts: int):
    """Property 22: 多次响应时间的一致性
    
    白皮书依据: 第十九章 19.3 应急响应流程
    
    Property: All response times for same alert level should meet SLA
    
    This ensures that:
    1. Response time is consistent across multiple alerts
    2. System doesn't degrade under load
    3. SLA is maintained for all alerts
    """
    system = EmergencyResponseSystem()
    
    # Trigger multiple alerts of each level
    for alert_level in [AlertLevel.WARNING, AlertLevel.DANGER, AlertLevel.CRITICAL]:
        sla = system.get_response_time_sla(alert_level)
        
        for i in range(num_alerts):
            start_time = datetime.now()
            
            procedure = system.trigger_alert(
                alert_level=alert_level,
                description=f"Test alert {i+1}"
            )
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            # Property: Each response should meet SLA
            # For CRITICAL (SLA=0), allow up to 1 second tolerance since actual execution takes time
            if alert_level == AlertLevel.CRITICAL:
                assert response_time < 1.0, (
                    f"Alert {i+1} CRITICAL response time {response_time:.3f}s should be < 1s"
                )
            else:
                assert response_time <= sla, (
                    f"Alert {i+1} response time {response_time:.3f}s exceeds SLA {sla}s "
                    f"for {alert_level.value}"
                )
            
            # Verify procedure was created
            assert procedure is not None
            assert procedure.success is True


def test_emergency_response_critical_immediate():
    """Property 22: CRITICAL级告警立即响应
    
    白皮书依据: 第十九章 19.3.1 应急响应分级
    
    Property: CRITICAL alerts must have SLA = 0 (immediate response)
    
    This ensures that:
    1. Critical situations get immediate attention
    2. No delay is acceptable for critical alerts
    3. System prioritizes safety
    """
    system = EmergencyResponseSystem()
    
    # CRITICAL SLA must be 0
    sla_critical = system.get_response_time_sla(AlertLevel.CRITICAL)
    assert sla_critical == 0, (
        f"CRITICAL SLA must be 0 (immediate), got {sla_critical}s"
    )
    
    # Trigger CRITICAL alert
    start_time = datetime.now()
    procedure = system.trigger_alert(
        alert_level=AlertLevel.CRITICAL,
        description="Critical system failure"
    )
    end_time = datetime.now()
    
    response_time = (end_time - start_time).total_seconds()
    
    # Response should be very fast (< 1 second in practice)
    assert response_time < 1.0, (
        f"CRITICAL response time {response_time:.3f}s should be < 1s"
    )
    
    # Verify procedure was created with correct level
    assert procedure.alert_level == AlertLevel.CRITICAL
    assert "P0级告警" in str(procedure.actions)


def test_emergency_response_procedure_tracking():
    """Property 22: 应急程序执行记录完整性
    
    白皮书依据: 第十九章 19.3 应急响应流程
    
    Property: All triggered alerts should be recorded in history
    
    This ensures that:
    1. Emergency response is auditable
    2. All procedures are tracked
    3. History is complete and accurate
    """
    system = EmergencyResponseSystem()
    
    # Trigger alerts of different levels
    alerts = [
        (AlertLevel.WARNING, "Warning test"),
        (AlertLevel.DANGER, "Danger test"),
        (AlertLevel.CRITICAL, "Critical test")
    ]
    
    for alert_level, description in alerts:
        system.trigger_alert(alert_level=alert_level, description=description)
    
    # Get history
    history = system.get_emergency_history(hours=24)
    
    # Property: All alerts should be in history
    assert len(history) == len(alerts), (
        f"History should contain {len(alerts)} procedures, got {len(history)}"
    )
    
    # Verify each alert is recorded
    for i, (alert_level, description) in enumerate(alerts):
        procedure = history[i]
        assert procedure.alert_level == alert_level
        assert procedure.description == description
        assert procedure.success is True
